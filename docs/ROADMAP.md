# ACASH — System Development Roadmap (Phases 0–16)

**Document:** `docs/ROADMAP.md`  
**Version:** 3.3.0  
**Date:** 2026-08-28  
**Governance Principle:** Sequential Phase Progression. No phase skipping. Every phase has explicit gates, acceptance criteria, and human approval checkpoints.

---

## Roadmap Overview

```
✅ Phase 0: Discovery & Architecture ──► [COMPLETED - PASSED]
   │
   ▼
✅ Phase 1: Foundation & Domain Core ──► Gate 1 [COMPLETED - PASSED — 27/27 Tests]
   │
   ▼
✅ Phase 2: Data Ingestion & Integrity Engine ──► Gate 2 [COMPLETED - PASSED — 57/57 Tests]
   │
   ▼
✅ Phase 3: Point-in-Time Microstructure & Feature Engine (3A/3B/3C) ──► Gate 3 [COMPLETED - PASSED — 122/122 Tests]
   ├─ ✅ Phase 3A: Canonical Trades Domain
   ├─ ✅ Phase 3B: Canonical Order Book Domain
   └─ ✅ Phase 3C: Microstructure Feature Engine
   │
   ▼
✅ Phase 4: Alpha Research Engine & Hypotheses ──► Gate 4 [COMPLETED - PASSED — 139/139 Tests]
   │
   ▼
✅ Phase 5: Backtesting Substrate & Simulation Engine ──► Gate 5 [COMPLETED - PASSED — 200/200 Tests]
   │
   ▼
✅ Phase 6: Statistical Validation & Overfitting Controls ──► Gate 6 [COMPLETED - PASSED — 252/252 Tests]









   │
   ▼

⏳ Phase 7: Regime Engine (Prove or Remove) ──► Gate 7 [UPCOMING]
   │
   ▼
⏳ Phase 8: Portfolio Engine (skfolio & Baselines) ──► Gate 8
   │
   ▼
⏳ Phase 9: Deterministic Risk Engine & Kill Switch ──► Gate 9

   │
   ▼
⏳ Phase 10: Transaction Cost & Slippage Modeling ──► Gate 10
   │
   ▼
⏳ Phase 11: Paper Trading Subsystem ──► Gate 11
   │
   ▼
⏳ Phase 12: MT5 & Venue Execution Adapters ──► Gate 12
   │
   ▼
⏳ Phase 13: Live Small Capital (MANDATORY HUMAN APPROVAL) ──► Gate 13
   │
   ▼
⏳ Phase 14: AI Quantitative Research Layer ──► Gate 14
   │
   ▼
⏳ Phase 15: Strategy Lifecycle State Machine ──► Gate 15
   │
   ▼
⏳ Phase 16: Performance Degradation & Data Flywheel ──► Ongoing
```

---

## Detailed Phase Breakdown

### ✅ Phase 0: Discovery & Architecture [COMPLETED - PASSED]
- **Objective:** Evaluate technologies, define domain architecture, produce ADRs, risk register, and establish project boundaries.
- **Deliverables:** Complete documentation suite in `docs/`.
- **Gate 0 Criteria:** Technology candidate matrix approved; architecture review signed off; Phase 1 implementation plan approved.

---

### ✅ Phase 1: Foundation & Domain Core [COMPLETED - PASSED]
- **Objective:** Establish the modular monolith structure, domain types, abstract interfaces, configuration management, structured logging, in-memory mock adapters, and correctness test harness.
- **Deliverables:**
  - Python project environment (`pyproject.toml`, virtual environment).
  - Core domain models (`Instrument`, `Bar`, `MarketDataSnapshot`, `Signal`, `TargetAllocation`, `RiskAssessment`, `Order`, `Fill`).
  - Core interface definitions (`IMarketDataProvider`, `IFeatureEngine`, `IStrategy`, `IPortfolioOptimizer`, `IRiskEngine`, `IBacktestEngine`, `IExecutionEngine`, `IDecisionLedger`).
  - Mock in-memory execution engine and market data provider for unit testing.
  - Structured JSON logger and typed configuration loader (`Pydantic` + `YAML`).
  - Unit and contract test suite verifying domain invariants, invalid states, interface contracts, serialization, and deterministic equivalent outcomes.
- **Gate 1 Criteria:** All unit tests pass (27/27); domain invariants verified; typing strictly enforced (`mypy` clean); zero live broker or Nautilus dependencies in core.

---

