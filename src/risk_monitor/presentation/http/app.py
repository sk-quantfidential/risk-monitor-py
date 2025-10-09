"""FastAPI application factory."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from risk_monitor.domain.ports.metrics import MetricsPort
from risk_monitor.infrastructure.config import Settings
from risk_monitor.infrastructure.observability.metrics_middleware import (
    create_red_metrics_middleware,
)
from risk_monitor.presentation.http.routers import health, metrics, risk

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan manager."""
    settings: Settings = app.state.settings
    logger.info("Starting Risk Monitor HTTP server",
                port=settings.http_port, version=settings.version)

    # Startup logic here - service registration, database connections, etc.
    yield

    # Shutdown logic here
    logger.info("Shutting down Risk Monitor HTTP server")


def create_fastapi_app(
    settings: Settings, metrics_port: Optional[MetricsPort] = None
) -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        settings: Application settings
        metrics_port: Optional MetricsPort for observability (Clean Architecture)
    """

    app = FastAPI(
        title="Risk Monitor API",
        description="Production-like risk monitoring service with dual HTTP/gRPC support",
        version=settings.version,
        default_response_class=ORJSONResponse,  # Faster JSON serialization
        lifespan=lifespan,
    )

    # Store settings and metrics_port for access in routes and middleware
    app.state.settings = settings
    app.state.metrics_port = metrics_port

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # OpenTelemetry instrumentation
    FastAPIInstrumentor.instrument_app(app)

    # RED metrics middleware (Clean Architecture: uses MetricsPort)
    if metrics_port:
        app.middleware("http")(create_red_metrics_middleware(metrics_port))

    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(risk.router, prefix="/api/v1", tags=["risk"])
    app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])

    # Add convenience root-level health endpoint (redirects to /api/v1/health)
    app.include_router(health.router, tags=["health-root"])

    return app