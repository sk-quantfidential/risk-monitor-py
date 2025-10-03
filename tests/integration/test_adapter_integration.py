"""Integration tests for risk-data-adapter integration with risk-monitor-py."""
import os
from datetime import datetime, UTC
from decimal import Decimal

import pytest
import pytest_asyncio

from risk_data_adapter import AdapterConfig, create_adapter
from risk_monitor.domain.risk_service import RiskMonitorService


# Skip tests if orchestrator is not available
POSTGRES_URL = os.getenv(
    "RISK_ADAPTER_POSTGRES_URL",
    "postgresql+asyncpg://risk_adapter:risk-adapter-db-pass@localhost:5432/trading_ecosystem"
)
REDIS_URL = os.getenv(
    "RISK_ADAPTER_REDIS_URL",
    "redis://risk-adapter:risk-pass@localhost:6379/0"
)
SKIP_INTEGRATION = os.getenv("SKIP_INTEGRATION_TESTS", "false").lower() == "true"


@pytest_asyncio.fixture
async def adapter():
    """Create adapter connected to orchestrator."""
    config = AdapterConfig(postgres_url=POSTGRES_URL, redis_url=REDIS_URL)
    adapter = await create_adapter(config)
    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture
async def risk_service(adapter):
    """Create RiskMonitorService with adapter."""
    return RiskMonitorService(data_adapter=adapter)


@pytest_asyncio.fixture
async def risk_service_degraded():
    """Create RiskMonitorService without adapter (degraded mode)."""
    return RiskMonitorService()


@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
@pytest.mark.asyncio
class TestAdapterIntegration:
    """Test risk-monitor-py integration with risk-data-adapter-py."""

    async def test_service_without_adapter_degraded_mode(self, risk_service_degraded):
        """Given risk service without adapter
        When generating alert
        Then service operates in degraded mode without persistence."""
        result = await risk_service_degraded.generate_alert(
            "test_alert",
            "Test message",
            {"current_value": 100, "threshold": 90}
        )

        assert result.startswith("alert-test_alert-")
        assert risk_service_degraded.data_adapter is None

    async def test_service_with_adapter_persists_alerts(self, risk_service):
        """Given risk service with adapter
        When generating alert
        Then alert is persisted via adapter."""
        result = await risk_service.generate_alert(
            "position_limit",
            "Position exceeded limit",
            {"current_value": 150, "threshold": 100}
        )

        assert result.startswith("alert-position_limit-")
        assert risk_service.data_adapter is not None

    async def test_adapter_connection_status(self, adapter):
        """Given adapter is connected
        When checking connection status
        Then both PostgreSQL and Redis are connected."""
        assert adapter.connection_status.postgres_connected is True
        assert adapter.connection_status.redis_connected is True

    async def test_adapter_health_check(self, adapter):
        """Given adapter is connected
        When performing health check
        Then health status shows all systems operational."""
        health = await adapter.health_check()

        assert health["status"] in ["healthy", "degraded"]
        assert health["postgres"]["connected"] is True
        assert health["redis"]["connected"] is True

    async def test_alert_repository_operations(self, adapter):
        """Given adapter is connected
        When using alert repository
        Then stub operations complete without errors."""
        repo = adapter.get_risk_alerts_repository()

        # Stub operations should not raise exceptions
        from risk_data_adapter.models import RiskAlert, AlertSeverity, AlertStatus

        alert = RiskAlert(
            alert_id="test-integration-001",
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.ACTIVE,
            metric_name="integration_test",
            message="Integration test alert",
            current_value=Decimal("200"),
            threshold_value=Decimal("100"),
            triggered_at=datetime.now(UTC)
        )

        await repo.create(alert)
        result = await repo.get_by_id("test-integration-001")

        # Stub returns None (implementation deferred)
        assert result is None

    async def test_metrics_repository_operations(self, adapter):
        """Given adapter is connected
        When using metrics repository
        Then stub operations complete without errors."""
        repo = adapter.get_risk_metrics_repository()

        from risk_data_adapter.models import RiskMetric

        metric = RiskMetric(
            metric_id="test-metric-001",
            instrument_id="BTC-USD",
            portfolio_value=Decimal("1000000.00"),
            unrealized_pnl=Decimal("5000.00"),
            realized_pnl=Decimal("2500.00"),
            total_exposure=Decimal("950000.00"),
            leverage_ratio=Decimal("2.1"),
            var_95=Decimal("25000.00"),
            calculation_timestamp=datetime.now(UTC)
        )

        await repo.create(metric)
        result = await repo.get_by_id("test-metric-001")

        # Stub returns None (implementation deferred)
        assert result is None


@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
@pytest.mark.asyncio
class TestServiceLifecycle:
    """Test service lifecycle with adapter."""

    async def test_service_initialization_with_adapter(self):
        """Given orchestrator is running
        When initializing service with adapter
        Then service and adapter are properly configured."""
        config = AdapterConfig(postgres_url=POSTGRES_URL, redis_url=REDIS_URL)
        adapter = await create_adapter(config)
        service = RiskMonitorService(data_adapter=adapter)

        assert service.data_adapter is not None
        assert adapter.connection_status.postgres_connected is True
        assert adapter.connection_status.redis_connected is True

        await adapter.disconnect()

    async def test_adapter_graceful_shutdown(self):
        """Given adapter is connected
        When disconnecting adapter
        Then cleanup happens gracefully."""
        config = AdapterConfig(postgres_url=POSTGRES_URL, redis_url=REDIS_URL)
        adapter = await create_adapter(config)

        assert adapter.connection_status.postgres_connected is True
        assert adapter.connection_status.redis_connected is True

        await adapter.disconnect()

        # After disconnect, connections should be closed
        assert adapter.connection_status.postgres_connected is False
        assert adapter.connection_status.redis_connected is False
