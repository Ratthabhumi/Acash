# ACASH — Architectural Decision Records (ADRs)

**Document:** `docs/DECISIONS.md`  
**Version:** 3.5.0 (Spot-Like Accounting & Semantic Lock Applied)  
**Date:** 2026-08-27  

---

## ADR-001: Complete Isolation Between ACASH and Project Atlas
- **Status:** Approved
- **Context:** Project Atlas focuses on global work intelligence. ACASH focuses on market data, quantitative research, capital allocation, risk control, and trade execution.
- **Decision:** ACASH and Project Atlas are completely independent systems. Zero shared code dependencies, zero runtime coupling.
- **Consequences:** Eliminates failure cascading and preserves quantitative research domain purity.

---

## ADR-002: Modular Monolith Architecture
- **Status:** Approved
- **Context:** Splitting early-stage quant systems into distributed microservices creates network latency, serialization overhead, and debugging complexity.
- **Decision:** Build ACASH as a high-cohesion, low-coupling **Modular Monolith** in Python executing locally on a single machine (AIO).
- **Consequences:** Maximizes execution velocity, simplifies testing, and eliminates distributed infrastructure overhead.

---

## ADR-003: Deterministic Hard Risk Engine Boundary
- **Status:** Approved
- **Context:** Algorithmic bugs and statistical regime changes can cause rapid capital depletion if risk controls are probabilistic or advisory.
- **Decision:** The Risk Engine is a strictly deterministic, non-negotiable software gate. If the Risk Engine rejects an allocation or triggers a kill switch, it overrules all Alpha models, Portfolio Optimizers, and AI proposals with 100% authority. Phase 1 defines the `IRiskEngine` interface contract and `RiskAssessment` domain model; real risk evaluation logic is deferred to Phase 9.
- **Consequences:** Mathematically guarantees capital preservation constraints cannot be bypassed.

---

## ADR-004: skfolio Evaluation Against Transparent Baselines
- **Status:** Approved
- **Context:** Complex optimizers can overfit in-sample and fail out-of-sample due to parameter estimation error.
- **Decision:** `skfolio` is adopted behind `IPortfolioOptimizer`, but **must be evaluated for statistically significant incremental value versus transparent baselines out-of-sample** (Equal Weight, Inverse Volatility, Cash/No-Trade). The system must NOT force skfolio to win. If a simple baseline is more robust out-of-sample, ACASH selects the baseline.
- **Consequences:** Balances advanced portfolio optimization and risk-allocation methods with rigorous empirical baseline discipline.

---

## ADR-005: NautilusTrader as Tier-2 Event Simulation Candidate & Phase 1 Boundary
- **Status:** Approved
- **Context:** Realistic backtesting requires order-book matching, queue priority, and latency models.
- **Decision:** NautilusTrader is classified as **ADAPT — Tier-2 event-driven simulation and future execution candidate**. Phase 1 MUST NOT implement live Nautilus execution. Phase 1 defines abstract interfaces (`IBacktestEngine`, `IExecutionEngine`) and Mock/InMemory implementations only. NautilusTrader integration remains a future Phase 5 PoC.
- **Consequences:** Prevents premature coupling and preserves sovereign domain independence.

---

## ADR-006: Analytical Data (Parquet + DuckDB) vs Transactional State (SQLite) & PostgreSQL Deferral
- **Status:** Approved
- **Context:** Analytical time-series queries and transactional operational state require different database characteristics.
- **Decision:**
  - Analytical / Research Data: Local partitioned **Parquet files + DuckDB** query engine. (DuckDB is NOT used as a transactional control-plane DB).
  - Transactional Operational State: Local **SQLite** for V1 (order states, positions, and **append-only decision audit ledger**).
  - Enterprise Control Plane: **PostgreSQL is DEFERRED** until concurrent multi-process writers, production durability, or operational requirements justify it. (Do NOT install PostgreSQL in Phase 1).
- **Consequences:** Delivers optimal performance for each access pattern without premature server overhead.

---

## ADR-007: Bi-Temporal Point-in-Time Data Modeling (Alpha-Lake Principles)
- **Status:** Approved
- **Context:** Temporal leakage and look-ahead bias in data ingestion invalidate backtesting results.
- **Decision:** Adopt bi-temporal modeling principles natively: every record explicitly stores $t_{\text{event}}$ (when it occurred) and $t_{\text{knowledge}}$ (when it was ingested). Queries enforce $t_{\text{knowledge}} \le T_{\text{decision}}$.
- **Consequences:** Guarantees absolute prevention of look-ahead leakage.

