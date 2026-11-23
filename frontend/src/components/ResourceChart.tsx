import { useEffect, useId, useState, type PointerEvent } from 'react';
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
  const [result, setResult] = useState<{
    range: HistoryMinutes;
    loader: typeof loadHistory;
    history: MetricHistory | null;
    error: string | null;
  } | null>(null);
  const [visible, setVisible] = useState<string[]>(
    series.map((item) => item.key),
  );
  const [selectedTime, setSelectedTime] = useState<number | null>(null);
  const gradientId = useId().replaceAll(':', '');

  useEffect(() => {
    if (!loadHistory) return;
    let active = true;
    let timer: number;
    let history: MetricHistory | null = null;
    setResult({ range, loader: loadHistory, history, error: null });

    async function refresh(fetchHistory: NonNullable<typeof loadHistory>) {
      try {
        history = await fetchHistory(range);
        if (active)
          setResult({ range, loader: fetchHistory, history, error: null });
      } catch (failure) {
        if (active)
          setResult({
            range,
            loader: fetchHistory,
            history,
            error:
              failure instanceof Error && failure.message
                ? failure.message
                : 'Could not load metric history.',
          });
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
  const currentResult =
    result?.range === range && result.loader === loadHistory
      ? result
      : undefined;
  const currentHistory = currentResult?.history;
  const error = currentResult?.error;
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
  // The API omits empty buckets. Start a new path when a bucket is missing.
  const groups: (typeof samples)[] = [];
  for (const sample of samples) {
    const previous = groups.at(-1)?.at(-1);
    if (
      !previous ||
      (currentHistory &&
        Date.parse(sample.collected_at) - Date.parse(previous.collected_at) >
          currentHistory.bucket_seconds * 1000)
    ) {
      groups.push([]);
    }
    groups[groups.length - 1].push(sample);
  }
  const pointX = (sample: (typeof samples)[number]) =>
    x(Date.parse(sample.collected_at));
  const nearestSample = (time: number) =>
    samples.reduce(
      (nearest, sample, index) =>
        Math.abs(Date.parse(sample.collected_at) - time) <
        Math.abs(Date.parse(samples[nearest].collected_at) - time)
          ? index
          : nearest,
      0,
    );
  const selected = selectedTime === null ? null : nearestSample(selectedTime);
  const displayed = samples[selected ?? samples.length - 1];
  const visibleSeries = series.filter((item) => visible.includes(item.key));

  function scrub(event: PointerEvent<SVGSVGElement>) {
    const matrix = event.currentTarget.getScreenCTM();
    if (!matrix) return;
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(
      matrix.inverse(),
    );
    if (point.x < 48 || point.x > 728 || point.y < 30 || point.y > 205) {
      setSelectedTime(null);
      return;
    }
    setSelectedTime(start + ((point.x - 48) / 680) * duration);
  }

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
                setSelectedTime(null);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {loadHistory && error && (
        <p
          role="alert"
          className={currentHistory ? 'form-error' : 'empty-state'}
        >
          {currentHistory
            ? `Could not refresh metric history. ${error}`
            : error}
        </p>
      )}
      {loadHistory && !currentHistory ? (
        !error && (
          <p role="status" className="empty-state">
            Loading metric history…
          </p>
        )
      ) : samples.length ? (
        <>
          <div className="chart-readout">
            <time dateTime={displayed.collected_at}>
              {new Date(displayed.collected_at).toLocaleString([], {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })}
            </time>
            <div>
              {visibleSeries.map((item) => (
                <span key={item.key}>
                  {item.name}{' '}
                  <strong style={{ color: item.color }}>
                    {displayed[item.key].toFixed(1)}%
                  </strong>
                </span>
              ))}
            </div>
          </div>
          <div
            className="chart-wrap"
            tabIndex={0}
            role="group"
            aria-label="Inspect measurements with the left and right arrow keys"
            onBlur={() => setSelectedTime(null)}
            onKeyDown={(event) => {
              if (event.key === 'Escape') {
                setSelectedTime(null);
                return;
              }
              if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight')
                return;
              event.preventDefault();
              const index =
                (selected ?? samples.length - 1) +
                (event.key === 'ArrowLeft' ? -1 : 1);
              const sample =
                samples[Math.max(0, Math.min(samples.length - 1, index))];
              setSelectedTime(Date.parse(sample.collected_at));
            }}
          >
            <svg
              viewBox="0 0 760 245"
              role="img"
              aria-label="CPU, memory, and disk utilization history. Exact values are available in the metrics table."
              onPointerMove={scrub}
              onPointerDown={scrub}
              onPointerLeave={() => setSelectedTime(null)}
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
              {groups.map((group) => (
                <g key={group[0].collected_at}>
                  {visible.includes('cpu_percent') && (
                    <path
                      fill={`url(#${gradientId})`}
                      d={`M${pointX(group[0])},205 ${group.map((sample) => `L${pointX(sample)},${y(sample.cpu_percent)}`).join(' ')} L${pointX(group[group.length - 1])},205 Z`}
                    />
                  )}
                  {visibleSeries.map((item) =>
                    group.length === 1 ? (
                      <circle
                        key={item.key}
                        cx={pointX(group[0])}
                        cy={y(group[0][item.key])}
                        r="2.7"
                        fill={item.color}
                      />
                    ) : (
                      <polyline
                        key={item.key}
                        fill="none"
                        stroke={item.color}
                        strokeWidth="2.2"
                        strokeLinejoin="round"
                        points={group
                          .map(
                            (sample) =>
                              `${pointX(sample)},${y(sample[item.key])}`,
                          )
                          .join(' ')}
                      />
                    ),
                  )}
                </g>
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
              {selected !== null && displayed && (
                <g className="chart-cursor" aria-hidden="true">
                  <line
                    x1={sampleX(selected)}
                    x2={sampleX(selected)}
                    y1="30"
                    y2="205"
                  />
                  {visibleSeries.map((item) => (
                    <circle
                      key={item.key}
                      cx={sampleX(selected)}
                      cy={y(displayed[item.key])}
                      r="4"
                      fill={item.color}
                    />
                  ))}
                </g>
              )}
            </svg>
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
        <div className="empty-state">No measurements in this time window.</div>
      )}
    </section>
  );
}
