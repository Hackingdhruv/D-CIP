# D-CIP — Setup & Demo Guide

**For GPCSSI evaluators/mentors.** This guide gets D-CIP running and walks
through a demo without requiring you to read the source code. Every command
and claim below was verified directly against the current repository —
real Docker builds, a freshly-migrated database, a real login test, and a
real image upload processed end-to-end through OCR.

---

## 1. What D-CIP Is

D-CIP (Digital Cyber Intelligence Platform) is an investigation-management
platform for cybercrime and digital forensics teams: case management,
integrity-verified evidence upload (SHA-256 + chain of custody), automated
entity/timeline extraction with OCR, an optional evidence-cited AI
assistant, and server-enforced role-based access control.

## 2. Minimum System Requirements

| | Core mode (recommended default) | Full mode (+ Neo4j, OpenSearch, and/or AI) |
|---|---|---|
| RAM | 4 GB workable, 8 GB comfortable | **16 GB recommended** — see §15 |
| Disk | 6 GB free | 10 GB free (Docker images/volumes + optional Ollama model) |
| OS | Windows 10/11, macOS, or Linux — Docker Desktop or Docker Engine required | same |

## 3. Required Software

| Software | Needed for |
|---|---|
| [Docker](https://docker.com) + Docker Compose v2 | Running the stack (recommended path) |
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

## 7. Docker/Service Startup — Core vs. Full Mode

Run from the repository root. Two modes are available:

**Core mode (recommended default)** — PostgreSQL, Redis, the API, the
Celery worker, and the web frontend. Neo4j and OpenSearch are **not**
started, matching the app code's own design (it already treats both as
optional and degrades gracefully without them):

```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile core up --build
```

**Full mode** — everything in core mode, plus Neo4j and OpenSearch, for
exercising the graph/search paths:

```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile full up --build
```

Both modes were verified from a clean build: core mode's API reports
healthy without ever waiting on Neo4j/OpenSearch; full mode's readiness
endpoint reports all four datastores `"ok"` once Neo4j and OpenSearch
finish their own startup (roughly a minute).

First run builds the API, worker, and web images from source, which can
take a few minutes.

## 8. Database Migrations

**No manual step is required.** The API container's entrypoint
automatically runs `alembic upgrade head` (applying all 9 migrations,
seeding RBAC roles/permissions and the default admin account) every time it
starts, before the server begins accepting requests. Verified by migrating
a completely empty database from scratch.

If you're running the backend outside Docker, apply migrations manually:
```bash
cd apps/api
uv run alembic upgrade head
```

## 9. Verifying All Services Are Healthy

Check container health directly:
```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile core ps
```
(swap `core` for `full` if you started full mode)

