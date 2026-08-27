# ACASH — Phase 1 Foundation & Domain Core Plan (Final Semantic Lock)

**Document:** `docs/PHASE_1_PLAN.md`  
**Version:** 3.10.0 (Accounting & Semantic Lock Applied)  
**Date:** 2026-08-27  
**Objective:** Build the sovereign foundation, domain types, abstract interfaces, configuration loader, structured logger, and correctness test harness.

---

## 1. Phase 1 Scope & Boundaries

Phase 1 focuses **exclusively on foundational infrastructure**. In accordance with the Master Engineering Prompt:
- **Zero trading strategies** will be implemented in Phase 1.
- **Zero live broker connections** or network requests will be executed.
- **Zero premature microservices** or distributed queues will be created.
- **Zero live Nautilus execution:** Phase 1 defines `IBacktestEngine` and `IExecutionEngine` with in-memory mock adapters only.
- **Zero live market data feeds:** `IMarketDataProvider` defines interface contracts only; Phase 1 operates with zero network connectivity using `MockMarketDataProvider`.
- **Zero trading or optimization logic:** Domain models define structure, invariants, serialization, and immutability only.
- **Zero Risk Engine logic:** Phase 1 defines the `IRiskEngine` interface contract and `RiskAssessment` domain model only; real risk evaluation logic is deferred to Phase 9.

---

## 2. Dependency Workflow & Reproducibility (`uv`)

### 2.1 Single Dependency Workflow: `pyproject.toml` + `uv.lock`
- **`pyproject.toml`** is the **sole declaration source of truth** for all project metadata and dependencies.
- **`uv.lock`** is the resolved dependency lockfile providing a **reproducible dependency environment**.
- **No manual maintenance:** `requirements.txt` and `requirements-dev.txt` are NOT manually maintained.

### 2.2 Phase 1 Baseline Dependencies
*Strictly minimal dependencies required for Phase 1 domain modeling, configuration, structured logging, and testing:*
- `pydantic>=2.0`: Strict type validation, immutable models (`frozen=True`).
- `pyyaml>=6.0`: Hierarchical YAML configuration parsing.
- `structlog>=23.1.0`: High-performance structured JSON logging with credential redaction.
- `pytest>=7.4.0`: Automated correctness test harness.
- `mypy>=1.5.0`: Static type analysis.

### 2.3 Deferred Dependencies (Not in Phase 1 Baseline)
*Heavy research, analytical, optimization, and execution packages are deferred:*
- `numpy`, `pandas`, `scipy`, `duckdb`: Deferred to data ingestion / analytics / feature phases.
- `skfolio`, `vectorbt`, `yfinance`, `plotly`: Deferred to research / portfolio phases.
- `MetaTrader5`: Deferred to Phase 12 for Windows MT5 broker execution.
- `nautilus_trader`: Deferred to Phase 5 for Tier-2 event backtest PoC.
- `PostgreSQL`: **DEFERRED** (Reconsidered only if multi-user concurrency or production durability requires it).

---

## 3. Sovereign Domain Models & Type Specifications (`acash.core.domain`)

### 3.1 Numeric Type Distinction & Strict Finite Value Enforcement

To prevent binary floating-point rounding errors and ensure mathematical soundness:
- **`Decimal` (Financial / Monetary / Accounting / Execution Quantities):**
  - Prices: `open`, `high`, `low`, `close`, `bid`, `ask`, `last_price`, `entry_price`, `current_price`, `price_limit`, `fill_price`
  - Quantities / Sizes: `quantity`, `bid_size`, `ask_size`, `fill_quantity`, `volume`, `tick_size`, `lot_size`, `min_order_quantity`
  - Monetary & Balance Values: `cash_balance`, `balance`, `equity`, `free_margin`, `margin_used`, `unrealized_pnl`, `realized_pnl`, `gross_exposure`, `net_exposure`, `fee`, `slippage`
  - *Invariant:* `Decimal` values must be finite and real; `Decimal('NaN')`, `Decimal('Infinity')`, and `Decimal('-Infinity')` are strictly rejected.
