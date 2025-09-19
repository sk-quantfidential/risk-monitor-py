# Risk Monitor

A production-grade risk monitoring system built in Python that provides real-time surveillance of trading operations, portfolio risk metrics, and compliance alerting across multiple venues and asset classes with realistic production constraints.

## 🎯 Overview

The Risk Monitor operates exactly like a real-world institutional risk system with strict production-like constraints. It can only access external-facing APIs from exchanges, custodians, and market data providers - just like a real risk system would in production. It continuously monitors positions, P&L, exposures, and compliance violations while emitting its own telemetry for audit correlation.

### Key Features
- **Production-Realistic Constraints**: Only accesses external APIs (exchanges, custodians, market data)
- **Real-Time Risk Surveillance**: Continuous monitoring of positions, P&L, and exposures
- **Compliance Alerting**: Automated detection and escalation of risk limit breaches
- **Multi-Venue Aggregation**: Consolidated view across all trading venues and custody accounts
- **Executive Dashboard**: Real-time risk visualization and portfolio health monitoring with historical reporting
- **Risk Signal Generation**: Emits compliance status for correlation with ecosystem events
- **Delta Risk Management**: Net underlying exposure tracking and hedging recommendations
- **Drawdown Monitoring**: Real-time P&L tracking with circuit breaker capabilities
- **Audit Trail**: Complete logging of all risk decisions and compliance signals
- **Circuit Breaker Integration**: Emergency position liquidation coordination

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Risk Monitor                          │
├─────────────────────────────────────────────────────────┤
│  External Data Sources (Production-Like Access)         │
│  ├─Exchange APIs (Account balances, positions, orders)  │
│  ├─Custodian APIs (Master account balances, transfers)  │
│  ├─Market Data APIs (Real-time prices, volatility)      │
│  └─Reference Data (Instrument specs, holidays, etc.)    │
├─────────────────────────────────────────────────────────┤
│  Risk Engine                                            │
│  ├─Position Aggregator (Cross-venue position netting)   │
│  ├─P&L Calculator (Real-time mark-to-market)            │
│  ├─Delta Calculator (Net underlying exposure tracking)  │
│  ├─Limit Monitor (Compliance checking and alerting)     │
│  ├─Drawdown Monitor (Peak-to-trough tracking)           │
│  └─Circuit Breaker (Emergency position management)      │
├─────────────────────────────────────────────────────────┤
│  Compliance & Alerting                                  │
│  ├─Alert Manager (Risk breach detection and routing)    │
│  ├─Escalation Engine (Multi-tier alerting workflows)    │
│  ├─Mandate Compliance (Reporting)                       │
│  └─Audit Logger (Complete decision audit trail)         │
├─────────────────────────────────────────────────────────┤
│  Dashboard & Analytics                                  │
│  ├─Real-Time Dashboard (Live risk metrics visualization)│
│  ├─Historical Reporting (Risk trend analysis)           │
│  ├─Performance Attribution (Strategy-level analysis)    │
│  └─Risk Signal Publisher (Prometheus compliance)        │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- Docker and Docker Compose
- Poetry (for dependency management)
- Access to market data APIs

### Development Setup
```bash
# Clone the repository
git clone <repo-url>
cd risk-monitor

# Install dependencies with Poetry
poetry install

# Activate virtual environment
poetry shell

# Configure API credentials
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your API credentials

# Run tests
make test

# Start development server
make run-dev
```

### Docker Deployment
```bash
# Build container
docker build -t risk-monitor .

# Run with docker-compose (recommended)
docker-compose up risk-monitor

# Access dashboard
open http://localhost:8080

# Verify health and risk monitoring
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/risk/status
```

## 📡 API Reference

### gRPC Services

#### Risk Monitoring Service
```protobuf
service RiskMonitoringService {
  rpc GetRiskStatus(RiskStatusRequest) returns (RiskStatus);
  rpc GetPositions(GetPositionsRequest) returns (PositionsResponse);
  rpc GetPortfolioSummary(PortfolioRequest) returns (PortfolioSummary);
  rpc GetComplianceStatus(ComplianceRequest) returns (ComplianceStatus);
  rpc GetAlerts(GetAlertsRequest) returns (AlertsResponse);
}
```

