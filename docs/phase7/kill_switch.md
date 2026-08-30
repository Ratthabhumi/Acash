# Phase 7: Kill Switch Engine Specification

## 1. Overview & First-Class Event Model
In Phase 7, the Kill Switch is not a casual `if` statement buried in routing logic. It is a **First-Class Event Engine** with deterministic triggers, immutable event logging, and fail-closed operational halts.

```text
[ Trigger Condition Detected ]
               │
               ▼
[ KillSwitchEngine Evaluates Invariants ]
               │
               ▼
[ KillSwitchEvent Emitted (Digest Sealed) ]
               │
      ┌────────┴────────┐
      ▼                 ▼
[ Cancel Working ]  [ Invalidate Live ]
[ Active Orders  ]  [ Authorizations  ]
```

---

## 2. Trigger Taxonomies

```python
class KillSwitchTriggerType(str, Enum):
    STALE_MARKET_DATA = "STALE_MARKET_DATA"        # Feed heartbeat exceeded max age (e.g. > 1500ms)
    MAX_DAILY_LOSS = "MAX_DAILY_LOSS"              # Realized + Unrealized loss breached daily limit
    MAX_DRAWDOWN = "MAX_DRAWDOWN"                  # Peak-to-trough equity drawdown breached limit
    BROKER_DISCONNECTED = "BROKER_DISCONNECTED"    # WebSocket/FIX session disconnected
    RECONCILIATION_FAILURE = "RECONCILIATION_FAILURE" # State mismatch with broker ledger
    CLOCK_SKEW_DETECTED = "CLOCK_SKEW_DETECTED"    # Host clock drifted > tolerance relative to exchange
    MARKET_CLOSED = "MARKET_CLOSED"                # Exchange trading session closed or halted
    MANUAL_HALT = "MANUAL_HALT"                    # Operator emergency kill switch triggered
```

---

## 3. Kill Switch Event Schema

```python
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
    action_taken: str = Field(description="'CANCEL_ALL_AND_HALT', 'CLOSE_POSITIONS_AND_HALT'.")
    actor: str = Field(description="'SYSTEM_AUTOMATED_RISK_GATE' or 'OPERATOR_<ID>'.")
    
    event_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of canonical kill event.")
```
