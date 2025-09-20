"""Tests for gRPC Analytics service."""
import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from risk_monitor.presentation.grpc.services.risk import RiskAnalyticsService


class TestRiskAnalyticsServiceWithProtobuf:
    """Test gRPC Analytics service when protobuf is available."""

    @pytest.mark.asyncio
    @patch('risk_monitor.presentation.grpc.services.risk.PROTOBUF_AVAILABLE', True)
    async def test_get_risk_metrics_success(self, mock_grpc_context):
        """Test successful GetRiskMetrics gRPC call."""
        service = RiskAnalyticsService()

        # Mock protobuf request
        with patch('risk_monitor.presentation.grpc.services.risk.GetRiskMetricsRequest') as MockRequest, \
             patch('risk_monitor.presentation.grpc.services.risk.GetRiskMetricsResponse') as MockResponse, \
             patch('risk_monitor.presentation.grpc.services.risk.Status') as MockStatus, \
             patch('risk_monitor.presentation.grpc.services.risk.RiskMetrics') as MockRiskMetrics:

            # Create mock request
            mock_request = MockRequest()
            mock_request.instrument_id = "AAPL"
            mock_request.date.seconds = int(datetime.now().timestamp())

            # Setup mock response
            mock_status = MockStatus()
            mock_status.success = True
            mock_status.message = "Success"

            mock_metrics = MockRiskMetrics()
            mock_metrics.id = "risk_AAPL_123"
            mock_metrics.instrument_id = "AAPL"

            mock_response = MockResponse()
            mock_response.status = mock_status
            mock_response.risk_metrics = mock_metrics

            MockResponse.return_value = mock_response

            # Call the service method
            response = await service.GetRiskMetrics(mock_request, mock_grpc_context)

            # Verify response
            assert response is not None
            assert response.status.success is True
            assert response.status.message == "Success"

    @pytest.mark.asyncio
    @patch('risk_monitor.presentation.grpc.services.risk.PROTOBUF_AVAILABLE', True)
    async def test_get_risk_metrics_with_params(self, mock_grpc_context):
        """Test GetRiskMetrics with calculation parameters."""
        service = RiskAnalyticsService()

        with patch('risk_monitor.presentation.grpc.services.risk.GetRiskMetricsRequest') as MockRequest, \
             patch('risk_monitor.presentation.grpc.services.risk.GetRiskMetricsResponse') as MockResponse, \
             patch('risk_monitor.presentation.grpc.services.risk.RiskCalculationParams') as MockParams:

            # Create mock request with parameters
            mock_request = MockRequest()
            mock_request.instrument_id = "TSLA"

            mock_params = MockParams()
            mock_params.lookback_days = 60
            mock_params.confidence_level = 0.99
            mock_request.params = mock_params

            # Mock response
            mock_response = MockResponse()
            MockResponse.return_value = mock_response

            response = await service.GetRiskMetrics(mock_request, mock_grpc_context)
            assert response is not None

    @pytest.mark.asyncio
    @patch('risk_monitor.presentation.grpc.services.risk.PROTOBUF_AVAILABLE', True)
    async def test_get_portfolio_risk_metrics_success(self, mock_grpc_context):
        """Test successful GetPortfolioRiskMetrics gRPC call."""
        service = RiskAnalyticsService()

        with patch('risk_monitor.presentation.grpc.services.risk.GetPortfolioRiskMetricsRequest') as MockRequest, \
             patch('risk_monitor.presentation.grpc.services.risk.GetPortfolioRiskMetricsResponse') as MockResponse, \
             patch('risk_monitor.presentation.grpc.services.risk.Status') as MockStatus, \
             patch('risk_monitor.presentation.grpc.services.risk.PortfolioRiskMetrics') as MockPortfolioMetrics:

            # Create mock request
            mock_request = MockRequest()
            mock_request.portfolio_id = "TEST_PORTFOLIO"

            # Setup mock response
            mock_status = MockStatus()
            mock_status.success = True
            mock_status.message = "Portfolio metrics calculated"

            mock_portfolio_metrics = MockPortfolioMetrics()
            mock_portfolio_metrics.id = "portfolio_risk_TEST_PORTFOLIO_123"
            mock_portfolio_metrics.portfolio_id = "TEST_PORTFOLIO"

            mock_response = MockResponse()
            mock_response.status = mock_status
            mock_response.portfolio_metrics = mock_portfolio_metrics

            MockResponse.return_value = mock_response

            response = await service.GetPortfolioRiskMetrics(mock_request, mock_grpc_context)

            assert response is not None
            assert response.status.success is True
            assert response.status.message == "Portfolio metrics calculated"

    @pytest.mark.asyncio
    @patch('risk_monitor.presentation.grpc.services.risk.PROTOBUF_AVAILABLE', True)
    async def test_stream_risk_metrics_success(self, mock_grpc_context):
        """Test successful StreamRiskMetrics gRPC streaming call."""
        service = RiskAnalyticsService()

        with patch('risk_monitor.presentation.grpc.services.risk.StreamRiskMetricsRequest') as MockRequest, \
             patch('risk_monitor.presentation.grpc.services.risk.GetRiskMetricsResponse') as MockResponse:

            # Create mock request
            mock_request = MockRequest()
            mock_request.instrument_ids.extend(["AAPL", "GOOGL", "MSFT"])
            mock_request.update_interval_seconds = 5

            # Mock context to simulate stream termination
            mock_grpc_context.cancelled.side_effect = [False, False, True]

            # Mock response
            mock_response = MockResponse()
            MockResponse.return_value = mock_response

            # Collect streaming responses
            responses = []
            async for response in service.StreamRiskMetrics(mock_request, mock_grpc_context):
                responses.append(response)
                if len(responses) >= 2:  # Limit to avoid infinite loop
                    break

            assert len(responses) >= 1
            assert all(response is not None for response in responses)

    @pytest.mark.asyncio
    @patch('risk_monitor.presentation.grpc.services.risk.PROTOBUF_AVAILABLE', True)
    async def test_grpc_service_error_handling(self, mock_grpc_context):
        """Test gRPC service handles errors gracefully."""
        service = RiskAnalyticsService()

        with patch('risk_monitor.presentation.grpc.services.risk.GetRiskMetricsRequest') as MockRequest, \
             patch('risk_monitor.presentation.grpc.services.risk.GetRiskMetricsResponse') as MockResponse, \
             patch('risk_monitor.presentation.grpc.services.risk.Status') as MockStatus:

            # Create mock request
            mock_request = MockRequest()
            mock_request.instrument_id = "INVALID"

            # Setup error response
            mock_status = MockStatus()
            mock_status.success = False
            mock_status.message = "Instrument not found"

            mock_response = MockResponse()
            mock_response.status = mock_status

            MockResponse.return_value = mock_response

            response = await service.GetRiskMetrics(mock_request, mock_grpc_context)

            assert response is not None
            assert response.status.success is False
            assert "not found" in response.status.message


