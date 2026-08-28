# ACASH — Phase 5 Design Proposal: Event-Driven Backtesting Substrate & NautilusTrader PoC Integration

**Document:** `docs/PHASE_5_DESIGN_PROPOSAL.md`  
**Version:** 1.3.0  
**Date:** 2026-08-28  
**Status:** **COMPLETED & PASSED — 181/181 TESTS (Commit `7f7befc`)**  
**Phase Objective:** Bridge the epistemic gap between **Statistical Predictive Association (Phase 4)** and **Simulated Event-Driven Execution Reality (Phase 5)** using NautilusTrader as an execution substrate while maintaining ACASH as the immutable single source of truth for canonical data, features, hypotheses, accounting, and manifests.

---

> [!NOTE]
> **Static Typing & Runtime Environment Scope Notice:**
> 1. **Mypy Static Typing Scope:** `mypy` is configured with `ignore_missing_imports = true` for `nautilus_trader.*` because NautilusTrader is distributed as Cython C-extensions without complete `.pyi` type stubs. Therefore, static type checking applies strictly to all ACASH internal interfaces, adapters, schemas, and accounting ledgers, while external Nautilus C-internals are verified through real un-mocked execution tests (`@pytest.mark.nautilus`).
> 2. **Environment Verification Binding:** Real-runtime integration is verified and pinned to `Python 3.14.3` + `nautilus-trader==1.231.0` + exact `uv.lock` cryptographic hash.
> 3. **Production Readiness Distinction:** Phase 5 provides verified substrate integration, float-free nanosecond preservation, zero silent rounding, and sovereign double-entry shadow accounting. Multi-venue live production readiness remains deferred to Phases 11–13.


---

## 1. Epistemic Architecture & Separation of Concerns

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             ACASH CORE (Source of Truth)                         │
│  - Canonical Market Data (Trades/Book)     - Microstructure Feature Engine       │
│  - Hypothesis Specifications & Research    - Canonical Portfolio Accounting      │
│  - Invariants, Risk Bounds & Ledgers       - Research & Backtest Manifests       │
└─────────────────────────┬────────────────────────────────────────────────────────┘
                          │ Adapter Translation (Feeds & Telemetry)
                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   NAUTILUS TRADER (Execution Substrate / Runtime Engine)          │
│  - Event-Driven Event Loop (Simulated Engine / Clock)                            │
│  - High-Precision Matching Engine (Order Book & Trades Replay)                   │
│  - Order Lifecycle State Machine (SUBMITTED -> ACCEPTED -> FILLED / CANCELLED)   │
│  - Latency & Queue Position Emulation                                            │
└─────────────────────────┬────────────────────────────────────────────────────────┘
                          │ Event Stream & Execution Telemetry
                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         REALITY-GAP TELEMETRY & ATTRIBUTION                      │
│  Research Assumption (Phase 4) ──► Simulated Execution (Phase 5) ──► Live (Ph 13)│
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Invariant Ownership Boundary

| Subsystem Domain | ACASH Core Ownership (Immutable) | NautilusTrader Substrate Role |
| :--- | :--- | :--- |
| **Historical Data** | DuckDB/Parquet Canonical Schema (Nanosecond PIT) | Ingests converted data objects (`DataCatalog` / `DataFeeder`) |
| **Alpha Signals** | Pure mathematical functions from Phase 3C/4 | Encapsulated in strategy actor handlers |
| **Order Matching** | Verification criteria and sanity checks | High-speed matching engine & queue emulation |
| **Cash & Equity Accounting** | Immutable double-entry ledger (`PortfolioState`, `CashBalance`) | Internal trading node accounting (verified against ACASH) |
| **Cost & Latency Models** | Mathematical cost formulas & latency distribution parameters | Execution node simulation parameterization |
| **Provenance & Lineage** | `BacktestManifest` with deterministic content hashes | Generates execution telemetry events |

---

## 2. Ten Core Semantic Specifications

