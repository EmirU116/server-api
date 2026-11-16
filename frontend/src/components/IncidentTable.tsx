import { useState } from 'react';
import { ArrowUpRight, CircleCheck, Search } from 'lucide-react';
import type { Incident, IncidentStatus } from '../types';

export function StatusBadge({ status }: { status: IncidentStatus }) {
  return (
    <span className={`badge status-${status}`}>
      <span className="status-dot" />
      {status === 'investigating'
        ? 'Investigating'
        : status === 'resolved'
          ? 'Resolved'
          : 'Open'}
    </span>
  );
}

export function IncidentTable({
  incidents,
  total,
  full = false,
  onEdit,
  onViewAll,
}: {
  incidents: Incident[];
  total: number;
  full?: boolean;
  onEdit: (incident: Incident) => void;
  onViewAll: () => void;
}) {
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const visible = incidents.filter(
    (incident) =>
      (filter === 'all' || incident.status === filter) &&
      `${incident.title} ${incident.description}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const rows = full ? visible : visible.slice(0, 3);

  return (
    <section
      className="panel incidents-panel"
      aria-labelledby="incidents-heading"
    >
      <div className="panel-heading">
        <div className="inline-heading">
          <h2 id="incidents-heading">
            {full ? 'Incident log' : 'Recent incidents'}
          </h2>
          <span className="count-badge">{total}</span>
        </div>
        {!full && (
          <button className="text-button" onClick={onViewAll}>
            View all incidents <ArrowUpRight size={15} />
          </button>
        )}
      </div>
      {full && (
        <div className="table-toolbar">
          <div className="status-filters" aria-label="Incident status filter">
            {['all', 'open', 'investigating', 'resolved'].map((status) => (
              <button
                key={status}
                aria-pressed={filter === status}
                onClick={() => setFilter(status)}
              >
                {status === 'all'
                  ? 'All incidents'
                  : status[0].toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
          <label className="search-field">
            <Search size={16} />
            <span className="sr-only">Search incidents</span>
            <input
              placeholder="Search incidents…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
        </div>
      )}
      {rows.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Incident</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Occurred</th>
                <th>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((incident) => (
                <tr key={incident.id}>
                  <td>
                    <button
                      className="incident-title"
                      onClick={() => onEdit(incident)}
                    >
                      {incident.title}
                    </button>
                    <span className="incident-description">
                      {incident.description}
                    </span>
                  </td>
                  <td>
                    <span className={`severity severity-${incident.severity}`}>
                      <span />
                      {incident.severity}
                    </span>
                  </td>
                  <td>
                    <StatusBadge status={incident.status} />
                  </td>
                  <td className="date-cell">
                    {new Date(incident.occurred_at).toLocaleDateString([], {
                      month: 'short',
                      day: 'numeric',
                    })}
                    <span>
                      {new Date(incident.occurred_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </td>
                  <td>
                    <button
                      className="icon-button"
                      aria-label={`Manage ${incident.title}`}
                      onClick={() => onEdit(incident)}
                    >
                      <ArrowUpRight size={17} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <CircleCheck size={28} />
          <h3>
            {query || filter !== 'all'
              ? 'No matching incidents'
              : 'No incidents recorded'}
          </h3>
          <p>
            {query || filter !== 'all'
              ? 'Try another search or status filter.'
              : 'New reports will appear here when an incident is created.'}
          </p>
        </div>
      )}
      {full && (
        <div className="table-footnote">
          {incidents.length < total
            ? `Search and filters apply to the latest ${incidents.length} of ${total} incidents.`
            : `${visible.length} matching incident${visible.length === 1 ? '' : 's'}`}
        </div>
      )}
    </section>
  );
}
