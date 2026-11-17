"""Bounded readiness checks with injectable probes and a testable clock."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from app.schemas.health import HealthChecks, HealthReport

Probe = Callable[[], Awaitable[bool]]
Clock = Callable[[], datetime]


class UnknownServer(LookupError):
    """The requested ID has no registered probe target."""


def utc_now() -> datetime:
    return datetime.now(UTC)


async def server_process_ready() -> bool:
    """Reaching this process proves local API availability, not EC2-wide health."""
    return True


async def database_not_configured() -> bool:
    """Fail readiness until persistence supplies a real database probe.

    An unconfigured database must never be reported as healthy. This keeps
    the public endpoint useful without requiring credentials for this first API.
    """
    return False


class HealthService:
    def __init__(
        self,
        server_probe: Probe = server_process_ready,
        database_probe: Probe = database_not_configured,
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

        server_up, database_up = await asyncio.gather(
            self._probe(self.server_probe),
            self._probe(self.database_probe),
        )
        return HealthReport(
            server_id=server_id,
            status="healthy" if server_up and database_up else "unhealthy",
            checked_at=self.clock().astimezone(UTC),
            checks=HealthChecks(
                server="up" if server_up else "down",
                database="up" if database_up else "down",
            ),
        )

    async def _probe(self, probe: Probe) -> bool:
        try:
            return await asyncio.wait_for(probe(), self.timeout_seconds) is True
        except TimeoutError:
            # A slow dependency is unhealthy; the route returns a structured 503.
            return False
        except Exception:
            # Other dependency failures must not leak internal exception details.
            return False
