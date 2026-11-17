"""GET-only information about the single configured server."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from app.api.validation import parse_server_id
from app.core.security import require_reader
from app.schemas.server import ServerInfo
from app.services.errors import UnknownServer
from app.services.server import ServerInfoUnavailable, ServerService

router = APIRouter(prefix="/api/v1", tags=["Server"])


def get_server_service(request: Request) -> ServerService:
    return request.app.state.server_service


@router.get(
    "/server",
    response_model=ServerInfo,
    dependencies=[Depends(require_reader)],
    responses={
        400: {"description": "Invalid or repeated server ID"},
        401: {"description": "Missing or invalid bearer token"},
        404: {"description": "Server is not registered"},
        422: {"description": "Unexpected query parameters or request body"},
        503: {"description": "Host information or reader authentication unavailable"},
        500: {"description": "Unexpected internal failure"},
    },
)
async def get_server(
    request: Request,
    response: Response,
    service: Annotated[ServerService, Depends(get_server_service)],
    server_id: Annotated[
        str | None, Query(description="Optional positive server ID")
    ] = None,
) -> ServerInfo:
    """Reject unsupported input and keep OS failures out of public responses."""
    for parameter in request.query_params:
        if parameter != "server_id":
            raise HTTPException(status_code=422)

    body = await request.body()
    if body:
        raise HTTPException(status_code=422)

    selected_id = None
    if server_id is not None:
        selected_id = parse_server_id(request, server_id)

    try:
        # Host file reads must not block other asynchronous request handlers.
        info = await run_in_threadpool(service.get_info, selected_id)
    except UnknownServer:
        raise HTTPException(status_code=404) from None
    except ServerInfoUnavailable:
        raise HTTPException(status_code=503) from None

    response.headers["Cache-Control"] = "no-store"
    return info
