# Phase 12 Red-Team Adversarial Test Matrix v1.0
## Adversarial Stress Vectors, Boundary Violations & Failure Modes

> **Document:** `docs/phase12/red_team_matrix_v1.md`  
> **Status:** RED-TEAM ADVERSARIAL MATRIX v1.0 (LOCKED ADVERSARIAL SPECIFICATION)  
> **Baseline Commit:** `31bb9bb` (`HEAD == origin/main`, 1,020 collected: 1,017 passed, 3 skipped, 0 failed, MyPy clean)  
> **Target System:** Phase 12 MT5 Broker Adapter, Contract Normalizer, 6-D Reconciliation & TradingView Ingress  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Single Authority Invariant)

---

## 1. Adversarial Test Philosophy

The Phase 12 execution adapter sits directly on the boundary between ACASH deterministic mathematical state and volatile broker socket reality. Unit tests proving happy-path serialization are **insufficient**.

Every test vector in this matrix attacks the assumptions of the adapter, terminal driver, contract normalizer, and webhook ingress across 6 adversarial domains:
1. **Order Lifecycle & Fill Telemetry Corruption (Vectors 1–6)**
2. **Terminal Disconnect, In-Flight Ambiguity & Reconnection (Vectors 7–11)**
3. **Multi-Account, Namespace Collision & Cryptographic Integrity (Vectors 12–15)**
4. **Symbol Specification & Normalization Boundary Violations (Vectors 16–20)**
5. **MQL5 Filling Mode & BOC Price Safety Invariant Attacks (Vectors 21–26)**
6. **TradingView Webhook Ingress, Replay & Security Boundary (Vectors 27–31)**

---

