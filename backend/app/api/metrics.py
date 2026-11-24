"""GET saved server statistics and POST validated collector samples."""

from datetime import datetime
from typing import Annotated, get_args

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import AwareDatetime
from starlette.concurrency import run_in_threadpool

from app.core.errors import PublicHTTPError
from app.core.security import require_collector, require_reader
from app.reusable import validate_json_write, validate_list_request
from app.schemas.metric import (
    HistoryMinutes,
    MetricCreate,
    MetricHistory,
    MetricPage,
    MetricRecord,
)
from app.services.metrics import (
    DuplicateMetric,
    FutureMetric,
    MetricsService,
    MetricsUnavailable,
)

router = APIRouter(prefix="/api/v1", tags=["Metrics"])
errors = {
    400: {"description": "Malformed JSON"},
    401: {"description": "Missing or invalid bearer token"},
    403: {"description": "Credential lacks the required role"},
    422: {"description": "Invalid or unsupported input"},
    500: {"description": "Unexpected internal error"},
    503: {"description": "Storage or role configuration unavailable"},
}


def get_metrics_service(request: Request) -> MetricsService:
    return request.app.state.metrics_service


@router.post(
    "/metrics",
    status_code=201,
    response_model=MetricRecord,
    dependencies=[Depends(require_collector)],
    responses={
        **errors,
        409: {"description": "Duplicate collection timestamp"},
        415: {"description": "Content-Type must be application/json"},
    },
)
async def post_metric(
    sample: MetricCreate,
    response: Response,
    service: Annotated[MetricsService, Depends(get_metrics_service)],
    received_at: Annotated[datetime, Depends(validate_json_write)],
) -> MetricRecord:
    """Store one sample atomically; duplicates do not overwrite history."""
    try:
        result = await run_in_threadpool(service.create, sample, received_at)
    except FutureMetric:
        raise PublicHTTPError(422, "collected_at cannot be in the future.") from None
    except DuplicateMetric:
        raise PublicHTTPError(
            409, "A measurement already exists for this server and collected_at."
        ) from None
    except MetricsUnavailable as exc:
        raise PublicHTTPError(503, exc.reason.value) from None
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get(
    "/metrics",
    response_model=MetricPage,
    dependencies=[Depends(require_reader)],
    responses=errors,
)
async def get_metrics(
    request: Request,
    response: Response,
    service: Annotated[MetricsService, Depends(get_metrics_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    start: Annotated[AwareDatetime | None, Query()] = None,
    end: Annotated[AwareDatetime | None, Query()] = None,
) -> MetricPage:
    """Read a bounded historical page; this never collects new measurements."""
    await validate_list_request(request, "limit", "offset", "start", "end")
    # Pydantic also accepts Unix numbers such as start=1700000000. Require the
    # documented ISO 8601 text instead; parsing already rejected invalid values.
    for name in ("start", "end"):
        if name in request.query_params:
            try:
                datetime.fromisoformat(request.query_params[name])
            except ValueError:
                raise PublicHTTPError(
                    422, f"Use an ISO 8601 timestamp with a timezone for {name}."
                ) from None
    if start is not None and end is not None and start > end:
        raise PublicHTTPError(422, "start must be earlier than or equal to end.")
    try:
        result = await run_in_threadpool(service.list, limit, offset, start, end)
    except MetricsUnavailable as exc:
        raise PublicHTTPError(503, exc.reason.value) from None
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get(
    "/metrics/history",
    response_model=MetricHistory,
    dependencies=[Depends(require_reader)],
    responses=errors,
)
async def get_metric_history(
    request: Request,
    response: Response,
    service: Annotated[MetricsService, Depends(get_metrics_service)],
    minutes: Annotated[int, Query()] = 30,
) -> MetricHistory:
    """Return averaged time buckets for a dashboard window."""
    await validate_list_request(request, "minutes")
    if minutes not in get_args(HistoryMinutes):
        raise PublicHTTPError(422, "minutes must be 30, 60, or 1440.")
    try:
        result = await run_in_threadpool(
            service.history, minutes, request.state.received_at
        )
    except MetricsUnavailable as exc:
        raise PublicHTTPError(503, exc.reason.value) from None
    response.headers["Cache-Control"] = "no-store"
    return result
