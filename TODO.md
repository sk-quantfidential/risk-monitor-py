# risk-monitor-py TODO

## epic-TSE-0001: Foundation Services & Infrastructure

### 🏗️ Milestone TSE-0001.1b: Python Services Bootstrapping
**Status**: ✅ COMPLETED
**Priority**: High

**Tasks**:
- [x] Create Python service directory structure following clean architecture
- [x] Implement health check endpoint (REST and gRPC)
- [x] Basic structured logging with levels
- [x] Error handling infrastructure
- [x] Dockerfile for service containerization
- [x] Update to Python 3.13

**BDD Acceptance**: All Python services can start, respond to health checks, and shutdown gracefully

---

### 🔗 Milestone TSE-0001.3c: Python Services gRPC Integration
**Status**: Not Started
**Priority**: High

**Tasks**:
- [ ] Implement gRPC server with health service
- [ ] Service registration with Redis-based discovery
- [ ] Configuration service client integration
- [ ] Inter-service communication testing

**BDD Acceptance**: Python services can discover and communicate with each other via gRPC

**Dependencies**: TSE-0001.1b (Python Services Bootstrapping), TSE-0001.3a (Core Infrastructure)

---

### ⚠️ Milestone TSE-0001.7a: Risk Monitor Data Collection (PRIMARY)
**Status**: Not Started
**Priority**: CRITICAL - Production-like data integration

**Tasks**:
- [ ] Position tracking from exchange APIs
- [ ] Balance tracking from custodian APIs
- [ ] Real-time market data feed integration
- [ ] **Pure production design** - only accesses production APIs
- [ ] Data validation and error handling
- [ ] API client resilience patterns

**BDD Acceptance**: Risk Monitor can collect position and market data from all production APIs

**Dependencies**: TSE-0001.3c (Python Services gRPC Integration), TSE-0001.4 (Market Data), TSE-0001.5b (Exchange), TSE-0001.6 (Custodian)

---

### ⚠️ Milestone TSE-0001.7b: Risk Monitor Alert Generation (PRIMARY)
**Status**: Not Started
**Priority**: CRITICAL - Core risk monitoring functionality

**Tasks**:
- [ ] Basic P&L calculation from market data
- [ ] Simple threshold monitoring (position limits)
- [ ] Alert generation and notification system
- [ ] Prometheus metrics emission for compliance signals
- [ ] Risk compliance status tracking
- [ ] Alert timing and latency monitoring

**BDD Acceptance**: Risk Monitor detects position limit breaches and emits alerts

**Dependencies**: TSE-0001.7a (Risk Monitor Data Collection)

---

### 📈 Milestone TSE-0001.12a: Data Flow Integration
**Status**: Not Started
**Priority**: Medium

**Tasks**:
- [ ] Integration with complete trading flow validation
- [ ] Risk alert correlation with audit system
- [ ] End-to-end risk monitoring validation
- [ ] Production-like risk dashboard validation

**BDD Acceptance**: Market data flows correctly from simulator to risk monitor with acceptable latency

**Dependencies**: TSE-0001.7b (Risk Monitor Alert Generation), TSE-0001.10 (Audit Infrastructure)

---

### 📈 Milestone TSE-0001.12b: Trading Flow Integration
**Status**: Not Started
**Priority**: Medium

**Tasks**:
- [ ] Risk monitoring during trading validation
- [ ] Real-time position and P&L tracking during trades
- [ ] Alert generation during active trading scenarios

**BDD Acceptance**: Complete trading flow works end-to-end with risk monitoring

**Dependencies**: TSE-0001.7b (Risk Monitor Alert Generation), TSE-0001.8 (Trading Engine), TSE-0001.6 (Custodian)

---

## Implementation Notes

- **Production Purity**: CRITICAL - Only access production APIs (exchange, custodian, market data)
- **No Audit Contamination**: Must NOT have access to simulation infrastructure
- **Signal Emission**: Risk compliance becomes another data stream for audit correlation
- **Alert Types**: Position limits, P&L drawdown, delta exposure, concentration risk
- **Performance**: Low-latency risk calculation and alert generation
- **Production Migration**: Must be deployable to production with zero changes

---

**Last Updated**: 2025-09-17