"""Shared middleware for both HTTP and gRPC protocols."""
import time
from typing import Any, Callable, Dict

import structlog
from opentelemetry import trace
from opentelemetry.instrumentation.utils import unwrap
from prometheus_client import Counter, Histogram

# Metrics
REQUEST_COUNT = Counter(
    "requests_total",
    "Total requests",
    ["method", "endpoint", "status", "protocol"]
)

REQUEST_DURATION = Histogram(
    "request_duration_seconds",
    "Request duration",
    ["method", "endpoint", "protocol"]
)

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class RequestTracker:
    """Shared request tracking for HTTP and gRPC."""

    def __init__(self, protocol: str, method: str, endpoint: str):
        self.protocol = protocol
        self.method = method
        self.endpoint = endpoint
        self.start_time = time.time()

    def track_completion(self, status: str) -> None:
        """Track request completion with metrics and logging."""
        duration = time.time() - self.start_time

        # Update metrics
        REQUEST_COUNT.labels(
            method=self.method,
            endpoint=self.endpoint,
            status=status,
            protocol=self.protocol
        ).inc()

        REQUEST_DURATION.labels(
            method=self.method,
            endpoint=self.endpoint,
            protocol=self.protocol
        ).observe(duration)

        # Log completion
        logger.info(
            "request_completed",
            protocol=self.protocol,
            method=self.method,
            endpoint=self.endpoint,
            status=status,
            duration_ms=round(duration * 1000, 2)
        )


async def trace_request(span_name: str, attributes: Dict[str, Any]) -> Any:
    """Create tracing span for requests."""
    with tracer.start_as_current_span(span_name) as span:
        for key, value in attributes.items():
            span.set_attribute(key, str(value))
        yield span