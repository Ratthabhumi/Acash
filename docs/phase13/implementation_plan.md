# ACASH Implementation Plan — Paper Trading Runtime Architecture (Rev 2.1)
# Formal Specification & Verification Contract

> **Document ID:** `docs/phase13/implementation_plan.md`  
> **Version:** 2.1.0 (Audited Implementation Specification Edition)  
> **Date:** 2026-09-05  
> **Governing Baseline:** `docs/phase13/paper_trading_readiness_audit.md` (Rev 2, Commit `284c36e`)  
> **Status:** PLAN REVISION ONLY — STRICT IMPLEMENTATION HALT  
> **Authority State:** `LOCKED — AWAITING EXPLICIT HUMAN PLAN APPROVAL`

---

## 1. Status / Governance Boundary

This document establishes the formal, non-negotiable **Implementation Contract Rev 2.1** for the ACASH continuous 3-month Paper Trading Runtime on the Windows development host. It incorporates all resolutions from the Human Auditor Plan Review.

### 1.1 Non-Negotiable Governance Invariants
- **Phase 13 Gate A:** `CERTIFIED` (Formal Human Sign-off 2026-09-04; MT5 Demo flat).
- **Phase 13 Gate B (Rev 10 Step 2):** `CONDITIONAL PASS` (B1–B22 PASS, B23.1 PASS, B23.2 NOT PROVEN / DEFERRED).
- **Assertion B23.2:** `NOT PROVEN / DEFERRED` to future dedicated cloud/VM infrastructure.
- **Step 3 Ceremony / Step 4 Activation / Slice 3:** `STRICTLY BLOCKED / LOCKED`.
- **Live Capital Authority:** `$0.00` | **Live Orders:** `0` | **Live Broker Connection:** `DISCONNECTED`.
- **Execution Authority:** This directive authorizes **ONLY the revision of this implementation plan specification**. It strictly forbids creating or modifying runtime source code, modifying tests, modifying frozen core contracts, or connecting to live broker environments.

---

## 2. Scope

The implementation scope of this contract is bounded strictly to **4 new runtime files and 1 unit test file**:

```text
src/acash/runtime/
├── paper_bridge.py        # Seam connecting Stage 5 allocation to OrderIntent & execution
├── feeder.py              # Forward market-data feed pump & freshness evaluator
├── rehydration.py         # Crash/restart state recovery & broker reconciliation
└── strategy_adapter.py    # Read/verify adapter binding strategy to session identity

tests/unit/runtime/
└── test_paper_bridge.py   # 20-vector adversarial unit & recovery test suite
```

Zero additional runtime files may be added.

---

## 3. Non-Goals (Explicitly Out-of-Scope)

1. **NO Live Trading or Capital Deployment:** Zero live orders; live capital remains strictly `$0.00`.
2. **NO Synthetic Dossiers:** Zero artificial `AlphaQualificationDossier` or `baseline_momentum_dossier.json` creation.
3. **NO Scope Expansion to Future Phases:** Phases 14, 17, 18, 19, 20, 21, 22, and 23 (Microstructure implementation) remain strictly frozen.
4. **NO Crypto Execution Implementation:** Weekend Crypto execution is an architectural concept only; zero crypto exchange APIs, zero credentials, zero network sockets, and zero crypto code in Rev 2.1.
5. **NO Modification of Frozen Core Contracts:** Phases 1–12 domain models, state machines, risk gates, and reconciliation engines remain 100% untouched.

---

## 4. Architecture Overview

The Paper Trading Runtime operates as an unattended, forward-evaluating daemon executing the canonical ACASH 5-stage cycle:

```text
                     FORWARD MARKET DATA FEEDER
              (MT5 Live Ticks or Streaming Parquet Pump)
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      CONTINUOUS PAPER DAEMON                           │
│                                                                        │
│   STAGE 1: Freshness Check (data_age_ms <= max_market_data_age_ms)    │
│   STAGE 2: Strategy Census (Read/Verify RESEARCH_QUALIFIED Dossier)   │
│   STAGE 3: Allocation Tournament (AllocationTournamentRunner)          │
│   STAGE 4: Sovereign Risk Gate (DeterministicRiskEngine + Kill Switch) │
│   STAGE 5: Execution Admission Verification                            │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │ Admitted AllocationDecision
                                 ▼
                     PAPER EXECUTION BRIDGE
         (Mechanical Delta Translation: Delta q = Target - Current)
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       PRIMARY EXECUTION VENUE         DETERMINISTIC TEST DOUBLE
         [MT5 Demo Account]           [Simulated Market Matcher]
    ├── Real Broker Execution         ├── 100% Offline / Deterministic
    ├── Terminal 6-D Reconciliation   ├── Explicit ExecutionCostModel
    └── Live Spread & Broker Fills    └── Unit & Soak Test Double
                 │                               │
                 └───────────────┬───────────────┘
                                 │ BrokerRawEvent
                                 ▼
                     EXECUTION COORDINATOR
           (transition_order() Sole State Authority)
                                 │
                                 ▼
                 FORENSIC PERSISTENCE & MONITORING
                 ├── OperationalLedger (Append-Only JSONL + SHA-256)
                 ├── MonitoringEvidenceLedger (Drift & Drag Evidence)
                 └── ExecutionManifest (Per-Order Forensic Lineage)
```

