"""Clean Architecture metrics middleware for FastAPI.

Uses MetricsPort abstraction instead of direct Prometheus imports,
enabling future migration to OpenTelemetry without changing this code.
"""
import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from risk_monitor.domain.ports.metrics import MetricsPort


def create_red_metrics_middleware(
    metrics_port: MetricsPort,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    """Create RED pattern metrics middleware for FastAPI.

    RED Pattern:
    - Rate: Total number of requests (counter)
    - Errors: Total number of errors (counter, 4xx/5xx)
    - Duration: Request duration distribution (histogram)

    Args:
        metrics_port: MetricsPort implementation for metrics collection

    Returns:
        FastAPI middleware function
    """

    async def red_metrics_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Middleware function that instruments HTTP requests with RED metrics."""
        # Record start time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Extract labels (low cardinality)
        route = request.url.path
        # Use route pattern if available (FastAPI provides this)
        if hasattr(request, "scope") and "route" in request.scope:
            route_obj = request.scope.get("route")
            if route_obj and hasattr(route_obj, "path"):
                route = route_obj.path

        # If route is empty, use special marker
        if not route:
            route = "unknown"

        labels = {
            "method": request.method,
            "route": route,
            "code": str(response.status_code),
        }

        # RED Metric 1: Rate - Total requests
        metrics_port.inc_counter("http_requests_total", labels)

        # RED Metric 2: Duration - Request duration histogram
        metrics_port.observe_histogram("http_request_duration_seconds", duration, labels)

        # RED Metric 3: Errors - Error counter (4xx, 5xx)
        if response.status_code >= 400:
            metrics_port.inc_counter("http_request_errors_total", labels)

        return response

    return red_metrics_middleware
