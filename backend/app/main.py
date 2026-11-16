"""FastAPI application factory, ready for the planned API routers."""

from fastapi import FastAPI

from app.core.config import Settings, load_settings
from app.core.errors import register_error_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an isolated application instance for Uvicorn or tests.

    Only interactive documentation is available in the foundation stage.
    Business routes will be added with persistence and authentication instead
    of returning placeholder successes that could imply server readiness.
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
    register_error_handlers(app)
    return app
