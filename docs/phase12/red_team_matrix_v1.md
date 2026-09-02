# Phase 12 Red-Team Adversarial Test Matrix v1.0
## Adversarial Stress Vectors, Boundary Violations & Failure Modes

> **Document:** `docs/phase12/red_team_matrix_v1.md`  
> **Status:** FINAL DRAFT — PENDING FINAL AUDIT APPROVAL  
> **Baseline Commit:** `2286bce` (`HEAD == origin/main`, 1,020 collected: 1,017 passed, 3 skipped, 0 failed, MyPy clean)  
> **Target System:** Phase 12 MT5 Broker Adapter, Contract Normalizer, 6-D Reconciliation & TradingView Ingress  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Single Authority Invariant)

---

## 1. Adversarial Test Philosophy

The Phase 12 execution adapter sits directly on the boundary between ACASH deterministic mathematical state and volatile broker socket reality. Unit tests proving happy-path serialization are **insufficient**.

Every test vector in this matrix attacks the assumptions of the adapter, terminal driver, contract normalizer, and webhook ingress across 6 adversarial domains (**31 adversarial vectors across 6 domains**):
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
│ RT-01│ Multi-Scope Duplicate Submission         │ Re-submitting identical intent_id   │ Global persisted receipt │
│      │                                          │ across cycles/restarts/reconnects   │ blocks duplicate order   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-02│ Multi-Account Deal Ticket Collision      │ Identical deal_ticket received from │ 9-tuple namespace check  │
│      │                                          │ distinct accounts/terminals         │ isolates deal identities │
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
│ RT-06│ Requote (10004) without Executed Deal    │ Broker server requotes price        │ Emit REQUOTE_OBSERVED;   │
│      │                                          │ without generating a deal ticket    │ ZERO realized drag added │
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
│      │                                          │ volume_min = 0.01                   │ (VOLUME_BELOW_MINIMUM)   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-17│ Non-Quantized Lot Step Attempt           │ Request volume 0.123 lot when       │ Quantizer rounds down to │
│      │                                          │ volume_step = 0.01                  │ 0.12 lot via ROUND_DOWN  │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-18│ Super-Maximum Lot Sizing Attempt         │ Request volume 150.0 lots when      │ DataContractError        │
│      │                                          │ volume_max = 100.0                  │ (VOLUME_ABOVE_MAXIMUM)   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-19│ Unnormalized Price Tick-Grid Attack      │ Limit price with unaligned decimal  │ Normalizer snaps to tick │
│      │                                          │ (e.g. 1.085123 on 5-digit point)    │ grid using maker rules   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-20│ Stop Distance Violation                  │ Limit order within stops_level      │ DataContractError        │
│      │                                          │ boundary from market price          │ (STOP_LEVEL_VIOLATION)   │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-21│ Market Execution RETURN Filling Attempt  │ Market BUY with RETURN filling      │ Fail closed pre-flight   │
│      │                                          │ under SYMBOL_TRADE_EXEC_MARKET      │ (NO_COMPATIBLE_FILLING)  │
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
│ RT-26│ BOC Stop-Limit 4-Case Boundary Violations│ Trigger <= ask, limit >= trigger,   │ DataContractError        │
│      │ & Post-Quantization Spread Crossing     │ or tick quantization crossing spread│ (BOC_PRICE_NOT_PASSIVE)  │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-27│ TradingView Non-Allowlisted IP / Token   │ Webhook from unknown IP or with     │ Ingress rejects with     │
│      │                                          │ invalid passphrase/token            │ 403 Forbidden / 401 Unauth│
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-28│ TradingView 5-Second Retry Handling      │ TradingView resends identical alert │ Pre-freshness lookup ACK │
│      │                                          │ payload after 5s retry attempt      │ 200 OK without duplicate │
├──────┼──────────────────────────────────────────┼─────────────────────────────────────┼──────────────────────────┤
│ RT-29│ TradingView Malformed JSON / Stale Alert │ Webhook with invalid JSON format or │ Ingress rejects with     │
│      │                                          │ timestamp older than 60s window     │ 422 Unproc / 400 Stale   │
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

