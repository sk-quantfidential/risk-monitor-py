"""Main application entry point for Risk Monitor service."""
import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI

from risk_monitor.infrastructure.config import get_settings
from risk_monitor.infrastructure.logging import setup_logging
from risk_monitor.presentation.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()
    logger = structlog.get_logger()

    logger.info("Starting Risk Monitor service", version=settings.version)

    # Startup logic here
    yield

    # Shutdown logic here
    logger.info("Shutting down Risk Monitor service")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Risk Monitor API",
        description="Production-like risk monitoring service",
        version=settings.version,
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(health_router, prefix="/api/v1", tags=["health"])

    return app


def setup_signal_handlers() -> None:
    """Setup graceful shutdown signal handlers."""
    def signal_handler(signum: int, frame) -> None:
        logging.info(f"Received signal {signum}, shutting down gracefully")
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def main() -> None:
    """Main application entry point."""
    setup_logging()
    setup_signal_handlers()

    settings = get_settings()
    app = create_app()

    config = uvicorn.Config(
        app=app,
        host=settings.host,
        port=settings.http_port,
        log_config=None,  # Use our own logging
        access_log=False,
    )

    server = uvicorn.Server(config)

    try:
        await server.serve()
    except KeyboardInterrupt:
        logging.info("Received shutdown signal")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())