"""FAISS-backed vector store for hypothesis memory.

Runs 100% locally — no cloud accounts, no API keys.
Uses SentenceTransformer for embeddings and FAISS for similarity search.
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from backend.config import settings

logger = logging.getLogger(__name__)

# Persist directory for FAISS indices and metadata
_PERSIST_DIR = Path(settings.VECTOR_STORE_DIR)


class VectorStore:
    """Manages two FAISS indices: *hypotheses* and *results*."""

    def __init__(self) -> None:
        _PERSIST_DIR.mkdir(parents=True, exist_ok=True)

        # Load embedding model (small & fast, ~90 MB)
        self._model = SentenceTransformer("all-MiniLM-L6-v2")
        self._dim = self._model.get_sentence_embedding_dimension()

        # Hypotheses index
        self._hyp_index, self._hyp_docs, self._hyp_ids, self._hyp_metas = (
            self._load_or_create("hypotheses")
        )

        # Results index
        self._res_index, self._res_docs, self._res_ids, self._res_metas = (
            self._load_or_create("results")
        )

        logger.info(
            "FAISS VectorStore initialised — persist_dir=%s  hypotheses=%d  results=%d",
            _PERSIST_DIR,
            self._hyp_index.ntotal,
            self._res_index.ntotal,
        )

    # ------------------------------------------------------------------ #
    #  Persistence helpers                                                #
    # ------------------------------------------------------------------ #

    def _index_path(self, name: str) -> str:
        return str(_PERSIST_DIR / f"{name}.faiss")

    def _meta_path(self, name: str) -> str:
        return str(_PERSIST_DIR / f"{name}_meta.pkl")

    def _load_or_create(
        self, name: str
    ) -> tuple[faiss.IndexFlatIP, list[str], list[str], list[dict]]:
        """Load a FAISS index + metadata from disk, or create a new one."""
        idx_path = self._index_path(name)
        meta_path = self._meta_path(name)

        if os.path.exists(idx_path) and os.path.exists(meta_path):
            index = faiss.read_index(idx_path)
            with open(meta_path, "rb") as f:
                saved = pickle.load(f)
            return index, saved["docs"], saved["ids"], saved["metas"]

        # Inner-product index (we normalise vectors → cosine similarity)
        index = faiss.IndexFlatIP(self._dim)
        return index, [], [], []

    def _save(self, name: str, index, docs, ids, metas) -> None:
        faiss.write_index(index, self._index_path(name))
        with open(self._meta_path(name), "wb") as f:
            pickle.dump({"docs": docs, "ids": ids, "metas": metas}, f)

    def _embed(self, texts: list[str]) -> np.ndarray:
        """Embed texts and L2-normalise so inner-product == cosine similarity."""
        vecs = self._model.encode(texts, convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(vecs)
        return vecs

    # ------------------------------------------------------------------ #
    #  Hypotheses                                                         #
    # ------------------------------------------------------------------ #

    def store_hypothesis(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Embed and store a hypothesis.  Returns the generated ID."""
        hyp_id = str(uuid.uuid4())
        meta = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        meta = {k: _safe_meta_value(v) for k, v in meta.items()}

        vec = self._embed([text])
        self._hyp_index.add(vec)
        self._hyp_docs.append(text)
        self._hyp_ids.append(hyp_id)
        self._hyp_metas.append(meta)
        self._save(
            "hypotheses",
            self._hyp_index,
            self._hyp_docs,
            self._hyp_ids,
            self._hyp_metas,
        )
        logger.info("Stored hypothesis %s", hyp_id)
        return hyp_id

    # ------------------------------------------------------------------ #
    #  Results                                                            #
    # ------------------------------------------------------------------ #

    def store_result(
        self,
        hypothesis_id: str,
        metrics: dict[str, Any],
        summary: str = "",
    ) -> str:
        """Link a backtest result to a hypothesis."""
        res_id = str(uuid.uuid4())
        doc = summary or json.dumps(metrics, default=str)
        meta = {
            "hypothesis_id": hypothesis_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **{k: _safe_meta_value(v) for k, v in metrics.items()},
        }

        vec = self._embed([doc])
        self._res_index.add(vec)
        self._res_docs.append(doc)
        self._res_ids.append(res_id)
        self._res_metas.append(meta)
        self._save(
            "results",
            self._res_index,
            self._res_docs,
            self._res_ids,
            self._res_metas,
        )
        logger.info("Stored result %s → hypothesis %s", res_id, hypothesis_id)
        return res_id

    # ------------------------------------------------------------------ #
    #  Search                                                             #
    # ------------------------------------------------------------------ #

    def search_similar(
        self, query: str, n: int = 5
    ) -> list[dict[str, Any]]:
        """Return the *n* most similar past hypotheses + their results."""
        if self._hyp_index.ntotal == 0:
            return []

        n = min(n, self._hyp_index.ntotal)
        q_vec = self._embed([query])
        distances, indices = self._hyp_index.search(q_vec, n)

        output: list[dict[str, Any]] = []
        for rank in range(len(indices[0])):
            idx = int(indices[0][rank])
            if idx < 0:
                continue
            hyp_id = self._hyp_ids[idx]
            doc = self._hyp_docs[idx]
            meta = self._hyp_metas[idx]
            # Convert cosine similarity → cosine distance for compatibility
            distance = 1.0 - float(distances[0][rank])

            # Fetch linked results
            result_metas = [
                m for m, rid_meta in zip(self._res_metas, self._res_metas)
                if m.get("hypothesis_id") == hyp_id
            ]
            output.append(
                {
                    "hypothesis_id": hyp_id,
                    "hypothesis": doc,
                    "metadata": meta,
                    "results": result_metas,
                    "distance": distance,
                }
            )
        return output

    def get_failed_patterns(self, n: int = 10) -> list[dict[str, Any]]:
        """Return hypotheses whose backtests had negative returns."""
        failed: list[dict[str, Any]] = []
        for i, meta in enumerate(self._res_metas):
            tr = meta.get("total_return", None)
            if tr is not None and (isinstance(tr, (int, float)) and tr < 0):
                hyp_id = meta.get("hypothesis_id", "")
                # Find the hypothesis text
                doc = "N/A"
                if hyp_id in self._hyp_ids:
                    hyp_idx = self._hyp_ids.index(hyp_id)
                    doc = self._hyp_docs[hyp_idx]
                failed.append(
                    {"hypothesis_id": hyp_id, "hypothesis": doc, "result": meta}
                )
                if len(failed) >= n:
                    break
        return failed

    def get_all_hypotheses(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return all stored hypotheses with their results (most recent first)."""
        output: list[dict[str, Any]] = []
        # Iterate in reverse for most-recent-first
        for i in range(len(self._hyp_ids) - 1, -1, -1):
            if len(output) >= limit:
                break
            hyp_id = self._hyp_ids[i]
            doc = self._hyp_docs[i]
            meta = self._hyp_metas[i]
            result_metas = [
                m for m in self._res_metas
                if m.get("hypothesis_id") == hyp_id
            ]
            output.append(
                {
                    "hypothesis_id": hyp_id,
                    "hypothesis": doc,
                    "metadata": meta,
                    "results": result_metas,
                }
            )
        return output


# ------------------------------------------------------------------ #
#  Helpers                                                            #
# ------------------------------------------------------------------ #

def _safe_meta_value(v: Any) -> str | int | float | bool:
    """Metadata only accepts primitive types."""
    if isinstance(v, (str, int, float, bool)):
        return v
    return str(v)