---

## 5. Component 1 — `paper_bridge.py`

### 5.1 Purpose & Authority Boundaries
`PaperExecutionBridge` serves exclusively as a mechanical translation and dispatch seam. It receives an admitted `AllocationDecision` from Stage 5, translates target weights into discrete unit share/lot deltas ($\Delta q_i$), verifies structural completeness, constructs canonical `OrderIntent` objects, dispatches them to the selected venue, and routes resulting `BrokerRawEvent` observations to the `ExecutionCoordinator`.

### 5.2 Strict Risk and Allocation Authority Chain
`PaperExecutionBridge` MUST NOT become a secondary risk engine. Sizing, risk budgeting, and governance authority are decoupled across strict boundaries:

```text
Existing Stage 5 / Canonical Allocation Authority
                    ↓
        validated AllocationDecision
                    ↓
            PaperExecutionBridge
                    ↓
      mechanical target-delta translation
                    ↓
               OrderIntent
                    ↓
             Execution Venue
```

#### Authority Table
| Functional Domain | Authoritative Component | Governed Contract |
|---|---|---|
| **Allocation Authority** | Stage 3 (`AllocationTournamentRunner`) | `src/acash/allocation/tournament.py` |
| **Position-Sizing Authority** | Stage 3 (`AllocationTournamentRunner`) | Canonical sizing rules based on capital and volatility |
| **Exposure Authority** | Stage 4 (`DeterministicRiskEngine` + Kill Switch) | Phase 9 Risk Bounds (`MaxGrossExposure`, `MaxNetExposure`) |
| **Min-Lot Authority** | Venue / Account Specification | `BrokerSymbolSpec.min_volume` (`src/acash/execution/mt5/adapter.py`) |
| **Venue Constraint Authority** | Venue Adapter & Account Limits | `BrokerSymbolSpec.volume_step`, `margin_initial` |

#### Permitted Actions for `PaperExecutionBridge`:
- Translate target weight vector $w^*$ into discrete share/contract delta: $\Delta q_i = q_{\text{target}, i} - q_{\text{current}, i}$.
- Validate structural completeness and schema correctness of `AllocationDecision`.
- Suppress mathematically zero/no-op deltas ($\|\Delta q_i\| < \text{min\_lot\_size} \implies \text{no dispatch}$).
- Construct and dispatch canonical `OrderIntent` DTOs.
- Forward raw broker events (`BrokerRawEvent`) into `ExecutionCoordinator`.

#### Strictly Prohibited Actions for `PaperExecutionBridge`:
- Inventing secondary portfolio risk rules or stop-loss mechanisms.
- Inventing secondary allocation or capital policies.
- Inventing secondary leverage, gross exposure, or net exposure caps.
- Computing secondary volatility models or beta estimations.
- Modifying strategy decision weights or generating autonomous trading signals.

### 5.3 Allowed Classes & Functions
```python
class PaperExecutionVenueType(str, Enum):
    MT5_DEMO = "MT5_DEMO"
    LOCAL_SIMULATOR = "LOCAL_SIMULATOR"

class PaperExecutionBridge:
    def __init__(
        self,
        coordinator: ExecutionCoordinator,
        venue_type: PaperExecutionVenueType,
        mt5_adapter: Optional[MT5BrokerAdapter] = None,
        matcher: Optional[SimulatedMarketMatcher] = None,
        symbol_spec_provider: Optional[Callable[[str], BrokerSymbolSpec]] = None,
    ) -> None: ...

    def evaluate_and_dispatch(
        self,
        allocation: AllocationDecision,
        portfolio: PortfolioState,
        current_snapshot: MarketDataSnapshot,
        cycle_identity: CycleIdentity,
        session_identity: PaperTradingSessionIdentity,
    ) -> Sequence[CoordinatorOutcome]: ...

    def _calculate_target_delta(
        self,
        target_allocation: AllocationDecision,
        current_portfolio: PortfolioState,
        symbol_spec: BrokerSymbolSpec,
    ) -> Decimal: ...
```

### 5.4 Local Simulator Seam & Deterministic Matcher
- `SimulatedMarketMatcher` is an offline test double that consumes an explicit `ExecutionCostModel` (Section 13).
- Emits canonical `BrokerRawEvent` sequences (`ACK` $\to$ `FILLED` or `REJECTED`).
- Operates purely in-memory with zero network connectivity.

---

## 6. Component 2 — `feeder.py`

### 6.1 Purpose & Market-Data Lifecycle
`ForwardMarketDataFeeder` supplies tick and bar snapshots to the runtime daemon, computing precise millisecond latency (`data_age_ms`) for Stage 1 evaluation.

### 6.2 Strict Separation: Forward Feed vs. Historical Parquet Pump
Production-like paper trading and offline test harnesses are fundamentally different operational modes:

| Operational Dimension | Production-Like Forward Paper Run | Deterministic Offline Test Double |
|---|---|---|
| **Data Source (`data_source`)** | `MT5_FORWARD` | `STREAMING_PARQUET_PUMP` |
| **Execution Mode (`execution_mode`)** | `MT5_DEMO_VENUE` | `LOCAL_SIMULATOR` |
| **Physical Venue (`venue`)** | `METAQUOTES_MT5_DEMO` | `IN_MEMORY_SIMULATOR` |
| **Classification** | **FORWARD_PAPER_RUN** | **OFFLINE_SIMULATION_HARNESS** |
| **Time Semantics** | Wall-clock progression (UTC) | Synthetic event-stepped timestamps |
| **90-Day Qualification** | **ELIGIBLE** (Satisfies forward requirement) | **INELIGIBLE** (Strictly test double) |

> [!CRITICAL]
> `STREAMING_PARQUET_PUMP` is NOT real-time market data. It MUST NOT qualify a session as the 90-day forward paper run. The runtime supervisor MUST abort startup if a session claims `FORWARD_PAPER_RUN` classification while configured with `STREAMING_PARQUET_PUMP`.

#### Permitted vs. Forbidden Combinations
- **Allowed A (Production-Like Paper):** `data_source = MT5_FORWARD` + `execution_mode = MT5_DEMO_VENUE`.
- **Allowed B (Deterministic Offline Simulation):** `data_source = STREAMING_PARQUET_PUMP` + `execution_mode = LOCAL_SIMULATOR`.
- **Allowed C (Forward Dry-Run / Staging Double):** `data_source = MT5_FORWARD` + `execution_mode = LOCAL_SIMULATOR`.
- **Strictly Forbidden D:** `data_source = STREAMING_PARQUET_PUMP` + `execution_mode = MT5_DEMO_VENUE` $\implies$ Raises `DataContractError` immediately.

### 6.3 Allowed Classes & Functions
```python
class FeedSourceType(str, Enum):
    MT5_FORWARD = "MT5_FORWARD"
    STREAMING_PARQUET_PUMP = "STREAMING_PARQUET_PUMP"

class MarketFeedStatus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    is_connected: bool
    last_tick_utc: datetime
    data_age_ms: int
    feed_source: FeedSourceType

class ForwardMarketDataFeeder:
    def __init__(
        self,
        provider: IMarketDataProvider,
        source_type: FeedSourceType,
        mt5_transport: Optional[NativeMT5Transport] = None,
        historical_iterator: Optional[Iterator[Bar]] = None,
        max_market_data_age_ms: int = 1500,
    ) -> None: ...

    def poll_next_market_snapshot(
        self,
        symbol: str,
        wall_clock_utc: datetime,
    ) -> Tuple[MarketDataSnapshot, int]: ...
```

### 6.4 Stale-Data Fail-Closed Invariants
- Point-in-time calculation: $\text{data\_age\_ms} = \max\left(0, \text{int}\left((t_{\text{wall\_clock\_utc}} - t_{\text{tick\_utc}}).\text{total\_seconds}() \times 1000\right)\right)$.
- If $\text{data\_age\_ms} > \text{max\_market\_data\_age\_ms}$ ($1500\text{ms}$):
  - In MT5 Forward mode: Marks snapshot as stale; Stage 1 halts the pulse, emits `CycleOutcome.DATA_STALE`, and suppresses all order dispatch.
  - In Offline Parquet mode: `data_age_ms` is fixed to $0$ by construction.

---

## 7. Component 3 — `rehydration.py`

### 7.1 Authoritative Recovery Source & Field Classification
`PortfolioStateRehydrator` recovers portfolio and account state upon daemon startup or crash restart. Rather than making unsupported assumptions about `OperationalCycleEvent` (which stores a cryptographic hash `portfolio_state_digest` rather than raw position mappings), recovery sources are strictly schema-grounded:

#### Authoritative Recovery Source:
- **MT5 Demo Mode:** Live Broker Terminal via `MT5BrokerAdapter` (`get_open_positions()`, `AccountInfo`) + Latest committed `portfolio_state.json` snapshot verified against `OperationalLedger.verify_ledger_integrity()`.
- **Local Simulator Mode:** On-disk `portfolio_state.json` snapshot bound to `OperationalCycleEvent.portfolio_state_digest`.

