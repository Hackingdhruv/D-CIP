"""TimelineEvent — the canonical investigation timeline record.

This is the central reconstruction store for Milestone 6. Unlike
:class:`EvidenceTimelineEvent` (the raw, append-only output of the AI extraction
pass), a ``TimelineEvent`` is a curated, enrichable record that can originate
from *any* source — AI extraction, OCR, EXIF, email headers, file metadata,
manual investigator entry, tasks, notes, reports, or case activity — and that
investigators can verify, tag, pin, bookmark, comment on, merge, and split.

Every AI-sourced event keeps a reference back to its supporting evidence
(``evidence_id`` + ``origin_event_id``) so the chain from conclusion to source
is never broken. Events are also designed to feed the relationship graph
(Milestone 7) via the ``entities`` JSON column.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.evidence import Evidence
    from app.models.timeline_event_comment import TimelineEventComment
    from app.models.user import User


class TimelineSourceType(str, Enum):
    """Where a timeline event came from."""

    AI_EXTRACTION = "ai_extraction"
    OCR = "ocr"
    EXIF = "exif"
    EMAIL = "email"
    FILE_METADATA = "file_metadata"
    EVIDENCE_METADATA = "evidence_metadata"
    MANUAL = "manual"
    TASK = "task"
    NOTE = "note"
    REPORT = "report"
    CASE_ACTIVITY = "case_activity"
    IMPORT = "import"


class TimelineEventType(str, Enum):
    """Full catalogue of investigation event types."""

    EVIDENCE_UPLOADED = "evidence_uploaded"
    EVIDENCE_PROCESSED = "evidence_processed"
    EMAIL_SENT = "email_sent"
    EMAIL_RECEIVED = "email_received"
    PHONE_CALL = "phone_call"
    SMS = "sms"
    INSTANT_MESSAGE = "instant_message"
    MESSAGE = "message"
    LOGIN = "login"
    LOGOUT = "logout"
    DEVICE_CONNECTED = "device_connected"
    DEVICE_REMOVED = "device_removed"
    GPS_LOCATION = "gps_location"
    PHOTO_TAKEN = "photo_taken"
    VIDEO_RECORDED = "video_recorded"
    BROWSER_HISTORY = "browser_history"
    WEBSITE_VISIT = "website_visit"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    USB_ACTIVITY = "usb_activity"
    FINANCIAL_TRANSACTION = "financial_transaction"
    TRANSACTION = "transaction"
    PURCHASE = "purchase"
    MEETING = "meeting"
    TRAVEL = "travel"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    DOCUMENT_CREATED = "document_created"
    TASK_COMPLETED = "task_completed"
    CASE_ACTIVITY = "case_activity"
    NOTE = "note"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class TimelineEventCategory(str, Enum):
    """Coarse grouping used for colour-coding and filtering."""

    COMMUNICATION = "communication"
    ACCESS = "access"
    LOCATION = "location"
    FILE = "file"
    FINANCIAL = "financial"
    DEVICE = "device"
    MEDIA = "media"
    WEB = "web"
    INVESTIGATION = "investigation"
    CUSTOM = "custom"


class TimelineVerificationStatus(str, Enum):
    """Investigator verification lifecycle for an event."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    REJECTED = "rejected"


