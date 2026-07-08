"""Unit tests for WatchlistMatchingEngine."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.evidence_entity import EvidenceEntity, EntitySource
from app.models.watchlist import Watchlist, WatchlistEntry, WatchlistType
from app.models.watchlist_alert import AlertType, AlertSeverity
from app.services.watchlist_matching import (
    WatchlistMatchingEngine,
    MatchResult,
    _severity_for_watchlist_type,
    _REPEATED_APPEARANCE_THRESHOLD,
)
from app.services.watchlist_service import _normalize


# ── Factories ─────────────────────────────────────────────────────────────────

def _uuid():
    return uuid.uuid4()


def _now():
    return datetime.now(timezone.utc)


def _watchlist(watchlist_type: str = "email", case_id=None) -> Watchlist:
    wl = MagicMock(spec=Watchlist)
    wl.id = _uuid()
    wl.watchlist_type = watchlist_type
    wl.name = f"Test {watchlist_type} watchlist"
    wl.is_active = True
    wl.case_id = case_id
    return wl


def _entry(value: str, is_regex: bool = False, watchlist=None) -> WatchlistEntry:
    e = MagicMock(spec=WatchlistEntry)
    e.id = _uuid()
    e.value = value
    e.normalized_value = _normalize(value)
    e.is_regex = is_regex
    e.is_active = True
    e.watchlist = watchlist or _watchlist()
    return e


def _entity(
    entity_type: str = "email",
    value: str = "test@example.com",
    case_id=None,
    evidence_id=None,
) -> EvidenceEntity:
    ent = MagicMock(spec=EvidenceEntity)
    ent.id = _uuid()
    ent.entity_type = entity_type
    ent.value = value
    ent.normalized_value = _normalize(value)
    ent.confidence = 1.0
    ent.source = EntitySource.REGEX.value
    ent.case_id = case_id or _uuid()
    ent.evidence_id = evidence_id or _uuid()
    return ent


def _mock_db():
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.scalar_one.return_value = 0
    db.execute.return_value = result
    return db


# ── Normalize helper ──────────────────────────────────────────────────────────

def test_normalize_strips_and_lowercases():
    assert _normalize("  TEST@EXAMPLE.COM  ") == "test@example.com"


def test_normalize_already_clean():
    assert _normalize("abc123") == "abc123"


# ── Severity mapping ──────────────────────────────────────────────────────────

def test_severity_crypto_wallet_is_critical():
    assert _severity_for_watchlist_type("crypto_wallet") == "critical"


def test_severity_email_is_high():
    assert _severity_for_watchlist_type("email") == "high"


def test_severity_domain_is_medium():
    assert _severity_for_watchlist_type("domain") == "medium"


# ── Exact match ───────────────────────────────────────────────────────────────

def test_exact_match_returns_true():
    engine = WatchlistMatchingEngine(MagicMock())
    entry = _entry("test@example.com")
    entity = _entity(value="test@example.com")
    assert engine._exact_match(entry, entity) is True


def test_exact_match_returns_false_on_different_value():
    engine = WatchlistMatchingEngine(MagicMock())
    entry = _entry("other@example.com")
    entity = _entity(value="test@example.com")
    assert engine._exact_match(entry, entity) is False


def test_exact_match_case_insensitive_via_normalization():
    engine = WatchlistMatchingEngine(MagicMock())
    entry = _entry("TEST@EXAMPLE.COM")
    # Entry normalized_value = "test@example.com"
    entity = _entity(value="test@example.com")
    # entity normalized_value = "test@example.com"
    assert engine._exact_match(entry, entity) is True


# ── Regex match ───────────────────────────────────────────────────────────────

def test_regex_match_valid_pattern():
    engine = WatchlistMatchingEngine(MagicMock())
    entry = _entry(r"192\.168\.\d+\.\d+", is_regex=True)
    entity = _entity(entity_type="ip_address", value="192.168.1.100")
    assert engine._regex_match(entry, entity) is True


def test_regex_match_no_match():
    engine = WatchlistMatchingEngine(MagicMock())
    entry = _entry(r"^10\.\d+\.\d+\.\d+$", is_regex=True)
    entity = _entity(entity_type="ip_address", value="192.168.1.1")
    assert engine._regex_match(entry, entity) is False


def test_regex_match_invalid_pattern_returns_false():
    engine = WatchlistMatchingEngine(MagicMock())
    entry = _entry(r"[invalid(", is_regex=True)
    entity = _entity(value="test@example.com")
    assert engine._regex_match(entry, entity) is False


def test_regex_match_case_insensitive():
    engine = WatchlistMatchingEngine(MagicMock())
    entry = _entry(r"admin@.*", is_regex=True)
    entity = _entity(value="ADMIN@CORP.COM")
    assert engine._regex_match(entry, entity) is True


# ── Watchlist pass integration ─────────────────────────────────────────────────

def test_watchlist_match_exact_hit():
    wl = _watchlist("email")
    entry = _entry("suspect@criminal.org", watchlist=wl)
    entity = _entity("email", "suspect@criminal.org")

    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value = iter([entry])
    db.execute.return_value = result

    engine = WatchlistMatchingEngine(db)
    results = engine._watchlist_match([entity], _uuid())
    assert len(results) == 1
    assert results[0].alert_type == AlertType.EXACT_MATCH.value
    assert results[0].matched_value == "suspect@criminal.org"


def test_watchlist_match_skips_wrong_entity_type():
    wl = _watchlist("email")
    entry = _entry("192.168.1.1", watchlist=wl)
    entity = _entity("ip_address", "192.168.1.1")

    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value = iter([entry])
    db.execute.return_value = result

    engine = WatchlistMatchingEngine(db)
    results = engine._watchlist_match([entity], _uuid())
    # email watchlist does not match ip_address entities
    assert len(results) == 0


def test_watchlist_match_regex_watchlist():
    wl = _watchlist("regex")
    entry = _entry(r".*\.ru$", is_regex=True, watchlist=wl)
    entity = _entity("domain", "evil.ru")

    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value = iter([entry])
    db.execute.return_value = result

    engine = WatchlistMatchingEngine(db)
    results = engine._watchlist_match([entity], _uuid())
    assert len(results) == 1
    assert results[0].alert_type == AlertType.REGEX_MATCH.value


def test_watchlist_match_high_risk_type():
    wl = _watchlist("crypto_wallet")
    crypto_value = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
    entry = _entry(crypto_value, watchlist=wl)
    entity = _entity("crypto_wallet", crypto_value)

    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value = iter([entry])
    db.execute.return_value = result

    engine = WatchlistMatchingEngine(db)
    results = engine._watchlist_match([entity], _uuid())
    assert len(results) == 1
    assert results[0].alert_type == AlertType.HIGH_RISK_MATCH.value
    assert results[0].severity == AlertSeverity.CRITICAL.value


# ── Repeated appearance ───────────────────────────────────────────────────────

def test_repeated_appearance_triggers_when_threshold_met():
    entity = _entity("email", "repeat@example.com")
    evidence_id = _uuid()
    entity.evidence_id = evidence_id

    db = MagicMock()
    result = MagicMock()
    # Already seen in 2 other evidence items → total 3 (meets threshold)
    result.scalar_one.return_value = _REPEATED_APPEARANCE_THRESHOLD - 1
    db.execute.return_value = result

    engine = WatchlistMatchingEngine(db)
    results = engine._repeated_appearance_check([entity], _uuid(), evidence_id)
    assert len(results) == 1
    assert results[0].alert_type == AlertType.REPEATED_APPEARANCE.value


def test_repeated_appearance_does_not_trigger_below_threshold():
    entity = _entity("email", "rare@example.com")
    evidence_id = _uuid()
    entity.evidence_id = evidence_id

    db = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = 1  # Only 1 other occurrence, need 2
    db.execute.return_value = result

    engine = WatchlistMatchingEngine(db)
    results = engine._repeated_appearance_check([entity], _uuid(), evidence_id)
    assert len(results) == 0


def test_repeated_appearance_deduplicates_same_entity():
    case_id = _uuid()
    evidence_id = _uuid()
    entity1 = _entity("email", "dup@example.com", case_id, evidence_id)
    entity2 = _entity("email", "dup@example.com", case_id, evidence_id)

    db = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = 5
    db.execute.return_value = result

    engine = WatchlistMatchingEngine(db)
    results = engine._repeated_appearance_check(
        [entity1, entity2], case_id, evidence_id
    )
    # Should only produce 1 result despite 2 entities with same value
    assert len(results) == 1


# ── Cross-case match ──────────────────────────────────────────────────────────

def test_cross_case_match_finds_other_cases():
    entity = _entity("email", "suspect@evil.org")
    case_id = _uuid()
    other_case_id = _uuid()

    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [other_case_id]
    db.execute.return_value = result

    engine = WatchlistMatchingEngine(db)
    results = engine._cross_case_match([entity], case_id)
    assert len(results) == 1
    assert results[0].alert_type == AlertType.CROSS_CASE_MATCH.value
    assert results[0].is_cross_case is True
    assert str(other_case_id) in results[0].cross_case_ids


def test_cross_case_match_no_other_cases():
    entity = _entity("email", "innocent@example.com")
    case_id = _uuid()

    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute.return_value = result

    engine = WatchlistMatchingEngine(db)
    results = engine._cross_case_match([entity], case_id)
    assert len(results) == 0


def test_cross_case_deduplicates_same_entity_type_value():
    case_id = _uuid()
    other_case = _uuid()
    entity1 = _entity("domain", "evil.org")
    entity2 = _entity("domain", "evil.org")

    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [other_case]
    db.execute.return_value = result

    engine = WatchlistMatchingEngine(db)
    results = engine._cross_case_match([entity1, entity2], case_id)
    assert len(results) == 1


# ── Full run ──────────────────────────────────────────────────────────────────

def test_run_returns_empty_when_no_entities():
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value = iter([])
    db.execute.return_value = result

    engine = WatchlistMatchingEngine(db)
    # Patch entity loading to return empty
    with patch.object(engine, "_watchlist_match", return_value=[]):
        with patch.object(engine, "_repeated_appearance_check", return_value=[]):
            with patch.object(engine, "_cross_case_match", return_value=[]):
                results = engine.run(_uuid(), _uuid())
    assert results == []