#### Field Classification Matrix:
| Field | Classification | Derivation / Verification Method | Mismatch Policy |
|---|---|---|---|
| `cash_balance` | **Broker Authoritative** (MT5) / **Snapshot Authoritative** (Local) | Queried from `AccountInfo.balance` (MT5) or deserialized from snapshot JSON (Local) | `HALT` if snapshot digest $\neq$ `portfolio_state_digest` |
| `positions` | **Broker Authoritative** (MT5) / **Snapshot Authoritative** (Local) | Queried from `get_open_positions()` (MT5) or deserialized from snapshot JSON (Local) | `HALT` if live broker position $\neq$ local snapshot |
| `realized_pnl` | **Broker Authoritative** (MT5) / **Snapshot Authoritative** (Local) | Sum of terminal closed deals from broker deal history / snapshot | `HALT` on corruption |
| `unrealized_pnl` | **Deterministically Derived** | Calculated as $\sum q_i \cdot (\text{mark\_price}_i - \text{entry\_price}_i)$ using exact `Decimal` arithmetic | `HALT` on arithmetic discrepancy |
| `total_equity` | **Broker Authoritative** (MT5) / **Deterministically Derived** (Local) | Queried from `AccountInfo.equity` (MT5) or computed as $\text{cash} + \text{unrealized}$ | `HALT` if accounting identity $\text{equity} \equiv \text{cash} + \text{unrealized}$ violated |
| `gross_exposure`| **Deterministically Derived** | $\sum \|q_i \cdot \text{mark\_price}_i\|$ derived via canonical `PortfolioState` validator | `HALT` on validation failure |
| `net_exposure`  | **Deterministically Derived** | $\sum q_i \cdot \text{mark\_price}_i$ derived via canonical `PortfolioState` validator | `HALT` on validation failure |

#### Mismatch Policy:
$$\text{Live Broker State} \neq \text{Snapshot State} \implies \mathbf{DISCREPANCY\_HALT}$$
The runtime immediately halts execution, logs a forensic incident, and refuses to process trading cycles until human reconciliation is completed.

### 7.2 Allowed Classes & Functions
```python
class RehydrationStatus(str, Enum):
    CLEAN_RECOVERY = "CLEAN_RECOVERY"
    DISCREPANCY_HALT = "DISCREPANCY_HALT"
    EMPTY_GENESIS = "EMPTY_GENESIS"

class PortfolioStateRehydrator:
    def __init__(
        self,
        ledger: OperationalLedger,
        snapshot_dir: Path,
        broker_adapter: Optional[BrokerAdapter] = None,
    ) -> None: ...

    def rehydrate(
        self,
        as_of_utc: datetime,
    ) -> Tuple[PortfolioState, AccountState, RehydrationStatus]: ...

    def _verify_snapshot_hash(
        self,
        snapshot: PortfolioState,
        expected_digest: str,
    ) -> bool: ...
```

---

## 8. Component 4 — `strategy_adapter.py`

### 8.1 Read/Verify Strategy Lifecycle Authority
- **Read/Verify Only:** `PaperStrategyAdapter` possesses strictly zero authority to promote, alter, or transition a strategy's lifecycle state.
- **Canonical Lifecycle Authority:** Sits exclusively in `src/acash/research/qualification.py` (`AlphaQualificationGate`).
- State transitions (`RESEARCH_QUALIFIED` $\to$ `FORWARD_PAPER_MONITORED`) may occur ONLY through the existing Phase 8.5 / Phase 17 canonical authority.
- If an authentic `AlphaQualificationDossier` is not present on disk:
  - `is_eligible = False`
  - Strategy weight is forced to `0.0`.
  - System executes governed 100% Cash fallback (`GOVERNANCE_FALLBACK`).
  - Zero synthetic or mock dossiers are permitted.

### 8.2 Candidate Strategy Status: BLOCKED
- **Strategy Identifier:** `STRAT-MOM-MULTI-HORIZON-V1` (`MultiHorizonMomentumStrategy`)
- **Status:** **`BLOCKED (QUALIFICATION PENDING)`**
- No `baseline_momentum_dossier.json` or equivalent synthetic artifact will be manufactured. The candidate strategy will only be traded after genuine qualification or under an explicit mock strategy test harness in unit testing.

### 8.3 Allowed Classes & Functions
```python
class PaperStrategyAdapter:
    def __init__(
        self,
        strategy_id: str,
        strategy_version: str,
        dossier_path: Optional[Path] = None,
        session_identity: Optional[PaperTradingSessionIdentity] = None,
    ) -> None: ...

    def verify_eligibility(self) -> bool: ...

    def generate_candidate_allocation(
        self,
        bars: Sequence[Bar],
        portfolio: PortfolioState,
        as_of_utc: datetime,
    ) -> AllocationDecision: ...
```

---

## 9. ExecutionManifest Schema Specification

Every executed paper order emits an immutable, cryptographically sealed `ExecutionManifest` matching the canonical Phase 7 schema:

### 9.1 Schema Definition
```python
class ExecutionManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Identifiers
    execution_id: str = Field(description="Unique deterministic execution identifier (EXEC-...).")
    paper_run_id: str = Field(description="Associated paper trading session identifier.")
    cycle_id: str = Field(description="Operational cycle identifier (CYCLE-...).")
    intent_id: str = Field(description="Originating OrderIntent identifier.")
    client_order_id: str = Field(description="Unique client order identifier sent to venue.")
    broker_order_id: Optional[str] = Field(default=None, description="Venue-assigned ticket/order identifier.")

    # Venue & Mode
    venue: str = Field(description="Execution venue identifier (METAQUOTES_MT5_DEMO, IN_MEMORY_SIMULATOR).")
    execution_mode: str = Field(description="MT5_DEMO_VENUE or LOCAL_SIMULATOR.")
    symbol: str = Field(description="Traded symbol (e.g. EURUSD).")
    order_side: str = Field(description="BUY or SELL.")
    order_type: str = Field(description="MARKET or LIMIT.")

    # Cryptographic Lineage & Digests
    input_digest: str = Field(description="SHA-256 digest of input OrderIntent and MarketDataSnapshot.")
    events_digest: str = Field(description="Canonical SHA-256 digest of observed BrokerRawEvent sequence.")
    execution_digest: str = Field(description="Canonical SHA-256 digest of complete serialized manifest.")

    # Timestamps (UTC)
    created_at: datetime = Field(description="Intent generation timestamp.")
    submitted_at: Optional[datetime] = Field(default=None, description="Venue dispatch timestamp.")
    acknowledged_at: Optional[datetime] = Field(default=None, description="Venue ACK timestamp.")
    closed_at: Optional[datetime] = Field(default=None, description="Terminal execution timestamp.")
    network_latency_ms: Optional[float] = Field(default=None, description="Round-trip network latency.")

    # Volumes & Prices (Decimal)
    requested_qty: Decimal = Field(description="Originally requested volume in lots/shares.")
    filled_qty: Decimal = Field(description="Cumulatively executed volume in lots/shares.")
    benchmark_mid_price: Decimal = Field(description="Arrival mid-price at dispatch time.")
    average_fill_price: Optional[Decimal] = Field(default=None, description="Volume-weighted average fill price.")
    realized_slippage_bps: Optional[Decimal] = Field(default=None, description="Realized execution slippage in bps.")
    total_commission_paid: Decimal = Field(default=Decimal("0.00"), description="Total commission incurred.")

    # Terminal State
    terminal_state: Optional[str] = Field(default=None, description="FILLED, REJECTED, CANCELLED, or null/UNKNOWN.")
```

### 9.2 Digest Rules & UNKNOWN Handling
- **Canonical Serialization:** All digests are computed using canonical JSON serialization (sorted keys, no extraneous whitespace, ISO-8601 UTC timestamps).
- **UNKNOWN Broker State:** If an order times out or broker status is pending, `terminal_state` MUST remain `null` or `"UNKNOWN"`.
- **Zero Invented Terminal States:** Under no circumstances will a timeout cause `terminal_state` to be populated with `"FILLED"` or `"CANCELLED"` without authoritative broker confirmation.

---

## 10. Paper Trading Session Identity Specification

Lineage metadata is strictly bound via `PaperTradingSessionIdentity`:

```python
class PaperTradingSessionIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    paper_run_id: str = Field(description="Unique deterministic session ID (e.g. PAPER-RUN-20260905-001).")
    strategy_id: str = Field(description="Canonical strategy identifier.")
    strategy_version: str = Field(description="Semantic version of strategy code.")
    start_time_utc: datetime = Field(description="Session initialization timestamp.")
    planned_end_time_utc: datetime = Field(description="Scheduled session end time (e.g. start + 90 days).")
    actual_end_time_utc: Optional[datetime] = Field(default=None, description="Recorded session termination time.")
    config_digest: str = Field(description="Canonical SHA-256 of RuntimePolicyConfig + ExecutionCostModel.")
    dossier_digest: str = Field(description="Canonical SHA-256 of AlphaQualificationDossier.")
    data_source: FeedSourceType = Field(description="MT5_FORWARD or STREAMING_PARQUET_PUMP.")
    execution_mode: PaperExecutionVenueType = Field(description="MT5_DEMO or LOCAL_SIMULATOR.")
```

---

## 11. Strategy Eligibility & Lifecycle Authority

```text
CANONICAL LIFECYCLE PATH:
HypothesisSpec ──► SearchTrialLedger ──► ValidationReport ──► AlphaQualificationGate ──► AlphaQualificationDossier
                                                                                                 │
                                                                                                 ▼
RuntimeSupervisor Stage 2 Census ◄── PaperStrategyAdapter (Read/Verify Only) ◄───────────────────┘
```

1. `PaperStrategyAdapter` loads the dossier from disk and verifies `dossier.dossier_digest == computed_hash`.
2. Verifies that `lifecycle_state in (AlphaLifecycleState.RESEARCH_QUALIFIED, AlphaLifecycleState.FORWARD_PAPER_MONITORED)`.
3. If unverified, corrupted, or missing $\implies$ `is_eligible = False`. Stage 2 logs census exclusion and allocates 100% Cash. Zero synthetic files are permitted.

---

## 12. Failure Semantics & Timeout Recovery

```text
DISPATCH TIMEOUT / NETWORK ERROR
               │
               ▼
      OrderState -> UNKNOWN
               │
               ▼
Authoritative 6-D Reconciliation (MT5AuthoritativeReconciler)
               │
       ┌───────┴───────┐
       ▼               ▼
[Terminal Confirmed]  [Unresolved Ambiguity]
(FILLED / CANCELLED)           │
       │                       ▼
Emits Terminal Manifest  DISCREPANCY_HALT & Operational Restriction
```

