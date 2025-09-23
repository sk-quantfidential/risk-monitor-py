"""Configuration service client for fetching centralized configuration."""
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from risk_monitor.infrastructure.config import Settings
from risk_monitor.infrastructure.service_discovery import ServiceDiscovery, ServiceInfo

logger = structlog.get_logger()

# Constants
DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes
DEFAULT_CONFIG_SERVICE_PORT = 8090
DEFAULT_CONFIG_SERVICE_HOST = "localhost"
VALID_CONFIG_TYPES = {"string", "number", "boolean", "json"}
CONFIG_KEY_PATTERN_REGEX = r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$"


class ConfigurationError(Exception):
    """Configuration service related errors."""
    pass


@dataclass
class ConfigurationValue:
    """Configuration value with metadata."""
    key: str
    value: str
    type: str = "string"
    environment: Optional[str] = None
    last_updated: Optional[str] = None
    version: Optional[str] = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def validate(self) -> bool:
        """Validate configuration value structure."""
        import re

        if not self.key or not isinstance(self.key, str):
            return False

        # Use regex pattern for more robust key validation
        if not re.match(CONFIG_KEY_PATTERN_REGEX, self.key):
            return False

        if not self.value:
            return False

        if self.type not in VALID_CONFIG_TYPES:
            return False

        return True

    def as_str(self) -> str:
        """Get value as string."""
        return str(self.value)

    def as_int(self) -> int:
        """Get value as integer."""
        if self.type == "number":
            return int(float(self.value))
        raise ValueError(f"Cannot convert {self.type} to int")

    def as_float(self) -> float:
        """Get value as float."""
        if self.type == "number":
            return float(self.value)
        raise ValueError(f"Cannot convert {self.type} to float")

    def as_bool(self) -> bool:
        """Get value as boolean."""
        if self.type == "boolean":
            return self.value.lower() in ("true", "1", "yes", "on")
        raise ValueError(f"Cannot convert {self.type} to bool")

    def as_json(self) -> Dict[str, Any]:
        """Get value as JSON object."""
        if self.type == "json":
            return json.loads(self.value)
        raise ValueError(f"Cannot convert {self.type} to JSON")