- **`float` (Statistical / Model / Ratio Quantities):**
  - `direction` (Range $[-1.0, 1.0]$)
  - `expected_return` (Continuous expected drift)
  - `uncertainty` (Range $[0.0, 1.0]$)
  - `weights` (Portfolio allocation ratios)
  - `cash_weight` (Cash weight ratio)
  - `margin_level_pct`, `leverage`, `max_drawdown_pct`, `risk_utilization_pct`
  - *Finite Rejection Rule:* **All float-valued domain fields must be strictly finite.** `math.isnan(x)` and `math.isinf(x)` are strictly rejected at model validation.

---

### 3.2 Immutable Mapping Specification (Pydantic-Compatible)

Domain collections (`PortfolioState.positions`, `TargetAllocation.weights`, `RiskAssessment.adjusted_weights`) follow the pipeline:
$$\text{Input Mutable Mapping} \to \text{Defensive Copy} \to \text{Immutable Internal Representation} \to \text{Domain Object}$$

The implementation guarantees:
1. Mutating the original input mapping after passing it to a domain constructor does NOT affect the domain object.
2. Mutating the domain object's mapping directly is rejected (e.g. raises `TypeError`).
3. Serialization (JSON / dict) operates cleanly via Pydantic.
4. Deserialization reconstructs equivalent immutable state.

---

### 3.3 Sovereign Domain Models

#### A. Enums (`acash.core.domain.enums`)
- **`AssetClass`:** `CRYPTO`, `EQUITY`, `FX`, `COMMODITY`
- **`BarTimeframe`:** `M1`, `M5`, `M15`, `H1`, `H4`, `D1` (`TICK` is NOT a bar timeframe)
- **`OrderType`:** `MARKET`, `LIMIT`, `STOP`
- **`OrderSide`:** `BUY`, `SELL`
- **`OrderStatus`:** `PENDING`, `SUBMITTED`, `FILLED`, `PARTIALLY_FILLED`, `CANCELLED`, `REJECTED`
- **`StrategyState`:** `ACTIVE`, `PAUSED`, `STOPPED`

#### B. Capital & Portfolio State Models
- **`Instrument`:**
  - `symbol: str`
  - `asset_class: AssetClass`
  - `base_currency: str`
  - `quote_currency: str`
  - `tick_size: Decimal` (> 0)
  - `lot_size: Decimal` (> 0)
  - `min_order_quantity: Decimal` (> 0)
- **`Position`:**
  - `symbol: str`
  - `quantity: Decimal` *(Signed: `+` = Long, `-` = Short, `0` = Flat)*
  - `entry_price: Decimal` (>= 0)
  - `current_price: Decimal` (>= 0)
  - `unrealized_pnl: Decimal`
  - `realized_pnl: Decimal`
  - `timestamp_utc: datetime`
  - Property: `market_value: Decimal = quantity * current_price` *(Phase 1 spot-like assumption)*
- **`PortfolioState`:**
  - `timestamp_utc: datetime`
  - `positions: Mapping[str, Position]` *(Defensively copied, immutable mapping)*
  - `cash_balance: Decimal` *(Realized account cash reflecting trade cash proceeds/payments and fees)*
  - `total_equity: Decimal` *(Source of Truth: $\text{cash\_balance} + \sum \text{Position.market\_value}$)*
  - `margin_used: Decimal` (>= 0)
  - `gross_exposure: Decimal` *(Invariant: $\sum |market\_value_i|$)*
  - `net_exposure: Decimal` *(Invariant: $\sum market\_value_i$)*
  - `unrealized_pnl: Decimal` *(Derived/reporting metric: $\sum Position_i.unrealized\_pnl$)*
  - `realized_pnl: Decimal` *(Reporting-only cumulative metric; strictly NOT added to total_equity)*
