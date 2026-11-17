"""Public readiness response; never include internal connection details."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthChecks(BaseModel):
    server: Literal["up", "down"]
    database: Literal["up", "down"]


class HealthReport(BaseModel):
    server_id: int
    status: Literal["healthy", "unhealthy"]
    checked_at: datetime
    checks: HealthChecks
