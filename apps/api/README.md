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
  api/          versioned HTTP routes (health, version)
  core/         config, logging, security, middleware, exceptions, DI
  db/           SQLAlchemy + Redis + Neo4j + OpenSearch connectivity
  repositories/ repository-pattern base
  services/     service-layer base
  schemas/      Pydantic request/response models
  worker/       Celery application
alembic/        database migration environment
tests/          pytest suite
```

No authentication, case, evidence, or AI logic is implemented in this milestone —
only the production-ready foundation.
