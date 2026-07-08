"""Unit tests for WatchlistService."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, call

import pytest

from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistEntry
from app.models.watchlist_alert import WatchlistAlert
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistEntryCreate,
    WatchlistEntryUpdate,
    WatchlistUpdate,
)
from app.services.watchlist_service import WatchlistService, _normalize


def _now():
    return datetime.now(timezone.utc)


def _user() -> User:
    u = User(
        email="analyst@example.com",
        username="analyst",
        full_name="Test Analyst",
        password_hash="$2b$12$fake",
    )
    u.id = uuid.uuid4()
    u.roles = []
    return u


def _mock_session():
    db = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = 0
    result.scalars.return_value.all.return_value = []
    result.scalars.return_value = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute.return_value = result
    return db


def _svc(db=None, actor=None) -> WatchlistService:
    return WatchlistService(db or _mock_session(), actor or _user())


# ── Normalize ─────────────────────────────────────────────────────────────────

def test_normalize_strips_whitespace_and_lowercases():
    assert _normalize("  Email@EXAMPLE.COM  ") == "email@example.com"


# ── list_watchlists ───────────────────────────────────────────────────────────

def test_list_watchlists_returns_response_with_zero():
    db = _mock_session()
    db.execute.return_value.scalar_one.return_value = 0
    db.execute.return_value.scalars.return_value.all.return_value = []
    svc = _svc(db)
    result = svc.list_watchlists()
    assert result.total == 0
    assert result.items == []
    assert result.page == 1


def test_list_watchlists_respects_pagination():
    db = _mock_session()
    db.execute.return_value.scalar_one.return_value = 50
    db.execute.return_value.scalars.return_value.all.return_value = []
    svc = _svc(db)
    result = svc.list_watchlists(page=3, page_size=10)
    assert result.page == 3
    assert result.pages == 5


# ── get_watchlist ─────────────────────────────────────────────────────────────

def test_get_watchlist_not_found_raises_404():
    db = _mock_session()
    db.get.return_value = None
    svc = _svc(db)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        svc.get_watchlist(uuid.uuid4())
    assert exc_info.value.status_code == 404


def test_get_watchlist_returns_model():
    db = _mock_session()
    wl = MagicMock(spec=Watchlist)
    wl.id = uuid.uuid4()
    wl.name = "My Watchlist"
    wl.description = None
    wl.watchlist_type = "email"
    wl.is_active = True
    wl.case_id = None
    wl.created_by_id = None
    wl.created_at = _now()
    wl.updated_at = _now()
    db.get.return_value = wl
    db.execute.return_value.scalar_one.return_value = 0
    svc = _svc(db)
    result = svc.get_watchlist(wl.id)
    assert result is wl


# ── create_watchlist ──────────────────────────────────────────────────────────

def test_create_watchlist_adds_to_session():
    db = _mock_session()
    db.execute.return_value.scalar_one.return_value = 0
    actor = _user()
    svc = _svc(db, actor)

    data = WatchlistCreate(
        name="Suspect Emails",
        watchlist_type="email",
        is_active=True,
    )
    # db.flush() is called; db.refresh() needs to populate the object
    created_wl = MagicMock(spec=Watchlist)
    created_wl.id = uuid.uuid4()
    created_wl.name = data.name
    created_wl.description = None
    created_wl.watchlist_type = data.watchlist_type
    created_wl.is_active = True
    created_wl.case_id = None
    created_wl.created_by_id = actor.id
    created_wl.created_at = _now()
    created_wl.updated_at = _now()
    db.refresh.side_effect = lambda obj: None
    db.get.return_value = None  # for email lookup

    with MagicMock() as MockWL:
        with MagicMock() as mock_cls:
            import app.services.watchlist_service as svc_mod
            orig_cls = svc_mod.Watchlist
            try:
                svc_mod.Watchlist = lambda **kw: created_wl
                result = svc.create_watchlist(data)
                assert db.add.called
            finally:
                svc_mod.Watchlist = orig_cls


# ── update_watchlist ──────────────────────────────────────────────────────────

def test_update_watchlist_sets_fields():
    db = _mock_session()
    wl = MagicMock(spec=Watchlist)
    wl.id = uuid.uuid4()
    wl.name = "Old Name"
    wl.description = None
    wl.watchlist_type = "email"
    wl.is_active = True
    wl.case_id = None
    wl.created_by_id = None
    wl.created_at = _now()
    wl.updated_at = _now()
    db.get.return_value = wl
    db.execute.return_value.scalar_one.return_value = 0
    svc = _svc(db)

    update = WatchlistUpdate(name="New Name", is_active=False)
    svc.update_watchlist(wl.id, update)
    assert wl.name == "New Name"
    assert wl.is_active is False


# ── delete_watchlist ──────────────────────────────────────────────────────────

def test_delete_watchlist_calls_delete():
    db = _mock_session()
    wl = MagicMock(spec=Watchlist)
    wl.id = uuid.uuid4()
    db.get.return_value = wl
    svc = _svc(db)
    svc.delete_watchlist(wl.id)
    db.delete.assert_called_once_with(wl)
    db.flush.assert_called()


# ── add_entry ─────────────────────────────────────────────────────────────────

def test_add_entry_normalizes_value():
    db = _mock_session()
    wl = MagicMock(spec=Watchlist)
    wl.id = uuid.uuid4()
    db.get.side_effect = [wl]  # first get is watchlist

    captured_entry = None

    def capture_add(obj):
        nonlocal captured_entry
        captured_entry = obj

    db.add.side_effect = capture_add
    # After flush+refresh, return the entry
    entry_mock = MagicMock(spec=WatchlistEntry)
    entry_mock.id = uuid.uuid4()
    entry_mock.watchlist_id = wl.id
    entry_mock.value = "SUSPECT@EVIL.COM"
    entry_mock.normalized_value = "suspect@evil.com"
    entry_mock.is_regex = False
    entry_mock.description = None
    entry_mock.is_active = True
    entry_mock.hit_count = 0
    entry_mock.created_by_id = _user().id
    entry_mock.created_at = _now()
    entry_mock.updated_at = _now()
    db.refresh.side_effect = lambda obj: None

    actor = _user()
    svc = _svc(db, actor)

    import app.services.watchlist_service as svc_mod
    orig_cls = svc_mod.WatchlistEntry
    try:
        svc_mod.WatchlistEntry = lambda **kw: entry_mock
        data = WatchlistEntryCreate(value="SUSPECT@EVIL.COM")
        svc.add_entry(wl.id, data)
    finally:
        svc_mod.WatchlistEntry = orig_cls


def test_add_entry_watchlist_not_found_raises_404():
    db = _mock_session()
    db.get.return_value = None
    svc = _svc(db)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        svc.add_entry(uuid.uuid4(), WatchlistEntryCreate(value="x"))
    assert exc_info.value.status_code == 404


# ── delete_entry ──────────────────────────────────────────────────────────────

def test_delete_entry_not_found_raises_404():
    db = _mock_session()
    db.get.return_value = None
    svc = _svc(db)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        svc.delete_entry(uuid.uuid4())
    assert exc_info.value.status_code == 404


def test_delete_entry_calls_delete():
    db = _mock_session()
    entry = MagicMock(spec=WatchlistEntry)
    entry.id = uuid.uuid4()
    db.get.return_value = entry
    svc = _svc(db)
    svc.delete_entry(entry.id)
    db.delete.assert_called_once_with(entry)


# ── get_stats ─────────────────────────────────────────────────────────────────

def test_get_stats_returns_zeros():
    db = _mock_session()
    # All counts return 0
    call_count = 0

    def execute_side(stmt):
        result = MagicMock()
        result.scalar_one.return_value = 0
        result.all.return_value = []
        return result

    db.execute.side_effect = execute_side
    svc = _svc(db)
    stats = svc.get_stats()
    assert stats.total_watchlists == 0
    assert stats.active_watchlists == 0
    assert stats.total_entries == 0
    assert stats.total_alerts == 0
