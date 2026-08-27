# ACASH — System Development Roadmap (Phases 0–16)

**Document:** `docs/ROADMAP.md`  
**Version:** 3.1.0  
**Date:** 2026-08-27  
**Governance Principle:** Sequential Phase Progression. No phase skipping. Every phase has explicit gates, acceptance criteria, and human approval checkpoints.

---

## Roadmap Overview

```
Phase 0: Discovery & Architecture [CURRENT - READY FOR APPROVAL]
   │
   ▼
Phase 1: Foundation & Domain Core ──► Gate 1
   │
   ▼
Phase 2: Data Ingestion & Integrity Engine ──► Gate 2
   │
   ▼
Phase 3: Point-in-Time Feature Engine ──► Gate 3
   │
   ▼
Phase 4: Alpha Research Engine & Hypotheses ──► Gate 4
   │
   ▼
Phase 5: Backtesting Substrate & Nautilus PoC ──► Gate 5
   │
   ▼
Phase 6: Statistical Validation & OOS Hard Gate ──► Gate 6
   │
   ▼
Phase 7: Regime Engine (Prove or Remove) ──► Gate 7
   │
   ▼
Phase 8: Portfolio Engine (skfolio & Baselines) ──► Gate 8
   │
   ▼
Phase 9: Deterministic Risk Engine & Kill Switch ──► Gate 9
   │
   ▼
Phase 10: Transaction Cost & Slippage Modeling ──► Gate 10
   │
   ▼
Phase 11: Paper Trading Subsystem ──► Gate 11
   │
   ▼
Phase 12: MT5 & Venue Execution Adapters ──► Gate 12
   │
   ▼
Phase 13: Live Small Capital (MANDATORY HUMAN APPROVAL) ──► Gate 13
   │
   ▼
Phase 14: AI Quantitative Research Layer ──► Gate 14
   │
   ▼
Phase 15: Strategy Lifecycle State Machine ──► Gate 15
   │
   ▼
Phase 16: Performance Degradation & Data Flywheel ──► Ongoing
```

---

## Detailed Phase Breakdown

### Phase 0: Discovery & Architecture (Current)
- **Objective:** Evaluate technologies, define domain architecture, produce ADRs, risk register, and establish project boundaries.
- **Deliverables:** Complete documentation suite in `docs/`.
- **Gate 0 Criteria:** Technology candidate matrix approved; architecture review signed off; Phase 1 implementation plan approved.

---

### Phase 1: Foundation & Domain Core
- **Objective:** Establish the modular monolith structure, domain types, abstract interfaces, configuration management, structured logging, in-memory mock adapters, and correctness test harness.
- **Deliverables:**
  - Python project environment (`pyproject.toml`, virtual environment).
  - Core domain models (`Instrument`, `Bar`, `MarketDataSnapshot`, `Signal`, `TargetAllocation`, `RiskAssessment`, `Order`, `Fill`).
  - Core interface definitions (`IMarketDataProvider`, `IFeatureEngine`, `IStrategy`, `IPortfolioOptimizer`, `IRiskEngine`, `IBacktestEngine`, `IExecutionEngine`, `IDecisionLedger`).
  - Mock in-memory execution engine and market data provider for unit testing.
  - Structured JSON logger and typed configuration loader (`Pydantic` + `YAML`).
  - Unit and contract test suite verifying domain invariants, invalid states, interface contracts, serialization, and deterministic equivalent outcomes.
- **Gate 1 Criteria:** All unit tests pass; domain invariants verified; typing strictly enforced (`mypy` clean); zero live broker or Nautilus dependencies in core.

---

### Phase 2: Data Ingestion & Integrity Engine
- **Objective:** Implement reliable ingestion for **one market** and **one primary data source** with strict point-in-time validation.
- **Deliverables:**
  - Ingestion adapter (e.g. `yfinance` research adapter / local Parquet for single liquid symbol).
  - Normalization pipeline with timestamp timezone enforcement (UTC only) and sequencing verification.
  - Automated data integrity checker (detects missing timestamps, impossible negative prices, duplicates, unit errors).
  - Provenance tracker recording dataset hash and retrieval metadata.
- **Gate 2 Criteria:** Data validation suite catches 100% of synthetic data corruption test cases.

---

### Phase 3: Point-in-Time Feature Engine
- **Objective:** Build modular, deterministic feature calculations with zero look-ahead bias.
- **Deliverables:**
  - Price/Return features (log returns, rolling volatility, ATR, momentum oscillators).
  - Volume features (relative volume, rolling VWAP, volume anomalies).
  - Anti-leakage pipeline guaranteeing $Feature(t)$ uses only data $\le t$.
  - Feature evaluation harness measuring Information Coefficient (IC) and mutual information.
