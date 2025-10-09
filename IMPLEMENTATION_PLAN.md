# Implementation Plan: TSE-0001.12.0b - Prometheus Metrics with Clean Architecture (risk-monitor-py)

## Branch
`feature/TSE-0001.12.0b-prometheus-metrics-client`

## Objective
Implement Prometheus metrics collection for risk-monitor-py using **Clean Architecture principles** (port/adapter pattern), following the proven pattern from audit-correlator-go. Enable future migration to pure OpenTelemetry by ensuring domain layer never depends on infrastructure concerns.

## Current State Analysis

**risk-monitor-py** currently has:
- ❌ **Non-Clean Architecture**: Direct `prometheus_client` imports in presentation/middleware layer
- ❌ **No MetricsPort abstraction**: Tight coupling to Prometheus implementation
- ❌ **Mixed concerns**: Middleware directly creates Counter/Histogram metrics
- ❌ **Hard to test**: Cannot mock metrics for unit tests
- ❌ **Not future-proof**: Cannot swap to OpenTelemetry without changing multiple layers

**What works well (to preserve)**:
- ✅ RED pattern metrics (Rate, Errors, Duration)
- ✅ Request tracking middleware
- ✅ Low-cardinality labels (method, endpoint, status, protocol)
- ✅ /metrics endpoint at root level

## Target Architecture (Clean Architecture Pattern)

```
┌─────────────────────────────────────────────────────────────┐
│                   Presentation Layer                        │
│  ┌────────────────┐  ┌──────────────────────────────────┐  │
│  │ Metrics Router │  │  RED Metrics Middleware          │  │
│  │  /metrics      │  │  (FastAPI middleware)            │  │
│  └────────┬───────┘  └──────────────┬───────────────────┘  │
│           │                          │                      │
└───────────┼──────────────────────────┼──────────────────────┘
            │   depends on interface   │
            ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Domain Layer (Port)                        │
│  ┌───────────────────────────────────────────────────────┐ │
│  │          MetricsPort (Protocol/ABC)                   │ │
│  │  - inc_counter(name, labels)                          │ │
│  │  - observe_histogram(name, value, labels)             │ │
│  │  - set_gauge(name, value, labels)                     │ │
│  │  - get_http_handler() -> Callable                     │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────┬─────────────────────────────────────┘
                        │  implemented by adapter
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure Layer (Adapter)                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │      PrometheusMetricsAdapter                         │ │
│  │  implements MetricsPort                               │ │
│  │                                                        │ │
│  │  - Uses prometheus_client library                     │ │
│  │  - Thread-safe lazy initialization                    │ │
│  │  - Registers Python runtime metrics                   │ │
│  │  - Applies constant labels (service, instance, ver)   │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Phases (TDD Red-Green-Refactor)

### Phase 0: Branch & Planning ✅
- Create feature branch
- Create IMPLEMENTATION_PLAN.md

### Phase 1: Domain Layer - MetricsPort Interface (RED)
**File**: `src/risk_monitor/domain/ports/metrics.py` (NEW)

Create failing tests first:
- `tests/unit/domain/ports/test_metrics_port.py` (NEW)
  - TestMetricsPortProtocol (interface validation)
  - TestMetricsLabels (helper struct tests)

**Expected**: Tests fail (module doesn't exist)

### Phase 2: Domain Layer - MetricsPort Implementation (GREEN)
Implement the port interface:
- MetricsPort protocol with 4 methods
- MetricsLabels dataclass with to_dict() and constant_labels()
- Pythonic design (snake_case, dataclasses, typing.Protocol)

**Expected**: Domain tests passing

### Phase 3: Infrastructure - PrometheusAdapter Tests (RED)
**File**: `tests/unit/infrastructure/observability/test_prometheus_adapter.py` (NEW)

Create comprehensive failing tests:
- TestPrometheusMetricsAdapter (8 scenarios)
  - Counter increment with labels
  - Histogram observation with values
  - Gauge setting with labels
  - HTTP handler generation
  - Thread-safe lazy initialization
  - Constant labels application
  - Python runtime metrics inclusion
  - Multiple metric types coexistence

**Expected**: Tests fail (adapter doesn't exist)

### Phase 4: Infrastructure - PrometheusAdapter Implementation (GREEN)
**File**: `src/risk_monitor/infrastructure/observability/prometheus_adapter.py` (NEW)

Implement adapter:
- PrometheusMetricsAdapter class implementing MetricsPort
- Thread-safe lazy metric initialization (counters/histograms/gauges dicts)
- Python runtime metrics (process_*, python_gc_*)
- Constant labels support
- Registry isolation (avoid global DEFAULT_REGISTRY)
- HTTP handler via generate_latest()

**Expected**: Infrastructure tests passing

### Phase 5: Infrastructure - Middleware Refactor Tests (RED)
**File**: `tests/unit/infrastructure/observability/test_metrics_middleware.py` (NEW)

Create failing tests for new middleware:
- TestREDMetricsMiddleware (FastAPI middleware)
  - Request counter increments
  - Duration histogram observations
  - Error counter on 4xx/5xx
  - Low-cardinality label validation
  - Mock MetricsPort usage (no Prometheus dependency)

**Expected**: Tests fail (new middleware doesn't exist)

### Phase 6: Infrastructure - Middleware Implementation (GREEN)
**File**: `src/risk_monitor/infrastructure/observability/metrics_middleware.py` (NEW)

Implement Clean Architecture middleware:
- REDMetricsMiddleware accepting MetricsPort
- FastAPI Starlette middleware pattern
- RED pattern: http_requests_total, http_request_duration_seconds, http_request_errors_total
- Labels: method, route, code (low cardinality)

**Deprecate**: `src/risk_monitor/presentation/shared/middleware.py` (old implementation)

**Expected**: Middleware tests passing

### Phase 7: Presentation - Metrics Router Refactor Tests (RED)
**File**: `tests/unit/presentation/http/routers/test_metrics.py` (NEW)

Create failing tests:
- TestMetricsRouter
  - Returns HTTP 200
  - Content-Type: text/plain
  - Contains Prometheus format metrics
  - Includes Python runtime metrics
  - Uses dependency injection (MetricsPort)

**Expected**: Tests fail (new router doesn't exist)

### Phase 8: Presentation - Metrics Router Implementation (GREEN)
**File**: Update `src/risk_monitor/presentation/http/routers/metrics.py`

Refactor to use MetricsPort:
- Accept MetricsPort via dependency injection
- Call port.get_http_handler()
- Return Response with proper content type

**Expected**: Presentation tests passing

### Phase 9: Main Application Integration
**File**: `src/risk_monitor/main.py`

Update DualProtocolServer:
1. Initialize PrometheusMetricsAdapter with constant labels
2. Pass metrics_port to create_fastapi_app()
3. Add metrics_port to app.state for router access

**File**: `src/risk_monitor/presentation/http/app.py`

Update create_fastapi_app():
1. Accept metrics_port parameter
2. Replace old RequestTracker middleware with REDMetricsMiddleware(metrics_port)
3. Pass metrics_port to metrics router

**Expected**: All 59 existing tests still passing + new tests

### Phase 10: Prometheus Configuration
**File**: `orchestrator-docker/prometheus/prometheus.yml`

Update risk-monitor scrape config:
- Add environment label
- Ensure scrape_interval: 15s
- Confirm metrics_path: /metrics
- Validate IP address (172.20.0.85)

### Phase 11: Full Test Suite Validation
Run complete test suite:
- Unit tests: All passing
- Integration tests: All passing
- Test coverage: Maintain ≥85%
- No regressions in existing functionality

### Phase 12: Documentation
**File**: `docs/prs/feature-TSE-0001.12.0b-prometheus-metrics-client.md` (NEW)

Create comprehensive PR documentation:
- Architecture diagram (ASCII art)
- Clean Architecture benefits explanation
- Migration path from old to new implementation
- Testing strategy and coverage
- Future OpenTelemetry migration notes

### Phase 13: TODO Updates
**File**: `risk-monitor-py/TODO.md`

Add new milestone:
```markdown
### 📊 Milestone TSE-0001.12.0b: Prometheus Metrics (Clean Architecture)
**Status**: ✅ COMPLETED
**Branch**: feature/TSE-0001.12.0b-prometheus-metrics-client

