"""Generic repository base.

The repository pattern isolates persistence concerns from services. Concrete
repositories bind a model and inherit standard CRUD operations; no concrete
repositories exist yet because no models are defined in this milestone.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Reusable CRUD operations over a single SQLAlchemy model."""

    model: type[ModelType]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: Any) -> ModelType | None:
        return self.session.get(self.model, entity_id)

    def list(self, *, limit: int = 50, offset: int = 0) -> list[ModelType]:
        stmt = select(self.model).limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars().all())

    def add(self, entity: ModelType) -> ModelType:
        self.session.add(entity)
        self.session.flush()
        return entity

    def delete(self, entity: ModelType) -> None:
        self.session.delete(entity)
        self.session.flush()
