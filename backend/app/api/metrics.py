"""GET saved server statistics and POST validated collector samples."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import AwareDatetime
from starlette.concurrency import run_in_threadpool

from app.core.security import require_collector, require_reader
from app.schemas.metric import MetricCreate, MetricPage, MetricRecord
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


async def validate_post(request: Request) -> datetime:
    """Use middleware receipt time and require the JSON media type."""
    if request.query_params:
        raise HTTPException(status_code=422)
    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip()
    if media_type.lower() != "application/json":
        raise HTTPException(status_code=415)
    return request.state.received_at


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
    received_at: Annotated[datetime, Depends(validate_post)],
) -> MetricRecord:
    """Store one sample atomically; duplicates do not overwrite history."""
    try:
        result = await run_in_threadpool(service.create, sample, received_at)
    except FutureMetric:
        raise HTTPException(status_code=422) from None
    except DuplicateMetric:
        raise HTTPException(status_code=409) from None
    except MetricsUnavailable:
        raise HTTPException(status_code=503) from None
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
    for name in request.query_params:
        if name not in {"limit", "offset", "start", "end"}:
            raise HTTPException(status_code=422)
        if len(request.query_params.getlist(name)) != 1:
            raise HTTPException(status_code=422)
        if name in {"start", "end"}:
            try:
                datetime.fromisoformat(request.query_params[name])
            except ValueError:
                raise HTTPException(status_code=422) from None
    if await request.body():
        raise HTTPException(status_code=422)
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=422)
    try:
        result = await run_in_threadpool(service.list, limit, offset, start, end)
    except MetricsUnavailable:
        raise HTTPException(status_code=503) from None
    response.headers["Cache-Control"] = "no-store"
    return result
