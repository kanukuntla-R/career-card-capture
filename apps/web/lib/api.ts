import type {
  CardRecord,
  CardRevision,
  CardType,
  CaptureSession,
  CareerEvent,
  EventDraft,
  GoogleSheetsStatus,
  GoogleSheetsSyncResult,
  OCRProviderInfo,
} from "./types";

const API_ROOT = "/backend";

type ApiErrorShape = { error?: { message?: string } };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorShape;
    throw new Error(body.error?.message ?? "Something went wrong. Please try again.");
  }
  return response.json() as Promise<T>;
}

export const api = {
  events: () => request<CareerEvent[]>("/api/v1/events"),
  createEvent: (draft: EventDraft) =>
    request<CareerEvent>("/api/v1/events", {
      method: "POST",
      body: JSON.stringify(draft),
    }),
  updateEvent: (eventId: string, draft: EventDraft) =>
    request<CareerEvent>(`/api/v1/events/${eventId}`, {
      method: "PATCH",
      body: JSON.stringify({
        ...draft,
        event_date: draft.event_date || null,
        location: draft.location?.trim() || null,
        course: draft.course?.trim() || null,
        topic: draft.topic?.trim() || null,
        notes: draft.notes?.trim() || null,
      }),
    }),
  archiveEvent: (eventId: string) =>
    request<CareerEvent>(`/api/v1/events/${eventId}`, { method: "DELETE" }),
  sessions: () => request<CaptureSession[]>("/api/v1/sessions"),
  session: (id: string) => request<CaptureSession>(`/api/v1/sessions/${id}`),
  createSession: (eventId: string) =>
    request<CaptureSession>(`/api/v1/events/${eventId}/sessions`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  completeSession: (id: string) =>
    request<CaptureSession>(`/api/v1/sessions/${id}/complete`, { method: "POST" }),
  reopenSession: (id: string) =>
    request<CaptureSession>(`/api/v1/sessions/${id}/reopen`, { method: "POST" }),
  cards: (sessionId: string, includeRemoved = false) =>
    request<CardRecord[]>(
      `/api/v1/sessions/${sessionId}/cards${includeRemoved ? "?include_removed=true" : ""}`,
    ),
  capture: (sessionId: string, image: Blob, mockText?: string) => {
    const form = new FormData();
    form.append("image", image, "capture.jpg");
    if (mockText) form.append("mock_text", mockText);
    return request<CardRecord>(`/api/v1/sessions/${sessionId}/cards`, {
      method: "POST",
      body: form,
    });
  },
  approve: (cardId: string, finalType: string, finalText: string) =>
    request<CardRecord>(`/api/v1/cards/${cardId}/approve`, {
      method: "POST",
      body: JSON.stringify({ final_type: finalType, final_text: finalText }),
    }),
  editCard: (cardId: string, finalType: CardType, finalText: string, reason?: string) =>
    request<CardRecord>(`/api/v1/cards/${cardId}`, {
      method: "PATCH",
      body: JSON.stringify({
        final_type: finalType,
        final_text: finalText,
        reason: reason?.trim() || null,
      }),
    }),
  cardRevisions: (cardId: string) =>
    request<CardRevision[]>(`/api/v1/cards/${cardId}/revisions`),
  removeCard: (cardId: string) =>
    request<CardRecord>(`/api/v1/cards/${cardId}`, { method: "DELETE" }),
  restoreCard: (cardId: string) =>
    request<CardRecord>(`/api/v1/cards/${cardId}/restore`, { method: "POST" }),
  skip: (cardId: string) =>
    request<CardRecord>(`/api/v1/cards/${cardId}/skip`, { method: "POST" }),
  retryOcr: (cardId: string) =>
    request<CardRecord>(`/api/v1/cards/${cardId}/retry-ocr`, { method: "POST" }),
  ocrProviders: () => request<OCRProviderInfo[]>("/api/v1/ocr/providers"),
  sheetsStatus: () => request<GoogleSheetsStatus>("/api/v1/sync/status"),
  syncSheets: () =>
    request<GoogleSheetsSyncResult>("/api/v1/sync/retry", { method: "POST" }),
  syncCard: (cardId: string) =>
    request<GoogleSheetsSyncResult>(`/api/v1/sync/cards/${cardId}/retry`, {
      method: "POST",
    }),
  exportCsvUrl: () => `${API_ROOT}/api/v1/export/cards.csv`,
  imageUrl: (cardId: string) => `${API_ROOT}/api/v1/cards/${cardId}/image`,
};
