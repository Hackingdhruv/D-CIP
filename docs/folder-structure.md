# Folder structure

> ⚠️ **Historical document.** This reflects the project's early foundation
> milestone, before the database migrations, most API routes, and most models
> existed. It's kept for history, not as a reference. For the current,
> accurate structure, see the [Project Structure section in
> README.md](../README.md#project-structure) or [`ARCHITECTURE.md`
> §1](../ARCHITECTURE.md#1-monorepo-layout).

```
dcip/
├── apps/
│   ├── web/                     React 19 + Vite SPA
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── ui/          shadcn/ui primitives
│   │   │   │   ├── layout/      app shell: sidebar, top nav, layout
│   │   │   │   ├── providers/   theme, query, modal, notifications, palette
│   │   │   │   └── common/      page header, empty state, loading, errors
│   │   │   ├── pages/           one component per section (empty, real copy)
│   │   │   ├── routes/          router configuration
│   │   │   ├── config/          env validation, navigation config
│   │   │   ├── lib/             api client, query client, utils
│   │   │   └── styles/          global stylesheet
│   │   └── tests/e2e/           Playwright specs
│   │
│   ├── api/                     FastAPI backend (Python 3.13)
│   │   ├── app/
│   │   │   ├── api/v1/routes/   health, version
│   │   │   ├── core/            config, logging, security, middleware, DI
│   │   │   ├── db/              SQLAlchemy + Neo4j/Redis/OpenSearch clients
│   │   │   ├── repositories/    repository-pattern base
│   │   │   ├── services/        service-layer base
│   │   │   ├── schemas/         Pydantic models
│   │   │   ├── worker/          Celery application
│   │   │   └── main.py          application factory
│   │   ├── alembic/             migration environment (no migrations yet)
│   │   └── tests/               pytest suite
│   │
│   └── worker/                  Celery worker image (reuses api code)
│
├── packages/
│   ├── config/                  shared tsconfig + ESLint configs
│   ├── types/                   shared TS types (roles, permissions, API)
│   ├── shared/                  RBAC matrix, constants, utilities
│   └── ui/                      design tokens, Tailwind preset, cn()
│
├── infrastructure/
│   ├── docker/                  docker-compose.yml (dev + prod profiles)
│   └── nginx/                   SPA server + edge reverse proxy configs
│
├── database/
│   ├── postgres/init/           extensions only (no tables)
│   ├── neo4j/                   connection config
│   └── opensearch/              connection config
│
├── docs/                        these guides
├── .github/workflows/           CI pipeline
├── package.json                 workspace root
├── pnpm-workspace.yaml
├── turbo.json
└── Makefile
```
