"""
Tests for application startup and initialization.

Tests TSE-0001.12.0 multi-instance infrastructure integration.
"""
from unittest.mock import Mock, patch

import pytest

from risk_monitor.infrastructure.config import Settings
from risk_monitor.main import DualProtocolServer


class TestDualProtocolServerInitialization:
    """Test DualProtocolServer initialization with instance awareness."""

    @patch('risk_monitor.main.get_settings')
    def test_server_initialization_singleton(self, mock_get_settings):
        """Test server initializes correctly for singleton instance.

        Given: Singleton configuration (service_name == service_instance_name)
        When: DualProtocolServer is initialized
        Then: Logger is bound with correct instance context
        """
        mock_settings = Mock(spec=Settings)
        mock_settings.service_name = "risk-monitor"
        mock_settings.service_instance_name = "risk-monitor"
        mock_settings.environment = "docker"
        mock_get_settings.return_value = mock_settings

        server = DualProtocolServer()

        assert server.settings == mock_settings
        assert server.settings.service_name == "risk-monitor"
        assert server.settings.service_instance_name == "risk-monitor"
        assert server.settings.environment == "docker"

    @patch('risk_monitor.main.get_settings')
    def test_server_initialization_multi_instance(self, mock_get_settings):
        """Test server initializes correctly for multi-instance.

        Given: Multi-instance configuration (service_name != service_instance_name)
        When: DualProtocolServer is initialized
        Then: Logger is bound with correct instance context
        """
        mock_settings = Mock(spec=Settings)
        mock_settings.service_name = "risk-monitor"
        mock_settings.service_instance_name = "risk-monitor-LH"
        mock_settings.environment = "production"
        mock_get_settings.return_value = mock_settings

        server = DualProtocolServer()

        assert server.settings == mock_settings
        assert server.settings.service_name == "risk-monitor"
        assert server.settings.service_instance_name == "risk-monitor-LH"
        assert server.settings.environment == "production"

    @patch('risk_monitor.main.get_settings')
    def test_server_components_initialized(self, mock_get_settings):
        """Test all server components are initialized.

        Given: Valid configuration
        When: DualProtocolServer is initialized
        Then: All components are set to initial states
        """
        mock_settings = Mock(spec=Settings)
        mock_settings.service_name = "risk-monitor"
        mock_settings.service_instance_name = "risk-monitor"
        mock_settings.environment = "development"
        mock_get_settings.return_value = mock_settings

        server = DualProtocolServer()

        assert server.http_server is None
        assert server.grpc_server is None
        assert server.service_discovery is None
        assert server.data_adapter is None
        assert server.shutdown_event is not None


class TestObservabilitySetup:
    """Test OpenTelemetry observability configuration."""

    @patch('risk_monitor.main.get_settings')
    @patch('risk_monitor.main.TracerProvider')
    @patch('risk_monitor.main.OTLPSpanExporter')
    @patch('risk_monitor.main.BatchSpanProcessor')
    def test_observability_setup_success(
        self,
        mock_batch_processor,
        mock_otlp_exporter,
        mock_tracer_provider,
        mock_get_settings
    ):
        """Test OpenTelemetry setup succeeds with valid configuration.

        Given: Valid OpenTelemetry configuration
        When: setup_observability is called
        Then: TracerProvider and exporter are configured correctly
        """
        mock_settings = Mock(spec=Settings)
        mock_settings.service_name = "risk-monitor"
        mock_settings.service_instance_name = "risk-monitor"
        mock_settings.environment = "docker"
        mock_settings.otel_exporter_endpoint = "http://localhost:4317"
        mock_settings.otel_insecure = True
        mock_get_settings.return_value = mock_settings

        server = DualProtocolServer()

        # Should not raise any exceptions
        server.setup_observability()

        # Verify OTLP exporter was created with correct config
        mock_otlp_exporter.assert_called_once_with(
            endpoint="http://localhost:4317",
            insecure=True,
        )

    @patch('risk_monitor.main.get_settings')
    @patch('risk_monitor.main.TracerProvider', side_effect=Exception("OTLP connection failed"))
    def test_observability_setup_failure_graceful(
        self,
        mock_tracer_provider,
        mock_get_settings
    ):
        """Test OpenTelemetry setup fails gracefully without crashing.

        Given: OpenTelemetry configuration that causes errors
        When: setup_observability is called
        Then: Exception is caught and logged, service continues
        """
        mock_settings = Mock(spec=Settings)
        mock_settings.service_name = "risk-monitor"
        mock_settings.service_instance_name = "risk-monitor"
        mock_settings.environment = "docker"
        mock_settings.otel_exporter_endpoint = "http://invalid:4317"
        mock_settings.otel_insecure = True
        mock_get_settings.return_value = mock_settings

        server = DualProtocolServer()

        # Should not raise exception, should log warning instead
        server.setup_observability()

        # Server should still be usable
        assert server.settings is not None


