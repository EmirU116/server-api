import { useId, useState } from 'react';
import type { Metric } from '../types';

const series = [
  { key: 'cpu_percent', name: 'CPU', color: '#b7e98b' },
  { key: 'memory_percent', name: 'Memory', color: '#9fa6f5' },
  { key: 'disk_percent', name: 'Disk', color: '#e9ba7d' },
] as const;

export function ResourceChart({ metrics }: { metrics: Metric[] }) {
  const [range, setRange] = useState(24);
  const [visible, setVisible] = useState<string[]>(
    series.map((item) => item.key),
  );
  const [hover, setHover] = useState<number | null>(null);
  const gradientId = useId().replaceAll(':', '');
  const latest = metrics[0] ? new Date(metrics[0].collected_at).getTime() : 0;
  // Relative to the newest sample so demo and historical data use honest labels.
  const samples = metrics
    .filter(
      (item) =>
        new Date(item.collected_at).getTime() >= latest - range * 3600_000,
    )
    .slice()
    .reverse();
  const x = (index: number) =>
    48 + (index / Math.max(samples.length - 1, 1)) * 680;
  const y = (value: number) => 205 - value * 1.7;
  const focused = hover === null ? null : samples[hover];

  return (
    <section className="panel chart-panel" aria-labelledby="resource-title">
      <div className="panel-heading">
        <div>
          <h2 id="resource-title">Resource utilization</h2>
          <p>Percent used · ending at latest sample</p>
        </div>
        <div className="segmented" aria-label="Chart time range">
          {[1, 6, 24].map((hours) => (
            <button
              key={hours}
              aria-pressed={range === hours}
              onClick={() => {
                setRange(hours);
                setHover(null);
              }}
            >
              {hours}h
            </button>
          ))}
        </div>
      </div>
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
                  d={`M48,205 ${samples.map((item, index) => `L${x(index)},${y(item.cpu_percent)}`).join(' ')} L${x(samples.length - 1)},205 Z`}
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
                        (sample, index) => `${x(index)},${y(sample[item.key])}`,
                      )
                      .join(' ')}
                  />
                ))}
              {samples
                .filter(
                  (_, index) =>
                    index === 0 ||
                    index === Math.floor((samples.length - 1) / 2) ||
                    index === samples.length - 1,
                )
                .map((item) => {
                  const index = samples.indexOf(item);
                  return (
                    <text
                      key={item.id}
                      x={x(index)}
                      y="232"
                      textAnchor={
                        index === 0
                          ? 'start'
                          : index === samples.length - 1
                            ? 'end'
                            : 'middle'
                      }
                      className="chart-label"
                    >
                      {new Date(item.collected_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </text>
                  );
                })}
              {hover !== null && (
                <line
                  x1={x(hover)}
                  x2={x(hover)}
                  y1="30"
                  y2="205"
                  stroke="#777e76"
                  strokeDasharray="4 4"
                />
              )}
              {samples.map((item, index) => (
                <rect
                  key={item.id}
                  x={x(index) - 680 / Math.max(samples.length, 1) / 2}
                  y="30"
                  width={680 / Math.max(samples.length - 1, 1)}
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
            <span className="sample-count">{samples.length} samples</span>
          </div>
        </>
      ) : (
        <div className="empty-state">
          No measurements yet. Collected samples will appear here.
        </div>
      )}
    </section>
  );
}
