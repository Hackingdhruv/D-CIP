"""User schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

import re

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema
from app.schemas.role import RoleReadSlim

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def _validate_email(v: str) -> str:
    if not _EMAIL_RE.match(v):
        raise ValueError("Enter a valid email address.")
    return v.lower()


def _validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(c.islower() for c in v):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit.")
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v):
        raise ValueError("Password must contain at least one special character.")
    return v


class UserCreate(BaseSchema):
    email: str = Field(min_length=1)
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: str = Field(min_length=1, max_length=255)
    password: str
    role_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        return _validate_email(v)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserUpdate(BaseSchema):
    email: str | None = None
    username: str | None = Field(
        default=None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$"
    )
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    avatar_url: str | None = None

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_email(v)
        return v


class UserRead(BaseSchema):
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    is_active: bool
    is_locked: bool
    avatar_url: str | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    roles: list[RoleReadSlim]
    permissions: list[str]


class UserReadSlim(BaseSchema):
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    is_active: bool
    is_locked: bool
    avatar_url: str | None
    last_login_at: datetime | None
    created_at: datetime
    roles: list[RoleReadSlim]


class UserListResponse(BaseSchema):
    items: list[UserReadSlim]
    total: int
    page: int
    page_size: int
    pages: int


class ProfileUpdate(BaseSchema):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    avatar_url: str | None = None
