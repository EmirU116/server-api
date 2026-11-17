"""Public GET-only readiness endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.schemas.health import HealthReport
from app.services.health import HealthService, UnknownServer

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
    if len(request.query_params.getlist("server_id")) != 1:
        raise HTTPException(status_code=400)

    try:
        value = int(server_id)
    except ValueError:
        raise HTTPException(status_code=400) from None

    if value < 1:
        raise HTTPException(status_code=400)

    return value


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
    for parameter in request.query_params:
        if parameter != "server_id":
            raise HTTPException(status_code=422)

    body = await request.body()
    if body:
        raise HTTPException(status_code=422)

    try:
        report = await service.check(server_id)
    except UnknownServer:
        raise HTTPException(status_code=404) from None
    response.status_code = 200 if report.status == "healthy" else 503
    response.headers["Cache-Control"] = "no-store"
    return report
