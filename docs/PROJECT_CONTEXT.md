# Project Context

## User and operational context

The application is being designed for Career Services card-entry work. The operator participates in different kinds of activities, including:

- tabling events,
- classroom presentations,
- other Career Services outreach activities.

For classroom presentations, topics may include items such as interview preparation, resumes, or application materials. Different classes/events should be represented separately in the system.

The physical cards have a consistent branded layout with a large white response area and a dark branded strip. A student writes either an employer name or a question in the white response area. Example real inputs provided during design included:

- Employer: `Fox Sports`
- Question: `What makes a potential employee stand out?`

The card itself does not need to contain the prompt/question text. The application infers whether the written response is an employer name or a question.

## Operator workflow requirements

The operator wants to process a stack quickly:

- place card under a 1080p webcam,
- let the application capture/read it,
- view the captured card and OCR result,
- make small or large corrections directly in the transcription field,
- change classification if needed,
- approve it,
- immediately continue to the next card.

The operator should not need to cancel/reject an entire card because one letter or word is wrong.

## Event vs. session

These are separate concepts.

### Event

Represents the real-world Career Services activity.

Examples:

- Fall Welcome Tabling
- Resume & Application Materials classroom presentation
- Interview Skills classroom presentation

Suggested event types:

- `TABLING`
- `CLASSROOM_PRESENTATION`
- `OTHER`

Optional event metadata may include:

- title
- event type
- event date
- location
- classroom/course
- presentation topic
- notes

### Capture session

Represents one data-entry work session for an event.

An event may have multiple capture sessions. Example:

- One event produces 350 physical cards.
- Session A enters 150 cards on Monday.
- Session B enters 200 cards on Tuesday.

A session can be closed and resumed later. It must persist across browser closure, machine shutdown, server restart, and future days.

Session states:

- `IN_PROGRESS`
- `COMPLETED`
- `ARCHIVED`

`COMPLETED` is not immutable. The operator can view/edit historical cards and may explicitly reopen the session to add more cards.

`ARCHIVED` hides the session from normal active views but does not delete data.

## Card data behavior

Card type:

- `EMPLOYER`
- `QUESTION`
- `UNKNOWN`

OCR produces a draft. The operator may edit it before approval.

Always preserve:

- raw OCR output,
- current final text,
- suggested type,
- final type,
- provider/model metadata,
- timestamps,
- whether the record was edited,
- revision history for later edits.

## Persistence requirement

The database is authoritative.

Google Sheets is a synchronized reporting/data-sharing destination. Editing a previously synchronized card must update the corresponding existing Google Sheet row, not append a duplicate.

## Self-hosting infrastructure context

The reference deployment uses a self-hosted Arch Linux machine.

Known setup:

- OS: Arch Linux
- deployment account and paths are environment-specific
- primarily managed through CLI/SSH; do not assume a desktop GUI
- OpenSSH is used
- Tailscale is already part of the user's private device connectivity
- Avahi is present
- Docker and Docker Compose are used
- Git over SSH is used
- Syncthing is used in some workflows
- the user also works from a MacBook Pro and a Windows PC
- Tailscale is the preferred private access pattern between devices
- do not hard-code or invent Tailnet IP addresses
- exact current device hostnames/Tailscale addresses must be discovered at deployment time

Prior machine information indicates roughly:

- 12-core Ryzen 9 9900X-class CPU
- 32 GB RAM
- NVIDIA RTX 5080-class GPU
- Arch system storage with LVM

However, Codex must verify actual hardware on the target machine with `lscpu`, `free -h`, and `nvidia-smi`; do not couple deployment to an assumed VRAM amount or driver/CUDA version.

## Intended private topology

Preferred target:

```text
MacBook / Windows workstation
        |
        | Tailscale
        v
Arch Linux host
        |
        +-- Web/API containers
        +-- PostgreSQL (private; Docker network only)
        +-- optional local OCR service/model
```

The webcam is attached to the operator's workstation. The web browser captures webcam frames with
the browser MediaDevices API. The camera does not need to be physically attached to the server.

For browser camera access, production-like remote access must use a secure browser context. Prefer HTTPS over Tailscale (for example using capabilities available in the installed Tailscale version) rather than exposing the application publicly merely to satisfy webcam security requirements.

A future VPS may be added, but Phase 1 should work without requiring one. If a VPS is introduced, it should communicate with private services over Tailscale rather than opening PostgreSQL publicly.

## Unknowns that must remain configurable

Do not invent these:

- exact Tailnet IP addresses
- exact MagicDNS hostname
- exact public domain/subdomain
- Google Sheet ID
- Google credential method allowed by ASU
- final OCR provider
- exact GPU VRAM/driver/CUDA state at deployment
- card image retention policy required by Career Services/ASU

Use environment variables and documented setup steps.