### ✅ Phase 2: Data Ingestion & Integrity Engine [COMPLETED - PASSED]
- **Objective:** Implement reliable ingestion for **one market** and **one primary data source** with strict point-in-time validation.
- **Deliverables:**
  - Ingestion adapter (`yfinance` research adapter / local Parquet for single liquid symbol).
  - Normalization pipeline with timestamp timezone enforcement (UTC only) and sequencing verification.
  - Automated data integrity checker (detects missing timestamps, impossible negative prices, duplicates, unit errors).
  - Provenance tracker recording dataset hash and retrieval metadata.
  - Recoverable Batch Commit Protocol (`PREPARED` $\to$ `PART_PUBLISHED` $\to$ `COMMITTED`).
  - DuckDB Point-in-Time qualification layer with multi-source isolation and lookahead prevention.
- **Gate 2 Criteria:** Data validation suite catches 100% of synthetic data corruption test cases (57/57 tests pass, `mypy` clean).

---

### ✅ Phase 3: Point-in-Time Feature Engine (3A/3B/3C) [COMPLETED - PASSED]
- **Objective:** Build modular, deterministic feature calculations with zero look-ahead bias across Trades, Order Book, and Microstructure.
- **Deliverables:**
  - **Phase 3A:** Canonical Trades Domain (Time & Sales, Aggressor Side flags, length-prefixed hashing).
  - **Phase 3B:** Canonical Order Book (L2 Depth Multi-Row Frames & Deltas, L3 MBO, deterministic 5-tuple order).
  - **Phase 3C:** Microstructure Feature Engine (Session VWAP, Volume Profile with POC lower-price tie-breakers, Value Area 70% bounds, Footprint Analytics, Depth-Weighted Micro-Price).
  - Dual-temporal point-in-time filtering ($T_{\text{event}} \le T_{\text{decision}} \land T_{\text{knowledge}} \le T_{\text{as\_of}}$).
- **Gate 3 Criteria:** Automated leakage unit tests verify zero future bar indexing; 122/122 tests pass, `mypy` clean.

---

### ✅ Phase 4: Alpha Research Engine & Baseline Hypotheses [COMPLETED - PASSED]
- **Objective:** Implement formal hypothesis registration, econometric OLS slope Beta HAC inference under Bartlett kernel, discrete forward returns, interval-based purging/embargo, and durable Blind OOS governance.
- **Deliverables:**
  - Hypothesis specification schema (`HypothesisSpecification`, `InvalidationCriteria`, parameter spaces).
  - Discrete bar-indexed forward returns ($R(t,H)$) with next-bar open entry alignment.
  - Econometric OLS slope $\hat{\beta}_H$ inference with Newey-West HAC covariance under Bartlett kernel.
  - Descriptive non-parametric association metrics: Pearson IC, Spearman Rank IC (fractional ties), autocorrelation.
  - 3-tier friction waterfall (Raw Edge $\to$ Net Edge $\to$ Economic Edge).
  - Interval-based boundary purging and unallocated embargo gaps ($\ge \max(H)$ bars).
  - Durable Blind OOS Governance Ledger (`data/manifests/research/governance_ledger.json`) with strict re-tuning locks (`UNEXPOSED` $\to$ `EVALUATED_LOCKED` $\to$ `EXHAUSTED`).
  - Baseline research models: Microstructure Imbalance Skew, VWAP Mean Reversion, Multi-Horizon Momentum.
- **Gate 4 Criteria:** Strategies generate reproducible signals on historical data without look-ahead errors; 139/139 unit tests pass, `mypy` clean.

---

### ✅ Phase 5: Backtesting Substrate & Simulation Engine [COMPLETED - PASSED]
- **Objective:** Establish the deterministic event-driven simulation backtest substrate preserving ACASH as the single source of truth for canonical data, features, accounting, and manifests.
- **Deliverables:**
  - Event-driven backtesting execution substrate with full simulated order lifecycle state machine.
  - Canonical Data Adapter with Phase 3B total ordering 5-tuple contract: $(T_{\text{event\_utc}}, \text{source\_order\_key}, \text{message\_rank}, \text{stream\_id}, \text{row\_sub\_index})$.
  - Realistic friction simulation (maker/taker fee tiers, bid/ask spread, fixed & dynamic slippage, causal dual-sided latency).
  - Independent double-entry shadow ledger decoupling Balance-Sheet View from Performance Attribution View ($|\text{AccountingResidual}| \le 10^{-10}$).
  - Deterministic content-derived `BacktestManifest` identity: $\text{manifest\_id} = \text{SHA256}(\text{canonical}(\text{hypothesis\_hash} + \text{data\_hashes} + \text{engine\_hash} + \text{strategy\_hash} + \text{seed}))[:32]$.
  - Reality Gap Telemetry Engine implementing disjoint non-overlapping reference-price decomposition: Spread Drag, Slippage Drag, Latency Drag, Fee Drag, Maker Adverse Selection Drag, and Unmodelled Residual.
  - Baseline strategy actors: Microstructure Imbalance (OBI) & Session VWAP Mean Reversion.
