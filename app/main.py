"""
CertFlow — FastAPI application entry point.

This is the main file that creates and configures the FastAPI application.

What it does:
  1. Creates the FastAPI instance with metadata for OpenAPI docs
  2. Configures CORS middleware
  3. Registers exception handlers
  4. Mounts API routers
  5. Sets up structured logging on startup

Interview note:
  The lifespan context manager runs setup code on startup and cleanup
  code on shutdown. This replaces the older @app.on_event("startup")
  pattern that FastAPI deprecated.

How to run:
  uvicorn app.main:app --reload
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import health_router_for_root, v1_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown logic.

    Startup:
      - Configure structured logging
      - Log that the application has started

    Shutdown:
      - (Future) Close database connection pools, cancel background tasks
    """
    setup_logging()
    settings = get_settings()
    logger.info(
        "CertFlow starting — environment=%s, log_level=%s",
        settings.ENVIRONMENT,
        settings.LOG_LEVEL,
    )
    yield
    logger.info("CertFlow shutting down")


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI instance.

    Using a factory function (instead of a module-level `app = FastAPI()`)
    makes testing easier: tests can call create_app() to get a fresh
    application instance with different configuration.
    """
    settings = get_settings()

    app = FastAPI(
        title="CertFlow",
        description=(
            "Production-Grade Bulk Certificate Generation API. "
            "Submit certificate generation jobs for lists of recipients, "
            "track progress, and download generated certificates."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- CORS ---
    # In development, allow local origins.
    # In production, CORS_ORIGINS should list explicit trusted origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Exception handlers ---
    register_exception_handlers(app)

    # --- Routers ---
    # Health endpoints at root level (not under /api/v1)
    app.include_router(health_router_for_root)

    # API v1 routes (jobs, certificates — added in later phases)
    app.include_router(v1_router, prefix="/api/v1")

    return app


# Module-level app instance used by `uvicorn app.main:app`
app = create_app()
