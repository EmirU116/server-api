"""Validated incident inputs and complete UTC response records."""

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

Severity = Literal["info", "warning", "critical"]
Status = Literal["open", "investigating", "resolved"]
Title = Annotated[str, Field(strict=True, min_length=1, max_length=200)]
Description = Annotated[str, Field(strict=True, min_length=1, max_length=5000)]


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Title
    description: Description
    severity: Severity
    occurred_at: AwareDatetime

    @field_validator("title", "description")
    @classmethod
    def reject_null_characters(cls, value: str) -> str:
        # PostgreSQL text cannot contain a null character; reject before writing.
        if "\x00" in value:
            raise ValueError("Text cannot contain null characters.")
        return value

    @field_validator("occurred_at", mode="before")
    @classmethod
    def reject_numeric_timestamp(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("Use a timezone-aware datetime.")
        return value

    @field_validator("occurred_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class IncidentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # None permits omission. The validator rejects explicitly supplied nulls.
    title: Title | None = None
    description: Description | None = None
    severity: Severity | None = None
    status: Status | None = None

    @field_validator("title", "description")
    @classmethod
    def reject_null_characters(cls, value: str | None) -> str | None:
        # PostgreSQL text cannot contain a null character; reject before writing.
        if value is not None and "\x00" in value:
            raise ValueError("Text cannot contain null characters.")
        return value

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
    created_at: AwareDatetime
    updated_at: AwareDatetime
    resolved_at: AwareDatetime | None

    @field_validator("created_at", "updated_at", "resolved_at")
    @classmethod
    def normalize_generated_times(cls, value: datetime | None) -> datetime | None:
        # PostgreSQL may return its session timezone; the API always returns UTC.
        return value.astimezone(UTC) if value is not None else None


class IncidentPage(BaseModel):
    items: list[IncidentRecord]
    total: int
    limit: int
    offset: int
