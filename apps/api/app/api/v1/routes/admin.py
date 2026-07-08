"""Enterprise Administration API routes.

All endpoints require admin:read (GET) or admin:write (POST/PUT/DELETE).
Prefix: /admin  (main.py prepends /api/v1)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import RequirePermission, SessionDep
from app.models.user import User
from app.schemas.admin import (
    AdminOverviewStats,
    AdminUserListResponse,
    AdminUserRead,
    AiConfigRead,
    AiUsageStats,
    AuditSearchResponse,
    AuditStats,
    ConfigEntry,
    ConfigUpdateRequest,
    InviteUserRequest,
    LockUserRequest,
    RecommendationsResponse,
    SecurityOverview,
    SessionListResponse,
    StorageOverview,
    SystemHealthResponse,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin"])

_READ = RequirePermission("admin:read")
_WRITE = RequirePermission("admin:write")


# ── Overview ──────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=AdminOverviewStats)
def get_admin_stats(
    session: SessionDep,
    current_user: User = _READ,
) -> AdminOverviewStats:
    return AdminService(session, current_user).get_overview_stats()


# ── Identity Administration ───────────────────────────────────────────────────

@router.get("/users", response_model=AdminUserListResponse)
def list_admin_users(
    session: SessionDep,
    current_user: User = _READ,
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    is_locked: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> AdminUserListResponse:
    return AdminService(session, current_user).list_users(
        q=q, is_active=is_active, is_locked=is_locked, page=page, page_size=page_size
    )


@router.get("/users/{user_id}", response_model=AdminUserRead)
def get_admin_user(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> AdminUserRead:
    result = AdminService(session, current_user).get_user(user_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return result


@router.post("/users/{user_id}/lock", response_model=AdminUserRead)
def lock_user(
    user_id: uuid.UUID,
    body: LockUserRequest,
    session: SessionDep,
    current_user: User = _WRITE,
) -> AdminUserRead:
    result = AdminService(session, current_user).lock_user(
        user_id, reason=body.reason, duration_minutes=body.duration_minutes
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    session.commit()
    return result


@router.post("/users/{user_id}/unlock", response_model=AdminUserRead)
def unlock_user(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _WRITE,
) -> AdminUserRead:
    result = AdminService(session, current_user).unlock_user(user_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    session.commit()
    return result


@router.post("/users/invite", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED)
def invite_user(
    body: InviteUserRequest,
    session: SessionDep,
    current_user: User = _WRITE,
) -> AdminUserRead:
    result = AdminService(session, current_user).invite_user(
        email=body.email,
        full_name=body.full_name,
        username=body.username,
        temp_password=body.temp_password,
        role_ids=body.role_ids,
    )
    session.commit()
    return result


@router.post("/users/{user_id}/force-password-reset", status_code=status.HTTP_204_NO_CONTENT)
def force_password_reset(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _WRITE,
) -> None:
    ok = AdminService(session, current_user).force_password_reset(user_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    session.commit()


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(
    session: SessionDep,
    current_user: User = _READ,
    user_id: uuid.UUID | None = Query(default=None),
    is_active: bool | None = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> SessionListResponse:
    return AdminService(session, current_user).list_sessions(
        user_id=user_id, is_active=is_active, page=page, page_size=page_size
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    session_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _WRITE,
) -> None:
    ok = AdminService(session, current_user).revoke_session(session_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session.commit()


@router.delete("/users/{user_id}/sessions", status_code=status.HTTP_204_NO_CONTENT)
def revoke_user_sessions(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _WRITE,
) -> None:
    AdminService(session, current_user).revoke_all_user_sessions(user_id)
    session.commit()


# ── Audit Center ──────────────────────────────────────────────────────────────

@router.get("/audit", response_model=AuditSearchResponse)
def search_audit(
    session: SessionDep,
    current_user: User = _READ,
    q: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> AuditSearchResponse:
    return AdminService(session, current_user).search_audit(
        q=q,
        event_type=event_type,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/audit/stats", response_model=AuditStats)
def get_audit_stats(
    session: SessionDep,
    current_user: User = _READ,
) -> AuditStats:
    return AdminService(session, current_user).get_audit_stats()


# ── Security Center ───────────────────────────────────────────────────────────

@router.get("/security", response_model=SecurityOverview)
def get_security_overview(
    session: SessionDep,
    current_user: User = _READ,
) -> SecurityOverview:
    return AdminService(session, current_user).get_security_overview()


# ── System Operations Center ──────────────────────────────────────────────────

@router.get("/system/health", response_model=SystemHealthResponse)
def get_system_health(
    session: SessionDep,
    current_user: User = _READ,
) -> SystemHealthResponse:
    return AdminService(session, current_user).get_system_health()


@router.get("/system/recommendations", response_model=RecommendationsResponse)
def get_recommendations(
    session: SessionDep,
    current_user: User = _READ,
) -> RecommendationsResponse:
    return AdminService(session, current_user).get_recommendations()


# ── AI Administration ─────────────────────────────────────────────────────────

@router.get("/ai/config", response_model=AiConfigRead)
def get_ai_config(
    session: SessionDep,
    current_user: User = _READ,
) -> AiConfigRead:
    return AdminService(session, current_user).get_ai_config()


@router.get("/ai/stats", response_model=AiUsageStats)
def get_ai_stats(
    session: SessionDep,
    current_user: User = _READ,
) -> AiUsageStats:
    return AdminService(session, current_user).get_ai_usage_stats()


# ── Storage Center ────────────────────────────────────────────────────────────

@router.get("/storage", response_model=StorageOverview)
def get_storage_overview(
    session: SessionDep,
    current_user: User = _READ,
) -> StorageOverview:
    return AdminService(session, current_user).get_storage_overview()


# ── Configuration Center ──────────────────────────────────────────────────────

@router.get("/config", response_model=list[ConfigEntry])
def list_config(
    session: SessionDep,
    current_user: User = _READ,
) -> list[ConfigEntry]:
    return AdminService(session, current_user).list_config()


@router.get("/config/{key}", response_model=ConfigEntry)
def get_config(
    key: str,
    session: SessionDep,
    current_user: User = _READ,
) -> ConfigEntry:
    result = AdminService(session, current_user).get_config(key)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config key not found")
    return result


@router.put("/config/{key}", response_model=ConfigEntry)
def set_config(
    key: str,
    body: ConfigUpdateRequest,
    session: SessionDep,
    current_user: User = _WRITE,
) -> ConfigEntry:
    result = AdminService(session, current_user).set_config(key, body.value)
    session.commit()
    return result
