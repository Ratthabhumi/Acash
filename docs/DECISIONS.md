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

---

## ADR-020: Market Microstructure Canonical Domains & Length-Prefixed Binary Serialization Protocol

- **Status:** **PROPOSED (Pending Phase 3 Sign-off)**
- **Date:** 2026-08-27
- **Context:** To support futures market microstructure research (e.g. CME ES/NQ) without violating the single-responsibility principle of the OHLCV Bar schema, ACASH expands to include distinct canonical data domains for Trades (Time & Sales) and Order Book (L2 Depth Snapshots & Deltas). To prevent delimiter collision and nanosecond precision loss during logical cryptographic hashing, an exact binary serialization protocol is required.
- **Decision:**
  1. **Domain Decoupling:** OHLCV (Phase 2), Trades (Phase 3A), and Order Book (Phase 3B) remain completely independent canonical domains with separate Arrow schemas, partition layouts, and point-in-time qualification queries.
  2. **Tri-Temporal Model:** Explicitly distinguishes `exchange_time_utc` (`timestamp[ns, tz=UTC]`, matching engine chronology), `feed_time_utc` (`timestamp[ns, tz=UTC]`, optional network egress), and `knowledge_time_utc` (`timestamp[us, tz=UTC]`, ACASH PIT qualification).
  3. **Calendar-Driven Session Determination:** `trading_date` is a session label produced by a versioned market/session calendar, not inferred from UTC time alone.
  4. **Opaque Sequence Scoping & Boundaries:** `source_seq_num` is an opaque upstream sequence identifier scoped to `(source_id, channel_id, symbol, trading_date)`. The schema does not assume contiguity, global uniqueness, or replay stability unless guaranteed by the source specification. Reset/restart rules are declared by source feeds and not inferred from session boundaries.
  5. **Message Identity vs. Row Identity:** Exchange network messages (packets) are decoupled from canonical row instances. Multi-trade/multi-depth messages expand deterministically via `match_sub_idx` and `level_idx`.
  6. **`trade_id` Optionality:** `trade_id` is nullable; ACASH never invents synthetic exchange IDs. Row uniqueness is guaranteed via the compound key.
  7. **Length-Prefixed Binary Serialization:** Provenance hashes (`canonical_trades_sha256`, `canonical_book_sha256`) use length-prefixed binary encoding `[uint32_be(len)][bytes]`, lossless `int64_be(epoch_nanoseconds)`, and record separator `0x1E`, guaranteeing collision-resistant determinism.
  8. **Downstream Feature Boundary & Configurable Research Conventions (Phase 3C):** Order Flow, Footprint Delta, Volume Profile (Value Area 70%), Imbalance (3x), and VWAP are computed as pure downstream mathematical transformations with versioned parameter configuration captured in Feature Manifests, containing zero strategy/signal logic.
- **Consequences:** Provides a rigorous, mathematically sound foundation for tick-by-tick microstructure research while eliminating look-ahead bias and delimiter ambiguity.

---

## ADR-021: Multi-Broker & Multi-Asset Architecture Decision (Asset-Agnostic Core, Independent Opportunity Discovery, and Policy-Driven Venue Routing)

