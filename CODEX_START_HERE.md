# CODEX START HERE

You are taking over implementation of a high-priority internal card-entry tool.

Do not start coding until you read `AGENTS.md` and the documentation set referenced by `README.md`.

## The one-sentence product

A Career Services operator places a handwritten response card under a webcam, OCR produces an editable draft, the operator corrects and approves it, PostgreSQL saves the authoritative record, and Google Sheets synchronizes it.

## Non-negotiable behavior

1. Sessions persist and can be resumed on a later day.
2. Completed sessions and approved cards can still be reopened/edited.
3. One wrong OCR character is fixed by editing text; the card does not need to be rejected.
4. Raw OCR is never overwritten by corrected final text.
5. Historical approved edits create revisions.
6. PostgreSQL is authoritative.
7. Google Sheets updates the existing logical row after edits; no duplicate row on retry.
8. OCR provider is replaceable.
9. Real data does not silently leave the private environment.
10. Deployment must fit an Arch Linux host + Tailscale setup.
11. PostgreSQL must not be publicly exposed.
12. Build the manual-capture/mock-OCR vertical slice before auto-capture and complex OCR deployment.

## Known infrastructure

The target is an Arch Linux host managed largely via SSH/CLI. Mac/Windows operator devices and
the server use Tailscale as the private connectivity pattern. The browser/webcam can remain on
the workstation while web/API/database run on the Linux host.

Do not invent IP addresses or Tailnet names. Discover them at deployment time.

Before host-level changes, perform the preflight in `docs/DEPLOYMENT_ARCH_TAILSCALE.md`.

## First coding objective

Complete Milestones 0–2 only.

At the end, demonstrate:

```text
create event
-> create session
-> webcam manual capture
-> mock OCR
-> edit OCR text
-> approve
-> PostgreSQL persistence
-> browser/server restart
-> resume session
-> see approved corrected card
```

Only after this works should implementation proceed to Sheets, real OCR, and auto-capture.
