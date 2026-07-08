"""AI Intelligence Engine routes.

All routes are case-scoped — every request must belong to an authorized case.
AI never fabricates evidence; all responses reference source evidence items.
"""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import RequirePermission, SessionDep
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.schemas.ai import (
    AiChatMessageRead,
    CaseSummaryRead,
    ChatHistoryResponse,
    ChatMessageRequest,
    EntityListResponse,
    EvidenceEntityRead,
    EvidenceKeywordRead,
    EvidenceSummaryRead,
    EvidenceTimelineEventRead,
    GraphResponse,
    KeywordListResponse,
    ProcessingStatusRead,
    SearchResponse,
    TimelineListResponse,
)
from app.services.ai_intelligence import AIIntelligenceService

router = APIRouter(prefix="/cases/{case_id}/ai", tags=["ai"])

_READ = RequirePermission("evidence:read")


# ── Case summary ───────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=CaseSummaryRead | None,
    summary="Get AI-generated case summary",
)
def get_case_summary(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> CaseSummaryRead | None:
    svc = AIIntelligenceService(session)
    summary = svc.get_case_summary(case_id)
    if not summary:
        return None
    return CaseSummaryRead.model_validate(summary)


@router.post(
    "/summary/regenerate",
    response_model=CaseSummaryRead | None,
    summary="Regenerate AI case summary",
)
def regenerate_case_summary(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> CaseSummaryRead | None:
    svc = AIIntelligenceService(session)
    try:
        summary = svc.regenerate_case_summary(case_id)
    except NotFoundError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Case not found.")
    if not summary:
        return None
    return CaseSummaryRead.model_validate(summary)


# ── Chat ───────────────────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=AiChatMessageRead,
    summary="Send a message to the AI assistant",
)
def send_chat_message(
    case_id: uuid.UUID,
    body: ChatMessageRequest,
    session: SessionDep,
    current_user: User = _READ,
) -> AiChatMessageRead:
    svc = AIIntelligenceService(session)
    try:
        msg = svc.chat(case_id, body.message, user_id=current_user.id)
    except NotFoundError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Case not found.")
    return AiChatMessageRead.model_validate(msg)


@router.get(
    "/chat/history",
    response_model=ChatHistoryResponse,
    summary="Get AI chat history for a case",
)
def get_chat_history(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> ChatHistoryResponse:
    svc = AIIntelligenceService(session)
    items, total = svc.get_chat_history(case_id, page=page, page_size=page_size)
    return ChatHistoryResponse(
        items=[AiChatMessageRead.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


# ── Entities ───────────────────────────────────────────────────────────────────

@router.get(
    "/entities",
    response_model=EntityListResponse,
    summary="List entities extracted across all case evidence",
)
def list_entities(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
    entity_type: str | None = Query(None, description="Filter by entity type"),
    q: str | None = Query(None, description="Search entity values"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> EntityListResponse:
    svc = AIIntelligenceService(session)
    items, total = svc.list_entities(
        case_id, entity_type=entity_type, q=q, page=page, page_size=page_size
    )
    return EntityListResponse(
        items=[EvidenceEntityRead.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


# ── Keywords ───────────────────────────────────────────────────────────────────

@router.get(
    "/keywords",
    response_model=KeywordListResponse,
    summary="List keywords extracted across all case evidence",
)
def list_keywords(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> KeywordListResponse:
    svc = AIIntelligenceService(session)
    items, total = svc.list_keywords(case_id, page=page, page_size=page_size)
    return KeywordListResponse(
        items=[EvidenceKeywordRead.model_validate(kw) for kw in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


# ── Timeline ───────────────────────────────────────────────────────────────────

@router.get(
    "/timeline",
    response_model=TimelineListResponse,
    summary="List timeline events extracted across all case evidence",
)
def list_timeline(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
    event_type: str | None = Query(None, description="Filter by event type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> TimelineListResponse:
    svc = AIIntelligenceService(session)
    items, total = svc.list_timeline(
        case_id, event_type=event_type, page=page, page_size=page_size
    )
    return TimelineListResponse(
        items=[EvidenceTimelineEventRead.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


# ── Search ─────────────────────────────────────────────────────────────────────

@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Full-text / semantic search across case evidence",
)
def search_evidence(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
    q: str = Query(..., min_length=1, description="Search query"),
) -> SearchResponse:
    svc = AIIntelligenceService(session)
    results = svc.search_evidence(case_id, q)
    from app.schemas.ai import SearchResultItem
    return SearchResponse(
        query=q,
        results=[SearchResultItem(**r) for r in results],
        total=len(results),
    )


# ── Relationship graph ─────────────────────────────────────────────────────────

@router.get(
    "/graph",
    response_model=GraphResponse,
    summary="Entity co-occurrence relationship graph data",
)
def get_relationship_graph(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
    max_nodes: int = Query(80, ge=10, le=150, description="Max entity nodes to include"),
) -> GraphResponse:
    svc = AIIntelligenceService(session)
    data = svc.get_relationship_graph(case_id, max_nodes=max_nodes)
    return GraphResponse(
        nodes=data["nodes"],
        edges=data["edges"],
        node_count=len(data["nodes"]),
        edge_count=len(data["edges"]),
    )


# ── Per-evidence AI data ───────────────────────────────────────────────────────

@router.get(
    "/evidence/{evidence_id}/summary",
    response_model=EvidenceSummaryRead | None,
    summary="AI summary for a single evidence item",
)
def get_evidence_ai_summary(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> EvidenceSummaryRead | None:
    svc = AIIntelligenceService(session)
    summary = svc.get_evidence_summary(evidence_id)
    if not summary:
        return None
    return EvidenceSummaryRead.model_validate(summary)


@router.get(
    "/evidence/{evidence_id}/entities",
    response_model=list[EvidenceEntityRead],
    summary="Entities extracted from a specific evidence item",
)
def get_evidence_entities(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> list[EvidenceEntityRead]:
    svc = AIIntelligenceService(session)
    entities = svc.get_evidence_entities(evidence_id)
    return [EvidenceEntityRead.model_validate(e) for e in entities]


@router.get(
    "/evidence/{evidence_id}/keywords",
    response_model=list[EvidenceKeywordRead],
    summary="Keywords from a specific evidence item",
)
def get_evidence_keywords(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> list[EvidenceKeywordRead]:
    svc = AIIntelligenceService(session)
    kws = svc.get_evidence_keywords(evidence_id)
    return [EvidenceKeywordRead.model_validate(k) for k in kws]


@router.get(
    "/evidence/{evidence_id}/timeline",
    response_model=list[EvidenceTimelineEventRead],
    summary="Timeline events from a specific evidence item",
)
def get_evidence_timeline(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> list[EvidenceTimelineEventRead]:
    svc = AIIntelligenceService(session)
    events = svc.get_evidence_timeline(evidence_id)
    return [EvidenceTimelineEventRead.model_validate(e) for e in events]


# ── Processing status ──────────────────────────────────────────────────────────

@router.get(
    "/processing-status",
    response_model=list[ProcessingStatusRead],
    summary="Processing pipeline status for all evidence in the case",
)
def get_processing_status(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> list[ProcessingStatusRead]:
    svc = AIIntelligenceService(session)
    statuses = svc.get_processing_status(case_id)
    return [ProcessingStatusRead(**s) for s in statuses]
