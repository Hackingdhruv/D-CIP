"""Case and related schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.user import UserReadSlim


class CaseAssignmentRead(BaseSchema):
    user: UserReadSlim
    role: str
    assigned_at: datetime


class CaseActivityRead(BaseSchema):
    id: uuid.UUID
    action: str
    description: str
    event_data: dict[str, Any] = {}
    created_at: datetime
    actor: UserReadSlim | None = None


class CaseTaskRead(BaseSchema):
    id: uuid.UUID
    case_id: uuid.UUID
    title: str
    description: str | None = None
    status: str
    priority: str
    due_date: datetime | None = None
    checklist: list[dict[str, Any]] = []
    assignee: UserReadSlim | None = None
    created_by: UserReadSlim
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class CaseTaskCreate(BaseSchema):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    priority: str = "medium"
    assignee_id: uuid.UUID | None = None
    due_date: datetime | None = None
    checklist: list[dict[str, Any]] = []


class CaseTaskUpdate(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee_id: uuid.UUID | None = None
    due_date: datetime | None = None
    checklist: list[dict[str, Any]] | None = None


class CaseNoteRead(BaseSchema):
    id: uuid.UUID
    case_id: uuid.UUID
    title: str
    content: str
    is_pinned: bool
    created_by: UserReadSlim
    updated_by: UserReadSlim | None = None
    created_at: datetime
    updated_at: datetime


class CaseNoteCreate(BaseSchema):
    title: str = Field(min_length=1, max_length=500)
    content: str = ""
    is_pinned: bool = False


class CaseNoteUpdate(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = None
    is_pinned: bool | None = None


class CaseAssignEntry(BaseSchema):
    user_id: uuid.UUID
    role: str = "investigator"


class CaseAssignRequest(BaseSchema):
    assignments: list[CaseAssignEntry]


class CaseCreate(BaseSchema):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    status: str = "open"
    priority: str = "medium"
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] = []
    is_private: bool = False


class CaseUpdate(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = None
    is_private: bool | None = None
    is_starred: bool | None = None


class CaseReadSlim(BaseSchema):
    id: uuid.UUID
    reference_number: str
    title: str
    description: str | None = None
    status: str
    priority: str
    category: str | None = None
    tags: list[str] = []
    is_private: bool
    is_starred: bool
    owner: UserReadSlim
    task_count: int = 0
    open_task_count: int = 0
    note_count: int = 0
    assignment_count: int = 0
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    archived_at: datetime | None = None


class CaseRead(BaseSchema):
    id: uuid.UUID
    reference_number: str
    title: str
    description: str | None = None
    status: str
    priority: str
    category: str | None = None
    tags: list[str] = []
    is_private: bool
    is_starred: bool
    owner: UserReadSlim
    created_by: UserReadSlim
    assignments: list[CaseAssignmentRead] = []
    tasks: list[CaseTaskRead] = []
    notes: list[CaseNoteRead] = []
    task_count: int = 0
    open_task_count: int = 0
    note_count: int = 0
    assignment_count: int = 0
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    archived_at: datetime | None = None


class CaseImportPreview(BaseSchema):
    """Structured fields extracted from an uploaded document, ready for user review."""
    title: str
    description: str | None = None
    priority: str = "medium"
    category: str | None = None
    tags: list[str] = []
    notes: list[str] = []
    raw_text_excerpt: str = ""
    ai_used: bool = False


class CaseListResponse(BaseSchema):
    items: list[CaseReadSlim]
    total: int
    page: int
    page_size: int
    pages: int
