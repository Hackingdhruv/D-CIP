"""Unit tests for SearchService helpers."""

from __future__ import annotations

import pytest


def test_snip_centres_on_match():
    from app.services.search_service import _snip

    text = "a " * 60 + "needle" + " b" * 60
    result = _snip(text, "needle")
    assert "needle" in result
    assert result.startswith("…")
    assert result.endswith("…")


def test_snip_short_text_no_ellipsis():
    from app.services.search_service import _snip

    short = "hello world"
    result = _snip(short, "world")
    assert result == "hello world"
    assert "…" not in result


def test_snip_empty_text():
    from app.services.search_service import _snip

    assert _snip("", "q") == ""
    assert _snip(None, "q") == ""  # type: ignore[arg-type]


def test_snip_no_match_starts_at_beginning():
    from app.services.search_service import _snip

    text = "x" * 300
    result = _snip(text, "missing")
    assert len(result) <= 205  # snippet + possible ellipsis
    assert "…" in result


def test_score_title_hit_higher():
    from app.services.search_service import _score

    title_score = _score(True, 100)
    body_score = _score(False, 100)
    assert title_score > body_score


def test_score_confidence_scales():
    from app.services.search_service import _score

    high = _score(False, 100, 0.95)
    low = _score(False, 100, 0.1)
    assert high > low


def test_case_url():
    from app.services.search_service import _case_url

    assert _case_url("abc-123") == "/cases/abc-123"


def test_evidence_url():
    from app.services.search_service import _evidence_url

    assert _evidence_url("case-1", "ev-2") == "/cases/case-1/evidence/ev-2"
