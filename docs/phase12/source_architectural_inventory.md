# Phase 12 Architecture & Capability Inventory (Revision 2)
## Multi-Venue Execution Topology, MetaTrader 5 (MT5) Adapter & TradingView Integration

> **Document:** `docs/phase12/source_architectural_inventory.md`  
> **Status:** APPROVED ARCHITECTURAL INVENTORY (Pre-Contract Specification v1.0)  
> **Baseline Commit:** `049e155` (`HEAD == origin/main`, 1,020 tests passed, MyPy clean)  
> **Frozen Baselines:** Phase 7 (Frozen), Phase 8 (`e6f1d04`), Phase 8.5 (`9ce1365`), Phase 9 (`6bd40d8`), Phase 10 (`3955bf6`), Phase 11 (`092a2b1`)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Sovereign Authority Separation)

---

## 1. Executive Summary & Sovereign Decoupling Matrix

$$\boxed{\mathbf{Research\ (8.5)} \neq \mathbf{Monitoring\ (11)} \neq \mathbf{Allocation\ (8)} \neq \mathbf{Supervisor\ (10)} \neq \mathbf{Risk\ (9)} \neq \mathbf{Execution\ (7/12)} \neq \mathbf{Broker}}$$

Phase 12 expands the sovereign execution plane established in Phase 7 by introducing a **Multi-Venue Execution Topology** with **MetaTrader 5 (MT5) as Execution Adapter #1** and establishing a strict, decoupled boundary for **TradingView as an Optional Auxiliary Ingress / Visualization Interface**.

```
                                      ACASH CORE
                                          │
                             Sovereign Execution Engine
                            (Phase 7 ExecutionCoordinator)
                                          │
                     ┌────────────────────┴────────────────────┐
                     │                                         │
            AlpacaPaperAdapter                          MT5BrokerAdapter
             (Phase 7 Venue)                           (Phase 12 Adapter #1)
                     │                                         │
             Alpaca REST / SSE                              MT5 IPC Bridge
                     │                                         │
             Alpaca Paper Venue                          MT5 Terminal
                                                               │
                                                          Broker Trade Server
```

### Sovereign Non-Negotiable Invariants:
1. **ACASH is the Sole Execution Authority & Source-of-Truth:**
   $$\boxed{\mathbf{ACASH} \equiv \text{Sole Execution Authority} \quad \land \quad \mathbf{BrokerAdapter} \neq \mathbf{StateAuthority}}$$
   - The broker adapter is strictly a **command sink + observation source**.
   - It translates broker reality onto canonical `BrokerRawEvent` observations and **never** mutates state machine transitions directly.
2. **MT5-First Execution Architecture:**
   - Direct, deterministic communication via the official Python IPC bridge (`MetaTrader5`) to the local MT5 terminal.
   - Full support for Orders, Deals, Positions, Margin Accounting, Requotes, Partial Fills, and Broker Reconciliations.
3. **TradingView Decoupled Boundary (Auxiliary Ingress & Visualization Only):**
   - TradingView is **NEVER** an execution authority and **NEVER** sits in the critical execution path.
   - **Strictly Prohibited:** $\text{ACASH} \to \text{TradingView} \to \text{MT5} \to \text{Broker}$.
   - Webhook alerts serve strictly as unvalidated candidate signal inputs that must pass through Research $\to$ Validation $\to$ Tournament $\to$ Risk $\to$ Admission before any order is submitted.
   - ACASH core execution has **zero dependency on TradingView plan tiers**; ACASH maintains its own internal terminal visualization dashboard.

---

## 2. MT5 Execution Lifecycle & Technical Semantics

### A. First-Class Multi-Tier Lifecycle: Order $\longrightarrow$ Deal $\longrightarrow$ Position

MT5 strictly separates requests, executions, and exposures into distinct entities:

```
ACASH OrderIntent (intent_id, intent_digest)
        │
        ▼
MT5 Order / TradeRequest (order_ticket)
        │
        ├───────────────────────────────────────┐
        ▼                                       ▼
  MT5 Deal #1 (deal_ticket_1)             MT5 Deal #2 (deal_ticket_2)
  [Volume: 0.4 Lot, Price: 1.0850]        [Volume: 0.6 Lot, Price: 1.0851]
        │                                       │
        └───────────────────┬───────────────────┘
                            │
                            ▼
                  Position State Snapshot
                 (position_ticket / symbol)
                            │
                            ▼
             ReconciliationEvidence vs ACASH
```

