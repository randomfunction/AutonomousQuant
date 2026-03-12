const API_BASE = 'http://localhost:8000';

export interface HypothesisData {
  hypothesis_id: string;
  hypothesis: string;
  metadata: Record<string, unknown>;
  results: Record<string, unknown>[];
}

export interface AgentRunResult {
  output: string;
  intermediate_steps: {
    tool: string;
    input: string;
    output: string;
  }[];
}

export async function fetchHypotheses(limit = 50): Promise<HypothesisData[]> {
  const res = await fetch(`${API_BASE}/api/hypotheses?limit=${limit}`);
  if (!res.ok) throw new Error(`Failed to fetch hypotheses: ${res.statusText}`);
  return res.json();
}

export async function fetchHypothesis(id: string): Promise<HypothesisData> {
  const res = await fetch(`${API_BASE}/api/hypotheses/${id}`);
  if (!res.ok) throw new Error(`Hypothesis not found: ${res.statusText}`);
  return res.json();
}

export async function runAgent(prompt: string): Promise<AgentRunResult> {
  const res = await fetch(`${API_BASE}/api/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) throw new Error(`Agent run failed: ${res.statusText}`);
  return res.json();
}

export async function checkHealth(): Promise<{ status: string; model: string }> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error('Backend not reachable');
  return res.json();
}
