# Architecture Decision Log

This file is intentionally committed and updated as decisions are made.

## D-001 — PostgreSQL is the source of truth

**Status:** Accepted

Google Sheets is a synchronized destination, not the application database.

Reason:

- supports persistent sessions
- supports revisions/history
- avoids spreadsheet-coupled architecture
- makes future analytics and VPS migration straightforward

## D-002 — Separate Event from Capture Session

**Status:** Accepted

An Event represents the real-world activity. A Capture Session represents a batch/data-entry period under that event.

Reason:

- one event may generate more cards than can be entered in one sitting
- operator must resume later
- different data-entry days should not become fake separate events

## D-003 — Completed sessions remain editable

**Status:** Accepted

`COMPLETED` means active entry is considered done, not that records are immutable.

Explicit reopen is required before adding new cards.

## D-004 — Preserve raw OCR and corrected text

**Status:** Accepted

OCR output is never overwritten by human correction.

Reason:

- auditability
- OCR benchmarking
- historical transparency

## D-005 — Historical edits create revisions

**Status:** Accepted

Approved records can change. A revision snapshot is appended before updating current final values.

## D-006 — OCR providers are pluggable

**Status:** Accepted

Core app must not depend on HunyuanOCR, Extend, or any single OCR implementation.

Initial adapters:

- Mock
- HunyuanOCR
- Extend

Final real-data default will be chosen after representative benchmark and privacy constraints.

## D-007 — Human approval is mandatory

**Status:** Accepted

Even high-confidence OCR does not bypass review in V1.

## D-008 — Webcam capture is browser-side

**Status:** Accepted

The 1080p camera is connected to the operator workstation. The browser captures still images;
an Arch Linux host may run the web/API/backend remotely over Tailscale.

Reason:

- avoids requiring camera physically attached to server
- fits Mac/Windows workstation + Arch server topology

## D-009 — Manual capture before auto-capture

**Status:** Accepted

Manual capture ships first to prove the vertical slice. Auto-detection/stability capture is layered on later.

## D-010 — Cloud OCR cannot be silent fallback

**Status:** Accepted

A local OCR failure cannot automatically send real card data to a cloud provider unless explicitly configured/authorized.

## D-011 — Tailscale preferred for private deployment

**Status:** Accepted

Use the existing Tailnet for remote/private application access. Do not expose PostgreSQL publicly.

## D-012 — Local HunyuanOCR uses the supported llama.cpp path

**Status:** Accepted for workstation validation

The local development workstation runs the quantized HunyuanOCR model behind llama.cpp's
OpenAI-compatible API. The application continues to call it through the pluggable OCR
provider interface.

Reason:

- the workstation has an RTX 5080 with 16 GB VRAM
- the native Transformers path documents a 24 GB minimum
- HunyuanOCR documents llama.cpp for consumer GPUs and PC-side deployment
- card images remain on the operator workstation and no cloud fallback is enabled

## D-013 — Card removal is reversible

**Status:** Accepted

The operator can remove an approved or skipped card from active history and statistics. Removal
is a soft-delete: the card, raw OCR, corrected text, OCR attempts, and edit revisions remain in the
database and the card can be restored from the session's removed-card view.

Reason:

- prevents an accidental removal from destroying validated data
- preserves the OCR and correction audit trail
- keeps active operational totals accurate
- provides an explicit lifecycle that can be migrated safely from SQLite to PostgreSQL

Retained card images are deleted when a card is removed. A card still under review must be
approved or skipped before it can be removed.

## Open decisions

### O-001 Final OCR provider
HunyuanOCR via llama.cpp is selected for local validation. Final production selection remains
pending a representative handwriting benchmark.

### O-002 Google credential mechanism
Pending actual ASU Google Workspace permissions:
- service account, or
- OAuth.

### O-003 Card image retention
Privacy-first proposed default: delete after approval.
Must be confirmed against operational/ASU policy.

### O-004 Authentication
Private Tailnet-only single-user V1 is acceptable as a starting implementation; broader team use requires app-level auth decision.
