"""FastAPI application factory, ready for the planned API routers."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from app.api.health import router as health_router
from app.api.incidents import router as incidents_router
from app.api.metrics import router as metrics_router
from app.api.server import router as server_router
from app.core.config import Settings, load_settings
from app.core.database import Database
from app.core.errors import register_error_handlers
from app.core.security import load_reader_token, load_token
from app.services.health import HealthService
from app.services.incidents import IncidentsService
from app.services.metrics import MetricsService
from app.services.server import ServerService


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an isolated application instance for Uvicorn or tests.

    Health is available without reader credentials. Its database check stays down
    until PostgreSQL credentials are configured. Server information requires a
    reader token; metrics use collector writes and incidents use admin writes.
    """
    settings = settings if settings is not None else load_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        try:
            yield
        finally:
            engine = application.state.database.engine
            if engine is not None:
                await run_in_threadpool(engine.dispose)

    expose_docs = settings.environment != "production"
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Server monitoring and incident management API (foundation).",
        debug=False,
        lifespan=lifespan,
        docs_url="/docs" if expose_docs else None,
        redoc_url="/redoc" if expose_docs else None,
        openapi_url="/openapi.json" if expose_docs else None,
    )
    app.state.settings = settings
    app.state.database = Database(settings)
    app.state.health_service = HealthService(
        database_probe=app.state.database.check
        if app.state.database.engine is not None
        else None,
        local_server_id=settings.server_id,
    )
    app.state.server_service = ServerService(settings.server_id, settings.server_name)
    app.state.reader_token = load_reader_token(settings)
    app.state.collector_token = load_token(
        settings.collector_token, settings.collector_token_file, "Collector"
    )
    app.state.admin_token = load_token(
        settings.admin_token, settings.admin_token_file, "Admin"
    )
    tokens = [app.state.reader_token, app.state.collector_token, app.state.admin_token]
    configured = [token.get_secret_value() for token in tokens if token is not None]
    if len(set(configured)) != len(configured):
        raise RuntimeError("Reader, collector, and admin tokens must be different.")
    app.state.incidents_service = IncidentsService(
        app.state.database.engine, settings.server_id
    )
    app.state.metrics_service = MetricsService(
        app.state.database.engine, settings.server_id
    )
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(server_router)
    app.include_router(metrics_router)
    app.include_router(incidents_router)
    return app
