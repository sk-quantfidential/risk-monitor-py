"""Main application entry point for Risk Monitor service with dual HTTP/gRPC support."""
import asyncio
import logging
import signal
from typing import Optional

import structlog
import uvicorn
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asyncio import AsyncIOInstrumentor
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient, GrpcInstrumentorServer
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from risk_monitor.infrastructure.config import get_settings
from risk_monitor.infrastructure.logging import setup_logging
from risk_monitor.presentation.http.app import create_fastapi_app
from risk_monitor.presentation.grpc.server import create_grpc_server

logger = structlog.get_logger()


class DualProtocolServer:
    """Dual protocol server running both HTTP and gRPC concurrently."""

    def __init__(self):
        self.settings = get_settings()
        self.http_server: Optional[uvicorn.Server] = None
        self.grpc_server: Optional = None
        self.shutdown_event = asyncio.Event()

    def setup_observability(self) -> None:
        """Setup OpenTelemetry tracing and instrumentation."""
        # Configure OpenTelemetry
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()

        # OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=self.settings.otel_exporter_endpoint,
            insecure=self.settings.otel_insecure,
        )

        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

        # Instrument libraries
        AsyncIOInstrumentor().instrument()
        GrpcInstrumentorClient().instrument()
        GrpcInstrumentorServer().instrument()
        RedisInstrumentor().instrument()

        logger.info("OpenTelemetry instrumentation configured",
                    endpoint=self.settings.otel_exporter_endpoint)

    def setup_signal_handlers(self) -> None:
        """Setup graceful shutdown signal handlers."""
        def signal_handler(signum: int, frame) -> None:
            logger.info("Received shutdown signal", signal=signum)
            self.shutdown_event.set()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    async def start_http_server(self) -> None:
        """Start the HTTP server."""
        try:
            app = create_fastapi_app(self.settings)

            config = uvicorn.Config(
                app=app,
                host=self.settings.host,
                port=self.settings.http_port,
                log_config=None,  # Use our own logging
                access_log=False,
                loop="asyncio",
            )

            self.http_server = uvicorn.Server(config)
            await self.http_server.serve()

        except Exception as e:
            logger.error("HTTP server failed", error=str(e))
            self.shutdown_event.set()
            raise

    async def start_grpc_server(self) -> None:
        """Start the gRPC server."""
        try:
            self.grpc_server = await create_grpc_server(self.settings)
            await self.grpc_server.wait_for_termination()

        except Exception as e:
            logger.error("gRPC server failed", error=str(e))
            self.shutdown_event.set()
            raise

    async def shutdown(self) -> None:
        """Gracefully shutdown both servers."""
        logger.info("Shutting down Risk Monitor service")

        shutdown_tasks = []

        if self.http_server:
            logger.info("Stopping HTTP server")
            self.http_server.should_exit = True
            shutdown_tasks.append(self.http_server.shutdown())

        if self.grpc_server:
            logger.info("Stopping gRPC server")
            shutdown_tasks.append(self.grpc_server.stop())

        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

        logger.info("Risk Monitor service stopped")

    async def run(self) -> None:
        """Run both HTTP and gRPC servers concurrently."""
        logger.info("Starting Risk Monitor service",
                    version=self.settings.version,
                    http_port=self.settings.http_port,
                    grpc_port=self.settings.grpc_port)

        # Start both servers concurrently
        try:
            await asyncio.gather(
                self.start_http_server(),
                self.start_grpc_server(),
                self._wait_for_shutdown(),
                return_exceptions=True
            )
        finally:
            await self.shutdown()

    async def _wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self.shutdown_event.wait()


async def main() -> None:
    """Main application entry point."""
    setup_logging()

    server = DualProtocolServer()
    server.setup_observability()
    server.setup_signal_handlers()

    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())