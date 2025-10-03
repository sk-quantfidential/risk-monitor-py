"""Core risk monitoring business logic."""
from datetime import datetime, UTC
from decimal import Decimal
from typing import Any, Optional

from risk_data_adapter import RiskDataAdapter
from risk_data_adapter.models import (
    AlertSeverity,
    AlertStatus,
    LimitType,
    RiskAlert,
    RiskLimit,
    RiskMetric,
)

from risk_monitor.infrastructure.logging import get_logger

logger = get_logger()


class RiskMonitorService:
    """Core risk monitoring service."""

    def __init__(self, data_adapter: Optional[RiskDataAdapter] = None) -> None:
        """Initialize risk monitoring service."""
        self.data_adapter = data_adapter
        self.position_limits: dict[str, float] = {}
        self.pnl_thresholds: dict[str, float] = {}

    async def calculate_pnl(self, account: str, asset: str) -> float:
        """Calculate P&L for account and asset."""
        logger.info("Calculating P&L", account=account, asset=asset)
        # TODO: Implement actual P&L calculation
        return 0.0

    async def check_position_limits(self, account: str, asset: str, position: float) -> bool:
        """Check if position exceeds limits."""
        logger.info("Checking position limits",
                   account=account, asset=asset, position=position)
        # TODO: Implement actual position limit checks
        return True

    async def generate_alert(self, alert_type: str, message: str, metadata: dict[str, Any]) -> str:
        """Generate risk alert."""
        logger.warning("Risk alert generated",
                      alert_type=alert_type, message=message, metadata=metadata)

        if self.data_adapter:
            # Create alert using data adapter
            alert = RiskAlert(
                alert_id=f"alert-{alert_type}-{datetime.now(UTC).timestamp()}",
                severity=AlertSeverity.HIGH,
                status=AlertStatus.ACTIVE,
                metric_name=alert_type,
                message=message,
                current_value=Decimal(str(metadata.get("current_value", 0))),
                threshold_value=Decimal(str(metadata.get("threshold", 0))),
                triggered_at=datetime.now(UTC)
            )

            try:
                repo = self.data_adapter.get_risk_alerts_repository()
                await repo.create(alert)
                logger.info("Alert persisted", alert_id=alert.alert_id)
                return alert.alert_id
            except Exception as e:
                logger.error("Failed to persist alert", error=str(e))

        return f"alert-{alert_type}-001"