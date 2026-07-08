# D-CIP Architecture

Master reference for how D-CIP is actually built, as of this pass. This document
describes **implemented** behavior only. Where the code diverges from
`README.md` or `docs/`, that is called out explicitly under "Known
discrepancies" — treat this file and the source tree as the source of truth
over marketing copy.

D-CIP is an investigation-case management platform: cases hold evidence files,
evidence is processed by an async pipeline (metadata → OCR → entity/keyword
extraction → timeline extraction → search indexing → optional AI summary),
extracted intelligence feeds a per-case AI chat assistant, a timeline, a
relationship graph, and a report generator. RBAC is enforced server-side on
every route.

---

## 1. Monorepo layout

pnpm + Turborepo (JS/TS side) and `uv` (Python side), unified by a root
`Makefile` and orchestrated at runtime by Docker Compose (`dev`/`prod`
profiles).

```
apps/
  web/     React 19 + Vite 5 SPA
  api/     FastAPI backend (routes → services → repositories → models)
  worker/  Celery worker container (reuses apps/api's code — see §9.2)
packages/
  types/   @dcip/types  — canonical roles.ts / permissions.ts / API envelope types
  shared/  @dcip/shared — RBAC matrix (mirrors backend), constants, utils
  ui/      @dcip/ui     — design tokens, Tailwind preset, cn()
  config/  @dcip/config — shared tsconfig + ESLint
database/  postgres/init (extensions only), neo4j/ + opensearch/ (connection config, no schema)
infrastructure/
  docker/  docker-compose.yml (dev + prod profiles)
  nginx/   edge proxy (prod) + SPA-serving config (baked into web image)
```

---

## 2. System diagram (as implemented)

```
React 19 SPA ──HTTPS, httpOnly cookies──▶ FastAPI (18 route modules, ~110 endpoints)
                                              │  routes → services → repositories → models
                          ┌───────────────────┼───────────────┬─────────────────┐
                     PostgreSQL            Redis           Neo4j            OpenSearch
                  (system of record,   (Celery broker/   (driver +        (1 index,
                   29ish models,        result backend,   health-check     dcip_evidence,
                   9 migrations)        rate-limit         only — no       opt-in via
                                        storage)            graph code     OPENSEARCH_ENABLED)
                                                             writes it)
                                              │
                                        Celery worker (apps/api/app/worker)
                                        process_evidence → ProcessingPipeline
                                        watchlist.match_evidence → WatchlistMatchingEngine
```

Redis is used for three distinct, non-overlapping purposes via separate DB
indices in compose: DB1 = Celery broker, DB2 = Celery result backend, DB3 =
rate-limit storage. It is **not** used for HTTP response caching or sessions —
sessions live in Postgres (`user_sessions` table).

---

## 3. Backend (`apps/api`)

### 3.1 Layering

Strict separation, enforced by convention not framework magic:

- **Routes** (`app/api/v1/routes/*.py`) — thin HTTP handlers; Pydantic
  validation; permission dependency declared at the function signature.
- **Services** (`app/services/*.py`) — business logic, orchestrate one or more
  repositories. `BaseService` is a thin constructor-injects-`Session` base.
- **Repositories** (`app/repositories/*.py`) — data access over SQLAlchemy
  models. `BaseRepository[ModelType]` gives `get`/`list`/`add`/`delete`;
  concrete repos add query methods.
- **Models** (`app/models/*.py`) — SQLAlchemy 2.x ORM classes, one file per
  model, all registered in `app/models/__init__.py` for Alembic autogenerate.
- **Core** (`app/core/`) — config (`config.py`), JWT/password (`security/`),
  RBAC dependency (`dependencies.py`), rate limiting (`rate_limit.py`),
  middleware, exceptions.
- **DB** (`app/db/`) — Postgres session factory + Neo4j/Redis/OpenSearch
  client factories.

### 3.2 Config & startup (`app/core/config.py`, `app/main.py`)

Pydantic `Settings` singleton (`get_settings()`, `lru_cache`d), loaded from
`.env`. `create_app()` is a factory (fresh instance per test). Middleware
stack outermost→innermost: `SlowAPIMiddleware` → `SecurityHeadersMiddleware` →
`RequestContextMiddleware` → `CORSMiddleware`.

**Production guard**: a `model_validator` refuses to boot if
`DCIP_ENV=production` and either `secret_key` is still the placeholder value
or `auth_cookie_secure` is false. `/docs`, `/redoc`, and the OpenAPI JSON route
are disabled outside non-production environments.

