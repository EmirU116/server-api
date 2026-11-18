"""Read and record metrics with atomic transactions and safe domain errors."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine, func, select
from sqlalchemy.exc import (
    IntegrityError,
    InterfaceError,
    OperationalError,
    ProgrammingError,
    TimeoutError,
)
from sqlalchemy.orm import Session

from app.models.metric import Metric
from app.schemas.metric import MetricCreate, MetricPage, MetricRecord


class MetricsUnavailable(Exception):
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
        if self.engine is None:
            raise MetricsUnavailable

        try:
            with Session(self.engine) as session, session.begin():
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
        except (OperationalError, InterfaceError, ProgrammingError, TimeoutError):
            raise MetricsUnavailable from None

    def list(
        self, limit: int, offset: int, start: datetime | None, end: datetime | None
    ) -> MetricPage:
        """Read count and page in one consistent PostgreSQL snapshot.

        Filter before counting. Server identity is supplied by configuration,
        so neither a reader nor collector can switch to another server's data.
        """
        if self.engine is None:
            raise MetricsUnavailable
        filters = [Metric.server_id == self.server_id]
        if start is not None:
            filters.append(Metric.collected_at >= start)
        if end is not None:
            filters.append(Metric.collected_at <= end)

        try:
            with self.engine.connect() as connection:
                connection = connection.execution_options(
                    isolation_level="REPEATABLE READ"
                )
                with Session(bind=connection) as session, session.begin():
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
        except (OperationalError, InterfaceError, ProgrammingError, TimeoutError):
            raise MetricsUnavailable from None