---

## ADR-008: Two-Tier Backtesting Substrate
- **Status:** Approved
- **Context:** Exploring wide parameter spaces is slow in event engines, while vectorized engines lack realistic fill fidelity.
- **Decision:** Implement a two-tier methodology:
  1. **Tier-1:** `vectorbt` for rapid exploratory factor scanning and parameter sweeps.
  2. **Tier-2:** `NautilusTrader` candidate / Custom event engine for realistic microstructure validation.
- **Consequences:** Combines maximum research exploration speed with institutional validation rigor.

---

## ADR-009: Strict Confinement of AI & Foundation Models
- **Status:** Approved
- **Context:** Foundation models (e.g. Kronos, Vibe-Trading, LLMs) can hallucinate and are non-deterministic.
- **Decision:** Confine AI strictly to the quantitative research layer (`acash.research.ai`) for hypothesis drafting and summary generation. No AI system will have direct execution, portfolio weight, or risk control access.
- **Consequences:** Harnesses AI for research ideation while keeping operational capital allocation 100% deterministic.

---

## ADR-010: MT5 Adapter as Initial External Execution Gateway
- **Status:** Approved
- **Context:** MetaTrader 5 provides access to retail broker liquidity on Windows.
- **Decision:** MT5 is adopted strictly as an initial external execution adapter behind `IExecutionEngine`. Zero strategy or portfolio logic will be written in MQL5.
- **Consequences:** Allows broker connectivity without platform dependence.

---

## ADR-011: Strategy Lifecycle State Machine & Degradation Policy
- **Status:** Approved
- **Context:** Strategies inevitably experience alpha decay over time.
- **Decision:** Enforce formal state transitions: $\text{IDEA} \to \text{RESEARCH} \to \text{VALIDATION} \to \text{PAPER} \to \text{SMALL LIVE} \to \text{PRODUCTION} \to \text{DEGRADATION} \to \text{REDUCE} \to \text{RETIRE}$.
- **Consequences:** Automatically protects capital against decaying alpha.

---

## ADR-012: Adoption of yfinance as Research Data Adapter
- **Status:** Approved
- **Context:** Quantitative research requires accessible historical market and fundamental data for rapid prototyping.
- **Decision:** Adopt `yfinance` as a **research-oriented market/fundamental data adapter with no paid subscription requirement for the intended research use case, subject to source availability, API limitations, and applicable terms**. It is strictly isolated behind `IMarketDataProvider` and prohibited from live production execution feeds.
- **Consequences:** Enables zero-subscription research prototyping without compromising live data integrity.

---

## ADR-013: Selection of skfolio over PyPortfolioOpt
- **Status:** Approved
- **Context:** Modern portfolio theory and risk budgeting require a unified, scikit-learn compatible optimization framework.
- **Decision:** Adopt `skfolio` and reject `PyPortfolioOpt` to eliminate duplicate dependency bloat and API fragmentation.
- **Consequences:** Standardizes on modern portfolio optimization and cross-validation while eliminating redundant dependencies.

---

## ADR-014: Adoption of Plotly for Research & Analytics Visualization
- **Status:** Approved
- **Context:** Visualizing backtest tear sheets, equity curves, drawdown waterfalls, and factor distributions requires interactive charting.
- **Decision:** Adopt `plotly` as an analytical visualization dependency confined to `acash.telemetry`, research notebooks, and dashboards. Plotly has zero access to decision or risk logic.
- **Consequences:** Provides interactive visualization without impacting core engine performance.

---

## ADR-015: Python-First Core and Conditional Native Performance Acceleration
- **Status:** Approved
- **Context:** Premature C++ implementation introduces high development friction.
- **Decision:** ACASH is built **Python-first**. Native performance optimization follows a strict scientific workflow:
  $$\text{CORRECTNESS (Python)} \to \text{PROFILE} \to \text{IDENTIFY BOTTLENECK} \to \text{BENCHMARK} \to \text{OPTIMIZE (Rust/Numba)}$$
  Custom C++ is rejected for V1. Rust is leveraged via NautilusTrader's pre-compiled event engine bindings when needed.
