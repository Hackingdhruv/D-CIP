"""Enterprise Administration schemas — all admin API response/request models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.base import BaseSchema


# ── Identity Administration ────────────────────────────────────────────────────

class AdminUserRead(BaseSchema):
    """Extended user view with admin-level fields."""
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    is_active: bool
    is_locked: bool
    failed_login_attempts: int
    locked_until: datetime | None
    last_login_at: datetime | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    roles: list[str]  # role names


class AdminUserListResponse(BaseSchema):
    items: list[AdminUserRead]
    total: int
    page: int
    page_size: int
    pages: int


class LockUserRequest(BaseSchema):
    reason: str | None = Field(default=None, max_length=500)
    duration_minutes: int = Field(default=60, ge=1, le=10080)


class InviteUserRequest(BaseSchema):
    email: str
    full_name: str
    username: str
    role_ids: list[uuid.UUID] = Field(default_factory=list)
    temp_password: str = Field(min_length=8)


class SessionRead(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    user_full_name: str
    ip_address: str | None
    user_agent: str | None
    is_active: bool
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime


class SessionListResponse(BaseSchema):
    items: list[SessionRead]
    total: int
    page: int
    page_size: int
    pages: int


# ── Audit Center ──────────────────────────────────────────────────────────────

class AuditEventRead(BaseSchema):
    id: uuid.UUID
    event_type: str
    user_id: uuid.UUID | None
    user_email: str | None
    user_full_name: str | None
    actor_id: uuid.UUID | None
    actor_email: str | None
    actor_full_name: str | None
    ip_address: str | None
    user_agent: str | None
    metadata: dict[str, Any] | None
    created_at: datetime


class AuditSearchResponse(BaseSchema):
    items: list[AuditEventRead]
    total: int
    page: int
    page_size: int
    pages: int


class AuditStatItem(BaseSchema):
    event_type: str
    count: int


class AuditStats(BaseSchema):
    total_events: int
    events_today: int
    events_this_week: int
    breakdown: list[AuditStatItem]
    generated_at: datetime


# ── Security Center ───────────────────────────────────────────────────────────

class FailedLoginSummary(BaseSchema):
    user_id: uuid.UUID | None
    user_email: str | None
    attempt_count: int
    last_attempt: datetime
    ip_addresses: list[str]


class SecurityOverview(BaseSchema):
    locked_users_count: int
    inactive_users_count: int
    failed_logins_24h: int
    active_sessions: int
    expired_sessions_24h: int
    top_failed_logins: list[FailedLoginSummary]
    locked_users: list[AdminUserRead]
    recent_suspicious_ips: list[str]
    generated_at: datetime


# ── System Operations Center ──────────────────────────────────────────────────

ServiceStatus = Literal["healthy", "degraded", "down", "unknown"]


class ServiceHealthDetail(BaseSchema):
    name: str
    status: ServiceStatus
    latency_ms: float | None
    message: str | None
    version: str | None
    last_check: datetime


class QueueDetail(BaseSchema):
    name: str
    pending: int
    active: int
    failed: int
    processed_total: int


class WorkerInfo(BaseSchema):
    name: str
    status: str
    active_tasks: int
    processed: int
    failed: int


class SystemHealthResponse(BaseSchema):
    services: list[ServiceHealthDetail]
    queues: list[QueueDetail]
    workers: list[WorkerInfo]
    overall_status: ServiceStatus
    generated_at: datetime


# ── System Recommendations ────────────────────────────────────────────────────

RecommendationSeverity = Literal["critical", "warning", "info"]


class SystemRecommendation(BaseSchema):
    id: str
    severity: RecommendationSeverity
    title: str
    description: str
    action: str | None
    metric_value: str | None
    generated_at: datetime


class RecommendationsResponse(BaseSchema):
    recommendations: list[SystemRecommendation]
    critical_count: int
    warning_count: int
    info_count: int
    generated_at: datetime


# ── AI Administration ─────────────────────────────────────────────────────────

class AiConfigRead(BaseSchema):
    provider: str
    model: str
    embedding_model: str
    max_tokens: int
    temperature: float
    api_base: str
    api_key_configured: bool
    ocr_enabled: bool


class AiModelStat(BaseSchema):
    model_name: str
    message_count: int
    last_used: datetime | None


class AiUsageStats(BaseSchema):
    total_messages: int
    messages_today: int
    messages_this_week: int
    messages_this_month: int
    models_used: list[AiModelStat]
    avg_messages_per_case: float
    top_users: list[dict[str, Any]]
    generated_at: datetime


# ── Storage Center ────────────────────────────────────────────────────────────

class StorageBreakdown(BaseSchema):
    mime_type: str
    label: str
    file_count: int
    total_bytes: int


class LargestFile(BaseSchema):
    evidence_id: uuid.UUID
    case_id: uuid.UUID
    case_reference: str
    original_filename: str
    mime_type: str
    file_size: int
    uploaded_at: datetime


class StorageOverview(BaseSchema):
    total_used_bytes: int
    total_file_count: int
    evidence_bytes: int
    evidence_count: int
    by_type: list[StorageBreakdown]
    growth_last_7_days: int
    growth_last_30_days: int
    warning_threshold_pct: int
    used_pct: float
    largest_files: list[LargestFile]
    generated_at: datetime


# ── Configuration Center ──────────────────────────────────────────────────────

class ConfigEntry(BaseSchema):
    key: str
    value: str | None
    description: str | None
    is_secret: bool
    updated_at: datetime
    updated_by_email: str | None


class ConfigUpdateRequest(BaseSchema):
    value: str | None


# ── Admin Overview Stats ──────────────────────────────────────────────────────

class AdminOverviewStats(BaseSchema):
    total_users: int
    active_users: int
    locked_users: int
    inactive_users: int
    total_roles: int
    total_permissions: int
    active_sessions: int
    audit_events_today: int
    failed_logins_24h: int
    evidence_items: int
    total_cases: int
    system_status: ServiceStatus
    generated_at: datetime