- **Status:** **Approved (Architecture Decision — Documentation Only)**
- **Date:** 2026-09-04
- **Context:** ACASH is designed as an autonomous, opportunity-driven trading infrastructure. The Core engine must not be architecturally coupled to any single broker or to the asset classes supported by the initial integration (MetaTrader 5). The broker is an execution venue, not the definition of ACASH's opportunity universe.
- **Decision:**
  1. **Asset-Class Agnostic Core:** ACASH Core is independent of asset class. MT5 / Pepperstone integration does not make ACASH a "Forex-only" system. Alpaca integration does not make ACASH an "equities-only" system.
  2. **Independent Opportunity Discovery:** Opportunity discovery is decoupled from broker connectivity. The Opportunity Engine scans market data for mathematical/economic edges first, identifies candidate instruments, determines venue eligibility, and selects venues via explicit policy. It does not restrict discovery to currently connected brokers.
  3. **Multi-Asset Architectural Horizon:** System design supports future discovery across FX, US Equities, ETFs, Futures, Options, and Crypto, contingent on canonical data, alpha, risk, and execution support.
  4. **Instrument & Venue Routing Layer:** Conceptually introduces a policy-driven, deterministic routing layer between Admission and Venue Adapters (e.g. AAPL $\to$ Alpaca/IBKR, EURUSD $\to$ MT5/OANDA).
  5. **Broker Roadmap & Priority:**
     - 1. MetaQuotes MT5 Demo: Current active certification baseline.
     - 2. Pepperstone + MT5: Primary external retail MT5 execution candidate (does not define asset scope).
     - 3. Alpaca: Existing integration/testing candidate + future US Equities/ETF execution candidate (requires formal architectural audit before live production use).
     - 4. OANDA API: Secondary direct-API native FX execution candidate (proves direct REST/v20 vs terminal-mediated execution).
     - 5. Interactive Brokers (IBKR): Future multi-asset execution candidate (Stocks, ETFs, Futures, Options).
     - 6. Multiple simultaneous live brokers: Strictly NOT APPROVED at current stage.
  6. **Zero Automatic Order Duplication:** Orders are never automatically mirrored or duplicated across venues. Multi-broker architecture is a capital allocation and venue routing model; total risk exposure remains strictly controlled.
  7. **Canonical Invariants:** All broker adapters must adhere to the sovereign ACASH boundary: zero lifecycle authority, fail-closed startup, absorbing BLOCKED state, zero synthetic fills or intent IDs, and full 6-D reconciliation provenance.
  8. **Full Specification:** Detailed in [`docs/architecture/multi_broker_multi_asset_decision.md`](architecture/multi_broker_multi_asset_decision.md).
- **Consequences:** Permanently protects ACASH Core against broker and asset-class lock-in, provides a clear multi-venue roadmap, and guarantees that multi-broker expansion preserves mathematical and governance integrity without premature implementation complexity.

---

## ADR-022: Market-Adaptive, Strategy-Agnostic & Event-Aware Trading Governance (Flexible Decisions + Fixed Safety Guardrails)

- **Status:** **Approved (Strategic Governance & Research Principle — Documentation Only)**
- **Date:** 2026-09-04
- **Context:** ACASH is an autonomous quantitative trading infrastructure. The system must not become permanently coupled to any single strategy, asset class, broker, or market regime, nor suffer from developer hubris assuming internal models or complex architectures are inherently superior. Trading performance must be evaluated purely on empirical risk-adjusted evidence across distinct market regimes and event conditions.
- **Decision:**
  1. **Core Paradigm (Flexible Decisions + Fixed Safety Guardrails):** ACASH Core decouples execution/risk infrastructure from strategy alpha. Software reliability, safety state machines, and reconciliation do not equate to a trading edge.
  2. **Strategy-Agnostic Neutrality:** Commercial EAs, grid/martingale systems, trend followers, and third-party algorithms are treated as legitimate benchmarks, research candidates, and potential execution targets, evaluated without condescension or unverified acceptance.
  3. **Market-Adaptive & Event-Aware Risk Governance:** High-impact economic news is treated as an explicit risk dimension with graduated policies (ALLOW, REDUCE, HOLD, BLOCK NEW ENTRY, DELAY, FLATTEN, EXIT, $0 ALLOCATION) rather than a crude universal binary trading ban. Acknowledges that Stop Loss is not a guaranteed execution price during news dislocations.
  4. **Strategy $\times$ Regime Evaluation:** Recognizes that strategies possess regime-dependent edges ($\text{Strategy} \times \text{Regime}$) rather than universal superiority.
  5. **Explainable Dynamic Capital Allocation:** Capital scales dynamically with empirical evidence and regime suitability, but remains strictly bounded by hard, non-negotiable risk limits. Every allocation decision must answer 9 explicit audit questions.
  6. **Anti-Bias Code of Conduct:** Epistemic claims must distinguish `PROVEN`, `REPORTED`, `UNVERIFIED`, `INFERRED`, and `UNKNOWN`. Evaluation rules, test periods, and hurdle rates must be frozen prior to tournaments to prevent retrospective goalpost shifting.
  7. **Full Specification:** Detailed in [`docs/architecture/market_adaptive_strategy_governance.md`](architecture/market_adaptive_strategy_governance.md).
  8. **Research & Strategy Evaluation Extension:** The formal 12-layer strategy evaluation methodology, cost models, near-death analysis, and fair tournament framework are detailed in [`docs/architecture/strategy_forensic_evaluation_framework.md`](architecture/strategy_forensic_evaluation_framework.md).