#### Alert Management Service
```protobuf
service AlertManagementService {
  rpc AcknowledgeAlert(AckAlertRequest) returns (AckAlertResponse);
  rpc EscalateAlert(EscalateRequest) returns (EscalateResponse);
  rpc GetAlertHistory(AlertHistoryRequest) returns (AlertHistoryResponse);
  rpc UpdateRiskLimits(UpdateLimitsRequest) returns (UpdateLimitsResponse);
}
```

### REST Endpoints

#### Production APIs (Management & Monitoring)
```
GET    /api/v1/risk/status
GET    /api/v1/positions/summary
GET    /api/v1/portfolio/pnl
GET    /api/v1/compliance/status
GET    /api/v1/alerts/active
GET    /api/v1/limits/current
POST   /api/v1/alerts/acknowledge
POST   /api/v1/limits/update
POST   /api/v1/emergency/circuit-breaker
```

#### Dashboard APIs (Real-time Visualization)
```
GET    /api/v1/dashboard/risk-metrics
GET    /api/v1/dashboard/position-heatmap
GET    /api/v1/dashboard/pnl-attribution
GET    /api/v1/dashboard/limit-utilization
WebSocket /ws/risk-updates (Real-time risk data stream)
```

#### Reporting APIs (Historical Analysis)
```
GET    /api/v1/reports/daily-risk-summary
GET    /api/v1/reports/limit-breach-history
GET    /api/v1/reports/performance-attribution
GET    /api/v1/reports/compliance-audit-trail
```

#### State Inspection APIs (Development/Audit)
```
GET    /debug/data-sources/status
GET    /debug/risk-calculations
GET    /debug/alert-processing-queue
GET    /debug/compliance-engine-state
GET    /metrics (Prometheus format)
```

### Health & Status APIs
```
GET    /health
GET    /api/v1/system/status
GET    /api/v1/data-sources/connectivity
GET    /metrics (Prometheus format)
```

## 🏦 External Data Integration

### Exchange API Integration
```python
class ExchangeDataProvider:
    """Interfaces with exchange APIs to get account data"""
    
    def __init__(self, exchange_config: Dict[str, Any]):
        self.exchange_name = exchange_config["name"]
        self.api_client = self.create_api_client(exchange_config)
        self.rate_limiter = RateLimiter(exchange_config["rate_limits"])
    
    def get_account_balances(self, account_id: str) -> Dict[str, Balance]:
        """Get current account balances - what a real risk system sees"""
        response = self.api_client.get_account(account_id)
        return self.parse_balances(response)
    
    def get_positions(self, account_id: str) -> List[Position]:
        """Get current trading positions"""
        response = self.api_client.get_positions(account_id)
        return self.parse_positions(response)
    
    def get_order_status(self, order_ids: List[str]) -> List[OrderStatus]:
        """Get current order statuses"""
        return [self.api_client.get_order(order_id) for order_id in order_ids]
```

### Custodian API Integration
```python
class CustodianDataProvider:
    """Interfaces with custodian APIs for master account data"""
    
    def get_master_balances(self, client_id: str) -> Dict[str, Balance]:
        """Get master account balances from custodian"""
        response = self.custodian_client.get_master_account(client_id)
        return self.parse_master_balances(response)
    
    def get_settlement_status(self, settlement_ids: List[str]) -> List[SettlementStatus]:
        """Check status of pending settlements"""
        return [self.custodian_client.get_settlement(sid) for sid in settlement_ids]
    
    def get_segregated_balances(self, client_id: str) -> Dict[str, Balance]:
        """Get segregated client asset balances"""
        response = self.custodian_client.get_segregated_accounts(client_id)
        return self.parse_segregated_balances(response)
```

### Market Data Integration
```python
class MarketDataProvider:
    """Interfaces with market data APIs for pricing"""
    
    def get_current_prices(self, symbols: List[str]) -> Dict[str, Price]:
        """Get current market prices for risk calculations"""
        return {symbol: self.price_client.get_price(symbol) for symbol in symbols}
    
    def get_volatility_data(self, symbols: List[str]) -> Dict[str, float]:
        """Get current volatility estimates for VAR calculations"""
        return {symbol: self.calc_realized_volatility(symbol) for symbol in symbols}
```

## 📊 Risk Calculation Engine

