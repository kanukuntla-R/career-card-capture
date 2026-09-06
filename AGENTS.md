# AGENTS.md — Instructions for Codex

This repository is an implementation project, not a prototype-only demo. Preserve the architecture and invariants described in `docs/`.

## Mission

Build the Career Card Capture application described in the documentation. Optimize first for a reliable operator workflow:

`camera -> capture -> OCR -> editable review -> approve -> PostgreSQL -> Google Sheets sync`

Sessions must persist and be resumable. Approved cards must remain editable without creating duplicate Google Sheet rows.

## Before changing anything

On an existing checkout:

1. Read `README.md` and every document named in its "Start here for Codex" section.
2. Inspect `git status`.
3. Inspect the repository tree.
4. Inspect existing environment files without printing secrets.
5. If deploying on a Linux host, inspect the machine before changing it:
   - `hostnamectl`
   - `uname -a`
   - `df -h`
   - `lsblk -f`
   - `free -h`
   - `lscpu`
   - `nvidia-smi` if available
   - `docker info`
   - `docker system df`
6. Do not alter Docker storage, disk partitions, Tailscale configuration, firewall rules, NVIDIA drivers, or system packages destructively without explicit user approval.

## Implementation rules

- Implement milestone-by-milestone from `docs/IMPLEMENTATION_PLAN.md`.
- Keep each milestone runnable.
- Run tests before moving to the next milestone.
- Prefer small commits with descriptive commit messages.
- Do not combine unrelated refactors with feature work.
- Do not rewrite the agreed product architecture unless a concrete blocker is found.
- If a blocker is found, document it in `docs/DECISIONS.md` before changing direction.
- Never commit secrets, API keys, OAuth credentials, Google service-account JSON, model tokens, or Tailnet addresses.
- Never hard-code a Tailscale IP. Prefer config or MagicDNS hostnames discovered on the actual Tailnet.
- Never expose PostgreSQL to the public internet.
- Never upload real student card images/text to a cloud OCR provider unless the user explicitly authorizes that provider for real data.
- Keep OCR providers behind the common interface.
- Keep Google Sheets behind the sync abstraction.
- Store raw OCR and final approved text separately.
- Keep revision history for post-approval edits.
- Do not treat `completed` sessions as immutable.
- Do not delete data when a user archives a session.

## UX rules

- Review must show image + editable transcription.
- One wrong letter must be fixable without rejecting/re-running the whole card.
- Keyboard workflow is first-class.
- Keyboard shortcuts must not fire while the operator is typing into an input/textarea unless the shortcut uses explicit modifiers and is intentionally safe.
- `Ctrl/Cmd + Enter` should approve from review unless later usability testing changes this decision.
- Failed/low-confidence OCR must degrade to editable manual review, not block the session.

## Quality gates

A milestone is not complete until:

- automated tests for its critical behavior pass,
- error states are handled,
- migration(s) are included if DB shape changed,
- docs are updated if behavior changed,
- the vertical path still runs end-to-end.

## High-priority constraint

This project is high priority. Favor a small, complete, dependable vertical slice over broad half-implemented features.
