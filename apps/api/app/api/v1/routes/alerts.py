"""Watchlist Alert management API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import RequirePermission, SessionDep
from app.models.user import User
from app.schemas.watchlist import (
    AlertStats,
    WatchlistAlertListResponse,
    WatchlistAlertRead,
)
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])

_READ = RequirePermission("alert:read")
_WRITE = RequirePermission("alert:write")


@router.get("/stats", response_model=AlertStats)
def get_stats(
    session: SessionDep,
    case_id: uuid.UUID | None = Query(None),
    current_user: User = _READ,
) -> AlertStats:
    return AlertService(session, current_user).get_stats(case_id=case_id)


@router.get("", response_model=WatchlistAlertListResponse)
def list_alerts(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    case_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    severity: str | None = Query(None),
    alert_type: str | None = Query(None),
    is_cross_case: bool | None = Query(None),
    current_user: User = _READ,
) -> WatchlistAlertListResponse:
    return AlertService(session, current_user).list_alerts(
        page=page,
        page_size=page_size,
        case_id=case_id,
        status=status,
        severity=severity,
        alert_type=alert_type,
        is_cross_case=is_cross_case,
    )


@router.get("/{alert_id}", response_model=WatchlistAlertRead)
def get_alert(
    alert_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> WatchlistAlertRead:
    return AlertService(session, current_user).get_alert(alert_id)


@router.post("/{alert_id}/acknowledge", response_model=WatchlistAlertRead)
def acknowledge_alert(
    alert_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _WRITE,
) -> WatchlistAlertRead:
    svc = AlertService(session, current_user)
    result = svc.acknowledge(alert_id)
    session.commit()
    return result


@router.post("/{alert_id}/resolve", response_model=WatchlistAlertRead)
def resolve_alert(
    alert_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _WRITE,
) -> WatchlistAlertRead:
    svc = AlertService(session, current_user)
    result = svc.resolve(alert_id)
    session.commit()
    return result


@router.post("/{alert_id}/dismiss", response_model=WatchlistAlertRead)
def dismiss_alert(
    alert_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _WRITE,
) -> WatchlistAlertRead:
    svc = AlertService(session, current_user)
    result = svc.dismiss(alert_id)
    session.commit()
    return result