### Position Aggregation
```python
class PositionAggregator:
    """Aggregates positions across all venues and accounts"""
    
    def calculate_net_positions(self) -> Dict[str, NetPosition]:
        """Calculate net positions across all venues"""
        all_positions = {}
        
        # Gather positions from all exchanges
        for exchange in self.exchanges:
            exchange_positions = exchange.get_positions()
            for symbol, position in exchange_positions.items():
                if symbol not in all_positions:
                    all_positions[symbol] = NetPosition(symbol=symbol)
                all_positions[symbol].add_venue_position(exchange.name, position)
        
        # Add custodian holdings
        custodian_balances = self.custodian.get_master_balances()
        for asset, balance in custodian_balances.items():
            symbol = f"{asset}-USD"  # Convert to trading symbol
            if symbol not in all_positions:
                all_positions[symbol] = NetPosition(symbol=symbol)
            all_positions[symbol].add_custodian_balance(balance)
        
        return all_positions
```

### P&L Calculation
```python
class PnLCalculator:
    """Real-time P&L calculation and attribution"""
    
    def calculate_realtime_pnl(self) -> PortfolioPnL:
        """Calculate current portfolio P&L using real-time prices"""
        positions = self.position_aggregator.get_net_positions()
        current_prices = self.market_data.get_current_prices(list(positions.keys()))
        
        total_unrealized_pnl = 0.0
        position_pnl = {}
        
        for symbol, position in positions.items():
            if position.size != 0:
                current_price = current_prices.get(symbol, position.avg_price)
                unrealized_pnl = (current_price - position.avg_price) * position.size
                position_pnl[symbol] = unrealized_pnl
                total_unrealized_pnl += unrealized_pnl
        
        # Add realized P&L from completed trades
        realized_pnl = self.get_realized_pnl_today()
        
        return PortfolioPnL(
            total_pnl=total_unrealized_pnl + realized_pnl,
            unrealized_pnl=total_unrealized_pnl,
            realized_pnl=realized_pnl,
            position_breakdown=position_pnl
        )
```

### Delta Risk Calculation
```python
class DeltaRiskCalculator:
    """Calculate net underlying exposure (delta) across all positions"""
    
    def calculate_portfolio_delta(self) -> Dict[str, float]:
        """Calculate net underlying asset exposure"""
        positions = self.position_aggregator.get_net_positions()
        deltas = {}
        
        for symbol, position in positions.items():
            if position.size == 0:
                continue
                
            # Parse symbol to get underlying assets
            base_asset, quote_asset = self.parse_symbol(symbol)
            
            # Calculate delta exposure to each underlying
            if base_asset not in deltas:
                deltas[base_asset] = 0.0
            if quote_asset not in deltas:
                deltas[quote_asset] = 0.0
            
            # Long position = long base asset, short quote asset
            current_price = self.market_data.get_current_price(symbol)
            deltas[base_asset] += position.size
            deltas[quote_asset] -= position.size * current_price
        
        return deltas
```

## 🚨 Compliance & Alerting System

### Risk Limit Configuration
```yaml
# risk_limits.yaml
risk_limits:
  position_limits:
    BTC-USD:
      max_long_notional: 5000000    # $5M max long exposure
      max_short_notional: 2500000   # $2.5M max short exposure
      concentration_limit: 0.30     # Max 30% of portfolio
      warn_at_utilization: 0.8
  
    ETH-USD:
      max_long_notional: 3000000    # $3M max long exposure
      max_short_notional: 1500000   # $1.5M max short exposure
      concentration_limit: 0.25     # Max 25% of portfolio
      warn_at_utilization: 0.8

  portfolio_limits:
    max_total_notional: 10000000    # $10M total exposure limit
    max_daily_loss: 500000          # $500K max daily loss
    max_drawdown_pct: 0.15          # 15% max drawdown from HWM
    max_var_99: 750000              # $750K max 1-day VaR
    max_leverage_ratio: 3.0         # 3:1 max leverage

  notional_limits:
    total_portfolio: 10000000  # $10M total notional
    per_symbol: 2000000       # $2M per symbol
    warn_at_utilization: 0.75

  delta_limits:
    BTC:
      max_net_exposure: 15.0    # Max 15 BTC net exposure
    ETH:
      max_net_exposure: 250.0   # Max 250 ETH net exposure
    USD:
      max_net_exposure: 5000000 # Max $5M USD net exposure

  drawdown_limits:
    daily_loss: -500000        # Max $500k daily loss
    max_drawdown: -0.15        # Max 15% drawdown from peak
    trailing_stop_pct: 0.10    # 10% trailing stop

  circuit_breakers:
    portfolio_loss_threshold: -1000000  # $1M total loss
    rapid_drawdown_threshold: -250000   # $250k in 10 minutes
    critical_alert_threshold: 5         # 5 critical alerts
    recovery_time_minutes: 60           # Circuit reset time

  operational_limits:
    position_staleness_minutes: 5   # Alert if position data >5min old
    pnl_calculation_frequency: 30   # Calculate P&L every 30 seconds
    alert_escalation_minutes: 10    # Escalate unacked alerts after 10min

alert_configuration:
  severity_thresholds:
    low: 0.5      # 50% of limit utilization
    medium: 0.75  # 75% of limit utilization
    high: 0.90    # 90% of limit utilization
    critical: 1.0 # Limit exceeded

  escalation_rules:
    high_severity:
      initial_notification: ["risk_team"]
      escalation_delay_minutes: 15
      escalate_to: ["head_of_trading", "cro"]
    critical_severity:
      initial_notification: ["risk_team", "head_of_trading"]
      escalation_delay_minutes: 5
      escalate_to: ["ceo", "board"]
```