- **Gate 3 Criteria:** Automated leakage unit tests verify zero future bar indexing; each feature demonstrates positive incremental predictive metric or is discarded.

---

### Phase 4: Alpha Research Engine & Baseline Hypotheses
- **Objective:** Implement formal hypothesis registration and initial transparent strategy baselines.
- **Deliverables:**
  - Hypothesis specification schema (rationale, assumptions, parameters, invalidation conditions).
  - Baseline Strategy 1: Trend / Momentum (e.g. Time-Series Momentum).
  - Baseline Strategy 2: Mean Reversion (e.g. Statistical Bollinger / RSI Band Reversion).
  - Signal generator producing expected returns and uncertainty estimates.
- **Gate 4 Criteria:** Strategies generate reproducible signals on historical data without look-ahead errors.

---

### Phase 5: Backtesting Substrate & NautilusTrader PoC
- **Objective:** Evaluate and establish the deterministic simulation backtest engine.
- **Deliverables:**
  - Lightweight custom vectorized / event backtester for rapid research.
  - NautilusTrader Proof of Concept (PoC) adapter benchmark.
  - Realistic friction simulation (fees, bid/ask spread, basic slippage).
- **Gate 5 Criteria:** PoC comparison completed; backtest outputs produce deterministic equivalent outcomes for identical inputs and configuration.

---

### Phase 6: Statistical Validation & OOS Hard Gate
- **Objective:** Enforce quantitative validation gates to eliminate data-snooping bias.
- **Deliverables:**
  - Strict 3-way partition harness: In-Sample (Train) $\to$ Validation $\to$ Held-Out Out-of-Sample (OOS).
  - Combinatorial Purged Cross-Validation (CPCV) module via `skfolio.model_selection`.
  - Multi-testing tracking: Deflated Sharpe Ratio (DSR) and Haircut Sharpe Ratio calculations.
  - Automated parameter sensitivity and slippage stress-testing suite.
- **Gate 6 Criteria:** Strategies must pass Out-of-Sample validation and DSR thresholds to proceed.

---

### Phase 7: Regime Engine
- **Objective:** Detect market regimes (volatility, trend, liquidity) and verify their utility.
- **Deliverables:**
  - Volatility regime detector (Realized Volatility percentile / GARCH filter).
  - Trend regime classifier (ADX / moving average slope).
  - Controlled ablation study: Strategy performance with regime filter vs without.
- **Gate 7 Criteria:** Regime filter must prove statistically significant improvement in risk-adjusted return net of turnover; otherwise, dropped.

---

### Phase 8: Portfolio Engine (skfolio & Baselines)
- **Objective:** Allocate capital across candidate assets/signals and cash ("NOWHERE").
- **Deliverables:**
  - Transparent Baseline Allocators: Equal Weight (1/N), Inverse Volatility (1/$\sigma$), 100% Cash.
  - `skfolio` portfolio optimization and risk-allocation methods including HRP, ERC and CVaR-based approaches.
  - Hurdle rate gate: If return < cost + hurdle, allocate to Cash.
- **Gate 8 Criteria:** `skfolio` must be evaluated for statistically significant incremental value versus transparent baselines out-of-sample; fallback to baseline if optimizer fails.

---

### Phase 9: Deterministic Risk Engine & Kill Switch
- **Objective:** Implement non-negotiable risk boundaries that overrule all upstream models.
- **Deliverables:**
  - Position limits, maximum leverage limit, maximum portfolio drawdown limit, daily loss limit.
  - Deterministic Risk Evaluator: `evaluate_allocation(...) -> Approved / Reduced / Rejected`.
  - Global Kill Switch: Immediate order cancellation and position flattening.
- **Gate 9 Criteria:** 100% passing rate on risk violation tests (oversized orders, drawdown breaches, rapid loss triggers).

---

### Phase 10: Transaction Cost & Slippage Modeling
- **Objective:** Embed high-fidelity friction models into every strategy evaluation.
- **Deliverables:**
  - Non-linear slippage models based on market volatility and order size relative to volume.
  - Spread and commission tables for target assets.
  - Net P&L verification harness.
- **Gate 10 Criteria:** Backtests evaluate strictly on Net P&L after friction; zero gross-only reporting permitted.

---