### Invariants:
- `TIMEOUT` transitions order strictly to `OrderState.UNKNOWN`.
- **Forbidden Assumptions:** `TIMEOUT \not\to FILLED`, `TIMEOUT \not\to REJECTED`, `TIMEOUT \not\to CANCELLED`.
- `PaperExecutionBridge` MUST NOT manufacture broker terminal events. `ExecutionCoordinator` is the sole state authority via `transition_order()`.

---

## 13. Execution Cost Model Specification

To eliminate arbitrary hard-coded numbers (magic constants) in the local simulator, all execution costs are explicitly modeled:

```text
ExecutionCostModel
    ├── SpreadModelConfig (base spread + volatility expansion)
    ├── SlippageModelConfig (fixed drag + random dispersion)
    └── CommissionModelConfig (round-turn commission per lot)
```

### 13.1 Schema & Parameter Provenance
```python
class SpreadModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    base_spread_pips: Decimal = Decimal("1.2")  # Typical EURUSD spread
    volatility_expansion_factor: Decimal = Decimal("1.0")

class SlippageModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    fixed_slippage_bps: Decimal = Decimal("0.20")
    random_slippage_std_bps: Decimal = Decimal("0.10")

class CommissionModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    commission_per_lot_usd: Decimal = Decimal("7.00")  # Standard institutional round-turn

class ExecutionCostModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    spread_model: SpreadModelConfig
    slippage_model: SlippageModelConfig
    commission_model: CommissionModelConfig
    provenance: str = Field(default="DETERMINISTIC_TEST_MODEL")
```

#### Parameter Provenance & Lineage Table:
| Parameter | Default Value | Authority Source | Ingested in `config_digest`? | Real-Market Representation |
|---|---|---|---|---|
| `base_spread_pips` | `1.2` | Deterministic Test Configuration | **YES** (Mandatory) | Local Simulator Estimate Only (MT5 uses live broker spread) |
| `volatility_expansion_factor`| `1.0` | Deterministic Test Configuration | **YES** (Mandatory) | Local Simulator Estimate Only |
| `fixed_slippage_bps` | `0.20` | Deterministic Test Configuration | **YES** (Mandatory) | Local Simulator Estimate Only (MT5 experiences broker slippage) |
| `random_slippage_std_bps` | `0.10` | Deterministic Test Configuration | **YES** (Mandatory) | Local Simulator Estimate Only |
| `commission_per_lot_usd` | `7.00` | Account Fee Specification | **YES** (Mandatory) | Local Simulator Estimate Only (MT5 uses account commission deal ledger) |

### 13.2 Rules:
1. Every execution-cost parameter MUST be explicit. No unexplained magic constants in simulation code.
2. All configurable execution-cost parameters MUST contribute directly to `session_identity.config_digest`.
3. Simulator results generated by `LOCAL_SIMULATOR` MUST be explicitly tagged as `LOCAL_SIMULATOR_ESTIMATE`. They must never be represented as empirical facts about MT5 broker execution.

---

## 14. Test Plan / 20-Vector Adversarial Matrix

The accompanying unit test suite (`tests/unit/runtime/test_paper_bridge.py`) implements exactly 20 planned adversarial vectors:

| Vector ID | Target Invariant | Scenario Description | Expected Fail-Closed Behavior |
|---|---|---|---|
| **V-01** | Zero Delta | Target allocation equals current position ($\Delta q \equiv 0$) | Emits 0 orders; dispatch suppressed cleanly. |
| **V-02** | Vetoed Allocation | Stage 4 risk engine returns `RiskVerdict.REJECTED` | Emits 0 orders; cycle outcome `RISK_REJECTED`. |
| **V-03** | Matcher Partial/Full Fill | Local matcher fills 50% / 100% of volume | Coordinator records fill; emits valid `ExecutionManifest`. |
| **V-04** | Rejected Order | Venue rejects order (e.g. invalid symbol/volume) | Coordinator transitions to `REJECTED`; incident logged. |
| **V-05** | Fresh Tick | Tick received with age 50ms | Stage 1 passes; `data_age_ms` recorded. |
| **V-06** | Stale Data | Tick received with age 2500ms (> 1500ms threshold) | Stage 1 halts pulse; emits `CycleOutcome.DATA_STALE`. |
| **V-07** | Clean Rehydration | Process restarts with valid ledger & snapshot | Rehydrates exact cash, positions, and equity. |
| **V-08** | Corrupted Ledger | Single byte mutated in `operational_ledger.jsonl` | Rehydration raises `DataContractError`; startup halted. |
| **V-09** | Broker Discrepancy | Live MT5 position differs from local snapshot | Rehydration emits `DISCREPANCY_HALT`; refuses cycles. |
| **V-10** | Session Identity Lineage | Verify complete session identity serialization | All fields present; `config_digest` validated. |
| **V-11** | Duplicate Intent | Re-submitting identical `intent_id` in same cycle | Deduplicated; zero duplicate broker orders dispatched. |
| **V-12** | Duplicate Client Order ID | Re-using `client_order_id` across cycles | Rejected by coordinator deduplication check. |
| **V-13** | Restart during UNKNOWN | Process killed while order in `UNKNOWN` state | Startup forces 6-D reconciliation before new cycles. |
| **V-14** | Restart after ACK before FILL | Process killed after ACK before fill event | Rehydrates pending status; awaits fill or queries broker. |
| **V-15** | Stale Feed with Open Position | Data feed drops while position is held | Rebalance halted; existing position held under stop. |
| **V-16** | Broker/Ledger Divergence | Deal occurs outside ACASH daemon control | Reconciler flags unexpected deal; triggers `DISCREPANCY_HALT`. |
| **V-17** | Session Identity Tampering | Changing session start time or run ID mid-flight | Startup validation detects tamper; halts daemon. |
| **V-18** | Dossier Digest Mismatch | Providing dossier with altered cryptographic hash | Stage 2 census rejects dossier as unverified. |
| **V-19** | Wrong Strategy Version | Strategy code version differs from session identity | Startup validation rejects mismatch; halts execution. |
| **V-20** | Wrong Config Digest | Changing slippage config without session re-creation | Startup validation rejects altered digest; halts execution. |

