# Phase 7: Dynamic Risk State & Epistemic Risk Invariants

## 1. Overview & The Epistemic Risk Principle
$$\boxed{\text{MODELLED RISK} \neq \text{ACTUAL RISK}}$$

In Phase 7, calculated risk metrics (e.g. Parametric VaR, CVaR) are explicitly declared as **modelled estimates** subject to estimation windows, model versions, and data latency. They must never be treated as omniscient future truth.

### The Staleness Invariant
> **"If risk calculation inputs are stale, missing, or contradictory, RiskState MUST transition to `UNKNOWN` $\implies$ immediately `HALT NEW ORDERS`."**
> 
> Never display last-known risk numbers as current ground truth when market feeds are stale.

---

## 2. Risk State Machine

```text
[ NORMAL ] ──► (Warning Threshold) ──► [ WARNING ]
    │                                         │
    │ (Limit Breach / High Risk)              │ (Further Degradation)
    ▼                                         ▼
[ RESTRICTED ] (De-risk only) ──────► [ HALTED ] (Kill Switch Engaged)
```

---

## 3. Dynamic Risk State Schema

```python
class CalculationStatus(str, Enum):
    NOMINAL = "NOMINAL"       # Up-to-date data, fully converged calculation
    DEGRADED = "DEGRADED"     # Partial feed coverage; conservative fallbacks active
    STALE = "STALE"           # Feed age exceeds freshness threshold
    UNKNOWN = "UNKNOWN"       # Calculation failed or data unavailable (Triggers HALT)

class RiskStatus(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    RESTRICTED = "RESTRICTED"
    HALTED = "HALTED"

class RiskState(BaseModel):
    """Dynamic, real-time snapshot of live risk and portfolio health."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime = Field(description="UTC timestamp of risk snapshot.")
    authorization_id: str = Field(description="Associated LiveAuthorization ID.")
    strategy_id: str = Field(description="Target strategy identifier.")
    
    # Financial Balances & PnL
    total_equity: Decimal = Field(description="Current mark-to-market equity.")
    realized_pnl_today: Decimal = Field(description="Realized PnL since daily reset.")
    unrealized_pnl: Decimal = Field(description="Floating unrealized PnL.")
    current_drawdown_pct: Decimal = Field(ge=0, le=100, description="Peak-to-trough drawdown percentage.")
    
    # Exposure & Sizing
    gross_exposure_notional: Decimal = Field(ge=0, description="Total gross notional exposure.")
    net_exposure_notional: Decimal = Field(description="Net directional notional exposure.")
    concentration_ratio: Decimal = Field(ge=0, le=1, description="Largest position notional / total equity.")
    
    # Quantitative Risk Estimates & Epistemic Metadata
    parametric_var_95: Decimal = Field(ge=0, description="1-day 95% Value at Risk (Modelled estimate).")
    historical_cvar_95: Decimal = Field(ge=0, description="1-day 95% Conditional Value at Risk (Modelled estimate).")
    confidence_level: float = Field(default=0.95, description="Statistical confidence level.")
    estimation_window_bars: int = Field(default=252, description="Lookback bar horizon used for covariance/VaR.")
    risk_model_version: str = Field(default="PARAMETRIC_GAUSSIAN_HURDLE_V1", description="Active risk model version.")
    
    # Data Freshness & Environmental Telemetry
    data_timestamp: datetime = Field(description="Timestamp of newest tick used in calculation.")
    data_age_ms: int = Field(ge=0, description="Age of newest input tick in milliseconds.")
    calculation_status: CalculationStatus = Field(description="Integrity status of risk calculation.")
    
    is_market_data_stale: bool = Field(description="True if data_age_ms exceeds staleness threshold.")
    is_broker_connected: bool = Field(description="True if gateway WebSocket/FIX session is active.")
    is_clock_skew_detected: bool = Field(description="True if local vs gateway timestamp exceeds threshold.")
    
    risk_status: RiskStatus = Field(description="Active operational risk status.")
    active_kill_switch_event_id: Optional[str] = Field(default=None, description="Linked KillSwitchEvent if HALTED.")
```