**Deliverables**:
- ✅ MetricsPort interface (domain/ports)
- ✅ PrometheusMetricsAdapter (infrastructure/observability)
- ✅ Clean Architecture middleware (decoupled from Prometheus)
- ✅ Comprehensive test suite (X tests passing)
- ✅ Future-proof for OpenTelemetry migration
```

**File**: `project-plan/TODO-MASTER.md`

Document under TSE-0001.12.0b section.

### Phase 14: Git Commits
Commit in repositories:
1. **risk-monitor-py**: All code changes, tests, documentation
2. **orchestrator-docker**: Prometheus configuration updates
3. **project-plan**: TODO-MASTER.md updates

## Python-Specific Design Decisions

### 1. Protocol vs ABC
Use `typing.Protocol` for MetricsPort (structural subtyping, more Pythonic than Go interfaces)

### 2. Dataclass for Labels
Use `@dataclass` for MetricsLabels (cleaner than Go structs)

### 3. Thread Safety
Python GIL provides some safety, but still use threading.Lock for dict mutations

### 4. Registry Isolation
Create custom Registry (not DEFAULT_REGISTRY) to avoid global state pollution

### 5. Async Compatibility
Ensure middleware works with FastAPI's async/await patterns

### 6. Type Hints
Full type hints with mypy strict mode compliance

## BDD Acceptance Criteria

✅ Risk Monitor exposes /metrics endpoint with Prometheus format
✅ RED pattern metrics collected for all HTTP requests
✅ Metrics use Clean Architecture (MetricsPort abstraction)
✅ Domain layer has zero Prometheus dependencies
✅ Can mock MetricsPort for testing without prometheus_client
✅ Python runtime metrics included (process, gc, threads)
✅ Constant labels applied (service, instance, version)
✅ Future OpenTelemetry migration requires only adapter swap

## Success Metrics

- ✅ MetricsPort interface defined in domain layer
- ✅ Zero prometheus_client imports in domain/application layers
- ✅ PrometheusMetricsAdapter passes 8+ test scenarios
- ✅ Middleware tests use mocked MetricsPort (no real Prometheus)
- ✅ All existing tests still passing (59+)
- ✅ New test coverage: 20+ tests for metrics functionality
- ✅ Clean Architecture compliance verified
- ✅ Prometheus scraping configured and validated

## Migration Notes

**Deprecation Path**:
- Old: `presentation/shared/middleware.py` with direct prometheus_client imports
- New: `infrastructure/observability/metrics_middleware.py` with MetricsPort injection
- Keep old file initially (mark deprecated), remove after validation

**Breaking Changes**: None (internal refactoring only)

## Dependencies

- prometheus_client>=0.23.1 (already in pyproject.toml ✅)
- Python 3.13 type hints and dataclasses ✅
- FastAPI Starlette middleware ✅

---

**Epic**: TSE-0001 Foundation Services & Infrastructure
**Milestone**: TSE-0001.12.0b Prometheus Metrics (Clean Architecture)
**Priority**: High
**Estimated Effort**: 14 phases (TDD red-green cycles)
**Created**: 2025-10-09
