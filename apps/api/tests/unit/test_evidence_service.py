"""Unit tests for EvidenceService business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.models.evidence import Evidence, EvidenceStatus
from app.models.user import User
from app.schemas.evidence import EvidenceUpdate
from app.services.evidence import EvidenceService, detect_mime_type, extract_metadata


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_user() -> User:
    u = User(
        email="analyst@example.com",
        username="analyst",
        full_name="Test Analyst",
        password_hash="$2b$12$fake",
    )
    u.id = uuid.uuid4()
    u.roles = []
    u.refresh_tokens = []
    u.password_reset_tokens = []
    u.sessions = []
    u.audit_events = []
    u.avatar_url = None
    u.last_login_at = None
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    return u


def _make_evidence(*, case_id: uuid.UUID | None = None, uploaded_by_id: uuid.UUID | None = None) -> MagicMock:
    ev = MagicMock(spec=Evidence)
    ev.id = uuid.uuid4()
    ev.case_id = case_id or uuid.uuid4()
    ev.original_filename = "invoice.pdf"
    ev.storage_path = f"evidence/{ev.case_id}/{ev.id}.pdf"
    ev.file_size = 12345
    ev.mime_type = "application/pdf"
    ev.file_extension = "pdf"
    ev.sha256_hash = "a" * 64
    ev.status = EvidenceStatus.COMPLETED.value
    ev.tags = []
    ev.priority = "medium"
    ev.source = None
    ev.classification = None
    ev.notes = None
    ev.is_starred = False
    ev.deleted_at = None
    ev.processing_error = None
    ev.processing_started_at = None
    ev.processing_completed_at = None
    ev.extracted_metadata = {}
    ev.uploaded_by_id = uploaded_by_id or uuid.uuid4()
    ev.created_at = datetime.now(timezone.utc)
    ev.updated_at = datetime.now(timezone.utc)
    ev.is_deleted = False
    ev.url = f"/uploads/{ev.storage_path}"
    return ev


def _make_service() -> tuple[EvidenceService, MagicMock]:
    db = MagicMock()
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock(return_value=None)
    storage = MagicMock()
    svc = EvidenceService.__new__(EvidenceService)
    svc.session = db
    svc._evidence = MagicMock()
    svc._custody = MagicMock()
    svc._cases = MagicMock()
    svc._storage = storage
    return svc, db


# ── detect_mime_type ───────────────────────────────────────────────────────────

class TestDetectMimeType:
    def test_detects_from_extension(self) -> None:
        assert detect_mime_type("report.pdf") == "application/pdf"

    def test_falls_back_to_hint(self) -> None:
        result = detect_mime_type("mystery_file", "text/plain")
        assert result == "text/plain"

    def test_defaults_to_octet_stream(self) -> None:
        result = detect_mime_type("mystery_file", None)
        assert result == "application/octet-stream"


# ── extract_metadata ───────────────────────────────────────────────────────────

class TestExtractMetadata:
    def test_returns_expected_keys(self) -> None:
        meta = extract_metadata(
            original_filename="test.csv",
            file_size=1024,
            sha256_hash="b" * 64,
            mime_type="text/csv",
            file_extension="csv",
        )
        assert meta["filename"] == "test.csv"
        assert meta["size_bytes"] == 1024
        assert meta["sha256"] == "b" * 64
        assert meta["mime_type"] == "text/csv"
        assert meta["extension"] == "csv"


# ── record_upload ──────────────────────────────────────────────────────────────

class TestRecordUpload:
    def test_case_not_found_raises(self) -> None:
        svc, _ = _make_service()
        svc._cases.get_active.return_value = None

        with pytest.raises(NotFoundError):
            svc.record_upload(
                uuid.uuid4(),
                original_filename="test.pdf",
                storage_path="evidence/x/y.pdf",
                file_size=100,
                mime_type="application/pdf",
                file_extension="pdf",
                sha256_hash="a" * 64,
                actor=_make_user(),
            )

    def test_duplicate_returns_existing_is_new_false(self) -> None:
        svc, _ = _make_service()
        case = MagicMock()
        case.id = uuid.uuid4()
        actor = _make_user()
        existing = _make_evidence(case_id=case.id)

        svc._cases.get_active.return_value = case
        svc._evidence.get_by_hash_in_case.return_value = existing

        result, is_new = svc.record_upload(
            case.id,
            original_filename="dup.pdf",
            storage_path="evidence/x/z.pdf",
            file_size=100,
            mime_type="application/pdf",
            file_extension="pdf",
            sha256_hash="a" * 64,
            actor=actor,
        )
        assert result is existing
        assert is_new is False
        svc._custody.log.assert_not_called()

    def test_new_upload_logs_custody_and_commits(self) -> None:
        svc, db = _make_service()
        case = MagicMock()
        case.id = uuid.uuid4()
        actor = _make_user()

        svc._cases.get_active.return_value = case
        svc._evidence.get_by_hash_in_case.return_value = None
        svc._custody.log.return_value = MagicMock()

        _, is_new = svc.record_upload(
            case.id,
            original_filename="new.pdf",
            storage_path="evidence/x/new.pdf",
            file_size=500,
            mime_type="application/pdf",
            file_extension="pdf",
            sha256_hash="c" * 64,
            actor=actor,
        )
        assert is_new is True
        db.add.assert_called_once()
        svc._custody.log.assert_called_once()
        db.commit.assert_called_once()


# ── get ───────────────────────────────────────────────────────────────────────

class TestGetEvidence:
    def test_not_found_raises(self) -> None:
        svc, _ = _make_service()
        svc._evidence.get_for_case.return_value = None

        with pytest.raises(NotFoundError):
            svc.get(uuid.uuid4(), uuid.uuid4())

    def test_returns_evidence(self) -> None:
        svc, _ = _make_service()
        ev = _make_evidence()
        svc._evidence.get_for_case.return_value = ev

        result = svc.get(ev.id, ev.case_id)
        assert result is ev


# ── update ────────────────────────────────────────────────────────────────────

class TestUpdateEvidence:
    def test_not_found_raises(self) -> None:
        svc, _ = _make_service()
        svc._evidence.get_for_case.return_value = None

        with pytest.raises(NotFoundError):
            svc.update(uuid.uuid4(), uuid.uuid4(), EvidenceUpdate(), actor=_make_user())

    def test_update_tags_logs_custody(self) -> None:
        svc, db = _make_service()
        ev = _make_evidence()
        svc._evidence.get_for_case.return_value = ev
        svc._custody.log.return_value = MagicMock()

        svc.update(ev.id, ev.case_id, EvidenceUpdate(tags=["financial"]), actor=_make_user())

        svc._custody.log.assert_called_once()
        db.commit.assert_called_once()


# ── delete ────────────────────────────────────────────────────────────────────

class TestDeleteEvidence:
    def test_not_found_raises(self) -> None:
        svc, _ = _make_service()
        svc._evidence.get_for_case.return_value = None

        with pytest.raises(NotFoundError):
            svc.delete(uuid.uuid4(), uuid.uuid4(), actor=_make_user())

    def test_soft_deletes_and_logs(self) -> None:
        svc, db = _make_service()
        ev = _make_evidence()
        svc._evidence.get_for_case.return_value = ev
        svc._custody.log.return_value = MagicMock()

        svc.delete(ev.id, ev.case_id, actor=_make_user())

        svc._evidence.soft_delete.assert_called_once_with(ev)
        svc._custody.log.assert_called_once()
        db.commit.assert_called_once()


# ── verify_hash ───────────────────────────────────────────────────────────────

class TestVerifyHash:
    def test_matching_hash_returns_true(self) -> None:
        svc, db = _make_service()
        ev = _make_evidence()
        ev.sha256_hash = "d" * 64
        svc._evidence.get_for_case.return_value = ev
        svc._storage.compute_sha256.return_value = "d" * 64
        svc._custody.log.return_value = MagicMock()

        result = svc.verify_hash(ev.id, ev.case_id, actor=_make_user())

        assert result["matches"] is True
        assert result["original_hash"] == "d" * 64
        db.commit.assert_called_once()

    def test_mismatched_hash_returns_false(self) -> None:
        svc, _ = _make_service()
        ev = _make_evidence()
        ev.sha256_hash = "d" * 64
        svc._evidence.get_for_case.return_value = ev
        svc._storage.compute_sha256.return_value = "e" * 64
        svc._custody.log.return_value = MagicMock()

        result = svc.verify_hash(ev.id, ev.case_id, actor=_make_user())
        assert result["matches"] is False
