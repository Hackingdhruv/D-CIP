"""Schemas for the health/readiness endpoints."""

from __future__ import annotations

from typing import Literal

from app.schemas.base import BaseSchema


class ComponentCheck(BaseSchema):
    status: Literal["ok", "error"]
    detail: str | None = None


class HealthStatus(BaseSchema):
    status: Literal["ok", "degraded", "error"]
    checks: dict[str, ComponentCheck]