### RT-01: Multi-Scope Duplicate Submission Idempotency
```python
def test_rt01_duplicate_submission_blocked_across_restarts():
    """Verify that an identical intent_id cannot be submitted twice even across restarts."""
    coordinator = create_execution_coordinator()
    intent = create_valid_order_intent(intent_id="intent-101")
    
    # 1. Initial submission
    receipt1 = coordinator.submit_intent(intent)
    assert receipt1.status == SubmissionStatus.ACCEPTED
    
    # 2. Re-submission in next cycle
    receipt2 = coordinator.submit_intent(intent)
    assert receipt2.status == SubmissionStatus.DUPLICATE_REJECTED
    
    # 3. Simulate process restart and reload
    coordinator_reloaded = reload_execution_coordinator_from_ledger()
    receipt3 = coordinator_reloaded.submit_intent(intent)
    assert receipt3.status == SubmissionStatus.DUPLICATE_REJECTED
```

### RT-02: Namespace-Aware Deal Deduplication
```python
def test_rt02_deal_dedupe_is_namespace_aware():
    """Verify deal tickets are partitioned across (broker_id, account_id, terminal_instance_id)."""
    coordinator = create_execution_coordinator()
    
    deal_account_a = MT5DealReality(
        deal_ticket=12345,
        order_ticket=999,
        position_ticket=101,
        symbol="EURUSD",
        deal_type="DEAL_TYPE_BUY",
        volume=Decimal("1.0"),
        price=Decimal("1.0850"),
        commission=Decimal("2.0"),
        fee=Decimal("0.0"),
        swap=Decimal("0.0"),
        profit=Decimal("0.0"),
        deal_time_utc=datetime.now(timezone.utc),
        comment="test-a",
        magic=1001,
    )
    
    # Deal on Account A processed
    event_a = BrokerRawEvent(
        broker_id="mt5_demo",
        account_id="acc_1001",
        terminal_instance_id="term_1",
        event_kind=BrokerEventKind.FILL_OBSERVED,
        deal_payload=deal_account_a,
    )
    assert coordinator.apply(event_a).is_accepted
    
    # Duplicate deal on Account A rejected
    assert coordinator.apply(event_a).is_duplicate_ignored
    
    # Same deal ticket on Account B is distinct and valid
    event_b = BrokerRawEvent(
        broker_id="mt5_demo",
        account_id="acc_1002",
        terminal_instance_id="term_2",
        event_kind=BrokerEventKind.FILL_OBSERVED,
        deal_payload=deal_account_a,
    )
    assert coordinator.apply(event_b).is_accepted
```

### RT-06: Requote Observation without Synthetic Drag
```python
def test_rt06_requote_emits_observation_without_synthetic_drag():
    """Verify retcode 10004 REQUOTE does not generate false execution drag records."""
    adapter = create_mock_mt5_adapter(simulate_retcode=10004) # REQUOTE
    intent = create_valid_order_intent()
    
    event = adapter.submit_order(intent)
    assert event.event_kind == BrokerEventKind.REJECT_OBSERVED
    assert event.rejection_reason == "REQUOTE_OBSERVED"
    
    # ExecutionCoordinator verifies no deal tickets exist -> drag record is NOT manufactured
    manifest = coordinator.get_execution_manifest(intent.intent_id)
    assert manifest.realized_vwap is None
    assert manifest.execution_drag_bps == Decimal("0.0")
```

