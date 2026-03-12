import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { LogEvent } from '../hooks/useWebSocket';

interface CodeViewerProps {
  logs: LogEvent[];
}

export default function CodeViewer({ logs }: CodeViewerProps) {
  // Extract the most recent backtest code from tool_call events
  const codeEvents = logs.filter(
    (l) =>
      l.type === 'tool_call' &&
      l.tool === 'write_and_execute_backtest' &&
      l.input
  );

  const latestCode = codeEvents.length > 0 ? extractCode(codeEvents[codeEvents.length - 1].input || '') : null;

  // Also extract the result if available
  const resultEvents = logs.filter(
    (l) => l.type === 'tool_result' && l.content?.includes('total_return')
  );
  const latestResult = resultEvents.length > 0 ? resultEvents[resultEvents.length - 1].content : null;

  return (
    <div className="panel code-viewer">
      <div className="panel-header">
        <h2>💻 Generated Code</h2>
        {codeEvents.length > 0 && (
          <span className="iteration-badge">
            Iteration {codeEvents.length}
          </span>
        )}
      </div>
      <div className="code-container">
        {!latestCode ? (
          <p className="empty-state">
            No backtest code generated yet. The agent will write strategies here.
          </p>
        ) : (
          <>
            <SyntaxHighlighter
              language="python"
              style={oneDark}
              showLineNumbers
              customStyle={{
                margin: 0,
                borderRadius: '8px',
                fontSize: '13px',
                background: '#1a1b26',
              }}
            >
              {latestCode}
            </SyntaxHighlighter>
            {latestResult && (
              <div className="code-result">
                <h3>📊 Backtest Result</h3>
                <pre>{formatJson(latestResult)}</pre>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function extractCode(input: string): string {
  try {
    // Try to parse as JSON and extract the 'code' field
    const parsed = JSON.parse(input);
    if (parsed.code) return parsed.code;
  } catch {
    // If not JSON, try to find Python code patterns
    const match = input.match(/(?:import backtrader|class Generated|def run_backtest)[\s\S]*/);
    if (match) return match[0];
  }
  return input;
}

function formatJson(raw: string): string {
  try {
    const obj = JSON.parse(raw);
    return JSON.stringify(obj, null, 2);
  } catch {
    return raw;
  }
}
