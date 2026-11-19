"""Bounded readiness checks with injectable probes and a testable clock."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from app.schemas.health import HealthChecks, HealthReport
from app.services.errors import UnknownServer

Probe = Callable[[], Awaitable[bool]]
Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


async def server_process_ready() -> bool:
    """Reaching this process proves local API availability, not EC2-wide health."""
    return True


class HealthService:
    def __init__(
        self,
        server_probe: Probe = server_process_ready,
        database_probe: Probe | None = None,
        *,
        timeout_seconds: float = 0.15,
        clock: Clock = utc_now,
        local_server_id: int = 1,
    ) -> None:
        self.server_probe = server_probe
        self.database_probe = database_probe
        self.timeout_seconds = timeout_seconds
        self.clock = clock
        # Only the local server is registered; do not probe arbitrary addresses.
        self.local_server_id = local_server_id

    async def check(self, server_id: int) -> HealthReport:
        """Run independent checks concurrently and mark failures as down.

        Probes must use nonblocking async I/O and respect cancellation. Each
        gets 150 ms by default, leaving room for a response within the 200 ms
        target. Concurrent checks share that time rather than adding it up.
        Exception strings are deliberately neither returned nor logged.
        """
        if server_id != self.local_server_id:
            raise UnknownServer

        server_failure, database_failure = await asyncio.gather(
            self._probe("Server", self.server_probe),
            self._probe("Database", self.database_probe),
        )
        failures = [reason for reason in (server_failure, database_failure) if reason]
        return HealthReport(
            server_id=server_id,
            status="unhealthy" if failures else "healthy",
            message=" ".join(failures) if failures else None,
            checked_at=self.clock().astimezone(UTC),
            checks=HealthChecks(
                server="down" if server_failure else "up",
                database="down" if database_failure else "up",
            ),
        )

    async def _probe(self, name: str, probe: Probe | None) -> str | None:
        """Return a safe reason when a required probe fails to establish readiness."""
        if probe is None:
            return f"{name} readiness check is not configured."
        try:
            if await asyncio.wait_for(probe(), self.timeout_seconds) is True:
                return None
            return f"{name} readiness check reported unavailable."
        except TimeoutError:
            return f"{name} readiness check timed out."
        except Exception:
            return f"{name} readiness check could not complete."
