"""GET-only information about the single configured server."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from app.core.errors import PublicHTTPError
from app.core.security import require_reader
from app.reusable import parse_server_id, validate_read_request
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
    await validate_read_request(request, "server_id")

    selected_id = None
    if server_id is not None:
        selected_id = parse_server_id(request, server_id)

    try:
        # Host file reads must not block other asynchronous request handlers.
        info = await run_in_threadpool(service.get_info, selected_id)
    except UnknownServer:
        raise PublicHTTPError(404, "No server is registered with this ID.") from None
    except ServerInfoUnavailable:
        raise PublicHTTPError(
            503, "Server information is temporarily unavailable."
        ) from None

    response.headers["Cache-Control"] = "no-store"
    return info
