"""User session schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.schemas.base import BaseSchema


class UserSessionRead(BaseSchema):
    id: uuid.UUID
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime
    is_active: bool
