"""Dashboard schemas — serialisable response models for all four dashboards.

• Executive Dashboard  — platform-wide investigation metrics
• Intelligence Dashboard — entity / timeline / evidence analytics
• Operations Dashboard  — service health and worker status
• Investigator Dashboard — personalised view for logged-in user
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import BaseSchema as BaseModel


# ── Shared helpers ─────────────────────────────────────────────────────────────

class KV(BaseModel):
    """Generic key/value pair for chart data points."""
    label: str
    value: int


class KVFloat(BaseModel):
    label: str
    value: float


class DateCount(BaseModel):
    date: str          # YYYY-MM-DD
    count: int


# ── Executive Dashboard ────────────────────────────────────────────────────────

class CaseStatusBreakdown(BaseModel):
    draft: int = 0
    open: int = 0
    in_progress: int = 0
    under_review: int = 0
    on_hold: int = 0
    closed: int = 0
    archived: int = 0


class CasePriorityBreakdown(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0


class InvestigatorWorkload(BaseModel):
    user_id: str
    full_name: str
    active_case_count: int
    open_task_count: int


class RecentCaseSummary(BaseModel):
    id: str
    reference_number: str
    title: str
    status: str
    priority: str
    updated_at: datetime


class ExecutiveDashboard(BaseModel):
    # Top-line counters
    active_cases: int
    high_priority_cases: int
    closed_cases: int
    total_cases: int

    # Evidence
    evidence_uploaded_today: int
    total_evidence: int

    # Reports
    reports_generated: int
    reports_published: int

    # AI / processing
    ai_queue_size: int                # evidence items still in AI processing pipeline
    avg_investigation_days: float     # avg (closed_at - created_at) in days

    # Breakdowns for charts
    status_breakdown: CaseStatusBreakdown
    priority_breakdown: CasePriorityBreakdown
    cases_opened_last_30_days: list[DateCount]   # daily opened cases (line chart)
    evidence_uploaded_last_30_days: list[DateCount]  # daily uploads (line chart)

    # Tables
    investigator_workload: list[InvestigatorWorkload]
    recently_active_cases: list[RecentCaseSummary]

    generated_at: datetime


# ── Intelligence Dashboard ─────────────────────────────────────────────────────

class EntityDistributionItem(BaseModel):
    entity_type: str
    count: int


class EvidenceTypeItem(BaseModel):
    mime_type: str
    label: str
    count: int


class ConfidenceBucket(BaseModel):
    bucket: str       # e.g. "0.9–1.0", "0.8–0.9"
    count: int


class TopKeyword(BaseModel):
    keyword: str
    total_score: float
    occurrence_count: int


class TopEntity(BaseModel):
    value: str
    entity_type: str
    occurrence_count: int
    avg_confidence: float


class IntelligenceDashboard(BaseModel):
    # Entity analytics
    entity_distribution: list[EntityDistributionItem]
    top_organizations: list[TopEntity]
    top_devices: list[TopEntity]
    top_persons: list[TopEntity]

    # Evidence analytics
    evidence_type_distribution: list[EvidenceTypeItem]

    # AI confidence histogram
    ai_confidence_distribution: list[ConfidenceBucket]

    # Keywords
    top_keywords: list[TopKeyword]

    # Timeline heatmap (last 30 days)
    timeline_heatmap: list[DateCount]

    # Relationship density proxy (entities per case)
    avg_entities_per_case: float
    total_unique_entities: int

    generated_at: datetime


# ── Operations Dashboard ───────────────────────────────────────────────────────

ServiceStatus = Literal["healthy", "degraded", "down", "unknown"]


class ServiceHealth(BaseModel):
    name: str
    status: ServiceStatus
    latency_ms: float | None = None
    message: str | None = None


class QueueInfo(BaseModel):
    name: str
    pending: int
    active: int = 0


class ProcessingStats(BaseModel):
    """Average duration in seconds for key processing stages."""
    avg_ocr_seconds: float | None = None
    avg_ai_seconds: float | None = None
    avg_total_seconds: float | None = None
    throughput_per_hour: float | None = None


class StorageStats(BaseModel):
    used_bytes: int
    file_count: int


class OperationsDashboard(BaseModel):
    services: list[ServiceHealth]
    queues: list[QueueInfo]

    # Evidence pipeline counters
    evidence_by_status: dict[str, int]
    failed_processing_24h: int

    processing_stats: ProcessingStats
    storage: StorageStats

    generated_at: datetime


# ── Investigator Dashboard ─────────────────────────────────────────────────────

class MyCase(BaseModel):
    id: str
    reference_number: str
    title: str
    status: str
    priority: str
    open_task_count: int
    updated_at: datetime


class MyTask(BaseModel):
    id: str
    case_id: str
    case_reference: str
    title: str
    priority: str
    due_date: datetime | None = None
    status: str


class MyNote(BaseModel):
    id: str
    case_id: str
    case_reference: str
    title: str
    is_pinned: bool
    updated_at: datetime


class MyEvidence(BaseModel):
    id: str
    case_id: str
    case_reference: str
    original_filename: str
    status: str
    created_at: datetime


class ProductivityMetrics(BaseModel):
    cases_active: int
    cases_closed_30d: int
    tasks_completed_30d: int
    evidence_items_uploaded_30d: int
    notes_created_30d: int


class InvestigatorDashboard(BaseModel):
    assigned_cases: list[MyCase]
    open_tasks: list[MyTask]
    recent_notes: list[MyNote]
    recent_evidence: list[MyEvidence]
    productivity: ProductivityMetrics
    generated_at: datetime
