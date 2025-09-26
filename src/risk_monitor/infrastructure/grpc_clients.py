"""gRPC clients for inter-service communication."""
import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union
from unittest.mock import MagicMock

import grpc
import structlog
from opentelemetry import trace
from opentelemetry.propagate import inject
from tenacity import retry, stop_after_attempt, wait_exponential

from risk_monitor.infrastructure.config import Settings
from risk_monitor.infrastructure.service_discovery import ServiceDiscovery, ServiceInfo

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)

# Constants
DEFAULT_GRPC_TIMEOUT = 30.0
DEFAULT_HEALTH_CHECK_TIMEOUT = 5.0
DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 5
DEFAULT_CIRCUIT_BREAKER_TIMEOUT = 60.0
DEFAULT_TRADING_ENGINE_PORT = 50051
DEFAULT_TEST_COORDINATOR_PORT = 50052


class ServiceCommunicationError(Exception):
    """Inter-service communication related errors."""
    pass


@dataclass
class StrategyStatus:
    """Trading strategy status information."""
    strategy_id: str
    status: str
    positions: List[Dict[str, Any]]
    last_updated: str
    performance: Optional[Dict[str, float]] = None


@dataclass
class Position:
    """Trading position information."""
    instrument_id: str
    quantity: float
    value: float
    side: str
    entry_price: Optional[float] = None
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None


@dataclass
class ScenarioStatus:
    """Test scenario status information."""
    scenario_id: str
    status: str
    start_time: str
    end_time: Optional[str] = None
    progress: Optional[float] = None
    current_phase: Optional[str] = None


@dataclass
class ChaosEvent:
    """Chaos engineering event information."""
    event_type: str
    target_service: str
    event_id: str
    timestamp: str
    parameters: Optional[Dict[str, Any]] = None
    severity: str = "medium"


@dataclass
class HealthResponse:
    """gRPC health check response."""
    status: str
    service: Optional[str] = None
    timestamp: Optional[str] = None


