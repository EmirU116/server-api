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

from app.core.errors import PublicInputError
from app.reusable import EventTimestamp, UtcDatetime, reject_null_characters

Severity = Literal["info", "warning", "critical"]
ActiveStatus = Literal["open", "investigating", "resolved"]
Status = Literal["planned", "open", "investigating", "resolved"]
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


class IncidentTrigger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: Literal["cpu", "gpu", "memory", "storage"]
    threshold_percent: Annotated[float, Field(strict=True, ge=0, le=100)]
    duration_seconds: Annotated[int, Field(strict=True, ge=5, le=600)]


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Title
    description: Description
    severity: Severity
    occurred_at: EventTimestamp | None
    trigger: IncidentTrigger | None = None


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Null clears a trigger. Other fields can only be omitted or given a value.
    title: Title | None = None
    description: Description | None = None
    severity: Severity | None = None
    status: ActiveStatus | None = None
    trigger: IncidentTrigger | None = None

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise PublicInputError("Supply at least one field to update.")
        for name in self.model_fields_set:
            if name != "trigger" and getattr(self, name) is None:
                raise PublicInputError(f"Supply a non-null value for {name}.")
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
