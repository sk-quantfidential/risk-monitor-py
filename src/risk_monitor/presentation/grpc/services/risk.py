"""gRPC risk monitoring service implementation using AnalyticsService."""
import asyncio
from typing import AsyncGenerator
from datetime import datetime, timezone

import structlog
from grpc import aio
from google.protobuf.timestamp_pb2 import Timestamp

# Import protobuf generated classes
try:
    from api.v1.analytics_service_pb2_grpc import AnalyticsServiceServicer
    from api.v1.analytics_service_pb2 import (
        GetRiskMetricsRequest, GetRiskMetricsResponse,
        GetPortfolioRiskMetricsRequest, GetPortfolioRiskMetricsResponse,
        RunStressTestsRequest, RunStressTestsResponse,
        RiskMetricType, RiskCalculationParams
    )
    from api.v1.common_responses_pb2 import ResponseStatus
    from market.v1.risk_metrics_pb2 import RiskMetrics, PortfolioRiskMetrics
    PROTOBUF_AVAILABLE = True
except ImportError:
    # Fallback for when protobuf schemas are not available
    AnalyticsServiceServicer = object
    PROTOBUF_AVAILABLE = False

from risk_monitor.presentation.shared.middleware import RequestTracker

logger = structlog.get_logger()


class RiskAnalyticsService(AnalyticsServiceServicer if PROTOBUF_AVAILABLE else object):
    """gRPC Analytics service implementation focused on risk monitoring."""

    async def GetRiskMetrics(self, request, context):
        """Get risk metrics for an instrument."""
        tracker = RequestTracker(
            protocol="grpc",
            method="GetRiskMetrics",
            endpoint="/api.v1.AnalyticsService/GetRiskMetrics"
        )

        try:
            logger.debug("Risk metrics requested", instrument_id=request.instrument_id)

            # Create mock risk metrics (TODO: Replace with actual calculation)
            risk_metrics = RiskMetrics(
                id=f"risk_{request.instrument_id}_{int(datetime.now().timestamp())}",
                instrument_id=request.instrument_id,
                calculation_date=Timestamp(seconds=int(datetime.now(timezone.utc).timestamp())),
                calculation_method="Historical Simulation"
            )

            response = GetRiskMetricsResponse(
                risk_metrics=risk_metrics,
                status=ResponseStatus(
                    code=0,
                    message="Success",
                    success=True
                )
            )

            tracker.track_completion("ok")
            return response

        except Exception as e:
            logger.error("Risk metrics request failed", error=str(e))
            tracker.track_completion("error")

            return GetRiskMetricsResponse(
                status=ResponseStatus(
                    code=500,
                    message=f"Internal error: {str(e)}",
                    success=False
                )
            )

    async def GetPortfolioRiskMetrics(self, request, context):
        """Get portfolio risk metrics."""
        tracker = RequestTracker(
            protocol="grpc",
            method="GetPortfolioRiskMetrics",
            endpoint="/api.v1.AnalyticsService/GetPortfolioRiskMetrics"
        )

        try:
            logger.debug("Portfolio risk metrics requested", portfolio_id=request.portfolio_id)

            # Create mock portfolio risk metrics (TODO: Replace with actual calculation)
            portfolio_metrics = PortfolioRiskMetrics(
                id=f"portfolio_risk_{request.portfolio_id}_{int(datetime.now().timestamp())}",
                portfolio_id=request.portfolio_id,
                calculation_date=Timestamp(seconds=int(datetime.now(timezone.utc).timestamp()))
            )

            response = GetPortfolioRiskMetricsResponse(
                portfolio_metrics=portfolio_metrics,
                status=ResponseStatus(
                    code=0,
                    message="Success",
                    success=True
                )
            )

            tracker.track_completion("ok")
            return response

        except Exception as e:
            logger.error("Portfolio risk metrics request failed", error=str(e))
            tracker.track_completion("error")

            return GetPortfolioRiskMetricsResponse(
                status=ResponseStatus(
                    code=500,
                    message=f"Internal error: {str(e)}",
                    success=False
                )
            )

    async def RunStressTests(self, request, context):
        """Run stress tests on portfolio or instrument."""
        tracker = RequestTracker(
            protocol="grpc",
            method="RunStressTests",
            endpoint="/api.v1.AnalyticsService/RunStressTests"
        )

        try:
            target = "portfolio" if request.HasField("portfolio_id") else "instrument"
            target_id = request.portfolio_id if request.HasField("portfolio_id") else request.instrument_id

            logger.debug("Stress tests requested", target=target, target_id=target_id)

            # TODO: Implement actual stress testing logic
            # For now, return empty results
            from market.v1.risk_metrics_pb2 import StressTestResults

            results = StressTestResults()

            response = RunStressTestsResponse(
                results=results,
                status=ResponseStatus(
                    code=0,
                    message="Stress tests completed",
                    success=True
                )
            )

            tracker.track_completion("ok")
            return response

        except Exception as e:
            logger.error("Stress tests failed", error=str(e))
            tracker.track_completion("error")

            return RunStressTestsResponse(
                status=ResponseStatus(
                    code=500,
                    message=f"Internal error: {str(e)}",
                    success=False
                )
            )

    async def StreamRiskMetrics(self, request, context):
        """Stream real-time risk metrics."""
        if not PROTOBUF_AVAILABLE:
            # Create mock response when protobuf unavailable
            mock_response = type('MockResponse', (), {})()
            yield mock_response
            return

        try:
            logger.debug("Risk metrics stream requested",
                        instrument_ids=getattr(request, 'instrument_ids', []))

            # Simulate streaming risk metrics
            while not context.cancelled():
                # Create mock streaming response
                risk_metrics = RiskMetrics(
                    id=f"stream_risk_{int(datetime.now().timestamp())}",
                    instrument_id="STREAM",
                    calculation_date=Timestamp(seconds=int(datetime.now(timezone.utc).timestamp()))
                )

                response = GetRiskMetricsResponse(
                    risk_metrics=risk_metrics,
                    status=ResponseStatus(
                        code=0,
                        message="Streaming risk metrics",
                        success=True
                    )
                )

                yield response
                await asyncio.sleep(5)  # Update every 5 seconds

        except Exception as e:
            logger.error("Error in streaming risk metrics", error=str(e))
            yield GetRiskMetricsResponse(
                status=ResponseStatus(
                    code=500,
                    message=f"Streaming error: {str(e)}",
                    success=False
                )
            )