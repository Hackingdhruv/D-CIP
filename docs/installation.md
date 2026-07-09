# Installation

## Prerequisites

| Tool   | Version | Notes                                  |
| ------ | ------- | -------------------------------------- |
| Node   | 20.11+  | Use `.nvmrc` → `nvm use`               |
| pnpm   | 9+      | `corepack enable` then `corepack prepare pnpm@9.12.0 --activate` |
| Python | 3.13    | Backend runtime                        |
| uv     | 0.4+    | Python package/venv manager            |
| Docker | latest  | For the full stack (datastores + apps) |

## 1. Clone and configure

```bash
git clone https://github.com/Hackingdhruv/D-CIP.git && cd D-CIP
cp .env.example .env
```

Edit `.env` as needed. For local development the defaults work as-is. **Before
deploying to production**, set a strong `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

The API refuses to start in production with the placeholder secret.

## 2a. Run with Docker (recommended)

```bash
# Core mode (recommended) — no Neo4j/OpenSearch, the app degrades gracefully without them.
docker compose -f infrastructure/docker/docker-compose.yml --profile core up --build

# Full mode — adds Neo4j and OpenSearch.
docker compose -f infrastructure/docker/docker-compose.yml --profile full up --build
```

Core mode starts PostgreSQL, Redis, the API, the worker, and the web app.
Full mode adds Neo4j and OpenSearch. Add the edge reverse proxy with the
`prod` profile:

```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile prod up --build -d
```

The repository ships a `Makefile` wrapping these commands: `make up` (core
mode), `make up-full`, `make up-prod`, `make down`, `make logs`, `make seed`
(demo data).

## 2b. Run the apps directly

Install JavaScript dependencies and start the web app and turbo tasks:

```bash
pnpm install
pnpm dev
```

In a second terminal, install and run the API:

```bash
cd apps/api
uv sync
uv run uvicorn app.main:app --reload
```

The API expects the datastores to be reachable. Start just those with Docker:

```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile core up postgres redis
```

## 3. Verify

- Web: <http://localhost:5173>
- API docs: <http://localhost:8000/docs>
- API liveness: <http://localhost:8000/api/v1/health>
- API readiness (checks every datastore): <http://localhost:8000/api/v1/health/ready>
