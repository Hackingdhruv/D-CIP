"""Unit tests for CaseService business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models.case import Case, CaseStatus
from app.models.case_task import CaseTask, TaskStatus
from app.models.case_note import CaseNote
from app.models.user import User
from app.services.case import CaseService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(
    *,
    permissions: list[str] | None = None,
    user_id: uuid.UUID | None = None,
) -> User:
    u = User(
        email="investigator@example.com",
        username="investigator",
        full_name="Test Investigator",
        password_hash="$2b$12$fake",
    )
    u.id = user_id or uuid.uuid4()
    u.roles = []
    u.refresh_tokens = []
    u.password_reset_tokens = []
    u.sessions = []
    u.audit_events = []
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    # Patch permissions property via a role-like mock
    if permissions:
        role = MagicMock()
        role.permissions = [
            MagicMock(**{"resource": p.split(":")[0], "action": p.split(":")[1]})
            for p in permissions
        ]
        u.roles = [role]
    return u


def _make_case(
    *,
    owner_id: uuid.UUID | None = None,
    is_private: bool = False,
    status: str = CaseStatus.OPEN.value,
) -> Case:
    c = Case(
        reference_number="CASE-2026-0001",
        title="Test Investigation",
        description="A test case",
        status=status,
        priority="medium",
        is_private=is_private,
        owner_id=owner_id or uuid.uuid4(),
        created_by_id=owner_id or uuid.uuid4(),
    )
    c.id = uuid.uuid4()
    c.tags = []
    c.is_starred = False
    c.assignments = []
    c.tasks = []
    c.notes = []
    c.created_at = datetime.now(timezone.utc)
    c.updated_at = datetime.now(timezone.utc)
    c.closed_at = None
    c.archived_at = None
    c.deleted_at = None
    return c


def _make_service() -> tuple[CaseService, MagicMock]:
    db = MagicMock()
    db.commit = MagicMock()
    db.add = MagicMock()
    db.flush = MagicMock()
    db.refresh = MagicMock()
    db.delete = MagicMock()
    svc = CaseService.__new__(CaseService)
    svc.session = db
    svc._cases = MagicMock()
    svc._tasks = MagicMock()
    svc._notes = MagicMock()
    svc._activities = MagicMock()
    svc._users = MagicMock()
    return svc, db


# ── create() ─────────────────────────────────────────────────────────────────

class TestCreateCase:
    def test_create_generates_reference(self) -> None:
        svc, db = _make_service()
        actor = _make_user()
        svc._cases.generate_reference_number.return_value = "CASE-2026-0001"
        svc._activities.log.return_value = MagicMock()
        db.refresh.return_value = None

        from app.schemas.case import CaseCreate
        data = CaseCreate(title="New Investigation")
        svc.create(data, actor=actor)

        svc._activities.log.assert_called_once()
        db.commit.assert_called_once()
        svc._cases.generate_reference_number.assert_called_once()


# ── get() ─────────────────────────────────────────────────────────────────────

class TestGetCase:
    def test_not_found_raises(self) -> None:
        svc, _ = _make_service()
        svc._cases.get_active.return_value = None
        with pytest.raises(NotFoundError):
            svc.get(uuid.uuid4(), viewer=_make_user())

    def test_private_case_inaccessible_to_non_owner(self) -> None:
        svc, _ = _make_service()
        owner = _make_user()
        viewer = _make_user()  # different user, no permissions

        case = _make_case(owner_id=owner.id, is_private=True)
        svc._cases.get_active.return_value = case

        with pytest.raises(PermissionDeniedError):
            svc.get(case.id, viewer=viewer)

    def test_private_case_accessible_to_owner(self) -> None:
        svc, _ = _make_service()
        owner = _make_user()
        case = _make_case(owner_id=owner.id, is_private=True)
        svc._cases.get_active.return_value = case

        result = svc.get(case.id, viewer=owner)
        assert result is case

    def test_public_case_accessible_to_anyone(self) -> None:
        svc, _ = _make_service()
        viewer = _make_user()
        case = _make_case(is_private=False)
        svc._cases.get_active.return_value = case

        result = svc.get(case.id, viewer=viewer)
        assert result is case


# ── archive() / restore() ────────────────────────────────────────────────────

class TestArchiveRestore:
    def test_archive_already_archived_raises(self) -> None:
        svc, _ = _make_service()
        viewer = _make_user()
        case = _make_case(owner_id=viewer.id)
        case.archived_at = datetime.now(timezone.utc)
        svc._cases.get_active.return_value = case

        with pytest.raises(ConflictError, match="already archived"):
            svc.archive(case.id, actor=viewer)

    def test_restore_not_archived_raises(self) -> None:
        svc, _ = _make_service()
        viewer = _make_user()
        case = _make_case(owner_id=viewer.id)
        case.archived_at = None
        svc._cases.get_active.return_value = case

        with pytest.raises(ConflictError, match="not archived"):
            svc.restore(case.id, actor=viewer)

    def test_archive_sets_fields(self) -> None:
        svc, db = _make_service()
        actor = _make_user()
        case = _make_case(owner_id=actor.id)
        svc._cases.get_active.return_value = case
        svc._activities.log.return_value = MagicMock()
        db.refresh.side_effect = lambda obj: None

        svc.archive(case.id, actor=actor)
        assert case.archived_at is not None
        assert case.status == CaseStatus.ARCHIVED.value


# ── create_task() ─────────────────────────────────────────────────────────────

class TestCreateTask:
    def test_case_not_found_raises(self) -> None:
        svc, _ = _make_service()
        svc._cases.get_active.return_value = None

        from app.schemas.case import CaseTaskCreate
        with pytest.raises(NotFoundError):
            svc.create_task(uuid.uuid4(), CaseTaskCreate(title="Task"), actor=_make_user())

    def test_creates_task_and_logs_activity(self) -> None:
        svc, db = _make_service()
        actor = _make_user()
        case = _make_case(owner_id=actor.id)
        svc._cases.get_active.return_value = case
        svc._activities.log.return_value = MagicMock()
        svc._users.get_active.return_value = None  # no assignee lookup needed
        db.refresh.return_value = None

        from app.schemas.case import CaseTaskCreate
        svc.create_task(case.id, CaseTaskCreate(title="Investigate logs"), actor=actor)
        svc._activities.log.assert_called_once()
        db.commit.assert_called_once()


# ── create_note() ─────────────────────────────────────────────────────────────

class TestCreateNote:
    def test_creates_note_and_logs_activity(self) -> None:
        svc, db = _make_service()
        actor = _make_user()
        case = _make_case(owner_id=actor.id)
        svc._cases.get_active.return_value = case
        svc._activities.log.return_value = MagicMock()
        db.refresh.side_effect = lambda obj: None

        from app.schemas.case import CaseNoteCreate
        svc.create_note(case.id, CaseNoteCreate(title="Evidence note", content="Details"), actor=actor)
        svc._activities.log.assert_called_once()
        db.commit.assert_called_once()
