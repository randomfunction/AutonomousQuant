import { useState, useEffect } from 'react';
import { fetchHypotheses, type HypothesisData } from '../api/client';

export default function HypothesisHistory() {
  const [hypotheses, setHypotheses] = useState<HypothesisData[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchHypotheses();
      setHypotheses(data);
    } catch (err) {
      console.error('Failed to load hypotheses:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="panel hypothesis-history">
      <div className="panel-header">
        <h2>📋 Hypothesis History</h2>
        <button className="refresh-btn" onClick={loadData} disabled={loading}>
          {loading ? '⏳' : '🔄'}
        </button>
      </div>
      <div className="history-container">
        {hypotheses.length === 0 ? (
          <p className="empty-state">
            No hypotheses stored yet. The agent will save its research here.
          </p>
        ) : (
          <table className="hypothesis-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Ticker</th>
                <th>Strategy</th>
                <th>Return</th>
                <th>Sharpe</th>
                <th>Drawdown</th>
              </tr>
            </thead>
            <tbody>
              {hypotheses.map((h) => {
                const result = h.results?.[0] || {};
                const totalReturn = Number(result.total_return ?? 0);
                const isSuccess = totalReturn > 0;
                const isExpanded = expanded === h.hypothesis_id;

                return (
                  <>
                    <tr
                      key={h.hypothesis_id}
                      className={`hypothesis-row ${isExpanded ? 'expanded' : ''}`}
                      onClick={() =>
                        setExpanded(isExpanded ? null : h.hypothesis_id)
                      }
                    >
                      <td>
                        <span
                          className={`status-badge ${isSuccess ? 'success' : 'failure'}`}
                        >
                          {isSuccess ? '✅' : '❌'}
                        </span>
                      </td>
                      <td className="ticker-cell">
                        {String(h.metadata?.ticker ?? 'N/A')}
                      </td>
                      <td>{String(h.metadata?.strategy_type ?? 'N/A')}</td>
                      <td
                        style={{
                          color: isSuccess ? '#66bb6a' : '#ef5350',
                          fontWeight: 600,
                        }}
                      >
                        {totalReturn.toFixed(2)}%
                      </td>
                      <td>{formatNum(result.sharpe_ratio)}</td>
                      <td>{formatNum(result.max_drawdown)}%</td>
                    </tr>
                    {isExpanded && (
                      <tr key={`${h.hypothesis_id}-detail`} className="detail-row">
                        <td colSpan={6}>
                          <div className="hypothesis-detail">
                            <h4>Hypothesis</h4>
                            <p>{h.hypothesis}</p>
                            {h.results.length > 0 && (
                              <>
                                <h4>Full Results</h4>
                                <pre>
                                  {JSON.stringify(h.results[0], null, 2)}
                                </pre>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function formatNum(val: unknown): string {
  if (val === null || val === undefined || val === 'None') return 'N/A';
  const n = Number(val);
  return isNaN(n) ? 'N/A' : n.toFixed(3);
}
