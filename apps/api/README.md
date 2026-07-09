# D-CIP API

FastAPI backend for the Digital Cyber Intelligence Platform.

## Local development

```bash
uv sync                       # install dependencies into .venv
uv run uvicorn app.main:app --reload
```

The interactive API docs are served at `http://localhost:8000/docs` (disabled in
production).

## Useful commands

```bash
uv run pytest                 # run tests with coverage
uv run ruff check .           # lint
uv run mypy app               # type-check
uv run alembic upgrade head   # apply migrations
```

## Layout

```
app/
  api/v1/routes/  18 route modules (auth, cases, evidence, ai, reports,
                  timeline, search, watchlists, alerts, admin, users,
                  roles, permissions, dashboard, notifications, ...)
  core/           config, logging, security, middleware, exceptions, DI
  db/             SQLAlchemy + Redis + Neo4j + OpenSearch connectivity
  models/         SQLAlchemy models (29)
  repositories/   repository-pattern data access
  services/       business logic layer
  schemas/        Pydantic request/response models
  worker/         Celery application and tasks (evidence pipeline)
alembic/          database migrations (9)
scripts/          seed_demo_data.py — manual, idempotent demo data
tests/            pytest suite (450 tests)
```

See [`ARCHITECTURE.md`](../../ARCHITECTURE.md) at the repo root for the full
technical reference.
