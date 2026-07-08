"""Watchlist, WatchlistEntry, WatchlistAlert, and AlertNotification schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import BaseSchema


# ── Watchlist ─────────────────────────────────────────────────────────────────

class WatchlistCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    watchlist_type: str
    is_active: bool = True
    case_id: uuid.UUID | None = None


class WatchlistUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    watchlist_type: str | None = None
    is_active: bool | None = None


class WatchlistRead(BaseSchema):
    id: uuid.UUID
    name: str
    description: str | None
    watchlist_type: str
    is_active: bool
    case_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    created_by_email: str | None = None
    entry_count: int = 0
    alert_count: int = 0
    created_at: datetime
    updated_at: datetime


class WatchlistListResponse(BaseSchema):
    items: list[WatchlistRead]
    total: int
    page: int
    pages: int


# ── WatchlistEntry ────────────────────────────────────────────────────────────

class WatchlistEntryCreate(BaseSchema):
    value: str = Field(..., min_length=1)
    is_regex: bool = False
    description: str | None = None


class WatchlistEntryUpdate(BaseSchema):
    value: str | None = Field(default=None, min_length=1)
    is_regex: bool | None = None
    description: str | None = None
    is_active: bool | None = None


class WatchlistEntryRead(BaseSchema):
    id: uuid.UUID
    watchlist_id: uuid.UUID
    value: str
    normalized_value: str
    is_regex: bool
    description: str | None
    is_active: bool
    hit_count: int
    created_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class WatchlistEntryListResponse(BaseSchema):
    items: list[WatchlistEntryRead]
    total: int


# ── WatchlistAlert ────────────────────────────────────────────────────────────

class WatchlistAlertRead(BaseSchema):
    id: uuid.UUID
    watchlist_id: uuid.UUID | None
    watchlist_entry_id: uuid.UUID | None
    evidence_id: uuid.UUID | None
    case_id: uuid.UUID
    alert_type: str
    severity: str
    title: str
    description: str | None
    matched_value: str | None
    matched_entity_type: str | None
    confidence: float
    status: str
    is_cross_case: bool
    # cross_case_ids contains str UUIDs; RBAC-filtered message added in API layer
    cross_case_count: int = 0
    cross_case_accessible: bool = False
    alert_metadata: dict[str, Any] = {}
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Denormalized display fields
    watchlist_name: str | None = None
    evidence_filename: str | None = None
    case_reference: str | None = None


class WatchlistAlertListResponse(BaseSchema):
    items: list[WatchlistAlertRead]
    total: int
    page: int
    pages: int
    new_count: int = 0
    critical_count: int = 0


class AlertStats(BaseSchema):
    total: int
    new_count: int
    acknowledged_count: int
    resolved_count: int
    dismissed_count: int
    critical_count: int
    high_count: int
    cross_case_count: int
    alerts_today: int
    alerts_this_week: int


# ── AlertNotification ─────────────────────────────────────────────────────────

class AlertNotificationRead(BaseSchema):
    id: uuid.UUID
    alert_id: uuid.UUID | None
    case_id: uuid.UUID | None
    title: str
    message: str | None
    level: str
    is_read: bool
    is_archived: bool
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseSchema):
    items: list[AlertNotificationRead]
    total: int
    unread_count: int


class NotificationCount(BaseSchema):
    unread_count: int


# ── Watchlist statistics ──────────────────────────────────────────────────────

class WatchlistStats(BaseSchema):
    total_watchlists: int
    active_watchlists: int
    total_entries: int
    total_alerts: int
    alerts_today: int
    alerts_this_week: int
    top_hit_watchlists: list[dict[str, Any]] = []