---

## 15. Pre-90-Day Progressive Validation Ladder

The 90-day continuous paper run clock MUST NOT start automatically upon code completion. It follows a strict 10-step ladder:

```text
[Step 1: Minimal Implementation] (4 runtime files + 1 test file only)
        ↓
[Step 2: Unit Tests] (20 adversarial vectors 100% PASS)
        ↓
[Step 3: Integration Tests] (Multi-pulse harness with MT5 Demo & Local Matcher)
        ↓
[Step 4: Restart & Recovery Tests] (Crash injection and rehydration audit)
        ↓
[Step 5: 24–72 Hour Unattended Soak Test] (Continuous execution on Dev Host)
        ↓
[Step 6: Soak Telemetry & Reconciliation Audit] (Zero memory leaks, zero unresolved incidents)
        ↓
[Step 7: Paper Run Readiness Review] (Formal audit package compilation)
        ↓
[Step 8: EXPLICIT HUMAN GO AUTHORIZATION] (Mandatory human checkpoint)
        ↓
[Step 9: 90-Day Continuous Paper Trading Operation] (Active forward tracking)
        ↓
[Step 10: 3-Month Formal Econometric & Reality Gap Review]
```

---

## 16. Weekday / Weekend Market Track Architecture (Future Roadmap Note)

> [!NOTE]
> **Architecture Concept Only — Strictly Non-Operational in Rev 2.1:**  
> The weekday MT5 Demo FX market closes on Saturday and Sunday. To enable continuous 24/7 validation without pausing execution loops, future architecture conceptually decouples market tracks:
>
> ```text
> ACASH Paper Runtime
>     ├── Weekday Track (Primary Phase 13 Validation)
>     │      └── MT5 Demo (FX / EURUSD)
>     │
>     └── Future Weekend Track (Exploratory / Deferred)
>            └── Crypto 24/7
>                  ├── Separate venue adapter
>                  ├── Separate strategy qualification
>                  ├── Separate execution model
>                  └── Separate metrics ledger
> ```
>
> **Strict Non-Operational Invariants:**
> 1. Crypto execution is **NOT IMPLEMENTED** in Rev 2.1 (0 code, 0 exchange APIs, 0 credentials, 0 network sockets).
> 2. Crypto MUST NOT be mixed into the 90-day MT5/EURUSD experiment.
> 3. Crypto performance MUST NOT be aggregated into the same experimental dataset.
> 4. Crypto requires completely independent `paper_run_id`, `strategy_id`, `strategy_version`, `market`, `venue`, `data_source`, `execution_mode`, `config_digest`, and `dossier_digest`.
> 5. Future Crypto Weekend Track requires its own independent strategy qualification.
> 6. Future Crypto execution cost model must be independently validated.
> 7. This note is **ARCHITECTURE ONLY** and represents zero implementation commitment in Phase 13.

---

## 17. File-Level Change Matrix

