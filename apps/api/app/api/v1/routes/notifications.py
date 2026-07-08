"""Notification API endpoints — server-backed feed for the current user."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import RequirePermission, SessionDep
from app.models.user import User
from app.schemas.watchlist import (
    AlertNotificationRead,
    NotificationCount,
    NotificationListResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Any authenticated user who has watchlist:read can see their own notifications
_AUTH = RequirePermission("watchlist:read")


@router.get("/count", response_model=NotificationCount)
def get_count(
    session: SessionDep,
    current_user: User = _AUTH,
) -> NotificationCount:
    return NotificationService(session, current_user).get_count()


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    unread_only: bool = Query(False),
    include_archived: bool = Query(False),
    current_user: User = _AUTH,
) -> NotificationListResponse:
    return NotificationService(session, current_user).list_notifications(
        page=page,
        page_size=page_size,
        unread_only=unread_only,
        include_archived=include_archived,
    )


@router.post("/{notification_id}/read", response_model=AlertNotificationRead)
def mark_read(
    notification_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _AUTH,
) -> AlertNotificationRead:
    svc = NotificationService(session, current_user)
    svc.mark_read(notification_id)
    session.commit()
    from app.models.alert_notification import AlertNotification
    notif = session.get(AlertNotification, notification_id)
    return AlertNotificationRead.model_validate(notif)


@router.post("/read-all")
def mark_all_read(
    session: SessionDep,
    current_user: User = _AUTH,
) -> dict:
    svc = NotificationService(session, current_user)
    count = svc.mark_all_read()
    session.commit()
    return {"marked_read": count}


@router.post("/{notification_id}/archive")
def archive_notification(
    notification_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _AUTH,
) -> dict:
    svc = NotificationService(session, current_user)
    svc.archive(notification_id)
    session.commit()
    return {"archived": True}


@router.delete("/{notification_id}", status_code=204)
def delete_notification(
    notification_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _AUTH,
) -> None:
    svc = NotificationService(session, current_user)
    svc.delete(notification_id)
    session.commit()
