"""Version endpoint exposing build/runtime metadata."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.version import VersionInfo

router = APIRouter(tags=["meta"])


@router.get("/version", response_model=VersionInfo, summary="Build and runtime metadata")
def version() -> VersionInfo:
    return VersionInfo(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment.value,
        commit=settings.git_commit,
    )
