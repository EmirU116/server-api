"""FastAPI application factory, ready for the planned API routers."""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import Settings, load_settings
from app.core.errors import register_error_handlers
from app.services.health import HealthService


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an isolated application instance for Uvicorn or tests.

    Health is available without credentials. Its database check remains down
    until persistence is configured; the other API groups are future work.
    """
    settings = settings if settings is not None else load_settings()
    expose_docs = settings.environment != "production"
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Server monitoring and incident management API (foundation).",
        debug=False,
        docs_url="/docs" if expose_docs else None,
        redoc_url="/redoc" if expose_docs else None,
        openapi_url="/openapi.json" if expose_docs else None,
    )
    app.state.settings = settings
    app.state.health_service = HealthService()
    register_error_handlers(app)
    app.include_router(health_router)
    return app
