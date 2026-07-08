"""Authentication schemas."""

from __future__ import annotations

import re

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema

_MIN_PW_LEN = 8
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def _validate_password_strength(v: str) -> str:
    if len(v) < _MIN_PW_LEN:
        raise ValueError(f"Password must be at least {_MIN_PW_LEN} characters.")
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(c.islower() for c in v):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit.")
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v):
        raise ValueError("Password must contain at least one special character.")
    return v


class LoginRequest(BaseSchema):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)
    remember_me: bool = False

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address.")
        return v.lower()


class RefreshRequest(BaseSchema):
    pass


class LogoutRequest(BaseSchema):
    pass


class ForgotPasswordRequest(BaseSchema):
    email: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address.")
        return v.lower()


class ResetPasswordRequest(BaseSchema):
    token: str = Field(min_length=1)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class ChangePasswordRequest(BaseSchema):
    current_password: str = Field(min_length=1)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class TokenResponse(BaseSchema):
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(BaseSchema):
    token_type: str = "bearer"
    expires_in: int
    user: UserRead  # type: ignore[name-defined]


class MessageResponse(BaseSchema):
    message: str


# Import deferred to avoid circular reference — resolved at the bottom.
from app.schemas.user import UserRead  # noqa: E402

AuthResponse.model_rebuild()
