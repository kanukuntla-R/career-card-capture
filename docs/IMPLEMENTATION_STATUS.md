# Implementation Status

Updated: 2026-09-06

## Completed in the initial implementation

### Milestone 0 — Repository foundation

- Next.js + TypeScript + Tailwind web app
- FastAPI + SQLAlchemy API
- Alembic initial migration
- PostgreSQL Docker Compose service with no host/public port
- health and database-readiness endpoints
- pinned dependency versions
- local and container development commands
- baseline backend/frontend tests and linting

### Milestone 1 — Events and persistent sessions

- create, list, view, edit, and safely archive event APIs
- create, list, resume, complete, reopen, and archive session APIs
- persisted session counts and recent-work dashboard
- event/session operator UI with editable event metadata and confirmed removal
- archived events and their sessions are hidden from active work without deleting data
- dashboard statistics for active sessions, captures, approvals/rate, and review backlog

### Milestone 2 — Manual capture, mock OCR, editable review

- 1080p-ideal browser camera request with device selection
- permission and hardware error states
- manual button/Space capture
- sample-card path for development without webcam hardware
- multipart image upload and temporary storage
- deterministic mock OCR provider behind a provider interface
- OCR-attempt persistence
- captured image + editable transcription review
- type correction and guarded keyboard shortcuts
- approval persistence that retains raw OCR separately
- privacy-first image deletion after approval
- skip and retry actions

### Local HunyuanOCR validation slice

- official consumer-GPU llama.cpp path selected after checking the workstation GPU and current HunyuanOCR guidance
- pinned Windows CUDA llama.cpp runtime and checksum-verified local downloader
- Q8 HunyuanOCR language model and multimodal projector stored in ignored local workspace storage
- OpenAI-compatible HunyuanOCR provider with health reporting and safe application-level failures
- OpenCV image decoding, quadrilateral detection, perspective correction, landscape orientation, branded-strip detection, and response-area crop
- conservative employer/question/unknown classification after transcription
- live local OCR status in the capture workspace
- per-session card history showing reviewed text, provider, status, and untouched OCR when corrected
- repeatable two-card complete-session smoke test

### Milestone 3 — Historical cards and revisions

- clean session-history table with response, type, status, provider, and edit actions
- inline approved-card editor available for active and completed sessions
- optional edit reason and visible untouched OCR during correction
- append-only `card_revisions` persistence with an Alembic migration
- revision-history endpoint and previous-edit summary in the editor
- raw OCR remains immutable when historical values change
- session activity timestamp updates after historical edits
- reversible approved/skipped card removal with an inline confirmation
- removed-card history filter and one-click restore
- removed cards excluded from event/session counts while OCR, final text, and revisions remain stored
- retained image deletion during removal
- Alembic `0003_card_removal` lifecycle migration

### Milestone 4 — Google Sheets synchronization

- optional service-account Google Sheets provider behind the sync gateway abstraction
- stable card UUID exported as Record ID, with cached row verification and ID-column repair search
- append-on-first-sync and update-in-place for historical card/event edits
- payload hashes and retry-safe behavior that prevent duplicate rows after an uncertain append
- persistent `NOT_REQUIRED`, `PENDING`, `SYNCED`, and `ERROR` states with safe operator errors
- reversible removal tombstones and restore-to-the-same-row behavior
- dashboard connection state, counts, sync/retry-all, Open Sheet, and CSV download controls
- per-card Sheet state and retry action in card history
- credential-independent CSV export using the same eight-column contract
- Alembic `0004_google_sheet_sync` migration

## Verification completed

- 13 backend tests exercise health/readiness, valid and invalid images, vision normalization, the Hunyuan request adapter, create event/session, capture, edit, approve, persistence after a new client, complete/reopen/archive behavior, Sheet append/update/removal/restore, uncertain-append idempotency, status counts, and CSV export
- frontend tests exercise keyboard approval and prevent classification shortcuts while typing
- 9 frontend tests exercise continuous camera use, the approved-card history editor, and connected/unconfigured Google Sheets dashboard states
- event-management tests exercise metadata updates, confirmed removal, and data preservation
- card-lifecycle tests exercise removal, count exclusion, hidden/default and removed views, image
  cleanup, OCR/revision preservation, and restoration
- backend lint and frontend lint pass
- Next.js production build passes
- local Alembic migration reaches `0004_google_sheet_sync` (head)
- local HunyuanOCR health check passes through the API and Next.js proxy
- complete local session passes with two generated photos, exact OCR transcriptions, human approval, raw-OCR preservation, persistence, and session completion
- live edit verification passes through the running API and web proxy; current value restored and two audit revisions retained
- live event-management verification passes: details updated, event safely archived, and associated session hidden while preserved
- live card-removal verification passes: active total changed from 2 to 1 while removed and returned
  to 2 after restore; OCR text, final text, and revisions were preserved
- local OCR validation session: `de835fb6-da01-4f32-ac02-403b3d318530`

## Deployment status

The Docker stack and persistent PostgreSQL/card-image bind volumes are running on a private Arch
Linux host, with HunyuanOCR served privately by a Windows GPU over Tailscale. The Google client
imports and fake gateway integration are locally verified. A real Google service account and test
Sheet are still required for the live external-provider check.

## Next milestone

Configure a test Google Sheet on the deployment host, verify service-account access, and run one
complete live session proving initial append, historical edit update-in-place, and retry behavior.
Continue the representative real-handwriting benchmark before treating the local model choice as
final.
