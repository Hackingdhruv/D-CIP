"""Evidence routes — Digital Evidence Intelligence Engine.

All routes are nested under /cases/{case_id}/evidence so that case-level
access control is naturally enforced: the caller must already have permission
to reach a case's evidence.

Upload is intentionally async to stream large files without loading them into
memory.  The sync EvidenceService is called only after the file is on disk.
"""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.core.dependencies import RequirePermission, SessionDep
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.schemas.evidence import (
    EvidenceCustodyEventRead,
    EvidenceListResponse,
    EvidencePreviewResponse,
    EvidenceRead,
    EvidenceReadSlim,
    EvidenceUpdate,
    EvidenceVerifyResponse,
)
from app.services.evidence import EvidenceService, detect_mime_type
from app.storage import get_storage

router = APIRouter(prefix="/cases/{case_id}/evidence", tags=["evidence"])

_READ = RequirePermission("evidence:read")
_UPLOAD = RequirePermission("evidence:upload")
_UPDATE = RequirePermission("evidence:update")
_DELETE = RequirePermission("evidence:delete")

_MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

# MIME types allowed for upload — unknown binaries are allowed via octet-stream
_ALLOWED_EXTENSIONS = {
    "pdf", "docx", "xlsx", "pptx", "txt", "csv", "json", "xml",
    "eml", "msg", "zip",
    "png", "jpg", "jpeg", "gif", "tiff",
    "mp4", "avi", "mov",
    "mp3", "wav",
    "log",
}

