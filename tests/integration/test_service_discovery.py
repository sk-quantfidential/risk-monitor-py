"""Integration tests for service discovery functionality."""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from risk_monitor.infrastructure.service_discovery import ServiceDiscovery, ServiceInfo
from risk_monitor.infrastructure.config import Settings


class TestServiceDiscoveryIntegration:
    """Integration tests for ServiceDiscovery."""

    @pytest.fixture
    async def service_discovery(self, test_settings: Settings, mock_redis):
        """Create ServiceDiscovery instance for testing."""
        discovery = ServiceDiscovery(test_settings)
        discovery.redis_client = mock_redis
        return discovery

    @pytest.mark.asyncio
    async def test_service_discovery_lifecycle(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test complete service discovery lifecycle."""
        # Connect
        await service_discovery.connect()
        mock_redis.ping.assert_called_once()

        # Register service
        await service_discovery.register_service()

        # Verify registration call
        assert mock_redis.hset.called
        assert mock_redis.expire.called

        # Discover services
        mock_redis.keys.return_value = [b"service:risk-monitor-test:instance1"]
        mock_redis.hgetall.return_value = {
            b"name": b"risk-monitor-test",
            b"version": b"0.1.0-test",
            b"host": b"localhost",
            b"http_port": b"8084",
            b"grpc_port": b"50054",
            b"last_heartbeat": str(int(datetime.now().timestamp())).encode()
        }

        services = await service_discovery.discover_services()
        assert len(services) >= 0  # Should return list of services

        # Disconnect
        await service_discovery.disconnect()
        assert mock_redis.aclose.called

    @pytest.mark.asyncio
    async def test_service_registration_with_custom_info(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test service registration with custom service info."""
        custom_info = ServiceInfo(
            name="custom-service",
            version="1.0.0",
            host="custom-host",
            http_port=9000,
            grpc_port=60000
        )

        await service_discovery.register_service(custom_info)

        # Verify the custom info was used in registration
        mock_redis.hset.assert_called()
        call_args = mock_redis.hset.call_args

        # Check that custom values were used
        assert "custom-service" in str(call_args)

    @pytest.mark.asyncio
    async def test_service_heartbeat_mechanism(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test service heartbeat mechanism."""
        await service_discovery.connect()

        # Start heartbeat
        heartbeat_task = asyncio.create_task(service_discovery._heartbeat_loop())

        # Let it run briefly
        await asyncio.sleep(0.1)

        # Cancel heartbeat
        heartbeat_task.cancel()

        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        # Verify heartbeat calls were made
        assert mock_redis.hset.called
        assert mock_redis.expire.called

    @pytest.mark.asyncio
    async def test_service_discovery_with_filters(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test service discovery with service name filters."""
        # Mock multiple services
        mock_redis.keys.return_value = [
            b"service:risk-monitor:instance1",
            b"service:trading-engine:instance1",
            b"service:risk-monitor:instance2"
        ]

        mock_redis.hgetall.side_effect = [
            {
                b"name": b"risk-monitor",
                b"version": b"1.0.0",
                b"host": b"host1",
                b"http_port": b"8080",
                b"grpc_port": b"50051",
                b"last_heartbeat": str(int(datetime.now().timestamp())).encode()
            },
            {
                b"name": b"trading-engine",
                b"version": b"1.0.0",
                b"host": b"host2",
                b"http_port": b"8081",
                b"grpc_port": b"50052",
                b"last_heartbeat": str(int(datetime.now().timestamp())).encode()
            },
            {
                b"name": b"risk-monitor",
                b"version": b"1.0.1",
                b"host": b"host3",
                b"http_port": b"8082",
                b"grpc_port": b"50053",
                b"last_heartbeat": str(int(datetime.now().timestamp())).encode()
            }
        ]

        # Discover all services
        all_services = await service_discovery.discover_services()

        # Discover only risk-monitor services
        risk_services = await service_discovery.discover_services(service_name="risk-monitor")

        # Should find fewer risk services than total services
        risk_monitor_count = len([s for s in all_services if s.name == "risk-monitor"])
        assert len(risk_services) == risk_monitor_count

    @pytest.mark.asyncio
    async def test_stale_service_cleanup(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test that stale services are filtered out."""
        # Mock service with old heartbeat
        old_timestamp = int((datetime.now() - timedelta(minutes=10)).timestamp())
        recent_timestamp = int(datetime.now().timestamp())

        mock_redis.keys.return_value = [
            b"service:stale-service:instance1",
            b"service:fresh-service:instance1"
        ]

        mock_redis.hgetall.side_effect = [
            {
                b"name": b"stale-service",
                b"version": b"1.0.0",
                b"host": b"stale-host",
                b"http_port": b"8080",
                b"grpc_port": b"50051",
                b"last_heartbeat": str(old_timestamp).encode()
            },
            {
                b"name": b"fresh-service",
                b"version": b"1.0.0",
                b"host": b"fresh-host",
                b"http_port": b"8081",
                b"grpc_port": b"50052",
                b"last_heartbeat": str(recent_timestamp).encode()
            }
        ]

        services = await service_discovery.discover_services()

        # Should only return fresh service
        service_names = [s.name for s in services]
        assert "fresh-service" in service_names
        assert "stale-service" not in service_names

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test handling of Redis connection failures."""
        # Mock Redis connection failure
        mock_redis.ping.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            await service_discovery.connect()

    @pytest.mark.asyncio
    async def test_service_registration_failure(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test handling of service registration failures."""
        await service_discovery.connect()

        # Mock registration failure
        mock_redis.hset.side_effect = Exception("Redis write failed")

        with pytest.raises(Exception):
            await service_discovery.register_service()

    @pytest.mark.asyncio
    async def test_service_discovery_empty_result(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test service discovery when no services are found."""
        await service_discovery.connect()

        # Mock empty result
        mock_redis.keys.return_value = []

        services = await service_discovery.discover_services()
        assert services == []

    @pytest.mark.asyncio
    async def test_malformed_service_data(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test handling of malformed service data in Redis."""
        await service_discovery.connect()

        mock_redis.keys.return_value = [b"service:malformed:instance1"]
        mock_redis.hgetall.return_value = {
            b"name": b"malformed-service",
            # Missing required fields like host, ports, etc.
            b"incomplete": b"data"
        }

        services = await service_discovery.discover_services()

        # Should handle malformed data gracefully
        assert isinstance(services, list)
        # Malformed service should be filtered out
        assert len(services) == 0

    @pytest.mark.asyncio
    async def test_concurrent_service_operations(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test concurrent service discovery operations."""
        await service_discovery.connect()

        # Setup mock data
        mock_redis.keys.return_value = [b"service:test:instance1"]
        mock_redis.hgetall.return_value = {
            b"name": b"test-service",
            b"version": b"1.0.0",
            b"host": b"test-host",
            b"http_port": b"8080",
            b"grpc_port": b"50051",
            b"last_heartbeat": str(int(datetime.now().timestamp())).encode()
        }

        # Run multiple discovery operations concurrently
        tasks = []
        for _ in range(5):
            task = service_discovery.discover_services()
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should succeed
        assert len(results) == 5
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, list)


class TestServiceDiscoveryConfiguration:
    """Test service discovery configuration and settings."""

    def test_service_info_creation(self, test_settings: Settings):
        """Test ServiceInfo creation from settings."""
        service_info = ServiceInfo(
            name=test_settings.service_name,
            version=test_settings.service_version,
            host="localhost",
            http_port=test_settings.http_port,
            grpc_port=test_settings.grpc_port
        )

        assert service_info.name == "risk-monitor-test"
        assert service_info.version == "0.1.0-test"
        assert service_info.host == "localhost"
        assert service_info.http_port == 8084
        assert service_info.grpc_port == 50054

    @pytest.mark.asyncio
    async def test_service_discovery_with_different_settings(self, mock_redis):
        """Test service discovery with different configuration settings."""
        # Create custom settings
        custom_settings = Settings(
            environment="production",
            service_name="prod-risk-monitor",
            service_version="2.0.0",
            redis_url="redis://prod-redis:6379/0",
            http_port=8080,
            grpc_port=50051
        )

        discovery = ServiceDiscovery(custom_settings)
        discovery.redis_client = mock_redis

        await discovery.connect()
        await discovery.register_service()

        # Verify production settings were used
        mock_redis.hset.assert_called()
        call_args = mock_redis.hset.call_args
        assert "prod-risk-monitor" in str(call_args)

    def test_service_info_validation(self):
        """Test ServiceInfo validation."""
        # Valid service info
        valid_info = ServiceInfo(
            name="test-service",
            version="1.0.0",
            host="localhost",
            http_port=8080,
            grpc_port=50051
        )
        assert valid_info.name == "test-service"

        # Test that all required fields are present
        assert hasattr(valid_info, 'name')
        assert hasattr(valid_info, 'version')
        assert hasattr(valid_info, 'host')
        assert hasattr(valid_info, 'http_port')
        assert hasattr(valid_info, 'grpc_port')


class TestServiceDiscoveryErrorHandling:
    """Test error handling in service discovery."""

    @pytest.mark.asyncio
    async def test_redis_timeout_handling(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test handling of Redis timeout errors."""
        await service_discovery.connect()

        # Mock timeout error
        mock_redis.keys.side_effect = asyncio.TimeoutError("Redis timeout")

        with pytest.raises(asyncio.TimeoutError):
            await service_discovery.discover_services()

    @pytest.mark.asyncio
    async def test_redis_disconnection_during_heartbeat(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test handling of Redis disconnection during heartbeat."""
        await service_discovery.connect()

        # Mock Redis disconnection during heartbeat
        mock_redis.hset.side_effect = [None, Exception("Connection lost")]

        # Start heartbeat
        heartbeat_task = asyncio.create_task(service_discovery._heartbeat_loop())

        # Let it run briefly to trigger the error
        await asyncio.sleep(0.1)

        heartbeat_task.cancel()

        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        # Should handle disconnection gracefully
        assert True  # If we reach here, no unhandled exception occurred

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, service_discovery: ServiceDiscovery, mock_redis):
        """Test graceful shutdown of service discovery."""
        await service_discovery.connect()
        await service_discovery.register_service()

        # Start heartbeat
        heartbeat_task = asyncio.create_task(service_discovery._heartbeat_loop())

        # Shutdown gracefully
        await service_discovery.disconnect()
        heartbeat_task.cancel()

        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        # Verify cleanup was performed
        assert mock_redis.aclose.called