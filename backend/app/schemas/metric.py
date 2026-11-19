"""Strict measurement inputs and UTC response contracts."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.reusable import EventTimestamp

Percentage = Annotated[float, Field(strict=True, ge=0, le=100, allow_inf_nan=False)]


class MetricCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collected_at: EventTimestamp
    cpu_percent: Percentage
    memory_percent: Percentage
    disk_percent: Percentage
    uptime_seconds: Annotated[int, Field(strict=True, ge=0, le=9223372036854775807)]


class MetricRecord(MetricCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class MetricPage(BaseModel):
    items: list[MetricRecord]
    total: int
    limit: int
    offset: int
