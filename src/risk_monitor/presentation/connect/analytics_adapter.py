"""Connect protocol adapter for AnalyticsService.

Adapts the existing gRPC AnalyticsService to Connect protocol for browser clients.
"""
import structlog
from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext

try:
    from api.v1.analytics_service_pb2 import (
        CalculateAnalyticsRequest,
        CalculateAnalyticsResponse,
        GetCorrelationAnalysisRequest,
        GetCorrelationAnalysisResponse,
        GetPerformanceAttributionRequest,
        GetPerformanceAttributionResponse,
        GetPortfolioRiskMetricsRequest,
        GetPortfolioRiskMetricsResponse,
        GetRiskMetricsRequest,
        GetRiskMetricsResponse,
        RunStressTestsRequest,
        RunStressTestsResponse,
        GenerateReportRequest,
        GenerateReportResponse,
    )
    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False

from risk_monitor.presentation.grpc.services.risk import RiskAnalyticsService

logger = structlog.get_logger()


class AnalyticsConnectAdapter:
    """Connect protocol adapter wrapping gRPC RiskAnalyticsService.

    This adapter implements the Connect protocol interface and delegates
    to the existing gRPC service implementation.
    """

    def __init__(self, grpc_service: RiskAnalyticsService):
        """Initialize adapter with gRPC service.

        Args:
            grpc_service: The underlying gRPC RiskAnalyticsService implementation
        """
        self.grpc_service = grpc_service
        logger.info("AnalyticsConnectAdapter initialized")

    async def get_risk_metrics(
        self,
        request: "GetRiskMetricsRequest",
        ctx: RequestContext
    ) -> "GetRiskMetricsResponse":
        """Get risk metrics for an instrument via Connect protocol.

        Args:
            request: GetRiskMetricsRequest message
            ctx: Connect request context

        Returns:
            GetRiskMetricsResponse message

        Raises:
            ConnectError: If the gRPC service raises an exception
        """
        try:
            # Call underlying gRPC service (context not needed for unary calls)
            response = await self.grpc_service.GetRiskMetrics(request, None)
            return response
        except Exception as e:
            logger.error("get_risk_metrics failed", error=str(e))
            raise ConnectError(Code.INTERNAL, f"Internal error: {str(e)}")

    async def get_portfolio_risk_metrics(
        self,
        request: "GetPortfolioRiskMetricsRequest",
        ctx: RequestContext
    ) -> "GetPortfolioRiskMetricsResponse":
        """Get portfolio-level risk metrics via Connect protocol.

        Args:
            request: GetPortfolioRiskMetricsRequest message
            ctx: Connect request context

        Returns:
            GetPortfolioRiskMetricsResponse message

        Raises:
            ConnectError: If the gRPC service raises an exception
        """
        try:
            response = await self.grpc_service.GetPortfolioRiskMetrics(request, None)
            return response
        except Exception as e:
            logger.error("get_portfolio_risk_metrics failed", error=str(e))
            raise ConnectError(Code.INTERNAL, f"Internal error: {str(e)}")

    async def run_stress_tests(
        self,
        request: "RunStressTestsRequest",
        ctx: RequestContext
    ) -> "RunStressTestsResponse":
        """Run stress test scenarios via Connect protocol.

        Args:
            request: RunStressTestsRequest message
            ctx: Connect request context

        Returns:
            RunStressTestsResponse message

        Raises:
            ConnectError: If the gRPC service raises an exception
        """
        try:
            response = await self.grpc_service.RunStressTests(request, None)
            return response
        except Exception as e:
            logger.error("run_stress_tests failed", error=str(e))
            raise ConnectError(Code.INTERNAL, f"Internal error: {str(e)}")

    # Unimplemented RPCs - return NOT_IMPLEMENTED error

    async def calculate_analytics(
        self,
        request: "CalculateAnalyticsRequest",
        ctx: RequestContext
    ) -> "CalculateAnalyticsResponse":
        """Not implemented in risk-monitor-py."""
        raise ConnectError(Code.UNIMPLEMENTED, "CalculateAnalytics not implemented")

    async def get_performance_attribution(
        self,
        request: "GetPerformanceAttributionRequest",
        ctx: RequestContext
    ) -> "GetPerformanceAttributionResponse":
        """Not implemented in risk-monitor-py."""
        raise ConnectError(Code.UNIMPLEMENTED, "GetPerformanceAttribution not implemented")

    async def get_correlation_analysis(
        self,
        request: "GetCorrelationAnalysisRequest",
        ctx: RequestContext
    ) -> "GetCorrelationAnalysisResponse":
        """Not implemented in risk-monitor-py."""
        raise ConnectError(Code.UNIMPLEMENTED, "GetCorrelationAnalysis not implemented")

    async def generate_report(
        self,
        request: "GenerateReportRequest",
        ctx: RequestContext
    ) -> "GenerateReportResponse":
        """Not implemented in risk-monitor-py."""
        raise ConnectError(Code.UNIMPLEMENTED, "GenerateReport not implemented")
