"""Persist immutable measurements, scoped to the configured local server."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = (
        UniqueConstraint("server_id", "collected_at", name="uq_metrics_server_time"),
        CheckConstraint("cpu_percent >= 0 AND cpu_percent <= 100"),
        CheckConstraint("memory_percent >= 0 AND memory_percent <= 100"),
        CheckConstraint("disk_percent >= 0 AND disk_percent <= 100"),
        CheckConstraint("uptime_seconds >= 0"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # Canonical decimal text preserves the existing positive server-ID contract
    # without introducing a new numeric size limit for configured identities.
    server_id: Mapped[str] = mapped_column(String, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cpu_percent: Mapped[float] = mapped_column(Float)
    memory_percent: Mapped[float] = mapped_column(Float)
    disk_percent: Mapped[float] = mapped_column(Float)
    uptime_seconds: Mapped[int] = mapped_column(BigInteger)
