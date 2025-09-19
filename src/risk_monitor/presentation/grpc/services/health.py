"""gRPC health service implementation."""
import asyncio

import structlog
from grpc import aio
from grpc_health.v1 import health_pb2, health_pb2_grpc

from risk_monitor.presentation.shared.middleware import RequestTracker

logger = structlog.get_logger()


class HealthService(health_pb2_grpc.HealthServicer):
    """gRPC health check service implementation."""

    async def Check(
        self,
        request: health_pb2.HealthCheckRequest,
        context: aio.ServicerContext
    ) -> health_pb2.HealthCheckResponse:
        """Handle health check requests."""
        tracker = RequestTracker(
            protocol="grpc",
            method="Check",
            endpoint="/grpc.health.v1.Health/Check"
        )

        try:
            # TODO: Implement actual health checks for dependencies
            service = request.service or "risk-monitor"

            logger.debug("Health check requested", service=service)

            tracker.track_completion("ok")
            return health_pb2.HealthCheckResponse(
                status=health_pb2.HealthCheckResponse.SERVING
            )

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            tracker.track_completion("error")
            return health_pb2.HealthCheckResponse(
                status=health_pb2.HealthCheckResponse.NOT_SERVING
            )

    async def Watch(
        self,
        request: health_pb2.HealthCheckRequest,
        context: aio.ServicerContext
    ) -> health_pb2.HealthCheckResponse:
        """Handle health check watch requests (streaming)."""
        service = request.service or "risk-monitor"

        logger.debug("Health watch started", service=service)

        try:
            # Send initial status
            yield health_pb2.HealthCheckResponse(
                status=health_pb2.HealthCheckResponse.SERVING
            )

            # Keep the stream alive and send periodic updates
            while not context.cancelled():
                await asyncio.sleep(30)  # Send update every 30 seconds

                # TODO: Implement actual health monitoring
                yield health_pb2.HealthCheckResponse(
                    status=health_pb2.HealthCheckResponse.SERVING
                )

        except Exception as e:
            logger.error("Health watch failed", error=str(e), service=service)
            yield health_pb2.HealthCheckResponse(
                status=health_pb2.HealthCheckResponse.NOT_SERVING
            )