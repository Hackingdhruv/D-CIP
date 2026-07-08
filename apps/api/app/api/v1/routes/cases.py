"""Case management endpoints."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.core.dependencies import RequirePermission, SessionDep
from app.models.user import User
from app.schemas.case import (
    CaseActivityRead,
    CaseAssignRequest,
    CaseCreate,
    CaseImportPreview,
    CaseListResponse,
    CaseNoteCreate,
    CaseNoteRead,
    CaseNoteUpdate,
    CaseRead,
    CaseReadSlim,
    CaseTaskCreate,
    CaseTaskRead,
    CaseTaskUpdate,
    CaseUpdate,
)
from app.services.case import CaseService

router = APIRouter(prefix="/cases", tags=["cases"])

_READ = RequirePermission("case:read")
_CREATE = RequirePermission("case:create")
_UPDATE = RequirePermission("case:update")
_DELETE = RequirePermission("case:delete")
_ASSIGN = RequirePermission("case:assign")


@router.get("", response_model=CaseListResponse, summary="List cases")
def list_cases(
    session: SessionDep,
    current_user: User = _READ,
    q: str | None = Query(default=None, description="Search term"),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    category: str | None = Query(default=None),
    is_starred: bool | None = Query(default=None),
    include_archived: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> CaseListResponse:
    svc = CaseService(session)
    return svc.list_cases(
        q=q,
        status=status,
        priority=priority,
        category=category,
        is_starred=is_starred,
        include_archived=include_archived,
        viewer=current_user,
        page=page,
        page_size=page_size,
    )


@router.post(
    "", response_model=CaseRead, status_code=status.HTTP_201_CREATED, summary="Create case"
)
def create_case(
    body: CaseCreate,
    session: SessionDep,
    current_user: User = _CREATE,
) -> CaseRead:
    svc = CaseService(session)
    case = svc.create(body, actor=current_user)
    return CaseRead.model_validate(case)


_IMPORT_ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "txt", "csv", "json", "xlsx", "xls", "eml", "msg", "log", "md",
}

_IMPORT_MAX_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post(
    "/import/preview",
    response_model=CaseImportPreview,
    summary="Parse a document and extract case fields for review",
)
async def import_case_preview(
    file: UploadFile = File(...),
    current_user: User = _CREATE,
) -> CaseImportPreview:
    filename = file.filename or "document"
    ext = Path(filename).suffix.lstrip(".").lower()

    if ext not in _IMPORT_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '.{ext}'. Supported: {', '.join(sorted(_IMPORT_ALLOWED_EXTENSIONS))}",
        )

    content = await file.read(_IMPORT_MAX_BYTES + 1)
    if len(content) > _IMPORT_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 20 MB import limit.",
        )

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        from app.services.text_extraction import extract_text
        text = extract_text(tmp_path, file.content_type or "", ext) or ""
    finally:
        tmp_path.unlink(missing_ok=True)

    from app.services.ai_provider import parse_document_for_case
    result = parse_document_for_case(filename, text)

    if result:
        return CaseImportPreview(
            title=result.title,
            description=result.description,
            priority=result.priority,
            category=result.category,
            tags=result.tags,
            notes=result.notes,
            raw_text_excerpt=text[:600],
            ai_used=True,
        )

    # Non-AI fallback: derive title from filename, use first 1000 chars as description
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    title = stem[:120] if stem else "Imported Case"
    return CaseImportPreview(
        title=title,
        description=text[:1000] or None,
        raw_text_excerpt=text[:600],
        ai_used=False,
    )


@router.get("/{case_id}", response_model=CaseRead, summary="Get case workspace")
def get_case(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> CaseRead:
    svc = CaseService(session)
    case = svc.get(case_id, viewer=current_user)
    return CaseRead.model_validate(case)


@router.put("/{case_id}", response_model=CaseRead, summary="Update case")
def update_case(
    case_id: uuid.UUID,
    body: CaseUpdate,
    session: SessionDep,
    current_user: User = _UPDATE,
) -> CaseRead:
    svc = CaseService(session)
    case = svc.update(case_id, body, actor=current_user)
    return CaseRead.model_validate(case)


@router.delete(
    "/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete case",
)
def delete_case(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _DELETE,
) -> None:
    svc = CaseService(session)
    svc.soft_delete(case_id, actor=current_user)


@router.post("/{case_id}/archive", response_model=CaseRead, summary="Archive case")
def archive_case(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _UPDATE,
) -> CaseRead:
    svc = CaseService(session)
    case = svc.archive(case_id, actor=current_user)
    return CaseRead.model_validate(case)


@router.post("/{case_id}/restore", response_model=CaseRead, summary="Restore archived case")
def restore_case(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _UPDATE,
) -> CaseRead:
    svc = CaseService(session)
    case = svc.restore(case_id, actor=current_user)
    return CaseRead.model_validate(case)


@router.post("/{case_id}/star", response_model=CaseRead, summary="Star a case")
def star_case(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> CaseRead:
    svc = CaseService(session)
    case = svc.star(case_id, actor=current_user)
    return CaseRead.model_validate(case)


@router.post("/{case_id}/unstar", response_model=CaseRead, summary="Unstar a case")
def unstar_case(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> CaseRead:
    svc = CaseService(session)
    case = svc.unstar(case_id, actor=current_user)
    return CaseRead.model_validate(case)


@router.put(
    "/{case_id}/assignments",
    response_model=CaseRead,
    summary="Set case team assignments",
)
def assign_users(
    case_id: uuid.UUID,
    body: CaseAssignRequest,
    session: SessionDep,
    current_user: User = _ASSIGN,
) -> CaseRead:
    svc = CaseService(session)
    case = svc.assign_users(case_id, body.assignments, actor=current_user)
    return CaseRead.model_validate(case)


@router.get(
    "/{case_id}/activities",
    response_model=list[CaseActivityRead],
    summary="List case activity feed",
)
def list_activities(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> list[CaseActivityRead]:
    svc = CaseService(session)
    items, _ = svc.list_activities(case_id, viewer=current_user, page=page, page_size=page_size)
    return [CaseActivityRead.model_validate(a) for a in items]


# ── Tasks ──────────────────────────────────────────────────────────────────────


@router.get(
    "/{case_id}/tasks",
    response_model=list[CaseTaskRead],
    summary="List case tasks",
)
def list_tasks(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> list[CaseTaskRead]:
    svc = CaseService(session)
    case = svc.get(case_id, viewer=current_user)
    return [CaseTaskRead.model_validate(t) for t in case.tasks]


@router.post(
    "/{case_id}/tasks",
    response_model=CaseTaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
)
def create_task(
    case_id: uuid.UUID,
    body: CaseTaskCreate,
    session: SessionDep,
    current_user: User = _UPDATE,
) -> CaseTaskRead:
    svc = CaseService(session)
    task = svc.create_task(case_id, body, actor=current_user)
    return CaseTaskRead.model_validate(task)


@router.put(
    "/{case_id}/tasks/{task_id}",
    response_model=CaseTaskRead,
    summary="Update task",
)
def update_task(
    case_id: uuid.UUID,
    task_id: uuid.UUID,
    body: CaseTaskUpdate,
    session: SessionDep,
    current_user: User = _UPDATE,
) -> CaseTaskRead:
    svc = CaseService(session)
    task = svc.update_task(case_id, task_id, body, actor=current_user)
    return CaseTaskRead.model_validate(task)


@router.delete(
    "/{case_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
)
def delete_task(
    case_id: uuid.UUID,
    task_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _UPDATE,
) -> None:
    svc = CaseService(session)
    svc.delete_task(case_id, task_id, actor=current_user)


# ── Notes ──────────────────────────────────────────────────────────────────────


@router.get(
    "/{case_id}/notes",
    response_model=list[CaseNoteRead],
    summary="List case notes",
)
def list_notes(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> list[CaseNoteRead]:
    svc = CaseService(session)
    case = svc.get(case_id, viewer=current_user)
    return [CaseNoteRead.model_validate(n) for n in case.notes]


@router.post(
    "/{case_id}/notes",
    response_model=CaseNoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create note",
)
def create_note(
    case_id: uuid.UUID,
    body: CaseNoteCreate,
    session: SessionDep,
    current_user: User = _UPDATE,
) -> CaseNoteRead:
    svc = CaseService(session)
    note = svc.create_note(case_id, body, actor=current_user)
    return CaseNoteRead.model_validate(note)


@router.put(
    "/{case_id}/notes/{note_id}",
    response_model=CaseNoteRead,
    summary="Update note",
)
def update_note(
    case_id: uuid.UUID,
    note_id: uuid.UUID,
    body: CaseNoteUpdate,
    session: SessionDep,
    current_user: User = _UPDATE,
) -> CaseNoteRead:
    svc = CaseService(session)
    note = svc.update_note(case_id, note_id, body, actor=current_user)
    return CaseNoteRead.model_validate(note)


@router.delete(
    "/{case_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete note",
)
def delete_note(
    case_id: uuid.UUID,
    note_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _UPDATE,
) -> None:
    svc = CaseService(session)
    svc.delete_note(case_id, note_id, actor=current_user)
