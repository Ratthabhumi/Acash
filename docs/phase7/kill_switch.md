# Phase 7: Kill Switch Engine & Safety Action Matrix

## 1. Overview & Core Safety Invariants
In Phase 7, the Kill Switch is a **First-Class Event Engine** with deterministic triggers, immutable event logging, and fail-closed operational halts.

### The Halt vs. Flatten Invariant
$$\boxed{\text{HALT\_NEW\_ORDERS} \neq \text{POSITION\_FLATTEN}}$$
* **Halt**: Immediately ceases all risk-increasing order submissions and cancels open working orders.
* **Flatten**: Aggressively liquidates existing market positions.
* **Core Rule**: Never blindly market-close open positions upon feed failures or disconnections, as blind liquidation during market data blackouts or illiquid periods can create catastrophic slippage and double execution.

---

## 2. Trigger-to-Action Safety Matrix

| Trigger Type | Cause Condition | Authorization Effect | Order Effect | Position Effect | Remediation Next Step |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`STALE_MARKET_DATA`** | Feed tick age $> 1500\text{ms}$ | `SUSPENDED` | Cancel open working limit orders | **HOLD POSITIONS** (Do NOT market close) | Wait for nominal feed restore or manual operator inspection |
| **`MAX_DAILY_LOSS`** | Daily Loss $\ge \text{Limit}$ | `SUSPENDED` | Cancel all working orders | **CONTROLLED DE-RISK** (Passive limit close or risk-managed exit) | Strategy locked until daily settlement reset |
| **`MAX_DRAWDOWN`** | Cumulative DD $\ge \text{Limit}$ | `REVOKED` | Cancel all working orders | **EMERGENCY DE-RISK** (Orderly close) | Permanent revocation; requires risk committee re-authorization |
| **`BROKER_DISCONNECTED`** | WebSocket/FIX heartbeat lost | `SUSPENDED` | Flag working orders as **`UNKNOWN`** | **HOLD & FREEZE** (Do not assume cancel worked) | Immediate Reconciliation Engine query upon reconnection |
| **`RECONCILIATION_FAILURE`** | Shadow vs Broker mismatch | `SUSPENDED` | Cancel all working orders | **FREEZE POSITIONS** | Raise critical incident; operator investigation required |
| **`CLOCK_SKEW_DETECTED`** | Host clock drift $> 500\text{ms}$ | `SUSPENDED` | Cancel open working orders | **HOLD POSITIONS** | Resync local NTP time before re-authorizing |
| **`MANUAL_HALT`** | Operator kill button pressed | `SUSPENDED` | Cancel all working orders | Operator-specified (HOLD or CLOSE) | Manual re-authorization required |

---

## 3. Kill Switch Event Schema

```python
class KillSwitchAction(str, Enum):
    HALT_NEW_ORDERS = "HALT_NEW_ORDERS"
    CANCEL_WORKING_ORDERS = "CANCEL_WORKING_ORDERS"
    CONTROLLED_DERISK = "CONTROLLED_DERISK"
    EMERGENCY_FLATTEN = "EMERGENCY_FLATTEN"
    FREEZE_AND_RECONCILE = "FREEZE_AND_RECONCILE"

class KillSwitchTriggerType(str, Enum):
    STALE_MARKET_DATA = "STALE_MARKET_DATA"
    MAX_DAILY_LOSS = "MAX_DAILY_LOSS"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    BROKER_DISCONNECTED = "BROKER_DISCONNECTED"
    RECONCILIATION_FAILURE = "RECONCILIATION_FAILURE"
    CLOCK_SKEW_DETECTED = "CLOCK_SKEW_DETECTED"
    MARKET_CLOSED = "MARKET_CLOSED"
    MANUAL_HALT = "MANUAL_HALT"

class KillSwitchEvent(BaseModel):
    """Immutable forensic event emitted upon automated or manual emergency halt."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(description="Unique deterministic kill switch event ID.")
    triggered_at: datetime = Field(description="UTC timestamp of emergency halt.")
    trigger_type: KillSwitchTriggerType = Field(description="Cause of emergency halt.")
    severity: str = Field(description="'CRITICAL' or 'FATAL'.")
    
    observed_metric_value: str = Field(description="Observed metric (e.g. 'drawdown=3.2%', 'feed_age=2500ms').")
    threshold_limit_value: str = Field(description="Configured limit threshold that was breached.")
    
    affected_strategies: Tuple[str, ...] = Field(description="Strategy IDs halted (or 'ALL').")
    primary_action: KillSwitchAction = Field(description="Primary immediate safety action.")
    position_action: KillSwitchAction = Field(description="Prescribed action on open positions.")
    actor: str = Field(description="'SYSTEM_AUTOMATED_RISK_GATE' or 'OPERATOR_<ID>'.")
    
    event_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of canonical kill event.")
```