- **Consequences:** Maximizes development velocity and mathematical correctness while preserving a proven path for high-performance execution.

---

## ADR-016: Domain Entity Flow Decoupling, Normalized Valuation & Append-Only Audit Lineage
- **Status:** Approved
- **Context:** Modeling domain entities as a single parent-child hierarchy violates the semantic separation between capital/portfolio state and decision/execution events.
- **Decision:**
   1. Separate domain entities into decoupled flows:
      - **External Account State:** Broker / Account source $\to$ `AccountState`
      - **Internal Portfolio State:** `Positions` + Market Prices $\to$ `PortfolioState`
      - **Decision Flow:** $\text{Signal} \to \text{TargetAllocation} \to \text{RiskAssessment} \to \text{Order} \to \text{Fill} \to \text{Position/Portfolio State Transition}$
   2. **Immutable State Transitions:** State updates never mutate existing frozen objects; receiving a Fill produces **NEW Position** and **NEW PortfolioState** snapshots.
   3. `DecisionRecord` is an **append-only audit and lineage object** referencing the complete decision chain. Historical decisions are never overwritten or retroactively mutated.
   4. Monetary values are normalized in a defined ACASH base currency.
   5. Configuration directory is standardized as `configs/` across documentation and code (`configs/*.yaml`).
- **Consequences:** Establishes mathematically sound domain entities, complete auditability, immutability guarantees, and clean separation of concerns.

---

## ADR-017: Phase 1 Spot-Like Portfolio Valuation, Fill Cash Flows & Allocation Boundary
- **Status:** Approved
- **Context:** In a spot-like asset purchase model, cash is exchanged directly for asset holdings. Calculating portfolio equity as `cash_balance + unrealized_pnl` incorrectly assumes a margin/derivative model where cash is not expended on asset acquisition. Furthermore, execution slippage units and allocation validation boundaries require explicit definition.
- **Decision:**
  1. **Portfolio Total Equity Source of Truth (Phase 1 Spot Assumption):**
     $$\text{Portfolio Total Equity} = \text{cash\_balance} + \sum_{i} \text{Position}_i.\text{market\_value}$$
     where $\text{Position.market\_value} = \text{signed quantity} \times \text{current\_price}$.
  2. **Fill Cash-Flow Semantics & Zero Double-Counting:**
     - **BUY Fill:** `cash_balance` decreases by $(\text{fill\_price} \times \text{fill\_quantity}) + \text{fee}$.
     - **SELL Fill:** `cash_balance` increases by $(\text{fill\_price} \times \text{fill\_quantity}) - \text{fee}$.
     - **Realized PnL:** Realized PnL is automatically incorporated into `cash_balance` via the trade cash proceeds/payments upon closing/reducing a position. Realized PnL is retained strictly as a reporting metric and MUST NOT be added to cash or equity a second time.
  3. **Slippage Units & Execution Metric:** `Fill.slippage` is defined as the absolute price difference between the execution reference price and the actual fill price, expressed in price units of the instrument. Because `fill_price` already reflects the executed price, slippage is an execution quality reporting metric only and is NOT subtracted from cash/PnL separately.
  4. **TargetAllocation Semantic Boundary:** Phase 1 does NOT enforce $\sum \text{weights} + \text{cash\_weight} = 1.0$ as a domain invariant. The domain model validates structural finite values only. Leverage constraints, shorting, gross/net limits, and portfolio feasibility are strictly enforced by future Portfolio and Risk Engines.
  5. **Order Status Lifecycle:** `Order` includes `status: OrderStatus = OrderStatus.PENDING` (`PENDING`, `SUBMITTED`, `FILLED`, `PARTIALLY_FILLED`, `CANCELLED`, `REJECTED`).
- **Consequences:** Enforces strict cash conservation, prevents realized-PnL double counting, clarifies slippage units, and preserves architectural flexibility for leveraged/market-neutral strategies.

---

