"use client";

import { type FormEvent, useState } from "react";

import { api } from "@/lib/api";
import type { CardRecord, CardRevision, CardType } from "@/lib/types";

interface CardHistoryProps {
  cards: CardRecord[];
  busy: boolean;
  onSave: (
    cardId: string,
    finalType: CardType,
    finalText: string,
    reason: string,
  ) => Promise<void>;
  onRemove: (cardId: string) => Promise<void>;
  onRestore: (cardId: string) => Promise<void>;
  onRetrySync: (cardId: string) => Promise<void>;
}

const typeLabels: Record<CardType, string> = {
  EMPLOYER: "Employer",
  QUESTION: "Question",
  UNKNOWN: "Unknown",
};

function providerLabel(provider: string | null): string {
  if (provider === "hunyuan") return "Local HunyuanOCR";
  if (provider === "mock") return "Development OCR";
  return "Manual entry";
}

function statusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

export function CardHistory({
  cards,
  busy,
  onSave,
  onRemove,
  onRestore,
  onRetrySync,
}: CardHistoryProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);
  const [showRemoved, setShowRemoved] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);
  const [draftText, setDraftText] = useState("");
  const [draftType, setDraftType] = useState<CardType>("UNKNOWN");
  const [reason, setReason] = useState("");
  const [revisions, setRevisions] = useState<CardRevision[]>([]);
  const [loadingRevisions, setLoadingRevisions] = useState(false);
  const [saving, setSaving] = useState(false);

  const beginEdit = async (card: CardRecord) => {
    setConfirmRemoveId(null);
    setEditingId(card.id);
    setDraftText(card.final_text ?? "");
    setDraftType(card.final_type ?? "UNKNOWN");
    setReason("");
    setRevisions([]);
    setLoadingRevisions(true);
    try {
      setRevisions(await api.cardRevisions(card.id));
    } catch {
      setRevisions([]);
    } finally {
      setLoadingRevisions(false);
    }
  };

  const cancelEdit = () => {
    setEditingId(null);
    setReason("");
    setRevisions([]);
  };

  const submitEdit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editingId || !draftText.trim() || saving || busy) return;
    setSaving(true);
    try {
      await onSave(editingId, draftType, draftText, reason);
      cancelEdit();
    } catch {
      // The parent displays the API error and the editor stays open for correction.
    } finally {
      setSaving(false);
    }
  };

  const beginRemove = (cardId: string) => {
    cancelEdit();
    setConfirmRemoveId(cardId);
  };

  const confirmRemove = async (cardId: string) => {
    if (busy || actionId) return;
    setActionId(cardId);
    try {
      await onRemove(cardId);
      setConfirmRemoveId(null);
    } catch {
      // The parent displays the API error and confirmation remains available to retry.
    } finally {
      setActionId(null);
    }
  };

  const restore = async (cardId: string) => {
    if (busy || actionId) return;
    setActionId(cardId);
    try {
      await onRestore(cardId);
    } catch {
      // The parent displays the API error.
    } finally {
      setActionId(null);
    }
  };

  const retrySync = async (cardId: string) => {
    if (busy || actionId) return;
    setActionId(cardId);
    try {
      await onRetrySync(cardId);
    } catch {
      // The parent displays the API error.
    } finally {
      setActionId(null);
    }
  };

  const removedCount = cards.filter((item) => item.status === "REMOVED").length;
  const activeCount = cards.length - removedCount;
  const visibleCards = showRemoved
    ? cards
    : cards.filter((item) => item.status !== "REMOVED");

  return (
    <section className="session-history page-frame" aria-label="Session card history">
      <div className="history-heading">
        <div>
          <p className="eyebrow">Saved in this session</p>
          <h2>Card history</h2>
          <p>Review approved responses and correct them without losing the original OCR.</p>
        </div>
        <div className="history-heading-actions">
          <span className="history-count">{activeCount} {activeCount === 1 ? "card" : "cards"}</span>
          {removedCount > 0 && (
            <button
              type="button"
              className="history-removed-toggle"
              onClick={() => setShowRemoved((current) => !current)}
              aria-pressed={showRemoved}
            >
              {showRemoved ? "Hide removed" : `Show removed (${removedCount})`}
            </button>
          )}
        </div>
      </div>

      {visibleCards.length ? (
        <div className="card-history-list">
          <div className="card-history-head" aria-hidden="true">
            <span>Card</span><span>Response</span><span>Type</span><span>Status</span><span />
          </div>
          {visibleCards.map((item) => {
            const isEditing = editingId === item.id;
            const isRemoved = item.status === "REMOVED";
            const isConfirmingRemove = confirmRemoveId === item.id;
            return (
              <article
                className={`card-history-row ${isEditing ? "is-editing" : ""} ${isRemoved ? "is-removed" : ""}`}
                key={item.id}
              >
                <div className="card-history-summary">
                  <span className="history-sequence">{String(item.sequence_number).padStart(2, "0")}</span>
                  <div className="history-copy">
                    <strong>{item.final_text || item.raw_ocr || "Manual transcription needed"}</strong>
                    <span>
                      {providerLabel(item.ocr_provider)}{item.was_edited ? " · Corrected" : ""}
                      {item.status === "APPROVED" && item.sync_status !== "NOT_REQUIRED"
                        ? ` · Sheets: ${statusLabel(item.sync_status).toLowerCase()}`
                        : ""}
                    </span>
                  </div>
                  <span className="history-type">{typeLabels[item.final_type ?? item.suggested_type ?? "UNKNOWN"]}</span>
                  <span className={`card-status card-status-${item.status.toLowerCase()}`}>{statusLabel(item.status)}</span>
                  <div className="history-row-actions">
                    {item.status === "APPROVED" && (
                      <button
                        type="button"
                        className="history-edit-button"
                        onClick={() => void beginEdit(item)}
                        disabled={busy || saving || Boolean(actionId)}
                        aria-expanded={isEditing}
                      >
                        {isEditing ? "Editing" : "Edit"}
                      </button>
                    )}
                    {item.sync_status === "ERROR" && item.status === "APPROVED" && (
                      <button
                        type="button"
                        className="history-sync-button"
                        onClick={() => void retrySync(item.id)}
                        disabled={busy || saving || Boolean(actionId)}
                      >
                        {actionId === item.id ? "Retrying…" : "Retry Sheet"}
                      </button>
                    )}
                    {(item.status === "APPROVED" || item.status === "SKIPPED") && (
                      <button
                        type="button"
                        className="history-remove-button"
                        onClick={() => beginRemove(item.id)}
                        disabled={busy || saving || Boolean(actionId)}
                        aria-label={`Remove card ${String(item.sequence_number).padStart(2, "0")}`}
                      >
                        Remove
                      </button>
                    )}
                    {isRemoved && (
                      <button
                        type="button"
                        className="history-restore-button"
                        onClick={() => void restore(item.id)}
                        disabled={busy || Boolean(actionId)}
                        aria-label={`Restore card ${String(item.sequence_number).padStart(2, "0")}`}
                      >
                        {actionId === item.id ? "Restoring…" : "Restore"}
                      </button>
                    )}
                    {item.status !== "APPROVED" && item.status !== "SKIPPED" && !isRemoved && (
                      <span className="history-no-action">—</span>
                    )}
                  </div>
                </div>

                {isConfirmingRemove && (
                  <div
                    className="history-remove-confirm"
                    role="alertdialog"
                    aria-label={`Remove card ${String(item.sequence_number).padStart(2, "0")}?`}
                  >
                    <div>
                      <strong>Remove this card from active history?</strong>
                      <span>It will leave the session totals, but its OCR and edits can be restored.</span>
                    </div>
                    <button
                      type="button"
                      className="button quiet"
                      onClick={() => setConfirmRemoveId(null)}
                      disabled={actionId === item.id}
                    >
                      Keep card
                    </button>
                    <button
                      type="button"
                      className="button danger history-confirm-remove"
                      onClick={() => void confirmRemove(item.id)}
                      disabled={busy || Boolean(actionId)}
                    >
                      {actionId === item.id ? "Removing…" : "Remove card"}
                    </button>
                  </div>
                )}

                {isEditing && (
                  <form className="history-editor" onSubmit={submitEdit}>
                    <div className="history-edit-main">
                      <fieldset className="history-type-picker">
                        <legend>Response type</legend>
                        {(["EMPLOYER", "QUESTION", "UNKNOWN"] as CardType[]).map((type) => (
                          <label className={draftType === type ? "selected" : ""} key={type}>
                            <input
                              type="radio"
                              name={`history-type-${item.id}`}
                              checked={draftType === type}
                              onChange={() => setDraftType(type)}
                            />
                            {typeLabels[type]}
                          </label>
                        ))}
                      </fieldset>
                      <label className="history-text-field">
                        <span>Approved response</span>
                        <textarea
                          value={draftText}
                          onChange={(event) => setDraftText(event.target.value)}
                          rows={3}
                          autoFocus
                        />
                      </label>
                      <label className="history-reason-field">
                        <span>Reason for change <em>Optional</em></span>
                        <input
                          value={reason}
                          onChange={(event) => setReason(event.target.value)}
                          placeholder="For example: corrected spelling from the physical card"
                          maxLength={500}
                        />
                      </label>
                    </div>

                    <aside className="history-audit-panel">
                      <span>Untouched OCR</span>
                      <p>{item.raw_ocr || "No OCR text was returned."}</p>
                      <small>Saving creates a revision. The OCR above is never changed.</small>
                      {!loadingRevisions && revisions.length > 0 && (
                        <details>
                          <summary>{revisions.length} previous {revisions.length === 1 ? "edit" : "edits"}</summary>
                          {revisions.map((revision) => (
                            <div className="revision-entry" key={revision.id}>
                              <strong>Revision {revision.revision_number}</strong>
                              <span>{revision.previous_final_text} → {revision.new_final_text}</span>
                            </div>
                          ))}
                        </details>
                      )}
                    </aside>

                    <div className="history-editor-actions">
                      <button type="button" className="button quiet" onClick={cancelEdit} disabled={saving}>Cancel</button>
                      <button type="submit" className="button primary" disabled={!draftText.trim() || saving || busy}>
                        {saving ? "Saving…" : "Save changes"}
                      </button>
                    </div>
                  </form>
                )}
              </article>
            );
          })}
        </div>
      ) : cards.length ? (
        <div className="history-empty">
          <span aria-hidden="true">✓</span>
          <div><strong>No active cards</strong><p>Use “Show removed” to restore a card.</p></div>
        </div>
      ) : (
        <div className="history-empty">
          <span aria-hidden="true">01</span>
          <div><strong>No cards captured yet</strong><p>Your reviewed responses will collect here.</p></div>
        </div>
      )}
    </section>
  );
}
