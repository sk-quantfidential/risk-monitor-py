"""Health check endpoints for HTTP API."""
import time

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from risk_monitor.infrastructure.config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    dependencies: dict[str, str]


class ReadinessResponse(BaseModel):
    """Readiness check response model."""
    ready: bool
    checks: dict[str, bool]
    timestamp: str


# Track service start time for uptime calculation
SERVICE_START_TIME = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        version=settings.version,
        uptime_seconds=round(time.time() - SERVICE_START_TIME, 2),
        dependencies={
            "redis": "unknown",
            "postgres": "unknown",
            "service_registry": "unknown"
        }
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
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )