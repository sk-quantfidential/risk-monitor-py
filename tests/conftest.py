"""Test configuration and fixtures."""
import asyncio
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from risk_monitor.infrastructure.config import Settings
from risk_monitor.presentation.http.app import create_fastapi_app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings configuration."""
    return Settings(
        environment="testing",
        debug=True,
        log_level="DEBUG",
        http_port=8084,
        grpc_port=50054,
        redis_url="redis://localhost:6379/15",  # Use test DB
        service_name="risk-monitor-test",
        service_version="0.1.0-test",
        otel_service_name="risk-monitor-test",
        otel_exporter_endpoint="http://localhost:4317",
        otel_insecure=True,
    )


@pytest.fixture
def fastapi_app(test_settings: Settings):
    """Create FastAPI application for testing."""
    return create_fastapi_app(test_settings)


@pytest.fixture
def test_client(fastapi_app) -> TestClient:
    """Create synchronous test client."""
    return TestClient(fastapi_app)


@pytest_asyncio.fixture
async def async_client(fastapi_app) -> AsyncGenerator[AsyncClient]:
    """Create async test client."""
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock = AsyncMock()
    mock.ping.return_value = True
    mock.hset.return_value = True
    mock.expire.return_value = True
    mock.hgetall.return_value = {}
    mock.keys.return_value = []
    mock.delete.return_value = True
    mock.aclose.return_value = None
    return mock


@pytest.fixture
def mock_service_discovery(mock_redis):
    """Mock service discovery for testing."""
    from risk_monitor.infrastructure.service_discovery import ServiceDiscovery

    mock_discovery = AsyncMock(spec=ServiceDiscovery)
    mock_discovery.redis_client = mock_redis
    mock_discovery.connect.return_value = None
    mock_discovery.register_service.return_value = None
    mock_discovery.disconnect.return_value = None
    mock_discovery.discover_services.return_value = []

    return mock_discovery


@pytest.fixture
def sample_risk_metrics():
    """Sample risk metrics data for testing."""
    return {
        "id": "risk_AAPL_1234567890",
        "instrument_id": "AAPL",
        "calculation_date": "2025-09-20T10:00:00Z",
        "calculation_method": "Historical Simulation",
        "volatility": {
            "historical_volatility_30d": 0.25,
            "implied_volatility": 0.22
        },
        "var_metrics": {
            "var_1d_95": 1000.0,
            "var_1d_99": 1500.0
        }
    }


@pytest.fixture
def sample_portfolio_metrics():
    """Sample portfolio risk metrics for testing."""
    return {
        "id": "portfolio_risk_TEST_PORTFOLIO_1234567890",
        "portfolio_id": "TEST_PORTFOLIO",
        "total_value": 1000000.0,
        "calculation_date": "2025-09-20T10:00:00Z",
        "concentration": {
            "single_name_concentration": 0.15,
            "top_10_concentration": 0.65
        }
    }


# gRPC Testing Fixtures
@pytest.fixture
def grpc_test_server():
    """Create gRPC test server."""
    from grpc_health.v1 import health_pb2_grpc
    from grpc_testing import server_from_dictionary

    from risk_monitor.presentation.grpc.services.health import HealthService

    # Create servicer
    health_service = HealthService()

    # Create test server
    servicers = {
        health_pb2_grpc.DESCRIPTOR.services_by_name['Health']: health_service
    }

    return server_from_dictionary(servicers, health_pb2_grpc.DESCRIPTOR)


@pytest.fixture
def mock_grpc_context():
    """Mock gRPC context for testing."""
    context = MagicMock()
    context.cancelled.return_value = False
    context.set_code = MagicMock()
    context.set_details = MagicMock()
    return context


# Protobuf Testing Fixtures
@pytest.fixture
def mock_protobuf_available(monkeypatch):
    """Mock protobuf availability for testing."""
    # This fixture can be used to test both scenarios:
    # - When protobuf is available
    # - When protobuf is not available
    pass


@pytest.fixture(autouse=True)
def disable_telemetry():
    """Disable OpenTelemetry for tests to avoid noise."""
    import os
    os.environ["OTEL_SDK_DISABLED"] = "true"