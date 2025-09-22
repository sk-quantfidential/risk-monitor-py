"""Tests for risk monitoring HTTP routes."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from risk_monitor.presentation.http.routers.risk import (
    RiskMetrics,
)


class TestRiskMetricsEndpoint:
    """Test HTTP risk metrics endpoint."""

    def test_get_risk_metrics_success(self, test_client: TestClient):
        """Test successful risk metrics retrieval."""
        response = test_client.get(
            "/api/v1/risk/metrics",
            params={"instrument_id": "AAPL"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure matches RiskMetrics model
        required_fields = [
            "portfolio_value", "unrealized_pnl", "realized_pnl",
            "total_exposure", "leverage_ratio", "var_95", "timestamp"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify data types
        assert isinstance(data["portfolio_value"], (int, float))
        assert isinstance(data["unrealized_pnl"], (int, float))
        assert isinstance(data["realized_pnl"], (int, float))
        assert isinstance(data["total_exposure"], (int, float))
        assert isinstance(data["leverage_ratio"], (int, float))
        assert isinstance(data["var_95"], (int, float))
        assert isinstance(data["timestamp"], str)

    def test_get_risk_metrics_with_params(self, test_client: TestClient):
        """Test risk metrics with custom parameters."""
        response = test_client.get(
            "/api/v1/risk/metrics",
            params={
                "instrument_id": "TSLA",
                "lookback_days": 60,
                "confidence_level": 0.99
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "portfolio_value" in data

    def test_get_risk_metrics_missing_instrument_id(self, test_client: TestClient):
        """Test risk metrics endpoint without required instrument_id."""
        response = test_client.get("/api/v1/risk/metrics")

        assert response.status_code == 422  # Validation error

    def test_get_risk_metrics_invalid_params(self, test_client: TestClient):
        """Test risk metrics with invalid parameters."""
        response = test_client.get(
            "/api/v1/risk/metrics",
            params={
                "instrument_id": "AAPL",
                "lookback_days": 0,  # Invalid: must be >= 1
                "confidence_level": 1.5  # Invalid: must be <= 0.99
            }
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_risk_metrics_async_client(self, async_client: AsyncClient):
        """Test risk metrics using async client."""
        response = await async_client.get(
            "/api/v1/risk/metrics",
            params={"instrument_id": "BTC-USD"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "portfolio_value" in data

    @patch('risk_monitor.presentation.shared.converters.PROTOBUF_AVAILABLE', False)
    def test_get_risk_metrics_fallback_mode(self, test_client: TestClient):
        """Test risk metrics fallback when protobuf unavailable."""
        response = test_client.get(
            "/api/v1/risk/metrics",
            params={"instrument_id": "AAPL"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should return mock data structure
        assert data["portfolio_value"] == 1000000.0
        assert data["unrealized_pnl"] == 5000.0
        assert data["realized_pnl"] == 2500.0
        assert data["total_exposure"] == 950000.0
        assert data["leverage_ratio"] == 2.1
        assert data["var_95"] == 25000.0

    @patch('risk_monitor.presentation.shared.converters.PROTOBUF_AVAILABLE', True)
    @patch('risk_monitor.presentation.grpc.services.risk.RiskAnalyticsService')
    def test_get_risk_metrics_grpc_integration(self, mock_service_class, test_client: TestClient):
        """Test risk metrics with gRPC service integration."""
        # Mock the gRPC service response
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status.success = True
        mock_response.risk_metrics = MagicMock()
        mock_service.GetRiskMetrics.return_value = mock_response

        # Mock the converter functions
        with patch('risk_monitor.presentation.shared.converters.create_risk_metrics_request') as mock_create_request, \
             patch('risk_monitor.presentation.shared.converters.protobuf_to_risk_metrics_model') as mock_converter:

            mock_converter.return_value = RiskMetrics(
                portfolio_value=2000000.0,
                unrealized_pnl=10000.0,
                realized_pnl=5000.0,
                total_exposure=1900000.0,
                leverage_ratio=1.5,
                var_95=30000.0,
                timestamp=datetime.now()
            )

            response = test_client.get(
                "/api/v1/risk/metrics",
                params={"instrument_id": "AAPL"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["portfolio_value"] == 2000000.0

            # Verify gRPC service was called
            mock_service.GetRiskMetrics.assert_called_once()
            mock_create_request.assert_called_once()

    @patch('risk_monitor.presentation.shared.converters.PROTOBUF_AVAILABLE', True)
    @patch('risk_monitor.presentation.grpc.services.risk.RiskAnalyticsService')
    def test_get_risk_metrics_grpc_error(self, mock_service_class, test_client: TestClient):
        """Test risk metrics when gRPC service returns error."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        # Mock error response
        mock_response = MagicMock()
        mock_response.status.success = False
        mock_response.status.message = "Risk calculation failed"
        mock_service.GetRiskMetrics.return_value = mock_response

        with patch('risk_monitor.presentation.shared.converters.create_risk_metrics_request'):
            response = test_client.get(
                "/api/v1/risk/metrics",
                params={"instrument_id": "INVALID"}
            )

            assert response.status_code == 500
            assert "Risk calculation failed" in response.json()["detail"]


