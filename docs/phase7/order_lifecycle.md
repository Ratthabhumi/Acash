# Phase 7: Order & Position Lifecycle Specification

## 1. Order State Machine
Phase 7 implements a deterministic, fail-closed order lifecycle that prevents phantom fills, unacknowledged position drift, and ambiguous broker communication.

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

[ ANY STATE (During Network Cut / Ambiguity) ] ──► [ UNKNOWN ] (Requires Reconciliation)
```

---

## 2. Order States & Terminal Paths

```python
class OrderLifecycleState(str, Enum):
    INTENT = "INTENT"                      # Created internally, pre-submission risk passed
    SUBMITTED = "SUBMITTED"                # Dispatched across network to broker
    ACKNOWLEDGED = "ACKNOWLEDGED"          # Confirmed received by broker order book
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Partial volume filled; balance working
    FILLED = "FILLED"                      # 100% volume filled (Terminal)
    CANCELLED = "CANCELLED"                # Canceled by strategy or risk manager (Terminal)
    REJECTED = "REJECTED"                  # Rejected by risk gate or broker (Terminal)
    EXPIRED = "EXPIRED"                    # Time-in-force expired (Terminal)
    UNKNOWN = "UNKNOWN"                    # Communication severed before ack/reject (Non-terminal / Critical)
```

---

## 3. The `UNKNOWN` State Invariant
> **"If the broker state cannot be verified, NEVER assume the order was unfilled."**

When an order enters `UNKNOWN` (e.g. timeout on gateway response, socket reconnect):
1. **Immediate Execution Freeze**: Strategy is placed into `RESTRICTED` mode; no new orders permitted.
2. **Reconciliation Trigger**: The Reconciliation Engine queries exchange order status API / execution report history.
3. **Fail-Closed Resolution**: The order remains `UNKNOWN` until an authoritative fill report or cancellation acknowledgment is received.
