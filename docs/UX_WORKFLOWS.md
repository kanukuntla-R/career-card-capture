# UX Workflows

## 1. Home / recent work

Primary goal: resume work fast.

Show:

- `Resume` for recent in-progress sessions
- recent completed sessions
- create event
- create session
- sync error indicator

Example:

```text
Career Card Capture

Resume work
------------------------------------------------
Fall Welcome Tabling
Session 1
50 cards · 46 approved · 4 need review
Last activity: yesterday
[Resume Session]

Recent events
...
```

## 2. Create event

Fields:

- title*
- event type*
- date
- location
- course
- topic
- notes

Only title/type are initially required.

Classroom-specific fields can be shown when type is `CLASSROOM_PRESENTATION` but remain optional.

## 3. Start session

From event:

```text
Event: Fall Welcome Tabling

[Start New Capture Session]

Existing Sessions
Session 1 — In Progress — 50 cards — [Resume]
Session 2 — Completed — 82 cards — [View]
```

## 4. Capture/review screen

Desktop layout should prioritize speed.

```text
┌───────────────────────────────────────────────────────────────┐
│ Event / Session                            Sync: OK            │
├───────────────────────────────┬───────────────────────────────┤
│ LIVE CAMERA / CAPTURED IMAGE  │ REVIEW                        │
│                               │                               │
│                               │ Type                          │
│                               │ [Question v]                  │
│                               │                               │
│                               │ Transcription                 │
│                               │ ┌───────────────────────────┐ │
│                               │ │ editable text...          │ │
│                               │ └───────────────────────────┘ │
│                               │                               │
│                               │ OCR info / warning            │
│                               │                               │
│                               │ [Retry] [Skip] [Approve]     │
├───────────────────────────────┴───────────────────────────────┤
│ Session: 47 cards · 44 approved · 3 review · 0 sync errors   │
└───────────────────────────────────────────────────────────────┘
```

After capture, the camera may remain visible or switch the left panel to the captured normalized card. The operator must be able to compare text against the image while editing.

## 5. Editing behavior

The transcription is a normal editable textarea/input.

Examples of allowed correction:

- `employe` -> `employee`
- fix capitalization
- add/remove punctuation
- replace a completely wrong word
- rewrite the entire transcription if OCR failed

Never require re-running OCR merely to make a correction.

The app stores:

- OCR draft in `raw_ocr`
- operator version in `final_text`

## 6. Approval

`Ctrl/Cmd + Enter` approves when:

- a review card exists,
- final text is valid,
- the action is not already in flight.

After success:

- show brief confirmation,
- advance to capture-ready state,
- preserve DB first,
- Google sync may occur asynchronously.

Do not block processing the next card on Google Sheets latency.

## 7. Keyboard shortcuts

Initial set:

| Shortcut | Action |
|---|---|
| Space | Capture |
| Ctrl/Cmd + Enter | Approve |
| Alt + E | Employer |
| Alt + Q | Question |
| Alt + U | Unknown |
| Alt + R | Retry OCR |
| Esc | Dismiss transient state |

Rules:

- Space must type a space inside text fields, not capture.
- Alt shortcuts should be disabled or carefully handled while using browser/OS reserved combinations.
- final mappings can be adjusted after real use.
- show shortcut hints in the UI.

## 8. Resume session

When user returns later:

- load session from PostgreSQL,
- restore event/session context,
- show counts,
- show unresolved `NEEDS_REVIEW` cards prominently,
- allow operator to either finish review backlog or capture new cards.

Do not assume "resume" always means card #51; there may be earlier failed/review cards.

## 9. Historical card editing

Session card table:

```text
#   Type       Response                                  Status      Sync
1   Employer   Fox Sports                                Approved    Synced
2   Question   What makes a potential employee...       Approved    Synced
3   Employer   Microsoft                                 Approved    Pending
```

Selecting a row opens detail/review:

- normalized image if retained
- raw OCR
- final text
- type
- timestamps
- sync state
- revision count

`Save Changes` creates revision + sync update when applicable.

## 10. Session completion/reopen

Completing a session:

- stops treating it as active,
- does not lock cards.

A completed session page offers:

- View Responses
- Reopen Session
- Export
- Sync status

Reopen returns state to `IN_PROGRESS`.

## 11. Error UX

Camera denied:
- explain how to re-enable permission
- keep rest of app usable

Vision failed:
- offer manual/full-frame OCR or manual transcription

OCR failed:
- show captured card and empty/editable field

Google sync failed:
- show non-blocking warning
- DB record remains approved
- provide retry

## 12. Accessibility

- all controls keyboard reachable
- visible focus states
- buttons have labels, not color-only meaning
- confidence/status uses text/icons in addition to color
- camera/review panels should scale down reasonably on laptop displays
