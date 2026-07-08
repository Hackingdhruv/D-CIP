"""Audit event repository."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select

from app.models.auth_audit_event import AuthAuditEvent
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuthAuditEvent]):
    model = AuthAuditEvent

    def log(
        self,
        event_type: str,
        *,
        user_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuthAuditEvent:
        event = AuthAuditEvent(
            event_type=event_type,
            user_id=user_id,
            actor_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_=metadata,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def search(
        self,
        *,
        user_id: uuid.UUID | None = None,
        event_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuthAuditEvent], int]:
        base = select(AuthAuditEvent)
        if user_id:
            base = base.where(AuthAuditEvent.user_id == user_id)
        if event_type:
            base = base.where(AuthAuditEvent.event_type == event_type)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        offset = (page - 1) * page_size
        stmt = base.order_by(AuthAuditEvent.created_at.desc()).offset(offset).limit(page_size)
        items = list(self.session.execute(stmt).scalars().all())
        return items, total
