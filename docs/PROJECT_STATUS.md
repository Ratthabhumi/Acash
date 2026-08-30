# ACASH — Project Status & Implementation Progress

**Document:** `docs/PROJECT_STATUS.md`  
**Project Name:** ACASH (Automated Capital Allocation System)  
**Status:** Phases 0–5 Complete & Frozen (v0.5.0-baseline-frozen); Phase 6 Methodological Remediation v1.1 Complete (Awaiting User Forensic Audit)  
**Date:** 2026-08-28  
**Operating Environment:** Windows 10/11 (AIO workstation)  
**Runtime:** Python 3.14.3 64-bit, Git 2.55.0  

---

## 1. Executive Summary

ACASH is a scientific, research-first, evidence-driven capital allocation and portfolio management platform. ACASH is **not** an indicator collection, **not** an MT5 EA bot, and **not** an unconstrained LLM trading agent. Its primary purpose is answering:

> *"Given the current market, available opportunities, portfolio state, uncertainty, liquidity, and risk constraints, where should capital be allocated?"* (including the valid decision: **NOWHERE**).

Phase 0 discovery and architecture evaluation is complete. All architectural foundations, open-source technology evaluations, storage tiers, decoupled execution boundaries, and correctness-driven testing criteria have been defined canonically in [`docs/`](./README.md).

---

## 2. Workspace & Environment Inspection

| Aspect | Inspected State | Notes / Implication |
| :--- | :--- | :--- |
| **Codebase State** | Greenfield (0 bytes production code) | Clean slate; zero legacy technical debt or coupling. |
| **Primary Machine** | Single Workstation (AIO) | Adheres to Section 29 (simple infrastructure first). |
| **Secondary Hardware** | Acer Ubuntu Server, ATX Proxmox | Available for future 24/7 services and staging/testing. |
| **Python Runtime** | Python 3.14.6 64-bit | Core packages built Python-first; `.venv` environment isolation. |
| **Package Manager** | `pip` 26.1.2 available | Virtual environment creation (`venv`) and deterministic dependency management. |
| **Version Control** | Git installed (`git 2.55.0`) | Repository initialization upon Phase 1 kickoff. |

---

## 3. Storage Architecture Summary

- **Analytical / Research Data:** Partitioned Parquet files + embedded DuckDB analytical query engine. (DuckDB is strictly analytical, not a transactional DB).
- **Transactional Operational State:** SQLite local database for V1 (order states, positions, audit ledger).
- **Control Plane Persistence:** PostgreSQL is **DEFERRED** until concurrent multi-process writers, production durability, or operational requirements justify it.

---

## 4. Phase 0 Deliverables Complete in `docs/`

1. [x] [docs/TECHNOLOGY_EVALUATION.md](./TECHNOLOGY_EVALUATION.md)
2. [x] [docs/ARCHITECTURE.md](./ARCHITECTURE.md)
3. [x] [docs/DATA_ARCHITECTURE.md](./DATA_ARCHITECTURE.md)
4. [x] [docs/EXECUTION_ARCHITECTURE.md](./EXECUTION_ARCHITECTURE.md)
5. [x] [docs/PORTFOLIO_ARCHITECTURE.md](./PORTFOLIO_ARCHITECTURE.md)
6. [x] [docs/RESEARCH_ARCHITECTURE.md](./RESEARCH_ARCHITECTURE.md)
7. [x] [docs/DECISIONS.md](./DECISIONS.md) (ADR-001 through ADR-015)
8. [x] [docs/RISKS.md](./RISKS.md)
9. [x] [docs/ROADMAP.md](./ROADMAP.md)
10. [x] [docs/PHASE_1_PLAN.md](./PHASE_1_PLAN.md)


---

## 5. Engineering Workflow Addendum

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

## 6. Engineering Research Addendum

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

## 7. Research Lessons — Trading Systems

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

## 8. Final Research Lesson — Market Structure

