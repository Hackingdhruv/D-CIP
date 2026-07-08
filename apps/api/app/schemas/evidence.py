"""Evidence and chain-of-custody schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.schemas.base import BaseSchema
from app.schemas.user import UserReadSlim


# ── Custody events ─────────────────────────────────────────────────────────────

class EvidenceCustodyEventRead(BaseSchema):
    id: uuid.UUID
    evidence_id: uuid.UUID
    action: str
    description: str
    reason: str | None = None
    event_data: dict = {}
    actor: UserReadSlim | None = None
    created_at: datetime


# ── Evidence read schemas ──────────────────────────────────────────────────────

class EvidenceReadSlim(BaseSchema):
    """Lightweight evidence record — used in list views."""

    id: uuid.UUID
    case_id: uuid.UUID
    original_filename: str
    file_size: int
    mime_type: str
    file_extension: str
    sha256_hash: str
    status: str
    tags: list[str] = []
    priority: str
    source: str | None = None
    classification: str | None = None
    is_starred: bool
    url: str
    uploaded_by: UserReadSlim
    created_at: datetime
    updated_at: datetime


class EvidenceRead(BaseSchema):
    """Full evidence record — includes metadata, notes, custody preview."""

    id: uuid.UUID
    case_id: uuid.UUID
    original_filename: str
    file_size: int
    mime_type: str
    file_extension: str
    sha256_hash: str
    status: str
    processing_error: str | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    extracted_metadata: dict = {}
    tags: list[str] = []
    priority: str
    source: str | None = None
    classification: str | None = None
    notes: str | None = None
    is_starred: bool
    url: str
    uploaded_by: UserReadSlim
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ── Write schemas ──────────────────────────────────────────────────────────────

class EvidenceUpdate(BaseSchema):
    tags: list[str] | None = None
    priority: str | None = None
    source: str | None = None
    classification: str | None = None
    notes: str | None = None
    is_starred: bool | None = None


# ── List response ──────────────────────────────────────────────────────────────

class EvidenceListResponse(BaseSchema):
    items: list[EvidenceReadSlim]
    total: int
    page: int
    page_size: int
    pages: int


# ── Preview response ───────────────────────────────────────────────────────────

class EvidencePreviewResponse(BaseSchema):
    type: str              # "text" | "image" | "pdf" | "unavailable"
    content: str | None = None   # for text preview
    url: str | None = None       # for image / pdf
    truncated: bool = False
    reason: str | None = None    # for unavailable


# ── Hash verify response ───────────────────────────────────────────────────────

class EvidenceVerifyResponse(BaseSchema):
    matches: bool
    original_hash: str
    computed_hash: str
