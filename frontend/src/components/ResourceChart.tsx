import { useEffect, useId, useState } from 'react';
import type { HistoryMinutes, Metric, MetricHistory } from '../types';

const series = [
  { key: 'cpu_percent', name: 'CPU', color: '#b7e98b' },
  { key: 'memory_percent', name: 'Memory', color: '#9fa6f5' },
  { key: 'disk_percent', name: 'Disk', color: '#e9ba7d' },
] as const;

const ranges = [
  { minutes: 30, label: '30 min' },
  { minutes: 60, label: '1 h' },
  { minutes: 1440, label: '24 h' },
] as const;

export function ResourceChart({
  metrics,
  loadHistory,
}: {
  metrics: Metric[];
  loadHistory?: (minutes: HistoryMinutes) => Promise<MetricHistory>;
}) {
  const [range, setRange] = useState<HistoryMinutes>(30);
  const [history, setHistory] = useState<MetricHistory | null>(null);
  const [error, setError] = useState('');
  const [visible, setVisible] = useState<string[]>(
    series.map((item) => item.key),
  );
  const [hover, setHover] = useState<number | null>(null);
  const gradientId = useId().replaceAll(':', '');

  useEffect(() => {
    if (!loadHistory) return;
    let active = true;
    let timer: number;
    async function refresh(fetchHistory: NonNullable<typeof loadHistory>) {
      try {
        const next = await fetchHistory(range);
        if (active) {
          setHistory(next);
          setError('');
        }
      } catch (failure) {
        if (active)
          setError(
            failure instanceof Error
              ? failure.message
              : 'Could not load metric history.',
          );
      } finally {
        if (active)
          timer = window.setTimeout(() => void refresh(fetchHistory), 30_000);
      }
    }
    void refresh(loadHistory);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [loadHistory, range]);

  const duration = range * 60_000;
  const currentHistory =
    history && Date.parse(history.end) - Date.parse(history.start) === duration
      ? history
      : null;
  const end = loadHistory
    ? currentHistory
      ? Date.parse(currentHistory.end)
      : Date.now()
    : metrics[0]
      ? Date.parse(metrics[0].collected_at)
      : Date.now();
  const start = end - duration;
  const samples = loadHistory
    ? (currentHistory?.items ?? [])
    : metrics
        .filter((item) => Date.parse(item.collected_at) >= start)
        .reverse();
  const x = (time: number) => 48 + ((time - start) / duration) * 680;
  const sampleX = (index: number) => x(Date.parse(samples[index].collected_at));
  const y = (value: number) => 205 - value * 1.7;
  const focused = hover === null ? null : samples[hover];

  return (
    <section className="panel chart-panel" aria-labelledby="resource-title">
      <div className="panel-heading">
        <div>
          <h2 id="resource-title">Resource utilization</h2>
          <p>
            {loadHistory
              ? 'Average percent used'
              : 'Percent used · demo history'}
          </p>
        </div>
        <div className="segmented" aria-label="Chart time range">
          {ranges.map(({ minutes, label }) => (
            <button
              key={minutes}
              aria-pressed={range === minutes}
              onClick={() => {
                setRange(minutes);
                setError('');
                setHover(null);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {error && (
        <p role="status" className="field-hint">
          {error}
        </p>
      )}
      {samples.length ? (
        <>
          <div className="chart-wrap">
            <svg
              viewBox="0 0 760 245"
              role="img"
              aria-label="CPU, memory, and disk utilization history. Exact values are available in the metrics table."
              onMouseLeave={() => setHover(null)}
            >
              <defs>
                <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#b7e98b" stopOpacity=".12" />
                  <stop offset="100%" stopColor="#b7e98b" stopOpacity="0" />
                </linearGradient>
              </defs>
              {[0, 25, 50, 75, 100].map((value) => (
                <g key={value}>
                  <line
                    x1="48"
                    x2="728"
                    y1={y(value)}
                    y2={y(value)}
                    className="chart-grid"
                  />
                  <text
                    x="30"
                    y={y(value) + 4}
                    textAnchor="end"
                    className="chart-label"
                  >
                    {value}%
                  </text>
                </g>
              ))}
              {visible.includes('cpu_percent') && (
                <path
                  fill={`url(#${gradientId})`}
                  d={`M${sampleX(0)},205 ${samples.map((item, index) => `L${sampleX(index)},${y(item.cpu_percent)}`).join(' ')} L${sampleX(samples.length - 1)},205 Z`}
                />
              )}
              {series
                .filter((item) => visible.includes(item.key))
                .map((item) => (
                  <polyline
                    key={item.key}
                    fill="none"
                    stroke={item.color}
                    strokeWidth="2.2"
                    strokeLinejoin="round"
                    points={samples
                      .map(
                        (sample, index) =>
                          `${sampleX(index)},${y(sample[item.key])}`,
                      )
                      .join(' ')}
                  />
                ))}
              {[start, start + duration / 2, end].map((time) => (
                <text
                  key={time}
                  x={x(time)}
                  y="232"
                  textAnchor={
                    time === start ? 'start' : time === end ? 'end' : 'middle'
                  }
                  className="chart-label"
                >
                  {new Date(time).toLocaleTimeString([], {
                    ...(range === 1440
                      ? { month: 'short', day: 'numeric' }
                      : {}),
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </text>
              ))}
              {hover !== null && focused && (
                <line
                  x1={sampleX(hover)}
                  x2={sampleX(hover)}
                  y1="30"
                  y2="205"
                  stroke="#777e76"
                  strokeDasharray="4 4"
                />
              )}
              {samples.map((item, index) => (
                <rect
                  key={item.collected_at}
                  x={sampleX(index) - 3}
                  y="30"
                  width="6"
                  height="175"
                  fill="transparent"
                  onMouseEnter={() => setHover(index)}
                />
              ))}
            </svg>
            {focused && (
              <div className="chart-tooltip">
                {new Date(focused.collected_at).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
                <strong>
                  CPU {focused.cpu_percent.toFixed(1)}% · Memory{' '}
                  {focused.memory_percent.toFixed(1)}% · Disk{' '}
                  {focused.disk_percent.toFixed(1)}%
                </strong>
              </div>
            )}
          </div>
          <div className="chart-legend">
            {series.map((item) => (
              <button
                key={item.key}
                aria-pressed={visible.includes(item.key)}
                onClick={() =>
                  setVisible((current) =>
                    current.includes(item.key)
                      ? current.filter((key) => key !== item.key)
                      : [...current, item.key],
                  )
                }
              >
                <span
                  style={{
                    background: item.color,
                    opacity: visible.includes(item.key) ? 1 : 0.25,
                  }}
                />
                {item.name}
              </button>
            ))}
            <span className="sample-count">
              {samples.length} {loadHistory ? 'bucket' : 'sample'}
              {samples.length !== 1 && 's'}
            </span>
          </div>
        </>
      ) : (
        <div className="empty-state">
          {loadHistory && !currentHistory && !error
            ? 'Loading metric history…'
            : 'No measurements in this time window.'}
        </div>
      )}
    </section>
  );
}