### Phase 11: Paper Trading Subsystem
- **Objective:** Real-time simulated execution against live market feeds.
- **Deliverables:**
  - Live data ingestion stream $\to$ Signal $\to$ Portfolio $\to$ Risk $\to$ Paper Execution.
  - Paper trade ledger recording signal timestamp, order timestamp, simulated fill, and slippage.
  - Continuous runtime operational verification.
- **Gate 11 Criteria:** Paper trading operates continuously without unhandled exceptions or state desynchronization.

---

### Phase 12: MT5 & Venue Execution Adapters
- **Objective:** Build thin, secure broker connectivity adapters.
- **Deliverables:**
  - MetaTrader 5 (MT5) IPC Gateway / Execution Adapter.
  - Account state, position, and order reconciliation loop.
  - Strict boundary: Zero strategy logic inside MT5/MQL5.
- **Gate 12 Criteria:** Order roundtrip latency and reconciliation tested in demo/staging broker account.

---

### Phase 13: Live Small Capital Deployment
- **Objective:** Real-world execution validation with micro-capital.
- **Deliverables:**
  - Live execution harness with minimum position sizes (micro-lots).
  - Live telemetry dashboard and real-time risk monitor.
  - Reconciliation between expected vs broker execution prices.
- **Gate 13 Criteria:** **EXPLICIT HUMAN APPROVAL REQUIRED (Section 37)**; all safety gates, kill switches, and alerts verified operational.

---

### Phase 14: AI Quantitative Research Layer
- **Objective:** Augment quant research with AI-driven hypothesis generation and reporting.
- **Deliverables:**
  - LLM hypothesis formulation assistant (`acash.research.ai`).
  - Automated research report generator conforming to Section 33.
  - Exploratory feature discovery tools.
- **Gate 14 Criteria:** AI outputs are treated strictly as unvalidated proposals; must pass full backtesting and statistical validation gates.

---

### Phase 15: Strategy Lifecycle Management
- **Objective:** Enforce automated governance from idea generation to retirement.
- **Deliverables:**
  - Strategy lifecycle state machine (`IDEA` $\to \dots \to$ `PRODUCTION` $\to$ `REDUCE` $\to$ `RETIRE`).
  - Rolling metric monitors (Sharpe, Drawdown, Profit Factor vs historical expectations).
- **Gate 15 Criteria:** Automated downgrade triggered when strategy underperforms statistical confidence bands.

---

### Phase 16: Performance Degradation & Data Flywheel
- **Objective:** Build continuous learning and proprietary decision memory.
- **Deliverables:**
  - Immutable Decision Ledger storing market state, features, signals, allocations, risk verdicts, and outcomes.
  - Post-mortem analytics pipeline feeding research back into hypothesis generation.
- **Gate 16 Criteria:** Closed-loop feedback cycle functioning as an automated research memory.

---

## Engineering Workflow Addendum

For ACASH development, follow an agentic engineering workflow:

1. Inspect the existing repository, architecture, ADRs, tests, and git history before modifying code.
2. Do not implement large changes immediately. First explain the impact, assumptions, affected modules, and implementation plan.
3. Preserve ACASH architectural boundaries and source-of-truth documentation.
4. Prefer minimal, reversible changes over broad refactors.
5. After implementation, run tests, static typing, invariant checks, and review the final diff.
6. Perform a self-review: identify assumptions, possible regressions, violated invariants, and unintended scope changes.
7. Record important architectural lessons or recurring mistakes in the appropriate project documentation.
8. Never grant an AI agent authority to bypass ACASH risk controls, decision boundaries, or execution safeguards.
9. External tools such as Agentic Trading Lab may be used only as independent research/evaluation references and must not become ACASH core dependencies without an explicit architectural decision.

### Core Engineering Loop:
$$\text{INSPECT} \to \text{UNDERSTAND} \to \text{PLAN} \to \text{APPROVE} \to \text{IMPLEMENT} \to \text{TEST} \to \text{SELF-REVIEW} \to \text{DOCUMENT}$$

---

## Engineering Research Addendum

Use the referenced trading-platform examples only as independent research references, not as ACASH architecture.

### Potential Future Concepts Worth Preserving:
- Multi-source news / external evidence ingestion
- Evidence provenance and timestamps
- Forward / out-of-sample testing
- Research reproducibility
- Portfolio analytics

*Do NOT expand Phase 1 scope for these concepts.*

