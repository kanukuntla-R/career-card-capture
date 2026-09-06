.PHONY: dev down test lint migrate migration

dev:
	docker compose up --build

down:
	docker compose down

test:
	cd apps/api && ../../.venv/bin/python -m pytest
	cd apps/web && npm test -- --run

lint:
	cd apps/api && ../../.venv/bin/python -m ruff check app tests alembic
	cd apps/web && npm run lint

migrate:
	docker compose run --rm api alembic upgrade head

migration:
	docker compose run --rm api alembic revision --autogenerate -m "$(name)"
