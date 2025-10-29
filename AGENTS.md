# Agent Guide: Risk Monitor Service

This document helps agents work effectively in this repository. It summarizes intent, structure, conventions, and tips that keep changes safe, minimal, and aligned with the tests and ecosystem.

## Scope & Goals

- Component: Risk monitoring microservice in a larger trading-ecosystem.
- Interfaces: Dual HTTP (FastAPI) and gRPC (grpc.aio) servers running concurrently.
- Behavior: Serves health/metrics endpoints, returns risk metrics (mock or via gRPC/protobuf), exposes basic alerts/limits routes, integrates with service discovery, inter-service gRPC clients, and a configuration service client.
- Production-like constraints: Prefer external-facing APIs and explicit service integration patterns; avoid hidden in-process shortcuts.
- Tests expect graceful behavior when protobuf schemas are not available (fallback mode).

## Repo Map (what you’ll touch most)

- `src/risk_monitor/main.py` — Entry point orchestrating HTTP and gRPC servers, signal handling, and OpenTelemetry setup.
- `src/risk_monitor/presentation/http/app.py` — FastAPI app factory, CORS, instrumentation, routers, middleware.
- `src/risk_monitor/presentation/http/routers/` — HTTP routes:
  - `health.py` — /api/v1/health, /health/live, /health/ready
  - `risk.py` — risk metrics, alerts, limits, and a 501 calculate endpoint
  - `metrics.py` — Prometheus scrape endpoint at `/metrics`
- `src/risk_monitor/presentation/grpc/server.py` — gRPC server and service registration (health + analytics when available).
- `src/risk_monitor/presentation/grpc/services/` — gRPC service implementations:
  - `health.py` — grpc.health.v1 implementation
  - `risk.py` — Analytics-style risk methods (mock/proto-backed)
- `src/risk_monitor/presentation/shared/` — Common middleware and converters (HTTP⇄protobuf); respect `PROTOBUF_AVAILABLE` gating.
- `src/risk_monitor/infrastructure/` — Cross-cutting infra:
  - `config.py` — Pydantic `Settings` (ports default: HTTP 8084, gRPC 50054)
  - `logging.py` — structlog setup
  - `service_discovery.py` — Redis-backed service registry client (heartbeat/TTL)
  - `grpc_clients.py` — Inter-service gRPC client base + concrete mock clients
  - `configuration_client.py` — HTTP client for centralized config service (with cache + validation)
- `src/risk_monitor/domain/` — Business logic placeholder (`risk_service.py`).
- `tests/` — Unit and integration tests. Treat as the behavioral contract for this repo.
- `proto/` — Protobuf schemas and scripts (optional at runtime; tests work without compiled Python stubs).

## Running & Testing

- Python: 3.13 target. Tests mock external dependencies and disable telemetry.
- Run tests:
  - `pytest -q` or `pytest tests/ -v`
- Start HTTP server (dev):
  - `uvicorn risk_monitor.main:app` is not used; instead run module entry `python -m risk_monitor.main` (it starts both servers). For HTTP-only dev, use `create_fastapi_app(Settings())` pattern via ASGI if needed.
- OpenTelemetry during tests:
  - Tests set `OTEL_SDK_DISABLED=true` automatically (see `tests/conftest.py`). Don’t re-enable it in tests.

## Protobuf & Fallback Mode

- Many endpoints/services are guarded by `PROTOBUF_AVAILABLE` (import try/except of `api.v1.*`, `market.v1.*`).
- If generated Python stubs aren’t present, the service must still work using mock data and minimalist responses. Do not break fallback paths.
- To generate Python code from protos (outside CI), use scripts under `proto/scripts/` (e.g., `generate-python.sh`) and ensure the generated packages are importable on PYTHONPATH.

## Service Discovery (Redis)

- Keys: `registry:services:{service_name}` with TTL ≈ `health_check_interval * 3` seconds.
- `ServiceDiscovery.connect()` establishes Redis and an HTTP client; `register_service()` writes `ServiceInfo` and starts a heartbeat loop.
- `discover_services()` filters out stale entries using `last_heartbeat` and test-friendly parsing.
- Tests mock Redis; avoid real Redis dependencies in unit tests.

