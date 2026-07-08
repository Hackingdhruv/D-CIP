"""Investigation timeline schemas (Milestone 6)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.user import UserReadSlim


# ── Comments ────────────────────────────────────────────────────────────────────

class TimelineCommentRead(BaseSchema):
    id: uuid.UUID
    event_id: uuid.UUID
    body: str
    author: UserReadSlim | None = None
    created_at: datetime
    updated_at: datetime


class TimelineCommentCreate(BaseSchema):
    body: str = Field(..., min_length=1, max_length=5000)


# ── Events ──────────────────────────────────────────────────────────────────────

class TimelineEventRead(BaseSchema):
    id: uuid.UUID
    case_id: uuid.UUID
    evidence_id: uuid.UUID | None = None
    origin_event_id: uuid.UUID | None = None
    source_type: str
    event_type: str
    category: str
    title: str
    description: str | None = None
    event_timestamp: datetime | None = None
    event_end_timestamp: datetime | None = None
    timezone_name: str | None = None
    confidence: float
    verification_status: str
    is_pinned: bool
    is_bookmarked: bool
    is_merged: bool
    merged_into_id: uuid.UUID | None = None
    color: str | None = None
    tags: list[str] = []
    entities: list[dict] = []
    location: dict | None = None
    attachments: list[dict] = []
    source_text: str | None = None
    source_reference: str | None = None
    comment_count: int = 0
    created_by: UserReadSlim | None = None
    created_at: datetime
    updated_at: datetime


class TimelineEventCreate(BaseSchema):
    event_type: str = Field(..., min_length=1, max_length=40)
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=20000)
    event_timestamp: datetime | None = None
    event_end_timestamp: datetime | None = None
    timezone_name: str | None = Field(default=None, max_length=60)
    category: str | None = Field(default=None, max_length=30)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_id: uuid.UUID | None = None
    color: str | None = Field(default=None, max_length=20)
    tags: list[str] = Field(default_factory=list)
    entities: list[dict] = Field(default_factory=list)
    location: dict | None = None
    attachments: list[dict] = Field(default_factory=list)
    source_reference: str | None = Field(default=None, max_length=500)


class TimelineEventUpdate(BaseSchema):
    event_type: str | None = Field(default=None, max_length=40)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=20000)
    event_timestamp: datetime | None = None
    event_end_timestamp: datetime | None = None
    timezone_name: str | None = Field(default=None, max_length=60)
    category: str | None = Field(default=None, max_length=30)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    color: str | None = Field(default=None, max_length=20)
    tags: list[str] | None = None
    entities: list[dict] | None = None
    location: dict | None = None
    attachments: list[dict] | None = None
    source_reference: str | None = Field(default=None, max_length=500)


class TimelineVerifyRequest(BaseSchema):
    status: str = Field(..., description="unverified | verified | disputed | rejected")


class TimelinePinRequest(BaseSchema):
    pinned: bool


class TimelineBookmarkRequest(BaseSchema):
    bookmarked: bool


class TimelineMergeRequest(BaseSchema):
    primary_id: uuid.UUID
    merge_ids: list[uuid.UUID] = Field(..., min_length=1)


# ── List / pagination ───────────────────────────────────────────────────────────

class TimelineListResponse(BaseSchema):
    items: list[TimelineEventRead]
    total: int
    page: int
    page_size: int
    pages: int


# ── Stats ───────────────────────────────────────────────────────────────────────

class TimelineStatsResponse(BaseSchema):
    total_events: int
    verified: int
    pinned: int
    bookmarked: int
    ai_generated: int
    manual: int
    by_category: dict[str, int]
    by_type: dict[str, int]
    by_source: dict[str, int]
    earliest: datetime | None = None
    latest: datetime | None = None
    undated: int = 0


# ── Analysis ────────────────────────────────────────────────────────────────────

class TimelineGap(BaseSchema):
    start: datetime
    end: datetime
    duration_hours: float
    before_event_id: uuid.UUID | None = None
    after_event_id: uuid.UUID | None = None


class TimelineConflict(BaseSchema):
    kind: str  # "timestamp_conflict" | "overlap"
    description: str
    event_ids: list[uuid.UUID]


class TimelineDuplicate(BaseSchema):
    description: str
    event_ids: list[uuid.UUID]


class TimelineCluster(BaseSchema):
    start: datetime
    end: datetime
    event_count: int
    span_minutes: float
    event_ids: list[uuid.UUID]
    label: str


class TimelineInactivity(BaseSchema):
    start: datetime
    end: datetime
    duration_hours: float


class TimelineGroup(BaseSchema):
    key: str
    label: str
    event_ids: list[uuid.UUID]


class TimelineAnalysisResponse(BaseSchema):
    analyzed_events: int
    gaps: list[TimelineGap]
    conflicts: list[TimelineConflict]
    duplicates: list[TimelineDuplicate]
    clusters: list[TimelineCluster]
    inactivity: list[TimelineInactivity]
    groups: list[TimelineGroup]
    narrative: str | None = None
    model_used: str | None = None
