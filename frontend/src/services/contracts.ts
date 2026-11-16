import type { Health, Incident, Metric, Page, ServerInfo } from '../types';

const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);
const timestamp = (value: unknown): value is string =>
  typeof value === 'string' && Number.isFinite(Date.parse(value));

/** TypeScript cannot validate network JSON. Check it before rendering values. */
export function isHealth(value: unknown): value is Health {
  return (
    record(value) &&
    ['healthy', 'unhealthy'].includes(String(value.status)) &&
    timestamp(value.checked_at) &&
    record(value.checks) &&
    ['up', 'down'].includes(String(value.checks.server)) &&
    ['up', 'down'].includes(String(value.checks.database))
  );
}

export function isServer(value: unknown): value is ServerInfo {
  return (
    record(value) &&
    [
      'id',
      'name',
      'hostname',
      'os_type',
      'os_name',
      'os_version',
      'architecture',
    ].every((key) => typeof value[key] === 'string')
  );
}

export function isMetric(value: unknown): value is Metric {
  return (
    record(value) &&
    typeof value.id === 'string' &&
    timestamp(value.collected_at) &&
    ['cpu_percent', 'memory_percent', 'disk_percent'].every(
      (key) =>
        typeof value[key] === 'number' &&
        Number.isFinite(value[key]) &&
        value[key] >= 0 &&
        value[key] <= 100,
    ) &&
    typeof value.uptime_seconds === 'number' &&
    Number.isInteger(value.uptime_seconds) &&
    value.uptime_seconds >= 0
  );
}

export function isIncident(value: unknown): value is Incident {
  return (
    record(value) &&
    ['id', 'title', 'description'].every(
      (key) => typeof value[key] === 'string',
    ) &&
    ['info', 'warning', 'critical'].includes(String(value.severity)) &&
    ['open', 'investigating', 'resolved'].includes(String(value.status)) &&
    ['occurred_at', 'created_at', 'updated_at'].every((key) =>
      timestamp(value[key]),
    ) &&
    (value.resolved_at === null || timestamp(value.resolved_at))
  );
}

export function isPage<T>(
  value: unknown,
  itemGuard: (item: unknown) => item is T,
): value is Page<T> {
  return (
    record(value) &&
    Array.isArray(value.items) &&
    value.items.every(itemGuard) &&
    typeof value.total === 'number' &&
    Number.isInteger(value.total) &&
    value.total >= value.items.length &&
    typeof value.limit === 'number' &&
    Number.isInteger(value.limit) &&
    value.limit >= 1 &&
    value.limit <= 100 &&
    typeof value.offset === 'number' &&
    Number.isInteger(value.offset) &&
    value.offset >= 0
  );
}
