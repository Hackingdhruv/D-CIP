"""Watchlist management API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import RequirePermission, SessionDep
from app.models.user import User
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistEntryCreate,
    WatchlistEntryListResponse,
    WatchlistEntryRead,
    WatchlistEntryUpdate,
    WatchlistListResponse,
    WatchlistRead,
    WatchlistStats,
    WatchlistUpdate,
)
from app.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/watchlists", tags=["watchlists"])

_READ = RequirePermission("watchlist:read")
_WRITE = RequirePermission("watchlist:write")


@router.get("/stats", response_model=WatchlistStats)
def get_stats(
    session: SessionDep,
    current_user: User = _READ,
) -> WatchlistStats:
    return WatchlistService(session, current_user).get_stats()


@router.get("", response_model=WatchlistListResponse)
def list_watchlists(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    watchlist_type: str | None = Query(None),
    is_active: bool | None = Query(None),
    case_id: uuid.UUID | None = Query(None),
    include_global: bool = Query(True),
    current_user: User = _READ,
) -> WatchlistListResponse:
    return WatchlistService(session, current_user).list_watchlists(
        page=page,
        page_size=page_size,
        watchlist_type=watchlist_type,
        is_active=is_active,
        case_id=case_id,
        include_global=include_global,
    )


@router.post("", response_model=WatchlistRead, status_code=201)
def create_watchlist(
    session: SessionDep,
    body: WatchlistCreate,
    current_user: User = _WRITE,
) -> WatchlistRead:
    svc = WatchlistService(session, current_user)
    result = svc.create_watchlist(body)
    session.commit()
    return result


@router.get("/{watchlist_id}", response_model=WatchlistRead)
def get_watchlist(
    watchlist_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> WatchlistRead:
    return WatchlistService(session, current_user).get_watchlist_read(watchlist_id)


@router.put("/{watchlist_id}", response_model=WatchlistRead)
def update_watchlist(
    watchlist_id: uuid.UUID,
    session: SessionDep,
    body: WatchlistUpdate,
    current_user: User = _WRITE,
) -> WatchlistRead:
    svc = WatchlistService(session, current_user)
    result = svc.update_watchlist(watchlist_id, body)
    session.commit()
    return result


@router.delete("/{watchlist_id}", status_code=204)
def delete_watchlist(
    watchlist_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _WRITE,
) -> None:
    svc = WatchlistService(session, current_user)
    svc.delete_watchlist(watchlist_id)
    session.commit()


# ── Entries ───────────────────────────────────────────────────────────────────

@router.get("/{watchlist_id}/entries", response_model=WatchlistEntryListResponse)
def list_entries(
    watchlist_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> WatchlistEntryListResponse:
    return WatchlistService(session, current_user).list_entries(watchlist_id)


@router.post(
    "/{watchlist_id}/entries",
    response_model=WatchlistEntryRead,
    status_code=201,
)
def add_entry(
    watchlist_id: uuid.UUID,
    session: SessionDep,
    body: WatchlistEntryCreate,
    current_user: User = _WRITE,
) -> WatchlistEntryRead:
    svc = WatchlistService(session, current_user)
    result = svc.add_entry(watchlist_id, body)
    session.commit()
    return result


@router.put("/entries/{entry_id}", response_model=WatchlistEntryRead)
def update_entry(
    entry_id: uuid.UUID,
    session: SessionDep,
    body: WatchlistEntryUpdate,
    current_user: User = _WRITE,
) -> WatchlistEntryRead:
    svc = WatchlistService(session, current_user)
    result = svc.update_entry(entry_id, body)
    session.commit()
    return result


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _WRITE,
) -> None:
    svc = WatchlistService(session, current_user)
    svc.delete_entry(entry_id)
    session.commit()
