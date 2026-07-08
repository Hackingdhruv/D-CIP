"""Case repository — persistence layer for Case and related models."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import extract, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.case import Case, CaseStatus
from app.models.case_activity import CaseActivity
from app.models.case_assignment import CaseAssignment
from app.models.case_note import CaseNote
from app.models.case_task import CaseTask, TaskStatus
from app.repositories.base import BaseRepository


class CaseRepository(BaseRepository[Case]):
    model = Case

    def get_active(self, case_id: uuid.UUID) -> Case | None:
        stmt = (
            select(Case)
            .options(selectinload(Case.assignments))
            .where(Case.id == case_id, Case.deleted_at.is_(None))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_reference(self, ref: str) -> Case | None:
        stmt = select(Case).where(
            Case.reference_number == ref, Case.deleted_at.is_(None)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def generate_reference_number(self) -> str:
        year = datetime.now(timezone.utc).year
        count_stmt = select(func.count()).select_from(Case).where(
            extract("year", Case.created_at) == year
        )
        count = self.session.execute(count_stmt).scalar_one()
        return f"CASE-{year}-{str(count + 1).zfill(4)}"

    def search(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        owner_id: uuid.UUID | None = None,
        is_starred: bool | None = None,
        include_archived: bool = False,
        viewer_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Case], int]:
        base = select(Case).where(Case.deleted_at.is_(None))

        if not include_archived:
            base = base.where(Case.archived_at.is_(None))

        if q:
            term = f"%{q.lower()}%"
            base = base.where(
                or_(
                    func.lower(Case.title).like(term),
                    func.lower(Case.description).like(term),
                    func.lower(Case.reference_number).like(term),
                )
            )

        if status:
            base = base.where(Case.status == status)
        if priority:
            base = base.where(Case.priority == priority)
        if category:
            base = base.where(Case.category == category)
        if owner_id:
            base = base.where(Case.owner_id == owner_id)
        if is_starred is not None:
            base = base.where(Case.is_starred == is_starred)

        # Private case filter: only show private cases the viewer owns or is assigned to
        if viewer_id is not None:
            assigned_subq = (
                select(CaseAssignment.case_id)
                .where(CaseAssignment.user_id == viewer_id)
                .scalar_subquery()
            )
            base = base.where(
                or_(
                    Case.is_private.is_(False),
                    Case.owner_id == viewer_id,
                    Case.id.in_(assigned_subq),
                )
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        offset = (page - 1) * page_size
        stmt = base.order_by(Case.updated_at.desc()).offset(offset).limit(page_size)
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def soft_delete(self, case: Case) -> None:
        case.deleted_at = datetime.now(timezone.utc)
        self.session.flush()


class CaseTaskRepository(BaseRepository[CaseTask]):
    model = CaseTask

    def get_for_case(self, task_id: uuid.UUID, case_id: uuid.UUID) -> CaseTask | None:
        stmt = select(CaseTask).where(
            CaseTask.id == task_id, CaseTask.case_id == case_id
        )
        return self.session.execute(stmt).scalar_one_or_none()


class CaseNoteRepository(BaseRepository[CaseNote]):
    model = CaseNote

    def get_for_case(self, note_id: uuid.UUID, case_id: uuid.UUID) -> CaseNote | None:
        stmt = select(CaseNote).where(
            CaseNote.id == note_id, CaseNote.case_id == case_id
        )
        return self.session.execute(stmt).scalar_one_or_none()


class CaseActivityRepository(BaseRepository[CaseActivity]):
    model = CaseActivity

    def list_for_case(
        self, case_id: uuid.UUID, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[CaseActivity], int]:
        base = select(CaseActivity).where(CaseActivity.case_id == case_id)
        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            base.order_by(CaseActivity.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def log(
        self,
        case_id: uuid.UUID,
        action: str,
        description: str,
        *,
        actor_id: uuid.UUID | None = None,
        event_data: dict | None = None,
    ) -> CaseActivity:
        activity = CaseActivity(
            case_id=case_id,
            actor_id=actor_id,
            action=action,
            description=description,
            event_data=event_data or {},
        )
        self.session.add(activity)
        self.session.flush()
        return activity