### Risk Limit Monitoring
```python
class RiskLimitMonitor:
    """Monitors positions against configured risk limits"""
    
    def __init__(self, limits_config: Dict[str, Any]):
        self.position_limits = limits_config["position_limits"]
        self.notional_limits = limits_config["notional_limits"]
        self.delta_limits = limits_config["delta_limits"]
        self.drawdown_limits = limits_config["drawdown_limits"]
    
    def check_all_limits(self) -> List[RiskBreach]:
        """Check all risk limits and return any breaches"""
        breaches = []
        
        # Check position limits
        positions = self.position_aggregator.get_net_positions()
        breaches.extend(self.check_position_limits(positions))
        
        # Check notional limits
        notional_exposure = self.calculate_notional_exposure(positions)
        breaches.extend(self.check_notional_limits(notional_exposure))
        
        # Check delta limits
        deltas = self.delta_calculator.calculate_portfolio_delta()
        breaches.extend(self.check_delta_limits(deltas))
        
        # Check drawdown limits
        pnl = self.pnl_calculator.calculate_realtime_pnl()
        breaches.extend(self.check_drawdown_limits(pnl))
        
        return breaches
    
    def check_position_limits(self, positions: Dict[str, NetPosition]) -> List[RiskBreach]:
        """Check individual position size limits"""
        breaches = []
        for symbol, position in positions.items():
            if symbol in self.position_limits:
                limits = self.position_limits[symbol]
                if position.size > limits["max_long"]:
                    breaches.append(RiskBreach(
                        breach_type="position_limit_long",
                        symbol=symbol,
                        current_value=position.size,
                        limit_value=limits["max_long"],
                        severity=self.calculate_breach_severity(position.size, limits["max_long"])
                    ))
                elif position.size < limits["max_short"]:
                    breaches.append(RiskBreach(
                        breach_type="position_limit_short",
                        symbol=symbol,
                        current_value=position.size,
                        limit_value=limits["max_short"],
                        severity=self.calculate_breach_severity(position.size, limits["max_short"])
                    ))
        return breaches
```

### Alert Management System
```python
class AlertManager:
    """Manages risk alert generation, routing, and escalation"""
    
    def __init__(self, alert_config: Dict[str, Any]):
        self.alert_config = alert_config
        self.active_alerts = {}
        self.alert_history = []
        self.escalation_engine = EscalationEngine(alert_config["escalation"])
    
    def process_risk_breach(self, breach: RiskBreach) -> Alert:
        """Process a risk limit breach and generate appropriate alert"""
        alert = Alert(
            alert_id=self.generate_alert_id(),
            breach=breach,
            timestamp=datetime.utcnow(),
            severity=breach.severity,
            status=AlertStatus.ACTIVE
        )
        
        # Store active alert
        self.active_alerts[alert.alert_id] = alert
        
        # Route alert based on severity and type
        self.route_alert(alert)
        
        # Log for audit trail
        self.audit_logger.log_alert_generated(alert)
        
        # Emit compliance signal for audit correlation
        self.emit_compliance_signal(alert)
        
        return alert
    
    def emit_compliance_signal(self, alert: Alert):
        """Emit compliance signal for audit correlator to pick up"""
        compliance_signal = ComplianceSignal(
            signal_type="risk_alert_generated",
            timestamp=alert.timestamp,
            severity=alert.severity.name,
            breach_type=alert.breach.breach_type,
            symbol=alert.breach.symbol,
            limit_exceeded=alert.breach.current_value > alert.breach.limit_value
        )
        
        # Publish to metrics for audit correlator
        self.metrics_publisher.publish_compliance_signal(compliance_signal)
```