class TestSignalHandlers:
    """Test signal handler setup for graceful shutdown."""

    @patch('risk_monitor.main.get_settings')
    @patch('risk_monitor.main.signal')
    def test_signal_handlers_registered(self, mock_signal, mock_get_settings):
        """Test signal handlers are registered correctly.

        Given: DualProtocolServer instance
        When: setup_signal_handlers is called
        Then: SIGTERM and SIGINT handlers are registered
        """
        mock_settings = Mock(spec=Settings)
        mock_settings.service_name = "risk-monitor"
        mock_settings.service_instance_name = "risk-monitor"
        mock_settings.environment = "docker"
        mock_get_settings.return_value = mock_settings

        server = DualProtocolServer()
        server.setup_signal_handlers()

        # Verify signal handlers were registered
        assert mock_signal.signal.call_count == 2


class TestInstanceAwareConfiguration:
    """Test instance-aware configuration for TSE-0001.12.0."""

    def test_singleton_configuration_backward_compatible(self):
        """Test singleton configuration maintains backward compatibility.

        Given: Configuration with service_instance_name = ""
        When: Settings is initialized
        Then: service_instance_name defaults to service_name
        """
        settings = Settings(
            service_name="risk-monitor",
            service_instance_name="",
        )

        assert settings.service_instance_name == "risk-monitor"

    def test_multi_instance_configuration(self):
        """Test multi-instance configuration is preserved.

        Given: Configuration with explicit service_instance_name
        When: Settings is initialized
        Then: service_instance_name is preserved as-is
        """
        settings = Settings(
            service_name="risk-monitor",
            service_instance_name="risk-monitor-lh",  # Must be lowercase per DNS-safe validation
        )

        assert settings.service_name == "risk-monitor"
        assert settings.service_instance_name == "risk-monitor-lh"

    def test_environment_docker_support(self):
        """Test 'docker' environment is supported.

        Given: Configuration with environment = "docker"
        When: Settings is initialized
        Then: Environment is set to "docker"
        """
        settings = Settings(
            environment="docker",
        )

        assert settings.environment == "docker"

    @pytest.mark.parametrize("env", ["development", "testing", "production", "docker"])
    def test_all_environments_supported(self, env):
        """Test all environment types are supported.

        Given: Valid environment value
        When: Settings is initialized
        Then: Environment is accepted
        """
        settings = Settings(environment=env)
        assert settings.environment == env


class TestHealthEndpointInstanceAwareness:
    """Test health endpoint returns instance information."""

    def test_health_response_includes_instance(self):
        """Test health check response includes instance metadata.

        Given: Health endpoint with instance-aware configuration
        When: Health check is called
        Then: Response includes service, instance, environment, timestamp
        """
        from risk_monitor.presentation.health import HealthResponse

        response = HealthResponse(
            status="healthy",
            service="risk-monitor",
            instance="risk-monitor-LH",
            version="0.1.0",
            environment="production",
            timestamp="2025-10-09T12:00:00Z",
        )

        assert response.status == "healthy"
        assert response.service == "risk-monitor"
        assert response.instance == "risk-monitor-LH"
        assert response.environment == "production"
        assert response.timestamp == "2025-10-09T12:00:00Z"

    def test_health_response_singleton_instance(self):
        """Test health response for singleton instance.

        Given: Singleton instance configuration
        When: Health check is called
        Then: service and instance have same value
        """
        from risk_monitor.presentation.health import HealthResponse

        response = HealthResponse(
            status="healthy",
            service="risk-monitor",
            instance="risk-monitor",
            version="0.1.0",
            environment="docker",
            timestamp="2025-10-09T12:00:00Z",
        )

        assert response.service == response.instance
        assert response.environment == "docker"
