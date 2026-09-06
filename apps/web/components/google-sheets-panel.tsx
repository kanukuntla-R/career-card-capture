"use client";

import { api } from "@/lib/api";
import type { GoogleSheetsStatus } from "@/lib/types";

interface GoogleSheetsPanelProps {
  status: GoogleSheetsStatus | null;
  busy: boolean;
  onSync: () => Promise<void>;
}

export function GoogleSheetsPanel({ status, busy, onSync }: GoogleSheetsPanelProps) {
  const connected = Boolean(status?.enabled && status.configured);
  const hasErrors = Boolean(status?.errors);
  const connectionLabel = connected
    ? hasErrors
      ? "Needs attention"
      : "Connected"
    : status?.enabled
      ? "Setup required"
      : "Not connected";

  return (
    <section className={`sheets-panel ${connected ? "is-connected" : ""}`} aria-label="Google Sheets export">
      <div className="sheets-brand" aria-hidden="true">G</div>
      <div className="sheets-copy">
        <div className="sheets-title-row">
          <p className="eyebrow">Export &amp; sharing</p>
          <span className={`sheets-connection ${hasErrors ? "has-error" : ""}`}>
            <i aria-hidden="true" />{connectionLabel}
          </span>
        </div>
        <h2>Google Sheets</h2>
        {connected ? (
          <p>
            Approved responses sync to <strong>{status?.tab_name}</strong>. Later edits update the
            same row using the card&apos;s permanent Record ID.
          </p>
        ) : (
          <p>
            Download a clean CSV now, or add a service account and Sheet ID on the server to keep
            one shared spreadsheet updated.
          </p>
        )}
        {status?.last_error && <p className="sheets-error" role="alert">{status.last_error}</p>}
      </div>

      <div className="sheets-counts" aria-label="Google Sheets sync totals">
        <span>
          <strong>{connected ? status?.synced ?? 0 : status?.eligible_cards ?? 0}</strong>
          {connected ? " synced" : " approved"}
        </span>
        <span><strong>{status?.pending ?? 0}</strong> pending</span>
        <span className={hasErrors ? "has-error" : ""}><strong>{status?.errors ?? 0}</strong> errors</span>
      </div>

      <div className="sheets-actions">
        <a className="button secondary" href={api.exportCsvUrl()} download>Download CSV</a>
        {status?.spreadsheet_url && connected && (
          <a className="button quiet" href={status.spreadsheet_url} target="_blank" rel="noreferrer">
            Open Sheet ↗
          </a>
        )}
        {connected && (
          <button className="button primary" type="button" onClick={() => void onSync()} disabled={busy}>
            {busy ? "Syncing…" : hasErrors ? "Retry sync" : "Sync approved cards"}
          </button>
        )}
      </div>
    </section>
  );
}
