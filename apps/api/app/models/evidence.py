"""Evidence model — digital evidence attached to an investigation case."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.evidence_custody import EvidenceCustodyEvent
    from app.models.user import User


class EvidenceStatus(str, Enum):
    UPLOADED = "uploaded"
    HASHING = "hashing"
    METADATA_EXTRACTION = "metadata_extraction"
    OCR_QUEUE = "ocr_queue"
    AI_QUEUE = "ai_queue"
    TIMELINE_QUEUE = "timeline_queue"
    GRAPH_QUEUE = "graph_queue"
    INDEXED = "indexed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvidencePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Original file info ─────────────────────────────────────────────────────
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # ── Processing pipeline ────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=EvidenceStatus.UPLOADED.value, index=True
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Extracted metadata (JSONB bag — extensible by AI milestone) ────────────
    extracted_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # OCR / native text extraction output, populated by the processing pipeline
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Classification ─────────────────────────────────────────────────────────
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EvidencePriority.MEDIUM.value
    )
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Ownership ──────────────────────────────────────────────────────────────
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # ── Soft delete ────────────────────────────────────────────────────────────
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    uploaded_by: Mapped[User] = relationship(
        "User", foreign_keys=[uploaded_by_id], lazy="selectin"
    )
    custody_events: Mapped[list[EvidenceCustodyEvent]] = relationship(
        "EvidenceCustodyEvent",
        back_populates="evidence",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="EvidenceCustodyEvent.created_at.desc()",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def url(self) -> str:
        return f"/uploads/{self.storage_path}"
