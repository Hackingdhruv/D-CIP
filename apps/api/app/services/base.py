"""Service layer base.

Services hold business logic and orchestrate repositories. They are constructed
with a database session (and, later, other collaborators) so they can be wired
through dependency injection. No concrete services exist in this milestone.
"""

from __future__ import annotations

from sqlalchemy.orm import Session


class BaseService:
    """Common base for all application services."""

    def __init__(self, session: Session) -> None:
        self.session = session