- **`AccountState`:**
  - *Derived strictly from external broker / account feed (never derived from PortfolioState).*
  - `account_id: str`
  - `currency: str`
  - `balance: Decimal`
  - `equity: Decimal`
  - `free_margin: Decimal`
  - `margin_level_pct: Optional[float]` *(Finite float)*
  - `leverage: float` (>= 1.0, Finite float)
  - `is_live: bool`
  - `timestamp_utc: datetime`

#### C. Market Data & Decision/Execution Models
- **`Bar`:**
  - `symbol: str`
  - `timeframe: BarTimeframe`
  - `event_start_utc: datetime`
  - `event_end_utc: datetime` (Invariant: `event_end_utc >= event_start_utc`)
  - `knowledge_time_utc: datetime` (Invariant: `knowledge_time_utc >= event_end_utc`)
  - `open: Decimal`, `high: Decimal`, `low: Decimal`, `close: Decimal` (> 0)
  - `volume: Decimal` (>= 0)
  - `provenance_hash: Optional[str]`
  - Invariants: `high >= max(open, close)` and `low <= min(open, close)`
- **`MarketDataSnapshot`:**
  - `symbol: str`
  - `bid: Decimal` (> 0), `ask: Decimal` (> 0) *(Invariant: `ask >= bid`)*
  - `bid_size: Decimal` (>= 0), `ask_size: Decimal` (>= 0)
  - `last_price: Decimal` (> 0)
  - `timestamp_utc: datetime`
- **`Signal`:**
  - `strategy_id: str`
  - `symbol: str`
  - `direction: float` (Finite float, $[-1.0, 1.0]$)
  - `expected_return: float` (Finite float)
  - `uncertainty: float` (Finite float, $[0.0, 1.0]$)
  - `horizon_seconds: int` (> 0)
  - `timestamp_utc: datetime`
- **`TargetAllocation`:**
  - `weights: Mapping[str, float]` *(Defensively copied, immutable mapping, finite floats)*
  - `cash_weight: float` (Finite float)
  - `rationale: str`
  - `timestamp_utc: datetime`
  - *Semantic Boundary:* Phase 1 domain model does NOT enforce $\sum \text{weights} + \text{cash\_weight} = 1.0$. Portfolio feasibility, leverage, and gross/net limits remain the responsibility of future Portfolio and Risk Engines.
- **`RiskAssessment`:**
  - `approved: bool`
  - `adjusted_weights: Mapping[str, float]` *(Defensively copied, immutable mapping, finite floats)*
  - `rejection_reason: Optional[str]`
  - `max_drawdown_pct: float` (Finite float)
  - `risk_utilization_pct: float` (Finite float)
  - `timestamp_utc: datetime`
- **`Order`:**
  - `order_id: str`
  - `symbol: str`
  - `order_type: OrderType`
  - `side: OrderSide`
  - `quantity: Decimal` (> 0)
  - `price_limit: Optional[Decimal]`
  - `status: OrderStatus` = `OrderStatus.PENDING`
  - `idempotency_key: str`
  - `correlation_id: str`
  - `created_at_utc: datetime`
- **`Fill`:**
  - `fill_id: str`
  - `order_id: str`
  - `symbol: str`
  - `side: OrderSide`
  - `fill_price: Decimal` (> 0)
  - `fill_quantity: Decimal` (> 0)
  - `fee: Decimal` (>= 0)
  - `slippage: Decimal` *(Absolute price difference in price units: $|\text{fill\_price} - \text{reference\_price}|$; execution quality reporting only)*
  - `correlation_id: str`
  - `timestamp_utc: datetime`

