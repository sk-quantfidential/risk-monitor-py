"""Configuration management for Risk Monitor service."""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    version: str = "0.1.0"
    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = False

    # Server settings
    host: str = "0.0.0.0"
    http_port: int = Field(default=8084, gt=0, le=65535)  # Risk Monitor HTTP port
    grpc_port: int = Field(default=50054, gt=0, le=65535)  # Risk Monitor gRPC port

    # Logging settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # External services
    redis_url: str = "redis://localhost:6379"
    postgres_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/trading_ecosystem"
    service_registry_url: str = "http://localhost:8080"

    # Service discovery settings
    service_name: str = "risk-monitor"
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


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()