#### Invariant: One OrderIntent $\longrightarrow$ Many Deals
- An `OrderIntent` generates an MT5 order ticket.
- Market execution or sweeping resting liquidity may result in **$0..N$ discrete Deal tickets** (partial fills, multi-level fills).
- `ExecutionManifest` in ACASH natively accumulates all linked `deal_ticket` records to compute exact Volume-Weighted Average Price (VWAP), total realized commissions, and slippage drag.

#### Lineage & Multi-Account Identification Tuple:
To prevent collisions across multi-account, multi-strategy, or concurrent deployments, all execution observations are bound to the 9-tuple:
$$\boxed{(\text{broker\_id}, \text{account\_id}, \text{terminal\_instance\_id}, \text{strategy\_id}, \text{cycle\_id}, \text{intent\_id}, \text{mt5\_order\_ticket}, \text{mt5\_deal\_ticket}, \text{position\_id})}$$

---

### B. Request Retcode $\neq$ Sovereign Lifecycle Authority

`mt5.order_send()` returns an `MqlTradeResult` structure containing a return code (`retcode`).

$$\boxed{\mathbf{MT5\ Retcode} \equiv \text{Adapter-Level Request Processing Outcome} \neq \mathbf{Final\ Lifecycle\ State}}$$

```
mt5.order_send() Result (Observation)
           │
           ▼
BrokerRawEvent (e.g. SUBMISSION_ACKNOWLEDGED / IMMEDIATE_FILL_OBSERVED / REJECT_OBSERVED)
           │
           ▼
ExecutionCoordinator.apply()  [Phase 7 Engine]
           │
           ▼
transition_order()  [SOLE State Machine Authority]
```

- A retcode of `10009` (`TRADE_RETCODE_DONE`) indicates that the trade server accepted/processed the request packet. It is treated as an **adapter observation**, which is then reconciled against authoritative `orders_get()`, `history_deals_get()`, and `positions_get()` streams before reaching terminal `FILLED` state in ACASH.
- Retcodes `10004` (`REQUOTE`), `10006` (`REJECT`), `10018` (`MARKET_CLOSED`), and `10031` (`CONNECTION_LOST`) emit structured raw observations triggering deterministic fail-closed coordination.

---

### C. Multi-Dimensional Filling-Mode Resolution Matrix

Selecting a filling mode cannot rely on `SYMBOL_FILLING_MODE` alone. It requires evaluating a 4-dimensional compatibility matrix:

$$\text{Filling Mode} = f(\text{Symbol Trade Execution Mode}, \text{Symbol Filling Flags}, \text{Order Type}, \text{Broker Policy})$$

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MT5 FILLING MODE RESOLUTION MATRIX                      │
├────────────────────────────┬─────────────────────────────┬──────────────────┤
│ Symbol Execution Mode      │ Order Type                  │ Permitted Mode   │
├────────────────────────────┼─────────────────────────────┼──────────────────┤
│ `SYMBOL_TRADE_EXEC_MARKET` │ Market (`BUY`/`SELL`)       │ `FOK` or `IOC`   │
│ (Market Execution)         │                             │ (*RETURN invalid)│
├────────────────────────────┼─────────────────────────────┼──────────────────┤
│ `SYMBOL_TRADE_EXEC_REQUEST`│ Market / Instant            │ `FOK` / `IOC`    │
│ / `INSTANT`                │                             │                  │
├────────────────────────────┼─────────────────────────────┼──────────────────┤
│ `SYMBOL_TRADE_EXEC_EXCHANGE`│ Exchange Market / Limit     │ `RETURN` / `IOC` │
├────────────────────────────┼─────────────────────────────┼──────────────────┤
│ Any Execution Mode         │ Pending (`LIMIT`/`STOP`)    │ `RETURN` (GTC)   │
└────────────────────────────┴─────────────────────────────┴──────────────────┘
```

> **Critical MQL5 Rule:** In **Market Execution** (`SYMBOL_TRADE_EXECUTION_MARKET`), the trade server executes at prevailing market prices and strictly **forbids `ORDER_FILLING_RETURN`** for market orders. The adapter normalizer verifies the symbol flags (`SYMBOL_FILLING_FOK`, `SYMBOL_FILLING_IOC`) and selects the supported policy prior to socket transmission.

---

### D. Magic Numbers & Comments: Non-Cryptographic Routing Metadata

$$\boxed{\mathbf{Tier\ 1:\ Canonical\ SHA-256\ Digest} \equiv \mathbf{Cryptographic\ Lineage\ Authority}}$$
$$\boxed{\mathbf{MT5\ Magic\ Number} \equiv \mathbf{Non-Authoritative\ Subsystem\ Routing\ Namespace}}$$
$$\boxed{\mathbf{MT5\ Comment} \equiv \mathbf{Transport\ Correlation\ Metadata\ Only}}$$

- `magic` (32-bit uint): Used strictly by the local MT5 terminal to partition orders and prevent interference across sub-systems. **Magic numbers are NOT cryptographic identifiers** (32-bit collision space is insufficient).
- `comment` (string, max 31 chars): Encodes human/transport correlation hints (e.g. `intent_digest[:16]`).
- All cryptographic lineage, signing, and verification remain anchored in ACASH Tier 1 canonical SHA-256 digests (`intent_digest`, `execution_digest`, `decision_digest`). Collisions or truncations in MT5 magic/comment fields do **not** compromise ACASH authorization or cryptographic integrity.

---

## 3. Symbol Mapping & Versioned Contract Specification Normalization

Symbol mapping is **not** a plain string prefix/suffix replacement. It is a formal, versioned `BrokerSymbolSpec` object:

```python
class BrokerSymbolSpec(BaseModel):
    """Immutable, versioned specification of broker-side instrument mechanics."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_symbol: str                    # e.g. 'EURUSD', 'XAUUSD', 'SPX500'
    broker_symbol: str                       # e.g. 'EURUSD.r', 'GOLD', 'US500.cash'
    contract_size: Decimal                   # e.g. 100000 for FX, 100 for Gold
    volume_min: Decimal                      # e.g. 0.01 Lot
    volume_max: Decimal                      # e.g. 100.00 Lot
    volume_step: Decimal                     # e.g. 0.01 Lot
    digits: int                              # e.g. 5
    point_size: Decimal                      # e.g. 0.00001
    trade_execution_mode: str                # 'MARKET', 'INSTANT', 'EXCHANGE'
    allowed_filling_modes: Tuple[str, ...]   # ('FOK', 'IOC')
    stops_level_points: int                  # Minimum stop distance in points
    margin_currency: str                     # e.g. 'USD'
    profit_currency: str                     # e.g. 'USD'
    spec_digest: str                         # SHA-256 canonical digest of specification
```

### Contract Normalizer Responsibilities:
1. Validates requested volume against `[volume_min, volume_max]` and snaps to nearest `volume_step`.
2. Converts canonical cash notional / base units $\longleftrightarrow$ MT5 Lots.
3. Quantizes limit/stop prices to valid `digits` and `point_size`.
4. Enforces broker stop-level distance constraints.

---

## 4. Reconciliation, Multi-Account & Terminal Resilience

```mermaid
flowchart TD
    subgraph ACASH_Engine [ACASH Execution Coordinator]
        InternalState[Internal Shadow Ledger & Positions]
    end

    subgraph MT5_Adapter [MT5 Broker Adapter Layer]
        IPC[MT5 Python IPC Bridge]
        HealthCheck[Periodic Heartbeat & Watchdog]
    end

    subgraph MT5_Terminal [Local Windows MT5 Terminal]
        TradeServer[Broker Trade Server Connection]
    end

    InternalState <-->|Reconciliation Evidence| IPC
    IPC <-->|Binary IPC| MT5_Terminal
    MT5_Terminal <-->|Encrypted Protocol| TradeServer
```

### Fail-Closed Operational Invariants:
1. **Terminal Disconnect / IPC Socket Collapse:**
   - If `mt5.terminal_info()` reports `connected == False` or IPC call times out $\implies$ immediately transition in-flight orders to `OrderLifecycleState.UNKNOWN`.
   - Halts all further submissions until full terminal reconnection and **6-Dimensional Broker Reconciliation** (`ReconciliationReport`) verify balance, equity, and positions against the internal shadow ledger.
2. **Multi-Account & Multi-Broker Isolation:**
   - Multiple MT5 terminal instances run concurrently via distinct installation paths (`path="C:/Program Files/.../terminal64.exe"`) and portable configurations.
   - Each account binds strictly to an isolated `ExecutionCoordinator` instance identified by `(broker_id, account_id)`.

---

## 5. Security & DPAPI Operational Identity Architecture

- **Windows DPAPI User-Context Bound:**
  - Credentials (`login`, `password`, `server`, `terminal_path`) are encrypted via **Windows DPAPI** (`CurrentUser` scope) and saved strictly at `$env:USERPROFILE\.acash\mt5_credentials.dpapi`.
  - **Operational Constraint:** The DPAPI vault is cryptographically bound to the Windows user account running the process. A service account or different Windows user **cannot** transparently decrypt a user-scoped vault.
  - Required Identity Triad:
    $$\boxed{\text{Credential Owner Identity} \equiv \text{Adapter Runtime Identity} \equiv \text{Terminal Process Owner}}$$
  - **Fail-Closed Behavior:** If the vault cannot be decrypted (e.g. wrong user profile, missing DPAPI key), startup fails closed immediately with `DataContractError("CREDENTIAL_VAULT_DECRYPTION_FAILED")`.
  - **Zero Plaintext Leakage:** `BrokerCredentials` redacts all credentials in `__repr__` and `__str__` (`********`); zero passwords in logs, exceptions, or git commits.

---

## 6. TradingView Decoupled Boundary & Operational Limitations

### A. Webhook Signal Ingress Architecture
```
TradingView Alert (Chart/Indicator)
           │
      HTTP POST (JSON)
           │
           ▼
TradingViewIngressGateway
  ├── HMAC-SHA256 Secret Verification
  ├── IP Whitelist / Timestamp Nonce Check
  ├── Schema Validation (Symbol, Timeframe, Signal Direction)
  └── Envelope Dispatcher
           │
           ▼
CandidateSignalEvent (Raw External Proposal)
           │
           ▼
[ACASH Research -> Validation -> Tournament -> Risk -> Admission]
           │
           ▼
MT5BrokerAdapter (Execution Only if Approved)
```

### B. Operational Limitations & Plan Tier Separation:
1. **Unreliable Auxiliary Ingress:**
   - TradingView webhooks use standard HTTP POST without delivery guarantees or retransmission protocols. Webhook delivery can fail or be delayed under network congestion.
   - The ACASH ingress endpoint is strictly fail-safe: malformed, delayed, or unverified webhook payloads are dropped without disrupting internal cycle schedules.
2. **Zero Inherent Authority:**
   - TradingView signals are **unvalidated proposals**. They enter with **$0.00 capital authority** and must navigate Phase 8.5 qualification, Phase 8 tournament, Phase 9 sovereign risk veto, and Phase 7 execution admission before touching MT5.
3. **Plan Tier Nuances (Free vs. Premium/Ultimate):**
   - **Core ACASH execution does not depend on TradingView plan tiers.**
   - However, TradingView standard alerts (Free/Essential) have a **maximum lifetime of 2 months**, whereas Premium/Ultimate alerts support open-ended continuous operation. ACASH documentation records this constraint so operators do not assume standard tier alerts persist indefinitely.
4. **Visualization:**
   - ACASH maintains its own internal offline visualization dashboard. TradingView chart markers are an optional presentation layer.

---

## 7. Proposed Phase 12 Implementation Slices

```
Slice 1: MT5 Domain Schemas, Enums & Broker Mapping (BMAP-MT5)
   │
   ▼
Slice 2: Symbol Specification Normalizer (BrokerSymbolSpec) & Unit Sizer
   │
   ▼
Slice 3: MT5 Terminal Driver & IPC Transport Bridge (Windows Local)
   │
   ▼
Slice 4: MT5 Broker Adapter (MT5BrokerAdapter) & 6-D Reconciliation Engine
   │
   ▼
Slice 5: TradingView Ingress Gateway (HMAC Sanitizer & Candidate Signal DTO)
   │
   ▼
Slice 6: Full Multi-Venue Integration, 20-Vector Red-Team & Freeze
```

---

## 8. Verification & Next Steps

- **Active Baseline Commit:** `049e155` (`HEAD == origin/main`)
- **Full Test Suite:** 1,020 passed, 0 failures, 2 warnings.
- **Static Type Checker:** MyPy clean across all active modules.
- **Rule:** Do NOT write production code for Phase 12 until this revised Inventory is approved and **Phase 12 Contract Specification v1.0** is drafted and locked.
