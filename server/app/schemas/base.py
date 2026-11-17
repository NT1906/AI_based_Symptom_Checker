"""Base Pydantic schema configuration for camelCase serialization.

Responsibilities:
    - Provide camelCase alias generation for client-facing JSON.
    - Enable population by field name (snake_case in Python, camelCase on wire).
    - Support ORM mode via from_attributes for database models.
    - Provide RequestSchemaBase with extra='forbid' and whitespace stripping (NFR-03).

Owner: Darshil (orchestration) · Task: S0-DAR-1, S2-DAR-7 · Requirements: NFR-03
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


class RequestSchemaBase(SchemaBase):
    """Base schema for API request payloads with strict input validation (NFR-03).

    Enforces mass-assignment protection by forbidding extra/unknown fields,
    automatic whitespace stripping on strings, and camelCase wire formatting.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


__all__ = [
    "RequestSchemaBase",
    "SchemaBase",
]
