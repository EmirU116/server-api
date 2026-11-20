"""Transactional incident CRUD scoped to the configured server."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Engine, func, select
from sqlalchemy.exc import (
    InterfaceError,
    OperationalError,
    ProgrammingError,
    TimeoutError,
)
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.schemas.incident import (
    IncidentCreate,
    IncidentPage,
    IncidentRecord,
    IncidentUpdate,
    Severity,
    Status,
)
from app.services.errors import StorageFailure, StorageUnavailable


class IncidentsUnavailable(StorageUnavailable):
    """Database is unavailable, unconfigured, or not migrated."""


class IncidentNotFound(Exception):
    """No incident belongs to this ID and configured server."""


class FutureIncident(Exception):
    """Occurrence time is later than request receipt."""


class IncidentsService:
    def __init__(
        self,
        engine: Engine | None,
        server_id: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.engine = engine
        self.server_id = str(server_id)
        self.clock = clock if clock is not None else lambda: datetime.now(UTC)

    @contextmanager
    def transaction(self, snapshot: bool = False) -> Iterator[Session]:
        """Commit complete operations; roll back failures before reporting them.

        Lists use one repeatable snapshot for their count and page. Mutations
        use ordinary transactions with row locks to serialize concurrent edits.
        """
        if self.engine is None:
            raise IncidentsUnavailable(StorageFailure.UNCONFIGURED)
        try:
            with self.engine.connect() as connection:
                if snapshot:
                    connection = connection.execution_options(
                        isolation_level="REPEATABLE READ"
                    )
                with Session(bind=connection) as session, session.begin():
                    yield session
        except (
            OperationalError,
            InterfaceError,
            ProgrammingError,
            TimeoutError,
        ) as exc:
            raise IncidentsUnavailable.from_database_error(exc) from None

    def find(self, session: Session, incident_id: UUID, lock: bool = False) -> Incident:
        query = select(Incident).where(
            Incident.id == incident_id, Incident.server_id == self.server_id
        )
        if lock:
            query = query.with_for_update()
        record = session.scalar(query)
        if record is None:
            raise IncidentNotFound
        return record

    def create(self, data: IncidentCreate, received_at: datetime) -> IncidentRecord:
        if data.occurred_at is not None and data.occurred_at > received_at.astimezone(
            UTC
        ):
            raise FutureIncident
        now = self.clock().astimezone(UTC)
        with self.transaction() as session:
            record = Incident(
                id=uuid4(),
                server_id=self.server_id,
                **data.model_dump(),
                status="planned" if data.occurred_at is None else "open",
                created_at=now,
                updated_at=now,
                resolved_at=None,
            )
            session.add(record)
            session.flush()
            result = IncidentRecord.model_validate(record)
        return result

    def list(
        self,
        limit: int,
        offset: int,
        status: Status | None = None,
        severity: Severity | None = None,
    ) -> IncidentPage:
        filters = [Incident.server_id == self.server_id]
        if status is not None:
            filters.append(Incident.status == status)
        if severity is not None:
            filters.append(Incident.severity == severity)
        with self.transaction(snapshot=True) as session:
            total = session.scalar(
                select(func.count()).select_from(Incident).where(*filters)
            )
            records = session.scalars(
                select(Incident)
                .where(*filters)
                .order_by(Incident.created_at.desc(), Incident.id.asc())
                .limit(limit)
                .offset(offset)
            )
            result = IncidentPage(
                items=[IncidentRecord.model_validate(row) for row in records],
                total=total,
                limit=limit,
                offset=offset,
            )
        return result

    def get(self, incident_id: UUID) -> IncidentRecord:
        with self.transaction() as session:
            result = IncidentRecord.model_validate(self.find(session, incident_id))
        return result

    def update(self, incident_id: UUID, changes: IncidentUpdate) -> IncidentRecord:
        with self.transaction() as session:
            record = self.find(session, incident_id, lock=True)
            values = changes.model_dump(exclude_unset=True)
            now = self.clock().astimezone(UTC)
            new_status = values.get("status", record.status)
            if record.status == "planned" and new_status != "planned":
                record.occurred_at = now
            if new_status == "resolved" and record.status != "resolved":
                record.resolved_at = now
            elif new_status != "resolved":
                record.resolved_at = None
            # An edit to an already resolved incident preserves resolution time.
            for name, value in values.items():
                setattr(record, name, value)
            record.updated_at = now
            session.flush()
            result = IncidentRecord.model_validate(record)
        return result

    def delete(self, incident_id: UUID) -> None:
        with self.transaction() as session:
            session.delete(self.find(session, incident_id, lock=True))
