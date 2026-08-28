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
├── pyproject.toml          # Packaging & dependencies
├── docs/                   # Canonical documentation suite (including docs/ROADMAP.md)

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

## 6. Comprehensive Phase Summary & Technical Invariant Reference

### Phase 0 — Discovery & Architecture (COMPLETED & APPROVED)
- **Objective:** Evaluate technologies, define the 7-layer Modular Monolith architecture, and establish Architectural Decision Records (ADR-001 through ADR-018).
- **Core Architecture:**
  1. *Research Data Layer:* Partitioned Parquet files + DuckDB vectorized SQL query engine.
  2. *Transactional Control Plane:* SQLite append-only decision audit ledger + order state machine.
  3. *Analytics & Quant Research:* `pandas`, `NumPy`, `vectorbt` (Tier-1 screening), `Plotly`.
  4. *Portfolio Engine:* `skfolio` (HRP, ERC, CVaR) vs transparent baselines (Equal Weight, Inverse Vol, Cash).
  5. *Event Simulation:* `NautilusTrader` as Tier-2 event-driven candidate (Phase 5 PoC Gate).
  6. *Execution Subsystem:* Sovereign `IExecutionEngine` abstraction decoupling broker mechanics.
  7. *Performance Layer:* Python-first $\to$ NumPy/Numba vectorization $\to$ Rust/C++ only after measured profiling.
- **Key Invariants:**
  - $\text{DATA} \to \text{EVIDENCE} \to \text{HYPOTHESIS} \to \text{RESEARCH} \to \text{ALPHA} \to \text{VALIDATION} \to \text{PORTFOLIO} \to \text{RISK} \to \text{EXECUTION}$
  - Risk Engine is a non-negotiable hard boundary (Risk `REJECT` $\implies$ `REJECT` always).
  - No speculative AI trading bots; AI is analytical only.

---

### Phase 1 — Foundation & Domain Core (COMPLETED & VERIFIED — Gate 1)
- **Objective:** Sovereign domain models, pure immutable state transitions, abstract interfaces, configuration loader, telemetry, and in-memory mock adapters.
- **Key Deliverables (`src/acash/core/`):**
  - *Domain Entities (`frozen=True`):* `Instrument`, `Bar`, `MarketDataSnapshot`, `Position`, `PortfolioState`, `AccountState`, `Signal`, `TargetAllocation`, `RiskAssessment`, `Order`, `Fill`, `DecisionRecord`.
  - *Pure State Transitions (`transitions.py`):*
    - `apply_fill_to_position`: 8 signed-quantity scenarios (Long Increase, Long Reduce, Long Close, Long $\to$ Short Reversal, Short Increase, Short Reduce, Short Close, Short $\to$ Long Reversal).
    - `apply_fill_to_portfolio`: Cash flow accounting ($\text{BUY} \implies \text{cash} - \text{val} - \text{fee}$, $\text{SELL} \implies \text{cash} + \text{val} - \text{fee}$), zero Realized PnL double counting, total equity recomputation ($\text{total\_equity} = \text{cash\_balance} + \sum \text{Position.market\_value}$).
    - `update_portfolio_market_prices`: Revalues active positions and portfolio metrics.
  - *Append-Only Decision Ledger (`InMemoryDecisionLedger`):* Rejects updates/deletions (`LedgerTamperError`), correlation ID query lineage.
  - *Configuration & Telemetry:* Strict Pydantic models (`AppConfig`), structured JSON logging with recursive secret redaction (`api_key`, `secret`, `password`, `token`, `private_key`).
- **Gate 1 Metrics:** 27/27 unit tests passing, `mypy` 0 errors across 45 files.

---