### 3.3 Auth & sessions

- JWT access tokens (HS256, 15 min, **always** — `remember_me` never extends
  the access token) + rotating refresh tokens, both delivered as httpOnly
  cookies. `remember_me` only extends the refresh-token/cookie lifetime (7d →
  30d).
- `AuthService.login()` (`app/services/auth.py`) checks active/not-locked,
  verifies bcrypt password, tracks `failed_login_attempts`, locks the account
  for 15 min after 5 failures, transparently rehashes weak hashes, issues
  token pair, writes a `UserSession` row (separate table from the refresh
  JWT) and an `AuthAuditEvent`.
- `refresh()` decodes the refresh JWT, looks up the persisted `RefreshToken`
  by `jti`, and **rotates** it (revoke old, issue new) — reuse of a revoked
  token is detectable.
- Token extraction (`app/core/dependencies.py`) reads the `access_token`
  cookie first, falls back to `Authorization: Bearer`.
- Password reset: token hashed with SHA-256, 60 min expiry, revokes all
  refresh tokens + sessions on successful reset. Dev mode logs the reset token
  instead of emailing it — no SMTP wiring exists yet.

### 3.4 RBAC

- Permissions are `resource:action` strings (`case:read`, `evidence:upload`,
  `admin:write`, etc.) — 21 defined in `packages/types/src/permissions.ts`,
  seeded into Postgres by migration 0001 and extended by later migrations
  (`timeline:*` in 0005, `report:write`/`report:publish` in 0006,
  `admin:read`/`admin:write` in 0007, `watchlist:*`/`alert:*` in 0008).
- Single matrix (`packages/shared/src/rbac.ts`) mirrored exactly by the
  Alembic seed data — **not** derived at runtime; if the matrix changes, both
  the TS file and a new migration must be updated by hand.
- 5 roles, explicit (not hierarchical/inherited) grants: Administrator (all
  permissions), Senior Investigator, Investigator, Analyst, Read Only.
- Enforcement: `RequirePermission(permission: str)` (`app/core/
  dependencies.py`) is a FastAPI dependency factory checked against
  `User.permissions` (a computed property flattening all assigned roles'
  permissions). Declared per-route, e.g. `Depends(RequirePermission
  ("evidence:read"))` — not global middleware.
- **Frontend RBAC is UI-gating only.** `useHasPermission`/`PermissionGuard`
  hide nav items and page elements; there is no route-level permission guard
  in the router (only an auth guard). A user who navigates directly to a URL
  they lack permission for relies entirely on the backend 403 — this is by
  design (server is the real boundary) but means pages must handle a 403
  response gracefully.

### 3.5 Middleware, errors, rate limiting

- `RequestContextMiddleware` — generates/propagates `X-Request-ID` and
  `X-Correlation-ID`, structured access-log line per request.
- `SecurityHeadersMiddleware` — `X-Content-Type-Options`, `X-Frame-Options:
  DENY`, `Referrer-Policy`, CSP (same-origin), `Permissions-Policy`,
  `WWW-Authenticate: Bearer` on 401.
- All domain exceptions (`NotFoundError`, `ConflictError`, `ValidationError`,
  `PermissionDeniedError`, `AuthenticationError`) funnel through one handler
  emitting `{"error": {"code", "message", "details", "request_id"}}`.
- `slowapi.Limiter`, default `120/min` globally, `10/min` on login, `5/min` on
  forgot-password. Storage is `memory://` by default (in-process — **not**
  safe for multi-worker deployments unless `RATE_LIMIT_STORAGE_URI` points at
  Redis, which prod compose does).

---

## 4. Data model (PostgreSQL)

System of record. 9 linear Alembic migrations (`0001`…`0009`, no branches),
~29 mapped SQLAlchemy classes (count varies 28–30 depending how the two
association `Table` objects are counted — not worth over-indexing on the
exact number). All PKs are `UUID` except `system_config` (string PK `key`).
FK `ondelete` convention: `CASCADE` for parent-owns-child, `RESTRICT` for
"created/uploaded/generated by" audit columns, `SET NULL` for optional actor
references.

