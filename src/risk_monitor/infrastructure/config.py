"""Configuration management for Risk Monitor service."""
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service Identity (NEW for multi-instance support)
    service_name: str = Field(default="risk-monitor", description="Service name")
    service_instance_name: str = Field(default="", description="Instance identifier (defaults to service_name)")

    # Application settings
    version: str = "0.1.0"
    environment: Literal["development", "testing", "production", "docker"] = "development"
    debug: bool = False

    # Server settings
    host: str = "0.0.0.0"
    http_port: int = Field(default=8080, gt=0, le=65535)  # Standard HTTP port (docker-compose maps to external)
    grpc_port: int = Field(default=50051, gt=0, le=65535)  # Standard gRPC port (docker-compose maps to external)

    # Logging settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # External services
    redis_url: str = "redis://localhost:6379"
    postgres_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/trading_ecosystem"
    service_registry_url: str = "http://localhost:8080"

    # Service discovery settings
    service_version: str = "0.1.0"
    health_check_interval: int = 30  # seconds
    registration_retry_interval: int = 5  # seconds

    # OpenTelemetry settings
    otel_service_name: str = "risk-monitor"
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_insecure: bool = True

    # Performance settings
    worker_pool_size: int = 10
    max_concurrent_requests: int = 100
    request_timeout: float = 30.0

    # Risk monitoring settings
    position_limit_threshold: float = 1000000.0  # $1M default
    pnl_threshold: float = 50000.0  # $50K default
    alert_cooldown_seconds: int = 300  # 5 minutes

    @field_validator('log_level', mode='before')
    @classmethod
    def normalize_log_level(cls, v: Any) -> str:
        """Normalize log level to uppercase for Literal validation."""
        if isinstance(v, str):
            return v.upper()
        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization hook for backward compatibility defaults."""
        # Backward compatibility: Default service_instance_name to service_name (singleton pattern)
        if not self.service_instance_name:
            self.service_instance_name = self.service_name


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()