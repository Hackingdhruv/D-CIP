"""Pydantic schemas for the Investigation Report Intelligence Engine."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import BaseSchema

# ── Enumerations ───────────────────────────────────────────────────────────────

ReportType = Literal[
    "executive",
    "detailed",
    "evidence_inventory",
    "timeline",
    "entity_intelligence",
    "chain_of_custody",
    "ai_findings",
    "case_progress",
    "activity",
]

ReportTemplate = Literal[
    "professional",
    "police",
    "cyber",
    "incident_response",
    "executive_summary",
    "custom",
]

ReportStatus = Literal["draft", "generating", "ready", "published", "archived"]

SectionType = Literal[
    "cover",
    "table_of_contents",
    "executive_summary",
    "case_overview",
    "evidence_inventory",
    "timeline",
    "entities",
    "ai_findings",
    "notes_tasks",
    "chain_of_custody",
    "appendix",
]

ExportFormat = Literal["pdf", "docx", "html", "json"]

# ── Section configuration ──────────────────────────────────────────────────────

class SectionConfig(BaseSchema):
    type: str
    title: str
    order_index: int
    enabled: bool = True


# ── Report filters (what data to pull into each section) ──────────────────────

class ReportFilters(BaseSchema):
    date_from: datetime | None = None
    date_to: datetime | None = None
    evidence_ids: list[str] | None = None
    entity_types: list[str] | None = None
    include_ai: bool = True
    max_entities_per_type: int = Field(50, ge=1, le=500)
    include_chain_of_custody: bool = True
    classification_label: str = "CONFIDENTIAL"
    watermark_text: str | None = None


# ── Create / generate request ──────────────────────────────────────────────────

class CreateReportRequest(BaseSchema):
    report_type: ReportType
    template: ReportTemplate = "professional"
    title: str = Field(..., min_length=1, max_length=500)
    sections_config: list[SectionConfig] = Field(default_factory=list)
    report_filters: ReportFilters = Field(default_factory=ReportFilters)


class GenerateReportRequest(BaseSchema):
    """Optional override for regeneration — omit to use stored config."""
    sections_config: list[SectionConfig] | None = None
    report_filters: ReportFilters | None = None


# ── Read schemas ───────────────────────────────────────────────────────────────

class ReportExportRead(BaseSchema):
    id: uuid.UUID
    report_id: uuid.UUID
    format: str
    file_size: int | None
    file_hash: str | None
    generated_by_id: uuid.UUID
    created_at: datetime


class ReportRead(BaseSchema):
    id: uuid.UUID
    case_id: uuid.UUID
    report_type: str
    template: str
    title: str
    status: str
    version: int
    content_hash: str | None
    parent_report_id: uuid.UUID | None
    sections_config: list[dict]
    report_filters: dict
    sections_content: dict
    generation_error: str | None
    generated_by_id: uuid.UUID
    approved_by_id: uuid.UUID | None
    generated_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    exports: list[ReportExportRead] = Field(default_factory=list)


class ReportListItem(BaseSchema):
    id: uuid.UUID
    case_id: uuid.UUID
    report_type: str
    template: str
    title: str
    status: str
    version: int
    content_hash: str | None
    parent_report_id: uuid.UUID | None
    generated_by_id: uuid.UUID
    generated_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    export_count: int = 0


# ── Template descriptor (returned by /templates endpoint) ──────────────────────

class TemplateDescriptor(BaseSchema):
    key: str
    label: str
    description: str
    sections: list[SectionConfig]


# ── Report type descriptor ─────────────────────────────────────────────────────

class ReportTypeDescriptor(BaseSchema):
    key: str
    label: str
    description: str
    default_template: str
