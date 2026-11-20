import { useState } from 'react';
import type { FormEvent } from 'react';
import { Trash2 } from 'lucide-react';
import type {
  Incident,
  IncidentInput,
  IncidentStatus,
  IncidentUpdate,
  Metric,
  Severity,
  WatchedMetric,
} from '../types';
import { evaluateTrigger, metricNames } from '../services/incidentTriggers';
import { Modal } from './Modal';

function localDatetime() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}

export function IncidentEditor({
  incident,
  demo,
  metrics,
  onClose,
  onSave,
  onDelete,
}: {
  incident: Incident | null;
  demo: boolean;
  metrics: Metric[];
  onClose: () => void;
  onSave: (input: IncidentInput | IncidentUpdate, id?: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [title, setTitle] = useState(incident?.title ?? '');
  const [description, setDescription] = useState(incident?.description ?? '');
  const [severity, setSeverity] = useState<Severity>(
    incident?.severity ?? 'warning',
  );
  const [status, setStatus] = useState<IncidentStatus>(
    incident?.status ?? 'open',
  );
  const [occurredAt, setOccurredAt] = useState(localDatetime);
  const [planned, setPlanned] = useState(false);
  const [metric, setMetric] = useState<WatchedMetric | ''>(
    incident?.trigger?.metric ?? '',
  );
  const [threshold, setThreshold] = useState(
    incident?.trigger?.threshold_percent ?? 90,
  );
  const [duration, setDuration] = useState(
    incident?.trigger?.duration_seconds ?? 60,
  );
  const canConfigure =
    planned || incident?.status === 'planned' || !!incident?.trigger;
  const trigger =
    canConfigure && metric
      ? {
          metric,
          threshold_percent: threshold,
          duration_seconds: duration,
        }
      : null;
  const validTrigger =
    Number.isFinite(threshold) &&
    threshold >= 0 &&
    threshold <= 100 &&
    Number.isInteger(duration) &&
    duration >= 5 &&
    duration <= 600;
  const reading =
    trigger && validTrigger ? evaluateTrigger(trigger, metrics, demo) : null;
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (!title.trim() || !description.trim()) {
      setError('A title and description are required.');
      return;
    }
    if (trigger && !validTrigger) {
      setError(
        'Choose a threshold from 0 to 100% and a whole duration from 5 to 600 seconds.',
      );
      return;
    }
    if (
      !incident &&
      !planned &&
      (!Number.isFinite(new Date(occurredAt).getTime()) ||
        new Date(occurredAt).getTime() > Date.now())
    ) {
      setError('Choose an occurrence time that is not in the future.');
      return;
    }
    setBusy(true);
    try {
      const shared = {
        title: title.trim(),
        description: description.trim(),
        severity,
        ...(trigger || incident?.trigger ? { trigger } : {}),
      };
      await onSave(
        incident
          ? { ...shared, ...(status === 'planned' ? {} : { status }) }
          : {
              ...shared,
              occurred_at: planned ? null : new Date(occurredAt).toISOString(),
            },
        incident?.id,
      );
      onClose();
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : 'Unable to save this incident.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!incident) return;
    setBusy(true);
    setError('');
    try {
      await onDelete(incident.id);
      onClose();
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : 'Unable to delete this incident.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title={incident ? 'Manage incident' : 'Create incident'}
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <p className="modal-description">
        {demo
          ? 'Demo changes stay in this tab until you reload or switch data sources.'
          : 'Changes will be saved to your server. Your token must have administrator permission.'}
      </p>
      <form onSubmit={submit}>
        <fieldset disabled={busy} className="form-fields">
          <label>
            Title
            <input
              autoFocus
              required
              maxLength={200}
              value={title}
              placeholder="For example: Database connection loss"
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <label>
            {planned || incident?.status === 'planned'
              ? 'Scenario and response steps'
              : 'Description'}
            <textarea
              required
              maxLength={5000}
              rows={4}
              value={description}
              placeholder="Describe the issue and what to check or do first."
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
          {!incident && (
            <label>
              Incident type
              <select
                value={planned ? 'planned' : 'occurred'}
                onChange={(event) =>
                  setPlanned(event.target.value === 'planned')
                }
              >
                <option value="occurred">Report an incident</option>
                <option value="planned">Plan ahead or run a drill</option>
              </select>
            </label>
          )}
          <div className="form-row">
            <label>
              Severity
              <select
                value={severity}
                onChange={(event) =>
                  setSeverity(event.target.value as Severity)
                }
              >
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="critical">Critical</option>
              </select>
            </label>
            {incident ? (
              <label>
                Status
                <select
                  value={status}
                  onChange={(event) =>
                    setStatus(event.target.value as IncidentStatus)
                  }
                >
                  {incident.status === 'planned' && (
                    <option value="planned">Planned</option>
                  )}
                  <option value="open">
                    {incident.status === 'planned' ? 'Open now' : 'Open'}
                  </option>
                  <option value="investigating">Investigating</option>
                  <option value="resolved">Resolved</option>
                </select>
              </label>
            ) : !planned ? (
              <label>
                Occurred at (local time)
                <input
                  type="datetime-local"
                  required
                  value={occurredAt}
                  onChange={(event) => setOccurredAt(event.target.value)}
                />
              </label>
            ) : null}
          </div>
          {canConfigure && (
            <div className="form-fields">
              <label>
                Watch a metric
                <select
                  value={metric}
                  onChange={(event) =>
                    setMetric(event.target.value as WatchedMetric | '')
                  }
                >
                  <option value="">No threshold</option>
                  {Object.entries(metricNames).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              {metric && (
                <div className="form-row">
                  <label>
                    At or above (%)
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step="any"
                      required
                      value={Number.isNaN(threshold) ? '' : threshold}
                      onChange={(event) =>
                        setThreshold(event.target.valueAsNumber)
                      }
                    />
                  </label>
                  <label>
                    Duration (seconds)
                    <input
                      type="number"
                      min={5}
                      max={600}
                      step={1}
                      required
                      value={Number.isNaN(duration) ? '' : duration}
                      onChange={(event) =>
                        setDuration(event.target.valueAsNumber)
                      }
                    />
                  </label>
                </div>
              )}
              {reading && (
                <p className="field-hint" role="status">
                  {reading.latest !== null &&
                    `Latest ${metricNames[metric || 'cpu']}: ${reading.latest}%. `}
                  {reading.label}.
                  {reading.seconds > 0 &&
                    ` At or above threshold for ${reading.seconds}s.`}
                </p>
              )}
            </div>
          )}
          {incident?.status === 'planned' && (
            <p className="field-hint">
              Keep this planned until you need it. Changing the status records
              the current time as the occurrence.
            </p>
          )}
          {incident && (
            <dl className="record-details">
              <div>
                <dt>Occurred</dt>
                <dd>
                  {incident.occurred_at
                    ? new Date(incident.occurred_at).toLocaleString()
                    : 'Not yet occurred'}
                </dd>
              </div>
              <div>
                <dt>Last updated</dt>
                <dd>{new Date(incident.updated_at).toLocaleString()}</dd>
              </div>
              {incident.resolved_at && (
                <div>
                  <dt>Resolved</dt>
                  <dd>{new Date(incident.resolved_at).toLocaleString()}</dd>
                </div>
              )}
              <div>
                <dt>Record ID</dt>
                <dd className="mono">{incident.id}</dd>
              </div>
            </dl>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          {confirmDelete && (
            <div className="delete-confirmation">
              <p>Delete this incident permanently? This cannot be undone.</p>
              <button
                type="button"
                className="button danger"
                onClick={() => void remove()}
              >
                Confirm deletion
              </button>
              <button
                type="button"
                className="button subtle"
                onClick={() => setConfirmDelete(false)}
              >
                Keep incident
              </button>
            </div>
          )}
          <div className="modal-footer">
            {incident && (
              <button
                type="button"
                className="icon-button delete-button"
                aria-label="Delete incident"
                onClick={() => setConfirmDelete(true)}
              >
                <Trash2 size={17} />
              </button>
            )}
            <span className="spacer" />
            <button
              type="button"
              className="button secondary"
              onClick={onClose}
            >
              Cancel
            </button>
            <button type="submit" className="button primary">
              {busy
                ? 'Saving…'
                : incident
                  ? 'Save changes'
                  : planned
                    ? 'Save incident plan'
                    : 'Create incident'}
            </button>
          </div>
        </fieldset>
      </form>
    </Modal>
  );
}
