import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  ArrowUpRight,
  Cable,
  Check,
  ChevronRight,
  CircleAlert,
  LayoutDashboard,
  Plus,
  RefreshCw,
  Server,
  Unplug,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { HealthPanel } from './components/HealthPanel';
import { MetricCards } from './components/MetricCards';
import { MetricsTable } from './components/MetricsTable';
import { ServerDetails } from './components/ServerDetails';
import { ResourceChart } from './components/ResourceChart';
import { IncidentEditor } from './components/IncidentEditor';
import { IncidentTable } from './components/IncidentTable';
import { Modal } from './components/Modal';
import { createApi } from './services/api';
import {
  createDemoIncident,
  createDemoSnapshot,
  updateDemoIncident,
} from './services/demo';
import type {
  Incident,
  IncidentInput,
  IncidentUpdate,
  Snapshot,
  View,
} from './types';

const navigation: { key: View; label: string; icon: LucideIcon }[] = [
  { key: 'overview', label: 'Overview', icon: LayoutDashboard },
  { key: 'metrics', label: 'Metrics', icon: Activity },
  { key: 'server', label: 'Server details', icon: Server },
  { key: 'incidents', label: 'Incidents', icon: CircleAlert },
];

export default function App() {
  const [view, setView] = useState<View>('overview');
  const [mode, setMode] = useState<'demo' | 'api'>('demo');
  const [snapshot, setSnapshot] = useState<Snapshot | null>(createDemoSnapshot);
  const [token, setToken] = useState('');
  const [tokenInput, setTokenInput] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editing, setEditing] = useState<Incident | null | undefined>(
    undefined,
  );
  const generation = useRef(0);
  const api = useMemo(() => createApi(token), [token]);
  const openCount =
    snapshot?.incidents.filter((item) => item.status !== 'resolved').length ??
    0;
  const title =
    view === 'overview'
      ? 'Server overview'
      : view === 'metrics'
        ? 'Resource metrics'
        : view === 'server'
          ? 'Server details'
          : 'Incident management';
  const subtitle =
    view === 'overview'
      ? 'A clear picture of your server. All in one place.'
      : view === 'metrics'
        ? 'Understand how your server resources are being used.'
        : view === 'server'
          ? 'The identity and environment of your monitored server.'
          : 'Track issues, investigate causes, and keep a record of resolutions.';

  useEffect(() => {
    document.title = `ServerWatch · ${title}`;
  }, [title]);

  async function loadApi(bearer: string) {
    const current = ++generation.current;
    setMode('api');
    setToken(bearer);
    setSnapshot(null);
    setError('');
    setNotice('');
    setLoading(true);
    try {
      const data = await createApi(bearer).snapshot();
      if (generation.current === current) setSnapshot(data);
    } catch (failure) {
      if (generation.current === current)
        setError(
          failure instanceof Error
            ? failure.message
            : 'Unable to load server data.',
        );
    } finally {
      if (generation.current === current) setLoading(false);
    }
  }

  function useDemo() {
    generation.current += 1;
    setMode('demo');
    setToken('');
    setTokenInput('');
    setSnapshot(createDemoSnapshot());
    setLoading(false);
    setError('');
    setNotice('');
  }

  async function saveIncident(
    input: IncidentInput | IncidentUpdate,
    id?: string,
  ) {
    if (!snapshot) return;
    const record =
      mode === 'demo'
        ? id
          ? updateDemoIncident(
              snapshot.incidents.find((item) => item.id === id)!,
              input as IncidentUpdate,
            )
          : createDemoIncident(input as IncidentInput)
        : id
          ? await api.updateIncident(id, input as IncidentUpdate)
          : await api.createIncident(input as IncidentInput);
    setSnapshot(
      (current) =>
        current && {
          ...current,
          incidents: id
            ? current.incidents.map((item) => (item.id === id ? record : item))
            : [record, ...current.incidents],
          incidentTotal: current.incidentTotal + (id ? 0 : 1),
        },
    );
    setNotice(
      `${mode === 'demo' ? 'Demo incident' : 'Incident'} ${id ? 'updated' : 'created'} successfully.`,
    );
  }

  async function deleteIncident(id: string) {
    if (mode === 'api') await api.deleteIncident(id);
    setSnapshot(
      (current) =>
        current && {
          ...current,
          incidents: current.incidents.filter((item) => item.id !== id),
          incidentTotal: current.incidentTotal - 1,
        },
    );
    setNotice(`${mode === 'demo' ? 'Demo incident' : 'Incident'} deleted.`);
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="sidebar" aria-label="Main navigation">
        <a className="brand" href="#main" onClick={() => setView('overview')}>
          <span className="brand-mark">
            <Activity size={23} strokeWidth={2.4} />
          </span>
          serverwatch
          <span className="brand-period" aria-hidden="true">
            .
          </span>
        </a>
        <div className="workspace">
          <span className="workspace-icon">
            <Server size={17} />
          </span>
          <div>
            <strong>Server workspace</strong>
            <span>Single-server monitoring</span>
          </div>
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {navigation.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              className={`nav-item ${view === key ? 'active' : ''}`}
              aria-current={view === key ? 'page' : undefined}
              onClick={() => setView(key)}
            >
              <Icon size={18} />
              <span>{label}</span>
              {key === 'incidents' && openCount > 0 && (
                <span className="nav-count">{openCount}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection-card">
            <span className={`connection-indicator ${mode}`} />
            <strong>
              {mode === 'demo' ? 'Demo workspace' : 'API workspace'}
            </strong>
            <p>
              {mode === 'demo'
                ? 'Explore with sample data.'
                : 'Connected data source selected.'}
            </p>
            <button onClick={() => setConnecting(true)}>
              <Cable size={14} />
              {mode === 'demo' ? 'Connect your API' : 'Connection settings'}
              <ArrowUpRight size={13} />
            </button>
          </div>
          <div className="sidebar-footer">
            <span className="avatar">SW</span>
            <div>
              <strong>ServerWatch</strong>
              <span>Monitoring & incidents</span>
            </div>
            <span className="version">v0.1</span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <Server size={15} />
            <span>Workspace</span>
            <ChevronRight size={13} />
            <strong>
              {navigation.find((item) => item.key === view)?.label}
            </strong>
          </div>
          <div className="topbar-actions">
            <span className={`source-badge ${mode}`}>
              <span />
              {mode === 'demo' ? 'Demo data' : 'API data'}
            </span>
            <span className="topbar-divider" />
            <span className="topbar-avatar">SW</span>
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          <div className="page-heading">
            <div>
              <div className="eyebrow">YOUR INFRASTRUCTURE, IN FOCUS</div>
              <h1>
                {title}
                <span aria-hidden="true">.</span>
              </h1>
              <p>{subtitle}</p>
            </div>
            <div className="heading-actions">
              <button
                className="button secondary"
                disabled={loading}
                onClick={() =>
                  mode === 'api'
                    ? void loadApi(token)
                    : setNotice(
                        'Demo samples are fixed. Incident edits remain until reload or a data-source switch.',
                      )
                }
              >
                <RefreshCw size={15} className={loading ? 'spin' : ''} />
                Refresh
              </button>
              <button
                className="button primary"
                disabled={!snapshot || loading}
                onClick={() => setEditing(null)}
              >
                <Plus size={17} />
                New incident
              </button>
            </div>
          </div>
          {mode === 'demo' && (
            <div className="demo-banner">
              <span className="demo-label">
                <span />
                DEMO MODE
              </span>
              <p>You’re viewing sample data. No live server is connected.</p>
              <button onClick={() => setConnecting(true)}>
                Connect API
                <ArrowUpRight size={14} />
              </button>
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              <Check size={16} />
              <span>{notice}</span>
              <button
                className="icon-button"
                aria-label="Dismiss notification"
                onClick={() => setNotice('')}
              >
                <X size={15} />
              </button>
            </div>
          )}
          {loading ? (
            <div className="loading-state" role="status">
              <RefreshCw className="spin" size={25} />
              <h2>Checking in with your server…</h2>
              <p>Loading health, metrics, server details, and incidents.</p>
            </div>
          ) : error ? (
            <section className="panel connection-error" role="alert">
              <Unplug size={34} />
              <h2>We couldn’t load your server</h2>
              <p>{error}</p>
              <p className="muted">
                The FastAPI foundation does not have business routes yet. No
                demo data is substituted in API mode.
              </p>
              <div>
                <button
                  className="button primary"
                  onClick={() => void loadApi(token)}
                >
                  Try again
                </button>
                <button className="button secondary" onClick={useDemo}>
                  Explore demo data
                </button>
              </div>
            </section>
          ) : (
            snapshot && (
              <>
                {(view === 'overview' || view === 'metrics') && (
                  <MetricCards snapshot={snapshot} openCount={openCount} />
                )}
                {(view === 'overview' || view === 'metrics') && (
                  <div
                    className={`monitoring-grid ${view === 'metrics' ? 'chart-only' : ''}`}
                  >
                    <ResourceChart metrics={snapshot.metrics} />
                    {view === 'overview' && (
                      <HealthPanel
                        snapshot={snapshot}
                        demo={mode === 'demo'}
                        onServer={() => setView('server')}
                      />
                    )}
                  </div>
                )}
                {(view === 'overview' || view === 'incidents') && (
                  <IncidentTable
                    key={view}
                    incidents={snapshot.incidents}
                    total={snapshot.incidentTotal}
                    full={view === 'incidents'}
                    onEdit={setEditing}
                    onViewAll={() => setView('incidents')}
                  />
                )}
                {view === 'metrics' && (
                  <MetricsTable metrics={snapshot.metrics} />
                )}
                {view === 'server' && (
                  <ServerDetails snapshot={snapshot} demo={mode === 'demo'} />
                )}
                {view === 'overview' && (
                  <div className="server-strip">
                    <span className="server-strip-icon">
                      <Server size={20} />
                    </span>
                    <div>
                      <strong>{snapshot.server.hostname}</strong>
                      <span>
                        {snapshot.server.os_name} {snapshot.server.os_version}{' '}
                        <span className="dot-separator">·</span>{' '}
                        {snapshot.server.architecture}
                      </span>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => setView('server')}
                    >
                      Server details
                      <ArrowUpRight size={15} />
                    </button>
                  </div>
                )}
                <footer className="page-footer">
                  <span>
                    <span className="tiny-dot" />
                    {mode === 'demo'
                      ? 'Sample workspace · not live monitoring'
                      : 'API workspace · refresh to fetch new data'}
                  </span>
                  <span>Built for a clearer view.</span>
                </footer>
              </>
            )
          )}
        </main>
      </div>
      {editing !== undefined && (
        <IncidentEditor
          incident={editing}
          demo={mode === 'demo'}
          onClose={() => setEditing(undefined)}
          onSave={saveIncident}
          onDelete={deleteIncident}
        />
      )}
      {connecting && (
        <Modal
          title="Connect your API"
          onClose={() => {
            setConnecting(false);
            setTokenInput('');
          }}
        >
          <p className="modal-description">
            Connect to your ServerWatch API. Until the backend routes are
            implemented, you can explore the demo instead.
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const bearer = tokenInput.trim();
              if (!bearer) return;
              setConnecting(false);
              setTokenInput('');
              void loadApi(bearer);
            }}
          >
            <div className="form-fields">
              <label>
                API path
                <input value="/api/v1" readOnly className="mono" />
              </label>
              <label>
                Bearer token
                <input
                  type="password"
                  required
                  autoComplete="off"
                  value={tokenInput}
                  placeholder="Enter your access token"
                  onChange={(event) => setTokenInput(event.target.value)}
                />
              </label>
              <p className="field-hint">
                Your token stays in memory and is cleared on reload or when
                returning to demo mode.
              </p>
              <div className="modal-footer">
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => {
                    useDemo();
                    setConnecting(false);
                  }}
                >
                  Use demo data
                </button>
                <button type="submit" className="button primary">
                  <Cable size={16} />
                  Connect
                </button>
              </div>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