### 2.1 Event Ordering Semantics & Adapter Ordering Policy
1. **Total Order Invariant (Aligning with Phase 3B Contract):** All simulated events within the backtest substrate are strictly sequenced by the deterministic 5-tuple:
   $$\text{EventOrder} = (T_{\text{event\_utc}}, \text{source\_order\_key}, \text{message\_rank}, \text{stream\_id}, \text{row\_sub\_index})$$
2. **Adapter Ordering Policy:** The NautilusTrader adapter MUST NOT assume integer sequence numbers are universally orderable across different feeds. Sequence ordering is source-specific and mediated via the canonical `source_order_key` byte-wise lexicographical order established in Phase 3B.
3. **Causal Timestamp Integrity:** An order generated at time $t$ in response to a market event arriving at $T_{\text{decision}}$ cannot be matched or processed at a matching engine timestamp $T_{\text{match}} < T_{\text{decision}} + \Delta T_{\text{latency}}$.
4. **No Retroactive State Reversal:** Market data events and fill messages are append-only.

### 2.2 Order Lifecycle State Machine
```
[CREATED] ──► [SUBMITTED] ──► [ACCEPTED] ──► [PARTIALLY_FILLED] ──► [FILLED]
    │             │               │                 │
    ▼             ▼               ▼                 ▼
[REJECTED]   [REJECTED]      [CANCELLED]       [CANCELLED]
```
- **Terminal States:** `FILLED`, `CANCELLED`, `REJECTED`, `EXPIRED`.
- **State Transition Invariants:**
  - Transition events are recorded with exact monotonic timestamp and reason code.
  - Zero state skipping: An order cannot transition directly from `CREATED` to `FILLED` without traversing `SUBMITTED` and `ACCEPTED`.

### 2.3 Fill and Partial-Fill Semantics
1. **Maker (Passive) Orders:**
   - Evaluated against Top-of-Book and depth updates.
   - Requires queue priority position emulation (FIFO or Pro-Rata).
   - Fills only occur when opposing aggressive trades trade through or match at the order's limit price.
2. **Taker (Aggressive) Orders:**
   - Consumes available liquidity from the canonical order book snapshot/delta at the moment of execution.
   - If order size $V_{\text{order}} > V_{\text{BBO}}$, sweeps depth across levels ($L_1, L_2, \dots, L_k$) computing Volume-Weighted Average Fill Price (VWAP).
   - If liquidity is exhausted before size is fulfilled, residual quantity is either cancelled (IOC/FOK) or placed on book (GTC) depending on order type.

### 2.4 Spread, Slippage, and Latency Modeling
1. **Quoted Spread Model:**
   $$\text{Spread}_{\text{cost}} = \frac{P_{\text{ask}} - P_{\text{bid}}}{2}$$
2. **Latency Model (Dual-Sided):**
   - **Signal/Decision Latency ($\Delta T_{\text{calc}}$):** Processing delay from feature computation to order creation.
   - **Uplink Transit Latency ($\Delta T_{\text{uplink}}$):** Network wire delay from client to simulated exchange gateway ($T_{\text{gateway}} = T_{\text{created}} + \Delta T_{\text{uplink}}$).
   - **Matching Engine Processing Delay ($\Delta T_{\text{engine}}$):** Internal exchange matching serialization delay.
   - **Downlink Execution Ack Latency ($\Delta T_{\text{downlink}}$):** Network transit delay of execution report back to strategy.
3. **Execution Slippage Function:**
   $$P_{\text{fill}} = P_{\text{expected}} + \text{Sign}(\text{Side}) \cdot \left(\text{SpreadHalf} + \text{Slippage}_{\text{fixed}} + \text{Impact}(V_{\text{order}}, \text{Depth})\right)$$

