import type {
  Incident,
  IncidentInput,
  IncidentUpdate,
  Snapshot,
} from '../types';

const anchor = new Date('2026-11-16T09:00:00Z').getTime();
const time = (minutesAgo: number) =>
  new Date(anchor - minutesAgo * 60_000).toISOString();

/** Fixed, deterministic fixtures. These are never presented as real host measurements. */
export function createDemoSnapshot(): Snapshot {
  return {
    health: {
      status: 'healthy',
      checked_at: time(0),
      checks: { server: 'up', database: 'up' },
    },
    server: {
      id: '529a234e-b07f-44ee-ae2e-95b272cceced',
      name: 'ServerWatch demo server',
      hostname: 'serverwatch-01',
      os_type: 'Linux',
      os_name: 'Ubuntu',
      os_version: '24.04 LTS',
      architecture: 'x86_64',
    },
    metrics: Array.from({ length: 96 }, (_, index) => {
      const wave = Math.sin(index * 0.45) * 7 + Math.cos(index * 0.17) * 9;
      return {
        id: `sample-${index}`,
        collected_at: time(index * 15),
        cpu_percent:
          Math.round((27.5 + wave + (index > 30 && index < 38 ? 30 : 0)) * 10) /
          10,
        memory_percent:
          Math.round((61.2 + Math.sin(index * 0.12) * 5) * 10) / 10,
        disk_percent: Math.round((43.8 - index * 0.025) * 10) / 10,
        uptime_seconds: 14 * 86400 + 7 * 3600 - index * 900,
      };
    }),
    incidents: [
      incident(
        'd2860789-521f-4747-b072-ba9fd104ba54',
        'Disk usage exceeded warning threshold',
        'Root filesystem crossed the sample warning threshold. Review log retention and available space.',
        'warning',
        'investigating',
        38,
      ),
      incident(
        '9b32a8f5-33fe-4303-bc18-568d9496f811',
        'Elevated CPU utilization',
        'A sample background process caused a short CPU spike. Check running jobs before resolving.',
        'critical',
        'open',
        95,
      ),
      incident(
        'df237089-521f-4747-b072-ba9fd104ba54',
        'Database connection restored',
        'The sample database connection recovered after a scheduled service restart.',
        'info',
        'resolved',
        210,
      ),
    ],
    incidentTotal: 3,
  };
}

function incident(
  id: string,
  title: string,
  description: string,
  severity: Incident['severity'],
  status: Incident['status'],
  minutesAgo: number,
): Incident {
  return {
    id,
    title,
    description,
    severity,
    status,
    occurred_at: time(minutesAgo),
    created_at: time(minutesAgo),
    updated_at: time(minutesAgo),
    resolved_at: status === 'resolved' ? time(minutesAgo - 10) : null,
  };
}

export function createDemoIncident(input: IncidentInput): Incident {
  const now = new Date().toISOString();
  return {
    ...input,
    id: crypto.randomUUID(),
    status: 'open',
    created_at: now,
    updated_at: now,
    resolved_at: null,
  };
}

/** Match the contract's resolution/reopening rules even in the local demo. */
export function updateDemoIncident(
  incident: Incident,
  input: IncidentUpdate,
): Incident {
  const now = new Date().toISOString();
  return {
    ...incident,
    ...input,
    updated_at: now,
    resolved_at:
      input.status === 'resolved' ? (incident.resolved_at ?? now) : null,
  };
}
