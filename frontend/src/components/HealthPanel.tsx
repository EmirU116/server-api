import {
  ArrowUpRight,
  CircleAlert,
  Database,
  Server,
  ShieldCheck,
} from 'lucide-react';
import type { Snapshot } from '../types';

export function HealthPanel({
  snapshot,
  demo,
  onServer,
}: {
  snapshot: Snapshot;
  demo: boolean;
  onServer: () => void;
}) {
  const healthy = snapshot.health.status === 'healthy';
  const uptime = snapshot.metrics[0]?.uptime_seconds;
  return (
    <section className="panel health-panel">
      <div className="panel-heading">
        <h2>Server health</h2>
        <span className="small-label">{demo ? 'SAMPLE' : 'LATEST CHECK'}</span>
      </div>
      <div className={`health-symbol ${healthy ? '' : 'unhealthy'}`}>
        {healthy ? <ShieldCheck size={28} /> : <CircleAlert size={28} />}
      </div>
      <h3>
        {healthy ? 'All systems operational' : 'A system needs attention'}
      </h3>
      <p>
        {snapshot.health.message ??
          (demo
            ? 'Example readiness check'
            : 'Reported by the health endpoint')}
      </p>
      {!demo && (
        <p>
          {snapshot.metrics[0] ? (
            <>
              Latest measurement:{' '}
              <time dateTime={snapshot.metrics[0].collected_at}>
                {new Date(snapshot.metrics[0].collected_at).toLocaleString()}
              </time>
            </>
          ) : (
            'No measurements received yet.'
          )}
        </p>
      )}
      <div className="health-checks">
        <div>
          <span>
            <Server size={14} />
            Server
          </span>
          <span
            className={
              snapshot.health.checks.server === 'up' ? 'check-up' : 'check-down'
            }
          >
            <span />
            {snapshot.health.checks.server === 'up'
              ? 'Operational'
              : 'Unavailable'}
          </span>
        </div>
        <div>
          <span>
            <Database size={14} />
            Database
          </span>
          <span
            className={
              snapshot.health.checks.database === 'up'
                ? 'check-up'
                : 'check-down'
            }
          >
            <span />
            {snapshot.health.checks.database === 'up'
              ? 'Connected'
              : 'Unavailable'}
          </span>
        </div>
      </div>
      <div className="health-foot">
        <span>
          {demo ? 'Sample uptime' : 'Reported uptime'}
          <strong>
            {uptime === undefined
              ? 'Not available'
              : `${Math.floor(uptime / 86400)}d ${Math.floor((uptime % 86400) / 3600)}h`}
          </strong>
        </span>
        <button
          className="icon-button"
          aria-label="View server details"
          onClick={onServer}
        >
          <ArrowUpRight size={17} />
        </button>
      </div>
    </section>
  );
}