# Text-based MIME types for in-browser preview
_TEXT_PREVIEW_TYPES = {
    "text/plain", "text/csv", "application/json", "text/xml",
    "application/xml", "text/x-log", "text/html", "text/markdown",
}
_TEXT_PREVIEW_EXTS = {"txt", "log", "csv", "json", "xml", "md", "ini", "cfg", "yaml", "yml"}


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _stream_to_disk(file: UploadFile, dest: Path, max_bytes: int) -> tuple[int, str]:
    """Async-stream *file* to *dest*, computing SHA-256 on the fly.

    Aborts and raises HTTP 413 if the upload exceeds *max_bytes* — checked
    during streaming so we never store an oversized file at all.

    Returns ``(bytes_written, sha256_hex)``.
    """
    import hashlib
    hasher = hashlib.sha256()
    size = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(dest, "wb") as fp:
            while True:
                chunk = await file.read(65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    # Stop immediately; caller cleans up the partial file.
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds the {max_bytes // (1024 * 1024)} MB limit.",
                    )
                fp.write(chunk)
                hasher.update(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    return size, hasher.hexdigest()


def _build_storage_path(case_id: uuid.UUID, evidence_id: uuid.UUID, ext: str) -> str:
    safe_ext = ext.lower().lstrip(".") or "bin"
    return f"evidence/{case_id}/{evidence_id}.{safe_ext}"


# ── Upload ─────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=list[EvidenceRead],
    status_code=status.HTTP_201_CREATED,
    summary="Upload evidence files",
)
async def upload_evidence(
    case_id: uuid.UUID,
    files: list[UploadFile] = File(..., description="One or more evidence files"),
    session: SessionDep = ...,
    current_user: User = _UPLOAD,
) -> list[EvidenceRead]:
    """Upload one or more files as evidence.

    Files are streamed to disk while computing SHA-256.  Duplicate files
    (same hash within the same case) are detected and the existing record is
    returned without creating a duplicate.
    """
    svc = EvidenceService(session)
    results: list[EvidenceRead] = []

    for file in files:
        filename = file.filename or "unknown"
        ext = Path(filename).suffix.lower().lstrip(".")
        mime_type = detect_mime_type(filename, file.content_type)

        # Generate a unique storage path before we know the hash
        evidence_id = uuid.uuid4()
        storage_path = _build_storage_path(case_id, evidence_id, ext)
        dest = Path("uploads") / storage_path

        # Stream to disk — size is enforced during streaming, not after.
        size, sha256 = await _stream_to_disk(file, dest, _MAX_FILE_SIZE)

        evidence, is_new = svc.record_upload(
            case_id,
            original_filename=filename,
            storage_path=storage_path,
            file_size=size,
            mime_type=mime_type,
            file_extension=ext,
            sha256_hash=sha256,
            actor=current_user,
        )

        # Duplicate detected — discard the file we just wrote
        if not is_new:
            dest.unlink(missing_ok=True)

        results.append(EvidenceRead.model_validate(evidence))

    return results


# ── List ───────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=EvidenceListResponse,
    summary="List evidence for a case",
)
def list_evidence(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
    q: str | None = Query(None, description="Search by filename"),
    mime_category: str | None = Query(None, description="Filter by MIME category, e.g. 'image'"),
    file_extension: str | None = Query(None, description="Filter by file extension"),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> EvidenceListResponse:
    svc = EvidenceService(session)
    return svc.list_evidence(
        case_id,
        q=q,
        mime_category=mime_category,
        status=status_filter,
        file_extension=file_extension,
        page=page,
        page_size=page_size,
    )


# ── Single evidence ────────────────────────────────────────────────────────────

@router.get(
    "/{evidence_id}",
    response_model=EvidenceRead,
    summary="Get evidence detail",
)
def get_evidence(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> EvidenceRead:
    svc = EvidenceService(session)
    evidence = svc.get(evidence_id, case_id)
    return EvidenceRead.model_validate(evidence)


@router.put(
    "/{evidence_id}",
    response_model=EvidenceRead,
    summary="Update evidence metadata",
)
def update_evidence(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    body: EvidenceUpdate,
    session: SessionDep,
    current_user: User = _UPDATE,
) -> EvidenceRead:
    svc = EvidenceService(session)
    evidence = svc.update(evidence_id, case_id, body, actor=current_user)
    return EvidenceRead.model_validate(evidence)


@router.delete(
    "/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete evidence",
)
def delete_evidence(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _DELETE,
) -> None:
    svc = EvidenceService(session)
    svc.delete(evidence_id, case_id, actor=current_user)


# ── Download ───────────────────────────────────────────────────────────────────

@router.get(
    "/{evidence_id}/download",
    summary="Download original evidence file",
)
def download_evidence(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> FileResponse:
    svc = EvidenceService(session)
    evidence = svc.get(evidence_id, case_id)

    file_path = Path("uploads") / evidence.storage_path
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage.",
        )

    svc.log_download(evidence.id, actor_id=current_user.id)

    return FileResponse(
        path=str(file_path),
        filename=evidence.original_filename,
        media_type=evidence.mime_type,
    )


# ── Preview ────────────────────────────────────────────────────────────────────

@router.get(
    "/{evidence_id}/preview",
    response_model=EvidencePreviewResponse,
    summary="Get a browser-safe preview of evidence",
)
def preview_evidence(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> EvidencePreviewResponse:
    svc = EvidenceService(session)
    evidence = svc.get(evidence_id, case_id)

    file_path = Path("uploads") / evidence.storage_path
    if not file_path.exists():
        return EvidencePreviewResponse(type="unavailable", reason="File not in storage.")

    mime = evidence.mime_type
    ext = evidence.file_extension.lower()

    if mime.startswith("image/"):
        return EvidencePreviewResponse(type="image", url=evidence.url)

    if mime == "application/pdf":
        return EvidencePreviewResponse(type="pdf", url=evidence.url)

    if mime in _TEXT_PREVIEW_TYPES or ext in _TEXT_PREVIEW_EXTS:
        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                content = f.read(8192)
            return EvidencePreviewResponse(
                type="text",
                content=content,
                truncated=evidence.file_size > 8192,
            )
        except Exception as exc:
            return EvidencePreviewResponse(
                type="unavailable", reason=f"Cannot read file: {exc}"
            )

    return EvidencePreviewResponse(
        type="unavailable",
        reason=f"No preview available for {mime or ext} files.",
    )


# ── Hash verify ────────────────────────────────────────────────────────────────

@router.post(
    "/{evidence_id}/verify",
    response_model=EvidenceVerifyResponse,
    summary="Verify SHA-256 hash integrity",
)
def verify_evidence(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> EvidenceVerifyResponse:
    svc = EvidenceService(session)
    result = svc.verify_hash(evidence_id, case_id, actor=current_user)
    return EvidenceVerifyResponse(**result)


# ── Chain of custody ───────────────────────────────────────────────────────────

@router.get(
    "/{evidence_id}/custody",
    response_model=list[EvidenceCustodyEventRead],
    summary="Chain of custody event log",
)
def get_custody(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> list[EvidenceCustodyEventRead]:
    svc = EvidenceService(session)
    events, _ = svc.get_custody(
        evidence_id, case_id, page=page, page_size=page_size
    )
    return [EvidenceCustodyEventRead.model_validate(e) for e in events]
