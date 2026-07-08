"""Unit tests for the timeline analysis engine (pure, dependency-free)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from app.services.timeline_analysis import (
    AnalysisEvent,
    analyze,
    detect_clusters,
    detect_conflicts,
    detect_duplicates,
    detect_gaps,
    detect_inactivity,
    group_related,
)

BASE = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _ev(minutes: float, etype: str = "login", title: str = "Login", category: str = "access") -> AnalysisEvent:
    return AnalysisEvent(
        id=uuid.uuid4(),
        timestamp=BASE + timedelta(minutes=minutes),
        event_type=etype,
        title=title,
        category=category,
    )


class TestGaps:
    def test_detects_gap_beyond_threshold(self) -> None:
        events = [_ev(0), _ev(60 * 48)]  # 48h apart
        gaps = detect_gaps(events, threshold_hours=24)
        assert len(gaps) == 1
        assert gaps[0].duration_hours == 48.0

    def test_no_gap_within_threshold(self) -> None:
        events = [_ev(0), _ev(60)]  # 1h apart
        assert detect_gaps(events, threshold_hours=24) == []

    def test_ignores_undated_events(self) -> None:
        undated = AnalysisEvent(id=uuid.uuid4(), timestamp=None, event_type="x", title="x")
        events = [_ev(0), undated, _ev(60 * 48)]
        assert len(detect_gaps(events, threshold_hours=24)) == 1


class TestInactivity:
    def test_detects_long_quiet_period(self) -> None:
        events = [_ev(0), _ev(60 * 100)]  # ~4 days
        out = detect_inactivity(events, threshold_hours=72)
        assert len(out) == 1
        assert out[0].duration_hours > 72


class TestDuplicates:
    def test_detects_near_identical_events(self) -> None:
        events = [
            _ev(0, "email_sent", "Email sent to john@acme.com"),
            _ev(0.5, "email_sent", "Email sent to john@acme.com"),
        ]
        dups = detect_duplicates(events, window_seconds=120)
        assert len(dups) == 1
        assert len(dups[0].event_ids) == 2

    def test_different_types_not_duplicate(self) -> None:
        events = [
            _ev(0, "email_sent", "Something happened"),
            _ev(0.5, "login", "Something happened"),
        ]
        assert detect_duplicates(events) == []

    def test_far_apart_not_duplicate(self) -> None:
        events = [
            _ev(0, "login", "User login"),
            _ev(60, "login", "User login"),  # 1h apart, beyond window
        ]
        assert detect_duplicates(events, window_seconds=120) == []


class TestConflicts:
    def test_detects_timestamp_conflict(self) -> None:
        events = [
            _ev(0, "meeting", "Board meeting with the CFO"),
            _ev(180, "meeting", "Board meeting with the CFO"),  # 3h apart
        ]
        conflicts = detect_conflicts(events, min_hours_apart=1.0)
        assert len(conflicts) == 1
        assert conflicts[0].kind == "timestamp_conflict"

    def test_no_conflict_when_close(self) -> None:
        events = [
            _ev(0, "meeting", "Board meeting"),
            _ev(10, "meeting", "Board meeting"),  # 10 min apart
        ]
        assert detect_conflicts(events, min_hours_apart=1.0) == []


class TestClusters:
    def test_detects_burst(self) -> None:
        events = [_ev(i) for i in (0, 5, 10, 15, 20)]  # 5 events in 20 min
        clusters = detect_clusters(events, window_minutes=60, min_events=4)
        assert len(clusters) == 1
        assert clusters[0].event_count == 5

    def test_sparse_events_no_cluster(self) -> None:
        events = [_ev(0), _ev(120), _ev(240)]  # 2h apart each
        assert detect_clusters(events, window_minutes=60, min_events=4) == []


class TestGrouping:
    def test_groups_by_category(self) -> None:
        events = [
            _ev(0, "login", "L", "access"),
            _ev(1, "email_sent", "E", "communication"),
            _ev(2, "logout", "O", "access"),
        ]
        groups = {g.key: g for g in group_related(events)}
        assert set(groups) == {"access", "communication"}
        assert len(groups["access"].event_ids) == 2


class TestAnalyzeAggregate:
    def test_runs_all_detectors(self) -> None:
        events = [_ev(i) for i in (0, 5, 10, 15)] + [_ev(60 * 80)]
        result = analyze(events)
        assert result.analyzed_events == 5
        assert len(result.clusters) >= 1
        assert len(result.gaps) >= 1
        assert len(result.inactivity) >= 1

    def test_empty_input(self) -> None:
        result = analyze([])
        assert result.analyzed_events == 0
        assert result.gaps == []
        assert result.clusters == []
