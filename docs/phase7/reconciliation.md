# Phase 7: Real-Time State Reconciliation Engine

## 1. Overview & Forensic Parity
In real-money trading, catastrophic losses often stem not from bad alpha models, but from **State Drift** between internal shadow ledgers and broker/exchange execution reality.

The Reconciliation Engine periodically (and on critical lifecycle events) performs bi-directional state reconciliation across 6 core dimensions:

```text
       ┌────────────────────────┐         ┌────────────────────────┐
       │   ACASH Shadow State   │         │  Broker/Exchange State │
       │  - Active Orders       │         │  - Working Orders      │
       │  - Open Positions      │ ◄─────► │  - Open Positions      │
       │  - Cash / Collateral   │         │  - Account Balance     │
       │  - Realized Trades     │         │  - Execution Fills     │
       └────────────────────────┘         └────────────────────────┘
                                    │
                                    ▼
                     [ Discrepancy Evaluation ]
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
              [ Parity 100% ]             [ Discrepancy Found ]
              (Log Nominal)                        │
                                                   ▼
                                      [ RECONCILIATION_FAILURE ]
                                                   │
                                                   ▼
                                      [ HALT ALL NEW ORDERS ]
                                      [ EMIT CRITICAL INCIDENT ]
```

---

## 2. The 6 Reconciliation Dimensions
1. **Order Count Parity**: Number of open/working orders in shadow ledger must exactly match broker state.
2. **Position Quantity Parity**: Net signed position units per symbol must match within numerical zero tolerance ($\le 10^{-8}$).
3. **Execution Fill Count & Volume Parity**: Cumulative filled lots per client order ID must match broker trade reports.
4. **Cash / Margin Equity Parity**: Realized cash balances must match within fee and interest settlement tolerances.
5. **Pending Cancellation Parity**: Orders marked `CANCELLED` internally must not exist on the broker order book.
6. **Average Price Reconciliation**: Internal VWAP calculation must match broker executed average price within slippage bounds.

---

## 3. Reconciliation Report Schema

```python
class ReconciliationReport(BaseModel):
    """Forensic report of state reconciliation between internal shadow ledger and broker."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    reconciliation_id: str = Field(description="Unique reconciliation event identifier.")
    timestamp: datetime = Field(description="UTC timestamp of reconciliation check.")
    venue: str = Field(description="Target exchange or broker venue.")
    is_in_parity: bool = Field(description="True if all 6 parity checks passed without discrepancy.")
    
    # Parity Metrics
    internal_open_orders_count: int = Field(description="Active order count in shadow ledger.")
    broker_open_orders_count: int = Field(description="Working order count on broker exchange.")
    
    position_discrepancies: Tuple[Dict[str, Any], ...] = Field(default=(), description="List of mismatched positions.")
    order_discrepancies: Tuple[Dict[str, Any], ...] = Field(default=(), description="List of mismatched orders.")
    cash_discrepancy_amount: Decimal = Field(default=Decimal("0.0"), description="Discrepancy in account equity.")
    
    action_taken: str = Field(description="'NOMINAL_LOGGED' or 'HALTED_ON_DISCREPANCY'.")
    report_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of reconciliation state.")
```
