# D-CIP Worker

Celery worker for background processing. It shares the backend codebase: the
Celery application is defined in `apps/api/app/worker/celery_app.py`, and this
service simply runs it.

No tasks are registered in the foundation milestone. The broker and result
backend are Redis, configured via the shared environment variables
(`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`).

## Run locally

From `apps/api` (so the `app` package is importable):

```bash
uv run celery -A app.worker.celery_app worker --loglevel=info
```

## Run via Docker

The worker image is built from the repository root (see the compose file) so it
can include the api source. The container command starts a worker with a
concurrency of two.
