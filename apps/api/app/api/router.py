"""Aggregates all versioned API routers into a single router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import health, version
from app.api.v1.routes import (
    admin,
    ai,
    alerts,
    auth,
    cases,
    dashboard,
    evidence,
    notifications,
    permissions,
    profile,
    reports,
    roles,
    search,
    timeline,
    users,
    watchlists,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(version.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(cases.router)
api_router.include_router(evidence.router)
api_router.include_router(timeline.router)
api_router.include_router(ai.router)
api_router.include_router(search.router)
api_router.include_router(reports.router)
api_router.include_router(dashboard.router)
api_router.include_router(admin.router)
api_router.include_router(watchlists.router)
api_router.include_router(alerts.router)
api_router.include_router(notifications.router)
