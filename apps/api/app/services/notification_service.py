"""NotificationService — server-backed AlertNotification feed."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alert_notification import AlertNotification
from app.models.case_assignment import CaseAssignment
from app.models.user import User
from app.models.watchlist_alert import WatchlistAlert
from app.schemas.watchlist import (
    AlertNotificationRead,
    NotificationCount,
    NotificationListResponse,
)


def _get_case_members(case_id: uuid.UUID, db: Session) -> list[uuid.UUID]:
    """Return user IDs of the case owner + all assigned users."""
    from app.models.case import Case
    case = db.get(Case, case_id)
    members: set[uuid.UUID] = set()
    if case and case.owner_id:
        members.add(case.owner_id)
    rows = db.execute(
        select(CaseAssignment.user_id).where(CaseAssignment.case_id == case_id)
    ).scalars()
    members.update(rows)
    return list(members)


class NotificationService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    # ── Fan-out notifications after alerts are created ────────────────────────

    @staticmethod
    def fan_out(
        db: Session,
        alert: WatchlistAlert,
    ) -> None:
        """Create per-user notifications for all case members."""
        recipients = _get_case_members(alert.case_id, db)
        level = _alert_level(alert.severity)
        for uid in recipients:
            notif = AlertNotification(
                user_id=uid,
                alert_id=alert.id,
                case_id=alert.case_id,
                title=alert.title[:500],
                message=alert.description,
                level=level,
            )
            db.add(notif)

    # ── User-facing queries ───────────────────────────────────────────────────

    def list_notifications(
        self,
        page: int = 1,
        page_size: int = 30,
        unread_only: bool = False,
        include_archived: bool = False,
    ) -> NotificationListResponse:
        stmt = select(AlertNotification).where(
            AlertNotification.user_id == self.user.id
        )
        if unread_only:
            stmt = stmt.where(AlertNotification.is_read.is_(False))
        if not include_archived:
            stmt = stmt.where(AlertNotification.is_archived.is_(False))

        total = self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        unread = self.db.execute(
            select(func.count(AlertNotification.id)).where(
                AlertNotification.user_id == self.user.id,
                AlertNotification.is_read.is_(False),
                AlertNotification.is_archived.is_(False),
            )
        ).scalar_one()

        items = self.db.execute(
            stmt.order_by(AlertNotification.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).scalars().all()

        return NotificationListResponse(
            items=[AlertNotificationRead.model_validate(n) for n in items],
            total=total,
            unread_count=unread,
        )

    def get_count(self) -> NotificationCount:
        unread = self.db.execute(
            select(func.count(AlertNotification.id)).where(
                AlertNotification.user_id == self.user.id,
                AlertNotification.is_read.is_(False),
                AlertNotification.is_archived.is_(False),
            )
        ).scalar_one()
        return NotificationCount(unread_count=unread)

    def mark_read(self, notification_id: uuid.UUID) -> None:
        notif = self._get_own(notification_id)
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            self.db.flush()

    def mark_all_read(self) -> int:
        rows = self.db.execute(
            select(AlertNotification).where(
                AlertNotification.user_id == self.user.id,
                AlertNotification.is_read.is_(False),
            )
        ).scalars().all()
        now = datetime.now(timezone.utc)
        for n in rows:
            n.is_read = True
            n.read_at = now
        self.db.flush()
        return len(rows)

    def archive(self, notification_id: uuid.UUID) -> None:
        notif = self._get_own(notification_id)
        notif.is_archived = True
        self.db.flush()

    def delete(self, notification_id: uuid.UUID) -> None:
        notif = self._get_own(notification_id)
        self.db.delete(notif)
        self.db.flush()

    def _get_own(self, notification_id: uuid.UUID) -> AlertNotification:
        notif = self.db.get(AlertNotification, notification_id)
        if notif is None or notif.user_id != self.user.id:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Notification not found")
        return notif


def _alert_level(severity: str) -> str:
    mapping = {
        "critical": "critical",
        "high": "error",
        "medium": "warning",
        "low": "info",
        "info": "info",
    }
    return mapping.get(severity, "info")