- **Gate 5 Criteria:** Bitwise-identical replay across identical inputs/configs, exact double-entry cash conservation, unmocked NautilusTrader integration, and zero phantom liquidity; 200/200 tests pass, `mypy` clean.



---

### ✅ Phase 6: Statistical Validation & Overfitting Controls [COMPLETED - PASSED]

- **Objective:** Enforce quantitative validation gates to eliminate data-snooping, selection bias, and backtest overfitting.
- **Deliverables:**
  - Combinatorial Purged Cross-Validation (CPCV) engine with contiguous $N$-group partitioning, exhaustive $\binom{N}{k}$ combinations, strict $[t+1, t+H]$ interval purging, post-test embargo buffers, and continuous pseudo-OOS path reconstruction ($\phi = \frac{k}{N}\binom{N}{k}$).
  - Deflated Sharpe Ratio (DSR) & Minimum Track Record Length (MinTRL) engine implementing Bailey & López de Prado (2014) non-normal asymptotic inference with Euler-Mascheroni constant $\gamma_E$, empirical trial variance $V$, Fisher-Pearson skewness $g_1$, and Pearson kurtosis $g_2$.
  - Multiple-testing accounting: Holm-Bonferroni step-down (FWER), Benjamini-Hochberg (FDR), and Harvey-Liu-Zhu (2016) Haircut Sharpe Ratio.
  - Probability of Backtest Overfitting (PBO) log-odds evaluation and parameter surface curvature / fragility testing across mandatory $\pm 25\%$ parameter grids.
  - Sovereign `StatisticalValidationGate` orchestrating multi-gate sequential evaluation, authoritative $K_{\text{ledger}} \equiv K_{\text{DSR}} \equiv K_{\text{Holm}} \equiv K_{\text{BH}}$ trial coupling, fail-closed missing data defense, and emitting immutable `ValidationReport` certificates with dual cryptographic lineage digests.
- **Gate 6 Criteria:** Strategies must satisfy DSR $\ge 0.95$, MinTRL, Holm-Bonferroni FWER significance, PBO $< 0.25$, flat parameter curvature, analytical friction monotonicity, and sealed OOS performance retention ($\text{SR}_{\text{OOS}} \ge 0.50 \cdot \text{SR}_{\text{IS}}$); 252/252 tests pass, `mypy` clean.











---

### ⏳ Phase 7: Regime Engine [UPCOMING]
- **Objective:** Detect market regimes (volatility, trend, liquidity) and verify their utility.
- **Deliverables:**
  - Volatility regime detector (Realized Volatility percentile / GARCH filter).
  - Trend regime classifier (ADX / moving average slope).
  - Controlled ablation study: Strategy performance with regime filter vs without.
- **Gate 7 Criteria:** Regime filter must prove statistically significant improvement in risk-adjusted return net of turnover; otherwise, dropped.

---

### ⏳ Phase 8: Portfolio Engine (skfolio & Baselines) [UPCOMING]
- **Objective:** Allocate capital across candidate assets/signals and cash ("NOWHERE").
- **Deliverables:**
  - Transparent Baseline Allocators: Equal Weight (1/N), Inverse Volatility (1/$\sigma$), 100% Cash.
  - `skfolio` portfolio optimization and risk-allocation methods including HRP, ERC and CVaR-based approaches.
  - Hurdle rate gate: If return < cost + hurdle, allocate to Cash.
- **Gate 8 Criteria:** `skfolio` must be evaluated for statistically significant incremental value versus transparent baselines out-of-sample; fallback to baseline if optimizer fails.

---

### ⏳ Phase 9: Deterministic Risk Engine & Kill Switch [UPCOMING]
- **Objective:** Implement non-negotiable risk boundaries that overrule all upstream models.
- **Deliverables:**
  - Position limits, maximum leverage limit, maximum portfolio drawdown limit, daily loss limit.
  - Deterministic Risk Evaluator: `evaluate_allocation(...) -> Approved / Reduced / Rejected`.
  - Global Kill Switch: Immediate order cancellation and position flattening.
- **Gate 9 Criteria:** 100% passing rate on risk violation tests (oversized orders, drawdown breaches, rapid loss triggers).

---

### ⏳ Phase 10: Transaction Cost & Slippage Modeling [UPCOMING]
- **Objective:** Embed high-fidelity friction models into every strategy evaluation.
- **Deliverables:**
  - Non-linear slippage models based on market volatility and order size relative to volume.
  - Spread and commission tables for target assets.
  - Net P&L verification harness.
- **Gate 10 Criteria:** Backtests evaluate strictly on Net P&L after friction; zero gross-only reporting permitted.

---

