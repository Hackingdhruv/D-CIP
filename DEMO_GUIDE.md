# D-CIP — Setup & Demo Guide

**For GPCSSI evaluators/mentors.** This guide gets D-CIP running and walks
through a demo without requiring you to read the source code. Every command
and claim below was verified directly against the current repository —
`git clone`, real Docker startup, a freshly-migrated database, and a real
login test.

---

## 1. What D-CIP Is

D-CIP (Digital Cyber Intelligence Platform) is an investigation-management
platform for cybercrime and digital forensics teams: case management,
integrity-verified evidence upload (SHA-256 + chain of custody), automated
entity/timeline extraction, an optional evidence-cited AI assistant, and
server-enforced role-based access control.

## 2. Minimum System Requirements

| | Recommended | Workable minimum |
|---|---|---|
| RAM | **16 GB** | 8 GB — see the RAM warning in §15, this is genuinely tight |
| Disk | 10 GB free | for Docker images, volumes, and (optionally) an Ollama model |
| OS | Windows 10/11, macOS, or Linux | Docker Desktop or Docker Engine required |

## 3. Required Software

| Software | Needed for |
|---|---|
| [Docker](https://docker.com) + Docker Compose v2 | Running the full stack (recommended path) |
| Git | Cloning the repository |
| Node.js 20.11+, pnpm 9+ | Only if running the frontend **outside** Docker |
| Python 3.13, [uv](https://docs.astral.sh/uv/) | Only if running the backend **outside** Docker |
| [Ollama](https://ollama.com) | Only if you want the AI Assistant running locally (optional) |

## 4–5. Clone the Repository

```bash
git clone https://github.com/Hackingdhruv/D-CIP.git
cd D-CIP
```

## 6. Environment Setup

```bash
cp .env.example .env
```

The defaults in `.env.example` are already usable for a local evaluation —
no edits are required to get the platform running. `AI_PROVIDER=none` by
default (AI is off until you opt in — see §13).

## 7. Docker/Service Startup

Run from the repository root:

```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile dev up --build
```

**This single command starts everything**: PostgreSQL, Redis, Neo4j,
OpenSearch, the API, the Celery worker, and the web frontend. First run
builds the API and web images from source, which can take several minutes.

> ⚠️ **Verified limitation**: the app's own code treats Neo4j and OpenSearch
> as optional (it degrades gracefully if they're down), but the Docker
> Compose file does **not** — the `api` service is hard-configured to wait
> for all four datastores to report healthy before it will start, in both
> the `dev` and `prod` profiles. There is currently no lighter profile that
> skips them. See §15 for why this matters on lower-RAM machines.

## 8. Database Migrations

**No manual step is required when using Docker.** The API container's
entrypoint automatically runs `alembic upgrade head` (applying all 9
migrations, seeding RBAC roles/permissions and the default admin account)
every time it starts, before the server begins accepting requests.

If you're running the backend outside Docker, apply migrations manually:
```bash
cd apps/api
uv run alembic upgrade head
```

## 9. Verifying All Services Are Healthy

Check container health directly:
```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile dev ps
```
All services should show `healthy` (datastores) or `running` (api/worker/web).

Check the application's own readiness endpoint (reports each datastore individually):
```bash
curl http://localhost:8000/api/v1/health/ready
```
A healthy response returns HTTP 200 with `"status": "ok"` and every
component (`postgres`, `redis`, `neo4j`, `opensearch`) marked `"ok"`.

## 10–11. URLs

| | URL |
|---|---|
| **Frontend** | http://localhost:5173 |
| **API interactive docs (Swagger)** | http://localhost:8000/docs |
| API readiness check | http://localhost:8000/api/v1/health/ready |

## 12. Demo Login Credentials

**Verified against a genuinely fresh, empty database** (migrated from
scratch with no other data present):

| | |
|---|---|
| **Email** | `admin@dcip.local` |
| **Password** | `Admin@dcip.2024!` |

This is the *only* account created automatically — there is no seeded
non-admin account and no seed script in the repository. To demonstrate a
non-admin role, log in as admin, go to **Administration → Identity → New
User**, and create one (takes under a minute; assign any non-administrator
role to see the permission difference).

> ⚠️ Intentionally documented for local demo/evaluation use only — not a
> production credential. Rotate or delete it before any shared deployment.

## 13. Enabling Ollama / Local AI (Optional)

The AI Assistant is fully optional — the rest of the platform is unaffected
either way. To enable it with a local, free, no-API-key model:

1. Install Ollama from [ollama.com](https://ollama.com) and make sure it's running (`ollama serve`, or it starts automatically on install).
2. Pull a model (see §14).
3. Add to your `.env`:
   ```
   AI_PROVIDER=ollama
   AI_API_BASE=http://localhost:11434/v1
   AI_MODEL=llama3.2
   AI_API_KEY=ollama-local
   ```
   (`AI_API_KEY` can be any non-empty string — Ollama doesn't check it.)
4. Restart the API container so it picks up the new `.env` values.

## 14. AI Model Installation Command

```bash
ollama pull llama3.2
```
This downloads a ~2 GB model. Any OpenAI-compatible model Ollama supports
will work — `llama3.2` is a reasonable default for a laptop.

## 15. RAM/Resource Warning — Ollama, Neo4j, OpenSearch

**This is based on direct, first-hand experience during this project's own
development, not a generic disclaimer:** running the full Docker stack
(with Neo4j and OpenSearch, which — see §7 — start unconditionally) *and*
Ollama simultaneously has been observed to exhaust available memory on an
8 GB machine badly enough to crash Docker Desktop's own virtual machine,
taking every container down with it.

- Neo4j and OpenSearch are both JVM-based and each reserve roughly
  512 MB–1 GB+ even at idle, on top of everything else.
- A small local Ollama model needs another 1–2 GB free to load without
  failing.
- **If your machine has 8 GB RAM or less**, expect this to be tight. Close
  other memory-heavy applications before starting, and consider running
  without Ollama (§16) or temporarily stopping Neo4j/OpenSearch with
  `docker compose ... stop neo4j opensearch` if you hit failures —
  the platform's core features (cases, evidence, RBAC, reporting) do not
  depend on either.
- 16 GB+ RAM is comfortable for the full stack, including AI.

## 16. Running Without AI

This is the **default** — `AI_PROVIDER=none` in `.env.example` requires no
action. Every other feature (cases, evidence pipeline, entity/timeline
extraction, RBAC, reporting, watchlists) works fully without it. The AI tab
will show a clear "AI is not configured" message instead of failing.

## 17. Suggested 5-Minute Evaluator Demo Flow

> No demo case ships with the repository — the database starts empty. The
> flow below has you create one live, which also demonstrates the evidence
> pipeline working in real time.

1. **Login** — http://localhost:5173, sign in with the admin credentials from §12.
2. **Executive Dashboard** — land here after login; note the role-based dashboard and system metrics.
3. **Cases** — open the Cases list, click **New Case**, give it a title (e.g. "Evaluator Demo") and priority.
4. **Evidence** — inside the new case, open the Evidence tab and upload a small file (a `.txt` or `.log` works well). Watch the processing status move through the pipeline stages (hash → metadata → extraction → timeline → indexed).
5. **AI Assistant** *(only if you completed §13)* — open the AI tab, click **Generate** for a case summary, or ask a question in Chat about the evidence you just uploaded. Every claim should cite the evidence file by name.
6. **Reports** — generate a report from the case (PDF/DOCX/HTML export).
7. **Administration** — as admin, briefly show Identity (user list), Roles/Permissions, and Audit Log to demonstrate server-enforced RBAC and the audit trail.

## 18. Troubleshooting Common Startup Issues

| Symptom | Likely cause / fix |
|---|---|
| `port is already allocated` | Something else is using 5173/8000/5432/6379/7474/7687/9200. Stop it, or change the host port mapping in `docker-compose.yml`. |
| Frontend loads but API calls fail right after `up` | The API is still applying migrations. Wait 15–30s and refresh — `web`'s container starts as soon as `api`'s container process launches, not after it's actually ready. |
| Neo4j or OpenSearch container keeps restarting / never turns healthy | Almost always memory pressure — see §15. Increase Docker Desktop's memory allocation (Settings → Resources) or free up host RAM. |
| "AI is not configured" message | Expected behavior when `AI_PROVIDER=none` (the default) — not a bug. See §13 to enable it. |
| AI Assistant errors even with Ollama configured | Confirm `ollama serve` is running and `ollama pull llama3.2` completed; test directly with `curl http://localhost:11434/v1/models`. Also check RAM (§15) — a failed model load under memory pressure is the most common cause. |
| OCR text extraction doesn't happen for image evidence when using Docker | The current API Docker image does not include the Tesseract binary, so OCR silently no-ops in the containerized path. Text-based evidence (`.txt`, `.log`, etc.) is unaffected. Running the backend outside Docker with Tesseract installed on the host enables it. |
| `SECRET_KEY` / production startup error | Only applies if you set `DCIP_ENV=production` — the app refuses to boot with the placeholder secret key in production mode. Not relevant for local evaluation (`DCIP_ENV=development` is the default). |

## 19. Stopping and Restarting

**Stop** (keeps your data):
```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile dev down
```

**Stop and wipe all data** (fresh slate next time):
```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile dev down -v
```

**Restart** (after a plain `down`, no rebuild needed):
```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile dev up
```