## ADR-018: Reality Gap Analysis & Execution Deviation Architecture
- **Status:** Approved
- **Context:** Backtest simulation results and paper trades inevitably diverge from live market execution due to spread expansion, quote latency, adverse selection, market impact, execution venue routing, and broker slippage. Treating strategy underperformance purely as an alpha failure without isolating execution friction leads to false model refactoring.
- **Decision:**
  1. **Reality Gap Pipeline:** Establish a continuous multi-stage pipeline:
     $$\text{Backtest} \to \text{Paper / Shadow} \to \text{Live} \to \text{Reality Gap Attribution}$$
     Attributing execution deviations systematically to:
     - **Data error** (quote timestamp jitter, stale prices, bar aggregation anomalies)
     - **Model / alpha error** (signal decay, parameter overfitting, regime shift)
     - **Execution error** (excess slippage, adverse queue priority, latency spikes)
     - **Broker / venue conditions** (spread blowout, asymmetric requotes, margin policy change)
  2. **Methodological Modeling Principles:**
     - **Spread Model:** Execution-sensitive research must model spread at the highest fidelity supported by available market data and strategy horizon. Lower-fidelity spread assumptions may be used when appropriate, but their limitations must be explicit.
     - **Slippage Model:** Adopt a graduated complexity approach ($\text{simple assumption} \to \text{empirical calibration} \to \text{liquidity/order-size aware} \to \text{nonlinear model only when evidence justifies it}$).
     - **Capital Flow Separation:** External capital flows (deposits, withdrawals, transfers) are treated as first-class capital flow events, strictly isolated from Trading PnL and trading-performance attribution metrics.
     - **Martingale & Exposure Escalation:** Classify Martingale-like exposure escalation as a **HARD RISK FLAG** requiring explicit risk justification, tail-loss analysis, ruin probability analysis, and non-bypassable risk-gate enforcement.
     - **Data Fidelity:** Data fidelity must match strategy horizon, execution sensitivity, and market microstructure requirements. Higher-fidelity tick/quote data is required when lower-resolution data cannot adequately represent the strategy's execution assumptions.
  3. **Guiding Principle:** The highest-value empirical capability of ACASH is measuring the difference between quantitative research expectation and live market reality.
- **Consequences:** Provides actionable empirical feedback to improve simulation realism, prevents erroneous alpha discarding, isolates broker friction, and enforces institutional-grade execution observability.

---

