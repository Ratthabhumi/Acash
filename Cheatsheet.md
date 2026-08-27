# ACASH — Developer & Quant Quick Reference Cheatsheet

**Project:** ACASH (Automated Capital Allocation System)  
**Version:** 1.0.0 (Phase 0 Standard)  

---

## 1. Core Principles & North Star

> **"DO NOT ASSUME AN EDGE. PROVE IT."**

$$\text{DATA} \to \text{EVIDENCE} \to \text{HYPOTHESIS} \to \text{RESEARCH} \to \text{ALPHA} \to \text{VALIDATION} \to \text{PORTFOLIO} \to \text{RISK} \to \text{EXECUTION} \to \text{OUTCOME} \to \text{FEEDBACK}$$

- **North Star:** "Given current market state, uncertainty, liquidity, and risk constraints, where should capital be allocated?" (Valid answer: **"NOWHERE"**).
- **Risk Gate Rule:** The Risk Engine is a non-negotiable hard boundary. If AI/Strategy says `BUY` and Risk says `REJECT` $\implies$ **`REJECT`**. Always.
- **Baseline Beating Rule:** `skfolio` allocations must demonstrate statistically significant out-of-sample outperformance net of turnover over Equal Weight ($1/N$) and Inverse Volatility ($1/\sigma$).

---

## 2. Mathematical Reference & Formulas

### Account & Exposure Invariants
- **Account Equity:**
  $$\text{Equity} = \text{Balance} + \text{Unrealized PnL}$$
  *(where Balance is realized cash before open position PnL).*
- **Normalized Gross Exposure:**
  $$\text{Gross Exposure} = \sum_{i} |\text{Normalized Position Value}_i|$$
  *(where Normalized Position Value is in ACASH base currency).*
- **Net P&L after Friction:**
  $$\text{Net P&L} = \text{Gross P&L} - (\text{Commissions} + \text{Spread} + \text{Slippage} + \text{Financing/Borrow Fees})$$

### Multiple Testing & Statistical Rigor
- **Deflated Sharpe Ratio (DSR):**
  $$DSR = \Phi \left( \frac{(\widehat{SR} - SR_0)\sqrt{T-1}}{\sqrt{1 - \widehat{\gamma}_3 \widehat{SR} + \frac{\widehat{\gamma}_4 - 1}{4}\widehat{SR}^2}} \right)$$
  *(where $SR_0$ is the expected maximum Sharpe under null hypothesis across $K$ parameter trials, $\gamma_3$ is skewness, $\gamma_4$ is kurtosis).*

---

## 3. Technology Stack & Decision Matrix

| Technology | Category | Decision | Role in ACASH |
| :--- | :--- | :--- | :--- |
| **ACASH Core** | Sovereign | **ADOPT** | Domain logic, deterministic risk boundary, append-only decision ledger. |
| **skfolio** | Portfolio | **ADOPT** | Portfolio optimization & risk allocation (HRP, ERC, CVaR) + CPCV. |
| **NautilusTrader** | Simulation | **ADAPT** | Tier-2 event backtesting candidate (Phase 5 PoC Gate). |
| **vectorbt (OSS)** | Research | **ADAPT** | Tier-1 Numba-accelerated fast parameter sweeps and factor screening. |
| **yfinance** | Data | **ADAPT** | Research-oriented data adapter (no paid subscription required for research). |
| **Plotly** | Visualization | **ADOPT** | Interactive charts, equity curves, drawdown waterfalls, and research tear sheets. |
| **Parquet + DuckDB**| Storage | **ADOPT** | Local columnar storage + analytical embedded query engine. |
| **SQLite** | Storage | **ADOPT** | Local V1 transactional operational state and append-only decision ledger. |
| **PostgreSQL** | Storage | **DEFERRED** | Enterprise control plane (reconsidered when multi-user/concurrent needs arise). |
| **MetaTrader 5** | Execution | **ADAPT** | Thin Windows IPC broker gateway; zero strategy logic in MQL5. |
| **PyPortfolioOpt** | Portfolio | **REJECT** | Redundant to `skfolio`; lacks scikit-learn pipeline design and CPCV. |
| **QuantConnect LEAN**| Engine | **REFERENCE** | Architectural reference for data slicing and fill models (.NET runtime rejected). |
| **C++** | Language | **REJECT V1** | Premature optimization; Python + NumPy/Numba/Nautilus Rust core is standard. |

---

## 4. Domain Flow & Lifecycle Hierarchy

```
        CAPITAL STATE FLOW                  DECISION & EXECUTION FLOW
        ──────────────────                  ─────────────────────────
           AccountState                                Signal
                ↓                                        ↓
         PortfolioState                           TargetAllocation
                ↓                                        ↓
            Position                               RiskAssessment
                                                         ↓
                                                OrderIntent / Order
                                                         ↓
                                                        Fill
                                                         ↓
                                         State Transition (NEW Snapshots)
                                         → NEW Position
                                         → NEW PortfolioState
                                         → NEW AccountState

                      CROSS-CUTTING AUDIT LINEAGE
                      ───────────────────────────
                             DecisionRecord
                (Append-Only: never overwritten or deleted)
```

---

## 5. Directory Structure Conventions