- **Consequences:** Permanently protects ACASH against self-deception, model overfitting, and architectural dogmatism. Establishes a permanent culture of intellectual honesty where capital allocation decisions are guided strictly by empirical evidence rather than ownership.

---

## ADR-023: Strategy Admission Standard, Quantitative Market State Architecture & Bounded Capital Governance

- **Status:** **Approved (Phase 17 Rev 4.1 Specification & Governance Contract)**
- **Date:** 2026-09-04
- **Context:** Quantitative systems fail when observed profitability is conflated with persistent skill or when backtests are treated as executable reality. To prevent curve-fitting, survivorship bias, regime blindness, and premature capital allocation, ACASH requires a formal institutional Strategy Admission Standard before any strategy may enter the sovereign catalog or be considered for capital allocation.
- **Decision:**
  1. **Epistemic Invariant:** Observed Profit $\neq$ Proven Skill $\neq$ Structural Edge $\neq$ Luck-Free Performance. Observed profitability is evidence to investigate, not permission to allocate capital.
  2. **Multi-Tier Pipeline:**
     $$\text{Raw Market Data} \longrightarrow \text{Feature Engineering} \longrightarrow \text{MarketStateVector} \longrightarrow \text{Regime Classification} \longrightarrow \text{Strategy} \times \text{Regime} \longrightarrow \text{Attribution} \longrightarrow \text{Admission} \longrightarrow \text{Capital Eligibility}$$
  3. **Quant Candlestick Architecture:** Candle/Bar representations are structured numerical observations, not visual discretionary signals. Features like returns, body/range ratio, wick asymmetry, and close location feed continuous `MarketStateVector` without embedding discrete regime labels.
  4. **Volume Provenance:** `VolumeType` strictly distinguishes `TICK_VOLUME`, `REAL_VOLUME`, `EXCHANGE_VOLUME`, and `UNKNOWN`.
  5. **Decoupled Uncertainty & Confidence:** Classification status (`CLASSIFIED`, `UNCLASSIFIED`, `INSUFFICIENT_EVIDENCE`), numeric confidence score, and derived `ConfidenceAssessment` (`ACCEPTABLE` vs `LOW`) carry explicit `ParameterProvenance` (eliminating ungrounded magic numbers).
  6. **11-Gate Admission Lifecycle (Gate 0–10):** From Strategy Definition (Gate 0) through Forward Demo Evidence (Gate 8) and Final Admission Dossier (Gate 10).
  7. **Strict Anti-Calendar Certification Rule:** Calendar duration (e.g. 90 days on demo) is strictly rejected as proof of edge. Certification requires `EffectiveEvidenceSample` ($N_{\text{eff}}$), regime diversity, stress survival, and execution observations.
  8. **Performance Attribution & Residual Invariant:** Historical performance is decomposed across 5 categorical sources (Skill, Structural Edge, Factor Exposure, Regime Tailwind, Luck). Unexplained residual return is strictly NOT assumed to be alpha.
  9. **Rejection of Single Skill Score:** Composite scalar scores (e.g. `skill_score = 87/100`) are prohibited; skill is represented via multi-dimensional `SkillEvidence` vector DTO using `EvidenceSupportLevel`.
  10. **Alternative Explanation Register:** Mandatory register of counter-hypotheses (`ALT-01` through `ALT-06`) answering the 20 Mandatory Admission Questions, including mandatory Q20: *"Why should this strategy NOT receive additional capital yet?"*
  11. **Decoupled Mechanism vs Style:** `StrategyMechanism` (market interaction/economics) is strictly separated from `StrategyStyle` (behavioral archetype).
  12. **Bounded Capital Allocation & Mandatory Zero Floor:** Phase 17 governs eligibility, bounds, proposals, and zero-allocation semantics (`allocation = $0.00` is always valid and default). Optimization solvers are deferred to Phase 21.
  13. **Strict Boundaries:** Live capital remains hard-locked at $0.00. Zero mutations to `src/acash/execution/`. MetaTrader 5 demo terminal remains 100% flat.