class ConfigurationServiceClient:
    """Client for centralized configuration service."""

    def __init__(self, settings: Settings, service_discovery: Optional[ServiceDiscovery] = None):
        self.settings = settings
        self.service_discovery = service_discovery
        self._http_client: Optional[httpx.AsyncClient] = None
        self._config_service_info: Optional[ServiceInfo] = None
        self._cache: Dict[str, ConfigurationValue] = {}
        self._cache_ttl: Dict[str, float] = {}
        self._connected = False
        self._subscribers: Dict[str, List[Callable]] = {}
        self.cache_hits = 0
        self._cache_misses = 0
        self._default_cache_ttl = DEFAULT_CACHE_TTL_SECONDS

    async def connect(self) -> None:
        """Connect to configuration service."""
        try:
            # Find configuration service via service discovery
            if self.service_discovery:
                self._config_service_info = await self.service_discovery.get_service("configuration-service")
                if not self._config_service_info:
                    raise ConfigurationError("Configuration service not found in service discovery")
            else:
                # Fallback to default configuration service endpoint
                self._config_service_info = ServiceInfo(
                    name="configuration-service",
                    version="1.0.0",
                    host=getattr(self.settings, 'config_service_host', DEFAULT_CONFIG_SERVICE_HOST),
                    http_port=getattr(self.settings, 'config_service_port', DEFAULT_CONFIG_SERVICE_PORT),
                    grpc_port=50090,
                    status="healthy"
                )

            # Create HTTP client
            base_url = f"http://{self._config_service_info.host}:{self._config_service_info.http_port}"
            self._http_client = httpx.AsyncClient(
                base_url=base_url,
                timeout=httpx.Timeout(10.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )

            # Test connection
            try:
                response = await self._http_client.get("/health")
                if not response.is_success:
                    raise ConfigurationError(f"Configuration service health check failed: {response.status_code}")
            except httpx.ConnectError as e:
                raise ConfigurationError(f"Cannot connect to configuration service: {e}")

            self._connected = True
            logger.info("Configuration service client connected",
                       endpoint=base_url)

        except Exception as e:
            logger.error("Failed to connect to configuration service", error=str(e))
            raise ConfigurationError(f"Connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from configuration service."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        self._connected = False
        self._cache.clear()
        self._cache_ttl.clear()
        self._subscribers.clear()

        logger.info("Configuration service client disconnected")

    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    def _validate_key(self, key: str) -> None:
        """Validate configuration key format and raise detailed error if invalid."""
        import re

        if not key or not isinstance(key, str):
            raise ConfigurationError("Configuration key must be a non-empty string")

        if not re.match(CONFIG_KEY_PATTERN_REGEX, key):
            raise ConfigurationError(
                f"Invalid configuration key format: '{key}'. "
                "Keys must start with a letter and contain only letters, numbers, "
                "underscores, and dots for hierarchy (e.g., 'app.database.timeout')"
            )

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.cache_hits + self._cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cached_keys": len(self._cache),
            "cache_size_bytes": sum(len(str(v.value)) for v in self._cache.values())
        }

    async def get_configuration(self, key: str, environment: Optional[str] = None) -> ConfigurationValue:
        """Get a single configuration value."""
        if not self._connected:
            raise ConfigurationError("Client not connected")

        # Validate key format with detailed error messages
        self._validate_key(key)

        # Check cache first
        cache_key = f"{key}:{environment or self.settings.environment}"
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            self.cache_hits += 1
            logger.debug("Configuration cache hit", key=key, environment=environment)
            return self._cache[cache_key]

        # Record cache miss
        self._cache_misses += 1

        try:
            # Fetch from service
            params = {"key": key}
            if environment:
                params["environment"] = environment

            response = await self._http_client.get("/api/v1/configuration", params=params)

            if response.status_code == 404:
                raise ConfigurationError(f"Configuration key not found: {key}")
            elif response.status_code == 500:
                raise ConfigurationError("Configuration service error")
            elif not response.is_success:
                raise ConfigurationError(f"Configuration service error: {response.status_code}")

            try:
                data = response.json()
            except json.JSONDecodeError:
                raise ConfigurationError("Invalid response format")

            # Validate response format
            required_fields = ["key", "value", "type"]
            if not all(field in data for field in required_fields):
                raise ConfigurationError("Invalid response format")

            config_value = ConfigurationValue(
                key=data["key"],
                value=data["value"],
                type=data["type"],
                environment=data.get("environment"),
                last_updated=data.get("last_updated"),
                version=data.get("version")
            )

            # Cache the result
            self._cache[cache_key] = config_value
            self._cache_ttl[cache_key] = time.time() + self._default_cache_ttl

            return config_value

        except httpx.TimeoutException:
            raise ConfigurationError("Configuration service timeout")
        except httpx.ConnectError:
            raise ConfigurationError("Configuration service connection error")

    async def get_configurations(self, keys: List[str], environment: Optional[str] = None) -> List[ConfigurationValue]:
        """Get multiple configuration values."""
        if not self._connected:
            raise ConfigurationError("Client not connected")

        # For MVP, implement as individual calls
        # TODO: Optimize with batch API call
        results = []
        for key in keys:
            try:
                config_value = await self.get_configuration(key, environment)
                results.append(config_value)
            except ConfigurationError:
                # Skip missing keys in batch operations
                continue

        return results

    async def subscribe_to_updates(self, pattern: str, callback: Callable[[str, ConfigurationValue], None]) -> None:
        """Subscribe to configuration updates matching a pattern."""
        if pattern not in self._subscribers:
            self._subscribers[pattern] = []
        self._subscribers[pattern].append(callback)

        logger.info("Subscribed to configuration updates", pattern=pattern)

    async def trigger_update_notification(self, key: str) -> None:
        """Trigger update notification for testing purposes."""
        # Invalidate cache
        cache_keys_to_remove = [cache_key for cache_key in self._cache.keys() if cache_key.startswith(f"{key}:")]
        for cache_key in cache_keys_to_remove:
            del self._cache[cache_key]
            del self._cache_ttl[cache_key]

        # Fetch new value
        try:
            new_value = await self.get_configuration(key)

            # Notify subscribers
            for pattern, callbacks in self._subscribers.items():
                if self._matches_pattern(key, pattern):
                    for callback in callbacks:
                        try:
                            callback(key, new_value)
                        except Exception as e:
                            logger.error("Configuration update callback failed", error=str(e))

        except ConfigurationError as e:
            logger.warning("Failed to fetch updated configuration", key=key, error=str(e))

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached value is still valid."""
        if cache_key not in self._cache_ttl:
            return False
        return time.time() < self._cache_ttl[cache_key]

    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches subscription pattern."""
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return key.startswith(prefix)
        return key == pattern