## 2. Comprehensive 31-Vector Adversarial Matrix

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    PHASE 12 RED-TEAM ADVERSARIAL MATRIX                                          │
├──────┬──────────────────────────────────────────┬─────────────────────────────────────┬──────────────────────────┤
│ ID   │ Adversarial Attack Vector                │ Expected Failure Mode / Boundary    │ Required Invariant Action│
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-01│ Duplicate Order Submission               │ Re-submitting identical intent_id   │ Fail-closed idempotency  │
│      │                                          │ within same cycle pulse             │ block (cached receipt)   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-02│ Duplicate Deal Ticket Observation        │ Adapter receives identical          │ Idempotent deal dedupe   │
│      │                                          │ deal_ticket twice                   │ (no duplicate exposure)  │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-03│ Single Order Split into 3 Fills (VWAP)   │ OrderIntent for 1.0 lot fills via   │ Aggregate to VWAP on     │
│      │                                          │ 3 distinct deal tickets             │ ExecutionManifest        │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-04│ Partial Fill with Immediate Cancel       │ Order fills 0.4 lot, remaining 0.6  │ PARTIALLY_FILLED state   │
│      │                                          │ cancelled by broker                 │ recorded; shadow updated │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-05│ Order Send Success with Zero Deal Ticket │ order_send returns 10009 but deals  │ In-flight order stays    │
│      │                                          │ table empty (settlement lag)        │ SUBMITTED until deal poll│
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-06│ Requote (10004) under Market Slippage    │ Broker server requotes price        │ Emit REJECT_OBSERVED;    │
│      │                                          │ during execution                    │ record drag attribution  │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-07│ Connection Drop Mid-order_send()         │ Socket cuts during socket packet tx │ Transition in-flight to  │
│      │                                          │ (unknown if server processed)       │ UNKNOWN; block cycles    │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-08│ Broker Terminal Crash / Restart          │ Terminal process killed externally  │ Adapter raises           │
│      │                                          │ during active polling               │ MT5ConnectionError       │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-09│ Post-Reconnect Phantom Position          │ Reconnection discovers untracked    │ 6-D Reconciliation fails;│
│      │                                          │ position opened externally          │ halt trading immediately │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-10│ Conflicting Position Volume Snapshot     │ Broker reports 1.5 lots; shadow     │ MT5ReconciliationError;  │
│      │                                          │ ledger calculates 1.0 lot           │ fail closed              │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-11│ Stale Account Balance Observation        │ Terminal returns cached equity from │ Stale timestamp detected;│
│      │                                          │ 5 minutes prior                     │ mark UNHEALTHY           │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-12│ Multi-Account Intent Cross-Leakage       │ Account A adapter attempts action   │ 9-tuple account_id check │
│      │                                          │ on Account B order ticket           │ blocks cross-account I/O │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-13│ Magic Number Collision                   │ External EA on terminal uses same   │ Tier 1 SHA-256 digest    │
│      │                                          │ 32-bit magic integer                │ ensures sovereign auth   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-14│ Comment Truncation Attack                │ Broker server truncates comment to  │ Cryptographic lineage    │
│      │                                          │ 15 characters                       │ unaffected by comment cut│
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-15│ Windows DPAPI Unauthorized User Context  │ Service runs under different user   │ Decryption fails closed  │
│      │                                          │ context than DPAPI owner            │ on startup (exit 1)      │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-16│ Sub-Minimum Lot Sizing Attempt           │ Request volume 0.005 lot when       │ DataContractError        │
│      │                                          │ volume_min = 0.01                   │ (VOLUME_OUT_OF_BOUNDS)   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-17│ Non-Quantized Lot Step Attempt           │ Request volume 0.123 lot when       │ DataContractError        │
│      │                                          │ volume_step = 0.01                  │ (VOLUME_STEP_MISMATCH)   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-18│ Super-Maximum Lot Sizing Attempt         │ Request volume 150.0 lots when      │ DataContractError        │
│      │                                          │ volume_max = 100.0                  │ (VOLUME_OUT_OF_BOUNDS)   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-19│ Unnormalized Price Decimal Attack        │ Limit price with 7 digits when      │ Normalizer quantizes to  │
│      │                                          │ symbol digits = 5                   │ 5 digits via point_size  │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-20│ Stop Distance Violation                  │ Limit order within stops_level      │ DataContractError        │
│      │                                          │ boundary from market price          │ (STOP_LEVEL_VIOLATION)   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-21│ Market Execution RETURN Filling Attempt  │ Market BUY with RETURN filling      │ Fail closed pre-flight   │
│      │                                          │ under SYMBOL_TRADE_EXEC_MARKET      │ (RETURN_FORBIDDEN)       │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-22│ BOC on Unsupported Order Type            │ PASSIVE_MAKER on market BUY or      │ DataContractError        │
│      │                                          │ breakout BUY_STOP                   │ (BOC_INVALID_ORDER_TYPE) │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-23│ BOC on Non-Exchange Execution Mode       │ PASSIVE_MAKER on symbol with        │ DataContractError        │
│      │                                          │ MARKET / REQUEST execution mode     │ (BOC_REQUIRES_EXCHANGE)  │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-24│ BOC on Symbol Lacking BOC Flag           │ PASSIVE_MAKER on Exchange symbol    │ DataContractError        │
│      │                                          │ without SYMBOL_FILLING_BOC bit      │ (SYMBOL_LACKS_BOC_FLAG)  │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-25│ BOC Price Not Passive (Limit Order)      │ BUY_LIMIT price >= current_ask     │ DataContractError        │
│      │                                          │ (taker fill danger)                 │ (BOC_PRICE_NOT_PASSIVE)  │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-26│ BOC Price Not Passive (Stop-Limit Order) │ BUY_STOP_LIMIT resting limit >=     │ DataContractError        │
│      │                                          │ stop trigger price                  │ (BOC_PRICE_NOT_PASSIVE)  │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-27│ TradingView Invalid HMAC Signature       │ Webhook payload with invalid or     │ Ingress rejects with 401;│
│      │                                          │ forged HMAC-SHA256 signature        │ zero internal mutation   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-28│ TradingView Replayed Webhook Attack      │ Valid webhook re-sent with expired  │ Nonce / timestamp window │
│      │                                          │ timestamp (> 3000ms drift)          │ (>3s) rejects with 400   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-29│ TradingView Malformed JSON Injection     │ Webhook sends malformed JSON or     │ Pydantic strict parsing  │
│      │                                          │ injection strings in symbol/action  │ rejects with 422         │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-30│ TradingView Direct Execution Bypass      │ Webhook payload attempts to force   │ $0.00 capital boundary   │
│      │                                          │ direct broker ticket execution      │ enforces candidate route │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-31│ TradingView Cloud Outage Simulation      │ TradingView webhook ingress down or │ Core ACASH trading loop  │
│      │                                          │ unreachable                         │ operates unaffected      │
└──────┴──────────────────────────────────────────┴─────────────────────────────────────┴──────────────────────────┘
```

---

## 3. Detailed Attack Vector Specifications

### RT-25 & RT-26: BOC Price-Side Passive Invariant Verification
```python
def test_rt25_boc_non_passive_buy_limit_fails():
    """Verify BUY_LIMIT with price >= ask is rejected pre-flight."""
    spec = create_exchange_symbol_spec(allowed_filling=("SYMBOL_FILLING_BOC",))
    with pytest.raises(DataContractError, match="BOC_PRICE_NOT_PASSIVE_BUY_LIMIT"):
        resolve_filling_mode(
            symbol_spec=spec,
            order_type=MT5OrderType.BUY_LIMIT,
            execution_policy=MT5ExecutionPolicy.PASSIVE_MAKER,
            limit_price=Decimal("1.0855"),
            current_bid=Decimal("1.0850"),
            current_ask=Decimal("1.0852"), # Price crosses ask!
        )