#### D. Cross-Cutting Audit Lineage Model
- **`DecisionRecord`:**
  - `decision_id: str`
  - `timestamp_utc: datetime`
  - `inputs_snapshot_ref: str`
  - `signal_ref: Optional[str]`
  - `target_allocation: Optional[TargetAllocation]`
  - `risk_assessment: Optional[RiskAssessment]`
  - `correlation_id: str`
  - `schema_version: str` = "1.0.0"
  - *Rule:* `DecisionRecord` is strictly append-only and immutable. Historical records are NEVER mutated to attach downstream fills or PnL; correlation is maintained via `correlation_id`.

---

## 4. Phase 1 Spot-Like Accounting & State Transitions

### 4.1 Fill Cash Flow Semantics & Zero Double-Counting
In the Phase 1 spot-like valuation model, cash is directly exchanged for assets:
- **BUY Fill:**
  $$\text{cash\_balance}_{\text{new}} = \text{cash\_balance}_{\text{old}} - (\text{fill\_price} \times \text{fill\_quantity}) - \text{fee}$$
- **SELL Fill:**
  $$\text{cash\_balance}_{\text{new}} = \text{cash\_balance}_{\text{old}} + (\text{fill\_price} \times \text{fill\_quantity}) - \text{fee}$$
- **Zero Realized PnL Double-Counting:**
  When a position is reduced or closed, the realized profit or loss is naturally embedded in the cash balance via the cash received from the sale vs cash paid at entry.
  *Example:*
  - Initial: Cash = 900, Position = +1 @ 100.
  - SELL 1 @ 110 (Fee = 0): Cash increases by 110 to 1010. Realized PnL is +10 (reporting value).
  - Cash is **1010**, NOT $1010 + 10 = 1020$ ❌.
  - Equity is $\text{Cash} + \text{Market Value} = 1010 + 0 = 1010$.
  - **`realized_pnl` is strictly a reporting metric and is NEVER added to cash or equity a second time.**

### 4.2 Portfolio Equity Source of Truth
$$\text{PortfolioState.total\_equity} = \text{cash\_balance} + \sum_{i} \text{Position}_i.\text{market\_value}$$
where for Phase 1 spot valuation:
$$\text{Position.market\_value} = \text{signed quantity} \times \text{current\_price}$$

- **Unrealized PnL (Reporting Metric):**
  $$\text{PortfolioState.unrealized\_pnl} = \sum_{i} \text{Position}_i.\text{unrealized\_pnl}$$
  where $\text{Position.unrealized\_pnl} = \text{signed quantity} \times (\text{current\_price} - \text{entry\_price})$.

### 4.3 Position Transition Semantics (Signed Quantity Math)
1. **Long Increase (Long + BUY):**
   - $\text{new\_qty} = \text{old\_qty} + \text{fill\_qty}$
   - $\text{new\_entry\_price} = \frac{(\text{old\_qty} \times \text{old\_entry}) + (\text{fill\_qty} \times \text{fill\_price})}{\text{new\_qty}}$
   - Realized PnL: Unchanged.
2. **Long Reduce (Long + SELL, $\text{fill\_qty} < \text{old\_qty}$):**
   - $\text{new\_qty} = \text{old\_qty} - \text{fill\_qty}$
   - $\text{entry\_price}$: Unchanged.
   - $\Delta \text{realized\_pnl} = \text{fill\_qty} \times (\text{fill\_price} - \text{old\_entry})$.
3. **Long Close (Long + SELL, $\text{fill\_qty} = \text{old\_qty}$):**
   - $\text{new\_qty} = 0$, $\text{entry\_price} = 0$.
   - $\Delta \text{realized\_pnl} = \text{fill\_qty} \times (\text{fill\_price} - \text{old\_entry})$.
4. **Long $\to$ Short Reversal (Long + SELL, $\text{fill\_qty} > \text{old\_qty}$):**
   - Closed portion: $\text{old\_qty}$ $\implies \Delta \text{realized\_pnl} = \text{old\_qty} \times (\text{fill\_price} - \text{old\_entry})$.
   - Residual portion: $\text{new\_qty} = -(\text{fill\_qty} - \text{old\_qty})$, $\text{new\_entry\_price} = \text{fill\_price}$.
