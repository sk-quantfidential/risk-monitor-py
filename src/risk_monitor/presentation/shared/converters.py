"""Converters between HTTP models and protobuf messages."""
from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel
from google.protobuf.timestamp_pb2 import Timestamp

# Import protobuf types with fallback
try:
    from market.v1.risk_metrics_pb2 import RiskMetrics, PortfolioRiskMetrics
    from api.v1.analytics_service_pb2 import GetRiskMetricsRequest, RiskCalculationParams
    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False


class RiskMetricsModel(BaseModel):
    """HTTP API model for risk metrics."""
    id: str
    instrument_id: str
    calculation_date: datetime
    calculation_method: str
    volatility: Optional[Dict[str, float]] = None
    var_metrics: Optional[Dict[str, float]] = None
    performance: Optional[Dict[str, float]] = None
    liquidity: Optional[Dict[str, float]] = None


class PortfolioRiskMetricsModel(BaseModel):
    """HTTP API model for portfolio risk metrics."""
    id: str
    portfolio_id: str
    total_value: Optional[float] = None
    calculation_date: datetime
    concentration: Optional[Dict[str, float]] = None
    portfolio_var: Optional[Dict[str, float]] = None


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
    calculation_params: Optional[Dict[str, Any]] = None
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