### ⏳ Phase 11: Paper Trading Subsystem [UPCOMING]
- **Objective:** Real-time simulated execution against live market feeds.
- **Deliverables:**
  - Live data ingestion stream $\to$ Signal $\to$ Portfolio $\to$ Risk $\to$ Paper Execution.
  - Paper trade ledger recording signal timestamp, order timestamp, simulated fill, and slippage.
  - Continuous runtime operational verification.
- **Gate 11 Criteria:** Paper trading operates continuously without unhandled exceptions or state desynchronization.

---

### ⏳ Phase 12: MT5 & Venue Execution Adapters [UPCOMING]
- **Objective:** Build thin, secure broker connectivity adapters.
- **Deliverables:**
  - MetaTrader 5 (MT5) IPC Gateway / Execution Adapter.
  - Account state, position, and order reconciliation loop.
  - Strict boundary: Zero strategy logic inside MT5/MQL5.
- **Gate 12 Criteria:** Order roundtrip latency and reconciliation tested in demo/staging broker account.

---

### ⏳ Phase 13: Live Small Capital Deployment [UPCOMING]
- **Objective:** Real-world execution validation with micro-capital.
- **Deliverables:**
  - Live execution harness with minimum position sizes (micro-lots).
  - Live telemetry dashboard and real-time risk monitor.
  - Reconciliation between expected vs broker execution prices.
- **Gate 13 Criteria:** **EXPLICIT HUMAN APPROVAL REQUIRED (Section 37)**; all safety gates, kill switches, and alerts verified operational.

---

### ⏳ Phase 14: AI Quantitative Research Layer [UPCOMING]
- **Objective:** Augment quant research with AI-driven hypothesis generation and reporting.
- **Deliverables:**
  - LLM hypothesis formulation assistant (`acash.research.ai`).
  - Automated research report generator conforming to Section 33.
  - Exploratory feature discovery tools.
- **Gate 14 Criteria:** AI outputs are treated strictly as unvalidated proposals; must pass full backtesting and statistical validation gates.

---

### ⏳ Phase 15: Strategy Lifecycle Management [UPCOMING]
- **Objective:** Enforce automated governance from idea generation to retirement.
- **Deliverables:**
  - Strategy lifecycle state machine (`IDEA` $\to \dots \to$ `PRODUCTION` $\to$ `REDUCE` $\to$ `RETIRE`).
  - Rolling metric monitors (Sharpe, Drawdown, Profit Factor vs historical expectations).
- **Gate 15 Criteria:** Automated downgrade triggered when strategy underperforms statistical confidence bands.

---

### ⏳ Phase 16: Performance Degradation & Data Flywheel [UPCOMING]
- **Objective:** Build long-term memory of decisions, outcomes, and market states.
- **Deliverables:**
  - Decision outcome recorder linking decisions to multi-horizon forward returns.
  - Degradation detector measuring statistical divergence in live vs backtest performance.
  - Proprietary decision memory database.
- **Gate 16 Criteria:** Continuous logging of all live decisions and automated alert on performance divergence.

---

## Reality Gap Analysis & Execution Deviation

The core empirical objective of ACASH is measuring:
> *"How much does what we expected in simulation diverge from what actually happened in the live market?"*

```
                 BACKTEST SIMULATION
                          │
                          ▼
                 PAPER / SHADOW TRADING
                          │
                          ▼
                    LIVE EXECUTION
                          │
                          ▼
               REALITY GAP ATTRIBUTION
```

### Multi-Phase Reality Pipeline:
- **Phase 2+ (Data Quality):** Data fidelity matching strategy horizon, timestamp integrity, provenance, spread capture.
- **Phase 5+ (Backtest):** Tick-aware simulation, data-supported spread fidelity, graduated slippage models (simple $\to$ calibrated $\to$ liquidity-aware).
- **Phase 6+ (Validation):** OOS, walk-forward matrix, forward testing, stress testing, regime analysis.
- **Phase 12+ (Live):** Actual fills, realized spreads, actual slippage, latency, broker reconciliation.
- **Phase 13+ (Reality Gap Attribution):** Systematic deviation tracking attributed to: Data error, Model/alpha error, Execution error, or Venue conditions.

### Deviation Metrics & Example:
| Metric | Expected (Simulation) | Actual (Live) | Reality Gap Deviation |
| :--- | :--- | :--- | :--- |
| **Entry Price** | 100.00 | 100.07 | **+7 bps** |
| **Prevailing Spread** | 2 bps | 9 bps | **+7 bps** |
| **Execution Slippage** | 1 bp | 6 bps | **+5 bps** |
| **Trade PnL** | +$240 | +$181 | **-24.6%** |
| **Roundtrip Latency** | 15 ms | 120 ms | **+105 ms** |

---

## License Notice

**Copyright © 2026 Ratthabhumi & ACASH Contributors. All Rights Reserved.**  
Proprietary and Confidential. Unauthorized copying, distribution, modification, or extraction is strictly prohibited.
