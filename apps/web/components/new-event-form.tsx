"use client";

import { useState } from "react";

import type { CareerEvent, EventDraft, EventType } from "@/lib/types";

interface EventFormProps {
  busy: boolean;
  initialEvent?: CareerEvent;
  onCancel: () => void;
  onRemove?: () => Promise<void>;
  onSubmit: (draft: EventDraft) => Promise<void>;
}

export function EventForm({
  busy,
  initialEvent,
  onCancel,
  onRemove,
  onSubmit,
}: EventFormProps) {
  const [draft, setDraft] = useState<EventDraft>(
    initialEvent
      ? {
          title: initialEvent.title,
          event_type: initialEvent.event_type,
          event_date: initialEvent.event_date ?? "",
          location: initialEvent.location ?? "",
          course: initialEvent.course ?? "",
          topic: initialEvent.topic ?? "",
          notes: initialEvent.notes ?? "",
        }
      : { title: "", event_type: "TABLING" },
  );
  const [confirmRemove, setConfirmRemove] = useState(false);
  const isEditing = Boolean(initialEvent);

  const update = (key: keyof EventDraft, value: string) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  return (
    <form
      className="event-form"
      onSubmit={(event) => {
        event.preventDefault();
        void onSubmit(draft);
      }}
    >
      <div className="form-heading">
        <div>
          <p className="eyebrow">{isEditing ? "Event settings" : "New event"}</p>
          <h2>{isEditing ? "Update event details" : "What are these cards from?"}</h2>
        </div>
        <button type="button" className="close-button" onClick={onCancel} aria-label="Close form">×</button>
      </div>

      <div className="form-grid">
        <label className="field field-wide">
          <span>Event title <em>Required</em></span>
          <input
            required
            autoFocus
            value={draft.title}
            onChange={(event) => update("title", event.target.value)}
            placeholder="Fall Welcome Tabling"
          />
        </label>

        <label className="field">
          <span>Event type <em>Required</em></span>
          <select
            value={draft.event_type}
            onChange={(event) => update("event_type", event.target.value as EventType)}
          >
            <option value="TABLING">Tabling</option>
            <option value="CLASSROOM_PRESENTATION">Classroom presentation</option>
            <option value="OTHER">Other</option>
          </select>
        </label>

        <label className="field">
          <span>Date</span>
          <input type="date" value={draft.event_date ?? ""} onChange={(event) => update("event_date", event.target.value)} />
        </label>

        <label className="field">
          <span>Location</span>
          <input value={draft.location ?? ""} onChange={(event) => update("location", event.target.value)} placeholder="Memorial Union" />
        </label>

        {draft.event_type === "CLASSROOM_PRESENTATION" && (
          <>
            <label className="field">
              <span>Course</span>
              <input value={draft.course ?? ""} onChange={(event) => update("course", event.target.value)} placeholder="ENG 101" />
            </label>
            <label className="field field-wide">
              <span>Presentation topic</span>
              <input value={draft.topic ?? ""} onChange={(event) => update("topic", event.target.value)} placeholder="Resume & application materials" />
            </label>
          </>
        )}

        <label className="field field-wide">
          <span>Notes</span>
          <textarea
            value={draft.notes ?? ""}
            onChange={(event) => update("notes", event.target.value)}
            placeholder="Optional context for this event"
            rows={3}
          />
        </label>
      </div>

      <div className="event-form-footer">
        {isEditing && onRemove ? (
          <div className="event-remove-control">
            {confirmRemove ? (
              <>
                <span>Remove this event? Its sessions and cards will be preserved.</span>
                <button type="button" className="text-button" onClick={() => setConfirmRemove(false)} disabled={busy}>Keep event</button>
                <button type="button" className="button danger small" onClick={() => void onRemove()} disabled={busy}>Remove event</button>
              </>
            ) : (
              <button type="button" className="text-button danger-text" onClick={() => setConfirmRemove(true)}>Remove event</button>
            )}
          </div>
        ) : <span />}
        <div className="form-actions">
          <button type="button" className="button quiet" onClick={onCancel}>Cancel</button>
          <button type="submit" className="button primary" disabled={busy || !draft.title.trim()}>
            {busy ? "Saving…" : isEditing ? "Save event" : "Create event"}
          </button>
        </div>
      </div>
    </form>
  );
}