5. **Short Increase (Short + SELL):**
   - $\text{new\_qty} = \text{old\_qty} - \text{fill\_qty}$ (more negative)
   - $\text{new\_entry\_price} = \frac{(|\text{old\_qty}| \times \text{old\_entry}) + (\text{fill\_qty} \times \text{fill\_price})}{|\text{new\_qty}|}$
   - Realized PnL: Unchanged.
6. **Short Reduce (Short + BUY, $\text{fill\_qty} < |\text{old\_qty}|$):**
   - $\text{new\_qty} = \text{old\_qty} + \text{fill\_qty}$ (less negative)
   - $\text{entry\_price}$: Unchanged.
   - $\Delta \text{realized\_pnl} = \text{fill\_qty} \times (\text{old\_entry} - \text{fill\_price})$.
7. **Short Close (Short + BUY, $\text{fill\_qty} = |\text{old\_qty}|$):**
   - $\text{new\_qty} = 0$, $\text{entry\_price} = 0$.
   - $\Delta \text{realized\_pnl} = \text{fill\_qty} \times (\text{old\_entry} - \text{fill\_price})$.
8. **Short $\to$ Long Reversal (Short + BUY, $\text{fill\_qty} > |\text{old\_qty}|$):**
   - Closed portion: $|\text{old\_qty}|$ $\implies \Delta \text{realized\_pnl} = |\text{old\_qty}| \times (\text{old\_entry} - \text{fill\_price})$.
   - Residual portion: $\text{new\_qty} = \text{fill\_qty} - |\text{old\_qty}|$, $\text{new\_entry\_price} = \text{fill\_price}$.

### 4.4 Pure State Transition Signatures
- `apply_fill_to_position(current_position: Optional[Position], fill: Fill) -> Position`
- `apply_fill_to_portfolio(portfolio: PortfolioState, fill: Fill) -> PortfolioState`
- `update_portfolio_market_prices(portfolio: PortfolioState, prices: Mapping[str, Decimal], timestamp: datetime) -> PortfolioState`

---

## 5. Configuration & Error Boundaries (`acash.core.config`)

- **Malformed YAML Syntax:** Handled at YAML parser stage $\implies$ raises `ConfigParseError` (wrapping `yaml.YAMLError`).
- **Valid YAML with Invalid Schema/Types:** Handled at Pydantic model validation stage $\implies$ raises `pydantic.ValidationError`.

---

## 6. Abstract Interface Contracts (`acash.core.interfaces`)

- `IMarketDataProvider`: Point-in-time historical bar retrieval and live snapshot stream contract (Phase 1 operates with zero network connectivity; `MockMarketDataProvider` only).
- `IFeatureEngine`: Point-in-time feature extraction with temporal anti-leakage verification.
- `IStrategy`: Hypothesis-driven signal generation contract.
- `IPortfolioOptimizer`: Target allocation calculation contract.
- `IRiskEngine`: Deterministic hard risk evaluator contract (interface definition only).
- `IBacktestEngine`: Simulation engine abstraction.
- `IExecutionEngine`: Order routing, state reconciliation, and adapter management contract.
- `IDecisionLedger`: **Append-only** audit logger and research memory store interface (`append_decision`, `query_decisions`, `reconstruct_lifecycle`).

---

## 7. Phase 1 Testing Philosophy & Acceptance Criteria

