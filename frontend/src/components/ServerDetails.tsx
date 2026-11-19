import { Server, Terminal } from 'lucide-react';
import type { Snapshot } from '../types';
import { HealthPanel } from './HealthPanel';

export function ServerDetails({
  snapshot,
  demo,
}: {
  snapshot: Snapshot;
  demo: boolean;
}) {
  const server = snapshot.server;
  return (
    <div className="server-details-grid">
      <section className="panel server-info-panel">
        <div className="panel-heading">
          <h2>Server identity</h2>
          <Terminal size={18} />
        </div>
        <div className="server-identity">
          <span>
            <Server size={30} />
          </span>
          <div>
            <h2>{server.hostname}</h2>
            <p>{server.name}</p>
          </div>
        </div>
        <dl className="server-fields">
          {[
            ['Display name', server.name],
            ['Hostname', server.hostname],
            ['OS type', server.os_type],
            ['Operating system', `${server.os_name} ${server.os_version}`],
            ['Architecture', server.architecture],
            ['Server ID', server.id],
          ].map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        <p className="panel-note">
          {demo
            ? 'Illustrative server identity. These values do not describe your machine.'
            : 'Identity returned by the configured monitored host.'}
        </p>
      </section>
      <HealthPanel
        snapshot={snapshot}
        demo={demo}
        onServer={() => document.getElementById('main')?.focus()}
      />
    </div>
  );
}
