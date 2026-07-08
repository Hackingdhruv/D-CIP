"""Universal search schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema


class SearchFilters(BaseSchema):
    types: list[str] | None = None
    case_id: uuid.UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    case_status: str | None = None
    priority: str | None = None
    entity_type: str | None = None
    confidence_min: float | None = Field(None, ge=0.0, le=1.0)


class SearchRequest(BaseSchema):
    query: str = Field(..., min_length=1, max_length=500)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class SearchResultItem(BaseSchema):
    id: str
    type: str
    title: str
    snippet: str
    case_id: str | None = None
    case_title: str | None = None
    case_reference: str | None = None
    evidence_id: str | None = None
    confidence: float | None = None
    score: float
    created_at: datetime
    url: str


class SearchResponse(BaseSchema):
    items: list[SearchResultItem]
    total: int
    page: int
    page_size: int
    pages: int
    query: str
    took_ms: int
    sources: dict[str, int]


class SearchSuggestion(BaseSchema):
    text: str
    suggestion_type: str


class SuggestionsResponse(BaseSchema):
    suggestions: list[SearchSuggestion]
