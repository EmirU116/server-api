"""Validated incident inputs and complete UTC response records."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.reusable import EventTimestamp, UtcDatetime, reject_null_characters

Severity = Literal["info", "warning", "critical"]
Status = Literal["open", "investigating", "resolved"]
Title = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=200),
    AfterValidator(reject_null_characters),
]
Description = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=5000),
    AfterValidator(reject_null_characters),
]


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Title
    description: Description
    severity: Severity
    occurred_at: EventTimestamp


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # None permits omission. The validator rejects explicitly supplied nulls.
    title: Title | None = None
    description: Description | None = None
    severity: Severity | None = None
    status: Status | None = None

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("Supply at least one field.")
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError("Fields cannot be null.")
        return self


class IncidentRecord(IncidentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: Status
    created_at: UtcDatetime
    updated_at: UtcDatetime
    resolved_at: UtcDatetime | None


class IncidentPage(BaseModel):
    items: list[IncidentRecord]
    total: int
    limit: int
    offset: int