class TestRiskAlertsEndpoint:
    """Test HTTP risk alerts endpoint."""

    def test_get_risk_alerts_default(self, test_client: TestClient):
        """Test getting risk alerts with default parameters."""
        response = test_client.get("/api/v1/risk/alerts")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if data:  # If alerts are returned
            alert = data[0]
            required_fields = [
                "alert_id", "severity", "message", "metric_name",
                "current_value", "threshold_value", "timestamp"
            ]
            for field in required_fields:
                assert field in alert

    def test_get_risk_alerts_with_severity_filter(self, test_client: TestClient):
        """Test getting risk alerts filtered by severity."""
        response = test_client.get(
            "/api/v1/risk/alerts",
            params={"severity": "high"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # All alerts should have 'high' severity
        for alert in data:
            assert alert["severity"] == "high"

    def test_get_risk_alerts_with_limit(self, test_client: TestClient):
        """Test getting risk alerts with limit parameter."""
        response = test_client.get(
            "/api/v1/risk/alerts",
            params={"limit": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_get_risk_alerts_invalid_severity(self, test_client: TestClient):
        """Test risk alerts with invalid severity parameter."""
        response = test_client.get(
            "/api/v1/risk/alerts",
            params={"severity": "invalid"}
        )

        assert response.status_code == 422

    def test_get_risk_alerts_invalid_limit(self, test_client: TestClient):
        """Test risk alerts with invalid limit parameter."""
        response = test_client.get(
            "/api/v1/risk/alerts",
            params={"limit": 0}  # Invalid: must be >= 1
        )

        assert response.status_code == 422


class TestRiskLimitsEndpoint:
    """Test HTTP risk limits endpoints."""

    def test_get_risk_limits(self, test_client: TestClient):
        """Test getting current risk limits."""
        response = test_client.get("/api/v1/risk/limits")

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "max_position_size", "max_leverage", "var_limit", "daily_loss_limit"
        ]
        for field in required_fields:
            assert field in data
            assert isinstance(data[field], (int, float))
            assert data[field] > 0

    def test_update_risk_limits_success(self, test_client: TestClient):
        """Test updating risk limits successfully."""
        new_limits = {
            "max_position_size": 2000000.0,
            "max_leverage": 2.5,
            "var_limit": 75000.0,
            "daily_loss_limit": 150000.0
        }

        response = test_client.put("/api/v1/risk/limits", json=new_limits)

        assert response.status_code == 200
        data = response.json()

        # Should return the updated limits
        assert data["max_position_size"] == 2000000.0
        assert data["max_leverage"] == 2.5
        assert data["var_limit"] == 75000.0
        assert data["daily_loss_limit"] == 150000.0

    def test_update_risk_limits_invalid_data(self, test_client: TestClient):
        """Test updating risk limits with invalid data."""
        invalid_limits = {
            "max_position_size": -1000.0,  # Invalid: must be > 0
            "max_leverage": 0,  # Invalid: must be > 0
            "var_limit": -500.0,  # Invalid: must be > 0
            "daily_loss_limit": 0  # Invalid: must be > 0
        }

        response = test_client.put("/api/v1/risk/limits", json=invalid_limits)

        assert response.status_code == 422

    def test_update_risk_limits_missing_fields(self, test_client: TestClient):
        """Test updating risk limits with missing required fields."""
        incomplete_limits = {
            "max_position_size": 1000000.0
            # Missing other required fields
        }

        response = test_client.put("/api/v1/risk/limits", json=incomplete_limits)

        assert response.status_code == 422


class TestRiskCalculationEndpoint:
    """Test HTTP risk calculation endpoint."""

    def test_calculate_risk_not_implemented(self, test_client: TestClient):
        """Test that risk calculation endpoint returns not implemented."""
        portfolio_positions = [
            {"symbol": "AAPL", "quantity": 100, "price": 150.0},
            {"symbol": "GOOGL", "quantity": 50, "price": 2500.0}
        ]

        response = test_client.post("/api/v1/risk/calculate", json=portfolio_positions)

        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]


class TestRiskEndpointIntegration:
    """Integration tests for risk endpoints."""

    def test_risk_endpoints_consistency(self, test_client: TestClient):
        """Test that risk endpoints return consistent data structures."""
        # Get current limits
        limits_response = test_client.get("/api/v1/risk/limits")
        assert limits_response.status_code == 200
        limits = limits_response.json()

        # Get risk metrics
        metrics_response = test_client.get(
            "/api/v1/risk/metrics",
            params={"instrument_id": "AAPL"}
        )
        assert metrics_response.status_code == 200
        metrics = metrics_response.json()

        # Verify that VaR doesn't exceed limits
        # This is a business logic check
        if metrics["var_95"] > limits["var_limit"]:
            # Should trigger an alert
            alerts_response = test_client.get("/api/v1/risk/alerts")
            assert alerts_response.status_code == 200

    def test_risk_endpoint_performance(self, test_client: TestClient):
        """Test that risk endpoints respond quickly."""
        import time

        start_time = time.time()
        response = test_client.get(
            "/api/v1/risk/metrics",
            params={"instrument_id": "AAPL"}
        )
        end_time = time.time()

        assert response.status_code == 200
        # Risk calculation should be fast (< 1 second)
        assert (end_time - start_time) < 1.0

    @pytest.mark.asyncio
    async def test_concurrent_risk_requests(self, async_client: AsyncClient):
        """Test handling of concurrent risk metric requests."""
        import asyncio

        # Make multiple concurrent requests
        tasks = []
        for i in range(5):
            task = async_client.get(
                "/api/v1/risk/metrics",
                params={"instrument_id": f"TEST{i}"}
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "portfolio_value" in data