### 7.1 Required Acceptance Criteria (Gate 1 Checklist)
1. [ ] **Unit Tests Pass:** All unit test suites execute cleanly via `pytest`.
2. [ ] **Spot-Like Accounting & Cash Flow Integrity Tested:**
   - Opening a long position (cash reduces, market value increases, equity conserved net of fees).
   - Increasing a position (weighted-average entry price updated, cash reduced).
   - Reducing a position (cash increases by sales proceeds, realized PnL captured in cash, equity conserved).
   - Closing a position (position becomes flat, cash updated, realized PnL retained for reporting).
   - Price appreciation (equity increases via market value, cash unchanged, unrealized PnL updated).
   - Price depreciation (equity decreases via market value, cash unchanged, unrealized PnL updated).
   - Fee deduction (fees properly deducted from cash and reflected in equity).
   - Equity conservation: $\text{total\_equity} = \text{cash\_balance} + \sum \text{Position.market\_value}$.
3. [ ] **Realized PnL Double-Counting Prevention Tested:**
   - Long trade: Buy 1 @ 100, Sell 1 @ 110 $\implies$ cash = 1010, `realized_pnl = +10`, equity = 1010 (not 1020).
   - Short trade: Sell 1 @ 100, Buy 1 @ 90 $\implies$ cash proceeds/payments reflect +10 gain, `realized_pnl = +10`, equity correctly conserved.
4. [ ] **Position Transition Semantics Tested:**
   - 8 transition scenarios (Long Increase, Long Reduce, Long Close, Long $\to$ Short Reversal, Short Increase, Short Reduce, Short Close, Short $\to$ Long Reversal) produce exact mathematical signed quantities, entry prices, and realized PnL.
5. [ ] **Slippage Units & Reporting Tested:**
   - `Fill.slippage` represents absolute price difference in price units and is NOT double-deducted from cash.
6. [ ] **TargetAllocation Semantic Boundary Tested:**
   - Validates finite floats only; does NOT reject allocations where sum of weights != 1.0.
7. [ ] **Order Lifecycle Tested:** `Order` contains `status: OrderStatus = OrderStatus.PENDING` and validates lifecycle states.
8. [ ] **Immutable Mappings Tested:**
   - Mutating input mappings after instantiation does not mutate domain objects.
   - In-place mutation of domain mappings is rejected (raises `TypeError`).
   - Serialization and deserialization round-trip correctly reconstructs immutable mappings.
9. [ ] **Finite Values & Invariants Tested:**
   - Prices, quantities, cash, equity, exposures, fees, and PnL use `Decimal` and reject `NaN`/`Infinity`.
   - All float fields strictly reject `NaN`, `+Infinity`, and `-Infinity`.
   - Candlestick geometry invariants verified: $\text{High} \ge \max(\text{Open}, \text{Close})$, $\text{Low} \le \min(\text{Open}, \text{Close})$, $\text{Price} > 0$.
10. [ ] **State Transition Integrity Tested:**
    - `apply_fill_to_position`, `apply_fill_to_portfolio`, and `update_portfolio_market_prices` return fresh snapshot instances without mutating prior state.
    - Zero `apply_portfolio_to_account` functions exist.
11. [ ] **Error Boundaries Tested Separately:**
    - Malformed YAML raises `ConfigParseError`.
    - Valid YAML with invalid schema raises `pydantic.ValidationError`.
12. [ ] **Interface Contracts Tested:**
    - Abstract base classes cannot be instantiated directly; implementations satisfy type signatures.
13. [ ] **Serialization & Deserialization Tested:**
    - Domain models serialize to and deserialize from JSON/dict without data truncation or precision loss.
14. [ ] **Append-Only Decision Ledger Contract Tested:**
    - Decision ledger enforces immutable inserts, rejects updates/deletions, and permits full audit reconstruction without retroactively mutating records.
15. [ ] **Deterministic Mock Behavior Tested:**
    - `MockExecutionEngine`, `MockMarketDataProvider` (Zero Network), and `InMemoryDecisionLedger` produce **deterministic equivalent outcomes for identical inputs, configuration, and execution environment**.
16. [ ] **Static Typing Verified:**
    - `mypy` completes with **zero type errors** across `acash.core`, `acash.execution`, `acash.data`, `acash.storage`, and `acash.telemetry`.
