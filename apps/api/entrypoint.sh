#!/bin/sh
# Run Alembic migrations then start the API server.
# Postgres is already healthy by the time this runs (docker-compose depends_on
# with condition: service_healthy), so no extra wait loop is needed.
set -e

echo "==> Running database migrations …"
alembic upgrade head
echo "==> Migrations complete."

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
