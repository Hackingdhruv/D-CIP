"""Case model — the core investigation workspace entity."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.case_activity import CaseActivity
    from app.models.case_assignment import CaseAssignment
    from app.models.case_note import CaseNote
    from app.models.case_task import CaseTask
    from app.models.user import User


class CaseStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    ON_HOLD = "on_hold"
    CLOSED = "closed"
    ARCHIVED = "archived"


class CasePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reference_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CaseStatus.OPEN.value
    )
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CasePriority.MEDIUM.value
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    owner: Mapped[User] = relationship(
        "User", foreign_keys=[owner_id], lazy="selectin"
    )
    created_by: Mapped[User] = relationship(
        "User", foreign_keys=[created_by_id], lazy="selectin"
    )
    assignments: Mapped[list[CaseAssignment]] = relationship(
        "CaseAssignment",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    tasks: Mapped[list[CaseTask]] = relationship(
        "CaseTask",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CaseTask.created_at",
    )
    notes: Mapped[list[CaseNote]] = relationship(
        "CaseNote",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CaseNote.created_at.desc()",
    )
    activities: Mapped[list[CaseActivity]] = relationship(
        "CaseActivity",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="CaseActivity.created_at.desc()",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    @property
    def open_task_count(self) -> int:
        from app.models.case_task import TaskStatus
        return sum(
            1
            for t in self.tasks
            if t.status in (TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value)
        )

    @property
    def note_count(self) -> int:
        return len(self.notes)

    @property
    def assignment_count(self) -> int:
        return len(self.assignments)