### RT-26: Stop-Limit BOC Invariants & Post-Quantization Boundary Testing
```python
def test_rt26_boc_stop_limit_comprehensive_boundary_rejections():
    """Verify all 4 Stop-Limit BOC invalid boundary states fail closed."""
    spec = create_exchange_symbol_spec(allowed_filling=("SYMBOL_FILLING_BOC",))
    
    # Case 1: BUY_STOP_LIMIT with trigger <= ask (Aggressive trigger)
    with pytest.raises(DataContractError, match="BOC_PRICE_NOT_PASSIVE_BUY_STOP_LIMIT"):
        resolve_filling_mode(
            symbol_spec=spec,
            order_type=MT5OrderType.BUY_STOP_LIMIT,
            execution_policy=MT5ExecutionPolicy.PASSIVE_MAKER,
            trigger_price=Decimal("1.0852"), # Equal to ask!
            limit_price=Decimal("1.0845"),
            current_bid=Decimal("1.0850"),
            current_ask=Decimal("1.0852"),
        )

    # Case 2: BUY_STOP_LIMIT with limit >= trigger (Aggressive limit on trigger)
    with pytest.raises(DataContractError, match="BOC_PRICE_NOT_PASSIVE_BUY_STOP_LIMIT"):
        resolve_filling_mode(
            symbol_spec=spec,
            order_type=MT5OrderType.BUY_STOP_LIMIT,
            execution_policy=MT5ExecutionPolicy.PASSIVE_MAKER,
            trigger_price=Decimal("1.0900"),
            limit_price=Decimal("1.0900"), # Equal to trigger!
            current_bid=Decimal("1.0850"),
            current_ask=Decimal("1.0852"),
        )

    # Case 3: SELL_STOP_LIMIT with trigger >= bid (Aggressive trigger)
    with pytest.raises(DataContractError, match="BOC_PRICE_NOT_PASSIVE_SELL_STOP_LIMIT"):
        resolve_filling_mode(
            symbol_spec=spec,
            order_type=MT5OrderType.SELL_STOP_LIMIT,
            execution_policy=MT5ExecutionPolicy.PASSIVE_MAKER,
            trigger_price=Decimal("1.0850"), # Equal to bid!
            limit_price=Decimal("1.0855"),
            current_bid=Decimal("1.0850"),
            current_ask=Decimal("1.0852"),
        )

    # Case 4: SELL_STOP_LIMIT with limit <= trigger (Aggressive limit on trigger)
    with pytest.raises(DataContractError, match="BOC_PRICE_NOT_PASSIVE_SELL_STOP_LIMIT"):
        resolve_filling_mode(
            symbol_spec=spec,
            order_type=MT5OrderType.SELL_STOP_LIMIT,
            execution_policy=MT5ExecutionPolicy.PASSIVE_MAKER,
            trigger_price=Decimal("1.0800"),
            limit_price=Decimal("1.0800"), # Equal to trigger!
            current_bid=Decimal("1.0850"),
            current_ask=Decimal("1.0852"),
        )
```

### RT-28: TradingView 5-Second Retry Handling with Pre-Freshness Idempotency
```python
def test_rt28_tradingview_5s_retry_handled_idempotently():
    """Verify legitimate 5-second retry returns 200 OK without duplicate candidate creation."""
    client = create_tradingview_test_client()
    payload = {
        "passphrase": "VALID_SECRET_TOKEN",
        "strategy_id": "MOM_ALPHA_01",
        "action": "BUY",
        "symbol": "EURUSD",
        "bar_time_utc": "2026-09-02T12:00:00.000000Z",
        "event_timestamp_utc": "2026-09-02T12:00:01.000000Z",
        "nonce": "producer-unique-nonce-123",
    }
    
    # Initial attempt
    res1 = client.post("/api/v1/ingress/tradingview", json=payload)
    assert res1.status_code == 200
    assert res1.json()["status"] == "PROPOSAL_INGESTED"
    
    # Simulated TradingView 5s retry with identical producer event payload and nonce
    res2 = client.post("/api/v1/ingress/tradingview", json=payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "IDEMPOTENT_ACK_DUPLICATE_DROPPED"
    
    # Ensure only 1 candidate signal was emitted to research queue
    signals = get_unvalidated_candidate_signals()
    assert len([s for s in signals if s.strategy_id == "MOM_ALPHA_01"]) == 1
```

---

## 4. Verification Ledger & Audit Signoff

- **Active Baseline Commit:** `2286bce` (`HEAD == origin/main`)
- **Total Adversarial Vectors:** 31 Vectors across 6 Domains.
- **Rule:** Every one of the 31 vectors must have an automated test in `tests/unit/execution/` and `tests/adversarial/` before Phase 12 Gate Freeze.