## Inter-service gRPC Clients

- `BaseGrpcClient` caches grpc.aio channels per address, performs a health-check on connect, wraps calls with a simple circuit-breaker counter and OTel span scaffolding.
- `TradingEngineClient` and `CoordinatorGrpcClient` currently return shaped mock objects in `_execute_call`. When adding new methods, either:
  - Keep mock implementations consistent with tests, or
  - Integrate real stubs behind feature flags while preserving existing tests.
- `InterServiceClientManager` discovers services when available; otherwise falls back to settings host/ports. Always support both paths.

## HTTP Endpoints: Contract Highlights

- Health
  - `/api/v1/health`: JSON with `status`, `timestamp`, `version`, `uptime_seconds`, `dependencies` containing `redis`, `postgres`, `service_registry`.
  - `/api/v1/health/live`: `{ status: "alive" }`.
  - `/api/v1/health/ready`: returns 200 and `{ ready: true, checks: {...} }` (tests assume all True for now); return 503 if not ready when you implement real checks.
- Risk
  - `/api/v1/risk/metrics`: requires `instrument_id`; validates `lookback_days` and `confidence_level`. If protobuf is available, calls gRPC Analytics service and converts the response. Otherwise, return the fixed mock structure (keep shape stable for tests).
  - `/api/v1/risk/alerts`: returns a list with optional `severity` filter and `limit`.
  - `/api/v1/risk/limits`: `GET` returns positive defaults; `PUT` echoes validated updates (no persistence yet).
  - `/api/v1/risk/calculate`: returns HTTP 501 Not Implemented.
- Metrics
  - `/metrics`: Prometheus plaintext via `prometheus_client.generate_latest()`.

## Converters (HTTP ↔ Protobuf)

- File: `presentation/shared/converters.py`.
- Keep conversions null/empty-safe and guarded by `PROTOBUF_AVAILABLE`. If you add new fields in protos, expand conversions carefully to keep HTTP models backward-compatible for tests.

## Observability & Logging

- Structured logs via `structlog` (JSON by default). Keep logs concise and context-rich.
- Request tracking middleware records Prometheus counters/histograms for both HTTP and gRPC calls.
- Tracing is configured in `main.py` via OTLP exporter. Don’t enable exporters during tests.

## Configuration Client

- Validates keys (hierarchical pattern), validates/handles HTTP responses, caches values with TTL, supports environment-specific fetches, and subscriptions for updates.
- In tests, some mocked `httpx` responses use a synchronous `json()` callable; don’t assume `await response.json()`.

## Coding Conventions

- Python 3.13 syntax; type hints on public functions.
- Pydantic v2 (`pydantic_settings`) for config; avoid introducing global state beyond `@lru_cache` for settings.
- Keep changes minimal and focused. Do not rename public endpoints, models, or change response shapes unless tests are updated accordingly.
- Prefer async I/O for network-bound operations. Avoid blocking calls in async paths.
- Use existing logging and metrics utilities; don’t add new logging frameworks.

## Test Strategy

- Favor unit tests with mocks over real network/Redis.
- Integration tests here still rely on mocks for external services; maintain those seams.
- When adding functionality:
  - Start with unit tests close to your changes.
  - If extending external interactions (e.g., new gRPC calls), add or adapt mocks and fixtures.
  - Avoid adding real network dependencies.

## Safe Change Checklist

- Run `pytest` and ensure no regressions.
- Validate fallback behavior with protobuf imports unavailable.
- Keep health endpoints fast (<100ms) and risk endpoints performant in tests (<1s).
- Ensure graceful shutdown paths are intact (no unawaited tasks).

## Common Pitfalls

- Breaking fallback paths when protobuf isn’t available.
- Performing blocking I/O in async code.
- Changing response schemas the tests rely on.
- Emitting real network calls in tests (violates test design and can hang CI).

## Contributing Notes

- Small, surgical patches over sweeping refactors.
- Update README/this guide when you change behaviors or add endpoints.
- Keep telemetry optional and silent in tests.

If you need more context, read `README.md` for the broader vision and use the tests as the ground truth for what must work today.