### 2.5 Formalized Double-Entry Accounting Views & Anti-Double-Counting Invariant
To prevent fatal double-counting of Realized PnL (since ACASH's `CashBalance` already incorporates closed-trade cash flows and deducted fees), accounting is strictly decoupled into two distinct views:

1. **Balance-Sheet (State Snapshot) View:**
   $$\text{Ending Equity}_t = \text{CashBalance}_t + \sum_{i} \text{UnrealizedPnL}_{i, t}$$
   *(where $\text{CashBalance}_t$ is the sovereign realized cash balance including closed-position realized PnL, cash flows, and fees).*

2. **Performance Attribution (Flow Reconciliation) View:**
   $$\text{Ending Equity}_t = \text{Starting Equity}_0 + \sum_{\tau=1}^t \text{External Cash Flows}_\tau + \sum_{\tau=1}^t \text{Realized PnL}_\tau + \text{Unrealized PnL}_t - \sum_{\tau=1}^t \text{Trading Fees}_\tau - \sum_{\tau=1}^t \text{Financing Costs}_\tau$$

3. **Anti-Double-Counting Invariant:**
   $$\text{Equity}_{\text{BalanceSheet}, t} \equiv \text{Equity}_{\text{PerformanceAttribution}, t}$$
   *Rule:* The Balance-Sheet View and Performance Attribution View must NEVER be blended or summed together.

4. **Substrate Independent Verification & Residual Invariant:**
   - ACASH maintains an independent shadow double-entry ledger of all cash balances, margin allocations, and positions.
   - Every simulated fill emitted by NautilusTrader is ingested by ACASH's `DecisionLedger` and verified:
     $$\text{AccountingResidual}_t = \text{Equity}_{\text{ACASH State}, t} - \text{Equity}_{\text{Nautilus}, t}$$
     $$\text{Invariant: } |\text{AccountingResidual}_t| \le \epsilon$$
     where $\epsilon = \text{Decimal}("0.0000000001")$ (exact numeric zero within fixed-precision Decimal-18 arithmetic). Any non-zero discrepancy outside rounding precision triggers immediate backtest invalidation.

### 2.6 Historical Replay Determinism & Pinned Environment Reproducibility
1. **Deterministic Pinned Environment Contract:** Bitwise reproducibility of trade logs, fills, equity curves, and performance metrics is guaranteed under a strictly pinned execution environment:
   - ACASH software version & Git commit hash
   - `pyproject.toml` configuration & resolved `uv.lock` dependency lockfile
   - NautilusTrader pinned release version
   - Python runtime version (`3.14.x`) and architecture
   - Canonical input data logical hashes (`canonical_data_hashes`)
   - Complete engine and strategy parameter configuration
   - Deterministic integer pseudo-random number generator (PRNG) seed
   - Timezone database (`tzdata`) version
2. **Zero Unseeded Randomness:** Any simulated jitter, network packet reordering, or latency sampling must use deterministic PRNGs initialized with the run seed.

### 2.7 Deterministic BacktestManifest Identity & Lineage
To eliminate reproducibility contradictions between random UUIDs and bitwise replay invariance, `BacktestManifest` identity is strictly **content-derived**:
$$\text{manifest\_id} = \text{SHA256}(\text{canonical}(\text{hypothesis\_spec\_hash} + \text{canonical\_data\_hashes} + \text{engine\_config\_hash} + \text{strategy\_config\_hash} + \text{seed}))[:32]$$
- **Lineage Structure:**
  - `manifest_id`: Deterministic 32-character hex string.
  - `hypothesis_id` & `hypothesis_spec_sha256`: Cryptographic linkage to Phase 4 hypothesis.
  - `canonical_data_hashes`: List of SHA-256 digests of all input market data chunks.
  - `engine_config_hash`: Hash of latency, fee, slippage, and execution parameters.
  - `strategy_config_hash`: Hash of strategy actor configuration.
  - `prng_seed`: Integer seed.
  - `execution_summary`:
    - Total Fills Count, Volume Executed, Total Fees (bps and USD).
    - Realized PnL, Sharpe Ratio, Sortino Ratio, Maximum Drawdown (MDD).
    - Reality Gap Metrics: Difference between Phase 4 Tier 3 Economic Edge and Phase 5 Simulated Net PnL.
- **Volatile Execution Timestamps:** `computed_at_utc` and `wall_clock_duration_ms` are recorded as auxiliary runtime metadata and **MUST NEVER** participate in the reproducibility hash or `manifest_id`.

### 2.8 Reality-Gap Telemetry Hooks
Phase 5 introduces explicit telemetry tracking the delta between analytical assumptions and simulated execution:
$$\Delta_{\text{Reality}} = \text{Edge}_{\text{Phase 4 Analytical (Tier 3)}} - \text{Edge}_{\text{Phase 5 Simulated Realized}}$$
- **Spread Drag Delta:** Quoted spread vs. actual executed spread.
- **Latency Slip Drag:** Slippage attributable to order transit delay.
- **Queue Position Drag:** Lost alpha due to non-execution of passive limit orders.

### 2.9 Failure and Crash Behavior
- If the Nautilus engine receives malformed timestamps or out-of-order market events, it must halt deterministically rather than silently interpolating.
- Corrupted backtest runs produce no manifest and are quarantined.

### 2.10 Deferred to Future Phases (Explicit Scope Boundaries)
- **Phase 6:** Formal multi-regime statistical hypothesis testing, combinatorial purged cross-validation (CPCV), and deflated Sharpe ratio.
- **Phase 7–10:** Portfolio optimization (skfolio), dynamic risk kill-switches, and non-linear multi-asset impact models.
- **Phase 11–13:** Live paper trading, MetaTrader 5 (MT5) bridge, FIX protocol adapters, and live execution.

---

## 3. Implementation Blueprint for Phase 5

```
src/acash/backtest/
├── __init__.py           # Public exports
├── schema.py             # BacktestConfiguration, SimulationLatencyConfig, BacktestManifest
├── adapter.py            # Canonical DuckDB/Parquet to NautilusTrader Data Adapter with EventOrderingPolicy
├── engine.py             # Event-driven backtesting execution runner wrapping Nautilus substrate
├── accounting.py         # ACASH Independent Double-Entry Shadow Ledger & Sanity Verifier
├── telemetry.py          # Reality Gap telemetry & Attribution Metrics
└── strategies/           # Encapsulated Baseline Strategy Actors
    ├── __init__.py
    ├── imbalance_actor.py
    └── vwap_actor.py
```

---

## 4. Gate 5 Acceptance Criteria
1. **Substrate Separation:** NautilusTrader operates strictly as an execution substrate; zero leakage of canonical accounting ownership.
2. **Deterministic Content-Derived Identity:** Rerunning identical canonical data + hypothesis + engine config + strategy config + seed produces bitwise-identical `manifest_id` and backtest logs.
3. **Event Ordering Compatibility:** Adapter orders events via the canonical Phase 3B `(event_time_utc, source_order_key, message_rank, stream_id, row_sub_index)` contract without assuming generic integer sequence monotonicity.
4. **Double-Entry Cash Conservation & Anti-Double Counting:** Balance-Sheet View and Performance Attribution View are strictly isolated; ACASH shadow ledger matches Nautilus fills with $|\text{AccountingResidual}| \le 10^{-10}$ (exact numeric zero).
5. **Pinned Dependency Reproducibility:** Environment reproducibility contract is strictly anchored to `pyproject.toml` + `uv.lock` + ACASH Git commit.
6. **Reality Gap Accounting:** Telemetry captures exact breakdown of spread, latency, and slippage drag against Phase 4 analytical baselines.
7. **No Production Execution:** 100% free of live broker adapters, MT5, or live trading connections.
8. **Regression Integrity:** 100% pytest pass rate across all 139 existing tests + Phase 5 tests, 0 mypy errors.

---

## 5. Review & Sign-off State
**This proposal (v1.2.0) is submitted for human architectural review. No Phase 5 implementation code will be written until formal human sign-off is granted.**