## ADR-019: Immutable Part Storage, Event-Key/Revision-Identity Semantics & Data Contract
- **Status:** Approved
- **Context:** Overwriting a single `data.parquet` file per partition creates serious data-loss and concurrency risks upon subsequent batch ingestions. Furthermore, timestamp monotonicity and cadence checks must distinguish between sequential distinct event observations and multiple historical revisions of the same event observation.
- **Decision:**
  1. **Immutable Append-Only Part Storage:** Datasets are stored as partitioned immutable part files:
     `data/parquet/{symbol}/{timeframe}/year={YYYY}/part-{batch_id}.parquet`
     Normal ingestion never overwrites existing part files; DuckDB queries scan all parts via Parquet globs.
  2. **Global Batch Idempotency & Strict 1:1 Ingestion Unit Contract:**
     - A canonical batch is defined as: $\text{ONE batch\_id} \equiv \text{ONE ingestion unit} \equiv \text{ONE source\_id} \equiv \text{ONE symbol} \equiv \text{ONE timeframe} \equiv \text{ONE year partition} \equiv \text{ONE immutable part file}$.
     - Multi-stream or multi-partition raw inputs are split into independent ingestion units with unique batch IDs.
     - `batch_id` is a globally unique immutable identity mapping to exactly one part path: `data/parquet/{symbol}/{timeframe}/year={YYYY}/part-{batch_id}.parquet`.
     - Retrying the same `batch_id` with identical canonical content is safely idempotent (no-op returning existing part path).
     - Ingestion of an existing `batch_id` with differing canonical content is rejected with `BatchCollisionError`.
     - Each `batch_id` produces exactly one provenance audit record.

  3. **Canonical Types & Precision Limits:**
     - Timestamps: `timestamp[us, tz=UTC]` (UTC microsecond precision).
     - Financial Numerics: `Decimal128(38, 18)` (Canonical representation supporting up to 18 fractional scale places; out-of-bound or non-finite values rejected).
  4. **Event Observation Key, Revision Identity & Immutable `revision_seq`:**
     - `Event Observation Key`: `(source_id, symbol, timeframe, event_start_utc)`.
     - `Revision Identity`: `(event_observation_key, knowledge_time_utc, revision_seq)`.
     - `revision_seq` is an **immutable persistence sequence value assigned once upon initial acceptance** ($\ge 1$, strictly unique per Event Observation Key, never renumbered or mutated).
     - **Deterministic Initial Tie-Breaker Scope:** `canonical_content_fingerprint ASC` is used as a tie-breaker **ONLY among unpersisted revisions newly accepted together in the same batch/operation** sharing the same `knowledge_time_utc`. It is never used to re-rank or renumber existing persisted records. Revisions arriving in later batches receive the next available sequence numbers (`seq = max(existing_seq) + 1`).
     - **Duplicate Rejection:** Same event + same knowledge + identical content is rejected as duplicate revision error (`ERROR / INVALID`).
     - **P-I-T Temporal Priority:** `knowledge_time_utc` is the primary ordering field (`ORDER BY knowledge_time_utc DESC, revision_seq DESC`); `revision_seq` acts strictly as the deterministic tie-breaker for equal knowledge times.
     - Duplicate Revision Identities are rejected as fatal errors (`ERROR / INVALID`) against incoming batches and existing canonical parts under the **Phase 2 single-writer scope**.




  5. **Distinct Event Monotonicity & `event_end_utc` Consistency Across Revisions:**
     - All revisions for the same Event Observation Key must have the exact same `event_end_utc` (differing values rejected as `ERROR / INVALID`).
     - Event-time monotonicity is validated over distinct event observation keys: $t_{\text{event\_start}, j+1} \ge t_{\text{event\_end}, j}$.
     - Revisions within an event are ordered and validated by distinct `(knowledge_time_utc, revision_seq)` with $t_{\text{knowledge}} \ge t_{\text{event\_end}}$.

  6. **Source-Aware P-I-T Revision Selection Standard:**
     ```sql
     WITH eligible AS (
         SELECT * FROM read_parquet('data/parquet/{symbol}/{timeframe}/**/*.parquet')
         WHERE knowledge_time_utc <= $as_of_knowledge_time_utc
           AND event_start_utc >= $start_utc AND event_end_utc <= $end_utc
     )
     SELECT * FROM eligible
     QUALIFY ROW_NUMBER() OVER (
         PARTITION BY source_id, symbol, timeframe, event_start_utc
         ORDER BY knowledge_time_utc DESC, revision_seq DESC
     ) = 1
     ORDER BY source_id ASC, event_start_utc ASC;
     ```
  7. **Deterministic Logical Data Hashes:**
     - `raw_source_sha256`: SHA-256 of raw input bytes.
     - `canonical_batch_sha256`: SHA-256 computed over the deterministic binary serialization of canonical data columns sorted by Revision Identity (excluding digest fields). Completely invariant to physical Parquet compression, chunking, or input row permutations.
     - Recorded in the append-only application audit log (`data/provenance_ledger.jsonl`).
  8. **Recoverable Batch Commit Protocol (Commit-Intent Manifest):**
     - Single-writer model without heavy distributed transactions.
     - **Manifest Lifecycle States:** `PREPARED` $\to$ `PART_PUBLISHED` $\to$ `COMMITTED` stored in `data/manifests/manifest-{batch_id}.json` via atomic write/fsync/replace.
     - **Sequence:** validate $\to$ normalize $\to$ compute `raw_source_sha256` & `canonical_batch_sha256` $\to$ write/fsync manifest (`PREPARED`) $\to$ write/validate staging part $\to$ `os.replace` to `part-{batch_id}.parquet` $\to$ update manifest (`PART_PUBLISHED`) $\to$ idempotent provenance ledger append from manifest metadata $\to$ update manifest (`COMMITTED`).
     - **Crash Recovery:**
       - Crash after part publication: recovery verifies `canonical_batch_sha256` from manifest, appends missing provenance, and transitions manifest to `COMMITTED`.
       - Crash after provenance append: recovery detects existing matching record in provenance ledger, does not append duplicate record, and transitions manifest to `COMMITTED`.
       - Orphan parts without manifests are quarantined without guessing metadata.



- **Consequences:** Eliminates partition overwrite data-loss risks, decouples event-time sequencing from revision ordering, guarantees logical invariance in cryptographic hashing, and enforces deterministic append-only growth.










