# Phase 7: Dynamic Risk State Specification

## 1. Overview & Risk State Machine
The `RiskState` tracks real-time portfolio health, exposure, value-at-risk, drawdown, and connectivity status. It transitions across 4 operational states:

```text
[ NORMAL ] ──► (Warning Breach) ──► [ WARNING ]
    │                                     │
    │ (Limit Breach / High Risk)          │ (Further Degradation)
    ▼                                     ▼
[ RESTRICTED ] (De-risk only) ──► [ HALTED ] (Emergency Kill Switch)
```

### State Definitions
1. `NORMAL`: Strategy operates with full order submission privileges within authorized bounds.
2. `WARNING`: Near limit boundary (e.g. $>80\%$ of daily loss limit). Telemetry alerts emitted; order rates throttled.
3. `RESTRICTED`: Position reduction / close-only orders allowed. No risk-increasing orders accepted.
4. `HALTED`: Complete execution freeze. All active orders canceled immediately; new orders rejected fail-closed.

---

## 2. Risk State Schema

```python
class RiskStatus(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    RESTRICTED = "RESTRICTED"
    HALTED = "HALTED"

class RiskState(BaseModel):
    """Dynamic, real-time snapshot of live risk and portfolio health."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime = Field(description="UTC timestamp of risk evaluation.")
    authorization_id: str = Field(description="Associated LiveAuthorization ID.")
    strategy_id: str = Field(description="Target strategy identifier.")
    
    # Financial State
    total_equity: Decimal = Field(description="Current mark-to-market equity.")
    realized_pnl_today: Decimal = Field(description="Realized PnL since daily reset.")
    unrealized_pnl: Decimal = Field(description="Floating unrealized PnL.")
    current_drawdown_pct: Decimal = Field(ge=0, le=100, description="Peak-to-trough drawdown percentage.")
    
    # Exposure & Capital
    gross_exposure_notional: Decimal = Field(ge=0, description="Total gross notional exposure.")
    net_exposure_notional: Decimal = Field(description="Net directional notional exposure.")
    concentration_ratio: Decimal = Field(ge=0, le=1, description="Largest position notional / total equity.")
    
    # Quantitative Risk Metrics
    parametric_var_95: Decimal = Field(ge=0, description="1-day 95% Value at Risk.")
    historical_cvar_95: Decimal = Field(ge=0, description="1-day 95% Conditional Value at Risk.")
    
    # Environmental & Operational Flags
    is_market_data_stale: bool = Field(description="True if last market tick exceeds staleness threshold.")
    is_broker_connected: bool = Field(description="True if gateway WebSocket/FIX session is active.")
    is_clock_skew_detected: bool = Field(description="True if local vs gateway timestamp exceeds threshold.")
    
    risk_status: RiskStatus = Field(description="Active operational risk status.")
    active_kill_switch_event_id: Optional[str] = Field(default=None, description="Linked KillSwitchEvent if HALTED.")
```
