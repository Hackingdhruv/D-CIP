"""Permission schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.schemas.base import BaseSchema


class PermissionRead(BaseSchema):
    id: uuid.UUID
    resource: str
    action: str
    description: str | None
    codename: str
    created_at: datetime