Check the application's own readiness endpoint (reports each datastore individually):
```bash
curl http://localhost:8000/api/v1/health/ready
```
In core mode, a healthy response returns `"status": "degraded"` with
`postgres`/`redis` marked `"ok"` and `neo4j`/`opensearch` marked `"error"`
(expected — they're not running) — the API and every core feature work
normally regardless. In full mode, `"status": "ok"` with all four `"ok"`.

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

This is the *only* account created automatically. To demonstrate a
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
development, not a generic disclaimer.** Core mode (§7) is deliberately
light and does not exhibit this problem. The warning below applies
specifically if you add full mode and/or Ollama on top of it:

- Neo4j and OpenSearch are both JVM-based and each reserve roughly
  512 MB–1 GB+ even at idle.
- A small local Ollama model needs another 1–2 GB free to load without
  failing.
- Running full mode *and* Ollama simultaneously has been observed to
  exhaust available memory on an 8 GB machine badly enough to crash Docker
  Desktop's own virtual machine, taking every container down with it.
- **If your machine has 8 GB RAM or less**, prefer core mode (§7) and skip
  Ollama, or run them one at a time. Core mode alone is comfortable even on
  constrained hardware.
- 16 GB+ RAM is comfortable for full mode with AI enabled simultaneously.

## 16. Running Without AI

This is the **default** — `AI_PROVIDER=none` in `.env.example` requires no
action. Every other feature (cases, evidence pipeline, OCR, entity/timeline
extraction, RBAC, reporting, watchlists) works fully without it. The AI tab
will show a clear "AI is not configured" message instead of failing.

## 16b. Demo Data Seeding (Optional)

The database starts empty. To populate it with one realistic, entirely
fictional demo case — investment-fraud scenario, complete with tasks,
notes, timeline events, and two evidence files (one plain-text log, one
image processed through real OCR) — run, after the stack is up:

```bash
docker compose -f infrastructure/docker/docker-compose.yml exec api python scripts/seed_demo_data.py
```

- **Manual only** — this never runs automatically, not even inside Docker.
- **Safe to re-run** — it checks for the demo case first and does nothing
  if it already exists (no duplicates).
- **Refuses to run in production** — exits with an error if
  `DCIP_ENV=production`, verified directly.
- All data is fictional: example-TLD emails, RFC 5737 documentation IP
  ranges, no real names or credentials.

If running the backend outside Docker: `cd apps/api && uv run python scripts/seed_demo_data.py`.

## 17. Suggested 5-Minute Evaluator Demo Flow

The preferred path — each step's exact command is in the section noted:

1. **Clone the repository** (§4–5).
2. **Configure the environment** — `cp .env.example .env` (§6).
3. **Start Core Mode** (§7):
   ```bash
   docker compose -f infrastructure/docker/docker-compose.yml --profile core up --build
   ```
4. **Login** — http://localhost:5173 with the documented demo admin credentials (§12): `admin@dcip.local` / `Admin@dcip.2024!`.
5. **Seed fictional demo data** (§16b):
   ```bash
   docker compose -f infrastructure/docker/docker-compose.yml exec api python scripts/seed_demo_data.py
   ```
6. **Open "[DEMO] Operation Golden Ledger — Cross-Border Investment Fraud"** in the Cases list.
7. **Explore Evidence, Timeline, Tasks, and Notes** — Evidence has two already-processed files (open `victim_chat_screenshot.png` and note its extracted text came from real OCR on the image, not typed in); Timeline shows the 5 seeded events in order; Tasks shows 4 items across pending/in-progress; Notes shows the 2 seeded investigator notes.
8. **Optionally enable Ollama for AI** (§13–14) — then open the AI tab, generate a case summary, or ask a question in Chat. Every claim should cite the evidence file by name.
9. **Optionally switch to Full Mode** (§7) if you want to see the Neo4j/OpenSearch-backed paths:
   ```bash
   docker compose -f infrastructure/docker/docker-compose.yml --profile full up -d
   ```

For a broader tour, also check the Executive Dashboard (lands here after login), Reports (generate a PDF/DOCX/HTML export from the case), and Administration (Identity, Roles/Permissions, Audit Log) to see RBAC and the audit trail.

## 18. Troubleshooting Common Startup Issues

| Symptom | Likely cause / fix |
|---|---|
| `port is already allocated` | Something else is using 5173/8000/5432/6379/(7474/7687/9200 in full mode). Stop it, or change the host port mapping in `docker-compose.yml`. |
| Frontend loads but API calls fail right after `up` | The API is still applying migrations. Wait 15–30s and refresh — `web`'s container starts as soon as `api`'s container process launches, not after it's actually ready. |
| `web` container shows `unhealthy` in `docker compose ps` | Known cosmetic issue in the container's internal healthcheck (`wget` can't reach `localhost` from inside that container) — the site itself works fine externally (verified: HTTP 200 on port 5173). Not a functional problem. |
| Neo4j or OpenSearch container keeps restarting / never turns healthy (full mode) | Almost always memory pressure — see §15. Increase Docker Desktop's memory allocation (Settings → Resources), free up host RAM, or just use core mode instead. |
| "AI is not configured" message | Expected behavior when `AI_PROVIDER=none` (the default) — not a bug. See §13 to enable it. |
| AI Assistant errors even with Ollama configured | Confirm `ollama serve` is running and `ollama pull llama3.2` completed; test directly with `curl http://localhost:11434/v1/models`. Also check RAM (§15) — a failed model load under memory pressure is the most common cause. |
| `SECRET_KEY` / production startup error | Only applies if you set `DCIP_ENV=production` — the app refuses to boot with the placeholder secret key in production mode, and the demo seed script also separately refuses to run. Not relevant for local evaluation (`DCIP_ENV=development` is the default). |

## 19. Stopping and Restarting

**Stop** (keeps your data):
```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile core down
```

**Stop and wipe all data** (fresh slate next time):
```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile core down -v
```

**Restart** (after a plain `down`, no rebuild needed):
```bash
docker compose -f infrastructure/docker/docker-compose.yml --profile core up
```

(Use `--profile full` throughout instead if you're running full mode.)