### Phase 2 — Data Ingestion & Integrity Engine (COMPLETED & VERIFIED — Gate 2)
- **Objective:** Sovereign market data ingestion, data contract enforcement, recoverable batch commit protocol, bi-temporal indexing, and DuckDB Point-in-Time analytical engine.
- **Key Deliverables (`src/acash/data/`):**
  - *Canonical Arrow Schema (`schema.py`):*
    - `Decimal128(38, 18)` exact financial decimal representation (rejects non-finite/NaN/Inf).
    - `timestamp[us, tz=UTC]` microsecond UTC timestamps matching DuckDB `TIMESTAMPTZ`.
    - `revision_seq` ($\ge 1$) scoped to Event Observation Key.
  - *Data Integrity Validator (`integrity.py`):*
    - Per-stream validation: `(source_id, symbol, timeframe)`.
    - `event_end_utc` consistency across revisions sharing the same Event Observation Key.
    - Distinct event monotonicity: $t_{\text{event\_start}, j+1} \ge t_{\text{event\_end}, j}$.
    - Append-only safe revision sequencing: `revision_seq` assigned once upon initial acceptance; never renumbered on historical backfills.
    - Intra-batch deterministic tie-breaker: `canonical_content_fingerprint ASC` used strictly for unpersisted revisions accepted together with the same knowledge time.
    - Anomaly preservation: Statistical warnings (price return spikes, volume surges) are flagged as warnings without mutating raw data.
  - *Provenance & Manifest Engine (`provenance.py`):*
    - `raw_source_sha256`: SHA-256 over raw input payload bytes.
    - `canonical_batch_sha256`: Logical data hash invariant to row order, Parquet compression codecs (zstd vs snappy), or chunking.
    - Fail-fast canonical schema validation: missing columns raise `DataContractError`.
    - Commit-intent manifests: Lifecycle states `PREPARED` $\to$ `PART_PUBLISHED` $\to$ `COMMITTED` with `fsync` before atomic replace.
    - Append-only audit ledger: `data/provenance_ledger.jsonl` with idempotent writes.
  - *Storage & Recoverable Commit Protocol (`storage.py`):*
    - Strict 1:1 Ingestion Unit mapping: `data/parquet/{symbol}/{timeframe}/year={YYYY}/part-{batch_id}.parquet`.
    - Crash recovery pass: Reconstructs authentic provenance from manifests without guessing; quarantines orphan parts to `data/quarantine/`.
    - DuckDB Point-in-Time Qualification Query:
      `QUALIFY ROW_NUMBER() OVER (PARTITION BY source_id, symbol, timeframe, event_start_utc ORDER BY knowledge_time_utc DESC, revision_seq DESC) = 1`
      (preserves independent source observations without premature merging).
  - *Ingestion Pipeline (`pipeline.py`):*
    - Global revision duplicate check against existing canonical Parquet parts prior to acceptance.
    - Deterministic batch identity derivation:
      $$\text{batch\_id} = \text{batch\_}\{\text{source\_id}\}\_\{\text{symbol}\}\_\{\text{timeframe}\}\_\{\text{year}\}\_\{\text{raw\_source\_sha256}[:16]\}$$
    - Idempotent replay: Replaying the same payload returns the existing part path without duplicate files or duplicate ledger records.
- **Gate 2 Metrics:** 57/57 unit & integration tests passing, `mypy` 0 errors across 60 files.

---

## 7. Phase Correctness Checklist


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

---

## 12. Reality Gap Analysis & Execution Deviation

- **Core Goal:** Measure divergence between simulation assumptions and live market reality:
  $$\text{ACASH RESEARCH (Expected)} \longleftrightarrow \text{LIVE EXECUTION (Actual)} \implies \text{REALITY GAP}$$
- **Deviation Metrics:**
  - $\Delta_{\text{entry}} = \text{Fill Price} - \text{Model Target}$ (bps)
  - $\Delta_{\text{spread}} = \text{Actual Spread} - \text{Expected Spread}$ (bps)
  - $\Delta_{\text{slippage}} = \text{Actual Slippage} - \text{Assumed Slippage}$ (bps)
  - $\Delta_{\text{latency}} = \text{Round-Trip Latency} - \text{Assumed Delay}$ (ms)
  - $\Delta_{\text{pnl}} = \frac{\text{Actual PnL} - \text{Expected PnL}}{\text{Expected PnL}}$ (%)
- **Takeaway:** Strategy underperformance may be execution friction, not alpha failure. Reality Gap monitoring isolates the truth.

---