### Circuit Breaker System
```python
class CircuitBreaker:
    """Emergency position management and trading halt capabilities"""
    
    def __init__(self, circuit_config: Dict[str, Any]):
        self.circuit_config = circuit_config
        self.circuit_state = CircuitState.CLOSED
        self.emergency_contacts = circuit_config["emergency_contacts"]
    
    def evaluate_circuit_conditions(self, pnl: PortfolioPnL, alerts: List[Alert]) -> bool:
        """Evaluate whether circuit breaker should be triggered"""
        
        # Check portfolio loss circuit breaker
        if pnl.total_pnl < self.circuit_config["portfolio_loss_threshold"]:
            self.trigger_circuit_breaker("portfolio_loss_limit", pnl.total_pnl)
            return True
        
        # Check rapid drawdown circuit breaker
        recent_pnl_change = self.calculate_recent_pnl_change()
        if recent_pnl_change < self.circuit_config["rapid_drawdown_threshold"]:
            self.trigger_circuit_breaker("rapid_drawdown", recent_pnl_change)
            return True
        
        # Check critical alert count
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        if len(critical_alerts) >= self.circuit_config["critical_alert_threshold"]:
            self.trigger_circuit_breaker("critical_alert_cascade", len(critical_alerts))
            return True
        
        return False
    
    def trigger_circuit_breaker(self, reason: str, trigger_value: float):
        """Trigger emergency circuit breaker"""
        self.circuit_state = CircuitState.OPEN
        
        # Send emergency notification
        self.send_emergency_notification(reason, trigger_value)
        
        # Log circuit breaker activation
        self.audit_logger.log_circuit_breaker_triggered(reason, trigger_value)
        
        # Emit critical compliance signal
        self.emit_critical_compliance_signal(reason, trigger_value)
```

## 📈 Risk Dashboard & Visualization

### Real-Time Dashboard Server
```python
class RiskDashboardServer:
    """Serves real-time risk dashboard and WebSocket updates"""
    
    def __init__(self):
        self.flask_app = Flask(__name__)
        self.socketio = SocketIO(self.flask_app)
        self.setup_routes()
        self.setup_websocket_handlers()
    
    def setup_routes(self):
        @self.flask_app.route('/dashboard')
        def risk_dashboard():
            return render_template('risk_dashboard.html')
        
        @self.flask_app.route('/api/v1/dashboard/risk-metrics')
        def get_risk_metrics():
            return jsonify(self.get_current_risk_metrics())
    
    def broadcast_risk_update(self, risk_data: Dict[str, Any]):
        """Broadcast real-time risk updates to dashboard clients"""
        self.socketio.emit('risk_update', risk_data, namespace='/risk')
    
    def get_current_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics for dashboard display"""
        positions = self.position_aggregator.get_net_positions()
        pnl = self.pnl_calculator.calculate_realtime_pnl()
        deltas = self.delta_calculator.calculate_portfolio_delta()
        active_alerts = list(self.alert_manager.active_alerts.values())
        
        return {
            "positions": self.format_positions_for_dashboard(positions),
            "pnl": self.format_pnl_for_dashboard(pnl),
            "deltas": deltas,
            "alerts": self.format_alerts_for_dashboard(active_alerts),
            "limit_utilization": self.calculate_limit_utilization(),
            "timestamp": datetime.utcnow().isoformat()
        }
```

### Dashboard Metrics Configuration
```yaml
# dashboard_config.yaml
dashboard:
  refresh_interval_seconds: 5
  charts:
    pnl_chart:
      timeframe: "24h"
      intervals: ["1m", "5m", "15m", "1h"]
    
    position_heatmap:
      grouping: "asset_class"
      color_scheme: "red_green"
      size_metric: "notional_value"
    
    alert_timeline:
      max_alerts: 50
      severity_colors:
        critical: "#ff0000"
        high: "#ff8800"
        medium: "#ffaa00"
        low: "#ffcc00"

  limits_display:
    show_utilization_percentage: true
    warn_at_utilization: 0.75
    alert_at_utilization: 0.90
```

