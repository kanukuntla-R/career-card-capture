# Testing and OCR Benchmark

## 1. Test pyramid

### Unit tests

Backend:

- event/session state transitions
- approval validation
- revision creation
- sync idempotency
- OCR provider interface/error mapping
- classification validation
- payload hashing

Vision:

- rotation
- perspective transform
- response-region crop
- no-card fallback

Frontend:

- shortcut behavior
- typing does not trigger capture
- edit + approve
- resume session rendering
- sync error state

### Integration tests

Use disposable PostgreSQL.

Test:

- create event -> session -> card -> approve
- close/reload simulation -> session/card persists
- historical edit -> revision + pending sync
- Google sync retry without duplication
- Alembic upgrade from empty DB

### End-to-end

Use Playwright with mocked camera/media where feasible.

Critical E2E:

1. create event
2. create session
3. capture fixture
4. mock OCR result
5. edit one word
6. approve
7. reload app
8. verify card persists
9. edit approved card
10. verify revision
11. verify sync mock updates same logical row

## 2. Manual camera test

Because browser webcam behavior depends on hardware/browser, maintain a short manual test checklist:

- camera permission grant
- camera permission denial
- 1080p request/fallback
- camera selector
- manual capture
- card at 0/90/180/270 degrees
- slight perspective skew
- pencil writing
- pen writing
- bright/dim lighting
- no-card scene

## 3. OCR benchmark dataset

Before choosing production OCR provider, prepare a labeled benchmark.

Target initial set: 30–50 representative cards.

For each image, store ground truth:

```json
{
  "id": "sample-001",
  "ground_truth_text": "Fox Sports",
  "ground_truth_type": "EMPLOYER"
}
```

Only use real cards in the benchmark if allowed. Otherwise create representative synthetic/manual samples.

## 4. Metrics

### Transcription

- Character Error Rate (CER)
- Word Error Rate (WER)
- exact/perfect transcription rate
- percentage requiring manual correction
- average number of edits per card

### Classification

- Employer accuracy
- Question accuracy
- Unknown/ambiguous handling
- confusion matrix

### Operational

- latency median/p95
- failure rate
- GPU memory/resource use
- provider cost if cloud
- privacy/deployment complexity

## 5. Provider comparison

Compare at least:

- HunyuanOCR local candidate
- Extend cloud candidate if authorized
- optional PaddleOCR/other provider only if needed

Do not keep adding providers unless the first comparison shows a real gap.

## 6. Human correction is success, not failure

The product does not require perfect OCR.

A useful model minimizes correction effort while the review UI makes corrections fast.

Track:

- no-edit approvals
- one-character/one-word edits
- major edits
- manual transcription after OCR failure

This metric is more directly relevant to operator productivity than leaderboard scores.

## 7. Performance test

Test a representative session such as:

- 50 cards
- repeated capture/review/approve
- DB restart and resume
- Google sync temporarily disabled, then restored

Acceptance: approved DB data is not lost and sync catches up without duplicates.