class CircuitBreaker:
    """Circuit breaker for service communication."""

    def __init__(
        self,
        failure_threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
        timeout: float = DEFAULT_CIRCUIT_BREAKER_TIMEOUT
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True

    def on_success(self):
        """Record successful execution."""
        self.failure_count = 0
        self.state = "CLOSED"

    def on_failure(self):
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class BaseGrpcClient(ABC):
    """Base class for gRPC clients."""

    # Class-level channel cache for connection reuse
    _channels: Dict[str, grpc.aio.Channel] = {}

    def __init__(self, service_name: str, host: str, port: int, settings: Settings):
        self.service_name = service_name
        self.host = host
        self.port = port
        self.settings = settings
        self._channel: Optional[grpc.aio.Channel] = None
        self._connected = False
        self.circuit_breaker = CircuitBreaker()
        self._call_count = 0
        self._error_count = 0

    @property
    def address(self) -> str:
        """Get gRPC service address."""
        return f"{self.host}:{self.port}"

    async def connect(self) -> None:
        """Connect to gRPC service."""
        try:
            # Reuse existing channel if available
            if self.address in self._channels:
                self._channel = self._channels[self.address]
                logger.debug("Reusing existing gRPC channel", address=self.address)
            else:
                # Create new channel
                self._channel = grpc.aio.insecure_channel(self.address)
                self._channels[self.address] = self._channel
                logger.info("Created new gRPC channel", address=self.address)

            # Test connection with health check
            await self._test_connection()
            self._connected = True

            logger.info("gRPC client connected",
                       service=self.service_name, address=self.address)

        except Exception as e:
            logger.error("Failed to connect to gRPC service",
                        service=self.service_name, error=str(e))
            raise ServiceCommunicationError(f"Connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from gRPC service."""
        self._connected = False
        # Note: We don't close the channel here as it might be shared
        # Channel cleanup is handled by the connection manager
        logger.info("gRPC client disconnected", service=self.service_name)

    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self._channel is not None

    def get_stats(self) -> Dict[str, Any]:
        """Get client performance statistics."""
        error_rate = (self._error_count / self._call_count * 100) if self._call_count > 0 else 0

        return {
            "service_name": self.service_name,
            "address": self.address,
            "connected": self.is_connected(),
            "total_calls": self._call_count,
            "error_count": self._error_count,
            "error_rate_percent": round(error_rate, 2),
            "circuit_breaker_state": self.circuit_breaker.state,
            "circuit_breaker_failures": self.circuit_breaker.failure_count
        }

    async def _test_connection(self) -> None:
        """Test gRPC connection with health check."""
        try:
            # Import here to avoid circular imports
            from grpc_health.v1 import health_pb2, health_pb2_grpc

            health_stub = health_pb2_grpc.HealthStub(self._channel)
            request = health_pb2.HealthCheckRequest(service="")

            response = await health_stub.Check(request, timeout=DEFAULT_HEALTH_CHECK_TIMEOUT)
            if response.status != health_pb2.HealthCheckResponse.SERVING:
                raise ServiceCommunicationError("Service not healthy")

        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.UNIMPLEMENTED:
                # Health service not implemented, assume service is available
                logger.warning("Health service not implemented", service=self.service_name)
                return
            raise ServiceCommunicationError(f"Health check failed: {e}")

    async def _make_call(self, method_name: str, request: Any, timeout: float = DEFAULT_GRPC_TIMEOUT) -> Any:
        """Make gRPC call with circuit breaker and retry logic."""
        if not self.circuit_breaker.can_execute():
            raise ServiceCommunicationError("Circuit breaker open")

        self._call_count += 1

        try:
            with tracer.start_span(f"grpc_call_{self.service_name}_{method_name}") as span:
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("grpc.method", method_name)

                # Inject tracing context into gRPC metadata
                metadata = []
                inject(metadata)

                # Execute the call
                response = await self._execute_call(method_name, request, timeout, metadata)

                self.circuit_breaker.on_success()
                span.set_attribute("grpc.status", "success")
                return response

        except Exception as e:
            self.circuit_breaker.on_failure()
            self._error_count += 1
            logger.error("gRPC call failed",
                        service=self.service_name, method=method_name, error=str(e))

            if "timeout" in str(e).lower():
                raise ServiceCommunicationError(f"Call timeout: {e}")
            elif "authentication" in str(e).lower():
                raise ServiceCommunicationError(f"Authentication failed: {e}")
            else:
                raise ServiceCommunicationError(f"gRPC call failed: {e}")

    @abstractmethod
    async def _execute_call(self, method_name: str, request: Any, timeout: float, metadata: List) -> Any:
        """Execute the actual gRPC call - implemented by subclasses."""
        pass

    async def health_check(self) -> HealthResponse:
        """Perform health check on the service."""
        try:
            from grpc_health.v1 import health_pb2, health_pb2_grpc

            health_stub = health_pb2_grpc.HealthStub(self._channel)
            request = health_pb2.HealthCheckRequest(service="")

            response = await health_stub.Check(request, timeout=DEFAULT_HEALTH_CHECK_TIMEOUT)
            status = "SERVING" if response.status == health_pb2.HealthCheckResponse.SERVING else "NOT_SERVING"

            return HealthResponse(
                status=status,
                service=self.service_name,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            )

        except Exception as e:
            logger.warning("Health check failed", service=self.service_name, error=str(e))
            return HealthResponse(status="UNKNOWN", service=self.service_name)


class TradingEngineClient(BaseGrpcClient):
    """gRPC client for trading-system-engine-py service."""

    def __init__(self, host: str, port: int, settings: Settings):
        super().__init__("trading-system-engine", host, port, settings)

    async def _execute_call(self, method_name: str, request: Any, timeout: float, metadata: List) -> Any:
        """Execute trading engine gRPC call."""
        # Mock implementation for now - will be replaced with actual protobuf calls
        if method_name == "get_strategy_status":
            return StrategyStatus(
                strategy_id=getattr(request, 'strategy_id', 'mock_strategy'),
                status="ACTIVE",
                positions=[],
                last_updated=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            )
        elif method_name == "get_current_positions":
            return [
                Position(
                    instrument_id="BTC/USD",
                    quantity=0.5,
                    value=25000.0,
                    side="LONG",
                    entry_price=49000.0,
                    current_price=50000.0,
                    unrealized_pnl=500.0
                )
            ]
        else:
            raise ServiceCommunicationError(f"Unknown method: {method_name}")

    async def get_strategy_status(self, strategy_id: str, timeout: float = DEFAULT_GRPC_TIMEOUT) -> StrategyStatus:
        """Get trading strategy status."""
        request = MagicMock()
        request.strategy_id = strategy_id
        return await self._make_call("get_strategy_status", request, timeout)

    async def get_current_positions(self, timeout: float = DEFAULT_GRPC_TIMEOUT) -> List[Position]:
        """Get current trading positions."""
        request = MagicMock()
        return await self._make_call("get_current_positions", request, timeout)


class CoordinatorGrpcClient(BaseGrpcClient):
    """gRPC client for test-coordinator-py service."""

    def __init__(self, host: str, port: int, settings: Settings):
        super().__init__("test-coordinator", host, port, settings)
        self._chaos_subscribers: List[Callable[[ChaosEvent], None]] = []

    async def _execute_call(self, method_name: str, request: Any, timeout: float, metadata: List) -> Any:
        """Execute test coordinator gRPC call."""
        # Mock implementation for now - will be replaced with actual protobuf calls
        if method_name == "get_current_scenario_status":
            return ScenarioStatus(
                scenario_id="test_scenario_001",
                status="RUNNING",
                start_time=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                progress=0.75,
                current_phase="chaos_injection"
            )
        elif method_name == "simulate_chaos_event":
            event_type = getattr(request, 'event_type', 'service_restart')
            target_service = getattr(request, 'target_service', 'unknown')

            # Create and notify about chaos event
            chaos_event = ChaosEvent(
                event_type=event_type,
                target_service=target_service,
                event_id=f"chaos_{int(time.time())}",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            )

            # Notify subscribers
            for callback in self._chaos_subscribers:
                try:
                    callback(chaos_event)
                except Exception as e:
                    logger.error("Chaos event callback failed", error=str(e))

            return chaos_event
        else:
            raise ServiceCommunicationError(f"Unknown method: {method_name}")

    async def get_current_scenario_status(self, timeout: float = DEFAULT_GRPC_TIMEOUT) -> ScenarioStatus:
        """Get current test scenario status."""
        request = MagicMock()
        return await self._make_call("get_current_scenario_status", request, timeout)

    async def subscribe_to_chaos_events(self, callback: Callable[[ChaosEvent], None]) -> None:
        """Subscribe to chaos event notifications."""
        self._chaos_subscribers.append(callback)
        logger.info("Subscribed to chaos events",
                   subscribers_count=len(self._chaos_subscribers))

    async def simulate_chaos_event(self, event_type: str, target_service: str, timeout: float = DEFAULT_GRPC_TIMEOUT) -> ChaosEvent:
        """Simulate a chaos engineering event."""
        request = MagicMock()
        request.event_type = event_type
        request.target_service = target_service
        return await self._make_call("simulate_chaos_event", request, timeout)


class InterServiceClientManager:
    """Manager for coordinating multiple gRPC service clients."""

    def __init__(self, settings: Settings, service_discovery: Optional[ServiceDiscovery] = None):
        self.settings = settings
        self.service_discovery = service_discovery
        self._trading_client: Optional[TradingEngineClient] = None
        self._test_coordinator_client: Optional[CoordinatorGrpcClient] = None
        self._clients: Dict[str, BaseGrpcClient] = {}
        self.connection_pool_size = 0
        self._initialization_time: Optional[float] = None

    async def initialize(self) -> None:
        """Initialize the client manager."""
        logger.info("Initializing inter-service client manager")
        self._initialization_time = time.time()
        # Initialization complete - clients will be created on-demand

    def get_manager_stats(self) -> Dict[str, Any]:
        """Get manager performance statistics."""
        uptime = time.time() - self._initialization_time if self._initialization_time else 0

        client_stats = {}
        for name, client in self._clients.items():
            client_stats[name] = client.get_stats()

        return {
            "uptime_seconds": round(uptime, 2),
            "active_clients": len(self._clients),
            "connection_pool_size": self.connection_pool_size,
            "total_channels": len(BaseGrpcClient._channels),
            "client_stats": client_stats
        }

    async def cleanup(self) -> None:
        """Cleanup all clients and connections."""
        logger.info("Cleaning up inter-service client manager")

        # Disconnect all clients
        cleanup_tasks = []
        for client in self._clients.values():
            if client.is_connected():
                cleanup_tasks.append(client.disconnect())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        # Close all shared channels
        close_tasks = []
        for channel in BaseGrpcClient._channels.values():
            close_tasks.append(channel.close())

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        BaseGrpcClient._channels.clear()
        self._clients.clear()
        self.connection_pool_size = 0

        logger.info("Inter-service client manager cleanup complete")

    async def get_trading_engine_client(self, use_fallback: bool = False) -> TradingEngineClient:
        """Get or create trading engine client."""
        if self._trading_client and self._trading_client.is_connected():
            return self._trading_client

        try:
            # Find trading engine service
            if self.service_discovery and not use_fallback:
                service_info = await self.service_discovery.get_service("trading-system-engine")
                if not service_info:
                    raise ServiceCommunicationError("Service not found: trading-system-engine")

                host = service_info.host
                port = service_info.grpc_port
            else:
                # Fallback to default endpoints
                host = getattr(self.settings, 'trading_engine_host', 'localhost')
                port = getattr(self.settings, 'trading_engine_grpc_port', DEFAULT_TRADING_ENGINE_PORT)

            # Create and connect client
            self._trading_client = TradingEngineClient(host, port, self.settings)
            await self._trading_client.connect()

            self._clients["trading-engine"] = self._trading_client
            self.connection_pool_size += 1

            logger.info("Trading engine client created", host=host, port=port)
            return self._trading_client

        except Exception as e:
            logger.error("Failed to create trading engine client", error=str(e))
            if "Service not found" in str(e):
                raise ServiceCommunicationError(f"Service not found: trading-system-engine")
            else:
                raise ServiceCommunicationError(f"Connection failed: {e}")

    async def get_test_coordinator_client(self, use_fallback: bool = False) -> CoordinatorGrpcClient:
        """Get or create test coordinator client."""
        if self._test_coordinator_client and self._test_coordinator_client.is_connected():
            return self._test_coordinator_client

        try:
            # Find test coordinator service
            if self.service_discovery and not use_fallback:
                service_info = await self.service_discovery.get_service("test-coordinator")
                if not service_info:
                    raise ServiceCommunicationError("Service not found: test-coordinator")

                host = service_info.host
                port = service_info.grpc_port
            else:
                # Fallback to default endpoints
                host = getattr(self.settings, 'test_coordinator_host', 'localhost')
                port = getattr(self.settings, 'test_coordinator_grpc_port', DEFAULT_TEST_COORDINATOR_PORT)

            # Create and connect client
            self._test_coordinator_client = CoordinatorGrpcClient(host, port, self.settings)
            await self._test_coordinator_client.connect()

            self._clients["test-coordinator"] = self._test_coordinator_client
            self.connection_pool_size += 1

            logger.info("Test coordinator client created", host=host, port=port)
            return self._test_coordinator_client

        except Exception as e:
            logger.error("Failed to create test coordinator client", error=str(e))
            if "Service not found" in str(e):
                raise ServiceCommunicationError(f"Service not found: test-coordinator")
            else:
                raise ServiceCommunicationError(f"Connection failed: {e}")