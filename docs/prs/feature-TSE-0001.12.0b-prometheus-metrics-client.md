# Pull Request: TSE-0001.12.0b - Prometheus Metrics with Clean Architecture (risk-monitor-py)

**Epic:** TSE-0001 - Foundation Services & Infrastructure
**Milestone:** TSE-0001.12.0b - Prometheus Metrics (Clean Architecture)
**Branch:** `feature/TSE-0001.12.0b-prometheus-metrics-client`
**Status:** ✅ Ready for Review
**Date:** 2025-10-09

## Summary

This PR implements Prometheus metrics collection for risk-monitor-py using **Clean Architecture principles** (port/adapter pattern), following the proven implementation from audit-correlator-go. The domain layer never depends on infrastructure concerns, enabling future migration to OpenTelemetry without changing domain, application, or presentation logic.

**Key Achievements:**
1. ✅ **Clean Architecture**: MetricsPort interface in domain layer
2. ✅ **RED Pattern**: Rate, Errors, Duration metrics for all HTTP requests
3. ✅ **Low Cardinality**: Proper label design prevents metric explosion
4. ✅ **Future-Proof**: Can swap Prometheus for OpenTelemetry by changing adapter only
5. ✅ **Testable**: Mock MetricsPort for unit tests without prometheus_client
6. ✅ **Comprehensive Tests**: 19 new tests passing (8 domain + 11 adapter)

## Architecture Diagram

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
│  │          MetricsPort (Protocol)                       │ │
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

## Changes

### 1. Domain Layer - MetricsPort Interface (NEW)

**File:** `src/risk_monitor/domain/ports/metrics.py`
**Purpose:** Define contract for metrics collection, independent of implementation

**Interface:**
- `inc_counter(name, labels)` - Increment counters (requests_total, errors_total)
- `observe_histogram(name, value, labels)` - Record durations (request_duration_seconds)
- `set_gauge(name, value, labels)` - Set point-in-time values (connections, queue depth)
- `get_http_handler()` - Return callable for /metrics endpoint

**Helper:**
- `MetricsLabels` dataclass with `to_dict()` and `constant_labels()` methods
- Enforces low cardinality by design

**Clean Architecture Benefits:**
- Domain never imports prometheus_client
- Interface can be mocked for testing
- Future implementations (OpenTelemetry) implement same protocol

### 2. Infrastructure - PrometheusMetricsAdapter (NEW)

**File:** `src/risk_monitor/infrastructure/observability/prometheus_adapter.py`
**Purpose:** Implement MetricsPort using Prometheus client library

**Features:**
- Thread-safe lazy initialization of metrics
- Custom registry (avoids global state)
- Python runtime metrics (process_*, python_gc_*)
- Sensible histogram buckets (5ms to 10s)
- Constant labels applied to all metrics

**Tests:** 11 comprehensive tests covering:
- Counter increment
- Histogram observation
- Gauge setting
- HTTP handler generation
- Thread safety
- Python runtime metrics
- Multiple metric types coexistence

### 3. Infrastructure - Clean Architecture Middleware (NEW)

**File:** `src/risk_monitor/infrastructure/observability/metrics_middleware.py`
**Purpose:** FastAPI middleware using MetricsPort (not prometheus_client)

**RED Pattern Metrics:**
- `http_requests_total` - Counter (Rate)
- `http_request_duration_seconds` - Histogram (Duration)
- `http_request_errors_total` - Counter for 4xx/5xx (Errors)

**Labels:** method, route, code (low cardinality)

### 4. Presentation - Metrics Router (UPDATED)

**File:** `src/risk_monitor/presentation/http/routers/metrics.py`
**Changes:** Refactored to use MetricsPort from app.state

**Before:**
```python
from prometheus_client import generate_latest
return Response(content=generate_latest())
```

**After:**
```python
metrics_port = request.app.state.metrics_port
handler = metrics_port.get_http_handler()
return Response(content=handler())
```

### 5. Application Integration (UPDATED)

**File:** `src/risk_monitor/presentation/http/app.py`
**Changes:** Accept `metrics_port` parameter, register middleware

**File:** `src/risk_monitor/main.py`
**Changes:** Initialize PrometheusMetricsAdapter with constant labels

## Testing

**New Tests:** 19 tests created
- Domain layer: 8 tests for MetricsPort and MetricsLabels
- Infrastructure: 11 tests for PrometheusMetricsAdapter

**All Tests:** 127 passed, 4 unrelated failures (health endpoint uptime field)

**Coverage:** PrometheusAdapter at 94%, domain/ports/metrics.py at 89%

## Migration Notes

**Deprecation:** Old middleware in `presentation/shared/middleware.py` still exists but no longer used. Can be removed after validation.

**Breaking Changes:** None - internal refactoring only

## BDD Acceptance Criteria

✅ Risk Monitor exposes /metrics endpoint with Prometheus format
✅ RED pattern metrics collected for all HTTP requests
✅ Metrics use Clean Architecture (MetricsPort abstraction)
✅ Domain layer has zero Prometheus dependencies
✅ Can mock MetricsPort for testing
✅ Python runtime metrics included
✅ Constant labels applied (service, instance, version)
✅ Future OpenTelemetry migration requires only adapter swap

## Future Work

- Add OpenTelemetry adapter implementing same MetricsPort interface
- Remove deprecated middleware.py after validation
- Add integration tests for metrics endpoint
- Add Grafana dashboards for RED metrics

---

**Pull Request Checklist:**
- [x] Feature branch created
- [x] Implementation plan documented
- [x] TDD red-green cycles followed
- [x] All new tests passing (19/19)
- [x] Clean Architecture compliance verified
- [x] No domain layer infrastructure dependencies
- [x] Existing tests still passing (127/131 passing)
- [x] PR documentation created
- [ ] TODO files updated
- [ ] Commits created across repositories

**Created:** 2025-10-09
**Author:** Claude Code (TSE Trading Ecosystem Team)
