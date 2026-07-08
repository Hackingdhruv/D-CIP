"""WatchlistAlert ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.case import Case
    from app.models.evidence import Evidence
    from app.models.watchlist import Watchlist, WatchlistEntry


class AlertType(str, Enum):
    EXACT_MATCH = "exact_match"
    REGEX_MATCH = "regex_match"
    FUZZY_MATCH = "fuzzy_match"
    CROSS_CASE_MATCH = "cross_case_match"
    HIGH_RISK_MATCH = "high_risk_match"
    REPEATED_APPEARANCE = "repeated_appearance"
    AI_ALERT = "ai_alert"
    MANUAL_ALERT = "manual_alert"
    SYSTEM_ALERT = "system_alert"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class WatchlistAlert(Base):
    __tablename__ = "watchlist_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    watchlist_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("watchlists.id", ondelete="SET NULL"), nullable=True, index=True
    )
    watchlist_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("watchlist_entries.id", ondelete="SET NULL"), nullable=True
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True, index=True
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AlertSeverity.MEDIUM.value, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AlertStatus.NEW.value, index=True
    )
    is_cross_case: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # List of case UUIDs (as strings) where the same entity was found
    cross_case_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    alert_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledged_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
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

    watchlist: Mapped[Watchlist | None] = relationship(
        "Watchlist", foreign_keys=[watchlist_id]
    )
    watchlist_entry: Mapped[WatchlistEntry | None] = relationship(
        "WatchlistEntry", foreign_keys=[watchlist_entry_id]
    )
    evidence: Mapped[Evidence | None] = relationship(
        "Evidence", foreign_keys=[evidence_id]
    )
    case: Mapped[Case] = relationship("Case", foreign_keys=[case_id])
    created_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[created_by_id]
    )
    acknowledged_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[acknowledged_by_id]
    )
    resolved_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[resolved_by_id]
    )
