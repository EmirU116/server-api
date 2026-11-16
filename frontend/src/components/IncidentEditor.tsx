import { useState } from 'react';
import type { FormEvent } from 'react';
import { Trash2 } from 'lucide-react';
import type {
  Incident,
  IncidentInput,
  IncidentStatus,
  IncidentUpdate,
  Severity,
} from '../types';
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
  onClose,
  onSave,
  onDelete,
}: {
  incident: Incident | null;
  demo: boolean;
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
    if (
      !incident &&
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
      };
      await onSave(
        incident
          ? { ...shared, status }
          : { ...shared, occurred_at: new Date(occurredAt).toISOString() },
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
              placeholder="A short description of what happened"
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <label>
            Description
            <textarea
              required
              maxLength={5000}
              rows={4}
              value={description}
              placeholder="Add context, impact, and any steps taken…"
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
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
                  <option value="open">Open</option>
                  <option value="investigating">Investigating</option>
                  <option value="resolved">Resolved</option>
                </select>
              </label>
            ) : (
              <label>
                Occurred at (local time)
                <input
                  type="datetime-local"
                  required
                  value={occurredAt}
                  onChange={(event) => setOccurredAt(event.target.value)}
                />
              </label>
            )}
          </div>
          {incident && (
            <dl className="record-details">
              <div>
                <dt>Occurred</dt>
                <dd>{new Date(incident.occurred_at).toLocaleString()}</dd>
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
              {busy ? 'Saving…' : incident ? 'Save changes' : 'Create incident'}
            </button>
          </div>
        </fieldset>
      </form>
    </Modal>
  );
}
