# Product Requirements

## 1. Product goal

Reduce the manual effort required to enter handwritten Career Services activity cards while keeping a human in control of the final data.

## 2. Primary user

Initial release: a Career Services operator processing physical cards after or during an event.

The architecture should not prevent future multi-user support, but V1 does not need enterprise RBAC.

## 3. Functional requirements

### PR-01 Event management

The operator can:

- create an event,
- edit event metadata,
- list/search events,
- view event statistics,
- archive an event without deleting its data.

Fields:

- title: required
- type: `TABLING | CLASSROOM_PRESENTATION | OTHER`
- date: optional
- location: optional
- course: optional
- topic: optional
- notes: optional

### PR-02 Persistent capture sessions

The operator can:

- create a capture session under an event,
- pause/close the UI,
- return later,
- resume an `IN_PROGRESS` session,
- mark a session `COMPLETED`,
- reopen a completed session to add more cards,
- archive a session,
- view/edit all cards from historical sessions.

No session state may depend only on browser memory.

### PR-03 Live webcam preview

The capture page provides a live 1080p-capable webcam preview where supported by the device.

Requirements:

- enumerate/select cameras when multiple are available,
- remember the selected camera locally where reasonable,
- handle camera permission denial cleanly,
- allow manual capture,
- allow later auto-capture after stable card detection.

### PR-04 Card capture

A captured frame receives:

- a unique card record,
- the event/session relationship,
- image processing,
- OCR processing,
- a review state.

The capture path must tolerate rotated or perspective-skewed cards.

### PR-05 OCR

OCR must be provider-agnostic.

Minimum providers:

1. Mock provider for deterministic development/tests.
2. HunyuanOCR adapter/local candidate.
3. Extend adapter/cloud benchmark candidate.

Real-data use of cloud OCR is disabled unless explicitly authorized/configured.

### PR-06 Card classification

Suggested card type:

- `EMPLOYER`
- `QUESTION`
- `UNKNOWN`

Low-confidence or ambiguous results must become `UNKNOWN` rather than forcing a potentially wrong category.

The reviewer can always change the type.

### PR-07 Editable review

Review page must show:

- captured/processed card image,
- raw OCR,
- editable final transcription,
- suggested/final card type,
- provider/model information where useful,
- OCR/confidence indicators,
- retry action,
- skip action,
- approve action.

The editable text field is the main correction mechanism. A one-character error must require only editing that character and approving.

### PR-08 Approval

Approval:

- validates final text is not empty unless explicitly allowed,
- persists final type/text,
- changes status to approved,
- records approval time,
- creates/updates Google sync work,
- advances efficiently to the next card.

### PR-09 Historical edits

Approved cards remain editable.

When final text or type changes:

- create an immutable revision snapshot,
- update the current response,
- mark the Google sync target pending,
- update the existing Google Sheet row rather than append a duplicate.

### PR-10 Keyboard workflow

Initial shortcuts:

- `Space`: manual capture when not typing
- `Ctrl/Cmd + Enter`: approve
- `Alt + E`: Employer
- `Alt + Q`: Question
- `Alt + U`: Unknown
- `Alt + R`: retry OCR
- `Esc`: leave/dismiss current transient action; do not silently delete records

Shortcuts must not interfere with text entry.

### PR-11 Session dashboard

Show at minimum:

- session name/event
- session state
- total cards
- cards awaiting review
- approved cards
- skipped/failed cards
- sync pending/errors
- recent cards

### PR-12 Google Sheets synchronization

PostgreSQL is authoritative.

The app can sync approved responses to a configured Google Sheet.

Required behavior:

- append a new row once for a new approved record,
- maintain a stable record identifier,
- update the correct existing row after later edits,
- retry transient failures,
- surface permanent failures to the operator,
- never create duplicates merely because a retry occurred.

### PR-13 Data portability

Provide later-safe export of event/session data as CSV and/or JSON. This is not required for the first vertical slice but the schema/API must not make it difficult.

### PR-14 Deployment

The application must run via Docker Compose on Linux.

It must be possible to:

- run locally for development,
- run on an Arch Linux host,
- access it privately over Tailscale,
- move it to a VPS later without replacing the data model.

## 4. Non-functional requirements

### Reliability

- no loss of approved records after refresh/restart,
- DB migrations are reproducible,
- sync jobs are idempotent,
- OCR failures are recoverable through manual editing.

### Usability

- card throughput is more important than decorative UI,
- common flow should be keyboard-friendly,
- review should not require multiple modal dialogs.

### Privacy

- real student data should remain local/private by default,
- images should not be retained indefinitely by accident,
- cloud OCR is opt-in for real data.

### Performance targets

Initial practical targets, not hard SLA:

- UI capture feedback: immediate
- frame capture to review result: aim < 5 seconds for typical local/cloud OCR, but do not sacrifice correctness to hit this
- approval action: < 500 ms UI acknowledgement after DB persistence
- next-card readiness: effectively immediate after approval

### Observability

Record enough structured logs to diagnose:

- OCR provider failures,
- vision/cropping failures,
- Google sync failures,
- DB migration/startup problems.

Do not log secrets or full card text at verbose levels in production by default.