### Portfolio Visualization
```python
def render_pnl_chart(self):
    """Real-time P&L chart"""
    st.subheader("P&L Timeline")
    
    pnl_history = self.risk_monitor.get_pnl_history(hours=24)
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Total P&L', 'Daily P&L'),
        vertical_spacing=0.1
    )
    
    # Total P&L line
    fig.add_trace(
        go.Scatter(
            x=pnl_history.timestamp,
            y=pnl_history.total_pnl,
            mode='lines',
            name='Total P&L',
            line=dict(color='blue', width=2)
        ),
        row=1, col=1
    )
    
    # Daily P&L bar chart
    fig.add_trace(
        go.Bar(
            x=pnl_history.timestamp,
            y=pnl_history.daily_pnl,
            name='Daily P&L',
            marker_color=['red' if x < 0 else 'green' for x in pnl_history.daily_pnl]
        ),
        row=2, col=1
    )
    
    fig.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
```


## 📊 Risk Signal Generation
### Compliance Signal Emission
```python
class RiskSignalPublisher:
    """Publishes risk compliance signals for audit correlation"""
    
    def __init__(self):
        self.prometheus_client = PrometheusClient()
        self.signal_history = []
    
    def emit_compliance_signal(self, alert: RiskAlert):
        """Emit compliance signal for audit correlation"""
        
        signal = ComplianceSignal(
            timestamp=datetime.utcnow(),
            signal_type="risk_alert_generated",
            severity=alert.severity,
            alert_type=alert.alert_type,
            current_value=alert.current_value,
            limit_value=alert.limit_value,
            breach_percentage=alert.breach_percentage,
            affected_assets=alert.affected_assets
        )
        
        # Publish to Prometheus for audit correlation
        self.prometheus_client.increment_counter(
            "risk_alert_generated_total",
            labels={
                "severity": alert.severity.value,
                "alert_type": alert.alert_type,
                "asset": ",".join(alert.affected_assets)
            }
        )
        
        # Emit structured log for audit trail
        self.emit_compliance_log(signal)
        
        self.signal_history.append(signal)
    
    def emit_limit_compliance_status(self, risk_snapshot: RiskSnapshot):
        """Emit regular compliance status signals"""
        
        for limit_name, compliance_status in risk_snapshot.compliance_status.items():
            self.prometheus_client.set_gauge(
                "risk_limit_utilization",
                compliance_status.utilization_percentage,
                labels={
                    "limit_type": limit_name,
                    "status": compliance_status.status
                }
            )
```

## 📊 Monitoring & Observability

### Prometheus Metrics (Compliance Signals)
```python
# Risk Monitor's own compliance signals for audit correlation
risk_compliance_status = Gauge('risk_compliance_status', 'Risk compliance status', ['mandate', 'symbol'])
risk_alert_generated = Counter('risk_alert_generated', 'Risk alerts generated', ['severity', 'breach_type'])
risk_limit_utilization = Gauge('risk_limit_utilization', 'Risk limit utilization ratio', ['limit_type', 'symbol'])
risk_position_size = Gauge('risk_position_size', 'Current position sizes', ['symbol', 'venue'])
risk_portfolio_pnl = Gauge('risk_portfolio_pnl', 'Current portfolio P&L', ['currency'])
risk_delta_exposure = Gauge('risk_delta_exposure', 'Net underlying exposure', ['asset'])
risk_drawdown = Gauge('risk_drawdown', 'Portfolio drawdown from peak', ['timeframe'])
risk_circuit_breaker = Counter('risk_circuit_breaker_triggered', 'Circuit breaker activations', ['reason'])
risk_monitor_latency = Histogram('risk_monitor_latency_seconds', 'Risk calculation latency', ['calculation_type'])
risk_data_staleness = Gauge('risk_data_staleness_seconds', 'Age of risk data', ['data_source'])
```

