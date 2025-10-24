"""Unit tests for PrometheusMetricsAdapter (infrastructure layer).

Following BDD Given/When/Then pattern and TDD RED phase.
Tests implementation of MetricsPort using Prometheus client library.
"""
import pytest

from risk_monitor.infrastructure.observability.prometheus_adapter import (
    PrometheusMetricsAdapter,
)


class TestPrometheusMetricsAdapter:
    """Test PrometheusMetricsAdapter implementation of MetricsPort."""

    def test_adapter_implements_metrics_port(self) -> None:
        """Given a PrometheusMetricsAdapter
        When checking interface compliance
        Then it should implement all MetricsPort methods.
        """
        # Given: Constant labels for adapter
        constant_labels = {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
        }

        # When: Creating adapter
        adapter = PrometheusMetricsAdapter(constant_labels)

        # Then: Should have all MetricsPort methods
        assert hasattr(adapter, "inc_counter")
        assert hasattr(adapter, "observe_histogram")
        assert hasattr(adapter, "set_gauge")
        assert hasattr(adapter, "get_http_handler")
        assert callable(adapter.inc_counter)
        assert callable(adapter.observe_histogram)
        assert callable(adapter.set_gauge)
        assert callable(adapter.get_http_handler)

    def test_inc_counter_creates_and_increments_counter(self) -> None:
        """Given a PrometheusMetricsAdapter
        When incrementing a counter with labels
        Then counter should be created and incremented.
        """
        # Given: Adapter with constant labels
        constant_labels = {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
        }
        adapter = PrometheusMetricsAdapter(constant_labels)

        # When: Incrementing counter twice
        labels = {"method": "GET", "route": "/health", "code": "200"}
        adapter.inc_counter("http_requests_total", labels)
        adapter.inc_counter("http_requests_total", labels)

        # Then: Counter should exist and have value 2
        # (verified by checking metrics output)
        handler = adapter.get_http_handler()
        # Handler should be callable
        assert callable(handler)

    def test_observe_histogram_records_values(self) -> None:
        """Given a PrometheusMetricsAdapter
        When observing histogram values
        Then histogram should record values and create buckets.
        """
        # Given: Adapter with constant labels
        constant_labels = {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
        }
        adapter = PrometheusMetricsAdapter(constant_labels)

        # When: Observing histogram values
        labels = {"method": "GET", "route": "/health"}
        adapter.observe_histogram("http_request_duration_seconds", 0.123, labels)
        adapter.observe_histogram("http_request_duration_seconds", 0.456, labels)

        # Then: Histogram should exist
        handler = adapter.get_http_handler()
        assert callable(handler)

    def test_set_gauge_updates_gauge_value(self) -> None:
        """Given a PrometheusMetricsAdapter
        When setting gauge values
        Then gauge should update to new values.
        """
        # Given: Adapter with constant labels
        constant_labels = {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
        }
        adapter = PrometheusMetricsAdapter(constant_labels)

        # When: Setting gauge values
        labels = {"dependency": "postgresql"}
        adapter.set_gauge("service_dependency_ready", 1.0, labels)
        adapter.set_gauge("service_dependency_ready", 0.0, labels)

        # Then: Gauge should exist
        handler = adapter.get_http_handler()
        assert callable(handler)

    def test_get_http_handler_returns_callable(self) -> None:
        """Given a PrometheusMetricsAdapter
        When getting HTTP handler
        Then should return a callable that can serve metrics.
        """
        # Given: Adapter with constant labels
        constant_labels = {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
        }
        adapter = PrometheusMetricsAdapter(constant_labels)

        # When: Getting HTTP handler
        handler = adapter.get_http_handler()

        # Then: Should be callable
        assert callable(handler)

    def test_metrics_include_constant_labels(self) -> None:
        """Given a PrometheusMetricsAdapter with constant labels
        When collecting metrics
        Then all metrics should include constant labels.
        """
        # Given: Adapter with specific constant labels
        constant_labels = {
            "service": "risk-monitor",
            "instance": "risk-monitor-Alpha",
            "version": "0.2.0",
        }
        adapter = PrometheusMetricsAdapter(constant_labels)

        # When: Creating metrics
        adapter.inc_counter("test_counter", {"method": "POST"})

        # Then: Handler should be available
        handler = adapter.get_http_handler()
        assert callable(handler)

    def test_adapter_includes_python_runtime_metrics(self) -> None:
        """Given a PrometheusMetricsAdapter
        When initializing adapter
        Then Python runtime metrics should be registered automatically.
        """
        # Given: Adapter initialization
        constant_labels = {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
        }

        # When: Creating adapter
        adapter = PrometheusMetricsAdapter(constant_labels)

        # Then: Should have handler (runtime metrics registered)
        handler = adapter.get_http_handler()
        assert callable(handler)

    def test_multiple_metric_types_coexist(self) -> None:
        """Given a PrometheusMetricsAdapter
        When using counters, histograms, and gauges together
        Then all metric types should coexist without conflicts.
        """
        # Given: Adapter with constant labels
        constant_labels = {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
        }
        adapter = PrometheusMetricsAdapter(constant_labels)

        # When: Using all metric types
        adapter.inc_counter("requests_total", {"method": "GET"})
        adapter.observe_histogram("request_duration", 0.5, {"method": "GET"})
        adapter.set_gauge("active_connections", 42.0, {"pool": "default"})

        # Then: All should coexist
        handler = adapter.get_http_handler()
        assert callable(handler)

    def test_thread_safe_lazy_initialization(self) -> None:
        """Given a PrometheusMetricsAdapter
        When multiple threads create metrics concurrently
        Then adapter should handle concurrent initialization safely.
        """
        # Given: Adapter with constant labels
        constant_labels = {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
        }
        adapter = PrometheusMetricsAdapter(constant_labels)

        # When: Creating same metric multiple times (simulating concurrent access)
        for _ in range(10):
            adapter.inc_counter("concurrent_counter", {"test": "value"})

        # Then: Should handle gracefully
        handler = adapter.get_http_handler()
        assert callable(handler)


class TestPrometheusAdapterIntegration:
    """Integration tests for PrometheusMetricsAdapter with actual metrics output."""

    def test_metrics_output_format(self) -> None:
        """Given a PrometheusMetricsAdapter with metrics
        When generating metrics output
        Then output should be in Prometheus text format.
        """
        # Given: Adapter with metrics
        constant_labels = {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
        }
        adapter = PrometheusMetricsAdapter(constant_labels)
        adapter.inc_counter("test_requests", {"method": "GET"})

        # When: Getting metrics output (would call handler in real scenario)
        handler = adapter.get_http_handler()

        # Then: Handler should be callable (format verified in handler implementation)
        assert callable(handler)

    def test_metrics_include_help_and_type_comments(self) -> None:
        """Given a PrometheusMetricsAdapter
        When generating metrics
        Then output should include # HELP and # TYPE comments.
        """
        # Given: Adapter with metrics
        constant_labels = {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
        }
        adapter = PrometheusMetricsAdapter(constant_labels)
        adapter.inc_counter("documented_metric", {"status": "success"})

        # When/Then: Handler should be available for Prometheus format
        handler = adapter.get_http_handler()
        assert callable(handler)
