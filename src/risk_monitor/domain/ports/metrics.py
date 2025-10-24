"""MetricsPort interface for observability metrics collection (domain layer).

This port abstracts the metrics implementation (Prometheus, OpenTelemetry, etc.)
following Clean Architecture principles: domain doesn't depend on infrastructure.

The domain layer defines WHAT metrics capabilities are needed, not HOW they're implemented.
Infrastructure adapters implement HOW (Prometheus, OpenTelemetry, etc.).
"""
from dataclasses import dataclass, field
from typing import Callable, Protocol


class MetricsPort(Protocol):
    """Port (interface) for observability metrics collection.

    This protocol defines the contract for metrics collection using Python's
    structural subtyping (Protocol). Any class implementing these methods
    automatically satisfies this interface without explicit inheritance.

    Following RED pattern metrics:
    - Rate: Total number of requests (counter)
    - Errors: Total number of errors (counter)
    - Duration: Request duration distribution (histogram)

    Additional capability:
    - Gauge: Point-in-time values (e.g., queue depth, connection count)
    """

    def inc_counter(self, name: str, labels: dict[str, str]) -> None:
        """Increment a counter metric by 1.

        Counters only go up (monotonically increasing).
        Use for: request counts, error counts, events processed.

        Args:
            name: Metric name (e.g., "http_requests_total")
            labels: Key-value pairs for metric dimensions
                   (e.g., {"method": "GET", "route": "/health", "code": "200"})
        """
        ...

    def observe_histogram(self, name: str, value: float, labels: dict[str, str]) -> None:
        """Record a value in a histogram metric.

        Histograms track distribution of values over time (e.g., request duration).
        Automatically creates buckets and calculates percentiles.

        Args:
            name: Metric name (e.g., "http_request_duration_seconds")
            value: Observed value (e.g., 0.123 for 123ms)
            labels: Key-value pairs for metric dimensions
        """
        ...

    def set_gauge(self, name: str, value: float, labels: dict[str, str]) -> None:
        """Set a gauge metric to a specific value.

        Gauges can go up or down. Use for: current temperature, queue depth,
        number of active connections, memory usage.

        Args:
            name: Metric name (e.g., "service_dependency_ready")
            value: Gauge value
            labels: Key-value pairs for metric dimensions
        """
        ...

    def get_http_handler(self) -> Callable:
        """Return an HTTP handler that serves the metrics endpoint.

        The handler should be compatible with FastAPI/Starlette route handlers.
        Format (Prometheus text, OpenMetrics, etc.) is determined by the adapter.

        Returns:
            Callable that can be used as FastAPI route handler
        """
        ...


@dataclass
class MetricsLabels:
    """Standard labels used across all metrics.

    These labels should have LOW CARDINALITY to avoid metric explosion.
    High cardinality labels (user IDs, request IDs, timestamps) should NEVER be used.

    Design principle: Labels represent dimensions for filtering/aggregating metrics.
    Each unique combination of label values creates a new time series.
    """

    # Constant labels (set once at startup, applied to all metrics)
    service: str = ""  # Service name (e.g., "risk-monitor")
    instance: str = ""  # Instance identifier (e.g., "risk-monitor" or "risk-monitor-Alpha")
    version: str = ""  # Version (git SHA or semver, e.g., "0.1.0")

    # Request labels (per-request, but limited cardinality)
    method: str = ""  # HTTP method (GET, POST, etc.) - low cardinality
    route: str = ""  # Route pattern (e.g., "/api/v1/health") - low cardinality, NOT full path
    code: str = ""  # HTTP status code (200, 404, 500) - low cardinality

    def to_dict(self) -> dict[str, str]:
        """Convert MetricsLabels to a dict for use with metrics methods.

        Only includes non-empty labels to avoid polluting metrics with empty values.

        Returns:
            Dictionary of label name to label value (only non-empty)
        """
        labels = {}

        if self.service:
            labels["service"] = self.service
        if self.instance:
            labels["instance"] = self.instance
        if self.version:
            labels["version"] = self.version
        if self.method:
            labels["method"] = self.method
        if self.route:
            labels["route"] = self.route
        if self.code:
            labels["code"] = self.code

        return labels

    def constant_labels(self) -> dict[str, str]:
        """Return only the constant labels (service identity).

        These labels are applied to all metrics as constant labels.
        Used during adapter initialization.

        Returns:
            Dictionary of constant labels (service, instance, version)
        """
        return {
            "service": self.service,
            "instance": self.instance,
            "version": self.version,
        }
