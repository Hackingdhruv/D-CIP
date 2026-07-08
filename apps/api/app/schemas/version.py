"""Schema for the version endpoint."""

from __future__ import annotations

from app.schemas.base import BaseSchema


class VersionInfo(BaseSchema):
    name: str
    version: str
    environment: str
    commit: str | None = None
