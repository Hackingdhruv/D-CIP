# syntax=docker/dockerfile:1
#
# The worker reuses the backend codebase (the Celery app lives in
# apps/api/app/worker). This image is built from the repository root so it can
# copy the api project; the compose file sets the build context accordingly.

# --- Builder -----------------------------------------------------------------
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.4.20 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app
COPY apps/api/pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project
COPY apps/api/app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# --- Runtime -----------------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --uid 10002 dcip

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/app /app/app

USER dcip

# Liveness: ask Celery to ping its own workers.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD celery -A app.worker.celery_app inspect ping -d celery@$HOSTNAME || exit 1

CMD ["celery", "-A", "app.worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