- **Consequences:** Permanently protects ACASH against performance chasing, selection bias, and unearned capital allocation. Establishes a reproducible, institutional standard for strategy research and qualification.

---

## ADR-024: Adaptive Multi-Horizon Strategy & Market-Regime Architecture (ACASH is Strategy-Agnostic and Market-Regime-Aware)

- **Status:** **Approved (Architecture Decision & Design Record — Phase 23 Baseline)**
- **Date:** 2026-09-05
- **Context:** ACASH is frequently misconstrued through traditional algorithmic trading archetypes (e.g. "Scalping Bot", "Intraday EA", "Swing System", or "Grid Trader"). Furthermore, traders often treat position scaling as fixed capital percentages (e.g. "3 fixed tranches of 30/30/40") or conflate signal generation with immediate trade execution. A foundational architectural boundary must be established: ACASH is an autonomous risk-controlled trading infrastructure; trading style, holding period, and entry mechanics are strategy-level properties, not platform identities.
- **Decision:**
  1. **Core Platform Identity:** ACASH Core is risk-controlled trading infrastructure (Execution, Risk, Reconciliation, Governance). Scalping, Intraday, Swing, Long-term, Trend Following, and Mean Reversion belong exclusively to the Strategy Layer.
  2. **Strategy != Authority:** Strategies propose; the Deterministic Risk Engine admits or vetoes; the Execution Engine performs only admitted actions; Governance authorizes operational parameters. A strategy signal is never an order.
  3. **Rejection of Fixed Capital Slicing:** The core engine strictly rejects hardcoded slice rules (e.g. 30/30/40). Position sizing is decoupled into Target Position, Risk Budget, Entry Schedule, and Dynamic Recalculation.
  4. **Risk-First Position Sizing:** Position size is derived from allowable currency Risk Budget divided by Stop Distance, never from percentage of capital alone.
  5. **Scale-In Philosophy:** Confirmation-driven pyramiding is the default ACASH philosophy. Blind averaging down is strictly rejected as a core engine default and permitted only in specialized, risk-bounded strategies admitted under Phase 17 standards.
  6. **Dynamic Risk Recalculation:** Every individual entry tranche requires an independent, fresh evaluation by the Risk Engine. Earlier approvals confer zero automatic authorization for future tranches.
  7. **Market-Regime Context:** Market regimes inform strategy eligibility and scoring, but never directly override Risk Engine limits. In uncertain or unclassified regimes, the system defaults fail-closed to `Cash = 100% (NO_TRADE)`.
  8. **Strategy Tournament Pathway:** Empirical evidence across backtesting, walk-forward validation, paper trading, and multi-model tournaments determines strategy viability under each regime. Current system alignment with Swing/Medium horizon is an initial baseline, not an architectural lock-in.
  9. **Full Specification:** Formally documented in [`docs/architecture/adaptive_multi_horizon_strategy_architecture.md`](architecture/adaptive_multi_horizon_strategy_architecture.md).
