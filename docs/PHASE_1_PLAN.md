# ACASH — Phase 1 Foundation & Domain Core Plan

**Document:** `docs/PHASE_1_PLAN.md`  
**Version:** 3.4.0 (Immutable State Transitions & Normalized Value Applied)  
**Date:** 2026-08-27  
**Objective:** Build the sovereign foundation, domain types, abstract interfaces, configuration loader, structured logger, and unit test harness.

---

## 1. Phase 1 Scope & Boundaries

Phase 1 focuses **exclusively on foundational infrastructure**. In accordance with the Master Engineering Prompt:
- **Zero trading strategies** will be implemented in Phase 1.
- **Zero live broker connections** or network requests will be executed.
- **Zero premature microservices** or distributed queues will be created.
- **Zero live Nautilus execution:** Phase 1 defines `IBacktestEngine` and `IExecutionEngine` with in-memory mock adapters only. NautilusTrader integration remains a future Phase 5 PoC.
- **Zero trading or optimization logic:** Domain models define structure, invariants, and serialization only.
- **Zero Risk Engine logic:** Phase 1 defines the `IRiskEngine` interface contract and `RiskAssessment` domain model only; real risk evaluation logic is deferred to Phase 9.

---

## 2. Strict Dependency Classification

### 2.1 FINAL_RUNTIME_DEPENDENCIES (Phase 1+ Core Engine)
*Essential dependencies required for core domain execution, deterministic risk evaluation, and storage:*
- `pydantic>=2.0`: Strict type validation and immutable settings.
- `numpy>=1.24.0`: Array representations and vector math.
- `pandas>=2.0.0`: Tabular time-series structures.
- `scipy>=1.10.0`: Statistical distributions, optimization helpers.
- `duckdb>=0.9.0`: Embedded zero-overhead in-process SQL engine (analytical research queries).
- `sqlite3`: Python standard library local transactional state store (append-only ledger).
- `pyyaml>=6.0`: Configuration file serialization.
- `structlog>=23.1.0`: High-performance structured JSON logging.

### 2.2 FINAL_RESEARCH_DEPENDENCIES (Quant Research & Validation)
*Dependencies required for portfolio optimization, fast screening, validation, and analytics:*
- `skfolio>=0.3.0`: Portfolio optimization and risk-allocation methods (HRP, ERC, CVaR) and Combinatorial Purged CV.
- `vectorbt>=0.25.0`: Rapid Numba-accelerated vectorized parameter sweeps.
- `yfinance>=0.2.30`: Research-oriented market/fundamental data adapter (no paid subscription requirement for research use case).
- `plotly>=5.18.0`: Interactive charts, equity curves, and research tear sheets.
- `pytest>=7.4.0`: Automated test runner.
- `mypy>=1.5.0`: Static type checking across all packages.

### 2.3 OPTIONAL / DEFERRED DEPENDENCIES (Not Installed in Phase 1)
- `MetaTrader5`: Deferred to Phase 12 for Windows MT5 broker execution.
- `nautilus_trader`: Deferred to Phase 5 for Tier-2 event backtest PoC.
- `PostgreSQL`: **DEFERRED** (Reconsidered only if concurrent multi-process writers, production durability, or operational requirements justify it; do NOT install in Phase 1).
- `hummingbot`: Deferred until market-making / liquidity provision hypotheses are researched.
- `freqtrade`: Kept as reference code for crypto CCXT connectors; no package installation needed.
- `kronos`: Deferred until Phase 14 AI forecasting experiments.

