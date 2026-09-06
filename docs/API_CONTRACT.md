# API Contract

Prefix V1 routes with `/api/v1`.

This is a design contract; exact response envelope may be refined during implementation as long as behavior remains consistent.

## Health

### `GET /health`
Process health.

### `GET /ready`
Readiness including DB connectivity. OCR/Google external dependencies should be reported separately rather than making the whole app unready unless required for core operation.

## Events

### `POST /api/v1/events`
Create event.

Request:

```json
{
  "title": "Fall Welcome Tabling",
  "event_type": "TABLING",
  "event_date": "2026-08-22",
  "location": "Memorial Union",
  "course": null,
  "topic": null,
  "notes": null
}
```

### `GET /api/v1/events`
List/filter events.

### `GET /api/v1/events/{event_id}`
Event detail + summary counts.

### `PATCH /api/v1/events/{event_id}`
Edit metadata.

### `DELETE /api/v1/events/{event_id}`
Safely removes an event from the active workspace by archiving it. Associated sessions and cards
remain stored and direct record access remains possible; this route does not hard-delete data.

## Sessions

### `POST /api/v1/events/{event_id}/sessions`
Create session.

### `GET /api/v1/sessions`
List recent/active sessions.

### `GET /api/v1/sessions/{session_id}`
Session metadata + counts.

### `POST /api/v1/sessions/{session_id}/complete`
Mark completed.

### `POST /api/v1/sessions/{session_id}/reopen`
Reopen completed session.

### `POST /api/v1/sessions/{session_id}/archive`
Archive.

## Cards

### `POST /api/v1/sessions/{session_id}/cards`

Multipart upload:
- image
- optional client capture metadata

Creates card and begins/processes vision + OCR.

Response should return either:
- result ready for review, or
- processing job/card ID if async path is used.

### `GET /api/v1/cards/{card_id}`
Return card detail.

### `GET /api/v1/sessions/{session_id}/cards`
Paginated/filterable session cards.

Filters:
- status
- `include_removed` (defaults to false)
- type
- search
- sync status

An explicit `status=REMOVED` filter or `include_removed=true` exposes soft-removed cards. Removed
cards are otherwise omitted from session history and event/session counts.

### `POST /api/v1/cards/{card_id}/retry-ocr`

Optional body:
```json
{
  "provider": "hunyuan"
}
```

Creates a new OCR attempt. Never destroys prior attempts.

### `POST /api/v1/cards/{card_id}/approve`

```json
{
  "final_type": "QUESTION",
  "final_text": "What makes a potential employee stand out?"
}
```

Semantics:

- transactional DB persistence,
- if raw OCR differs from final text set `was_edited=true`,
- approval creates pending Google sync intent,
- response returns persisted card.

### `PATCH /api/v1/cards/{card_id}`

For historical edit:

```json
{
  "final_type": "EMPLOYER",
  "final_text": "Fox Sports"
}
```

If card is already approved and final fields change:

1. create revision,
2. update current value,
3. mark sync pending.

### `POST /api/v1/cards/{card_id}/skip`
Marks skipped; does not delete.

### `DELETE /api/v1/cards/{card_id}`

Reversibly removes an approved or skipped card from active history and statistics. Raw OCR,
corrected text, OCR attempts, and edit revisions remain stored. Any retained image files are
deleted. Cards still under review must be approved or skipped first.

An optional `reason` query parameter may be supplied. Repeating removal for an already removed
card is idempotent.

### `POST /api/v1/cards/{card_id}/restore`

Restores a removed card to its previous `APPROVED` or `SKIPPED` status. Text and revision history
are unchanged; deleted image files are not recreated.

## OCR providers

### `GET /api/v1/ocr/providers`
Return configured providers and readiness, not secrets.

Example:

```json
[
  {"id":"mock","enabled":true,"ready":true},
  {"id":"hunyuan","enabled":true,"ready":false,"detail":"model not loaded"},
  {"id":"extend","enabled":false,"ready":false}
]
```

## Google Sheets

### `GET /api/v1/sync/status`
Returns whether Google Sheets is enabled/configured, its safe browser URL and tab name, eligible
approved-card count, `PENDING`/`SYNCED`/`ERROR` counts, and the latest safe error message. It never
returns credentials.

### `POST /api/v1/sync/verify`

Checks service-account access and creates the exact header row when the configured tab is empty.
An existing incompatible header returns a safe configuration error.

### `POST /api/v1/sync/retry`
Queues all currently approved records and processes pending/failed records. The response includes
attempted, succeeded, and failed counts. Google failure does not roll back approved PostgreSQL data.

### `POST /api/v1/sync/cards/{card_id}/retry`
Retries one approved card, using its stable Record ID to find and update the same logical row.

### `GET /api/v1/export/cards.csv`

Downloads all active approved cards using the same eight-column contract as Google Sheets. This
endpoint works when Google Sheets is disabled or credentials are unavailable.

## Stats

### `GET /api/v1/events/{event_id}/stats`
Counts by card type/status/session.

### `GET /api/v1/sessions/{session_id}/stats`
Capture/review/sync counts.

## API error shape

Use a predictable structure such as:

```json
{
  "error": {
    "code": "OCR_PROVIDER_UNAVAILABLE",
    "message": "OCR provider is unavailable.",
    "request_id": "..."
  }
}
```

Do not return provider secrets, stack traces, or raw credentials.

## Idempotency

Approval and sheet sync must be safe against retries.

Consider client-generated idempotency keys for capture if duplicate uploads become an observed problem. Do not overcomplicate V1 unless needed.
