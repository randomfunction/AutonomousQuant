import { useEffect, useRef } from 'react';
import type { LogEvent } from '../hooks/useWebSocket';

interface ReasoningLogProps {
  logs: LogEvent[];
  isRunning: boolean;
}

const typeConfig: Record<string, { label: string; color: string; icon: string }> = {
  status: { label: 'STATUS', color: '#64b5f6', icon: '📡' },
  thinking: { label: 'THINKING', color: '#ce93d8', icon: '🧠' },
  thought: { label: 'THOUGHT', color: '#b39ddb', icon: '💭' },
  tool_call: { label: 'TOOL CALL', color: '#4fc3f7', icon: '🔧' },
  tool_result: { label: 'RESULT', color: '#81c784', icon: '📊' },
  action: { label: 'ACTION', color: '#ffb74d', icon: '⚡' },
  final_answer: { label: 'ANSWER', color: '#aed581', icon: '✅' },
  error: { label: 'ERROR', color: '#ef5350', icon: '❌' },
  done: { label: 'DONE', color: '#66bb6a', icon: '🏁' },
};

export default function ReasoningLog({ logs, isRunning }: ReasoningLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="panel reasoning-log">
      <div className="panel-header">
        <h2>🧠 Reasoning Log</h2>
        {isRunning && <span className="pulse-dot" />}
      </div>
      <div className="log-container">
        {logs.length === 0 && (
          <p className="empty-state">
            No reasoning steps yet. Send a prompt to start the agent.
          </p>
        )}
        {logs.map((log, i) => {
          const cfg = typeConfig[log.type] || typeConfig.status;
          return (
            <div key={i} className="log-entry" style={{ borderLeftColor: cfg.color }}>
              <div className="log-entry-header">
                <span className="log-badge" style={{ background: cfg.color }}>
                  {cfg.icon} {cfg.label}
                </span>
                {log.tool && <span className="log-tool">{log.tool}</span>}
                {log.timestamp && (
                  <span className="log-time">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </div>
              {log.content && <pre className="log-content">{log.content}</pre>}
              {log.input && (
                <details className="log-details">
                  <summary>Input</summary>
                  <pre>{log.input}</pre>
                </details>
              )}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