def test_rt26_boc_non_passive_stop_limit_fails():
    """Verify BUY_STOP_LIMIT with limit_price >= trigger_price is rejected."""
    spec = create_exchange_symbol_spec(allowed_filling=("SYMBOL_FILLING_BOC",))
    with pytest.raises(DataContractError, match="BOC_PRICE_NOT_PASSIVE_BUY_STOP_LIMIT"):
        resolve_filling_mode(
            symbol_spec=spec,
            order_type=MT5OrderType.BUY_STOP_LIMIT,
            execution_policy=MT5ExecutionPolicy.PASSIVE_MAKER,
            trigger_price=Decimal("1.0900"),
            limit_price=Decimal("1.0905"), # Limit price higher than trigger!
            current_bid=Decimal("1.0850"),
            current_ask=Decimal("1.0852"),
        )
```

### RT-07: In-Flight Socket Drop Disconnect Handling
```python
def test_rt07_socket_drop_transitions_to_unknown():
    """Verify socket drop during order submission marks order UNKNOWN."""
    adapter = create_mock_mt5_adapter(simulate_socket_timeout=True)
    with pytest.raises(MT5ConnectionError):
        adapter.submit_order(intent)

    # Sovereign ExecutionCoordinator must record UNKNOWN, not CANCELLED/REJECTED
    order_state = coordinator.get_order(intent.intent_id)
    assert order_state.lifecycle_state == OrderLifecycleState.UNKNOWN
```

### RT-27 & RT-28: TradingView Ingress Security & Replay Attacks
```python
def test_rt27_tradingview_invalid_hmac_rejected():
    """Verify forged webhook signature returns 401 Unauthorized."""
    response = client.post(
        "/api/v1/ingress/tradingview",
        content=valid_payload_bytes,
        headers={"X-TradingView-Signature": "invalid_forged_signature"},
    )
    assert response.status_code == 401


def test_rt28_tradingview_replayed_timestamp_rejected():
    """Verify expired webhook timestamp is rejected."""
    expired_payload = create_tv_payload(timestamp_utc=now() - timedelta(seconds=10))
    signature = sign_hmac(expired_payload, secret_key)
    response = client.post(
        "/api/v1/ingress/tradingview",
        content=expired_payload,
        headers={"X-TradingView-Signature": signature},
    )
    assert response.status_code == 400
```

---

## 4. Verification Ledger & Audit Signoff

- **Baseline Commit:** `31bb9bb` (`HEAD == origin/main`)
- **Total Adversarial Vectors:** 31 Vectors across 6 Domains.
- **Rule:** Every one of the 31 vectors must have an automated test in `tests/unit/execution/` and `tests/adversarial/` before Phase 12 Gate Freeze.
