# Architecture

D-CIP is a monorepo composed of three runnable applications (web, api, worker),
shared packages, and four backing datastores. This document describes the
foundation as built; feature subsystems (auth, cases, evidence, AI) are layered
on top in later milestones without changing these load-bearing decisions.

## High-level shape

```
                 ┌──────────── Browser ────────────┐
                 │   React 19 SPA (apps/web)        │
                 └───────────────┬─────────────────┘
                                 │  HTTPS  (/api)
                 ┌───────────────▼─────────────────┐
   NGINX edge →  │        FastAPI (apps/api)        │
                 │  routes · DI · services · repos  │
                 └───┬───────┬───────┬───────┬──────┘
                     │       │       │       │
              PostgreSQL  Redis   Neo4j   OpenSearch
             (system of  (cache, (graph) (search)
               record)   queue,
                         session)
                     ▲
                     │ broker
              ┌──────┴───────┐
              │ Celery worker│  (apps/worker)
              └──────────────┘
```

## Datastore responsibilities

| Store      | Role                                                         |
| ---------- | ----------------------------------------------------------- |
| PostgreSQL | System of record — all relational, transactional data.      |
| Neo4j      | Relationship graph — entities and the links between them.   |
| OpenSearch | Full-text and (later) semantic search.                      |
| Redis      | Cache, Celery broker/result backend, and session storage.   |

## Backend layering

The API follows a clean separation so business logic stays testable and
persistence concerns stay isolated:

- **Routes** (`app/api`) — thin HTTP handlers; validation via Pydantic schemas.
- **Dependencies** (`app/core/dependencies.py`) — inject settings, the database
  session, and clients.
- **Services** (`app/services`) — business logic; orchestrate repositories.
- **Repositories** (`app/repositories`) — data access over SQLAlchemy models.
- **Core** (`app/core`) — config, logging, security, middleware, exceptions.
- **DB** (`app/db`) — engine/session and the Neo4j/Redis/OpenSearch clients.

Cross-cutting concerns are middleware: a request-context middleware assigns a
request id and propagates a correlation id (both surfaced on every log line and
response header), and a security-headers middleware applies a conservative
baseline. Errors funnel through a single set of handlers that emit one stable
envelope shape.

## Architectural decisions (locked)

These were settled at project inception and carry through every milestone:

1. **Multi-tenancy.** Every future domain table carries an `organization_id`,
   enforced at the repository layer so tenant isolation can't be forgotten at a
   call site.
2. **Evidence integrity.** Evidence is hashed (SHA-256) on ingest; originals are
   stored immutably (append-only), derived artifacts are kept separately, and
   the chain of custody is an immutable log.
3. **RBAC.** Permissions are `resource:action` strings mapped to roles by a
   single matrix shared between backend enforcement and frontend UI gating
   (`packages/shared/src/rbac.ts`). Roles: Administrator, Senior Investigator,
   Investigator, Analyst, Read Only.
4. **Monorepo tooling.** pnpm workspaces + Turborepo for JS, uv for Python;
   TypeScript types for the API are generated from its OpenAPI schema.
5. **Auth tokens.** Short-lived access JWTs plus refresh tokens, delivered as
   httpOnly secure cookies, with Redis-backed revocation. (Utilities exist now;
   the login flow lands with the auth milestone.)
6. **AI provenance.** Every AI finding will carry its model, version,
   prompt hash, and confidence, and move through a review state machine
   (`suggested → accepted | rejected | edited`). AI assists; it never decides.

## Frontend composition

The web app is a single-page application built with React 19 + Vite 5.

**Provider layering** — two tiers of providers exist:
1. *Non-router providers* (ThemeProvider, QueryProvider, AuthProvider, etc.) are
   mounted **above** `<RouterProvider>` in `App.tsx` so they are available to
   every route including public ones.
2. *Router-aware providers* (CommandPaletteProvider, which calls `useNavigate`)
   are mounted **inside** the router tree, wrapping `<AppLayout />`.

**Route code splitting** — all page-level components are loaded via
`React.lazy()`. A `<LazyLayout>` component wraps `<Outlet />` in both a
`<Suspense>` boundary (spinner while chunks load) and a `<RouteErrorBoundary>`
(inline error fallback that keeps the app shell visible). Auth pages and 404 are
eagerly loaded as they are tiny and always needed.

**Design system** — design tokens, the Tailwind preset, and the `cn` helper live
in `packages/ui` so the visual language is defined in exactly one place.

## Security model

**Auth tokens** — access tokens are always short-lived (15 min) regardless of
remember_me. remember_me only extends the refresh token lifetime (7 days →
30 days). Tokens are delivered as httpOnly cookies; the `secure` flag is
enforced at boot when `DCIP_ENV=production`.

**Security headers** — every response carries a baseline set via
`SecurityHeadersMiddleware`: `X-Content-Type-Options: nosniff`, `X-Frame-Options:
DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, Content-Security-Policy
(same-origin), and `Permissions-Policy` disabling camera/mic/geo.

**Rate limiting** — slowapi limits are backed by Redis (`RATE_LIMIT_STORAGE_URI`)
so limits are shared across all API workers in a multi-process deployment.

**Evidence streaming** — uploaded files are streamed directly to disk while
computing SHA-256. File size is enforced byte-by-byte during streaming so an
oversized upload never lands on disk before rejection.

## Deployment

The API container runs `entrypoint.sh` on startup, which applies
`alembic upgrade head` before launching uvicorn. docker-compose waits for
postgres to be healthy before starting the API container, so migrations run
against a ready database on every container restart.

Evidence files are stored in a named Docker volume (`evidence-uploads`) shared
by the `api` and `worker` containers so uploaded files survive container
re-creation and are accessible for Celery processing.

## Shared packages

| Package         | Purpose                                                |
| --------------- | ------------------------------------------------------ |
| `@dcip/types`   | Roles, permissions, and API contract types.            |
| `@dcip/shared`  | RBAC matrix, constants, framework-agnostic utilities.  |
| `@dcip/ui`      | Design tokens, Tailwind preset, UI helpers.            |
| `@dcip/config`  | Shared TypeScript and ESLint configuration.            |