# Maps each event type to its default category. Used at ingest time so events
# arrive pre-classified; investigators may override the category afterwards.
EVENT_TYPE_CATEGORY: dict[str, str] = {
    TimelineEventType.EMAIL_SENT.value: TimelineEventCategory.COMMUNICATION.value,
    TimelineEventType.EMAIL_RECEIVED.value: TimelineEventCategory.COMMUNICATION.value,
    TimelineEventType.PHONE_CALL.value: TimelineEventCategory.COMMUNICATION.value,
    TimelineEventType.SMS.value: TimelineEventCategory.COMMUNICATION.value,
    TimelineEventType.INSTANT_MESSAGE.value: TimelineEventCategory.COMMUNICATION.value,
    TimelineEventType.MESSAGE.value: TimelineEventCategory.COMMUNICATION.value,
    TimelineEventType.MEETING.value: TimelineEventCategory.COMMUNICATION.value,
    TimelineEventType.LOGIN.value: TimelineEventCategory.ACCESS.value,
    TimelineEventType.LOGOUT.value: TimelineEventCategory.ACCESS.value,
    TimelineEventType.USB_ACTIVITY.value: TimelineEventCategory.DEVICE.value,
    TimelineEventType.DEVICE_CONNECTED.value: TimelineEventCategory.DEVICE.value,
    TimelineEventType.DEVICE_REMOVED.value: TimelineEventCategory.DEVICE.value,
    TimelineEventType.GPS_LOCATION.value: TimelineEventCategory.LOCATION.value,
    TimelineEventType.TRAVEL.value: TimelineEventCategory.LOCATION.value,
    TimelineEventType.PHOTO_TAKEN.value: TimelineEventCategory.MEDIA.value,
    TimelineEventType.VIDEO_RECORDED.value: TimelineEventCategory.MEDIA.value,
    TimelineEventType.BROWSER_HISTORY.value: TimelineEventCategory.WEB.value,
    TimelineEventType.WEBSITE_VISIT.value: TimelineEventCategory.WEB.value,
    TimelineEventType.DOWNLOAD.value: TimelineEventCategory.WEB.value,
    TimelineEventType.UPLOAD.value: TimelineEventCategory.WEB.value,
    TimelineEventType.FINANCIAL_TRANSACTION.value: TimelineEventCategory.FINANCIAL.value,
    TimelineEventType.TRANSACTION.value: TimelineEventCategory.FINANCIAL.value,
    TimelineEventType.PURCHASE.value: TimelineEventCategory.FINANCIAL.value,
    TimelineEventType.FILE_CREATED.value: TimelineEventCategory.FILE.value,
    TimelineEventType.FILE_MODIFIED.value: TimelineEventCategory.FILE.value,
    TimelineEventType.DOCUMENT_CREATED.value: TimelineEventCategory.FILE.value,
    TimelineEventType.EVIDENCE_UPLOADED.value: TimelineEventCategory.INVESTIGATION.value,
    TimelineEventType.EVIDENCE_PROCESSED.value: TimelineEventCategory.INVESTIGATION.value,
    TimelineEventType.TASK_COMPLETED.value: TimelineEventCategory.INVESTIGATION.value,
    TimelineEventType.CASE_ACTIVITY.value: TimelineEventCategory.INVESTIGATION.value,
    TimelineEventType.NOTE.value: TimelineEventCategory.INVESTIGATION.value,
}


def category_for_event_type(event_type: str) -> str:
    """Return the default category for *event_type* (``custom`` when unknown)."""
    return EVENT_TYPE_CATEGORY.get(event_type, TimelineEventCategory.CUSTOM.value)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Primary supporting evidence (nullable — manual / activity events have none)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # When ingested from the raw extraction store, the source row id. Used to
    # guarantee idempotent ingest (one canonical event per extracted event).
    origin_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, default=TimelineEventCategory.CUSTOM.value, index=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Real-world occurrence (not the record-creation time).
    event_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    # Optional end of an interval event (travel, meeting, call duration…).
    event_end_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    timezone_name: Mapped[str | None] = mapped_column(String(60), nullable=True)

    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    verification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TimelineVerificationStatus.UNVERIFIED.value,
        index=True,
    )

    is_pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Merge / split support. A merged-away ("child") event points at the
    # surviving primary via ``merged_into_id`` and is hidden from default views.
    is_merged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("timeline_events.id", ondelete="SET NULL"), nullable=True, index=True
    )

    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Entity references — feeds the relationship graph in Milestone 7.
    # Each item: {"type": "...", "value": "..."}.
    entities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # {"label": str, "lat": float|None, "lng": float|None}
    location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Attached evidence previews: [{"evidence_id": str, "filename": str}]
    attachments: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free-form pointer to the originating object (task id, note id, url…).
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

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

    evidence: Mapped[Evidence | None] = relationship(
        "Evidence", foreign_keys=[evidence_id], lazy="selectin"
    )
    created_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[created_by_id], lazy="selectin"
    )
    comments: Mapped[list[TimelineEventComment]] = relationship(
        "TimelineEventComment",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TimelineEventComment.created_at",
    )

    @property
    def comment_count(self) -> int:
        try:
            return len(self.comments)
        except Exception:  # detached / not loaded
            return 0
