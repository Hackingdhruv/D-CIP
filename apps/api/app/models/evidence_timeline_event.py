"""EvidenceTimelineEvent — real-world events extracted from evidence."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.evidence import Evidence


class TimelineEventType(str, Enum):
    EMAIL_SENT = "email_sent"
    EMAIL_RECEIVED = "email_received"
    LOGIN = "login"
    LOGOUT = "logout"
    PURCHASE = "purchase"
    TRAVEL = "travel"
    MEETING = "meeting"
    TRANSACTION = "transaction"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    PHONE_CALL = "phone_call"
    MESSAGE = "message"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    DOCUMENT_CREATED = "document_created"
    UNKNOWN = "unknown"


class EvidenceTimelineEvent(Base):
    __tablename__ = "evidence_timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    event_title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # When this event occurred in the real world (not when the record was created)
    event_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    evidence: Mapped[Evidence] = relationship("Evidence", foreign_keys=[evidence_id])
