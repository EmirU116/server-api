"""Strict measurement inputs and UTC response contracts."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

Percentage = Annotated[float, Field(strict=True, ge=0, le=100, allow_inf_nan=False)]


class MetricCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collected_at: AwareDatetime
    cpu_percent: Percentage
    memory_percent: Percentage
    disk_percent: Percentage
    uptime_seconds: Annotated[int, Field(strict=True, ge=0, le=9223372036854775807)]

    @field_validator("collected_at", mode="before")
    @classmethod
    def reject_numeric_timestamp(cls, value):
        # Accept RFC3339 text or Python datetimes, not Unix numbers/booleans.
        if not isinstance(value, (str, datetime)):
            raise ValueError("Use a timezone-aware datetime.")
        return value

    @field_validator("collected_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class MetricRecord(MetricCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class MetricPage(BaseModel):
    items: list[MetricRecord]
    total: int
    limit: int
    offset: int
