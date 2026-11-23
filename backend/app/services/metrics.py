"""Read and record metrics with atomic transactions and safe domain errors."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError

from app.models.metric import Metric
from app.reusable import storage_transaction
from app.schemas.metric import (
    HistoryMinutes,
    MetricCreate,
    MetricHistory,
    MetricPage,
    MetricPoint,
    MetricRecord,
)
from app.services.errors import StorageUnavailable


class MetricsUnavailable(StorageUnavailable):
    """Storage is unavailable, unconfigured, or its migration has not run."""


class DuplicateMetric(Exception):
    """A sample already exists for the same server and collection time."""


class FutureMetric(Exception):
    """Collection time is later than API receipt time."""


class MetricsService:
    def __init__(self, engine: Engine | None, server_id: int) -> None:
        self.engine = engine
        self.server_id = str(server_id)

    def create(self, sample: MetricCreate, received_at: datetime) -> MetricRecord:
        """Validate time before inserting; commit only a complete valid record.

        Database uniqueness handles simultaneous duplicate submissions safely.
        Session contexts roll back failures before errors reach the API layer.
        """
        if sample.collected_at > received_at.astimezone(UTC):
            raise FutureMetric
        try:
            with storage_transaction(self.engine, MetricsUnavailable) as session:
                record = Metric(
                    id=uuid4(), server_id=self.server_id, **sample.model_dump()
                )
                session.add(record)
                session.flush()
                result = MetricRecord.model_validate(record)
            return result
        except IntegrityError as exc:
            if (
                getattr(exc.orig, "sqlstate", None) == "23505"
                and exc.orig.diag.constraint_name == "uq_metrics_server_time"
            ):
                raise DuplicateMetric from None
            raise

    def list(
        self, limit: int, offset: int, start: datetime | None, end: datetime | None
    ) -> MetricPage:
        """Read count and page in one consistent PostgreSQL snapshot.

        Filter before counting. Server identity is supplied by configuration,
        so neither a reader nor collector can switch to another server's data.
        """
        filters = [Metric.server_id == self.server_id]
        if start is not None:
            filters.append(Metric.collected_at >= start)
        if end is not None:
            filters.append(Metric.collected_at <= end)

        with storage_transaction(
            self.engine, MetricsUnavailable, snapshot=True
        ) as session:
            total = session.scalar(
                select(func.count()).select_from(Metric).where(*filters)
            )
            records = session.scalars(
                select(Metric)
                .where(*filters)
                .order_by(Metric.collected_at.desc(), Metric.id.asc())
                .limit(limit)
                .offset(offset)
            )
            return MetricPage(
                items=[MetricRecord.model_validate(row) for row in records],
                total=total,
                limit=limit,
                offset=offset,
            )

    def history(self, minutes: HistoryMinutes, now: datetime) -> MetricHistory:
        """Average stored samples into UTC buckets for bounded chart responses."""
        bucket_seconds = {30: 15, 60: 30, 1440: 720}[minutes]
        start = now - timedelta(minutes=minutes)
        bucket = func.date_bin(
            timedelta(seconds=bucket_seconds), Metric.collected_at, start
        )
        query = (
            select(
                bucket.label("collected_at"),
                func.avg(Metric.cpu_percent).label("cpu_percent"),
                func.avg(Metric.memory_percent).label("memory_percent"),
                func.avg(Metric.disk_percent).label("disk_percent"),
            )
            .where(
                Metric.server_id == self.server_id,
                Metric.collected_at >= start,
                Metric.collected_at < now,
            )
            .group_by(bucket)
            .order_by(bucket)
        )
        with storage_transaction(self.engine, MetricsUnavailable) as session:
            return MetricHistory(
                start=start,
                end=now,
                bucket_seconds=bucket_seconds,
                items=[
                    MetricPoint.model_validate(row)
                    for row in session.execute(query).mappings()
                ],
            )
