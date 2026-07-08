"""Timeline analysis engine — pure, deterministic, dependency-free.

This module reconstructs higher-order structure from a flat list of timeline
events: gaps, conflicting timestamps, duplicates, suspicious activity clusters,
periods of inactivity, and related-event groups.

It is intentionally free of any database or framework imports so it can be unit
tested in isolation and reused by both the API service and the Celery worker.
All functions operate on lightweight :class:`AnalysisEvent` records and return
plain dataclasses.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher


@dataclass(frozen=True)
class AnalysisEvent:
    id: uuid.UUID
    timestamp: datetime | None
    event_type: str
    title: str
    category: str = "custom"


@dataclass
class Gap:
    start: datetime
    end: datetime
    duration_hours: float
    before_event_id: uuid.UUID | None
    after_event_id: uuid.UUID | None


@dataclass
class Conflict:
    kind: str
    description: str
    event_ids: list[uuid.UUID]


@dataclass
class Duplicate:
    description: str
    event_ids: list[uuid.UUID]


@dataclass
class Cluster:
    start: datetime
    end: datetime
    event_count: int
    span_minutes: float
    event_ids: list[uuid.UUID]
    label: str


@dataclass
class Inactivity:
    start: datetime
    end: datetime
    duration_hours: float


@dataclass
class Group:
    key: str
    label: str
    event_ids: list[uuid.UUID] = field(default_factory=list)


@dataclass
class AnalysisResult:
    analyzed_events: int
    gaps: list[Gap]
    conflicts: list[Conflict]
    duplicates: list[Duplicate]
    clusters: list[Cluster]
    inactivity: list[Inactivity]
    groups: list[Group]


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _dated(events: list[AnalysisEvent]) -> list[AnalysisEvent]:
    """Return only events with a timestamp, sorted ascending."""
    dated = [e for e in events if e.timestamp is not None]
    dated.sort(key=lambda e: e.timestamp)  # type: ignore[arg-type, return-value]
    return dated


# ── Detectors ───────────────────────────────────────────────────────────────────

def detect_gaps(
    events: list[AnalysisEvent], *, threshold_hours: float = 24.0
) -> list[Gap]:
    """Consecutive dated events separated by more than *threshold_hours*."""
    dated = _dated(events)
    gaps: list[Gap] = []
    for prev, nxt in zip(dated, dated[1:]):
        assert prev.timestamp and nxt.timestamp
        delta_h = (nxt.timestamp - prev.timestamp).total_seconds() / 3600.0
        if delta_h > threshold_hours:
            gaps.append(
                Gap(
                    start=prev.timestamp,
                    end=nxt.timestamp,
                    duration_hours=round(delta_h, 2),
                    before_event_id=prev.id,
                    after_event_id=nxt.id,
                )
            )
    return gaps


def detect_inactivity(
    events: list[AnalysisEvent], *, threshold_hours: float = 72.0
) -> list[Inactivity]:
    """Highlight long quiet periods (gaps beyond a larger threshold)."""
    out: list[Inactivity] = []
    for g in detect_gaps(events, threshold_hours=threshold_hours):
        out.append(
            Inactivity(start=g.start, end=g.end, duration_hours=g.duration_hours)
        )
    return out


def detect_duplicates(
    events: list[AnalysisEvent],
    *,
    window_seconds: float = 120.0,
    title_threshold: float = 0.85,
) -> list[Duplicate]:
    """Same type + near-identical title within a short time window."""
    dated = _dated(events)
    dups: list[Duplicate] = []
    used: set[uuid.UUID] = set()
    for i, a in enumerate(dated):
        if a.id in used:
            continue
        group = [a.id]
        for b in dated[i + 1 :]:
            assert a.timestamp and b.timestamp
            if (b.timestamp - a.timestamp).total_seconds() > window_seconds:
                break
            if b.id in used:
                continue
            if a.event_type == b.event_type and _similar(a.title, b.title) >= title_threshold:
                group.append(b.id)
                used.add(b.id)
        if len(group) > 1:
            used.update(group)
            dups.append(
                Duplicate(
                    description=(
                        f"{len(group)} near-identical '{a.event_type}' events "
                        f"within {int(window_seconds)}s — possible duplicates."
                    ),
                    event_ids=group,
                )
            )
    return dups


def detect_conflicts(
    events: list[AnalysisEvent], *, min_hours_apart: float = 1.0
) -> list[Conflict]:
    """Events describing the same thing but with disagreeing timestamps.

    Two dated events of the same type with highly similar titles but timestamps
    more than *min_hours_apart* apart are flagged as a timestamp conflict.
    """
    dated = _dated(events)
    conflicts: list[Conflict] = []
    seen_pairs: set[frozenset[uuid.UUID]] = set()
    for i, a in enumerate(dated):
        for b in dated[i + 1 :]:
            assert a.timestamp and b.timestamp
            if a.event_type != b.event_type:
                continue
            hours_apart = abs((b.timestamp - a.timestamp).total_seconds()) / 3600.0
            if hours_apart < min_hours_apart:
                continue
            if _similar(a.title, b.title) >= 0.9:
                pair = frozenset({a.id, b.id})
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                conflicts.append(
                    Conflict(
                        kind="timestamp_conflict",
                        description=(
                            f"Two '{a.event_type}' events with matching descriptions "
                            f"are timestamped {round(hours_apart, 1)}h apart."
                        ),
                        event_ids=[a.id, b.id],
                    )
                )
    return conflicts


def detect_clusters(
    events: list[AnalysisEvent],
    *,
    window_minutes: float = 60.0,
    min_events: int = 4,
) -> list[Cluster]:
    """Suspicious activity clusters: >= *min_events* within *window_minutes*."""
    dated = _dated(events)
    clusters: list[Cluster] = []
    n = len(dated)
    i = 0
    window_s = window_minutes * 60.0
    while i < n:
        j = i
        while j + 1 < n:
            assert dated[i].timestamp and dated[j + 1].timestamp
            if (dated[j + 1].timestamp - dated[i].timestamp).total_seconds() <= window_s:
                j += 1
            else:
                break
        count = j - i + 1
        if count >= min_events:
            assert dated[i].timestamp and dated[j].timestamp
            span_min = (dated[j].timestamp - dated[i].timestamp).total_seconds() / 60.0
            clusters.append(
                Cluster(
                    start=dated[i].timestamp,
                    end=dated[j].timestamp,
                    event_count=count,
                    span_minutes=round(span_min, 1),
                    event_ids=[e.id for e in dated[i : j + 1]],
                    label=(
                        f"{count} events within {round(span_min, 1)} min — "
                        "concentrated activity."
                    ),
                )
            )
            i = j + 1
        else:
            i += 1
    return clusters


def group_related(events: list[AnalysisEvent]) -> list[Group]:
    """Group events by category for at-a-glance navigation."""
    buckets: dict[str, Group] = {}
    for e in events:
        cat = e.category or "custom"
        if cat not in buckets:
            buckets[cat] = Group(key=cat, label=cat.replace("_", " ").title())
        buckets[cat].event_ids.append(e.id)
    return [g for g in buckets.values() if g.event_ids]


def analyze(
    events: list[AnalysisEvent],
    *,
    gap_threshold_hours: float = 24.0,
    inactivity_threshold_hours: float = 72.0,
    cluster_window_minutes: float = 60.0,
    cluster_min_events: int = 4,
) -> AnalysisResult:
    """Run every detector and return a combined result."""
    return AnalysisResult(
        analyzed_events=len(events),
        gaps=detect_gaps(events, threshold_hours=gap_threshold_hours),
        conflicts=detect_conflicts(events),
        duplicates=detect_duplicates(events),
        clusters=detect_clusters(
            events,
            window_minutes=cluster_window_minutes,
            min_events=cluster_min_events,
        ),
        inactivity=detect_inactivity(
            events, threshold_hours=inactivity_threshold_hours
        ),
        groups=group_related(events),
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