### Phase 5 — Backtesting Substrate & Simulation Engine (COMPLETED & HARDENED — Gate 5)
- **Objective:** Establish sovereign event-driven backtesting substrate, dual double-entry shadow ledger, unmocked NautilusTrader substrate, and Reality Gap telemetry.
- **Key Deliverables (`src/acash/backtest/`):**
  - *Sovereign Event Engine (`engine.py`):*
    - Full simulated order state machine (`CREATED` $\to$ `SUBMITTED` $\to$ `ACCEPTED` $\to$ `PARTIALLY_FILLED` $\to$ `FILLED` $\to$ `CANCELLED` $\to$ `REJECTED`).
    - Maker queue modeling with depth volume consumption and zero phantom fill invariant (`trade_size <= 0` strictly produces zero fill).
    - Causal dual-sided latency (submission + ACK roundtrip before active matching).
  - *Double-Entry Shadow Accounting Ledger (`accounting.py`):*
    - Decouples Balance-Sheet View ($\text{Cash} + \text{Unrealized PnL} = \text{Total Equity}$) from Performance Attribution View ($\text{Realized PnL} + \text{Unrealized PnL} - \text{Fees}$).
    - Mark-to-market contract revaluation using dynamic instrument specifications and multipliers (`ES: 50.0`, `NQ: 20.0`, `YM: 5.0`, `RTY: 50.0`, `GC: 100.0`, `CL: 1000.0`).
    - Internal conservation verification ($|\text{AccountingResidual}| \le 10^{-10}$).
  - *Canonical Data Adapter (`adapter.py`):*
    - Total ordering 5-tuple: $(T_{\text{event\_utc}}, \text{source\_order\_key}, \text{message\_rank}, \text{stream\_id}, \text{row\_sub\_index})$.
    - Strict price and size positivity validation (`price > 0`, `size > 0`).
    - Multi-match sub-index discrimination: `ch{channel}_seq{source_seq}_sub{match_sub_idx}`.
  - *Unmocked NautilusTrader Integration (`nautilus_bridge.py`):*
    - Nautilus ParquetDataCatalog export with deterministic nullable trade ID mapping policy.
    - True runtime simulation with `BacktestEngine`, `FuturesContract`, custom strategies, and `engine.trader` report ingestion.
    - Peak-to-trough max drawdown, closed trade win rate, and total submitted order telemetry.
  - *Reality Gap Telemetry Engine (`telemetry.py`):*
    - Decomposes execution divergence against Phase 4 analytical edge:
      $$\text{Reality Gap} = \text{Analytical Edge (bps)} - \text{Simulated Realized Return (bps)} = \text{Spread Drag} + \text{Latency Slip Drag} + \text{Queue Drag}$$
  - *Deterministic Backtest Manifest (`schema.py`):*
    - Cryptographic 32-hex manifest ID:
      $$\text{manifest\_id} = \text{SHA256}(\text{canonical}(\text{hypothesis\_hash} + \text{canonical\_data\_hashes} + \text{engine\_config\_hash} + \text{strategy\_config\_hash} + \text{seed}))[:32]$$
- **Gate 5 Metrics:** 200/200 unit & integration tests passing (including real Nautilus runtime tests), `mypy` 0 errors across 130 files.

---

## 13. Completed Architecture & Subsystem Reference (Phases 0–5)

```
Phase 0: Discovery & Architecture ──► 17 tech evaluated, 7 decoupled layers, ADR-001 to ADR-019
Phase 1: Foundation & Domain Core ──► Immutable domain models, signed position fills, append ledger (27/27 tests)
Phase 2: Data Ingestion & Integrity ──► Canonical PyArrow schema, Recoverable 2-Phase Commit, DuckDB PIT (57/57 tests)
Phase 3: Market Microstructure & Features ──► Trades, L2/L3 Order Book, pure VWAP/Profile/Footprint (122/122 tests)
Phase 4: Alpha Research & Hypotheses ──► Pre-registered hypotheses, OLS Beta HAC, Blind OOS Ledger (139/139 tests)
Phase 5: Backtesting Substrate & Simulation ──► Sovereign event runner, double-entry ledger, Nautilus substrate (200/200 tests)
```

### Phase 1: Foundation & Invariant Rules
- **Signed Quantity Arithmetic:** `qty > 0` = Long, `qty < 0` = Short.
- **Pure State Transitions:** 8 scenario position updates producing new immutable snapshots; zero Realized PnL double counting.
- **Double-Entry Balance Rule:** Realized Cash + Unrealized PnL = Equity.

