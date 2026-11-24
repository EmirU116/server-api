import type { IncidentTrigger, Metric, WatchedMetric } from '../types';

export const metricNames: Record<WatchedMetric, string> = {
  cpu: 'CPU',
  memory: 'Memory',
  disk: 'Disk',
};

const sampleFields = {
  cpu: 'cpu_percent',
  memory: 'memory_percent',
  disk: 'disk_percent',
} as const;

/** Evaluate the most recent uninterrupted run of readings above the limit. */
export function evaluateTrigger(
  trigger: IncidentTrigger,
  samples: Metric[],
  demo = false,
  now = Date.now(),
) {
  const { metric, threshold_percent, duration_seconds } = trigger;
  const field = sampleFields[metric];
  const sorted = [...samples].sort(
    (a, b) => Date.parse(b.collected_at) - Date.parse(a.collected_at),
  );
  const newest = sorted[0];
  if (!newest) return { label: 'No readings yet', latest: null, seconds: 0 };
  const latest = newest[field];
  const newestTime = Date.parse(newest.collected_at);
  if (!demo && now - newestTime > 15_000)
    return { label: 'Reading is stale', latest, seconds: 0 };
  if (latest < threshold_percent)
    return { label: 'Below threshold', latest, seconds: 0 };

  // Live sampling runs every five seconds. Demo samples are 15 minutes apart.
  const maxGap = demo ? 15 * 60_000 : 15_000;
  let through = newestTime;
  for (const sample of sorted.slice(1)) {
    const time = Date.parse(sample.collected_at);
    if (through - time > maxGap || sample[field] < threshold_percent) break;
    through = time;
  }
  const seconds = Math.floor((newestTime - through) / 1000);
  return {
    label:
      seconds >= duration_seconds
        ? 'Threshold met'
        : 'Waiting for sustained readings',
    latest,
    seconds,
  };
}
