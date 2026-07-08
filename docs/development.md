# Developer setup

## Workspace overview

This is a pnpm + Turborepo monorepo for the JavaScript side and a uv-managed
project for the Python backend. Shared frontend logic lives in `packages/`.

## Common commands

Run from the repository root unless noted.

| Command           | What it does                                       |
| ----------------- | -------------------------------------------------- |
| `pnpm dev`        | Run dev tasks across the workspace (web on :5173)  |
| `pnpm build`      | Build all JS packages and the web app              |
| `pnpm lint`       | ESLint across the workspace                        |
| `pnpm typecheck`  | TypeScript checks across the workspace             |
| `pnpm test`       | Vitest unit tests                                  |
| `pnpm format`     | Prettier write                                     |

Backend (run inside `apps/api`):

| Command                              | What it does           |
| ------------------------------------ | ---------------------- |
| `uv run uvicorn app.main:app --reload` | Run the API with reload |
| `uv run pytest`                      | Tests with coverage    |
| `uv run ruff check .`                | Lint                   |
| `uv run black . && uv run isort .`   | Format                 |
| `uv run mypy app`                    | Type-check             |
| `uv run alembic upgrade head`        | Apply migrations       |

End-to-end (inside `apps/web`):

```bash
pnpm exec playwright install   # one-time browser download
pnpm test:e2e
```

## Code quality

- **TypeScript** — strict, with `noUncheckedIndexedAccess`. ESLint (flat config,
  shared from `@dcip/config`) and Prettier enforce style.
- **Python** — Ruff, Black, isort, and strict mypy. Config lives in
  `apps/api/pyproject.toml`.

Install the recommended VS Code extensions (`.vscode/extensions.json`) and copy
`.vscode/settings.recommended.json` to `.vscode/settings.json` for format-on-save.

## Adding a model and migration

1. Define a SQLAlchemy model that inherits `app.db.base.Base`.
2. Import it in `apps/api/alembic/env.py` so autogenerate sees it.
3. `uv run alembic revision --autogenerate -m "add <thing>"`.
4. Review the generated migration, then `uv run alembic upgrade head`.

## Conventions

- API routes are versioned under `/api/v1`.
- Every response includes `X-Request-ID` and `X-Correlation-ID`; pass an inbound
  `X-Correlation-ID` to trace a request across services.
- Frontend reads only `VITE_`-prefixed environment variables, validated in
  `apps/web/src/config/env.ts`.
