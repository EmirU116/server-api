"""Persist operational incidents separately from immutable measurements."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint("char_length(title) BETWEEN 1 AND 200"),
        CheckConstraint("char_length(description) BETWEEN 1 AND 5000"),
        CheckConstraint("severity IN ('info', 'warning', 'critical')"),
        CheckConstraint(
            "status IN ('planned', 'open', 'investigating', 'resolved')",
            name="incidents_status_check",
        ),
        CheckConstraint(
            "(status = 'planned') = (occurred_at IS NULL)",
            name="incidents_occurrence_check",
        ),
        CheckConstraint(
            "(status = 'resolved' AND resolved_at IS NOT NULL) OR "
            "(status != 'resolved' AND resolved_at IS NULL)"
        ),
        Index("ix_incidents_server_created", "server_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    server_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(5000))
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trigger: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
