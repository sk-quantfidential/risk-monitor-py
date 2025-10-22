"""Health check endpoints for Risk Monitor service."""

from datetime import datetime, timezone

from fastapi import APIRouter, status
from pydantic import BaseModel

from risk_monitor.infrastructure.config import get_settings
from risk_monitor.infrastructure.logging import get_logger

router = APIRouter()
logger = get_logger()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    instance: str  # NEW: Instance identifier
    version: str
    environment: str  # NEW: Deployment environment
    timestamp: str  # NEW: ISO8601 timestamp


class ReadinessResponse(BaseModel):
    """Readiness check response model."""
    status: str
    checks: dict[str, str]


@router.get("/health", status_code=status.HTTP_200_OK, response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint with instance awareness."""
    settings = get_settings()

    logger.info("Health check requested")

    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        instance=settings.service_instance_name,  # NEW
        version=settings.version,
        environment=settings.environment,  # NEW
        timestamp=datetime.now(timezone.utc).isoformat(),  # NEW
    )


@router.get("/ready", status_code=status.HTTP_200_OK, response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """Readiness check with dependency validation."""
    logger.info("Readiness check requested")

    # TODO: Add actual dependency checks (Redis, external APIs, etc.)
    checks = {
        "redis": "ok",
        "external_apis": "ok",
    }

    return ReadinessResponse(
        status="ready",
        checks=checks,
    )