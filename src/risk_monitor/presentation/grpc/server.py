"""gRPC server implementation."""
import asyncio
from typing import Optional

import grpc
import structlog
from grpc import aio
from grpc_health.v1 import health_pb2_grpc
from grpc_reflection.v1alpha import reflection

from risk_monitor.infrastructure.config import Settings
from risk_monitor.presentation.grpc.services.health import HealthService
from risk_monitor.presentation.grpc.services.risk import RiskService

logger = structlog.get_logger()


class GrpcServer:
    """gRPC server for Risk Monitor service."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.server: Optional[aio.Server] = None

    async def start(self) -> None:
        """Start the gRPC server."""
        self.server = aio.server()

        # Add health service
        health_service = HealthService()
        health_pb2_grpc.add_HealthServicer_to_server(health_service, self.server)

        # Add risk monitoring service
        risk_service = RiskService()
        # TODO: Add generated risk service to server when protobuf schemas are integrated
        # risk_pb2_grpc.add_RiskMonitorServicer_to_server(risk_service, self.server)

        # Enable reflection for debugging
        service_names = (
            health_pb2_grpc.SERVICE_NAME,
            # "risk.v1.RiskMonitor",  # TODO: Add when protobuf schemas are ready
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(service_names, self.server)

        # Configure server address
        listen_addr = f"{self.settings.host}:{self.settings.grpc_port}"
        self.server.add_insecure_port(listen_addr)

        logger.info("Starting gRPC server",
                    address=listen_addr, version=self.settings.version)

        await self.server.start()

    async def stop(self) -> None:
        """Stop the gRPC server gracefully."""
        if self.server:
            logger.info("Stopping gRPC server")
            await self.server.stop(grace=5.0)

    async def wait_for_termination(self) -> None:
        """Wait for server termination."""
        if self.server:
            await self.server.wait_for_termination()


async def create_grpc_server(settings: Settings) -> GrpcServer:
    """Create and configure gRPC server."""
    server = GrpcServer(settings)
    await server.start()
    return server