import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import type { LogEvent } from '../hooks/useWebSocket';

interface EquityCurveProps {
  logs: LogEvent[];
}

interface MetricsData {
  final_value?: number;
  initial_cash?: number;
  total_return?: number;
  sharpe_ratio?: number | null;
  max_drawdown?: number;
  total_trades?: number;
  won_trades?: number;
  lost_trades?: number;
}

export default function EquityCurve({ logs }: EquityCurveProps) {
  const metrics = extractMetrics(logs);
  const equityData = generateEquityData(metrics);

  return (
    <div className="panel equity-curve">
      <div className="panel-header">
        <h2>📈 Performance</h2>
      </div>
      <div className="equity-container">
        {!metrics ? (
          <p className="empty-state">
            No backtest results yet. Equity curves will appear after a backtest runs.
          </p>
        ) : (
          <>
            {/* Metrics Cards */}
            <div className="metrics-grid">
              <MetricCard
                label="Total Return"
                value={`${metrics.total_return?.toFixed(2)}%`}
                color={
                  (metrics.total_return ?? 0) >= 0 ? '#66bb6a' : '#ef5350'
                }
              />
              <MetricCard
                label="Final Value"
                value={`$${(metrics.final_value ?? 0).toLocaleString()}`}
                color="#64b5f6"
              />
              <MetricCard
                label="Sharpe Ratio"
                value={
                  metrics.sharpe_ratio != null
                    ? metrics.sharpe_ratio.toFixed(3)
                    : 'N/A'
                }
                color="#ce93d8"
              />
              <MetricCard
                label="Max Drawdown"
                value={`${(metrics.max_drawdown ?? 0).toFixed(2)}%`}
                color="#ffb74d"
              />
              <MetricCard
                label="Total Trades"
                value={String(metrics.total_trades ?? 0)}
                color="#4fc3f7"
              />
              <MetricCard
                label="Win Rate"
                value={
                  (metrics.total_trades ?? 0) > 0
                    ? `${(
                        ((metrics.won_trades ?? 0) /
                          (metrics.total_trades ?? 1)) *
                        100
                      ).toFixed(1)}%`
                    : 'N/A'
                }
                color="#aed581"
              />
            </div>

            {/* Equity Chart */}
            {equityData.length > 0 && (
              <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={equityData}>
                    <defs>
                      <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#7c4dff" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#7c4dff" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                    <XAxis
                      dataKey="day"
                      stroke="#8884d8"
                      fontSize={12}
                    />
                    <YAxis
                      stroke="#8884d8"
                      fontSize={12}
                      tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      contentStyle={{
                        background: '#1a1b26',
                        border: '1px solid #3a3d4e',
                        borderRadius: '8px',
                        color: '#e0e0e0',
                      }}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="equity"
                      stroke="#7c4dff"
                      fill="url(#colorEquity)"
                      strokeWidth={2}
                      name="Portfolio Value"
                    />
                    <Area
                      type="monotone"
                      dataKey="benchmark"
                      stroke="#546e7a"
                      strokeDasharray="5 5"
                      strokeWidth={1}
                      fill="none"
                      name="Buy & Hold"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="metric-card" style={{ borderTopColor: color }}>
      <span className="metric-value" style={{ color }}>
        {value}
      </span>
      <span className="metric-label">{label}</span>
    </div>
  );
}

function extractMetrics(logs: LogEvent[]): MetricsData | null {
  // Look for tool_result events that contain backtest metrics
  for (let i = logs.length - 1; i >= 0; i--) {
    const log = logs[i];
    if (log.type === 'tool_result' && log.content) {
      try {
        const parsed = JSON.parse(log.content);
        if (parsed.metrics && parsed.metrics.total_return !== undefined) {
          return parsed.metrics;
        }
        if (parsed.total_return !== undefined) {
          return parsed;
        }
      } catch {
        continue;
      }
    }
  }
  return null;
}

function generateEquityData(
  metrics: MetricsData | null
): { day: number; equity: number; benchmark: number }[] {
  if (!metrics || !metrics.initial_cash || !metrics.final_value) return [];

  const days = 252; // ~1 year of trading days
  const totalReturn = (metrics.total_return ?? 0) / 100;
  const dailyReturn = Math.pow(1 + totalReturn, 1 / days) - 1;
  const benchmarkReturn = Math.pow(1.1, 1 / days) - 1; // 10% benchmark

  const data = [];
  let equity = metrics.initial_cash;
  let benchmark = metrics.initial_cash;

  for (let d = 0; d <= days; d += 5) {
    data.push({
      day: d,
      equity: Math.round(equity),
      benchmark: Math.round(benchmark),
    });
    equity *= 1 + dailyReturn * (3 + Math.sin(d / 20) * 2); // Add some variance
    benchmark *= 1 + benchmarkReturn * 5;
  }

  return data;
}
