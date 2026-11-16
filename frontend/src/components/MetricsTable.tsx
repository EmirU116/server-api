import { useState } from 'react';
import type { Snapshot } from '../types';

export function MetricsTable({ metrics }: { metrics: Snapshot['metrics'] }) {
  const [page, setPage] = useState(0);
  const pageSize = 10;
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Measurement history</h2>
          <p>Newest first · up to 100 recent API samples</p>
        </div>
        <span className="small-label">{metrics.length} SAMPLES</span>
      </div>
      {metrics.length ? (
        <>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Collected at (local time)</th>
                  <th>CPU</th>
                  <th>Memory</th>
                  <th>Disk</th>
                  <th>Uptime</th>
                </tr>
              </thead>
              <tbody>
                {metrics
                  .slice(page * pageSize, (page + 1) * pageSize)
                  .map((item) => (
                    <tr key={item.id}>
                      <td className="mono">
                        {new Date(item.collected_at).toLocaleString()}
                      </td>
                      <td>{item.cpu_percent.toFixed(1)}%</td>
                      <td>{item.memory_percent.toFixed(1)}%</td>
                      <td>{item.disk_percent.toFixed(1)}%</td>
                      <td>{Math.floor(item.uptime_seconds / 3600)}h</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <span>
              Showing {page * pageSize + 1}–
              {Math.min((page + 1) * pageSize, metrics.length)} of{' '}
              {metrics.length}
            </span>
            <div>
              <button
                className="button secondary"
                disabled={page === 0}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </button>
              <button
                className="button secondary"
                disabled={(page + 1) * pageSize >= metrics.length}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </>
      ) : (
        <div className="empty-state">No measurements recorded yet.</div>
      )}
    </section>
  );
}
