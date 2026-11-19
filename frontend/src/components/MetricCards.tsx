import {
  ArrowDownLeft,
  ArrowUpRight,
  CircleAlert,
  Cpu,
  HardDrive,
  MemoryStick,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { Snapshot } from '../types';

export function MetricCards({
  snapshot,
  openCount,
}: {
  snapshot: Snapshot;
  openCount: number;
}) {
  const current = snapshot.metrics[0];
  const previous = snapshot.metrics[1];
  const cards: {
    label: string;
    value: number | undefined;
    previous?: number;
    icon: LucideIcon;
    color: string;
  }[] = [
    {
      label: 'CPU usage',
      value: current?.cpu_percent,
      previous: previous?.cpu_percent,
      icon: Cpu,
      color: 'green',
    },
    {
      label: 'Memory usage',
      value: current?.memory_percent,
      previous: previous?.memory_percent,
      icon: MemoryStick,
      color: 'purple',
    },
    {
      label: 'Disk usage',
      value: current?.disk_percent,
      previous: previous?.disk_percent,
      icon: HardDrive,
      color: 'amber',
    },
  ];
  return (
    <div className="metric-grid">
      {cards.map(({ label, value, previous: before, icon: Icon, color }) => {
        const change =
          value === undefined || before === undefined ? null : value - before;
        return (
          <section className="metric-card" key={label}>
            <div className="metric-card-top">
              <span>{label}</span>
              <Icon size={18} />
            </div>
            <div className="metric-value">
              {value?.toFixed(1) ?? '—'}
              <span>{value === undefined ? '' : '%'}</span>
            </div>
            <div className="metric-progress">
              <span
                className={color}
                style={{ width: `${Math.min(100, Math.max(0, value ?? 0))}%` }}
              />
            </div>
            <div className="metric-caption">
              {change === null ? (
                'Waiting for measurements'
              ) : (
                <>
                  <span className={`change ${change <= 0 ? 'down' : 'up'}`}>
                    {change <= 0 ? (
                      <ArrowDownLeft size={13} />
                    ) : (
                      <ArrowUpRight size={13} />
                    )}
                    {Math.abs(change).toFixed(1)} pp
                  </span>
                  <span>vs. previous sample</span>
                </>
              )}
            </div>
          </section>
        );
      })}
      <section className="metric-card incident-card">
        <div className="metric-card-top">
          <span>
            {snapshot.incidents &&
            snapshot.incidentTotal !== null &&
            snapshot.incidents.length < snapshot.incidentTotal
              ? 'Open incidents (loaded)'
              : 'Open incidents'}
          </span>
          <CircleAlert size={18} />
        </div>
        <div className="metric-value">
          {snapshot.incidents === null
            ? '—'
            : openCount.toString().padStart(2, '0')}
          <span className="incident-value-label">
            {snapshot.incidents === null
              ? 'unavailable'
              : openCount === 1
                ? 'incident'
                : 'incidents'}
          </span>
        </div>
        {snapshot.incidents !== null && (
          <div className="incident-mini-status">
            {snapshot.incidents.some(
              (item) =>
                item.status !== 'resolved' && item.severity === 'critical',
            ) && (
              <span>
                <i className="critical-dot" />
                Critical
              </span>
            )}
            <span>
              <i className="warning-dot" />
              {
                snapshot.incidents.filter(
                  (item) => item.status === 'investigating',
                ).length
              }{' '}
              investigating
            </span>
          </div>
        )}
        <div className="metric-caption">
          {snapshot.incidents === null
            ? 'Incident monitoring is not available yet'
            : openCount
              ? 'Some issues need your attention'
              : 'No open issues in loaded records'}
        </div>
      </section>
    </div>
  );
}
