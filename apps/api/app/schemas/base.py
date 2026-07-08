"""Base Pydantic schema.

All API schemas inherit from :class:`BaseSchema`, which reads attributes from ORM
objects and serialises field names to camelCase for the TypeScript client while
still accepting snake_case input.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )
