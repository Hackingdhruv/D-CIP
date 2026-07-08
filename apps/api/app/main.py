"""FastAPI application factory.

``create_app`` assembles the application from its parts: logging, middleware,
CORS, the rate-limit framework, exception handlers, and the versioned API
router. Keeping construction in a factory makes the app trivial to instantiate
fresh inside tests.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import limiter
from app.db import neo4j_client

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown hooks."""
    logger.info(
        "Starting %s in %s mode", settings.app_name, settings.environment.value
    )
    yield
    neo4j_client.close_driver()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    configure_logging(
        level=settings.log_level,
        json_logs=settings.log_format.lower() == "json",
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="D-CIP — Digital Cyber Intelligence Platform API.",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url=f"{settings.api_prefix}/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )

    # Rate limiting framework.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Middleware. The last added wraps the others, so CORS sits outermost and
    # request-context binding wraps route handling.
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # Serve uploaded avatars as static files.
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"name": settings.app_name, "status": "ok", "docs": "/docs"}

    return app


app = create_app()
