"""User model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.associations import user_roles


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
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

    # Explicit primaryjoin resolves FK ambiguity (user_id vs assigned_by_id both → users)
    roles: Mapped[list[Role]] = relationship(  # type: ignore[name-defined]
        "Role",
        secondary=user_roles,
        primaryjoin=lambda: User.id == user_roles.c.user_id,
        lazy="selectin",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(  # type: ignore[name-defined]
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(  # type: ignore[name-defined]
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[UserSession]] = relationship(  # type: ignore[name-defined]
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list[AuthAuditEvent]] = relationship(  # type: ignore[name-defined]
        "AuthAuditEvent",
        foreign_keys="AuthAuditEvent.user_id",
        back_populates="user",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def permissions(self) -> list[str]:
        """Flat list of permission strings across all roles."""
        seen: set[str] = set()
        result: list[str] = []
        for role in self.roles:
            for perm in role.permissions:
                key = f"{perm.resource}:{perm.action}"
                if key not in seen:
                    seen.add(key)
                    result.append(key)
        return result
