/** Browser contracts mirror docs/api.md; credentials never belong in this model. */
export type Severity = 'info' | 'warning' | 'critical';
export type IncidentStatus = 'open' | 'investigating' | 'resolved';
export type View = 'overview' | 'metrics' | 'server' | 'incidents';

export interface Health {
  status: 'healthy' | 'unhealthy';
  checked_at: string;
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

export interface Incident {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  status: IncidentStatus;
  occurred_at: string;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface IncidentInput {
  title: string;
  description: string;
  severity: Severity;
  occurred_at: string;
}

export type IncidentUpdate = Pick<
  Incident,
  'title' | 'description' | 'severity' | 'status'
>;

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
  incidents: Incident[];
  incidentTotal: number;
}
