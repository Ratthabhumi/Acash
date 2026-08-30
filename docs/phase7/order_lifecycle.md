# Phase 7: Order Intent & Lifecycle Specification

## 1. Order Intent as a First-Class Immutable Contract
Before an order reaches a network socket or broker adapter, the strategy must emit an immutable `OrderIntent`.

The `OrderIntent` cryptographically binds the strategy's signal to an active `LiveAuthorization` and an immutable snapshot of current portfolio risk.

```text
Signal Event (Atlas / Strategy)
       │
       ▼
LiveAuthorization Check (Pre-execution validation)
       │
       ▼
OrderIntent (First-Class Immutable Object)
       │
       ▼
Execution Router → Submitted → Acknowledged → Filled
       │
       ▼
ExecutionManifest (Links back to intent_digest)
```

---

## 2. Order Intent Schema

```python
class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LIMIT = "STOP_LIMIT"

class TimeInForce(str, Enum):
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    DAY = "DAY"

class OrderIntent(BaseModel):
    """Immutable intent to place an order, emitted before broker transmission."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    intent_id: str = Field(description="Unique deterministic order intent ID.")
    authorization_id: str = Field(description="Active LiveAuthorization ID under which order is submitted.")
    strategy_id: str = Field(description="Originating strategy identifier.")
    
    venue: str = Field(description="Target broker / exchange venue.")
    symbol: str = Field(description="Tradeable asset symbol.")
    side: OrderSide = Field(description="'BUY' or 'SELL'.")
    order_type: OrderType = Field(description="'LIMIT', 'MARKET', 'STOP_LIMIT'.")
    time_in_force: TimeInForce = Field(default=TimeInForce.GTC, description="Time-in-force condition.")
    
    quantity: Decimal = Field(gt=0, description="Requested order volume.")
    limit_price: Optional[Decimal] = Field(default=None, description="Limit price for non-market orders.")
    stop_price: Optional[Decimal] = Field(default=None, description="Stop trigger price if applicable.")
    
    created_at: datetime = Field(description="UTC timestamp of intent creation.")
    
    # Cryptographic Provenance Bindings
    signal_event_hash: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of triggering market signal event.")
    risk_snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of RiskState at time of pre-submission check.")
    intent_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of canonical order intent payload.")
```

---

## 3. Order Lifecycle State Machine

```text
[ INTENT ]
    │
    ▼
[ SUBMITTED ] ──► (Broker Rejects) ──► [ REJECTED ] (Terminal)
    │
    ▼
[ ACKNOWLEDGED ] ──► (User Cancels) ──► [ CANCELLED ] (Terminal)
    │
    ├──► (Partial Fill) ──► [ PARTIALLY_FILLED ]
    │                              │
    ▼                              ▼
[ FILLED ] (Terminal)         [ FILLED ] (Terminal)

[ ANY STATE (Network Cut / Timeout) ] ──► [ UNKNOWN ] (Requires Reconciliation)
```

### The `UNKNOWN` State Invariant
> **"If the broker state cannot be verified, NEVER assume the order was unfilled."**

When an order enters `UNKNOWN` (e.g. timeout on gateway response, socket reconnect):
1. **Immediate Execution Freeze**: Strategy is placed into `RESTRICTED` mode; no new orders permitted.
2. **Reconciliation Trigger**: The Reconciliation Engine queries exchange order status API / execution report history.
3. **Fail-Closed Resolution**: The order remains `UNKNOWN` until an authoritative fill report or cancellation acknowledgment is received.
