"""Base Pydantic schema configuration for camelCase serialization.

Responsibilities:
    - Provide camelCase alias generation for client-facing JSON.
    - Enable population by field name (snake_case in Python, camelCase on wire).
    - Support ORM mode via from_attributes for database models.

Owner: Darshil (orchestration) · Task: S0-DAR-1 · Requirements: N/A
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SchemaBase(BaseModel):
    """Base schema enforcing camelCase JSON serialization and attribute mapping.

    Attributes:
        model_config: ConfigDict with camelCase alias generator and attribute mapping.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