### Audit Trail Logging
```json
{
  "timestamp": "2025-09-16T14:23:45.123Z",
  "level": "warn",
  "service": "risk-monitor",
  "correlation_id": "risk-check-001",
  "event": "risk_limit_breach",
  "breach_type": "position_limit_long",
  "symbol": "BTC-USD",
  "current_position": 12.5,
  "position_limit": 10.0,
  "breach_severity": "high",
  "alert_id": "alert-456789",
  "compliance_action": "alert_generated",
  "audit_trail": {
    "data_sources_checked": ["exchange-1", "exchange-2", "custodian-1"],
    "calculation_method": "net_position_aggregation",
    "price_timestamp": "2025-09-16T14:23:40.000Z",
    "risk_engine_version": "2.1.3"
  }
}
```

## 🧪 Testing

### Risk Calculation Testing
```python
class TestRiskCalculations(unittest.TestCase):
    def setUp(self):
        self.risk_monitor = RiskMonitor(test_config)
        self.mock_exchanges = create_mock_exchanges()
        self.mock_custodian = create_mock_custodian()
    
    def test_position_aggregation_accuracy(self):
        """Test that positions are correctly aggregated across venues"""
        # Set up mock positions across multiple exchanges
        self.mock_exchanges['exchange-1'].set_position('BTC-USD', 5.0)
        self.mock_exchanges['exchange-2'].set_position('BTC-USD', -2.5)
        
        # Calculate net position
        net_positions = self.risk_monitor.position_aggregator.get_net_positions()
        
        # Verify correct aggregation
        self.assertEqual(net_positions['BTC-USD'].size, 2.5)
    
    def test_limit_breach_detection(self):
        """Test risk limit breach detection accuracy"""
        # Set position that exceeds limits
        self.mock_exchanges['exchange-1'].set_position('BTC-USD', 15.0)  # Limit is 10.0
        
        # Check for breaches
        breaches = self.risk_monitor.limit_monitor.check_all_limits()
        
        # Verify breach detected
        self.assertEqual(len(breaches), 1)
        self.assertEqual(breaches[0].breach_type, 'position_limit_long')
```

### Integration Testing
```bash
# Test with mock external APIs
make test-integration

# Test alert routing and escalation
make test-alert-system

# Test circuit breaker functionality
make test-circuit-breaker

# Test dashboard real-time updates
make test-dashboard-websockets
```

## ⚙️ Configuration

### Environment Variables
```bash
# Core settings
RISK_MONITOR_PORT=8080
RISK_MONITOR_GRPC_PORT=50055
RISK_MONITOR_LOG_LEVEL=info

# External API configuration
EXCHANGE_API_KEYS='{"exchange-1": "key1", "exchange-2": "key2"}'
CUSTODIAN_API_KEY=your_custodian_api_key
MARKET_DATA_API_KEY=your_market_data_key

# Risk monitoring settings
RISK_CHECK_INTERVAL_SECONDS=5
ALERT_RETENTION_DAYS=90
CIRCUIT_BREAKER_ENABLED=true
DASHBOARD_ENABLED=true

# Compliance settings
EMIT_COMPLIANCE_SIGNALS=true
AUDIT_LOG_RETENTION_DAYS=365
REGULATORY_REPORTING_ENABLED=true
```

### Risk Monitor Configuration
```yaml
# risk_monitor_config.yaml
monitoring:
  calculation_frequency_seconds: 30
  position_staleness_threshold_minutes: 5
  pnl_precision_decimals: 8
  
external_apis:
  exchanges:
    - name: "exchange-simulator-1"
      base_url: "http://exchange-simulator:8080"
      api_key: "${EXCHANGE_1_API_KEY}"
      timeout_seconds: 10
      retry_attempts: 3
  
  custodians:
    - name: "custodian-simulator"
      base_url: "http://custodian-simulator:8081"
      api_key: "${CUSTODIAN_API_KEY}"
      settlement_check_frequency_minutes: 60

dashboard:
  title: "Trading Risk Monitor"
  refresh_interval_seconds: 5
  chart_history_hours: 24
  alert_sound_enabled: true
  
  layout:
    show_portfolio_overview: true
    show_position_details: true
    show_pnl_chart: true
    show_risk_metrics: true
    show_active_alerts: true

alerting:
  escalation_delay_minutes: 10
  max_alerts_per_hour: 50
  alert_channels:
    - type: "prometheus"
      enabled: true
    - type: "webhook"
      url: "${ALERT_WEBHOOK_URL}"
      enabled: false
```