- **Options Flow as Positioning:** Do NOT interpret Options Flow simply as bullish/bearish sentiment. Flow is an observation of transactions/positioning; the core question is: *"At this price/structure, who is forced to react, and what happens if price reaches that level?"*
- **Market Structure Precedes Strategy:** Market structure comes before strategy. Identify important levels/zones and how price behaves around them before choosing a strategy.
- **3-Dimensional Options Evaluation:** For options, evaluate at least 3 dimensions concurrently: $\text{Direction} \times \text{Volatility} \times \text{Time}$. Do not judge an option setup from direction alone.
- **Market State $\neq$ Trade Signal:** Distinguish "market state / setup" $\neq$ "trade signal". The system should explain what condition exists and what actions/risk responses become relevant, rather than blindly outputting BUY/SELL.
- **Real Arbitrage Exploitability:** Arbitrage is only meaningful when the pricing relationship is actually demonstrably exploitable after transaction costs, liquidity, execution risk, and timing friction.

**Market Structure Decision Loop:**
$$\text{OBSERVE} \to \text{IDENTIFY STRUCTURE} \to \text{QUANTIFY RISK/REWARD} \to \text{EVALUATE CONDITIONS} \to \text{DECIDE}$$

---

## 9. Quantitative Reasoning & Deterministic Risk Pipeline

1. **Risk State Representation:** Continuous tracking of portfolio risk capacity, limit headroom, and drawdown state.
2. **Margin Buffer Safety Threshold:** Mandatory buffer between utilized margin and maintenance thresholds before approving any allocation.
3. **Net & Dollar Exposure Tracking:** Explicit dollar-denominated exposure accounting ($\text{Gross Exposure} = \sum |\text{Dollar Value}|$, $\text{Net Exposure} = \sum \text{Dollar Value}$).
4. **Deterministic Edge Metrics:** All performance metrics (Sharpe, DSR, Information Ratio, expectancy, max drawdown) are calculated strictly by deterministic mathematical algorithms.
5. **Separation of Raw Metrics from AI Reasoning:** Raw quantitative metrics remain pure and immutable. AI reasoning operates strictly downstream as an explanatory research tool, NEVER generating unverified numbers or placing trades.

### Core Processing Flow:
$$\text{DATA} \to \text{QUANT ENGINE} \to \text{RISK STATE} \to \text{AI REASONING}$$

$$\text{NOT: DATA} \to \text{AI} \to \text{Unverified Numbers} \to \text{TRADE}$$

---

## 10. Phase 1 Implementation & Gate 1 Summary

- **Implementation Date:** 2026-08-27
- **Test Suite Results:** 27 passed in 0.21s (100% pass rate via `pytest`)
- **Static Type Check:** Success (0 type errors in 45 source files via `mypy`)
- **Delivered Packages & Modules:**
  - `src/acash/core/domain/`: Domain entities (`Instrument`, `Bar`, `MarketDataSnapshot`, `Position`, `PortfolioState`, `AccountState`, `Signal`, `TargetAllocation`, `RiskAssessment`, `Order`, `Fill`, `DecisionRecord`) and pure state transitions (`transitions.py`).
  - `src/acash/core/interfaces/`: 8 ABC interface contracts (`IMarketDataProvider`, `IFeatureEngine`, `IStrategy`, `IPortfolioOptimizer`, `IRiskEngine`, `IBacktestEngine`, `IExecutionEngine`, `IDecisionLedger`).
  - `src/acash/core/config/`: Schema and hierarchical YAML loader (`base.yaml`, `research.yaml`, `development.yaml`).
  - `src/acash/telemetry/`: Structured JSON logging with credential redaction (`api_key`, `secret`, `password`, `token`, `private_key`).
  - In-Memory Mock Adapters: `MockExecutionEngine`, `MockMarketDataProvider` (zero network), `InMemoryDecisionLedger`.
  - `pyproject.toml` + `uv.lock`: Sole dependency source of truth.
- **Gate 1 Status:** **PASSED & VERIFIED**. Awaiting explicit user approval before proceeding to Phase 2.
