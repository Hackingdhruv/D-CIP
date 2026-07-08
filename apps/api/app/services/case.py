"""Case management service — business logic for the investigation workspace."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models.case import Case, CaseStatus
from app.models.case_assignment import AssignmentRole, CaseAssignment
from app.models.case_task import CaseTask, TaskStatus
from app.models.case_note import CaseNote
from app.models.user import User
from app.repositories.case import (
    CaseActivityRepository,
    CaseNoteRepository,
    CaseRepository,
    CaseTaskRepository,
)
from app.repositories.user import UserRepository
from app.schemas.case import (
    CaseAssignEntry,
    CaseCreate,
    CaseListResponse,
    CaseNoteCreate,
    CaseNoteUpdate,
    CaseReadSlim,
    CaseTaskCreate,
    CaseTaskUpdate,
    CaseUpdate,
)
from app.services.base import BaseService


class CaseService(BaseService):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self._cases = CaseRepository(session)
        self._tasks = CaseTaskRepository(session)
        self._notes = CaseNoteRepository(session)
        self._activities = CaseActivityRepository(session)
        self._users = UserRepository(session)

    # ── Case CRUD ─────────────────────────────────────────────────────────────

    def create(self, data: CaseCreate, *, actor: User) -> Case:
        ref = self._cases.generate_reference_number()
        case = Case(
            reference_number=ref,
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            category=data.category,
            tags=data.tags or [],
            is_private=data.is_private,
            owner_id=actor.id,
            created_by_id=actor.id,
        )
        self.session.add(case)
        self.session.flush()

        self._activities.log(
            case.id,
            "case.created",
            f"Case '{case.title}' was created.",
            actor_id=actor.id,
            event_data={"reference_number": ref, "status": case.status},
        )
        self.session.commit()
        self.session.refresh(case)
        return case

    def get(self, case_id: uuid.UUID, *, viewer: User) -> Case:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, viewer)
        return case

    def update(self, case_id: uuid.UUID, data: CaseUpdate, *, actor: User) -> Case:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)

        changes: dict = {}
        if data.title is not None:
            changes["title"] = data.title
            case.title = data.title
        if data.description is not None:
            changes["description"] = "updated"
            case.description = data.description
        if data.status is not None:
            old_status = case.status
            case.status = data.status
            changes["status"] = f"{old_status} → {data.status}"
            if data.status == CaseStatus.CLOSED.value and case.closed_at is None:
                case.closed_at = datetime.now(timezone.utc)
        if data.priority is not None:
            changes["priority"] = data.priority
            case.priority = data.priority
        if data.category is not None:
            case.category = data.category
        if data.tags is not None:
            case.tags = data.tags
        if data.is_private is not None:
            case.is_private = data.is_private
        if data.is_starred is not None:
            case.is_starred = data.is_starred

        if changes:
            self._activities.log(
                case.id,
                "case.updated",
                f"Case was updated: {', '.join(changes.keys())}.",
                actor_id=actor.id,
                event_data=changes,
            )
        self.session.commit()
        self.session.refresh(case)
        return case

    def archive(self, case_id: uuid.UUID, *, actor: User) -> Case:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)
        if case.archived_at is not None:
            raise ConflictError("Case is already archived.")

        case.archived_at = datetime.now(timezone.utc)
        case.status = CaseStatus.ARCHIVED.value
        self._activities.log(
            case.id, "case.archived", "Case was archived.", actor_id=actor.id
        )
        self.session.commit()
        self.session.refresh(case)
        return case

    def restore(self, case_id: uuid.UUID, *, actor: User) -> Case:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)
        if case.archived_at is None:
            raise ConflictError("Case is not archived.")

        case.archived_at = None
        case.status = CaseStatus.OPEN.value
        self._activities.log(
            case.id, "case.restored", "Case was restored from archive.", actor_id=actor.id
        )
        self.session.commit()
        self.session.refresh(case)
        return case

    def soft_delete(self, case_id: uuid.UUID, *, actor: User) -> None:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)
        self._cases.soft_delete(case)
        self.session.commit()

    def star(self, case_id: uuid.UUID, *, actor: User) -> Case:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)
        case.is_starred = True
        self.session.commit()
        self.session.refresh(case)
        return case

    def unstar(self, case_id: uuid.UUID, *, actor: User) -> Case:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)
        case.is_starred = False
        self.session.commit()
        self.session.refresh(case)
        return case

    def list_cases(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        owner_id: uuid.UUID | None = None,
        is_starred: bool | None = None,
        include_archived: bool = False,
        viewer: User,
        page: int = 1,
        page_size: int = 20,
    ) -> CaseListResponse:
        items, total = self._cases.search(
            q=q,
            status=status,
            priority=priority,
            category=category,
            owner_id=owner_id,
            is_starred=is_starred,
            include_archived=include_archived,
            viewer_id=viewer.id,
            page=page,
            page_size=page_size,
        )
        pages = max(1, math.ceil(total / page_size))
        return CaseListResponse(
            items=[CaseReadSlim.model_validate(c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    # ── Assignments ───────────────────────────────────────────────────────────

    def assign_users(
        self,
        case_id: uuid.UUID,
        entries: list[CaseAssignEntry],
        *,
        actor: User,
    ) -> Case:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)

        # Validate all user IDs in one query before making any changes.
        user_ids = [e.user_id for e in entries]
        users_by_id = self._users.get_many_active(user_ids)
        missing = [uid for uid in user_ids if uid not in users_by_id]
        if missing:
            raise NotFoundError(f"User(s) not found: {', '.join(str(u) for u in missing)}")

        # Replace assignments
        case.assignments.clear()
        self.session.flush()

        for entry in entries:
            a = CaseAssignment(
                case_id=case_id,
                user_id=entry.user_id,
                role=entry.role,
                assigned_by_id=actor.id,
            )
            self.session.add(a)

        self._activities.log(
            case.id,
            "case.assigned",
            f"Case team updated with {len(entries)} member(s).",
            actor_id=actor.id,
            event_data={"count": len(entries)},
        )
        self.session.commit()
        self.session.refresh(case)
        return case

    # ── Activities ────────────────────────────────────────────────────────────

    def list_activities(
        self,
        case_id: uuid.UUID,
        *,
        viewer: User,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list, int]:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, viewer)
        return self._activities.list_for_case(case_id, page=page, page_size=page_size)

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def create_task(
        self, case_id: uuid.UUID, data: CaseTaskCreate, *, actor: User
    ) -> CaseTask:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)

        if data.assignee_id is not None:
            if self._users.get_active(data.assignee_id) is None:
                raise NotFoundError("Assignee not found.")

        task = CaseTask(
            case_id=case_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            assignee_id=data.assignee_id,
            due_date=data.due_date,
            checklist=data.checklist or [],
            created_by_id=actor.id,
        )
        self.session.add(task)
        self.session.flush()

        self._activities.log(
            case_id, "task.created", f"Task '{task.title}' was created.", actor_id=actor.id
        )
        self.session.commit()
        self.session.refresh(task)
        return task

    def update_task(
        self,
        case_id: uuid.UUID,
        task_id: uuid.UUID,
        data: CaseTaskUpdate,
        *,
        actor: User,
    ) -> CaseTask:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)

        task = self._tasks.get_for_case(task_id, case_id)
        if task is None:
            raise NotFoundError("Task not found.")

        if data.title is not None:
            task.title = data.title
        if data.description is not None:
            task.description = data.description
        if data.status is not None:
            task.status = data.status
            if data.status == TaskStatus.COMPLETED.value and task.completed_at is None:
                task.completed_at = datetime.now(timezone.utc)
                self._activities.log(
                    case_id,
                    "task.completed",
                    f"Task '{task.title}' was marked complete.",
                    actor_id=actor.id,
                )
        if data.priority is not None:
            task.priority = data.priority
        if data.assignee_id is not None:
            task.assignee_id = data.assignee_id
        if data.due_date is not None:
            task.due_date = data.due_date
        if data.checklist is not None:
            task.checklist = data.checklist

        self.session.commit()
        self.session.refresh(task)
        return task

    def delete_task(
        self, case_id: uuid.UUID, task_id: uuid.UUID, *, actor: User
    ) -> None:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)

        task = self._tasks.get_for_case(task_id, case_id)
        if task is None:
            raise NotFoundError("Task not found.")

        self.session.delete(task)
        self.session.commit()

    # ── Notes ─────────────────────────────────────────────────────────────────

    def create_note(
        self, case_id: uuid.UUID, data: CaseNoteCreate, *, actor: User
    ) -> CaseNote:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)

        note = CaseNote(
            case_id=case_id,
            title=data.title,
            content=data.content,
            is_pinned=data.is_pinned,
            created_by_id=actor.id,
        )
        self.session.add(note)
        self.session.flush()

        self._activities.log(
            case_id, "note.created", f"Note '{note.title}' was added.", actor_id=actor.id
        )
        self.session.commit()
        self.session.refresh(note)
        return note

    def update_note(
        self,
        case_id: uuid.UUID,
        note_id: uuid.UUID,
        data: CaseNoteUpdate,
        *,
        actor: User,
    ) -> CaseNote:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)

        note = self._notes.get_for_case(note_id, case_id)
        if note is None:
            raise NotFoundError("Note not found.")

        if data.title is not None:
            note.title = data.title
        if data.content is not None:
            note.content = data.content
        if data.is_pinned is not None:
            note.is_pinned = data.is_pinned
        note.updated_by_id = actor.id

        self.session.commit()
        self.session.refresh(note)
        return note

    def delete_note(
        self, case_id: uuid.UUID, note_id: uuid.UUID, *, actor: User
    ) -> None:
        case = self._cases.get_active(case_id)
        if case is None:
            raise NotFoundError("Case not found.")
        self._assert_can_view(case, actor)

        note = self._notes.get_for_case(note_id, case_id)
        if note is None:
            raise NotFoundError("Note not found.")

        self.session.delete(note)
        self._activities.log(
            case_id, "note.deleted", f"Note '{note.title}' was deleted.", actor_id=actor.id
        )
        self.session.commit()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _assert_can_view(self, case: Case, viewer: User) -> None:
        if not case.is_private:
            return
        if viewer.id == case.owner_id:
            return
        assigned_ids = {a.user_id for a in case.assignments}
        if viewer.id in assigned_ids:
            return
        # Users with case:assign or case:delete can see private cases (supervisors/admins)
        if "case:assign" in viewer.permissions or "case:delete" in viewer.permissions:
            return
        raise PermissionDeniedError("You do not have access to this private case.")