### Important Architectural Rules:
1. **Append-Only Immutable Lineage:** `DecisionRecord` is immutable and append-only. Do not mutate it later to attach Fill/PnL outcomes. Preserve lineage through immutable references/correlation IDs so the complete decision $\to$ execution $\to$ outcome chain can be reconstructed without modifying historical records.
2. **Evidence-Driven Rigor:** Do not treat AI confidence scores, huge backtest returns, or large data-source counts as evidence of trading edge without proper calibration, bias checks, and out-of-sample validation.
3. **Strict External System Isolation:** External systems such as MT4/MT5 or Agentic Trading Lab may only be future adapters/research references and must never become ACASH core dependencies without an explicit ADR.
4. **Phase 1 Boundary:** Keep Phase 1 strictly foundational.

---

## Research Lessons — Trading Systems

1. **Data Quality and Provenance:**
   $$\text{Source} \to \text{Ingestion} \to \text{Validation} \to \text{Normalization} \to \text{Evidence} \to \text{Decision}$$
2. **AI as Analytical Component, NOT Authority:**
   AI must remain an analytical component, NOT the final trading authority. Never treat AI confidence as proven probability/edge.
3. **Multi-Source Evidence Treatment:**
   News, macro, options, Greeks, IV, and external data should be treated as evidence/research inputs, not automatic signals.
4. **Explainability & Traceability:**
   Every decision should be explainable and traceable back to its evidence, data, calculations, and timestamp.
5. **Backtest Metrics $\neq$ Proven Edge:**
   Backtest metrics (win rate, PF, Sharpe, expectancy, etc.) do NOT prove a real edge without proper OOS/forward testing, leakage checks, costs, slippage, and regime validation.
6. **Observability Hierarchy:**
   $$\text{System State} \to \text{Metrics} \to \text{Monitoring} \to \text{Audit/Investigation}$$
7. **Decoupled External Platforms:**
   External platforms/data providers may be used for independent research/evaluation, but must NOT become ACASH core dependencies without an explicit architectural decision.

> [!IMPORTANT]
> **Boundary Preservation:** Do not add new features or perform broad refactors based on these lessons. Preserve current ACASH boundaries and apply only minimal, reversible documentation/architecture updates where justified.

**Core Research Loop:**
$$\text{Evidence} \to \text{Analysis} \to \text{Decision} \to \text{Execution} \to \text{Outcome} \to \text{Audit/Learning}$$

---

## Final Research Lesson — Market Structure

- **Options Flow as Positioning:** Do NOT interpret Options Flow simply as bullish/bearish sentiment. Flow is an observation of transactions/positioning; the core question is: *"At this price/structure, who is forced to react, and what happens if price reaches that level?"*
- **Market Structure Precedes Strategy:** Market structure comes before strategy. Identify important levels/zones and how price behaves around them before choosing a strategy.
- **3-Dimensional Options Evaluation:** For options, evaluate at least 3 dimensions concurrently: $\text{Direction} \times \text{Volatility} \times \text{Time}$. Do not judge an option setup from direction alone.
- **Market State $\neq$ Trade Signal:** Distinguish "market state / setup" $\neq$ "trade signal". The system should explain what condition exists and what actions/risk responses become relevant, rather than blindly outputting BUY/SELL.
- **Real Arbitrage Exploitability:** Arbitrage is only meaningful when the pricing relationship is actually demonstrably exploitable after transaction costs, liquidity, execution risk, and timing friction.

**Market Structure Decision Loop:**
$$\text{OBSERVE} \to \text{IDENTIFY STRUCTURE} \to \text{QUANTIFY RISK/REWARD} \to \text{EVALUATE CONDITIONS} \to \text{DECIDE}$$

---

## Quantitative Reasoning & Deterministic Risk Pipeline

1. **Risk State Representation:** Continuous tracking of portfolio risk capacity, limit headroom, and drawdown state.
2. **Margin Buffer Safety Threshold:** Mandatory buffer between utilized margin and maintenance thresholds before approving any allocation.
3. **Net & Dollar Exposure Tracking:** Explicit dollar-denominated exposure accounting ($\text{Gross Exposure} = \sum |\text{Dollar Value}|$, $\text{Net Exposure} = \sum \text{Dollar Value}$).
4. **Deterministic Edge Metrics:** All performance metrics (Sharpe, DSR, Information Ratio, expectancy, max drawdown) are calculated strictly by deterministic mathematical algorithms.
5. **Separation of Raw Metrics from AI Reasoning:** Raw quantitative metrics remain pure and immutable. AI reasoning operates strictly downstream as an explanatory research tool, NEVER generating unverified numbers or placing trades.

### Core Processing Flow:
$$\text{DATA} \to \text{QUANT ENGINE} \to \text{RISK STATE} \to \text{AI REASONING}$$

$$\text{NOT: DATA} \to \text{AI} \to \text{Unverified Numbers} \to \text{TRADE}$$





