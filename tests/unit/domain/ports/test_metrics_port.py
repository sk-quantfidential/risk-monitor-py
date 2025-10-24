"""Unit tests for MetricsPort interface (domain layer).

Following BDD Given/When/Then pattern and TDD RED phase.
Tests written BEFORE implementation to drive design.
"""
from typing import Callable
from unittest.mock import MagicMock

import pytest

from risk_monitor.domain.ports.metrics import MetricsLabels, MetricsPort


class TestMetricsPortProtocol:
    """Test MetricsPort protocol definition following Clean Architecture."""

    def test_metrics_port_defines_inc_counter_method(self) -> None:
        """Given a MetricsPort implementation
        When checking the interface
        Then it should have inc_counter method accepting name and labels.
        """
        # Given: A mock implementation of MetricsPort
        mock_port = MagicMock(spec=MetricsPort)

        # When: We check for the method
        # Then: The method should exist
        assert hasattr(mock_port, "inc_counter")
        assert callable(mock_port.inc_counter)

    def test_metrics_port_defines_observe_histogram_method(self) -> None:
        """Given a MetricsPort implementation
        When checking the interface
        Then it should have observe_histogram method accepting name, value, and labels.
        """
        # Given: A mock implementation of MetricsPort
        mock_port = MagicMock(spec=MetricsPort)

        # When: We check for the method
        # Then: The method should exist
        assert hasattr(mock_port, "observe_histogram")
        assert callable(mock_port.observe_histogram)

    def test_metrics_port_defines_set_gauge_method(self) -> None:
        """Given a MetricsPort implementation
        When checking the interface
        Then it should have set_gauge method accepting name, value, and labels.
        """
        # Given: A mock implementation of MetricsPort
        mock_port = MagicMock(spec=MetricsPort)

        # When: We check for the method
        # Then: The method should exist
        assert hasattr(mock_port, "set_gauge")
        assert callable(mock_port.set_gauge)

    def test_metrics_port_defines_get_http_handler_method(self) -> None:
        """Given a MetricsPort implementation
        When checking the interface
        Then it should have get_http_handler method returning a callable.
        """
        # Given: A mock implementation of MetricsPort
        mock_port = MagicMock(spec=MetricsPort)
        mock_port.get_http_handler.return_value = lambda: None

        # When: We check for the method
        # Then: The method should exist and return callable
        assert hasattr(mock_port, "get_http_handler")
        assert callable(mock_port.get_http_handler)
        handler = mock_port.get_http_handler()
        assert callable(handler)


class TestMetricsLabels:
    """Test MetricsLabels dataclass helper."""

    def test_metrics_labels_to_dict_includes_all_fields(self) -> None:
        """Given MetricsLabels with all fields populated
        When converting to dict
        Then all fields should be included.
        """
        # Given: MetricsLabels with all fields
        labels = MetricsLabels(
            service="risk-monitor",
            instance="risk-monitor",
            version="0.1.0",
            method="GET",
            route="/api/v1/health",
            code="200",
        )

        # When: Converting to dict
        result = labels.to_dict()

        # Then: All fields should be present
        assert result == {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
            "method": "GET",
            "route": "/api/v1/health",
            "code": "200",
        }

    def test_metrics_labels_to_dict_excludes_empty_fields(self) -> None:
        """Given MetricsLabels with some empty fields
        When converting to dict
        Then only non-empty fields should be included.
        """
        # Given: MetricsLabels with partial fields
        labels = MetricsLabels(
            service="risk-monitor",
            instance="risk-monitor",
            version="0.1.0",
            method="",  # Empty
            route="",  # Empty
            code="",  # Empty
        )

        # When: Converting to dict
        result = labels.to_dict()

        # Then: Only constant labels should be present
        assert result == {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
        }

    def test_metrics_labels_constant_labels_returns_only_service_info(self) -> None:
        """Given MetricsLabels with all fields
        When calling constant_labels
        Then only service, instance, version should be returned.
        """
        # Given: MetricsLabels with all fields
        labels = MetricsLabels(
            service="risk-monitor",
            instance="risk-monitor",
            version="0.1.0",
            method="GET",
            route="/api/v1/health",
            code="200",
        )

        # When: Getting constant labels
        result = labels.constant_labels()

        # Then: Only service identity labels
        assert result == {
            "service": "risk-monitor",
            "instance": "risk-monitor",
            "version": "0.1.0",
        }

    def test_metrics_labels_ensures_low_cardinality(self) -> None:
        """Given MetricsLabels design
        When analyzing label structure
        Then it should enforce low cardinality by design (limited field types).
        """
        # Given: MetricsLabels structure
        labels = MetricsLabels(
            service="risk-monitor",
            instance="risk-monitor",
            version="0.1.0",
            method="POST",  # Low cardinality (HTTP methods)
            route="/api/v1/metrics",  # Low cardinality (route patterns, not full paths)
            code="201",  # Low cardinality (HTTP status codes)
        )

        # When: Converting to dict
        result = labels.to_dict()

        # Then: All labels should be low cardinality types
        assert len(result) == 6  # Only 6 label types total
        assert all(isinstance(v, str) for v in result.values())
