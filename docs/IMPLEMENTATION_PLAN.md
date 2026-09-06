# Implementation Plan

High priority: deliver working increments. Do not attempt the final architecture in one pass.

## Milestone 0 — Repository foundation

Deliver:

- project tree
- Next.js web app
- FastAPI app
- PostgreSQL Compose service
- SQLAlchemy + Alembic
- health/readiness endpoints
- `.env.example`
- Makefile/dev commands
- baseline lint/test tooling

Exit criteria:

- `docker compose up` starts core services
- web can call API
- migration runs
- CI/local test command passes

## Milestone 1 — Events and persistent sessions

Deliver:

- event CRUD
- session create/list/resume/complete/reopen/archive
- DB persistence
- home/recent sessions UI

Exit criteria:

- create an event
- start a session
- restart browser/server
- resume same session
- complete and reopen it

No camera/OCR dependency required yet.

## Milestone 2 — Manual camera capture + mock OCR + editable review

Deliver:

- browser webcam preview
- camera permission handling
- manual capture
- upload captured still to API
- simple initial normalized image handling
- Mock OCR provider
- card record lifecycle
- review page
- edit transcription
- change type
- keyboard approval
- approve to PostgreSQL

Exit criteria:

- capture a card
- mock OCR appears
- edit one letter
- approve
- reload
- approved corrected text persists while raw OCR remains unchanged

This is the first complete vertical slice.

## Milestone 3 — Historical cards + revisions

Deliver:

- session card list
- card detail
- edit approved record
- revision history persistence
- status/count dashboard

Exit criteria:

- edit a previously approved record the next day/session
- revision exists
- current value updates
- no original raw OCR is lost

## Milestone 4 — Google Sheets synchronization

Deliver:

- credential abstraction
- stable Record ID column
- append-on-first-sync
- update-on-edit
- retry/error states
- idempotency tests
- dashboard sync indicator

Use a test Sheet first.

Exit criteria:

- approve -> one row
- edit same card -> same logical row updated
- retries do not duplicate rows

## Milestone 5 — Vision pipeline

Deliver:

- OpenCV card detection
- perspective correction
- orientation
- response-area crop
- fallback paths
- quality metrics
- fixture tests

Exit criteria:

- representative rotated/skewed card images normalize correctly enough for OCR
- low-confidence detection still permits manual review

## Milestone 6 — Real OCR provider: HunyuanOCR

Deliver:

- isolated Hunyuan service/adapter
- readiness endpoint
- GPU/runtime setup documented
- real card transcription
- safe fallback to manual review

Do not alter host GPU stack without approval.

Exit criteria:

- local provider can process sample cards
- failure does not block manual entry
- main API can run even when Hunyuan service is disabled

## Milestone 7 — Extend provider benchmark adapter

Deliver only after credentials/real-data usage decision:

- Extend adapter
- cloud-use opt-in guard
- structured extraction
- benchmark runner support

Exit criteria:

- synthetic/authorized sample can be processed
- no silent cloud fallback

## Milestone 8 — OCR benchmark and provider decision

Run 30–50 representative labeled cards.

Produce:

- CER/WER
- exact rate
- manual correction rate
- classification accuracy
- latency
- deployment/cost notes

Update `docs/DECISIONS.md` with selected default provider.

## Milestone 9 — Auto-capture scanner behavior

Deliver:

- card presence detection
- stability state
- automatic single capture
- wait-for-removal
- toggle for manual/auto capture

Exit criteria:

- same card is not repeatedly captured
- operator can process a stack without clicking capture
- manual mode remains available

## Milestone 10 — Arch/Tailscale production-like deployment

Deliver:

- production Compose config
- persistent DB volume
- private HTTPS/Tailscale access
- backup/restore docs
- start/stop/update procedure
- no public DB exposure

Exit criteria:

- workstation on Tailnet opens app securely
- browser camera works
- application survives container/host restart
- session can resume
- DB backup and restore tested

## Explicitly out of scope until core is stable

- multi-tenant SaaS
- complex role-based permissions
- Kubernetes
- Kafka
- generic document OCR platform
- mobile native app
- advanced AI analytics/clustering
- public internet exposure
- automatic cloud fallback
