# ACASH — System Development Roadmap (Phases 0–16)

**Project:** ACASH (Automated Capital Allocation System)  
**Governance Principle:** Sequential Phase Progression. No skipping phases. Every phase requires rigorous acceptance criteria and human approval checkpoints.

---

## High-Level Progression Diagram

```
Phase 0: Discovery & Architecture [COMPLETED — APPROVED]
   │
   ▼
Phase 1: Foundation & Domain Core ──► Gate 1 [COMPLETED & VERIFIED — 27/27 Tests]
   │
   ▼
Phase 2: Data Ingestion & Integrity Engine ──► Gate 2 [COMPLETED & VERIFIED — 57/57 Tests]
   │
   ▼
Phase 3: Market Microstructure & PIT Feature Engine ──► Gate 3 [DESIGN STAGE]
   ├─ Phase 3A: Canonical Trades Domain (Time & Sales, Aggressor Side)
   ├─ Phase 3B: Canonical Order Book Domain (L2 Depth Snapshots & Deltas, L3 MBO)
   └─ Phase 3C: Microstructure Research Engine (VWAP, Volume Profile, Footprint, Delta)
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

### Phase 1: Foundation & Domain Core (COMPLETED & VERIFIED — Gate 1 Passed)
- Sovereign domain entities (`Instrument`, `Bar`, `Position`, `PortfolioState`, `AccountState`, `Signal`, `TargetAllocation`, `RiskAssessment`, `Order`, `Fill`, `DecisionRecord`).
- Pure immutable state transitions: 8 signed-quantity position fill scenarios, spot cash flows, zero Realized PnL double-counting.
- Core abstract interface contracts (`IMarketDataProvider`, `IFeatureEngine`, `IStrategy`, `IPortfolioOptimizer`, `IRiskEngine`, `IBacktestEngine`, `IExecutionEngine`, `IDecisionLedger`).
- In-memory mock adapters, append-only decision ledger, structured logging with secret redaction.
- Verified: 27/27 unit tests passing, `mypy` 0 errors.

### Phase 2: Data Ingestion & Integrity Engine (COMPLETED & VERIFIED — Gate 2 Passed)
- Sovereign market data ingestion with Canonical PyArrow schema (`Decimal128(38, 18)`, `timestamp[us, tz=UTC]`).
- Data integrity engine: Per-stream validation, `event_end_utc` consistency, distinct event monotonicity, and anomaly preservation without data mutation.
- Bi-temporal indexing ($t_{\text{event}}$ vs $t_{\text{knowledge}}$), append-only `revision_seq` sequencing, and intra-batch fingerprint tie-breaking.
- Recoverable Batch Commit Protocol: Commit-intent manifests (`PREPARED` $\to$ `PART_PUBLISHED` $\to$ `COMMITTED`), crash recovery pass, and orphan part quarantine.
- DuckDB Point-in-Time qualification query layer with source isolation.
- Global revision duplicate check and idempotent pipeline ingestion replay.
- Verified: 57/57 unit and integration tests passing, `mypy` 0 errors.

### Phase 3: Market Microstructure & PIT Feature Engine (DESIGN STAGE)
- **Phase 3A — Canonical Trades Domain:** Time & Sales, tick executions, and aggressor side flags.
- **Phase 3B — Canonical Order Book Domain:** L2 MBP depth snapshots/deltas and L3 MBO queue reconstruction.
- **Phase 3C — Microstructure Research Engine:** Pure derived feature transformations (Anchored/Rolling VWAP, Volume & TPO Profile, Footprint/Delta cluster, Imbalance & Absorption detection, and strict Anti-Leakage guard).


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

### ENGINEERING WORKFLOW ADDENDUM

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

**Core loop:**
$$\text{INSPECT} \to \text{UNDERSTAND} \to \text{PLAN} \to \text{APPROVE} \to \text{IMPLEMENT} \to \text{TEST} \to \text{SELF-REVIEW} \to \text{DOCUMENT}$$

---

### ENGINEERING RESEARCH ADDENDUM

Use the referenced trading-platform examples only as independent research references, not as ACASH architecture.

Potential future concepts worth preserving:
- Multi-source news / external evidence ingestion
- Evidence provenance and timestamps
- Forward / out-of-sample testing
- Research reproducibility
- Portfolio analytics

Do NOT expand Phase 1 scope for these concepts.

**Important architectural rule:**
`DecisionRecord` is immutable and append-only. Do not mutate it later to attach Fill/PnL outcomes. Preserve lineage through immutable references/correlation IDs so the complete decision $\to$ execution $\to$ outcome chain can be reconstructed without modifying historical records.

Do not treat AI confidence scores, huge backtest returns, or large data-source counts as evidence of trading edge without proper calibration, bias checks, and out-of-sample validation.

External systems such as MT4/MT5 or Agentic Trading Lab may only be future adapters/research references and must never become ACASH core dependencies without an explicit ADR.

Keep Phase 1 strictly foundational.

---

### RESEARCH LESSONS — TRADING SYSTEMS

1. **Data Quality & Provenance:** $\text{Source} \to \text{Ingestion} \to \text{Validation} \to \text{Normalization} \to \text{Evidence} \to \text{Decision}$
2. **AI is Analytical, NOT Final Authority:** Never treat AI confidence as proven probability/edge.
3. **Multi-Source Evidence:** Treat news, macro, Greeks, and IV as evidence inputs, not automatic signals.
4. **Explainability & Traceability:** Every decision must be traceable to data, calculations, and timestamps.
5. **Backtest Metrics $\neq$ Edge:** Require proper OOS validation, leak checks, slippage, and regime tests.
6. **Observability:** $\text{System State} \to \text{Metrics} \to \text{Monitoring} \to \text{Audit/Investigation}$
7. **External Decoupling:** External platforms/data providers are research references only, not core dependencies.

**Core Research Loop:**
$$\text{Evidence} \to \text{Analysis} \to \text{Decision} \to \text{Execution} \to \text{Outcome} \to \text{Audit/Learning}$$

---

### FINAL RESEARCH LESSON — MARKET STRUCTURE

- **Options Flow as Positioning:** Do NOT interpret Options Flow simply as bullish/bearish sentiment. Flow is positioning; ask: *"At this price/structure, who is forced to react, and what happens if price reaches that level?"*
- **Market Structure Precedes Strategy:** Identify important levels/zones and behavior before choosing a strategy.
- **3D Options:** Evaluate $\text{Direction} \times \text{Volatility} \times \text{Time}$ together.
- **State $\neq$ Signal:** "Market state/setup" $\neq$ "trade signal". Explain condition and risk response, not blind BUY/SELL.
- **Real Arbitrage:** Exploitable only after all costs, liquidity, execution, and timing risks.

**Market Structure Decision Loop:**
$$\text{OBSERVE} \to \text{IDENTIFY STRUCTURE} \to \text{QUANTIFY RISK/REWARD} \to \text{EVALUATE CONDITIONS} \to \text{DECIDE}$$

---

### QUANTITATIVE REASONING & RISK PIPELINE

1. **Risk State:** Continuous mathematical tracking of risk capacity and drawdown limits.
2. **Margin Buffer:** Safety buffer between used margin and limits before approving orders.
3. **Net & Dollar Exposure:** Explicit dollar-denominated exposure calculations.
4. **Deterministic Edge Metrics:** Pure mathematical indicators, never probabilistic guesses.
5. **Separate Raw Metrics from AI:** AI reasons on top of validated quant outputs; never trades directly.

$$\text{DATA} \to \text{QUANT ENGINE} \to \text{RISK STATE} \to \text{AI REASONING}$$
*$$\text{NOT: DATA} \to \text{AI} \to \text{Unverified Numbers} \to \text{TRADE}$$*

---

### REALITY GAP ANALYSIS & EXECUTION DEVIATION

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

**Multi-Phase Reality Pipeline:**
- **Phase 2+ (Data Quality):** Data fidelity matching strategy horizon, timestamp integrity, provenance, spread capture.
- **Phase 5+ (Backtest):** Tick-aware simulation, data-supported spread fidelity, graduated slippage models (simple $\to$ calibrated $\to$ liquidity-aware).
- **Phase 6+ (Validation):** OOS, walk-forward matrix, forward testing, stress testing, regime analysis.
- **Phase 12+ (Live):** Actual fills, realized spreads, actual slippage, latency, broker reconciliation.
- **Phase 13+ (Reality Gap Attribution):** Systematic deviation tracking attributed to: Data error, Model/alpha error, Execution error, or Venue conditions.

**Core Methodological Principles:**
1. **Spread Modeling:** Model spread at highest fidelity supported by data; explicit limitations on lower-resolution assumptions.
2. **Slippage Modeling:** Graduated complexity based on empirical evidence ($\text{simple} \to \text{calibrated} \to \text{liquidity-aware}$).
3. **Capital Flows:** External capital flows (deposits/withdrawals) are first-class events, strictly isolated from Trading PnL.
4. **Martingale:** Classify Martingale-like exposure escalation as a **HARD RISK FLAG** requiring explicit tail and ruin analysis.
5. **Data Fidelity:** Match fidelity to strategy horizon and execution sensitivity; use tick/quote data when lower resolution is inadequate.

| Metric | Expected (Simulation) | Actual (Live) | Reality Gap Deviation |
| :--- | :--- | :--- | :--- |
| **Entry Price** | 100.00 | 100.07 | **+7 bps** |
| **Prevailing Spread** | 2 bps | 9 bps | **+7 bps** |
| **Execution Slippage** | 1 bp | 6 bps | **+5 bps** |
| **Trade PnL** | +$240 | +$181 | **-24.6%** |
| **Roundtrip Latency** | 15 ms | 120 ms | **+105 ms** |

---

For in-depth specifications, see **[docs/ROADMAP.md](file:///c:/Users/MewMew/Desktop/Co-op/Acash/docs/ROADMAP.md)**.