- **Consequences:** Permanently protects ACASH against premature horizon or style lock-in, guarantees risk-first sizing across all strategy types, enforces confirmation-driven scaling discipline, and provides a clear architectural foundation for future Strategy Tournament (Phase 18) and Dynamic Allocation (Phase 21) implementations.
  10. **Phase 23 Amendment:** Formally extended by ADR-025 and [`docs/architecture/phase23_amendment_microstructure_and_shadow_decisions.md`](architecture/phase23_amendment_microstructure_and_shadow_decisions.md).

---

## ADR-025: Market Microstructure, Order-Book Event Intelligence & Shadow Decision Evaluation (Phase 23 Amendment)

- **Status:** **Approved (Phase 23 Architectural Amendment — Documentation & Design Only)**
- **Date:** 2026-09-05
- **Context:** Conventional OHLCV and trade-tape backtesting cannot reconstruct non-executed order dynamics (such as phantom depth, quote-stuffing, or rapid add/cancel bursts) because non-executed orders are absent from bar and tick datasets. Furthermore, evaluating trading performance based solely on executed trades introduces severe survivorship and filter bias: systems cannot determine whether a risk or regime filter was beneficial (prevented a disaster) or harmful (destroyed profitable alpha) without tracking counterfactual market outcomes for rejected decisions.
- **Decision:**
  1. **Research Data Hierarchy:** Formally define three research tiers: Level 1 (OHLCV bars), Level 2 (Trade tape / tick prints), and Level 3 (Order-book event stream: MBO/MBP with Add, Modify, Cancel, Execute).
  2. **Order-Book Intelligence:** Codify the invariant that *Order Book Snapshot $\neq$ Order Book Intelligence*. Real microstructure research requires time-ordered order-book event streams plus temporal analysis.
  3. **Microstructure Anomaly Detection (No Unverified Claims):** Potential spoofing-like patterns are treated as statistical liquidity fragility signals that reduce confidence or scale down position size (`MICROSTRUCTURE_NORMAL`, `MICROSTRUCTURE_CAUTION`, `MICROSTRUCTURE_ANOMALOUS`, `SUSPICIOUS_LIQUIDITY`). ACASH strictly prohibits claiming automated proof of illegal market manipulation or spoofing without formal empirical validation.
  4. **Strict Enforcement Boundaries:** Microstructure analysis is purely observational and contextual. It inserts into the strategy pipeline before the Risk Engine: `Signal Proposal` $\to$ `Microstructure Check` $\to$ `Deterministic Risk Engine` $\to$ `ALLOW / REDUCE / REJECT`. Microstructure signals CANNOT bypass the Risk Engine or transmit broker orders directly.
  5. **Shadow Decision System:** Every rejected, suppressed, or haircut candidate trade proposal generates an immutable `ShadowDecisionRecord`. The system tracks subsequent market path (MFE, MAE, counterfactual PnL) over the strategy's expected horizon to measure filter efficiency and calculate false-positive filtering costs. Actual trading equity is strictly partitioned from shadow/hypothetical PnL.
  6. **External System & Reference Discipline:** Commercial references (e.g. Phantom Trader / GhostBot) are classified strictly as external conceptual inspiration, NOT validated benchmarks or proven detectors. External samples (such as public 44-trade runs) are observable reference data, NOT ground-truth training or validation data.
  7. **Full Specification:** Detailed in [`docs/architecture/phase23_amendment_microstructure_and_shadow_decisions.md`](architecture/phase23_amendment_microstructure_and_shadow_decisions.md).
- **Consequences:** Provides the formal data contract, feature space, and decision-learning infrastructure required for ACASH to evolve into a full temporal microstructure intelligence platform while preserving deterministic risk safety, fail-closed data quality handling, and strict governance boundaries.




