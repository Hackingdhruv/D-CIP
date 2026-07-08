"""Investigation Timeline routes (Milestone 6).

All routes are nested under ``/cases/{case_id}/timeline`` so case-level access
control is enforced before any timeline data is reachable. Read uses
``timeline:read``; creating/editing uses ``timeline:write``; destructive or
structural operations (merge, split, verify, delete) require ``timeline:manage``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query, Response
from fastapi.responses import StreamingResponse

from app.core.dependencies import RequirePermission, SessionDep
from app.models.user import User
from app.schemas.timeline import (
    TimelineAnalysisResponse,
    TimelineBookmarkRequest,
    TimelineCommentCreate,
    TimelineCommentRead,
    TimelineEventCreate,
    TimelineEventRead,
    TimelineEventUpdate,
    TimelineListResponse,
    TimelineMergeRequest,
    TimelinePinRequest,
    TimelineStatsResponse,
    TimelineVerifyRequest,
)
from app.services.timeline import TimelineService

router = APIRouter(prefix="/cases/{case_id}/timeline", tags=["timeline"])

_READ = RequirePermission("timeline:read")
_WRITE = RequirePermission("timeline:write")
_MANAGE = RequirePermission("timeline:manage")


def _csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


# ── List / create ────────────────────────────────────────────────────────────────

@router.get("", response_model=TimelineListResponse, summary="List timeline events")
def list_events(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
    q: str | None = Query(None, description="Keyword search (title/description/source)"),
    event_types: str | None = Query(None, description="Comma-separated event types"),
    categories: str | None = Query(None, description="Comma-separated categories"),
    source_types: str | None = Query(None, description="Comma-separated source types"),
    verification: str | None = Query(None, description="Comma-separated verification statuses"),
    tag: str | None = Query(None),
    min_confidence: float | None = Query(None, ge=0, le=1),
    max_confidence: float | None = Query(None, ge=0, le=1),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    is_pinned: bool | None = Query(None),
    is_bookmarked: bool | None = Query(None),
    include_merged: bool = Query(False),
    sort_by: str = Query("event_timestamp"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
) -> TimelineListResponse:
    svc = TimelineService(session)
    return svc.list_events(
        case_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
        q=q,
        event_types=_csv(event_types),
        categories=_csv(categories),
        source_types=_csv(source_types),
        verification=_csv(verification),
        tag=tag,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        date_from=date_from,
        date_to=date_to,
        is_pinned=is_pinned,
        is_bookmarked=is_bookmarked,
        include_merged=include_merged,
    )


@router.post(
    "",
    response_model=TimelineEventRead,
    status_code=201,
    summary="Create a manual timeline event",
)
def create_event(
    case_id: uuid.UUID,
    body: TimelineEventCreate,
    session: SessionDep,
    current_user: User = _WRITE,
) -> TimelineEventRead:
    svc = TimelineService(session)
    event = svc.create_event(case_id, body, actor=current_user)
    return TimelineEventRead.model_validate(event)


# ── Stats / analysis / export ────────────────────────────────────────────────────

@router.get("/stats", response_model=TimelineStatsResponse, summary="Timeline statistics")
def timeline_stats(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> TimelineStatsResponse:
    return TimelineService(session).stats(case_id)


@router.get(
    "/analysis",
    response_model=TimelineAnalysisResponse,
    summary="AI-assisted timeline analysis (gaps, conflicts, clusters…)",
)
def timeline_analysis(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
    use_ai: bool = Query(True, description="Include the AI narrative reconstruction"),
) -> TimelineAnalysisResponse:
    return TimelineService(session).analyze(case_id, use_ai=use_ai)


@router.get("/export", summary="Export the timeline (json|csv|pdf)")
def export_timeline(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
    format: str = Query("json", pattern="^(json|csv|pdf)$"),
) -> Response:
    content, media_type, filename = TimelineService(session).export(case_id, format)
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/ingest",
    summary="Re-sync AI-extracted events into the canonical timeline",
)
def ingest_timeline(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _WRITE,
) -> dict:
    created = TimelineService(session).ingest_from_extraction(case_id)
    return {"ingested": created}


# ── Merge ────────────────────────────────────────────────────────────────────────

@router.post(
    "/merge",
    response_model=TimelineEventRead,
    summary="Merge duplicate events into a primary",
)
def merge_events(
    case_id: uuid.UUID,
    body: TimelineMergeRequest,
    session: SessionDep,
    current_user: User = _MANAGE,
) -> TimelineEventRead:
    svc = TimelineService(session)
    primary = svc.merge_events(case_id, body.primary_id, body.merge_ids, actor=current_user)
    return TimelineEventRead.model_validate(primary)


# ── Single event ─────────────────────────────────────────────────────────────────

@router.get("/{event_id}", response_model=TimelineEventRead, summary="Get a timeline event")
def get_event(
    case_id: uuid.UUID,
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> TimelineEventRead:
    event = TimelineService(session).get_event(event_id, case_id)
    return TimelineEventRead.model_validate(event)


@router.put("/{event_id}", response_model=TimelineEventRead, summary="Update a timeline event")
def update_event(
    case_id: uuid.UUID,
    event_id: uuid.UUID,
    body: TimelineEventUpdate,
    session: SessionDep,
    current_user: User = _WRITE,
) -> TimelineEventRead:
    event = TimelineService(session).update_event(event_id, case_id, body, actor=current_user)
    return TimelineEventRead.model_validate(event)


@router.delete("/{event_id}", status_code=204, summary="Delete a timeline event")
def delete_event(
    case_id: uuid.UUID,
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _MANAGE,
) -> None:
    TimelineService(session).delete_event(event_id, case_id, actor=current_user)


# ── Flags ────────────────────────────────────────────────────────────────────────

@router.post("/{event_id}/pin", response_model=TimelineEventRead, summary="Pin/unpin an event")
def pin_event(
    case_id: uuid.UUID,
    event_id: uuid.UUID,
    body: TimelinePinRequest,
    session: SessionDep,
    current_user: User = _WRITE,
) -> TimelineEventRead:
    event = TimelineService(session).set_pinned(event_id, case_id, body.pinned, actor=current_user)
    return TimelineEventRead.model_validate(event)


@router.post(
    "/{event_id}/bookmark",
    response_model=TimelineEventRead,
    summary="Bookmark/unbookmark an event",
)
def bookmark_event(
    case_id: uuid.UUID,
    event_id: uuid.UUID,
    body: TimelineBookmarkRequest,
    session: SessionDep,
    current_user: User = _WRITE,
) -> TimelineEventRead:
    event = TimelineService(session).set_bookmarked(
        event_id, case_id, body.bookmarked, actor=current_user
    )
    return TimelineEventRead.model_validate(event)


@router.post(
    "/{event_id}/verify",
    response_model=TimelineEventRead,
    summary="Set the verification status of an event",
)
def verify_event(
    case_id: uuid.UUID,
    event_id: uuid.UUID,
    body: TimelineVerifyRequest,
    session: SessionDep,
    current_user: User = _MANAGE,
) -> TimelineEventRead:
    event = TimelineService(session).set_verification(
        event_id, case_id, body.status, actor=current_user
    )
    return TimelineEventRead.model_validate(event)


@router.post("/{event_id}/split", summary="Split a merged event back into its parts")
def split_event(
    case_id: uuid.UUID,
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _MANAGE,
) -> dict:
    count = TimelineService(session).split_event(event_id, case_id, actor=current_user)
    return {"restored": count}


# ── Comments ─────────────────────────────────────────────────────────────────────

@router.get(
    "/{event_id}/comments",
    response_model=list[TimelineCommentRead],
    summary="List comments on an event",
)
def list_comments(
    case_id: uuid.UUID,
    event_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> list[TimelineCommentRead]:
    comments = TimelineService(session).list_comments(event_id, case_id)
    return [TimelineCommentRead.model_validate(c) for c in comments]


@router.post(
    "/{event_id}/comments",
    response_model=TimelineCommentRead,
    status_code=201,
    summary="Add a comment to an event",
)
def add_comment(
    case_id: uuid.UUID,
    event_id: uuid.UUID,
    body: TimelineCommentCreate,
    session: SessionDep,
    current_user: User = _WRITE,
) -> TimelineCommentRead:
    comment = TimelineService(session).add_comment(
        event_id, case_id, body.body, actor=current_user
    )
    return TimelineCommentRead.model_validate(comment)
