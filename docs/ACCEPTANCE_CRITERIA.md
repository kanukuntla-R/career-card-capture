# Acceptance Criteria

The project is considered usable for V1 when all Critical criteria pass.

## Critical

### A. Persistence

- [ ] Operator can create an event.
- [ ] Operator can create a session.
- [ ] Operator can close browser and resume the session later.
- [ ] Host/container restart does not lose persisted events/sessions/cards.

### B. Camera/capture

- [ ] Operator can select/allow a webcam.
- [ ] Live preview works in the supported browser.
- [ ] Operator can capture a still card image.
- [ ] Camera denial/failure has a useful error state.

### C. OCR/review

- [ ] OCR provider returns a draft or a recoverable error.
- [ ] Review shows card image and text together.
- [ ] Operator can edit a single character without rejecting/re-running the card.
- [ ] Operator can edit the whole transcription.
- [ ] Operator can change Employer/Question/Unknown.
- [ ] Raw OCR remains preserved after edits.
- [ ] `Ctrl/Cmd + Enter` can approve without breaking text editing.

### D. Approved history

- [ ] Approved card persists.
- [ ] Approved card can be opened later.
- [ ] Approved card can be edited.
- [ ] Later edit creates a revision.
- [ ] Completed sessions can be reopened.
- [ ] Archived sessions are not deleted.

### E. Google Sheets

- [ ] New approved card creates one logical Sheet row.
- [ ] Stable record ID is included.
- [ ] Editing an existing card updates that row.
- [ ] Retry does not duplicate the row.
- [ ] Sheets outage does not lose DB approval.
- [ ] Sync errors are visible/retryable.

### F. Deployment

- [ ] Core stack starts with Docker Compose.
- [ ] PostgreSQL is not publicly exposed.
- [ ] App can be accessed privately from another Tailnet device.
- [ ] Remote browser access uses a secure context so webcam APIs work.
- [ ] secrets are not committed.
- [ ] DB backup/restore is documented and tested.

## Important but may ship shortly after V1

- [ ] automatic card contour detection
- [ ] perspective correction
- [ ] orientation correction
- [ ] response-area crop
- [ ] auto-capture after stable frame
- [ ] wait-for-card-removal logic
- [ ] OCR benchmark report
- [ ] session CSV/JSON export

## Quality bar

A feature is not accepted only because the happy-path UI appears to work.

For data-changing features:

- persistence tests must exist,
- error path must be handled,
- DB migrations must exist,
- sync actions must be idempotent where applicable.
