"""Health check endpoints for HTTP API."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from risk_monitor.infrastructure.config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    instance: str
    version: str
    environment: str
    timestamp: str


class ReadinessResponse(BaseModel):
    """Readiness check response model."""
    ready: bool
    checks: dict[str, bool]
    timestamp: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint with instance awareness."""
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        instance=settings.service_instance_name,
        version=settings.version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive"}


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """Kubernetes readiness probe endpoint with dependency checks."""
    settings = get_settings()

    # TODO: Implement actual dependency health checks
    checks = {
        "redis": True,  # await check_redis_health()
        "postgres": True,  # await check_postgres_health()
        "service_registry": True,  # await check_service_registry_health()
    }

    ready = all(checks.values())

    if not ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )

    return ReadinessResponse(
        ready=ready,
        checks=checks,
        timestamp=datetime.now(timezone.utc).isoformat()
    )