"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { CameraPanel } from "@/components/camera-panel";
import { CardHistory } from "@/components/card-history";
import { GoogleSheetsPanel } from "@/components/google-sheets-panel";
import { EventForm } from "@/components/new-event-form";
import { api } from "@/lib/api";
import { reviewShortcut } from "@/lib/shortcuts";
import type {
  CardRecord,
  CardType,
  CaptureSession,
  CareerEvent,
  EventDraft,
  GoogleSheetsStatus,
  OCRProviderInfo,
} from "@/lib/types";

type View = "home" | "event" | "capture";

const typeLabels: Record<CardType, string> = {
  EMPLOYER: "Employer",
  QUESTION: "Question",
  UNKNOWN: "Unknown",
};

function formatActivity(value: string): string {
  const date = new Date(value);
  const diff = Date.now() - date.getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function eventTypeLabel(value: string): string {
  if (value === "CLASSROOM_PRESENTATION") return "Classroom presentation";
  return value.charAt(0) + value.slice(1).toLowerCase();
}

export function CareerCardApp() {
  const [view, setView] = useState<View>("home");
  const [events, setEvents] = useState<CareerEvent[]>([]);
  const [sessions, setSessions] = useState<CaptureSession[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<CareerEvent | null>(null);
  const [activeSession, setActiveSession] = useState<CaptureSession | null>(null);
  const [card, setCard] = useState<CardRecord | null>(null);
  const [sessionCards, setSessionCards] = useState<CardRecord[]>([]);
  const [ocrProviders, setOcrProviders] = useState<OCRProviderInfo[]>([]);
  const [sheetsStatus, setSheetsStatus] = useState<GoogleSheetsStatus | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [finalText, setFinalText] = useState("");
  const [finalType, setFinalType] = useState<CardType>("UNKNOWN");
  const [showNewEvent, setShowNewEvent] = useState(false);
  const [showEventSettings, setShowEventSettings] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [syncBusy, setSyncBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    const [eventList, sessionList, providerList, nextSheetsStatus] = await Promise.all([
      api.events(),
      api.sessions(),
      api.ocrProviders(),
      api.sheetsStatus(),
    ]);
    setEvents(eventList);
    setSessions(sessionList);
    setOcrProviders(providerList);
    setSheetsStatus(nextSheetsStatus);
    return { eventList, sessionList };
  }, []);

  useEffect(() => {
    // Initial API hydration necessarily updates the client-only workspace state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh()
      .catch((cause: unknown) =>
        setError(cause instanceof Error ? cause.message : "The application could not load."),
      )
      .finally(() => setLoading(false));
  }, [refresh]);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(""), 2600);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  const eventSessions = useMemo(
    () => sessions.filter((session) => session.event_id === selectedEvent?.id),
    [selectedEvent, sessions],
  );
  const activeSessions = useMemo(
    () => sessions.filter((session) => session.status === "IN_PROGRESS"),
    [sessions],
  );
  const approvedTotal = useMemo(
    () => sessions.reduce((sum, session) => sum + session.approved_cards, 0),
    [sessions],
  );
  const reviewTotal = useMemo(
    () => sessions.reduce((sum, session) => sum + session.review_cards, 0),
    [sessions],
  );
  const capturedTotal = useMemo(
    () => sessions.reduce((sum, session) => sum + session.total_cards, 0),
    [sessions],
  );
  const approvalRate = capturedTotal
    ? Math.round((approvedTotal / capturedTotal) * 100)
    : 0;
  const configuredOcr = useMemo(
    () => ocrProviders.find((provider) => provider.enabled),
    [ocrProviders],
  );

  const syncSheets = useCallback(async (silent = false) => {
    if (!sheetsStatus?.enabled || !sheetsStatus.configured || syncBusy) return;
    setSyncBusy(true);
    if (!silent) setError("");
    try {
      const result = await api.syncSheets();
      setSheetsStatus(result);
      if (activeSession) {
        setSessionCards(await api.cards(activeSession.id, true));
      }
      if (!silent) {
        setNotice(
          result.failed
            ? `${result.failed} card${result.failed === 1 ? "" : "s"} could not sync. You can retry.`
            : result.attempted
              ? `${result.succeeded} card${result.succeeded === 1 ? "" : "s"} synced to Google Sheets.`
              : "Google Sheets is already up to date.",
        );
      }
    } catch (cause) {
      if (!silent) {
        setError(cause instanceof Error ? cause.message : "Google Sheets could not be updated.");
      }
      try {
        setSheetsStatus(await api.sheetsStatus());
      } catch {
        // Preserve the actionable sync error already shown to the operator.
      }
    } finally {
      setSyncBusy(false);
    }
  }, [activeSession, sheetsStatus, syncBusy]);

  const retryCardSheetSync = async (cardId: string) => {
    setError("");
    try {
      const result = await api.syncCard(cardId);
      setSheetsStatus(result);
      if (activeSession) setSessionCards(await api.cards(activeSession.id, true));
      if (result.failed) throw new Error(result.last_error ?? "Google Sheets could not be updated.");
      setNotice("Card synced to its Google Sheet row.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Google Sheets could not be updated.");
      throw cause;
    }
  };

  const createEvent = async (draft: EventDraft) => {
    setBusy(true);
    setError("");
    try {
      const created = await api.createEvent({
        ...draft,
        event_date: draft.event_date || undefined,
        location: draft.location || undefined,
        course: draft.course || undefined,
        topic: draft.topic || undefined,
      });
      await refresh();
      setSelectedEvent(created);
      setShowNewEvent(false);
      setView("event");
      setNotice("Event created. Start a capture session when you’re ready.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create the event.");
    } finally {
      setBusy(false);
    }
  };

  const openEvent = (event: CareerEvent) => {
    setSelectedEvent(event);
    setShowEventSettings(false);
    setView("event");
    setError("");
  };

  const updateEvent = async (draft: EventDraft) => {
    if (!selectedEvent) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api.updateEvent(selectedEvent.id, draft);
      setSelectedEvent(updated);
      setEvents((current) =>
        current.map((event) => (event.id === updated.id ? updated : event)),
      );
      setShowEventSettings(false);
      setNotice("Event details updated.");
      void syncSheets(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The event could not be updated.");
    } finally {
      setBusy(false);
    }
  };

  const removeEvent = async () => {
    if (!selectedEvent) return;
    setBusy(true);
    setError("");
    try {
      await api.archiveEvent(selectedEvent.id);
      setShowEventSettings(false);
      setSelectedEvent(null);
      setView("home");
      await refresh();
      setNotice("Event removed from the workspace. Its sessions and cards were preserved.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The event could not be removed.");
    } finally {
      setBusy(false);
    }
  };

  const openSession = useCallback(async (captureSession: CaptureSession) => {
    setBusy(true);
    setError("");
    try {
      const [freshSession, cards] = await Promise.all([
        api.session(captureSession.id),
        api.cards(captureSession.id, true),
      ]);
      const unresolved = cards
        .slice()
        .reverse()
        .find((item) => item.status === "NEEDS_REVIEW" || item.status === "OCR_FAILED");
      setActiveSession(freshSession);
      setSessionCards(cards);
      setSelectedEvent(events.find((event) => event.id === freshSession.event_id) ?? null);
      setCard(unresolved ?? null);
      setFinalText(unresolved?.final_text ?? unresolved?.raw_ocr ?? "");
      setFinalType(unresolved?.final_type ?? unresolved?.suggested_type ?? "UNKNOWN");
      setPreviewUrl(unresolved?.has_image ? api.imageUrl(unresolved.id) : null);
      setView("capture");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not open the session.");
    } finally {
      setBusy(false);
    }
  }, [events]);

  const startSession = async () => {
    if (!selectedEvent) return;
    setBusy(true);
    setError("");
    try {
      const created = await api.createSession(selectedEvent.id);
      await refresh();
      await openSession(created);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start the session.");
      setBusy(false);
    }
  };

  const capture = async (image: Blob, localPreviewUrl: string, mockText?: string) => {
    if (!activeSession) return;
    setBusy(true);
    setError("");
    setPreviewUrl(localPreviewUrl);
    try {
      const created = await api.capture(activeSession.id, image, mockText);
      setCard(created);
      setSessionCards((current) => [created, ...current]);
      setFinalText(created.final_text ?? created.raw_ocr ?? "");
      setFinalType(created.final_type ?? created.suggested_type ?? "UNKNOWN");
      setActiveSession(await api.session(activeSession.id));
      setNotice(created.status === "OCR_FAILED" ? "OCR failed. Type the response manually." : "Draft ready for review.");
    } catch (cause) {
      URL.revokeObjectURL(localPreviewUrl);
      setPreviewUrl(null);
      setError(cause instanceof Error ? cause.message : "The card could not be captured.");
    } finally {
      setBusy(false);
    }
  };

  const approve = useCallback(async () => {
    if (!card || !activeSession || busy || !finalText.trim()) return;
    setBusy(true);
    setError("");
    try {
      const approved = await api.approve(card.id, finalType, finalText);
      const freshSession = await api.session(activeSession.id);
      if (previewUrl?.startsWith("blob:")) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      setCard(null);
      setFinalText("");
      setFinalType("UNKNOWN");
      setActiveSession(freshSession);
      setSessionCards((current) =>
        current.map((item) => (item.id === approved.id ? approved : item)),
      );
      setSessions((current) => current.map((item) => (item.id === freshSession.id ? freshSession : item)));
      setNotice(`Card ${freshSession.approved_cards} approved and saved.`);
      void syncSheets(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The card could not be approved.");
    } finally {
      setBusy(false);
    }
  }, [activeSession, busy, card, finalText, finalType, previewUrl, syncSheets]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!card) return;
      const action = reviewShortcut(event);
      if (!action) return;
      event.preventDefault();
      if (action === "approve") void approve();
      if (action === "employer") setFinalType("EMPLOYER");
      if (action === "question") setFinalType("QUESTION");
      if (action === "unknown") setFinalType("UNKNOWN");
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [approve, card]);

  const skip = async () => {
    if (!card || !activeSession) return;
    setBusy(true);
    try {
      const skipped = await api.skip(card.id);
      const freshSession = await api.session(activeSession.id);
      setActiveSession(freshSession);
      setSessionCards((current) =>
        current.map((item) => (item.id === skipped.id ? skipped : item)),
      );
      setCard(null);
      setPreviewUrl(null);
      setFinalText("");
      setNotice("Card skipped. It remains in the session history.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The card could not be skipped.");
    } finally {
      setBusy(false);
    }
  };

  const retryOcr = async () => {
    if (!card) return;
    setBusy(true);
    try {
      const retried = await api.retryOcr(card.id);
      setCard(retried);
      setFinalText(retried.final_text ?? retried.raw_ocr ?? "");
      setFinalType(retried.final_type ?? retried.suggested_type ?? "UNKNOWN");
      setSessionCards((current) =>
        current.map((item) => (item.id === retried.id ? retried : item)),
      );
      setNotice("Local OCR ran again. Previous attempts are preserved.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "OCR retry failed.");
    } finally {
      setBusy(false);
    }
  };

  const editHistoryCard = async (
    cardId: string,
    nextType: CardType,
    nextText: string,
    reason: string,
  ) => {
    setBusy(true);
    setError("");
    try {
      const updated = await api.editCard(cardId, nextType, nextText, reason);
      setSessionCards((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      if (activeSession) {
        const freshSession = await api.session(activeSession.id);
        setActiveSession(freshSession);
        setSessions((current) =>
          current.map((item) => (item.id === freshSession.id ? freshSession : item)),
        );
      }
      setNotice(`Card ${updated.sequence_number} updated. Previous value preserved.`);
      void syncSheets(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The saved card could not be updated.");
      throw cause;
    } finally {
      setBusy(false);
    }
  };

  const removeHistoryCard = async (cardId: string) => {
    setBusy(true);
    setError("");
    try {
      const removed = await api.removeCard(cardId);
      setSessionCards((current) =>
        current.map((item) => (item.id === removed.id ? removed : item)),
      );
      if (activeSession) {
        const freshSession = await api.session(activeSession.id);
        setActiveSession(freshSession);
        setSessions((current) =>
          current.map((item) => (item.id === freshSession.id ? freshSession : item)),
        );
      }
      setNotice(
        `Card ${removed.sequence_number} removed from active history. You can restore it anytime.`,
      );
      void syncSheets(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The card could not be removed.");
      throw cause;
    } finally {
      setBusy(false);
    }
  };

  const restoreHistoryCard = async (cardId: string) => {
    setBusy(true);
    setError("");
    try {
      const restored = await api.restoreCard(cardId);
      setSessionCards((current) =>
        current.map((item) => (item.id === restored.id ? restored : item)),
      );
      if (activeSession) {
        const freshSession = await api.session(activeSession.id);
        setActiveSession(freshSession);
        setSessions((current) =>
          current.map((item) => (item.id === freshSession.id ? freshSession : item)),
        );
      }
      setNotice(`Card ${restored.sequence_number} restored to session history.`);
      void syncSheets(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The card could not be restored.");
      throw cause;
    } finally {
      setBusy(false);
    }
  };

  const completeSession = async () => {
    if (!activeSession) return;
    setBusy(true);
    try {
      const completed = await api.completeSession(activeSession.id);
      setActiveSession(completed);
      await refresh();
      setNotice("Session marked complete. Its records remain editable.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not complete the session.");
    } finally {
      setBusy(false);
    }
  };

  const reopenSession = async () => {
    if (!activeSession) return;
    setBusy(true);
    try {
      const reopened = await api.reopenSession(activeSession.id);
      setActiveSession(reopened);
      await refresh();
      setNotice("Session reopened. You can add more cards.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not reopen the session.");
    } finally {
      setBusy(false);
    }
  };

  const goHome = () => {
    if (previewUrl?.startsWith("blob:")) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setCard(null);
    setSessionCards([]);
    setActiveSession(null);
    setSelectedEvent(null);
    setShowEventSettings(false);
    setView("home");
    setError("");
    void refresh().catch(() => undefined);
  };

  if (loading) {
    return (
      <main className="loading-screen">
        <div className="brand-mark">CC</div>
        <p>Opening your capture desk…</p>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={goHome} aria-label="Career Card Capture home">
          <span className="brand-mark">CC</span>
          <span><strong>Career Card</strong><small>Capture desk</small></span>
        </button>
        <div className="topbar-actions">
          <span className="privacy-pill"><span aria-hidden="true">●</span> Private workspace</span>
          {view !== "home" && <button className="text-button" onClick={goHome}>All events</button>}
        </div>
      </header>

      {error && (
        <div className="global-alert" role="alert">
          <span>{error}</span>
          <button onClick={() => setError("")} aria-label="Dismiss error">×</button>
        </div>
      )}
      {notice && <div className="toast" role="status">{notice}</div>}

      {view === "home" && (
        <main className="dashboard page-frame">
          <section className="hero">
            <div>
              <p className="eyebrow">Operator workspace</p>
              <h1>Turn every card into a clean, reviewed record.</h1>
              <p className="hero-copy">Capture the handwriting, correct the draft, approve it, and keep moving through the stack.</p>
            </div>
            <button className="button primary large" onClick={() => setShowNewEvent(true)}>+ Create event</button>
          </section>

          <section className="summary-row" aria-label="Workspace totals">
            <article className="summary-stat">
              <span>Active sessions</span><strong>{activeSessions.length}</strong>
              <small>Across {events.length} {events.length === 1 ? "event" : "events"}</small>
            </article>
            <article className="summary-stat">
              <span>Cards captured</span><strong>{capturedTotal}</strong>
              <small>In {sessions.length} {sessions.length === 1 ? "session" : "sessions"}</small>
            </article>
            <article className="summary-stat approval-stat">
              <span>Cards approved</span><strong>{approvedTotal}</strong>
              <small>{approvalRate}% approval rate</small>
              <div className="stat-progress" role="progressbar" aria-label="Approval rate" aria-valuenow={approvalRate} aria-valuemin={0} aria-valuemax={100}><i style={{ width: `${approvalRate}%` }} /></div>
            </article>
            <article className={`summary-stat review-stat ${reviewTotal ? "has-review" : "is-clear"}`}>
              <span>Need review</span><strong>{reviewTotal}</strong>
              <small>{reviewTotal ? "Ready for operator review" : "Everything is caught up"}</small>
            </article>
          </section>

          <GoogleSheetsPanel
            status={sheetsStatus}
            busy={syncBusy}
            onSync={() => syncSheets(false)}
          />

          {showNewEvent && <EventForm busy={busy} onCancel={() => setShowNewEvent(false)} onSubmit={createEvent} />}

          <section className="section-block">
            <div className="section-heading">
              <div><p className="eyebrow">Pick up where you left off</p><h2>Resume work</h2></div>
              <span>{activeSessions.length} active</span>
            </div>
            {activeSessions.length ? (
              <div className="resume-list">
                {activeSessions.slice(0, 3).map((session, index) => (
                  <article className="resume-card" key={session.id}>
                    <div className="session-number">{String(index + 1).padStart(2, "0")}</div>
                    <div className="resume-main">
                      <span className="event-kind">{eventTypeLabel(session.event_type)}</span>
                      <h3>{session.event_title}</h3>
                      <p>{session.name} · Last activity {formatActivity(session.last_activity_at)}</p>
                    </div>
                    <div className="mini-stats" aria-label="Session card counts">
                      <span><strong>{session.approved_cards}</strong> approved</span>
                      <span><strong>{session.review_cards}</strong> review</span>
                    </div>
                    <button className="button dark" onClick={() => void openSession(session)} disabled={busy}>Resume session <span aria-hidden="true">→</span></button>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <span className="empty-icon" aria-hidden="true">✦</span>
                <h3>No active sessions yet</h3>
                <p>Create an event, then start a session for its first stack of cards.</p>
              </div>
            )}
          </section>

          <section className="section-block">
            <div className="section-heading">
              <div><p className="eyebrow">Organized by activity</p><h2>Recent events</h2></div>
              <button className="text-button" onClick={() => setShowNewEvent(true)}>New event +</button>
            </div>
            {events.length ? (
              <div className="event-grid">
                {events.map((event) => {
                  const related = sessions.filter((session) => session.event_id === event.id);
                  const cards = related.reduce((sum, session) => sum + session.total_cards, 0);
                  return (
                    <button className="event-card" key={event.id} onClick={() => openEvent(event)}>
                      <span className="event-card-top"><span className="event-kind">{eventTypeLabel(event.event_type)}</span><span aria-hidden="true">↗</span></span>
                      <strong>{event.title}</strong>
                      <span className="event-meta">{event.event_date ? new Date(`${event.event_date}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "Date not set"}{event.location ? ` · ${event.location}` : ""}</span>
                      <span className="event-card-footer">{related.length} {related.length === 1 ? "session" : "sessions"}<b>{cards} cards</b></span>
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="empty-line">Your events will appear here after you create the first one.</p>
            )}
          </section>
        </main>
      )}

      {view === "event" && selectedEvent && (
        <main className="page-frame event-page">
          <button className="back-link" onClick={goHome}>← Back to events</button>
          <section className="event-hero">
            <div>
              <span className="event-kind">{eventTypeLabel(selectedEvent.event_type)}</span>
              <h1>{selectedEvent.title}</h1>
              <p>{selectedEvent.event_date ? new Date(`${selectedEvent.event_date}T12:00:00`).toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" }) : "No date set"}{selectedEvent.location ? ` · ${selectedEvent.location}` : ""}</p>
            </div>
            <div className="event-hero-actions">
              <button className="button quiet" onClick={() => setShowEventSettings((current) => !current)} disabled={busy}>Edit event</button>
              <button className="button primary large" onClick={() => void startSession()} disabled={busy}>{busy ? "Starting…" : "+ Start capture session"}</button>
            </div>
          </section>

          {showEventSettings && (
            <EventForm
              key={selectedEvent.id}
              busy={busy}
              initialEvent={selectedEvent}
              onCancel={() => setShowEventSettings(false)}
              onRemove={removeEvent}
              onSubmit={updateEvent}
            />
          )}

          <section className="section-block event-sessions">
            <div className="section-heading"><div><p className="eyebrow">Batches of work</p><h2>Capture sessions</h2></div><span>{eventSessions.length} total</span></div>
            {eventSessions.length ? (
              <div className="session-table">
                <div className="session-table-head"><span>Session</span><span>Status</span><span>Progress</span><span>Last activity</span><span /></div>
                {eventSessions.map((session) => (
                  <div className="session-row" key={session.id}>
                    <strong>{session.name}</strong>
                    <span className={`status-badge status-${session.status.toLowerCase()}`}>{session.status.replace("_", " ")}</span>
                    <span>{session.approved_cards} of {session.total_cards} approved</span>
                    <span>{formatActivity(session.last_activity_at)}</span>
                    <button className="button small secondary" onClick={() => void openSession(session)}>{session.status === "IN_PROGRESS" ? "Resume" : "View"}</button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state"><span className="empty-icon">01</span><h3>Ready for the first stack?</h3><p>Start a session now. You can close it and return on another day without losing your place.</p></div>
            )}
          </section>
        </main>
      )}

      {view === "capture" && activeSession && (
        <main className="capture-page">
          <section className="capture-header page-frame">
            <div className="breadcrumb"><button onClick={goHome}>Events</button><span>/</span><button onClick={() => { setSelectedEvent(events.find((event) => event.id === activeSession.event_id) ?? null); setView("event"); }}>{activeSession.event_title}</button><span>/</span><strong>{activeSession.name}</strong></div>
            <div className="capture-title-row">
              <div><p className="eyebrow">{activeSession.status.replace("_", " ")}</p><h1>{activeSession.event_title}</h1></div>
              <span className={`ocr-runtime ${configuredOcr?.ready ? "is-ready" : "is-offline"}`}>
                <span aria-hidden="true">●</span>
                {configuredOcr?.id === "hunyuan" ? "Local HunyuanOCR" : "Development OCR"}
                {configuredOcr?.ready ? " ready" : " offline"}
              </span>
              {activeSession.status === "IN_PROGRESS" ? (
                <button className="button quiet" onClick={() => void completeSession()} disabled={busy || Boolean(card)}>Complete session</button>
              ) : (
                <button className="button secondary" onClick={() => void reopenSession()} disabled={busy}>Reopen session</button>
              )}
            </div>
          </section>

          <section className="capture-workspace page-frame">
            <CameraPanel
              busy={busy}
              locked={Boolean(card) || activeSession.status !== "IN_PROGRESS"}
              imageUrl={previewUrl ?? (card?.has_image ? api.imageUrl(card.id) : null)}
              onCapture={capture}
            />

            <section className={`review-panel ${card ? "is-active" : ""}`} aria-label="OCR review">
              <div className="panel-heading">
                <div><p className="eyebrow">Review</p><h2>{card ? `Card ${card.sequence_number}` : "Waiting for a capture"}</h2></div>
                {card && <span className="draft-pill">Human review required</span>}
              </div>

              {card ? (
                <div className="review-content">
                  <fieldset className="type-picker">
                    <legend>Response type</legend>
                    {(["EMPLOYER", "QUESTION", "UNKNOWN"] as CardType[]).map((type) => (
                      <label key={type} className={finalType === type ? "selected" : ""}>
                        <input type="radio" name="card-type" value={type} checked={finalType === type} onChange={() => setFinalType(type)} />
                        <span>{typeLabels[type]}</span>
                        <kbd>{type === "EMPLOYER" ? "Alt E" : type === "QUESTION" ? "Alt Q" : "Alt U"}</kbd>
                      </label>
                    ))}
                  </fieldset>

                  <label className="transcription-field">
                    <span>Transcription <em>Edit anything the OCR got wrong</em></span>
                    <textarea value={finalText} onChange={(event) => setFinalText(event.target.value)} autoFocus rows={6} placeholder="Type the response exactly as written…" />
                  </label>

                  <div className="ocr-note">
                    <div><span className="ocr-mark" aria-hidden="true">Ai</span><p><strong>{card.status === "OCR_FAILED" ? "OCR needs help" : card.ocr_provider === "hunyuan" ? "Local HunyuanOCR draft" : "Development OCR draft"}</strong><span>{card.ocr_provider ?? "manual"} · {card.ocr_model ?? "manual review"}{card.ocr_confidence !== null ? ` · ${Math.round(card.ocr_confidence * 100)}% confidence` : ""}</span></p></div>
                    {card.raw_ocr && <details><summary>View untouched OCR</summary><p>{card.raw_ocr}</p></details>}
                  </div>

                  <div className="review-actions">
                    <button className="button quiet" onClick={() => void skip()} disabled={busy}>Skip</button>
                    <button className="button secondary" onClick={() => void retryOcr()} disabled={busy || !card.has_image}>Retry OCR</button>
                    <button className="button primary approve" onClick={() => void approve()} disabled={busy || !finalText.trim()}>
                      {busy ? "Saving…" : "Approve & next"}<kbd>⌘/Ctrl ↵</kbd>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="review-empty">
                  <span aria-hidden="true">→</span>
                  <h3>{activeSession.status === "IN_PROGRESS" ? "Capture a card to begin" : "This session is complete"}</h3>
                  <p>{activeSession.status === "IN_PROGRESS" ? "The OCR draft will appear here. You’ll always review it before anything is approved." : "Reopen the session if more cards need to be added."}</p>
                </div>
              )}
            </section>
          </section>

          <CardHistory
            cards={sessionCards}
            busy={busy}
            onSave={editHistoryCard}
            onRemove={removeHistoryCard}
            onRestore={restoreHistoryCard}
            onRetrySync={retryCardSheetSync}
          />

          <section className="session-strip">
            <div className="page-frame session-strip-inner">
              <div><span>Session progress</span><strong>{activeSession.name}</strong></div>
              <div className="strip-stat"><strong>{activeSession.total_cards}</strong><span>Total cards</span></div>
              <div className="strip-stat approved"><strong>{activeSession.approved_cards}</strong><span>Approved</span></div>
              <div className="strip-stat review"><strong>{activeSession.review_cards}</strong><span>Need review</span></div>
              <div className="strip-stat"><strong>{activeSession.skipped_cards}</strong><span>Skipped</span></div>
              <div className="keyboard-hint"><span>Shortcuts</span><kbd>Space</kbd> capture <kbd>Ctrl ↵</kbd> approve</div>
            </div>
          </section>
        </main>
      )}
    </div>
  );
}
