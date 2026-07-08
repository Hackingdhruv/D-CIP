"""Investigation Report models.

Two tables:
  - investigation_reports  — report config + generated content
  - report_exports         — each format export (PDF, DOCX, HTML, JSON)

Reports are version-tracked; regenerating a report creates a new row with
parent_report_id pointing to the previous version. This makes every published
report immutable.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.user import User


class InvestigationReport(Base):
    __tablename__ = "investigation_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Classification ─────────────────────────────────────────────────────────
    # Possible values: executive, detailed, evidence_inventory, timeline,
    # entity_intelligence, chain_of_custody, ai_findings, case_progress, activity
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Template used: professional, police, cyber, incident_response,
    # executive_summary, custom
    template: Mapped[str] = mapped_column(String(50), nullable=False, default="professional")

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    # ── Status lifecycle: draft → generating → ready → published → archived ────
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # SHA-256 of JSON-serialised sections_content (ensures immutability)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Versioning ─────────────────────────────────────────────────────────────
    parent_report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("investigation_reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Configuration (persisted so reports can be regenerated) ───────────────
    # [{type, title, order_index, enabled}]
    sections_config: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # {date_from, date_to, evidence_ids, entity_types, include_ai, watermark_text,
    #  classification_label, include_chain_of_custody, max_entities_per_type}
    report_filters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # ── Generated content (keyed by section type) ────────────────────────────
    sections_content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Authorship ─────────────────────────────────────────────────────────────
    generated_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    case: Mapped[Case] = relationship("Case")
    generated_by: Mapped[User] = relationship("User", foreign_keys=[generated_by_id])
    approved_by: Mapped[User | None] = relationship("User", foreign_keys=[approved_by_id])
    exports: Mapped[list[ReportExport]] = relationship(
        "ReportExport", back_populates="report", cascade="all, delete-orphan"
    )
    previous_versions: Mapped[list[InvestigationReport]] = relationship(
        "InvestigationReport",
        foreign_keys=[parent_report_id],
        back_populates="parent",
        lazy="select",
    )
    parent: Mapped[InvestigationReport | None] = relationship(
        "InvestigationReport",
        foreign_keys=[parent_report_id],
        back_populates="previous_versions",
        remote_side=[id],
    )


class ReportExport(Base):
    __tablename__ = "report_exports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigation_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # pdf, docx, html, json
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # SHA-256 of exported file content
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    generated_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    report: Mapped[InvestigationReport] = relationship("InvestigationReport", back_populates="exports")
    generated_by: Mapped[User] = relationship("User", foreign_keys=[generated_by_id])
