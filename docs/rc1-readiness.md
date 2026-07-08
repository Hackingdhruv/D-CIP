# RC1 Readiness Assessment — D-CIP v0.1.0

**Date:** 2026-07-01  
**Assessed by:** Engineering RC1 audit pass  
**Test baseline:** 428 backend tests passing, TypeScript: 0 errors

---

## Summary verdict

**Status: RC1 READY — pending final production secrets + smoke test**

The platform is feature-complete through Milestone 10 (Enterprise Admin). All
critical security fixes from this pass are in place. The remaining gate is a
single manual smoke test with a real Docker Compose stack and production-style
environment variables (`DCIP_ENV=production`, a real `SECRET_KEY`,
`AUTH_COOKIE_SECURE=true`).

---

## Changes applied in this RC1 pass

### Security (critical — already shipped)

| Issue | Fix | File |
|---|---|---|
| Access tokens issued with 30-day expiry when remember_me=true | Access tokens always 15 min; remember_me only extends refresh token (30 d) | `app/services/auth.py` |
| `debug=True` default leaked stack traces and OpenAPI in production | Changed default to `False`; startup fails in production with placeholder `SECRET_KEY` or `AUTH_COOKIE_SECURE=false` | `app/core/config.py` |
| No Content-Security-Policy header | Added CSP + all baseline security headers; WWW-Authenticate on 401 | `app/core/middleware.py` |
| Evidence file size enforced after writing (wasted disk) | Size checked during streaming; partial file cleaned up on abort | `app/api/v1/routes/evidence.py` |

### Performance

| Issue | Fix | File |
|---|---|---|
| 1.3 MB single JS bundle | Route-level lazy loading via `React.lazy()` + `LazyLayout` Suspense wrapper | `apps/web/src/routes/index.tsx` |
| `_assert_can_view` triggered lazy load of `case.assignments` on every case fetch | Added `selectinload(Case.assignments)` to `CaseRepository.get_active` | `apps/api/app/repositories/case.py` |
| `assign_users` made one DB query per user to validate (N queries) | Added `UserRepository.get_many_active(ids)` for single batch query | `apps/api/app/repositories/user.py`, `app/services/case.py` |
| `case_assignments.user_id` unindexed (used in every case list subquery) | Migration 0009 adds index + `cases.deleted_at`, `users.deleted_at`, `case_activities.created_at` | `alembic/versions/0009_add_performance_indexes.py` |

### Reliability

| Issue | Fix | File |
|---|---|---|
| API container started without running migrations | Added `entrypoint.sh` that runs `alembic upgrade head` before uvicorn | `apps/api/entrypoint.sh`, `apps/api/Dockerfile` |
| Evidence files lost on container restart | Named volume `evidence-uploads` mounted on both `api` and `worker` containers | `infrastructure/docker/docker-compose.yml` |
| Rate limiter used in-memory storage in multi-worker Docker deployments | Wired `RATE_LIMIT_STORAGE_URI=redis://redis:6379/3` in docker-compose | `infrastructure/docker/docker-compose.yml` |

### UX

| Issue | Fix | File |
|---|---|---|
| Root ErrorBoundary caused full-page takeover for any route error | Added `RouteErrorBoundary` (inline, keeps app shell) wrapping `LazyLayout` | `apps/web/src/components/common/error-boundary.tsx`, `routes/index.tsx` |

### Accessibility

| Issue | Fix | File |
|---|---|---|
| "Forgot password" link removed from keyboard tab order | Removed `tabIndex={-1}` | `pages/auth/login-page.tsx` |
| Password toggle removed from keyboard tab order | Removed `tabIndex={-1}`, added `aria-pressed` | `pages/auth/login-page.tsx` |
| Command palette trigger had no ARIA label | Added `aria-label="Open command palette (Ctrl+K)"` | `components/layout/top-nav.tsx` |
| Notification bell count not read by screen readers | Badge marked `aria-hidden`; count moved into button `aria-label` | `components/layout/top-nav.tsx` |
| Sidebar `<aside>` and `<nav>` had no landmark labels | Added `aria-label="Main sidebar"` and `aria-label="Main navigation"` | `components/layout/sidebar.tsx` |

### Documentation

| Item | File |
|---|---|
| `.env.example` missing AI, OCR, OpenSearch, upload config sections | `.env.example` |
| Architecture doc outdated (pre-RC1 provider architecture) | `docs/architecture.md` updated with provider layering, security model, deployment section |

---

## What is NOT in RC1 (by design)

- **Email delivery for password reset** — dev mode logs the token; production requires SMTP/transactional email wiring. Flag as post-RC1.
- **AI provider connected** — `AI_PROVIDER=none` by default. AI UI is built; set `AI_PROVIDER=openai` and `AI_API_KEY` to enable.
- **OpenSearch semantic search** — `OPENSEARCH_ENABLED=false` by default. Full-text indexing pipeline is built; opt-in when OpenSearch is provisioned.
- **Multi-organisation tenancy** — `organization_id` columns exist in the schema per ADR; row-level scoping enforcement is post-RC1.

---

## Pre-production checklist

Before cutting a production deployment:

- [ ] Generate `SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- [ ] Set `DCIP_ENV=production` and `AUTH_COOKIE_SECURE=true`
- [ ] Set `CORS_ORIGINS` to the real frontend domain
- [ ] Provision persistent volumes for `postgres-data`, `redis-data`, `neo4j-data`, `opensearch-data`, `evidence-uploads`
- [ ] Change default DB passwords from `dcip_dev_password`
- [ ] Change default Neo4j password from `dcip_neo4j_password`
- [ ] Change default OpenSearch password from `dcip_opensearch_password`
- [ ] Change default admin password (`admin@dcip.local / Admin@dcip.2024!`) on first login
- [ ] Set `LOG_FORMAT=json` and pipe to a log aggregator
- [ ] Set up NGINX TLS termination (reverse proxy config exists in `infrastructure/nginx/`)
- [ ] Configure SMTP for password reset emails (currently only logged in dev mode)
- [ ] Run `docker compose --profile prod up --build` and verify `/api/v1/health/ready` returns 200

---

## Security constraints (permanent — must survive all future changes)

These are non-negotiable invariants established at project inception:

1. Access tokens are always short-lived (15 min). `remember_me` only extends the refresh token.
2. Every AI finding must carry its model, prompt hash, and confidence. AI assists; it never decides.
3. Every AI output must be linked to supporting evidence. AI must say "I don't know" when evidence is insufficient.
4. Every AI response must be logged.
5. RBAC is enforced in both the route layer (RequirePermission) and the service layer. Never return data the user's roles don't allow.
6. Evidence originals are immutable; chain of custody is an append-only log.
7. Never return data from one case to a user whose roles don't include access to that case.
8. `AUTH_COOKIE_SECURE=true` is enforced at startup in production. The app will refuse to start without it.
9. `SECRET_KEY` must not be the placeholder value in production. The app will refuse to start.
