# ACASH — System Development Roadmap (Phases 0–16)

**Project:** ACASH (Automated Capital Allocation System)  
**Governance Principle:** Sequential Phase Progression. No skipping phases. Every phase requires rigorous acceptance criteria and human approval checkpoints.

---

## High-Level Progression Diagram

```
Phase 0: Discovery & Architecture [COMPLETE — APPROVED]
   │
   ▼
Phase 1: Foundation & Domain Core ──► Gate 1 (Packaging, Invariants, Interfaces, Mocks)
   │
   ▼
Phase 2: Data Ingestion & Integrity Engine ──► Gate 2 (Single Market, Provenance, Bi-temporal)
   │
   ▼
Phase 3: Point-in-Time Feature Engine ──► Gate 3 (Zero Look-Ahead Leakage, IC > 0)
   │
   ▼
Phase 4: Alpha Research Engine & Hypotheses ──► Gate 4 (Momentum & Mean-Reversion Baselines)
   │
   ▼
Phase 5: Backtesting Substrate & Nautilus PoC ──► Gate 5 (Deterministic Event Sim Benchmark)
   │
   ▼
Phase 6: Statistical Validation & OOS Hard Gate ──► Gate 6 (Combinatorial Purged CV & DSR)
   │
   ▼
Phase 7: Regime Engine ──► Gate 7 (Trend & Volatility Regimes: Prove or Remove)
   │
   ▼
Phase 8: Portfolio Engine ──► Gate 8 (skfolio vs Equal Weight / Inv Vol / Cash)
   │
   ▼
Phase 9: Deterministic Risk Engine & Kill Switch ──► Gate 9 (Hard Drawdown & Leverage Limits)
   │
   ▼
Phase 10: Transaction Cost & Slippage Modeling ──► Gate 10 (Net P&L Friction Realism)
   │
   ▼
Phase 11: Paper Trading Subsystem ──► Gate 11 (Real-Time Live Feed Simulation)
   │
   ▼
Phase 12: MT5 & Venue Execution Adapters ──► Gate 12 (Broker Gateway & Reconciliation)
   │
   ▼
Phase 13: Live Small Capital ──► Gate 13 (EXPLICIT HUMAN APPROVAL REQUIRED)
   │
   ▼
Phase 14: AI Quantitative Research Layer ──► Gate 14 (Hypothesis Assistant & Reporting)
   │
   ▼
Phase 15: Strategy Lifecycle Management ──► Gate 15 (Degradation & Retirement State Machine)
   │
   ▼
Phase 16: Performance Degradation & Data Flywheel ──► Ongoing (Proprietary Decision Memory)
```

---

## Phase Breakdown & Key Deliverables

### Phase 0: Discovery & Architecture (COMPLETE)
- Comprehensive evaluation of 17 technologies across 10 engineering criteria.
- Canonical architectural documentation created in [`docs/`](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs).

### Phase 1: Foundation & Domain Core (CURRENT STARTING POINT)
- Sovereign domain entities (`Instrument`, `Bar`, `Position`, `PortfolioState`, `AccountState`, `Signal`, `TargetAllocation`, `RiskAssessment`, `Order`, `Fill`, `DecisionRecord`).
- Core abstract interface contracts (`IMarketDataProvider`, `IFeatureEngine`, `IStrategy`, `IPortfolioOptimizer`, `IRiskEngine`, `IBacktestEngine`, `IExecutionEngine`, `IDecisionLedger`).
- In-memory mock adapters and correctness-driven test suite.

### Phase 2: Data Ingestion & Integrity Engine
- Ingest single liquid asset market with strict UTC point-in-time timestamping.
- Bi-temporal indexing ($t_{\text{event}}$ vs $t_{\text{knowledge}}$) and SHA-256 batch provenance.

### Phase 3: Point-in-Time Feature Engine
- Modular feature extractors (log returns, ATR, rolling VWAP, volume anomalies).
- Automated unit tests asserting zero forward-looking leakage ($Feature(t) = Feature(t \mid Data_{\le t})$).

### Phase 4: Alpha Research Engine
- Formal hypothesis schemas (assumptions, parameter ranges, invalidation conditions).
- Initial transparent baseline strategies: Time-Series Momentum and Statistical Mean-Reversion.

### Phase 5: Backtesting Substrate & NautilusTrader PoC
- Benchmark lightweight custom vectorized backtester vs NautilusTrader Rust-native event core.
- Verify deterministic equivalent outcomes for identical inputs.

### Phase 6: Statistical Validation & OOS Hard Gate
- 3-way partition: Train $\to$ Validation $\to$ Held-Out Out-of-Sample (OOS).
- Combinatorial Purged Cross-Validation (`skfolio.model_selection.CombinatorialPurgedCV`).
- Deflated Sharpe Ratio (DSR) multi-testing correction.

### Phase 7: Regime Engine
- Realized volatility percentile and trend strength classification.
- *Rule:* If regime filtering fails to improve out-of-sample risk-adjusted return net of turnover, it is discarded.

### Phase 8: Portfolio Engine
- `skfolio` risk allocation methods (HRP, ERC, CVaR) vs simple baselines (Equal Weight, Inverse Volatility, Cash/NOWHERE).
- *Rule:* The system selects the simple baseline if sophisticated optimization fails to demonstrate statistically significant incremental value out-of-sample.

### Phase 9: Deterministic Risk Engine
- Hard code boundaries: Max drawdown limit, maximum leverage limit, daily loss limit, asset concentration caps.
- Global Kill Switch: Immediate order cancellation and position flattening.

### Phase 10: Transaction Cost Model
- Net P&L evaluation incorporating commissions, spreads, volatility-dependent slippage, and borrow fees.

### Phase 11: Paper Trading Subsystem
- Continuous real-time simulation against live market feeds with automated slippage and fill logging.

### Phase 12: MT5 & Broker Adapters
- MetaTrader 5 Windows IPC execution adapter with background position and order reconciliation loops.

### Phase 13: Live Small Capital Deployment
- **MANDATORY HUMAN APPROVAL GATE.** Micro-lot live execution to validate latency, spread, and broker behavior.

### Phase 14: AI Quantitative Research Layer
- LLM hypothesis formulation assistant and automated research reporting.
- Confined strictly to `acash.research.ai` with zero execution or risk authority.

### Phase 15: Strategy Lifecycle Management
- Automated state machine: $\text{IDEA} \to \text{RESEARCH} \to \text{VALIDATION} \to \text{PAPER} \to \text{SMALL LIVE} \to \text{PRODUCTION} \to \text{DEGRADATION} \to \text{REDUCE} \to \text{RETIRE}$.

### Phase 16: Performance Degradation & Data Flywheel
- Append-only Decision Ledger database feeding closed-loop research memory.

---

For in-depth specifications, see **[docs/ROADMAP.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/ROADMAP.md)**.
