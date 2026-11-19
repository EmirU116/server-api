"""Public GET-only readiness endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.reusable import parse_server_id, validate_read_request
from app.schemas.health import HealthReport
from app.services.errors import UnknownServer
from app.services.health import HealthService

router = APIRouter(prefix="/api/v1", tags=["Health"])


def get_health_service(request: Request) -> HealthService:
    """Keep dependency probes replaceable without coupling the route to a DB."""
    return request.app.state.health_service


def validate_server_id(
    request: Request,
    server_id: Annotated[
        str, Query(description="Positive numeric server ID (local server: 1)")
    ],
) -> int:
    """Return 400 for invalid IDs instead of FastAPI's default numeric 422.

    Missing input uses FastAPI's standard required-parameter 422.
    Duplicate IDs are rejected because the target would be ambiguous.
    """
    return parse_server_id(request, server_id)


@router.get(
    "/health",
    response_model=HealthReport,
    responses={
        400: {"description": "Invalid server ID"},
        404: {"description": "Server is not registered"},
        503: {"model": HealthReport, "description": "A required check failed"},
    },
)
async def get_health(
    request: Request,
    response: Response,
    service: Annotated[HealthService, Depends(get_health_service)],
    server_id: Annotated[int, Depends(validate_server_id)],
) -> HealthReport:
    """Report readiness for a registered server without authentication.

    Return 200 only when every required check passes. Keep dependency failures
    in the same response structure with 503, rather than leaking exceptions.
    """
    await validate_read_request(request, "server_id")

    try:
        report = await service.check(server_id)
    except UnknownServer:
        raise HTTPException(status_code=404) from None
    response.status_code = 200 if report.status == "healthy" else 503
    response.headers["Cache-Control"] = "no-store"
    return report