### Risk Limits Configuration
```yaml
# risk_limits.yaml
risk_limits:
  position_limits:
    BTC-USD:
      max_long: 10.0
      max_short: -5.0
      warn_at_utilization: 0.8
    ETH-USD:
      max_long: 200.0
      max_short: -100.0
      warn_at_utilization: 0.8
  
  notional_limits:
    total_portfolio: 10000000  # $10M total notional
    per_symbol: 2000000       # $2M per symbol
    warn_at_utilization: 0.75
  
  delta_limits:
    BTC: 
      max_net_exposure: 15.0    # Max 15 BTC net exposure
    ETH:
      max_net_exposure: 250.0   # Max 250 ETH net exposure
    USD:
      max_net_exposure: 5000000 # Max $5M USD net exposure
  
  drawdown_limits:
    daily_loss: -500000        # Max $500k daily loss
    max_drawdown: -0.15        # Max 15% drawdown from peak
    trailing_stop_pct: 0.10    # 10% trailing stop
  
  circuit_breakers:
    portfolio_loss_threshold: -1000000  # $1M total loss
    rapid_drawdown_threshold: -250000   # $250k in 10 minutes
    critical_alert_threshold: 5         # 5 critical alerts
    recovery_time_minutes: 60           # Circuit reset time

alert_configuration:
  severity_thresholds:
    low: 0.5      # 50% of limit utilization
    medium: 0.75  # 75% of limit utilization  
    high: 0.90    # 90% of limit utilization
    critical: 1.0 # Limit exceeded
  
  escalation_rules:
    high_severity:
      initial_notification: ["risk_team"]
      escalation_delay_minutes: 15
      escalate_to: ["head_of_trading", "cro"]
    critical_severity:
      initial_notification: ["risk_team", "head_of_trading"]
      escalation_delay_minutes: 5
      escalate_to: ["ceo", "board"]
```

## 🐳 Docker Configuration

### Dockerfile
```dockerfile
FROM python:3.13-slim as builder

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry export -f requirements.txt --output requirements.txt

FROM python:3.13-slim
WORKDIR /app

# Install system dependencies for financial calculations
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

# Expose ports for API and dashboard
EXPOSE 8080 50055

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8084/health').raise_for_status()"

CMD ["python", "-m", "risk_monitor.main"]
```

### Health Checks
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/health').raise_for_status()"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

## 🔒 Security & Compliance

### API Security
- **Secure Credential Storage**: API keys stored in environment variables or secret management
- **Rate Limit Respect**: Automatic rate limiting for external API calls
- **Connection Security**: TLS encryption for all external API communications
- **Audit Logging**: Complete logging of all external API calls and responses

### Regulatory Compliance
- **Audit Trail**: Complete audit trail of all risk decisions and compliance actions
- **Data Retention**: Configurable data retention policies for compliance requirements
- **Reporting**: Automated generation of regulatory risk reports
- **Compliance Signals**: Structured compliance events for audit correlation

## 🚀 Performance

### Benchmarks
- **Risk Calculation Latency**: <100ms for complete portfolio risk assessment
- **Alert Generation**: <50ms from breach detection to alert routing
- **Dashboard Updates**: <5 second end-to-end risk data refresh
- **External API Response**: <2 seconds for all venue data aggregation

### Resource Usage
- **Memory**: ~300MB baseline + ~50MB per monitored venue
- **CPU**: <30% single core under normal monitoring load
- **Network**: <5MB/hour external API calls
- **Disk**: <50MB logs per day

## 🤝 Contributing

### Development Guidelines
1. Maintain production-realistic constraints (external API access only)
2. Ensure all risk calculations are auditable and explainable
3. Add comprehensive logging for compliance requirements
4. Test with realistic market scenarios and edge cases
5. Document all compliance signals and their meanings

### Adding New Risk Metrics
1. Implement calculation logic with proper error  RiskMetricsCalculator
2. Add corresponding alert logic in ComplianceEngine
3. Update dashboard visualization components
4. Add Prometheus metrics for audit correlation
5. Include comprehensive unit and integration tests

## 📚 References
- **Risk Management Standards**: [Link to institutional risk management practices]
- **Regulatory Requirements**: [Link to compliance documentation]
- **API Integration Guide**: [Link to exchange/custodian API documentation]
- **Dashboard Development**: [Link to Streamlit/Dash development guides]


**Status**: 🚧 Development Phase
**Maintainer**: [Your team]
**Last Updated**: September 2025
