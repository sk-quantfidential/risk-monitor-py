"""Prometheus metrics endpoint using Clean Architecture.

Updated to use MetricsPort abstraction instead of direct prometheus_client imports.
This enables future migration to OpenTelemetry without changing this code.
"""
from fastapi import APIRouter, Request, Response

router = APIRouter()


@router.get("")
async def metrics(request: Request) -> Response:
    """Prometheus metrics endpoint.

    Retrieves metrics from the MetricsPort stored in app.state.
    The actual metrics format (Prometheus, OpenMetrics, etc.) is
    determined by the adapter implementation.
    """
    # Get metrics_port from app state (injected during app creation)
    metrics_port = request.app.state.metrics_port

    # Get the metrics handler from the port
    handler = metrics_port.get_http_handler()

    # Generate metrics output
    metrics_output = handler()

    return Response(
        content=metrics_output,
        media_type="text/plain; version=0.0.4; charset=utf-8",  # Prometheus format
    )