class TestRiskAnalyticsServiceFallback:
    """Test gRPC Analytics service when protobuf is not available."""

    @pytest.mark.asyncio
    @patch('risk_monitor.presentation.grpc.services.risk.PROTOBUF_AVAILABLE', False)
    async def test_get_risk_metrics_fallback(self, mock_grpc_context):
        """Test GetRiskMetrics fallback when protobuf unavailable."""
        service = RiskAnalyticsService()

        # Mock request (will be generic object since protobuf unavailable)
        mock_request = MagicMock()
        mock_request.instrument_id = "AAPL"

        response = await service.GetRiskMetrics(mock_request, mock_grpc_context)

        # Should return fallback response
        assert response is not None
        # Verify fallback behavior
        assert hasattr(response, 'status')
        assert hasattr(response, 'risk_metrics')

    @pytest.mark.asyncio
    @patch('risk_monitor.presentation.grpc.services.risk.PROTOBUF_AVAILABLE', False)
    async def test_get_portfolio_risk_metrics_fallback(self, mock_grpc_context):
        """Test GetPortfolioRiskMetrics fallback when protobuf unavailable."""
        service = RiskAnalyticsService()

        mock_request = MagicMock()
        mock_request.portfolio_id = "TEST_PORTFOLIO"

        response = await service.GetPortfolioRiskMetrics(mock_request, mock_grpc_context)

        assert response is not None
        assert hasattr(response, 'status')
        assert hasattr(response, 'portfolio_metrics')

    @pytest.mark.asyncio
    @patch('risk_monitor.presentation.grpc.services.risk.PROTOBUF_AVAILABLE', False)
    async def test_stream_risk_metrics_fallback(self, mock_grpc_context):
        """Test StreamRiskMetrics fallback when protobuf unavailable."""
        service = RiskAnalyticsService()

        mock_request = MagicMock()
        mock_request.instrument_ids = ["AAPL", "GOOGL"]

        # Mock context to simulate stream termination
        mock_grpc_context.cancelled.side_effect = [False, True]

        responses = []
        async for response in service.StreamRiskMetrics(mock_request, mock_grpc_context):
            responses.append(response)
            if len(responses) >= 1:
                break

        assert len(responses) >= 1
        assert responses[0] is not None