```
acash/
├── README.md               # Main repository orientation
├── Cheatsheet.md           # Developer & Quant quick reference
├── Roadmap.md              # High-level 16-phase roadmap
├── Acash_Talk-27-08-2026.md# Complete conversation log
├── pyproject.toml          # Poetry / Hatch packaging & dependencies
├── docs/                   # Canonical documentation suite (11 files)
├── configs/                # Environment configurations (configs/*.yaml)
│   ├── base.yaml
│   ├── research.yaml
│   └── paper.yaml
├── data/                   # Local storage (Git-ignored)
│   ├── raw/                # Immutable raw data + SHA-256 manifests
│   ├── normalized/         # Partitioned Parquet files
│   └── ledger/             # SQLite append-only audit database
├── acash/                  # Sovereign Modular Monolith package
│   ├── core/               # Domain models, abstract interfaces, config
│   ├── data/               # Ingestion, normalization, provenance
│   ├── features/           # Point-in-time feature extractors
│   ├── research/           # Hypotheses, strategies, validation
│   ├── portfolio/          # skfolio & baseline allocators
│   ├── risk/               # Hard deterministic risk boundaries (Phase 9)
│   ├── execution/          # Pluggable broker adapters (Mock in Phase 1)
│   └── telemetry/          # Structured JSON logging & metrics
└── tests/
    └── unit/               # Fast, correctness-focused test suite
```

---

## 6. Phase 1 Correctness Checklist

- [ ] Domain models are immutable (`frozen=True`).
- [ ] Candlestick geometry invariants enforced ($\text{High} \ge \max(\text{Open}, \text{Close})$, $\text{Low} \le \min(\text{Open}, \text{Close})$, $\text{Price} > 0$).
- [ ] Normalized Account math invariants verified ($\text{Equity} = \text{Balance} + \text{Unrealized PnL}$).
- [ ] State transitions create new distinct snapshot instances without mutation.
- [ ] Semantically invalid timestamps (e.g. `event_start > event_end`) raise exceptions.
- [ ] Abstract interfaces cannot be instantiated directly.
- [ ] Decision ledger is strictly append-only (rejects updates/deletes).
- [ ] Mock adapters produce deterministic equivalent outcomes.
- [ ] `configs/*.yaml` parses with strict Pydantic validation.
- [ ] `mypy` static type checking passes with zero errors.

---

## 7. Engineering Workflow Addendum

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

## 8. Engineering Research Addendum

- **Research References:** External trading platforms/examples are strictly research references, not ACASH core architecture.
- **Future Concepts:** Multi-source news/evidence ingestion, provenance timestamps, OOS testing, research reproducibility, and portfolio analytics are preserved for future phases. (Do NOT expand Phase 1 scope).
- **Append-Only Decision Record:** `DecisionRecord` is strictly immutable and append-only. Never mutate historical records to attach Fills/PnL outcomes; preserve lineage via immutable references / correlation IDs.
- **Evidence Over Noise:** No AI confidence score, giant backtest return, or data count is evidence without proper calibration, bias checks, and OOS validation.
- **Dependency Isolation:** External tools (MT4/MT5, Agentic Trading Lab) are decoupled adapters/references, requiring explicit ADRs before core inclusion.
- **Phase 1 Discipline:** Keep Phase 1 strictly foundational.

---

## 9. Research Lessons — Trading Systems

- **Data Lineage:** $\text{Source} \to \text{Ingestion} \to \text{Validation} \to \text{Normalization} \to \text{Evidence} \to \text{Decision}$
- **AI Safety:** AI is analytical only. Never treat AI confidence as probability/edge.
- **External Data as Evidence:** News, macro, options, Greeks, IV are research inputs, not auto-signals.
- **Traceability:** Every decision must trace back to raw data, calculations, and exact timestamps.
- **Backtest Skepticism:** Backtests do NOT prove an edge without OOS testing, leakage checks, friction, and regime stress.
- **Observability:** $\text{State} \to \text{Metrics} \to \text{Monitoring} \to \text{Audit}$
- **Core Loop:** $\text{Evidence} \to \text{Analysis} \to \text{Decision} \to \text{Execution} \to \text{Outcome} \to \text{Audit/Learning}$

---

## 10. Final Research Lesson — Market Structure

- **Options Flow as Positioning:** Flow is positioning, not simple sentiment. Question: *"Who is forced to react at this level?"*
- **Structure Precedes Strategy:** Map key levels/zones and behavior before choosing strategy.
- **3D Options:** Evaluate $\text{Direction} \times \text{Volatility} \times \text{Time}$ together.
- **State $\neq$ Signal:** Explain conditions & risk response; do not output blind BUY/SELL.
- **Real Arbitrage:** Valid only if exploitable net of costs, liquidity, execution, and timing.
- **Core Loop:** $\text{OBSERVE} \to \text{IDENTIFY STRUCTURE} \to \text{QUANTIFY RISK/REWARD} \to \text{EVALUATE CONDITIONS} \to \text{DECIDE}$

---

## 11. Quantitative Reasoning & Deterministic Risk Pipeline

1. **Risk State:** Formal monitoring of risk capacity, limit headroom, and drawdown state.
2. **Margin Buffer:** Strict margin buffer safety margin before allowing new orders.
3. **Net & Dollar Exposure:** Explicit dollar-denominated gross and net exposure metrics.
4. **Deterministic Edge:** Analytical metrics (Sharpe, DSR, Expectancy) are 100% mathematical.
5. **Separate Raw Metrics from AI:** AI reasons on top of verified quant metrics; never trades directly.

$$\text{DATA} \to \text{QUANT ENGINE} \to \text{RISK STATE} \to \text{AI REASONING}$$
*$$\text{NOT: DATA} \to \text{AI} \to \text{Unverified Numbers} \to \text{TRADE}$$*





