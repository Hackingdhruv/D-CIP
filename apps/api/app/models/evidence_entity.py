"""EvidenceEntity — named entities extracted from evidence text."""

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


class EntityType(str, Enum):
    PERSON = "person"
    EMAIL = "email"
    PHONE = "phone"
    ORGANIZATION = "organization"
    DOMAIN = "domain"
    URL = "url"
    IP_ADDRESS = "ip_address"
    DATE = "date"
    LOCATION = "location"
    COUNTRY = "country"
    CITY = "city"
    DEVICE = "device"
    OS = "os"
    BROWSER = "browser"
    FILENAME = "filename"
    FILE_HASH = "file_hash"
    BANK_ACCOUNT = "bank_account"
    CRYPTO_WALLET = "crypto_wallet"
    VEHICLE_NUMBER = "vehicle_number"
    UNKNOWN = "unknown"


class EntitySource(str, Enum):
    REGEX = "regex"
    NLP = "nlp"
    METADATA = "metadata"


class EvidenceEntity(Base):
    __tablename__ = "evidence_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Denormalized for case-level aggregate queries without joining through evidence
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default=EntitySource.REGEX.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    evidence: Mapped[Evidence] = relationship("Evidence", foreign_keys=[evidence_id])
