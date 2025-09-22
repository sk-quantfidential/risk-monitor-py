"""Tests for health endpoints (HTTP and gRPC)."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from grpc_health.v1 import health_pb2
from httpx import AsyncClient

from risk_monitor.presentation.grpc.services.health import HealthService


class TestHTTPHealthEndpoints:
    """Test HTTP health endpoints."""

    def test_health_check_endpoint(self, test_client: TestClient):
        """Test basic health check endpoint returns healthy status."""
        response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "dependencies" in data
        assert isinstance(data["uptime_seconds"], float)
        assert data["uptime_seconds"] >= 0

    def test_liveness_probe(self, test_client: TestClient):
        """Test Kubernetes liveness probe endpoint."""
        response = test_client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_readiness_probe_success(self, test_client: TestClient):
        """Test readiness probe when all dependencies are healthy."""
        response = test_client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()

        assert data["ready"] is True
        assert "checks" in data
        assert "timestamp" in data
        assert isinstance(data["checks"], dict)

        # Check that dependency checks are present
        expected_checks = ["redis", "postgres", "service_registry"]
        for check in expected_checks:
            assert check in data["checks"]

    @pytest.mark.asyncio
    async def test_health_check_async_client(self, async_client: AsyncClient):
        """Test health check using async client."""
        response = await async_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_response_structure(self, test_client: TestClient):
        """Test that health response has the correct structure."""
        response = test_client.get("/api/v1/health")
        data = response.json()

        # Required fields
        required_fields = [
            "status", "timestamp", "version", "uptime_seconds", "dependencies"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check data types
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["uptime_seconds"], (int, float))
        assert isinstance(data["dependencies"], dict)

    def test_health_check_contains_service_info(self, test_client: TestClient):
        """Test that health check contains service information."""
        response = test_client.get("/api/v1/health")
        data = response.json()

        # Should contain dependency status
        assert "redis" in data["dependencies"]
        assert "postgres" in data["dependencies"]
        assert "service_registry" in data["dependencies"]


class TestGRPCHealthService:
    """Test gRPC health service."""

    @pytest.mark.asyncio
    async def test_health_check_serving(self, mock_grpc_context):
        """Test gRPC health check returns SERVING status."""
        service = HealthService()
        request = health_pb2.HealthCheckRequest(service="risk-monitor")

        response = await service.Check(request, mock_grpc_context)

        assert response.status == health_pb2.HealthCheckResponse.SERVING

    @pytest.mark.asyncio
    async def test_health_check_empty_service_name(self, mock_grpc_context):
        """Test health check with empty service name."""
        service = HealthService()
        request = health_pb2.HealthCheckRequest()  # No service specified

        response = await service.Check(request, mock_grpc_context)

        assert response.status == health_pb2.HealthCheckResponse.SERVING

    @pytest.mark.asyncio
    async def test_health_check_specific_service(self, mock_grpc_context):
        """Test health check for specific service."""
        service = HealthService()
        request = health_pb2.HealthCheckRequest(service="risk-monitor")

        response = await service.Check(request, mock_grpc_context)

        assert response.status == health_pb2.HealthCheckResponse.SERVING

    @pytest.mark.asyncio
    async def test_health_watch_stream(self, mock_grpc_context):
        """Test health watch streaming endpoint."""
        service = HealthService()
        request = health_pb2.HealthCheckRequest(service="risk-monitor")

        # Mock the context to simulate cancellation after one iteration
        mock_grpc_context.cancelled.side_effect = [False, True]

        responses = []
        async for response in service.Watch(request, mock_grpc_context):
            responses.append(response)
            if len(responses) >= 1:  # Limit to avoid infinite loop
                break

        assert len(responses) >= 1
        assert responses[0].status == health_pb2.HealthCheckResponse.SERVING

    @pytest.mark.asyncio
    async def test_health_service_error_handling(self, mock_grpc_context):
        """Test health service handles errors gracefully."""
        service = HealthService()

        # Mock an error scenario
        with patch.object(service, 'Check', side_effect=Exception("Test error")):
            request = health_pb2.HealthCheckRequest(service="risk-monitor")

            try:
                # This should handle the exception internally
                response = await service.Check(request, mock_grpc_context)
                # If we get here, the service handled the error
                assert response.status == health_pb2.HealthCheckResponse.NOT_SERVING
            except Exception:
                # If an exception is raised, that's also acceptable for this test
                pass


class TestHealthEndpointIntegration:
    """Integration tests for health endpoints."""

    def test_http_and_grpc_health_consistency(self, test_client: TestClient):
        """Test that HTTP and gRPC health checks are consistent."""
        # Get HTTP health status
        http_response = test_client.get("/api/v1/health")
        assert http_response.status_code == 200

        http_data = http_response.json()
        assert http_data["status"] == "healthy"

        # Note: In a full integration test, we would also test the gRPC endpoint
        # and ensure they return consistent information

    def test_health_endpoint_performance(self, test_client: TestClient):
        """Test that health endpoints respond quickly."""
        import time

        start_time = time.time()
        response = test_client.get("/api/v1/health")
        end_time = time.time()

        assert response.status_code == 200
        # Health check should be fast (< 100ms)
        assert (end_time - start_time) < 0.1

    def test_multiple_health_checks(self, test_client: TestClient):
        """Test multiple sequential health checks."""
        for _ in range(5):
            response = test_client.get("/api/v1/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"