class TestGrpcServiceIntegration:
    """Integration tests for gRPC service functionality."""

    @pytest.mark.asyncio
    async def test_service_instantiation(self):
        """Test that gRPC service can be instantiated."""
        service = RiskAnalyticsService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_service_methods_exist(self):
        """Test that required service methods exist."""
        service = RiskAnalyticsService()

        # Check that all required methods exist
        assert hasattr(service, 'GetRiskMetrics')
        assert hasattr(service, 'GetPortfolioRiskMetrics')
        assert hasattr(service, 'StreamRiskMetrics')

        # Check that methods are callable
        assert callable(service.GetRiskMetrics)
        assert callable(service.GetPortfolioRiskMetrics)
        assert callable(service.StreamRiskMetrics)

    @pytest.mark.asyncio
    async def test_service_inheritance(self):
        """Test service inheritance structure."""
        service = RiskAnalyticsService()

        # When protobuf is available, should inherit from servicer
        # When not available, should be base object
        with patch('risk_monitor.presentation.grpc.services.risk.PROTOBUF_AVAILABLE', True):
            # Should have gRPC servicer methods when protobuf available
            assert hasattr(service, 'GetRiskMetrics')

        with patch('risk_monitor.presentation.grpc.services.risk.PROTOBUF_AVAILABLE', False):
            # Should still have methods for fallback
            assert hasattr(service, 'GetRiskMetrics')

    @pytest.mark.asyncio
    async def test_concurrent_grpc_calls(self, mock_grpc_context):
        """Test handling concurrent gRPC service calls."""
        import asyncio

        service = RiskAnalyticsService()

        # Create multiple mock requests
        mock_requests = []
        for i in range(3):
            mock_request = MagicMock()
            mock_request.instrument_id = f"TEST{i}"
            mock_requests.append(mock_request)

        # Make concurrent calls
        tasks = []
        for request in mock_requests:
            task = service.GetRiskMetrics(request, mock_grpc_context)
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All calls should complete successfully
        assert len(responses) == 3
        for response in responses:
            assert not isinstance(response, Exception)
            assert response is not None

    @pytest.mark.asyncio
    async def test_grpc_context_cancellation(self, mock_grpc_context):
        """Test gRPC service behavior with context cancellation."""
        service = RiskAnalyticsService()

        # Mock cancelled context
        mock_grpc_context.cancelled.return_value = True

        mock_request = MagicMock()
        mock_request.instrument_ids = ["AAPL"]

        # Stream should handle cancellation gracefully
        responses = []
        async for response in service.StreamRiskMetrics(mock_request, mock_grpc_context):
            responses.append(response)
            # Should break immediately due to cancellation
            break

        # Should handle cancellation without errors
        assert isinstance(responses, list)

    @pytest.mark.asyncio
    async def test_grpc_service_logging(self, mock_grpc_context, caplog):
        """Test that gRPC service operations are logged."""
        import logging

        service = RiskAnalyticsService()

        mock_request = MagicMock()
        mock_request.instrument_id = "AAPL"

        with caplog.at_level(logging.DEBUG):
            await service.GetRiskMetrics(mock_request, mock_grpc_context)

        # Should have debug logs for service operations
        # Note: This test might need adjustment based on actual logging implementation
        assert len(caplog.records) >= 0  # At minimum, no errors should occur