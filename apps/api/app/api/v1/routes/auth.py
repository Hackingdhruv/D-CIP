"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.dependencies import CurrentUserDep, SessionDep
from app.core.rate_limit import limiter
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
)
from app.schemas.user import UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])

_COOKIE_OPTS: dict = dict(
    httponly=True,
    secure=settings.auth_cookie_secure,
    samesite=settings.auth_cookie_samesite,
)


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    *,
    max_age: int | None = None,
) -> None:
    domain = settings.auth_cookie_domain if settings.auth_cookie_domain != "localhost" else None
    access_max_age = max_age or (settings.access_token_expire_minutes * 60)
    refresh_max_age = max_age or (settings.refresh_token_expire_minutes * 60)
    response.set_cookie(
        "access_token",
        access_token,
        max_age=access_max_age,
        domain=domain,
        **_COOKIE_OPTS,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=refresh_max_age,
        domain=domain,
        **_COOKIE_OPTS,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")


@router.post("/login", response_model=AuthResponse, summary="Login")
@limiter.limit("10/minute")
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
) -> AuthResponse:
    svc = AuthService(session)
    access_token, refresh_token, user = svc.login(
        body.email,
        body.password,
        remember_me=body.remember_me,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    # access_token cookie tracks refresh_token lifetime (remember_me extends that);
    # the actual JWT inside expires per settings.access_token_expire_minutes.
    cookie_max_age = (30 * 24 * 60 * 60) if body.remember_me else (settings.refresh_token_expire_minutes * 60)
    _set_auth_cookies(response, access_token, refresh_token, max_age=cookie_max_age)
    return AuthResponse(
        expires_in=cookie_max_age,
        user=UserRead.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Logout")
def logout(
    request: Request,
    response: Response,
    session: SessionDep,
    current_user: CurrentUserDep,
    refresh_token: str | None = Cookie(default=None),
) -> None:
    svc = AuthService(session)
    svc.logout(
        refresh_token,
        current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _clear_auth_cookies(response)


@router.post("/refresh", response_model=AuthResponse, summary="Refresh access token")
def refresh(
    request: Request,
    response: Response,
    session: SessionDep,
    refresh_token: str | None = Cookie(default=None),
) -> AuthResponse:
    from app.core.exceptions import AuthenticationError

    if not refresh_token:
        raise AuthenticationError("No refresh token provided.")

    svc = AuthService(session)
    new_access, new_refresh, user = svc.refresh(
        refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_auth_cookies(response, new_access, new_refresh)
    return AuthResponse(
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserRead.model_validate(user),
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
)
@limiter.limit("5/minute")
def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    session: SessionDep,
) -> MessageResponse:
    svc = AuthService(session)
    raw_token = svc.forgot_password(
        body.email,
        ip_address=request.client.host if request.client else None,
    )
    msg = "If that email is registered, a reset link has been sent."
    if settings.debug and raw_token:
        msg = f"[DEV] Reset token: {raw_token}"
    return MessageResponse(message=msg)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using token",
)
def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    session: SessionDep,
) -> MessageResponse:
    svc = AuthService(session)
    svc.reset_password(
        body.token,
        body.new_password,
        ip_address=request.client.host if request.client else None,
    )
    return MessageResponse(message="Password has been reset successfully.")


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password (authenticated)",
)
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> MessageResponse:
    svc = AuthService(session)
    svc.change_password(
        current_user,
        body.current_password,
        body.new_password,
        ip_address=request.client.host if request.client else None,
    )
    return MessageResponse(message="Password changed successfully.")
