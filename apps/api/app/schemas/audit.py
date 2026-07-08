"""Audit event schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.schemas.base import BaseSchema


class AuditEventRead(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    event_type: str
    ip_address: str | None
    user_agent: str | None
    metadata_: dict[str, Any] | None
    created_at: datetime


class AuditEventListResponse(BaseSchema):
    items: list[AuditEventRead]
    total: int
    page: int
    page_size: int
    pages: int
