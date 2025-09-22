"""FastAPI application factory."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from risk_monitor.infrastructure.config import Settings
from risk_monitor.presentation.http.routers import health, metrics, risk
from risk_monitor.presentation.shared.middleware import RequestTracker

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


def create_fastapi_app(settings: Settings) -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="Risk Monitor API",
        description="Production-like risk monitoring service with dual HTTP/gRPC support",
        version=settings.version,
        default_response_class=ORJSONResponse,  # Faster JSON serialization
        lifespan=lifespan,
    )

    # Store settings for access in lifespan
    app.state.settings = settings

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

    # Request tracking middleware
    @app.middleware("http")
    async def track_requests(request: Request, call_next):
        tracker = RequestTracker(
            protocol="http",
            method=request.method,
            endpoint=str(request.url.path)
        )

        try:
            response = await call_next(request)
            tracker.track_completion(str(response.status_code))
            return response
        except Exception as e:
            tracker.track_completion("error")
            logger.error("Request failed", error=str(e), path=request.url.path)
            raise

    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(risk.router, prefix="/api/v1", tags=["risk"])
    app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])

    return app