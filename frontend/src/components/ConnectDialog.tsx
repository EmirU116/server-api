import { useState } from 'react';
import { Cable } from 'lucide-react';
import { Modal } from './Modal';

interface ConnectDialogProps {
  /** Live tokens are only accepted over HTTPS or on this machine. */
  allowLiveTokens: boolean;
  onConnect: (readerToken: string, adminToken: string) => void;
  onDemo: () => void;
  onClose: () => void;
}

/** Collect tokens locally; they leave this component only on submit. */
export function ConnectDialog({
  allowLiveTokens,
  onConnect,
  onDemo,
  onClose,
}: ConnectDialogProps) {
  const [tokenInput, setTokenInput] = useState('');
  const [adminInput, setAdminInput] = useState('');

  return (
    <Modal title="Connect your API" onClose={onClose}>
      {!allowLiveTokens ? (
        <p className="modal-description">
          Open ServerWatch over HTTPS to connect with a token. Demo mode is
          available over HTTP.
        </p>
      ) : (
        <>
          <p className="modal-description">
            Use your reader token to view live data. To create or edit
            incidents, also enter the separate incident admin token.
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const bearer = tokenInput.trim();
              if (!bearer) return;
              onConnect(bearer, adminInput.trim());
            }}
          >
            <div className="form-fields">
              <label>
                API path
                <input value="/api/v1" readOnly className="mono" />
              </label>
              <label>
                Incident admin token (optional)
                <input
                  type="password"
                  autoComplete="off"
                  value={adminInput}
                  onChange={(event) => setAdminInput(event.target.value)}
                />
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
                  onClick={onDemo}
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
        </>
      )}
    </Modal>
  );
}
