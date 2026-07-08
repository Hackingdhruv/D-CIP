"""Evidence chain-of-custody event — append-only audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.user import User


class CustodyAction(str, Enum):
    UPLOADED = "uploaded"
    VIEWED = "viewed"
    DOWNLOADED = "downloaded"
    PROCESSED = "processed"
    TAGGED = "tagged"
    UPDATED = "updated"
    LINKED = "linked"
    EXPORTED = "exported"
    VERIFIED = "verified"
    DELETED = "deleted"
    RESTORED = "restored"


class EvidenceCustodyEvent(Base):
    __tablename__ = "evidence_custody_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    evidence: Mapped[Evidence] = relationship(
        "Evidence", back_populates="custody_events"
    )
    actor: Mapped[User | None] = relationship(
        "User", foreign_keys=[actor_id], lazy="selectin"
    )