| Migration | Adds |
|---|---|
| 0001 | Identity/RBAC: `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `refresh_tokens`, `password_reset_tokens`, `user_sessions`, `auth_audit_events`. Seeds 5 roles, 16 permissions, full grant matrix, default admin (`admin@dcip.local`). |
| 0002 | Cases: `cases`, `case_assignments`, `case_activities`, `case_tasks`, `case_notes`. |
| 0003 | Evidence: `evidence`, `evidence_custody_events`. |
| 0004 | AI/NLP extraction: `evidence_entities`, `evidence_keywords`, `evidence_timeline_events`, `evidence_summaries`, `case_summaries`, `ai_chat_messages`. |
| 0005 | Curated timeline: `timeline_events` (self-referencing merge via `merged_into_id`), `timeline_event_comments`. Seeds `timeline:*` permissions. |
| 0006 | Reports: `investigation_reports` (self-referencing version chain via `parent_report_id`), `report_exports`. Seeds `report:write`/`report:publish`. |
| 0007 | `system_config` (key/value, 15 seeded defaults incl. `ai_enabled=false`, `opensearch_enabled=false`). Seeds `admin:read`/`admin:write`. |
| 0008 | Watchlists/alerts: `watchlists`, `watchlist_entries`, `watchlist_alerts`, `alert_notifications`. Seeds `watchlist:*`/`alert:*`. |
| 0009 | Pure performance indexes — no schema change (`case_assignments.user_id`, `cases.deleted_at`, `users.deleted_at`, `case_activities.created_at`). |

Postgres init (`database/postgres/init/01-extensions.sql`) only enables
`uuid-ossp`, `pgcrypto`, `pg_trgm` — Alembic owns 100% of the schema, no
tables/roles are created outside it.

`Evidence.status` is an 11-value enum
(`UPLOADED, HASHING, METADATA_EXTRACTION, OCR_QUEUE, AI_QUEUE,
TIMELINE_QUEUE, GRAPH_QUEUE, INDEXED, COMPLETED, FAILED, CANCELLED`) — see
§5 for which of these are actually reachable in practice.

---

## 5. Evidence processing pipeline

### 5.1 Upload (synchronous, `POST /cases/{case_id}/evidence`)

`evidence.py` route streams the upload to disk in 64KB chunks while computing
SHA-256 incrementally (`_stream_to_disk`) — never buffers the whole file in
memory; a 500MB cap is enforced mid-stream (partial file deleted on abort).
`EvidenceService.record_upload()` then:

1. Deduplicates by SHA-256 **within the case** — a repeat upload returns the
   existing record (`is_new=False`) and the just-written duplicate file is
   deleted.
2. Creates the `Evidence` row, writes a chain-of-custody `UPLOADED` event.
3. Sets status to `OCR_QUEUE` as a holding state, commits, **then** dispatches
   the Celery task (deliberately after commit, to avoid the worker reading a
   row that doesn't exist yet).

### 5.2 Async pipeline (`app/services/processing_pipeline.py`, driven by Celery
task `process_evidence` in `app/worker/tasks/evidence.py`)

Actual stage order, each stage independently try/excepted (a failure in one
stage logs a warning and the pipeline continues; only a top-level exception
sets `FAILED`):

1. **`METADATA_EXTRACTION`** — EXIF/GPS for images.
2. **`OCR_QUEUE`** — native text extraction first (PDF text layer,
   DOCX/XLSX/EML/plaintext via `text_extraction.py`); Tesseract OCR fallback
   (`ocr.py`) for images or text-less PDFs, gated by `OCR_ENABLED`. PDF OCR
   only rasterizes embedded image XObjects (typical scanner output), not full
   vector-page rendering — there is no `pdf2image`/poppler dependency.
3. **`AI_QUEUE`** — despite the name, this is **not** the LLM call: regex +
   optional spaCy entity extraction (`entity_extraction.py`, capped
   1000/evidence) and TF-based keyword extraction (`keyword_extraction.py`,
   capped 30), then fire-and-forget dispatches the separate
   `watchlist.match_evidence` Celery task.
4. **`TIMELINE_QUEUE`** — regex-based date/event detection
   (`timeline_extraction.py`, capped 200 events), mirrored idempotently into
   the canonical `timeline_events` table via `TimelineService
   .ingest_from_extraction`.
5. **`GRAPH_QUEUE`** — status flag only; **no code runs in this stage** (see
   §7).
6. **`INDEXED`** — pushes filename/text/entities/keywords into OpenSearch if
   `OPENSEARCH_ENABLED`.
7. Unlabeled final step — optional LLM evidence summary (`ai_provider
   .generate_evidence_summary`) written to `evidence_summaries` if AI is
   configured.
8. **`COMPLETED`** — `processing_completed_at` set, `extracted_metadata`
   persisted, commit.

`EvidenceStatus.HASHING` is defined in the enum but never assigned anywhere —
hashing genuinely happens (during upload streaming), just without ever being
reflected as a distinct DB status.

### 5.3 Watchlist matching (`app/services/watchlist_matching.py`, its own
Celery task `watchlist.match_evidence`)

Runs three independent passes over the entities just extracted for one
evidence item: (1) exact/regex match against active `watchlist_entries`
(global or case-scoped), with `crypto_wallet`/`bank_account`/`sha256`/`md5`
matches always escalated to CRITICAL severity; (2) repeated-appearance check
(same entity in ≥3 evidence items in one case); (3) cross-case match
(deliberately RBAC-blind at match time — RBAC is enforced when results are
later read via the API, not during matching). Matches become `WatchlistAlert`
rows and fan out `AlertNotification`s to case members.

---

## 6. AI subsystem

### 6.1 Provider abstraction (`app/services/ai_provider.py`)

Wraps the `openai` SDK behind `AI_PROVIDER=none|openai|ollama`. `none` (the
default) short-circuits `_get_client()` to `(None, None)` with no network call
attempted; `ollama` is just the same OpenAI-compatible client pointed at a
local Ollama base URL, not a separate integration. Every public function
(`generate_evidence_summary`, `generate_case_summary`, `chat`,
`generate_timeline_analysis`, `parse_document_for_case`) checks
`if not client: return None` immediately, so nothing in the app hard-depends
on AI being configured — verified end-to-end: pipeline still reaches
`COMPLETED` without a summary, case-summary regeneration is a no-op, and chat
falls back to a hardcoded "AI is not configured..." message that is still
persisted as a normal `AiChatMessage` row.

### 6.2 Grounding / citation enforcement

Enforced entirely through a shared system prompt injected on every call
("Only use information from the provided evidence context... Always cite...
If insufficient, say 'I don't have enough evidence to answer this'... Never
speculate... scoped to a single case"). This is **prompt engineering, not a
code-level verification step** — there is no output-side check that a claimed
citation actually appears in the cited evidence, no retrieval scoring.
Compliance depends on the model obeying instructions.

### 6.3 Chat context — recency-based, not vector RAG

`AIIntelligenceService.chat()` queries the 20 most-recently-created
`COMPLETED` evidence rows for the case (`ORDER BY created_at DESC LIMIT 20`),
truncates each to 2000 chars, and stuffs up to 10 into the prompt as raw text.
There is no embedding similarity search or relevance ranking selecting
*which* evidence goes into context — it's recency plus a hard cap.
`generate_embeddings()` exists in `ai_provider.py` but has no caller anywhere
in the codebase — embeddings/semantic retrieval are stubbed, not wired in.

### 6.4 Timeline narrative

Deterministic analysis (`timeline_analysis.py` — gap/conflict/duplicate/
cluster detection, pure and dependency-free) runs regardless of AI
configuration. An optional LLM narrative layer
(`ai_provider.generate_timeline_analysis`) is explicitly instructed not to
introduce any event not already in the deterministic findings.

---

## 7. Knowledge graph — Neo4j is not currently load-bearing

Neo4j is deployed in `docker-compose.yml` and health-checked in four places
(`health.py` readiness probe, `main.py` shutdown, `admin_service.py` and
`dashboard_service.py` health tiles) — **all four uses are connectivity pings
only** (`driver.verify_connectivity()`). There are no Cypher `CREATE`/`MERGE`/
`MATCH` queries anywhere in the codebase, and the `GRAPH_QUEUE` pipeline stage
that would presumably populate it is an empty status flag.

The relationship graph actually served to the frontend
(`GET /cases/{id}/ai/graph`, rendered via React Flow in the case workspace's
Graph tab) comes from `AIIntelligenceService.get_relationship_graph()`, which
builds an **entity co-occurrence graph entirely from Postgres**: nodes from
deduped `EvidenceEntity` rows, edges from counting how many evidence items two
entities co-occur in. This is graph-shaped output computed with an in-memory
pass over SQL rows, not a graph-database query. If you're asked to extend "the
knowledge graph," decide explicitly whether to wire Neo4j in for real or
continue building on the Postgres co-occurrence approach — don't assume Neo4j
already backs anything.

---

## 8. Search

Single OpenSearch index, `dcip_evidence` (`app/services/opensearch_service
.py`), gated end-to-end by `OPENSEARCH_ENABLED` (default `false`) — every
call no-ops gracefully (returns `False`/`[]`, logs) when disabled or
unreachable. Mapping: `evidence_id`/`case_id`/`mime_type`/`status` (keyword),
`filename`/`text_content`/`entities` (text, standard analyzer), `keywords`
(keyword), `created_at` (date). `search()` is a `multi_match` across
`filename^2, text_content, entities, keywords` with highlighting — lexical
(BM25-style) search, not semantic/vector search. `database/opensearch/
index-templates/` on disk is an empty placeholder; the real mapping lives in
the service code.

`SearchService` (universal Ctrl+K search) is a separate, broader concern:
queries cases, evidence (filename + OCR text), AI summaries, entities,
keywords, timeline events, notes, tasks, and users directly from Postgres,
RBAC-filtered to accessible cases — it does not depend on OpenSearch being
enabled.

---

## 9. Frontend (`apps/web/src`)

### 9.1 Composition & routing

Two-tier provider layering in `App.tsx`: non-router providers
(`ThemeProvider`, `QueryProvider`, `AuthProvider`, etc.) sit above
`RouterProvider` so public routes get them too; router-aware providers
(`CommandPaletteProvider`, needs `useNavigate`) sit inside, wrapping
`AppLayout`. All authenticated pages are `React.lazy()`-loaded behind one
shared `Suspense`/`RouteErrorBoundary` (`LazyLayout`); auth pages and 404 are
eager. Route guarding is auth-only (`ProtectedRoute`) — no per-route
permission check (see §3.4). `src/features/` and `src/app/` exist as empty
directories — not part of the actual architecture.

39 page components under `src/pages/` (top-level pages, `auth/`, `cases/`
case-workspace tabs, `admin/` 8 modules, `profile/`).

### 9.2 Data layer

- `src/lib/api-client.ts` — single `apiFetch<T>()` wrapper over native
  `fetch`, `credentials: 'include'` (cookie auth, no manual bearer-token
  handling), throws a typed `ApiRequestError` on non-2xx matching the shared
  `ApiError` envelope. No axios, no interceptor chain.
- `src/lib/query-client.ts` — TanStack Query v5, 30s stale time, retries
  transient failures up to 2x but never retries 4xx.
- 13 domain API modules (`src/lib/api/*.ts`) and 12 domain hook files
  (`src/hooks/*.ts`), one per module: cases, evidence, dashboard, search,
  watchlist (also covers alerts + notifications), reports, roles, users,
  sessions, admin, ai, auth. Newer/larger hook files use a key-factory object
  pattern (`xKeys.all/list()/detail()`); older ones use inline array
  literals — inconsistent but not broken.
- Type duplication: `apps/web/src/types/*.ts` are hand-written and
  independently maintained from `packages/types` — only `lib/api-client.ts`
  and `config/navigation.ts` actually import from `@dcip/types`. Drift risk if
  backend contracts change without updating both places.

### 9.3 Notable components

- **Command palette (Ctrl+K)** — `CommandPaletteProvider`, static nav
  commands + live `useSearchSuggestions` results, global keydown listener.
- **Graph tab** (`pages/cases/graph-tab.tsx`) — React Flow (`@xyflow/react`),
  circular-sector layout grouped by entity type, fed by
  `useRelationshipGraph(caseId)` → the Postgres co-occurrence endpoint (§7).
  The top-level `/graph` route is a separate, still-empty placeholder page —
  the working graph only exists inside a case workspace.
- **Report builder** — 4-step wizard dialog (type → template → sections →
  confirm).
- **Dashboards** — Chart.js-backed `ChartBar`/`ChartLine`/`ChartPie` +
  `StatCard`/`HealthBadge`/`Heatmap`, composing 4 dashboard variants
  (executive/intelligence/operations/investigator) plus several admin pages.

---

## 10. Infrastructure

`infrastructure/docker/docker-compose.yml` — services: `postgres` (16-alpine),
`redis` (7-alpine, AOF persistence), `neo4j` (5-community), `opensearch`
(2.17.1, single-node, security plugin disabled), `api`, `worker` (shares the
`api` Dockerfile/codebase — see below), `web`, and `proxy` (nginx, **prod
profile only**). Named volumes for all datastores plus `evidence-uploads`
(shared between `api` and `worker` containers). The API container's
`entrypoint.sh` runs `alembic upgrade head` before `uvicorn` on every start.

**Worker note**: `apps/worker/` contains a stub `tasks/evidence.py` left over
from an early milestone (broken import path `apps.worker.celery_app`, empty
task body) that is **not** what actually runs. The real worker container
(`apps/worker/Dockerfile`) runs `celery -A app.worker.celery_app worker`,
i.e. it reuses `apps/api`'s codebase — the live task is
`apps/api/app/worker/tasks/evidence.py`. Don't edit `apps/worker/tasks/` and
expect it to take effect; it's dead code that should eventually be deleted.

NGINX has two independent configs: the prod-profile edge proxy
(`nginx.conf`/`conf.d/default.conf`, unifies web+API behind one origin so
cookies stay first-party and CORS is avoided) and `web.conf` (baked into the
web image, serves the built SPA with immutable asset caching + `no-cache` on
`index.html`). Neither config terminates TLS — HTTPS would need to be added
externally.

---

## 11. Testing

Backend: 33 files, ~428 tests (verified by running `pytest --collect-only`;
README's "302 across 38" is stale). **Every test mocks the SQLAlchemy
`Session` directly** (`unittest.mock.MagicMock`) and, for route-layer
integration tests, overrides the `_get_current_user` FastAPI dependency with a
fake user — there is no real database, no SQLite/testcontainers layer, in
either the `unit/` or `integration/` tier. The distinction is "service tests
with a mocked session" vs. "route tests through `TestClient` with a mocked
session/mocked auth," not fidelity level. `processing_pipeline.py` (the
orchestrator itself) and `opensearch_service.py` show 0% coverage — only
their constituent sub-services are unit-tested in isolation.

Frontend: 3 Vitest files / 6 tests (auth-gating + one shared header
component) + 1 Playwright file / 2 smoke tests (app shell loads, 404 works) —
against 147 source files. No coverage of evidence upload, AI chat, timeline,
graph, watchlists, reports, or admin UI.

---

## 12. Known discrepancies (docs/marketing vs. code — trust the code)

- **Neo4j is provisioned and health-checked but never written to or queried**
  for actual graph data (§7). The "knowledge graph" feature is a Postgres
  co-occurrence computation.
- **Test counts are stale in README** (302/38 claimed vs. 428/33 actual).
- **`apps/worker/tasks/evidence.py` is dead/orphaned code**; the real worker
  task lives in `apps/api/app/worker/tasks/evidence.py` (§10).
- **`EvidenceStatus.HASHING` is never assigned** despite being a defined enum
  value; hashing happens during upload streaming without that status label.
- **The "7-stage pipeline" README bullet undercounts reality** — actual
  stages include `INDEXED` (OpenSearch) which isn't mentioned, and
  `GRAPH_QUEUE` which does nothing (§5.2).
- **AI chat is not retrieval-augmented in the vector sense** — it's
  recency-ordered context stuffing; `generate_embeddings()` is dead code
  with no caller.
- **`docs/folder-structure.md` describes a pre-migrations, foundation-era
  state** ("no migrations yet," "no tables") — it predates the current
  schema by many milestones. Don't use it as a reference.
- **Frontend `NAVIGATION` config (`src/config/navigation.ts`) doesn't reflect
  the actual admin sidebar** — `AdminLayout` has more admin sections (System,
  Storage, AI, Audit, Security, Config) than the shared nav config lists.
- Model/route/table counts vary by ±1 across different enumeration passes
  (28–30 models, 18–19 route modules) — not worth chasing exactly; use
  §4/§3 as the structural reference rather than a specific number.

---

## 13. Non-negotiable invariants (per `docs/rc1-readiness.md`, still true)

1. Access tokens are always short-lived (15 min); `remember_me` only extends
   the refresh token.
2. RBAC is enforced server-side (`RequirePermission`) on every protected
   route — frontend gating is cosmetic only.
3. Evidence originals are immutable; deletion is always soft (tombstone +
   custody log entry), never physical.
4. Every AI response is persisted (`ai_chat_messages`), including the
   "AI is not configured" fallback.
5. `AUTH_COOKIE_SECURE=true` and a non-placeholder `SECRET_KEY` are enforced
   at startup in production — the app refuses to boot otherwise.
6. Never return data from one case to a user whose roles don't grant access
   to that case.
