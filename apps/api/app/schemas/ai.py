"""AI intelligence schemas — request/response models for AI endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema


# ── Entity ─────────────────────────────────────────────────────────────────────

class EvidenceEntityRead(BaseSchema):
    id: uuid.UUID
    evidence_id: uuid.UUID
    case_id: uuid.UUID
    entity_type: str
    value: str
    normalized_value: str
    confidence: float
    context: str | None = None
    source: str
    created_at: datetime


class EntityListResponse(BaseSchema):
    items: list[EvidenceEntityRead]
    total: int
    page: int
    page_size: int
    pages: int


# ── Keyword ────────────────────────────────────────────────────────────────────

class EvidenceKeywordRead(BaseSchema):
    id: uuid.UUID
    evidence_id: uuid.UUID
    case_id: uuid.UUID
    keyword: str
    score: float
    created_at: datetime


class KeywordListResponse(BaseSchema):
    items: list[EvidenceKeywordRead]
    total: int
    page: int
    page_size: int
    pages: int


# ── Timeline ───────────────────────────────────────────────────────────────────

class EvidenceTimelineEventRead(BaseSchema):
    id: uuid.UUID
    evidence_id: uuid.UUID
    case_id: uuid.UUID
    event_type: str
    event_title: str
    description: str | None = None
    event_timestamp: datetime | None = None
    confidence: float
    source_text: str | None = None
    created_at: datetime


class TimelineListResponse(BaseSchema):
    items: list[EvidenceTimelineEventRead]
    total: int
    page: int
    page_size: int
    pages: int


# ── Evidence Summary ───────────────────────────────────────────────────────────

class EvidenceSummaryRead(BaseSchema):
    id: uuid.UUID
    evidence_id: uuid.UUID
    summary_text: str
    key_findings: list[str]
    model_used: str | None = None
    created_at: datetime
    updated_at: datetime


# ── Case Summary ───────────────────────────────────────────────────────────────

class CaseSummaryRead(BaseSchema):
    id: uuid.UUID
    case_id: uuid.UUID
    summary_text: str
    key_findings: list[str]
    potential_leads: list[str]
    missing_information: list[str]
    open_questions: list[str]
    model_used: str | None = None
    created_at: datetime
    updated_at: datetime


# ── Chat ───────────────────────────────────────────────────────────────────────

class ChatMessageRequest(BaseSchema):
    message: str = Field(..., min_length=1, max_length=4000)


class AiChatMessageRead(BaseSchema):
    id: uuid.UUID
    case_id: uuid.UUID
    user_id: uuid.UUID | None = None
    role: str
    content: str
    evidence_references: list[str]
    model_used: str | None = None
    created_at: datetime


class ChatHistoryResponse(BaseSchema):
    items: list[AiChatMessageRead]
    total: int
    page: int
    page_size: int
    pages: int


# ── Search ─────────────────────────────────────────────────────────────────────

class SearchResultItem(BaseSchema):
    evidence_id: str
    filename: str
    score: float
    highlights: list[str] = Field(default_factory=list)


class SearchResponse(BaseSchema):
    query: str
    results: list[SearchResultItem]
    total: int


# ── Relationship graph ─────────────────────────────────────────────────────────

class GraphNode(BaseSchema):
    id: str
    label: str
    node_type: str
    confidence: float
    evidence_count: int = 1


class GraphEdge(BaseSchema):
    source: str
    target: str
    weight: int


class GraphResponse(BaseSchema):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    node_count: int
    edge_count: int


# ── Processing status ──────────────────────────────────────────────────────────

class ProcessingStatusRead(BaseSchema):
    evidence_id: uuid.UUID
    filename: str
    status: str
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    processing_error: str | None = None
    word_count: int | None = None
    language: str | None = None
    entity_count: int | None = None
    keyword_count: int | None = None
    timeline_event_count: int | None = None
    has_summary: bool = False
