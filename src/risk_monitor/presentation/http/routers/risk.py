"""Risk monitoring HTTP endpoints."""
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter()


class RiskMetrics(BaseModel):
    """Risk metrics model."""
    portfolio_value: float = Field(..., description="Total portfolio value in USD")
    unrealized_pnl: float = Field(..., description="Unrealized P&L in USD")
    realized_pnl: float = Field(..., description="Realized P&L in USD")
    total_exposure: float = Field(..., description="Total exposure in USD")
    leverage_ratio: float = Field(..., description="Current leverage ratio")
    var_95: float = Field(..., description="Value at Risk (95% confidence)")
    timestamp: datetime = Field(..., description="Metrics timestamp")


class RiskAlert(BaseModel):
    """Risk alert model."""
    alert_id: str
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: datetime


class RiskLimits(BaseModel):
    """Risk limits configuration."""
    max_position_size: float = Field(..., gt=0)
    max_leverage: float = Field(..., gt=0)
    var_limit: float = Field(..., gt=0)
    daily_loss_limit: float = Field(..., gt=0)


@router.get("/risk/metrics")
async def get_risk_metrics(
    instrument_id: str = Query(..., description="Instrument ID to get risk metrics for"),
    lookback_days: int = Query(30, ge=1, le=365, description="Historical lookback period"),
    confidence_level: float = Query(0.95, ge=0.5, le=0.99, description="VaR confidence level")
):
    """Get risk metrics for a specific instrument."""
    try:
        # Import protobuf services if available
        from risk_monitor.presentation.shared.converters import (
            PROTOBUF_AVAILABLE,
            create_risk_metrics_request,
            protobuf_to_risk_metrics_model,
        )

        if not PROTOBUF_AVAILABLE:
            # Fallback to mock data
            return RiskMetrics(
                portfolio_value=1000000.0,
                unrealized_pnl=5000.0,
                realized_pnl=2500.0,
                total_exposure=950000.0,
                leverage_ratio=2.1,
                var_95=25000.0,
                timestamp=datetime.now()
            )

        # Create and execute gRPC request internally
        from risk_monitor.presentation.grpc.services.risk import RiskAnalyticsService

        analytics_service = RiskAnalyticsService()
        request = create_risk_metrics_request(
            instrument_id=instrument_id,
            calculation_params={
                "lookback_days": lookback_days,
                "confidence_level": confidence_level
            }
        )

        # Mock context for internal call
        class MockContext:
            def cancelled(self):
                return False

        response = await analytics_service.GetRiskMetrics(request, MockContext())

        if response.status.success:
            # Convert protobuf response to HTTP model
            risk_model = protobuf_to_risk_metrics_model(response.risk_metrics)
            return risk_model
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.status.message
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get risk metrics: {str(e)}"
        )


@router.get("/risk/alerts", response_model=list[RiskAlert])
async def get_risk_alerts(
    severity: str | None = Query(None, pattern="^(low|medium|high|critical)$"),
    limit: int = Query(10, ge=1, le=100)
) -> list[RiskAlert]:
    """Get active risk alerts."""
    # TODO: Implement actual alert retrieval logic
    alerts = [
        RiskAlert(
            alert_id="alert_001",
            severity="high",
            message="Position size exceeds limit",
            metric_name="position_size",
            current_value=1200000.0,
            threshold_value=1000000.0,
            timestamp=datetime.now()
        )
    ]

    if severity:
        alerts = [alert for alert in alerts if alert.severity == severity]

    return alerts[:limit]


@router.get("/risk/limits", response_model=RiskLimits)
async def get_risk_limits() -> RiskLimits:
    """Get current risk limits configuration."""
    # TODO: Load from configuration or database
    return RiskLimits(
        max_position_size=1000000.0,
        max_leverage=3.0,
        var_limit=50000.0,
        daily_loss_limit=100000.0
    )


@router.put("/risk/limits", response_model=RiskLimits)
async def update_risk_limits(limits: RiskLimits) -> RiskLimits:
    """Update risk limits configuration."""
    # TODO: Implement actual limits update logic with validation
    return limits


@router.post("/risk/calculate")
async def calculate_risk(portfolio_positions: list[dict]) -> RiskMetrics:
    """Calculate risk metrics for given portfolio positions."""
    # TODO: Implement actual risk calculation engine
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Risk calculation engine not yet implemented"
    )