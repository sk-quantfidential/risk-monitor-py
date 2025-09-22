"""Converters between HTTP models and protobuf messages."""
from datetime import datetime
from typing import Any

from google.protobuf.timestamp_pb2 import Timestamp
from pydantic import BaseModel

# Import protobuf types with fallback
try:
    from api.v1.analytics_service_pb2 import (
        GetRiskMetricsRequest,
        RiskCalculationParams,
    )
    from market.v1.risk_metrics_pb2 import PortfolioRiskMetrics, RiskMetrics
    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False


class RiskMetricsModel(BaseModel):
    """HTTP API model for risk metrics."""
    id: str
    instrument_id: str
    calculation_date: datetime
    calculation_method: str
    volatility: dict[str, float] | None = None
    var_metrics: dict[str, float] | None = None
    performance: dict[str, float] | None = None
    liquidity: dict[str, float] | None = None


class PortfolioRiskMetricsModel(BaseModel):
    """HTTP API model for portfolio risk metrics."""
    id: str
    portfolio_id: str
    total_value: float | None = None
    calculation_date: datetime
    concentration: dict[str, float] | None = None
    portfolio_var: dict[str, float] | None = None


def timestamp_to_datetime(timestamp: Timestamp) -> datetime:
    """Convert protobuf Timestamp to Python datetime."""
    return datetime.fromtimestamp(timestamp.seconds + timestamp.nanos / 1e9)


def datetime_to_timestamp(dt: datetime) -> Timestamp:
    """Convert Python datetime to protobuf Timestamp."""
    timestamp = Timestamp()
    timestamp.FromDatetime(dt)
    return timestamp


def protobuf_to_risk_metrics_model(proto_metrics: 'RiskMetrics') -> RiskMetricsModel:
    """Convert protobuf RiskMetrics to HTTP model."""
    if not PROTOBUF_AVAILABLE:
        raise RuntimeError("Protobuf schemas not available")

    return RiskMetricsModel(
        id=proto_metrics.id,
        instrument_id=proto_metrics.instrument_id,
        calculation_date=timestamp_to_datetime(proto_metrics.calculation_date),
        calculation_method=proto_metrics.calculation_method,
        # TODO: Convert nested protobuf structures to dictionaries
        volatility={} if not proto_metrics.HasField("volatility") else {},
        var_metrics={} if not proto_metrics.HasField("var") else {},
        performance={} if not proto_metrics.HasField("performance") else {},
        liquidity={} if not proto_metrics.HasField("liquidity") else {}
    )


def protobuf_to_portfolio_risk_model(proto_metrics: 'PortfolioRiskMetrics') -> PortfolioRiskMetricsModel:
    """Convert protobuf PortfolioRiskMetrics to HTTP model."""
    if not PROTOBUF_AVAILABLE:
        raise RuntimeError("Protobuf schemas not available")

    return PortfolioRiskMetricsModel(
        id=proto_metrics.id,
        portfolio_id=proto_metrics.portfolio_id,
        calculation_date=timestamp_to_datetime(proto_metrics.calculation_date),
        # TODO: Convert nested protobuf structures
        total_value=None,
        concentration={},
        portfolio_var={}
    )


def create_risk_metrics_request(
    instrument_id: str,
    calculation_params: dict[str, Any] | None = None
) -> 'GetRiskMetricsRequest':
    """Create protobuf GetRiskMetricsRequest from HTTP parameters."""
    if not PROTOBUF_AVAILABLE:
        raise RuntimeError("Protobuf schemas not available")

    request = GetRiskMetricsRequest()
    request.instrument_id = instrument_id
    request.date.FromDatetime(datetime.now())

    if calculation_params:
        params = RiskCalculationParams()
        if "lookback_days" in calculation_params:
            params.lookback_days = calculation_params["lookback_days"]
        if "confidence_level" in calculation_params:
            params.confidence_level = calculation_params["confidence_level"]
        if "benchmark_id" in calculation_params:
            params.benchmark_id = calculation_params["benchmark_id"]

        request.params.CopyFrom(params)

    return request