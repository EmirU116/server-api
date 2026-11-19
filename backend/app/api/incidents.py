"""Read incidents as a reader; create, edit, and delete as an administrator."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from app.core.errors import PublicHTTPError
from app.core.security import require_admin, require_reader
from app.reusable import (
    validate_json_write,
    validate_list_request,
    validate_read_request,
)
from app.schemas.incident import (
    IncidentCreate,
    IncidentPage,
    IncidentRecord,
    IncidentUpdate,
    Severity,
    Status,
)
from app.services.incidents import (
    FutureIncident,
    IncidentNotFound,
    IncidentsService,
    IncidentsUnavailable,
)

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents"])
errors = {
    400: {"description": "Malformed JSON"},
    401: {"description": "Missing or invalid bearer token"},
    403: {"description": "Credential lacks the required role"},
    404: {"description": "Incident not found"},
    415: {"description": "Content-Type must be application/json"},
    422: {"description": "Invalid or unsupported input"},
    500: {"description": "Unexpected internal error"},
    503: {"description": "Storage or required role unavailable"},
}


def get_service(request: Request) -> IncidentsService:
    return request.app.state.incidents_service


async def validate_read(request: Request) -> None:
    await validate_read_request(request)


async def call_service(response: Response, operation, *args):
    """Keep blocking storage work off the event loop and map safe domain errors."""
    try:
        result = await run_in_threadpool(operation, *args)
    except IncidentNotFound:
        raise PublicHTTPError(404, "No incident exists with this ID.") from None
    except FutureIncident:
        raise PublicHTTPError(422, "occurred_at cannot be in the future.") from None
    except IncidentsUnavailable as exc:
        raise PublicHTTPError(503, exc.reason.value) from None
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post(
    "",
    status_code=201,
    response_model=IncidentRecord,
    dependencies=[Depends(require_admin)],
    responses=errors,
)
async def create_incident(
    data: IncidentCreate,
    response: Response,
    service: Annotated[IncidentsService, Depends(get_service)],
    received_at: Annotated[datetime, Depends(validate_json_write)],
) -> IncidentRecord:
    result = await call_service(response, service.create, data, received_at)
    response.headers["Location"] = f"/api/v1/incidents/{result.id}"
    return result


@router.get(
    "",
    response_model=IncidentPage,
    dependencies=[Depends(require_reader)],
    responses=errors,
)
async def list_incidents(
    request: Request,
    response: Response,
    service: Annotated[IncidentsService, Depends(get_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    status: Status | None = None,
    severity: Severity | None = None,
) -> IncidentPage:
    await validate_list_request(request, "limit", "offset", "status", "severity")
    return await call_service(response, service.list, limit, offset, status, severity)


@router.get(
    "/{incident_id}",
    response_model=IncidentRecord,
    dependencies=[Depends(require_reader), Depends(validate_read)],
    responses=errors,
)
async def get_incident(
    incident_id: UUID,
    response: Response,
    service: Annotated[IncidentsService, Depends(get_service)],
) -> IncidentRecord:
    return await call_service(response, service.get, incident_id)


@router.patch(
    "/{incident_id}",
    response_model=IncidentRecord,
    dependencies=[Depends(require_admin), Depends(validate_json_write)],
    responses=errors,
)
async def update_incident(
    incident_id: UUID,
    data: IncidentUpdate,
    response: Response,
    service: Annotated[IncidentsService, Depends(get_service)],
) -> IncidentRecord:
    return await call_service(response, service.update, incident_id, data)


@router.delete(
    "/{incident_id}",
    status_code=204,
    dependencies=[Depends(require_admin), Depends(validate_read)],
    responses=errors,
)
async def delete_incident(
    incident_id: UUID,
    response: Response,
    service: Annotated[IncidentsService, Depends(get_service)],
) -> None:
    await call_service(response, service.delete, incident_id)