| Target File Path | Purpose | Allowed Classes & Functions | Consumed Contracts | Contracts NOT Allowed to Change | Test Coverage | Operational Risk | Rollback Impact |
|---|---|---|---|---|---|---|---|
| `src/acash/runtime/paper_bridge.py` | Order translation & dispatch seam | `PaperExecutionBridge`, `SimulatedMarketMatcher`, `PaperExecutionVenueType`, `ExecutionCostModel` | `AllocationDecision`, `OrderIntent`, `BrokerRawEvent`, `ExecutionCoordinator` | Zero secondary risk logic; zero sizing alterations; zero frozen core edits. | V-01, V-02, V-03, V-04, V-11, V-12, V-20 | Low (isolated translation layer) | Clean deletion; zero core regressions |
| `src/acash/runtime/feeder.py` | Market data feed pump & freshness | `ForwardMarketDataFeeder`, `MarketFeedStatus`, `FeedSourceType` | `IMarketDataProvider`, `Bar`, `MarketDataSnapshot`, `NativeMT5Transport` | Zero synthetic bar imputation; zero silent fallback on stale ticks. | V-05, V-06, V-15 | Low (read-only polling adapter) | Clean deletion; zero core regressions |
| `src/acash/runtime/rehydration.py` | Crash/restart recovery & reconciliation | `PortfolioStateRehydrator`, `RehydrationStatus`, `PortfolioSnapshotStore` | `OperationalLedger`, `OperationalCycleEvent`, `PortfolioState`, `MT5BrokerAdapter` | Zero position fabrication; zero recovery on broken ledger hash. | V-07, V-08, V-09, V-13, V-14, V-16 | Medium (state reconstruction) | Revert to clean empty genesis |
| `src/acash/runtime/strategy_adapter.py` | Read/verify strategy adapter | `PaperStrategyAdapter`, `PaperTradingSessionIdentity` | `MultiHorizonMomentumStrategy`, `AlphaQualificationDossier`, `AlphaLifecycleState` | Zero lifecycle promotion; zero synthetic dossier creation. | V-10, V-17, V-18, V-19 | Low (read/verify wrapper) | Clean deletion; strategy stays blocked |
| `tests/unit/runtime/test_paper_bridge.py` | Adversarial test suite | 20 test functions matching V-01 through V-20 | Pytest fixtures, mock adapters, temporary file fixtures | No skipped tests; no assertions claiming unverified behavior. | V-01 through V-20 | None (test suite only) | Deletion of test file |

---

## 18. Frozen-Core Protection

The ACASH core architecture (Phases 1–12) is formally **FROZEN**. The implementation of Rev 2.1 MUST NOT modify:
- `ExecutionCoordinator` state machine or transition semantics (`src/acash/execution/coordinator.py`).
- `transition_order()` sole state authority (`src/acash/execution/state_machine.py`).
- Phase 9 Sovereign Risk Engine contracts (`src/acash/risk/risk_engine.py`).
- Sovereign Kill Switch controller or persistence (`src/acash/risk/kill_switch.py`).
- Phase 12 MT5 Authoritative Reconciler (`src/acash/execution/mt5/reconciliation.py`).
- Phase 8.5 Alpha Qualification Gate contracts (`src/acash/research/qualification.py`).

If any implementation requirement appears to necessitate modifying frozen core files, work MUST halt immediately for architectural escalation (`BLOCKED / ESCALATION`).

---

## 19. Acceptance Criteria Checklist (Rev 2.1 Contract)

- [ ] Zero synthetic dossiers; candidate strategy remains explicitly marked `BLOCKED (QUALIFICATION PENDING)`.
- [ ] `PaperExecutionBridge` is strictly translation and dispatch; zero secondary risk logic.
- [ ] Risk and allocation ownership chain is unambiguous.
- [ ] `ExecutionCostModel` formally specified with spread, slippage, and commission components.
- [ ] Zero magic numbers; all simulator cost parameters contribute to `config_digest`.
- [ ] Rehydration authority schema-grounded; recovery fields classified with `DISCREPANCY_HALT`.
- [ ] Frozen `UNKNOWN` / `TIMEOUT` semantics preserved; zero fabricated terminal states.
- [ ] `MT5_FORWARD` data source strictly separated from offline `STREAMING_PARQUET_PUMP`.
- [ ] `PaperStrategyAdapter` is strictly read/verify; zero lifecycle promotion authority.
- [ ] Complete `ExecutionManifest` schema and digest rules specified.
- [ ] Complete `PaperTradingSessionIdentity` metadata specified (including planned and actual end timestamps).
- [ ] Adversarial test matrix expanded to 20 comprehensive failure vectors.
- [ ] Weekend Crypto Track isolated as a future architecture note (zero code in Rev 2.1).
- [ ] Pre-90-Day Progressive Validation Ladder established (including 24–72h soak test).
- [ ] Live capital remains strictly `$0.00`; live orders remain `0`.
- [ ] Zero frozen core modifications permitted.
- [ ] Zero runtime source implementation performed during plan revision.

---

## 20. Implementation Gate & Next Steps

This document is submitted for **Human Plan Review**.

```text
CURRENT GATE: IMPLEMENTATION PLANNING GATE
STATUS:       LOCKED — AWAITING EXPLICIT HUMAN PLAN APPROVAL
```

Execution of source code implementation remains strictly blocked until the Human Auditor responds with explicit authorization:
```text
APPROVED IMPLEMENTATION PLAN REV2.1
```
or
```text
GO IMPLEMENTATION
```

---

## 21. Explicit Non-Claims

1. Approval of this plan does NOT constitute approval to trade live capital.
2. Approval of this plan does NOT constitute an assertion that `MultiHorizonMomentumStrategy` has positive empirical alpha.
3. Passing unit tests on `test_paper_bridge.py` does NOT constitute completion of the 90-day paper trading validation.
4. Local simulator results under `SimulatedMarketMatcher` do NOT prove real-world MT5 execution quality.
