"""Universal search route.

Requires evidence:read permission. Results are automatically scoped to the
cases the requesting user can access.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import RequirePermission, SessionDep
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResponse, SuggestionsResponse, SearchSuggestion
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])

_READ = RequirePermission("evidence:read")


@router.post("", response_model=SearchResponse)
def search(
    body: SearchRequest,
    session: SessionDep,
    current_user: User = _READ,
) -> SearchResponse:
    """Search across all content types accessible to the requesting user."""
    svc = SearchService(session, current_user)
    result = svc.search(
        query=body.query,
        filters=body.filters,
        page=body.page,
        page_size=body.page_size,
    )
    return SearchResponse(**result)


@router.get("/suggestions", response_model=SuggestionsResponse)
def suggestions(
    session: SessionDep,
    q: str = Query(..., min_length=2, max_length=100),
    current_user: User = _READ,
) -> SuggestionsResponse:
    """Return autocomplete suggestions for a partial query."""
    svc = SearchService(session, current_user)
    raw = svc.suggestions(q)
    return SuggestionsResponse(
        suggestions=[SearchSuggestion(**s) for s in raw]
    )
