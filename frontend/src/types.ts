/** Browser contracts mirror docs/api.md; credentials never belong in this model. */
export type Severity = 'info' | 'warning' | 'critical';
export type IncidentStatus = 'planned' | 'open' | 'investigating' | 'resolved';
export type View = 'overview' | 'metrics' | 'server' | 'incidents';

export type WatchedMetric = 'cpu' | 'gpu' | 'memory' | 'storage';

export interface IncidentTrigger {
  metric: WatchedMetric;
  threshold_percent: number;
  duration_seconds: number;
}

export interface Health {
  server_id: number;
  status: 'healthy' | 'unhealthy';
  checked_at: string;
  message?: string;
  checks: { server: 'up' | 'down'; database: 'up' | 'down' };
}

export interface ServerInfo {
  id: number;
  name: string;
  hostname: string;
  os_type: string;
  os_name: string;
  os_version: string;
  architecture: string;
}

export interface Metric {
  id: string;
  collected_at: string;
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  uptime_seconds: number;
}

export type HistoryMinutes = 30 | 60 | 1440;
export type MetricPoint = Omit<Metric, 'id' | 'uptime_seconds'>;
export interface MetricHistory {
  start: string;
  end: string;
  bucket_seconds: number;
  items: MetricPoint[];
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  status: IncidentStatus;
  occurred_at: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  trigger?: IncidentTrigger | null;
}

export interface IncidentInput {
  title: string;
  description: string;
  severity: Severity;
  occurred_at: string | null;
  trigger?: IncidentTrigger | null;
}

export type IncidentUpdate = Pick<
  Incident,
  'title' | 'description' | 'severity' | 'trigger'
> & { status?: Exclude<IncidentStatus, 'planned'> };

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Snapshot {
  health: Health;
  server: ServerInfo;
  metrics: Metric[];
  // Null means this capability is unavailable, rather than an empty result.
  incidents: Incident[] | null;
  incidentTotal: number | null;
}

export type DemoSnapshot = Snapshot & {
  incidents: Incident[];
  incidentTotal: number;
};
