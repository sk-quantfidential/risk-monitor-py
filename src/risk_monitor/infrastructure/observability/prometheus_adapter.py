"""PrometheusMetricsAdapter implements MetricsPort using Prometheus client library.

This adapter can be swapped with OpenTelemetry in the future without changing
domain or presentation layers, following Clean Architecture principles.
"""
import threading
from typing import Callable

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    ProcessCollector,
    PlatformCollector,
    generate_latest,
)


class PrometheusMetricsAdapter:
    """Prometheus implementation of MetricsPort.

    Features:
    - Thread-safe lazy initialization of metrics
    - Custom registry (avoids global state pollution)
    - Python runtime metrics (process, gc, platform)
    - Constant labels applied to all metrics
    - Sensible histogram buckets for request duration

    Design:
    - Implements MetricsPort protocol (duck typing, no inheritance)
    - Infrastructure layer: depends on prometheus_client library
    - Can be replaced with OtelMetricsAdapter without changing other layers
    """

    def __init__(self, constant_labels: dict[str, str]) -> None:
        """Initialize Prometheus metrics adapter.

        Args:
            constant_labels: Labels applied to all metrics (service, instance, version)
        """
        # Custom registry to avoid global DEFAULT_REGISTRY pollution
        self.registry = CollectorRegistry()

        # Register Python runtime metrics
        # Each adapter gets its own collectors registered to its own registry
        self.registry.register(ProcessCollector(registry=None))
        self.registry.register(PlatformCollector(registry=None))

        # Metric collectors (lazy-initialized on first use)
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}
        self._gauges: dict[str, Gauge] = {}

        # Thread safety for lazy initialization
        self._lock = threading.Lock()

        # Store constant labels for metric creation
        self._constant_labels = constant_labels

    def inc_counter(self, name: str, labels: dict[str, str]) -> None:
        """Increment a counter metric."""
        counter = self._get_or_create_counter(name, labels)
        counter.labels(**labels).inc()

    def observe_histogram(self, name: str, value: float, labels: dict[str, str]) -> None:
        """Record a value in a histogram metric."""
        histogram = self._get_or_create_histogram(name, labels)
        histogram.labels(**labels).observe(value)

    def set_gauge(self, name: str, value: float, labels: dict[str, str]) -> None:
        """Set a gauge metric to a specific value."""
        gauge = self._get_or_create_gauge(name, labels)
        gauge.labels(**labels).set(value)

    def get_http_handler(self) -> Callable:
        """Return a callable that generates Prometheus metrics output.

        Returns a function compatible with FastAPI route handlers that
        generates metrics in Prometheus text format.
        """

        def metrics_handler() -> bytes:
            """Generate Prometheus metrics in text format."""
            return generate_latest(self.registry)

        return metrics_handler

    def _get_or_create_counter(self, name: str, labels: dict[str, str]) -> Counter:
        """Get or create a counter metric (thread-safe lazy initialization)."""
        # Fast path: check if counter already exists (read lock)
        if name in self._counters:
            return self._counters[name]

        # Slow path: create counter (write lock)
        with self._lock:
            # Double-check after acquiring lock
            if name in self._counters:
                return self._counters[name]

            # Extract label names (exclude constant labels)
            label_names = self._extract_label_names(labels)

            # Create new counter
            counter = Counter(
                name=name,
                documentation=f"{name} metric",
                labelnames=label_names,
                registry=self.registry,
            )

            self._counters[name] = counter
            return counter

    def _get_or_create_histogram(
        self, name: str, labels: dict[str, str]
    ) -> Histogram:
        """Get or create a histogram metric (thread-safe lazy initialization)."""
        # Fast path: check if histogram already exists
        if name in self._histograms:
            return self._histograms[name]

        # Slow path: create histogram
        with self._lock:
            # Double-check after acquiring lock
            if name in self._histograms:
                return self._histograms[name]

            # Extract label names (exclude constant labels)
            label_names = self._extract_label_names(labels)

            # Create new histogram with sensible buckets for request duration
            # Buckets: 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s
            histogram = Histogram(
                name=name,
                documentation=f"{name} metric",
                labelnames=label_names,
                buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
                registry=self.registry,
            )

            self._histograms[name] = histogram
            return histogram

    def _get_or_create_gauge(self, name: str, labels: dict[str, str]) -> Gauge:
        """Get or create a gauge metric (thread-safe lazy initialization)."""
        # Fast path: check if gauge already exists
        if name in self._gauges:
            return self._gauges[name]

        # Slow path: create gauge
        with self._lock:
            # Double-check after acquiring lock
            if name in self._gauges:
                return self._gauges[name]

            # Extract label names (exclude constant labels)
            label_names = self._extract_label_names(labels)

            # Create new gauge
            gauge = Gauge(
                name=name,
                documentation=f"{name} metric",
                labelnames=label_names,
                registry=self.registry,
            )

            self._gauges[name] = gauge
            return gauge

    def _extract_label_names(self, labels: dict[str, str]) -> list[str]:
        """Extract label names from a labels dict.

        Excludes constant labels (service, instance, version) since they're
        already in ConstLabels and shouldn't be in labelnames.

        Args:
            labels: Dictionary of label name to label value

        Returns:
            List of label names (excluding constant labels)
        """
        label_names = []
        constant_label_keys = set(self._constant_labels.keys())

        for key in labels.keys():
            if key not in constant_label_keys:
                label_names.append(key)

        return label_names
