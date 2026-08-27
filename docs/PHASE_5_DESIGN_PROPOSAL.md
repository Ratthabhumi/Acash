# ACASH — Phase 5 Design Proposal: Event-Driven Backtesting Substrate & NautilusTrader PoC Integration

**Document:** `docs/PHASE_5_DESIGN_PROPOSAL.md`  
**Version:** 1.0.0  
**Date:** 2026-08-28  
**Status:** **PROPOSED — AWAITING ARCHITECTURAL REVIEW & SIGN-OFF**  
**Phase Objective:** Bridge the epistemic gap between **Statistical Predictive Association (Phase 4)** and **Simulated Event-Driven Execution Reality (Phase 5)** using NautilusTrader as an execution substrate while maintaining ACASH as the immutable single source of truth for canonical data, features, hypotheses, accounting, and manifests.

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
| **Provenance & Lineage** | `BacktestManifest` with cryptographic hashes | Generates execution telemetry events |

---

## 2. Ten Core Semantic Specifications

### 2.1 Event Ordering Semantics
1. **Total Order Invariant:** All simulated events within the substrate are strictly sequenced by the 5-tuple:
   $$\text{EventOrder} = (T_{\text{event\_utc}}, \text{message\_rank}, \text{sequence\_num}, \text{stream\_id}, \text{row\_sub\_index})$$
2. **Causal Timestamp Integrity:** An order generated at time $t$ in response to a market event arriving at $T_{\text{decision}}$ cannot be matched or processed at a matching engine timestamp $T_{\text{match}} < T_{\text{decision}} + \Delta T_{\text{latency}}$.
3. **No Retroactive State Reversal:** Market data events and fill messages are append-only.

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

### 2.5 Portfolio Accounting Boundary & Double-Entry Invariants
1. **Independent Verification Ledger:**
   - ACASH maintains an independent shadow ledger of all cash balances, margin allocations, and positions.
   - Every simulated fill emitted by NautilusTrader is ingested by ACASH's `DecisionLedger` and verified against:
     $$\text{Equity}_t = \text{CashBalance}_t + \sum_{i} \left( \text{Position}_{i, t} \times P_{\text{market}, i, t} \right) - \text{UnrealizedFees}_t$$
2. **Cash Conservation Invariant:**
   - Sum of realized PnL, cash injections, trading fees, and financing costs must strictly balance to zero discrepancy.

### 2.6 Historical Replay Determinism
1. **Zero Randomness without Explicit Seed:** All latency distributions, randomized jitter, or tie-breakers must use deterministic pseudo-random generators seeded with cryptographic run parameters.
2. **Replay Invariance:** Re-running the identical backtest configuration against identical canonical Parquet files must produce bitwise-identical trade logs, fills, equity curves, and manifests.

### 2.7 Backtest Reproducibility & BacktestManifest
Every Phase 5 simulation emits an immutable `BacktestManifest`:
- `manifest_id`: Unique identifier (`bkt_{hypothesis_id}_{timestamp}_{uuid}`).
- `hypothesis_id` & `hypothesis_spec_sha256`: Cryptographic linkage to Phase 4 hypothesis.
- `canonical_data_hashes`: List of SHA-256 digests of all input market data chunks.
- `engine_config_hash`: Hash of latency, fee, slippage, and execution parameters.
- `execution_summary`:
  - Total Fills Count, Volume Executed, Total Fees (bps and USD).
  - Realized PnL, Sharpe Ratio, Sortino Ratio, Maximum Drawdown (MDD).
  - Reality Gap Metrics: Difference between Phase 4 Tier 3 Economic Edge and Phase 5 Simulated Net PnL.

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
├── adapter.py            # Canonical DuckDB/Parquet to NautilusTrader Data Adapter
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
2. **Deterministic Replay:** Identical inputs produce bitwise-identical trade logs, fills, and manifests across multiple execution runs.
3. **Double-Entry Cash Conservation:** ACASH shadow ledger matches Nautilus fills with 0 cash discrepancy.
4. **Reality Gap Accounting:** Telemetry captures exact breakdown of spread, latency, and slippage drag against Phase 4 analytical baselines.
5. **No Production Execution:** 100% free of live broker adapters, MT5, or live trading connections.
6. **Regression Integrity:** 100% pytest pass rate across all 139 existing tests + Phase 5 tests, 0 mypy errors.

---

## 5. Review & Sign-off State
**This proposal is submitted for human architectural review. No Phase 5 implementation code will be written until formal human sign-off is granted.**
