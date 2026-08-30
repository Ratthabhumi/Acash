# Phase 7: Live Execution Manifest Specification

## 1. Overview & Forensic Lineage
Every order execution in Phase 7 produces an immutable `ExecutionManifest` capturing complete execution provenance, network latency, slippage attribution, and fill economics.

```text
ValidationReport (Phase 6)
       │
       ▼
LiveAuthorization
       │
       ▼
OrderIntent (intent_digest)
       │
       ▼
ExecutionManifest (Binds intent_digest → execution_digest)
       │
       ▼
FillEvents & Shadow Ledger Entries
```

---

## 2. Execution Manifest Schema

```python
class ExecutionManifest(BaseModel):
    """Immutable forensic audit record of a single live order execution."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_id: str = Field(description="Unique deterministic execution identifier.")
    authorization_id: str = Field(description="Linked LiveAuthorization identifier.")
    strategy_id: str = Field(description="Target strategy identifier.")
    intent_id: str = Field(description="Linked OrderIntent identifier.")
    intent_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of originating OrderIntent.")
    
    client_order_id: str = Field(description="Client order identifier.")
    broker_order_id: Optional[str] = Field(default=None, description="Assigned broker order ID.")
    
    venue: str = Field(description="Target exchange or broker venue (e.g. 'BINANCE_FUTURES', 'INTERACTIVE_BROKERS').")
    symbol: str = Field(description="Tradeable asset symbol.")
    order_side: str = Field(description="'BUY' or 'SELL'.")
    order_type: str = Field(description="'LIMIT', 'MARKET', 'STOP_LIMIT'.")
    
    # Timing & Latency Attribution
    created_at: datetime = Field(description="Timestamp when OrderIntent was constructed.")
    submitted_at: datetime = Field(description="Timestamp when order packet left socket.")
    acknowledged_at: Optional[datetime] = Field(default=None, description="Timestamp of broker acknowledgment.")
    first_fill_at: Optional[datetime] = Field(default=None, description="Timestamp of first fill packet.")
    closed_at: Optional[datetime] = Field(default=None, description="Timestamp when order reached terminal state.")
    
    network_latency_ms: Optional[float] = Field(default=None, description="Wire transit latency (ack - submit).")
    exchange_queue_latency_ms: Optional[float] = Field(default=None, description="Queue latency on exchange.")
    
    # Fill Economics & Slippage Attribution
    requested_qty: Decimal = Field(gt=0, description="Requested volume from OrderIntent.")
    filled_qty: Decimal = Field(ge=0, description="Cumulative filled volume.")
    benchmark_mid_price: Decimal = Field(gt=0, description="Mid price at moment of OrderIntent creation.")
    average_fill_price: Optional[Decimal] = Field(default=None, description="Volume-weighted average fill price.")
    realized_slippage_bps: Optional[float] = Field(default=None, description="Realized execution drag relative to benchmark.")
    total_commission_paid: Decimal = Field(ge=0, default=Decimal("0.0"), description="Total exchange/broker fees.")
    
    # Lineage Hashes
    source_signal_event_hash: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of triggering market event.")
    execution_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of canonical execution record.")
```
