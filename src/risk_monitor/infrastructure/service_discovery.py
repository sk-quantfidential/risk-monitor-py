"""Service discovery using Redis backend."""
import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

import httpx
import redis.asyncio as redis
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from risk_monitor.infrastructure.config import Settings

logger = structlog.get_logger()


@dataclass
class ServiceInfo:
    """Service registration information."""
    name: str
    version: str
    host: str
    http_port: int
    grpc_port: int
    status: str = "healthy"
    metadata: Optional[Dict[str, Any]] = None
    registered_at: float = 0.0
    last_heartbeat: float = 0.0

    def __post_init__(self):
        if self.registered_at == 0.0:
            self.registered_at = time.time()
        if self.last_heartbeat == 0.0:
            self.last_heartbeat = time.time()

    @property
    def redis_key(self) -> str:
        """Generate Redis key for service registration."""
        return f"registry:services:{self.name}"

    @property
    def http_url(self) -> str:
        """Generate HTTP base URL for service."""
        return f"http://{self.host}:{self.http_port}"

    @property
    def grpc_address(self) -> str:
        """Generate gRPC address for service."""
        return f"{self.host}:{self.grpc_port}"


class ServiceDiscovery:
    """Redis-based service discovery client."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.service_info: Optional[ServiceInfo] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.registration_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Connect to Redis and HTTP clients."""
        try:
            self.redis_client = redis.from_url(
                self.settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={},
            )

            # Test connection
            await self.redis_client.ping()

            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )

            logger.info("Service discovery connected",
                        redis_url=self.settings.redis_url)

        except Exception as e:
            logger.error("Failed to connect to service discovery", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect and cleanup resources."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()

        if self.registration_task:
            self.registration_task.cancel()

        if self.service_info:
            await self.deregister_service()

        if self.redis_client:
            await self.redis_client.aclose()

        if self.http_client:
            await self.http_client.aclose()

        logger.info("Service discovery disconnected")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def register_service(self) -> None:
        """Register this service in Redis."""
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")

        self.service_info = ServiceInfo(
            name=self.settings.service_name,
            version=self.settings.service_version,
            host=self.settings.host,
            http_port=self.settings.http_port,
            grpc_port=self.settings.grpc_port,
            metadata={
                "environment": self.settings.environment,
                "capabilities": ["http", "grpc", "metrics", "health"],
                "protocols": {
                    "http": f"http://{self.settings.host}:{self.settings.http_port}",
                    "grpc": f"{self.settings.host}:{self.settings.grpc_port}"
                }
            }
        )

        # Register in Redis
        service_data = asdict(self.service_info)
        await self.redis_client.hset(
            self.service_info.redis_key,
            mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                     for k, v in service_data.items()}
        )

        # Set TTL
        await self.redis_client.expire(
            self.service_info.redis_key,
            self.settings.health_check_interval * 3
        )

        # Register with central service registry
        await self._register_with_central_registry()

        # Start heartbeat
        if not self.heartbeat_task or self.heartbeat_task.done():
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info("Service registered",
                    service=self.settings.service_name,
                    http_port=self.settings.http_port,
                    grpc_port=self.settings.grpc_port)

    async def _register_with_central_registry(self) -> None:
        """Register with central service registry HTTP API."""
        if not self.service_info or not self.http_client:
            return

        try:
            registration_data = {
                "name": self.service_info.name,
                "version": self.service_info.version,
                "endpoints": {
                    "http": self.service_info.http_url,
                    "grpc": self.service_info.grpc_address,
                    "health": f"{self.service_info.http_url}/api/v1/health",
                    "metrics": f"{self.service_info.http_url}/metrics"
                },
                "metadata": self.service_info.metadata
            }

            response = await self.http_client.post(
                f"{self.settings.service_registry_url}/api/v1/services",
                json=registration_data,
                timeout=5.0
            )

            if response.is_success:
                logger.info("Registered with central service registry")
            else:
                logger.warning("Failed to register with central service registry",
                               status_code=response.status_code)

        except Exception as e:
            logger.warning("Central service registry unavailable",
                           error=str(e))

    async def deregister_service(self) -> None:
        """Deregister this service from Redis."""
        if not self.redis_client or not self.service_info:
            return

        try:
            await self.redis_client.delete(self.service_info.redis_key)
            logger.info("Service deregistered", service=self.settings.service_name)
        except Exception as e:
            logger.error("Failed to deregister service", error=str(e))

    async def discover_services(self, service_name: Optional[str] = None) -> List[ServiceInfo]:
        """Discover services from Redis."""
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")

        pattern = f"registry:services:{service_name}" if service_name else "registry:services:*"

        try:
            keys = await self.redis_client.keys(pattern)
            services = []

            for key in keys:
                service_data = await self.redis_client.hgetall(key)
                if service_data:
                    # Parse JSON fields
                    for field in ["metadata"]:
                        if field in service_data:
                            try:
                                service_data[field] = json.loads(service_data[field])
                            except json.JSONDecodeError:
                                service_data[field] = {}

                    # Convert numeric fields
                    for field in ["http_port", "grpc_port", "registered_at", "last_heartbeat"]:
                        if field in service_data:
                            try:
                                service_data[field] = float(service_data[field])
                            except ValueError:
                                service_data[field] = 0.0

                    services.append(ServiceInfo(**service_data))

            return services

        except Exception as e:
            logger.error("Failed to discover services", error=str(e))
            return []

    async def get_service(self, service_name: str) -> Optional[ServiceInfo]:
        """Get specific service information."""
        services = await self.discover_services(service_name)
        return services[0] if services else None

    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat to maintain service registration."""
        while True:
            try:
                await asyncio.sleep(self.settings.health_check_interval)

                if self.service_info and self.redis_client:
                    self.service_info.last_heartbeat = time.time()

                    # Update heartbeat timestamp
                    await self.redis_client.hset(
                        self.service_info.redis_key,
                        "last_heartbeat",
                        str(self.service_info.last_heartbeat)
                    )

                    # Refresh TTL
                    await self.redis_client.expire(
                        self.service_info.redis_key,
                        self.settings.health_check_interval * 3
                    )

                    logger.debug("Service heartbeat sent")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat failed", error=str(e))
                # Try to re-register after failure
                try:
                    await asyncio.sleep(self.settings.registration_retry_interval)
                    await self.register_service()
                except Exception as re_error:
                    logger.error("Re-registration failed", error=str(re_error))