### Phase 2: Data Ingestion & Storage Rules
- **Canonical Arrow Types:** `price`/`size` = `Decimal128(38, 18)`, `timestamp` = `timestamp[us, tz=UTC]`.
- **Bi-temporal Indexing:** $t_{\text{event}}$ (exchange event time) vs $t_{\text{knowledge}}$ (system ingestion time).
- **Recoverable Batch Commit Protocol:** `PREPARED` $\to$ `PART_PUBLISHED` $\to$ `COMMITTED`. Uncommitted parts quarantined.
- **Cross-Batch Deduplication:** `(source_id, symbol, tf, event_start, knowledge_time) -> fingerprint` rejecting duplicate/conflicting revisions across batches.
- **Idempotency & Replay:** Parquet paths: `data/parquet/{symbol}/{timeframe}/year={YYYY}/part-{batch_id}.parquet`. Logical hashing invariant to row ordering and compression codec.

### Phase 3: Market Microstructure & Derived Features
- **Phase 3A Trades:** Nanosecond execution replay, aggressor side (`BUY`/`SELL`), multi-match `match_sub_idx` sequencing, length-prefixed hashing.
- **Phase 3B Order Book:** Multi-row frame snapshots and deltas; deterministic 5-tuple order:
  $$\text{ReconstructionOrder} = (\text{exchange\_time\_utc}, \text{source\_order\_key}, \text{message\_type\_rank}, \text{stream\_id}, \text{row\_sub\_index})$$
  Explicit `CLEAR` level semantics (distinguishing NULL clear from zero-volume deletion).
- **Phase 3C Feature Engine:** Pure derived features (Session VWAP, Volume-Weighted Dispersion $\sigma$, Volume Profile with lower-price-first tie-breaking, Value Area 70% bounds, Footprint Analytics, Depth-Weighted Micro-Price).
- **Dual-Temporal PIT Filter:** $T_{\text{event}} \le T_{\text{decision}} \land T_{\text{knowledge}} \le T_{\text{as\_of}}$.

### Phase 4: Alpha Research & Econometric Inference
- **Inference Estimator:** $R(t, H) = \alpha_H + \beta_H X_t + \epsilon_t$ with HAC covariance on $\hat{\beta}_H$ using Bartlett kernel.
- **Discrete Bar-Indexed Returns:** $R(t, H) = \frac{P_{\text{close}, t+H} - P_{\text{open}, t+1}}{P_{\text{open}, t+1}}$ with exact $\text{label\_interval} = [T_{\text{open}, t+1}, T_{\text{close}, t+H}]$.
- **Boundary Purging & Embargo:** Training samples with label intervals crossing $T_{\text{train\_end}}$ are purged; embargo gap $\ge \max(H)$ bars enforced between splits.
- **3-Tier Friction Waterfall:**
  - Tier 1: $\mathbb{E}[R \cdot \text{Signal}] \times 10{,}000$ (bps)
  - Tier 2: Tier 1 - $(\text{Quoted Spread} + \text{Roundtrip Fees})$
  - Tier 3: Tier 2 - $\text{Fixed Slippage Proxy}$
- **Durable Blind OOS State Machine:** `UNEXPOSED` $\to$ `EVALUATED_LOCKED` $\to$ `EXHAUSTED` persisted in `data/manifests/research/governance_ledger.json`.
- **Search Accounting:** `ResearchSearchRecord` tracks total effective trials, preventing untracked multiple testing.

### Phase 5: Backtesting Substrate & Simulation Engine
- **Event-Driven Runner:** Order matching engine with maker queue consumption, trade-through validation, and zero phantom liquidity (`trade_size <= 0 -> fill = 0`).
- **Shadow Accounting Ledger:** Double-entry conservation ($|\text{Residual}| \le 10^{-10}$), multiplier-adjusted MTM, zero Realized PnL double counting.
- **NautilusTrader Substrate:** Unmocked execution bridge with ParquetDataCatalog export, contract specification mapping, and execution reports parsing.
- **Reality Gap Attribution:** Quantitative decomposition of execution drag into spread, latency, and queue drag against Phase 4 predictive edges.


---

## 14. License Notice

**Copyright © 2026 Ratthabhumi & ACASH Contributors. All Rights Reserved.**  
Proprietary and Confidential. Unauthorized copying, distribution, modification, or extraction is strictly prohibited.

