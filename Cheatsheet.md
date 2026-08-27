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
