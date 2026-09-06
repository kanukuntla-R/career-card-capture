# Development Setup

## Prerequisites

Expected:

- Git
- Docker
- Docker Compose
- Node.js/npm for direct frontend development
- Python tooling for direct API development

Prefer containers for dependencies such as PostgreSQL.

## Suggested commands

Codex should create a Makefile or scripts with equivalents of:

```text
make dev
make test
make lint
make migrate
make migration name="..."
make down
```

Do not require the user to memorize raw Docker commands for normal development.

## Environment

Copy:

```bash
cp .env.example .env
```

Fill only the values needed for the milestone.

Mock OCR should allow development without cloud credentials or GPU.

## Database

Initial startup:

1. start PostgreSQL
2. run Alembic migrations
3. start API
4. start web

Seed data should be optional and clearly separated from real data.

## Sample cards

Do not commit real student card photographs by default.

Use synthetic fixtures or explicit approved samples.

## Local camera

When the web app runs on `localhost`, browser camera APIs can be used without configuring public HTTPS.

Test Chrome/Chromium and Firefox behavior if both are relevant.

## Coding conventions

Backend:

- type hints
- Pydantic schemas
- explicit service boundaries
- no giant route handlers containing DB + CV + OCR + sync logic

Frontend:

- strict TypeScript
- isolate camera/media logic in hooks/components
- do not store authoritative session/card state only in client state
- handle loading/error states explicitly

## Repository hygiene

Ignore:

- `.env`
- credentials
- model weights
- database files/dumps
- captured card images
- generated OCR artifacts
- Node/Python caches
