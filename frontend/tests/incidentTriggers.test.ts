import { expect, it } from 'vitest';
import { evaluateTrigger } from '../src/services/incidentTriggers';
import type { IncidentTrigger, Metric } from '../src/types';

const now = Date.parse('2026-11-20T12:00:00Z');
const rule: IncidentTrigger = {
  metric: 'disk',
  threshold_percent: 90,
  duration_seconds: 10,
};

function sample(secondsAgo: number, disk = 90): Metric {
  return {
    id: String(secondsAgo),
    collected_at: new Date(now - secondsAgo * 1000).toISOString(),
    cpu_percent: 95,
    memory_percent: 40,
    disk_percent: disk,
    uptime_seconds: 200,
  };
}

it('uses the selected metric and measures the contiguous window in time order', () => {
  const readings = [sample(10), sample(0), sample(5)];
  expect(evaluateTrigger(rule, readings, false, now).label).toBe(
    'Threshold met',
  );
  expect(
    evaluateTrigger({ ...rule, metric: 'cpu' }, readings, false, now).latest,
  ).toBe(95);
  expect(
    evaluateTrigger({ ...rule, metric: 'memory' }, readings, false, now).label,
  ).toBe('Below threshold');
});

it('does not confirm a crossing through a gap, a drop, or stale data', () => {
  expect(
    evaluateTrigger(rule, [sample(0), sample(16)], false, now).seconds,
  ).toBe(0);
  expect(
    evaluateTrigger(rule, [sample(0), sample(5, 89), sample(10)], false, now)
      .seconds,
  ).toBe(0);
  expect(
    evaluateTrigger(rule, [sample(20), sample(25), sample(30)], false, now)
      .label,
  ).toBe('Reading is stale');
});