### 2.4 REJECTED DEPENDENCIES (Explicitly Prohibited)
- `PyPortfolioOpt`: **REJECTED** (Redundant to `skfolio`; lacks scikit-learn API and CPCV).
- `QuantConnect LEAN (.NET CLR)`: **REJECTED** (Unnecessary C# runtime overhead in Python modular monolith).
- `Kafka / Redis / ClickHouse`: **REJECTED** (Unnecessary distributed infrastructure complexity; DuckDB + Parquet + SQLite is standard).
- `Custom C++ Substrate`: **REJECTED for V1** (Premature optimization; Python + NumPy/Numba/Nautilus Rust core is superior).

---

## 3. Phase 1 Deliverables & Components

### 3.1 Sovereign Domain Models (`acash.core.domain`)

#### A. Capital & Portfolio State Models (Immutable Snapshots)
- **`Instrument`:** Ticker symbol, asset class (`CRYPTO`, `EQUITY`, `FX`, `COMMODITY`), base/quote currency, minimum tick size, lot size precision.
- **`Position`:** Asset holding in base currency (`symbol`, `quantity`, `entry_price`, `current_price`, `unrealized_pnl`, `realized_pnl`, `timestamp_utc`).
- **`PortfolioState`:** Aggregated portfolio state snapshot (`timestamp_utc`, `positions: Dict[str, Position]`, `total_equity`, `cash_balance`, `margin_used`, `gross_exposure`, `net_exposure`, `unrealized_pnl`, `realized_pnl`).
- **`AccountState`:** Top-level broker account health snapshot (`account_id`, `currency`, `balance`, `equity`, `free_margin`, `margin_level_pct`, `leverage`, `is_live`, `timestamp_utc`).

#### B. Market Data & Decision/Execution Models
- **`Bar`:** Bi-temporal OHLCV record (`symbol`, `timeframe`, `event_start_utc`, `event_end_utc`, `knowledge_time_utc`, `open`, `high`, `low`, `close`, `volume`, `provenance_hash`).
- **`MarketDataSnapshot`:** Real-time top-of-book snapshot (`bid`, `ask`, `bid_size`, `ask_size`, `last_price`, `timestamp_utc`).
- **`Signal`:** Directional research signal (`direction` $[-1.0, 1.0]$, `expected_return`, `uncertainty` $[0.0, 1.0]$, `horizon_seconds`, `strategy_id`).
- **`TargetAllocation`:** Candidate portfolio weights (`weights: Dict[str, float]`, `cash_weight: float`, `rationale: str`).
- **`RiskAssessment`:** Risk evaluation verdict (`approved: bool`, `adjusted_weights: Dict[str, float]`, `rejection_reason: Optional[str]`, `max_drawdown_pct`, `risk_utilization_pct`).
- **`Order`:** Executable order intent (`order_id`, `symbol`, `order_type`, `side`, `quantity`, `price_limit`, `idempotency_key`, `created_at_utc`).
- **`Fill`:** Trade execution result (`fill_id`, `order_id`, `symbol`, `fill_price`, `fill_quantity`, `fee`, `slippage`, `timestamp_utc`).

#### C. Cross-Cutting Audit Lineage Model
- **`DecisionRecord`:** Append-only audit record capturing the decision chain:
  `{decision_id, timestamp_utc, inputs_snapshot_ref, signal_ref, target_allocation, risk_assessment, order_ids, fill_ids, realized_pnl, schema_version}`.

### 3.2 Normalized Monetary Valuation & Immutable State Transitions
- **Normalized Base Currency:** Monetary values are modeled in a defined ACASH base currency.
- **Account Balance vs Equity:**
  $$\text{Equity} = \text{Balance} + \text{Unrealized PnL}$$
  where $\text{Balance}$ represents the realized cash balance prior to unrealized position PnL.
- **Normalized Gross Exposure:**
  $$\text{Gross Exposure} = \sum_{i} |\text{Normalized Position Value}_i|$$
  where **Normalized Position Value** is the position value expressed in ACASH base currency.
- **Immutable State Transitions:** State updates never mutate existing frozen objects; receiving a `Fill` produces **NEW Position**, **NEW PortfolioState**, and **NEW AccountState** snapshots.
- **Deferred Valuation Rules:** Contract multipliers, futures contract specifications, CFD lot sizes, and live FX conversions remain deferred from Phase 1 domain models.

### 3.3 Abstract Interface Contracts (`acash.core.interfaces`)
- `IMarketDataProvider`: Point-in-time historical bar retrieval and live snapshot stream.
- `IFeatureEngine`: Point-in-time feature extraction with temporal anti-leakage verification.
- `IStrategy`: Hypothesis-driven signal generation.
- `IPortfolioOptimizer`: Portfolio allocation calculators (`skfolio` and transparent baselines).
- `IRiskEngine`: Deterministic hard risk evaluator contract (interface definition only).
- `IBacktestEngine`: Deterministic simulation engine abstraction.
- `IExecutionEngine`: Order routing, state reconciliation, and adapter management.
- `IDecisionLedger`: **Append-only** audit logger and research memory store interface (`append_decision`, `query_decisions`, `reconstruct_lifecycle`).

### 3.4 In-Memory Mock Adapters (`acash.execution.mock`)
- `MockExecutionEngine`: Deterministic in-memory order executor for unit testing.
- `MockMarketDataProvider`: In-memory synthetic bar and quote provider.
- `InMemoryDecisionLedger`: In-memory append-only decision store for contract testing.

### 3.5 Typed Configuration & Logging
- **`acash.core.config`:** Pydantic-based configuration schemas reading hierarchical YAML files from **`configs/*.yaml`** (`configs/base.yaml`, `configs/research.yaml`, etc.).
- **`acash.telemetry.logging`:** High-performance structured JSON logger with automatic API key / password redaction filters.

---

## 4. Phase 1 Testing Philosophy & Acceptance Criteria

### 4.1 Testing Philosophy
- **Do not equate passing tests with correctness.**
- **Do NOT impose an arbitrary 100% code-coverage target.** The objective is correctness and invariant enforcement, not vanity coverage percentages.

### 4.2 Required Acceptance Criteria
Before Phase 1 is deemed complete and Gate 1 is passed:
1. [ ] **Unit Tests Pass:** All unit test suites execute cleanly via `pytest`.
2. [ ] **Domain Invariants & Immutability Tested:**
   - Immutability (`frozen=True`) across all domain models (mutation raises exceptions).
   - Candlestick geometry invariants ($\text{High} \ge \max(\text{Open}, \text{Close})$, $\text{Low} \le \min(\text{Open}, \text{Close})$, $\text{Price} > 0$).
   - Normalized Account math invariants ($\text{Equity} = \text{Balance} + \text{Unrealized PnL}$, $\text{Gross Exposure} = \sum |\text{Normalized Position Value}|$).
   - State transition immutability: applying a Fill produces new distinct snapshot instances.
3. [ ] **Invalid States Tested:** Negative prices, inverted spreads, NaN/infinite returns, invalid allocations, and semantically invalid timestamps (e.g. `event_start > event_end`) raise explicit domain exceptions (with stream ordering handled at data ingestion/normalization).
4. [ ] **Interface Contracts Tested:** Abstract base classes cannot be instantiated directly; implementations satisfy type signatures.
5. [ ] **Serialization & Deserialization Tested:** Domain models cleanly serialize to and deserialize from JSON/dict without data truncation or precision loss.
6. [ ] **Append-Only Decision Ledger Contract Tested:** Decision ledger enforces immutable inserts, rejects updates/deletions, and permits full audit reconstruction.
7. [ ] **Deterministic Mock Behavior Tested:** In-memory mock execution (`MockExecutionEngine`), mock data (`MockMarketDataProvider`), and in-memory ledger (`InMemoryDecisionLedger`) produce deterministic equivalent outcomes for identical inputs, configuration, and execution environment.
8. [ ] **Configuration Validation Tested:** Missing keys, invalid types, and malformed environment variables in `configs/*.yaml` trigger clear Pydantic validation errors.
9. [ ] **Static Typing Verified:** `mypy` runs clean across `acash.core` and `acash.telemetry`.
