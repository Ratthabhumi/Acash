# ACASH Implementation Plan — Paper Trading Runtime Architecture (Rev 2.2)
# Formal Specification & Verification Contract
## Incorporating Auditor Review 2.2 Amendments & Weekend Track Architecture

> **Document ID:** `docs/phase13/implementation_plan.md`  
> **Version:** 2.2.1 (Audited Specification Edition — Partial Fill & Quantization Amendment)  
> **Date:** 2026-09-05 (Saturday)  
> **Governing Baseline:** `docs/phase13/paper_trading_readiness_audit.md` (Rev 2, Commit `284c36e`)  
> **Status:** PLAN REVISION ONLY — STRICT IMPLEMENTATION HALT  
> **Authority State:** `LOCKED — AWAITING EXPLICIT HUMAN PLAN APPROVAL`

---

## 1. Status / Governance Boundary

This document establishes the formal, non-negotiable **Implementation Contract Rev 2.2** for the ACASH continuous Paper Trading Runtime on the Windows development host. It incorporates all resolutions from the Human Auditor Rev 2.1 and Rev 2.2 reviews:
1. Formally specifies the **multi-stage partial-fill lifecycle** (`ACK` $\to$ `PARTIAL_FILL` $\to$ working residual $\to$ `FILLED`).
2. Formally specifies the **deterministic volume_step quantization pipeline** using `ROUND_DOWN`, residual drop, and minimum-lot boundary validation.
3. Unifies execution-cost parameter provenance strictly under **`DETERMINISTIC_TEST_CONFIGURATION`**.
4. Eliminates circular hash dependencies in `ExecutionManifest`.
5. Enforces single canonical schema ownership (`ExecutionManifest` consumed from Phase 7 core).
6. Preserves the **Weekend Paper Track Architecture Amendment** (`ARCHITECTURALLY DEFINED / NOT IMPLEMENTED / NOT OPERATIONAL`).

### 1.1 Non-Negotiable Governance Invariants
- **Phase 13 Gate A:** `CERTIFIED` (Formal Human Sign-off 2026-09-04; MT5 Demo flat).
- **Phase 13 Gate B (Rev 10 Step 2):** `CONDITIONAL PASS` (B1–B22 PASS, B23.1 PASS, B23.2 NOT PROVEN / DEFERRED).
- **Assertion B23.2:** `NOT PROVEN / DEFERRED` to future dedicated cloud/VM infrastructure.
- **Step 3 Ceremony / Step 4 Activation / Slice 3:** `STRICTLY BLOCKED / LOCKED`.
- **Live Capital Authority:** `$0.00` | **Live Orders:** `0` | **Live Broker Connection:** `DISCONNECTED`.
- **Execution Authority:** This directive authorizes **ONLY the revision of this implementation plan specification**. It strictly forbids creating or modifying runtime source code, modifying tests, modifying frozen core contracts, connecting to live brokers, or implementing crypto execution logic.

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
4. **NO Crypto Execution Implementation:** Weekend Crypto execution is an architectural concept only; zero crypto exchange APIs, zero exchange credentials, zero crypto broker implementation, zero crypto `OrderIntent` dispatch, and zero crypto network sockets in Rev 2.2.
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
    ├── Real Broker Execution         ├── 100% Offline / Seeded Deterministic
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
                 └── ExecutionManifest (Canonical Phase 7 Forensic Contract)
```

---

## 5. Component 1 — `paper_bridge.py`

### 5.1 Purpose & Authority Boundaries
`PaperExecutionBridge` serves exclusively as a mechanical translation and dispatch seam. It receives an admitted `AllocationDecision` from Stage 5, translates target weights into discrete unit share/lot deltas ($\Delta q_i$), verifies structural completeness, quantizes volume against venue step boundaries, constructs canonical `OrderIntent` objects, dispatches them to the selected venue, and routes resulting `BrokerRawEvent` observations to the `ExecutionCoordinator`.

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
     volume_step Quantization (ROUND_DOWN)
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
| **Venue Constraint Authority** | Venue Adapter & Account Limits | `BrokerSymbolSpec.volume_step`, `BrokerSymbolSpec.volume_max` |

#### 5.2.1 Canonical Volume Quantization Pipeline
To resolve Blocker 2 from the auditor review, the bridge enforces an explicit, deterministic quantization pipeline grounded in `src/acash/execution/mt5/normalizer.py:normalize_volume`:

```text
raw_delta (Δq = q_target - q_current)
          │
          ▼
Direction Determination:
  - If Δq > 0: OrderSide.BUY
  - If Δq < 0: OrderSide.SELL
  - If Δq == 0: ZERO DELTA -> Suppress Dispatch (0 orders emitted)
          │
          ▼
Magnitude Extraction: q_mag = |Δq|
          │
          ▼
volume_step Quantization (Policy: ROUND_DOWN / Floor towards zero):
  steps = floor(q_mag / symbol_spec.volume_step)
  quantized_lots = steps * symbol_spec.volume_step
  residual = q_mag - quantized_lots
          │
          ├──> Residual Handling: The fractional residual r < volume_step
          │    cannot be represented by the venue step grid. It is dropped
          │    and retained as unallocated cash portfolio balance.
          │
          ▼
Minimum-Volume Boundary Validation:
  - If quantized_lots < symbol_spec.min_volume:
      Suppress dispatch cleanly (no-op; 0 orders emitted; no broker error).
          │
          ▼
Maximum-Volume Boundary Validation:
  - If quantized_lots > symbol_spec.volume_max:
      Raise DataContractError (fail-closed venue constraint breach).
          │
          ▼
Exponent Normalization:
  quantized_lots = quantized_lots.quantize(symbol_spec.volume_step, rounding=ROUND_DOWN)
          │
          ▼
Construct Canonical OrderIntent(volume=quantized_lots, side=direction, ...)
```

#### Permitted Actions for `PaperExecutionBridge`:
- Translate target weight vector $w^*$ into discrete share/contract delta: $\Delta q_i = q_{\text{target}, i} - q_{\text{current}, i}$.
- Quantize magnitude using the canonical `ROUND_DOWN` pipeline.
- Suppress sub-minimum or zero deltas ($\Delta q_{\text{quantized}} < \text{min\_volume} \implies \text{no dispatch}$).
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

    def _quantize_target_delta(
        self,
        target_allocation: AllocationDecision,
        current_portfolio: PortfolioState,
        symbol_spec: BrokerSymbolSpec,
    ) -> Optional[Tuple[Decimal, OrderSide]]: ...
```

### 5.4 Local Simulator Seam & Deterministic Matcher (Partial-Fill Lifecycle)
To resolve Blocker 1 from the auditor review, `SimulatedMarketMatcher` implements explicit, canonical multi-stage fill semantics matching `src/acash/execution/state_machine.py`:

```text
[OrderIntent Received]
          │
          ▼
[BrokerEventKind.ACK] ──► Coordinator State: ACKNOWLEDGED
          │
          ├───► FULL_FILL_MODE:
          │       Emits BrokerEventKind.FILLED (filled_qty = requested_qty)
          │       Coordinator State: FILLED (Terminal)
          │       Emits canonical ExecutionManifest.
          │
          ├───► PARTIAL_FILL_MODE (Multi-Stage Lifecycle for V-03):
          │       Pulse 1: Emits BrokerEventKind.PARTIAL_FILL (filled_qty = requested_qty * 0.50)
          │                Coordinator State: PARTIALLY_FILLED
          │                Residual quantity (50%) remains active on simulated venue.
          │       Pulse 2: Emits BrokerEventKind.FILLED (filled_qty = requested_qty)
          │                Coordinator State: FILLED (Terminal)
          │                Emits canonical ExecutionManifest.
          │
          └───► REJECT_MODE:
                  Emits BrokerEventKind.REJECTED (or ACK -> REJECTED)
                  Coordinator State: REJECTED (Terminal)
```

- Uses an explicit PRNG seed (`prng_seed: int`) bound into `config_digest` to ensure 100% mathematical reproducibility across all unit and soak test runs.
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
| `realized_pnl` | **Broker Authoritative** (MT5) / **Snapshot Authoritative** (Local) | Sum of terminal closed deals from broker deal history / snapshot store | `HALT` on corruption |
| `unrealized_pnl` | **Deterministically Derived** | Calculated as $\sum q_i \cdot (\text{mark\_price}_i - \text{entry\_price}_i)$ using exact `Decimal` arithmetic | `HALT` on arithmetic discrepancy |
| `total_equity` | **Broker Authoritative** (MT5) / **Explicit Simulator Accounting Model** (Local) | Queried from `AccountInfo.equity` (MT5). In Local Simulator, derived via explicit simulator accounting model: $\text{equity} = \text{cash} + \text{realized\_pnl} + \text{unrealized\_pnl} - \text{commissions}$ | `HALT` if accounting invariant violated |
| `gross_exposure`| **Deterministically Derived** | $\sum \|q_i \cdot \text{mark\_price}_i\|$ derived via canonical `PortfolioState` validator | `HALT` on validation failure |
| `net_exposure`  | **Deterministically Derived** | $\sum q_i \cdot \text{mark\_price}_i$ derived via canonical `PortfolioState` validator | `HALT` on validation failure |

> [!IMPORTANT]
> **No Universal Accounting Fallacy:** The formula $\text{equity} = \text{cash} + \text{realized\_pnl} + \text{unrealized\_pnl} - \text{commissions}$ is strictly an explicit invariant of the Local Simulator accounting store. It is NOT assumed to represent live broker margin/financing rules. In MT5 mode, `AccountInfo.equity` is the sole broker-authoritative source of truth.

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

## 9. ExecutionManifest Contract & Non-Circular Digest Specification

### 9.1 Canonical Schema Authority
To prevent the creation of a duplicate source of truth, **the runtime DOES NOT define a new `ExecutionManifest` class**.

`PaperExecutionBridge` directly imports and instantiates the **existing frozen Phase 7 canonical contract**:
```python
from acash.execution.schema import ExecutionManifest
```
All fields, field validators, and typing constraints match the authoritative contract in `src/acash/execution/schema.py:609`.

### 9.2 Non-Circular Digest Preimage Specification
`ExecutionManifest.execution_digest` is a 64-character lowercase hexadecimal SHA-256 hash. To eliminate the circular definition identified in the auditor review, the digest is computed over a strictly non-self-referential preimage, matching the existing repository standard in `src/acash/monitoring/schema.py:596` and `src/acash/execution/alpaca/order_exercise.py:252`:

$$\text{execution\_digest} = \text{SHA-256}\left(\text{CanonicalConfigSerializer.serialize}(\mathcal{P}_{\text{manifest}})\right)$$

where the preimage dictionary $\mathcal{P}_{\text{manifest}}$ contains all fields of the execution manifest **strictly excluding the `execution_digest` field itself**:

$$\mathcal{P}_{\text{manifest}} = \{ k: v \mid (k, v) \in \text{manifest\_dict.items()} \land k \neq \text{"execution\_digest"} \}$$

### 9.3 UNKNOWN Broker Handling
- If an order times out or broker status is pending, `closed_at` MUST remain `None` and `terminal_state` is unassigned.
- **Zero Invented Terminal States:** Under no circumstances will a timeout cause an order to be manufactured as `"FILLED"` or `"CANCELLED"` without authoritative broker deal evidence or 6-D reconciliation.

---

## 10. Paper Trading Session Identity Specification

### 10.1 Schema Authority
Unlike `ExecutionManifest` (which is an existing Phase 7 contract), `PaperTradingSessionIdentity` is a **NEW Phase 13 runtime contract** defined in `src/acash/runtime/strategy_adapter.py`. It establishes cryptographic session lineage for paper trading:

```python
class PaperTradingSessionIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    paper_run_id: str = Field(description="Unique deterministic session ID (e.g. PAPER-RUN-20260905-MT5-001).")
    strategy_id: str = Field(description="Canonical strategy identifier.")
    strategy_version: str = Field(description="Semantic version of strategy code.")
    market: str = Field(description="Target market identifier (TRADITIONAL_FX, DIGITAL_ASSET).")
    venue: str = Field(description="Execution venue identifier (METAQUOTES_MT5_DEMO, IN_MEMORY_SIMULATOR).")
    data_source: FeedSourceType = Field(description="MT5_FORWARD or STREAMING_PARQUET_PUMP.")
    execution_mode: PaperExecutionVenueType = Field(description="MT5_DEMO or LOCAL_SIMULATOR.")
    start_time_utc: datetime = Field(description="Session initialization timestamp.")
    planned_end_time_utc: datetime = Field(description="Scheduled session end time (e.g. start + 90 days).")
    actual_end_time_utc: Optional[datetime] = Field(default=None, description="Recorded session termination time.")
    config_digest: str = Field(description="Canonical SHA-256 of RuntimePolicyConfig + ExecutionCostModel.")
    dossier_digest: str = Field(description="Canonical SHA-256 of AlphaQualificationDossier.")
```

> **Note on Identifiers:** Example IDs such as `PAPER-RUN-20260905-MT5-001` (Weekday) and `PAPER-RUN-20260905-CRYPTO-WEEKEND-001` (Weekend) illustrate deterministic naming conventions; they are not hardcoded into runtime source.

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

## 13. Deterministic Execution Cost Model Specification

To eliminate arbitrary hard-coded numbers (magic constants) in the local simulator, all execution costs are explicitly modeled. To satisfy strict reproducibility, dispersion is explicitly seeded:

```text
ExecutionCostModel
    ├── SpreadModelConfig (base spread + volatility expansion)
    ├── SlippageModelConfig (deterministic fixed drag + seeded PRNG dispersion)
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
    fixed_slippage_bps: Decimal = Decimal("0.20")  # Deterministic base drag
    prng_seed: int = Field(default=42, description="Explicit deterministic PRNG seed for reproducible dispersion.")
    dispersion_slippage_std_bps: Decimal = Field(
        default=Decimal("0.00"),
        description="Set to 0.00 for pure deterministic drag; non-zero uses deterministic seeded PRNG.",
    )

class CommissionModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    commission_per_lot_usd: Decimal = Decimal("7.00")  # Deterministic test-model fee parameter

class ExecutionCostModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    spread_model: SpreadModelConfig
    slippage_model: SlippageModelConfig
    commission_model: CommissionModelConfig
    provenance: str = Field(default="DETERMINISTIC_TEST_MODEL")
```

#### Parameter Provenance & Lineage Table:
All simulator parameters are classified strictly under **`DETERMINISTIC_TEST_CONFIGURATION`** to avoid unsupported assertions regarding empirical broker contracts:

| Parameter | Default Value | Authority Source | Ingested in `config_digest`? | Real-Market Representation |
|---|---|---|---|---|
| `base_spread_pips` | `1.2` | `DETERMINISTIC_TEST_CONFIGURATION` | **YES** (Mandatory) | Local Simulator Estimate Only (MT5 uses live broker spread) |
| `volatility_expansion_factor`| `1.0` | `DETERMINISTIC_TEST_CONFIGURATION` | **YES** (Mandatory) | Local Simulator Estimate Only |
| `fixed_slippage_bps` | `0.20` | `DETERMINISTIC_TEST_CONFIGURATION` | **YES** (Mandatory) | Local Simulator Estimate Only (MT5 experiences broker slippage) |
| `prng_seed` | `42` | `DETERMINISTIC_TEST_CONFIGURATION` | **YES** (Mandatory) | Seed for deterministic pseudorandom slippage generation |
| `dispersion_slippage_std_bps`| `0.00` | `DETERMINISTIC_TEST_CONFIGURATION` | **YES** (Mandatory) | Local Simulator Estimate Only (0.00 = pure deterministic fixed drag) |
| `commission_per_lot_usd` | `7.00` | `DETERMINISTIC_TEST_CONFIGURATION` | **YES** (Mandatory) | Local Simulator Estimate Only (default $7.00/lot is a deterministic model parameter; NOT an asserted broker contract) |

### 13.2 Rules:
1. Every execution-cost parameter MUST be explicit. No unexplained magic constants in simulation code.
2. All configurable execution-cost parameters (including `prng_seed`) MUST contribute directly to `session_identity.config_digest`.
3. Simulator results generated by `LOCAL_SIMULATOR` MUST be explicitly tagged as `LOCAL_SIMULATOR_ESTIMATE`. They must never be represented as empirical facts about MT5 broker execution.

---

## 14. Test Plan / 20-Vector Adversarial Matrix

### 14.1 Single-File Constraint & Architecture Alignment
> [!NOTE]
> **Single-File Test Suite Constraint (`tests/unit/runtime/test_paper_bridge.py`):**  
> The consolidation of 20 adversarial vectors into a single test file is a **governance constraint bounded by the locked 5-file implementation scope**, NOT a conflation of component boundaries. The test file is partitioned into 4 distinct, hermetic test suites:
> 1. `TestPaperExecutionBridge` (Vectors V-01 to V-04, V-11, V-12, V-19, V-20)
> 2. `TestForwardMarketDataFeeder` (Vectors V-05, V-06, V-15)
> 3. `TestPortfolioStateRehydrator` (Vectors V-07 to V-09, V-10, V-13, V-14, V-16)
> 4. `TestPaperStrategyAdapter` (Vectors V-17, V-18)

### 14.2 Adversarial Vector Specification
| Vector ID | Target Invariant | Scenario Description | Expected Fail-Closed Behavior |
|---|---|---|---|
| **V-01** | Zero Delta | Target allocation equals current position ($\Delta q \equiv 0$) | Emits 0 orders; dispatch suppressed cleanly. |
| **V-02** | Vetoed Allocation | Stage 4 risk engine returns `RiskVerdict.REJECTED` | Emits 0 orders; cycle outcome `RISK_REJECTED`. |
| **V-03** | Matcher Partial/Full Fill | Local matcher emits deterministic multi-stage fill: `ACK` $\to$ `PARTIAL_FILL` (50% volume, order in `PARTIALLY_FILLED`, residual working) $\to$ subsequent pulse emits `FILLED` (100% volume, order in `FILLED`). | Coordinator transitions `ACKNOWLEDGED` $\to$ `PARTIALLY_FILLED` $\to$ `FILLED`; emits canonical `ExecutionManifest`. |
| **V-04** | Rejected Order | Venue rejects order (e.g. invalid symbol/volume) | Coordinator transitions to `REJECTED`; incident logged. |
| **V-05** | Fresh Tick | Tick received with age 50ms | Stage 1 passes; `data_age_ms` recorded. |
| **V-06** | Stale Data | Tick received with age 2500ms (> 1500ms threshold) | Stage 1 halts pulse; emits `CycleOutcome.DATA_STALE`. |
| **V-07** | Clean Rehydration | Process restarts with valid ledger & snapshot | Rehydrates exact cash, positions, and equity from verified sources. |
| **V-08** | Corrupted Ledger | Single byte mutated in `operational_ledger.jsonl` | Rehydration raises `DataContractError`; startup halted. |
| **V-09** | Broker Discrepancy | Live MT5 position differs from local snapshot | Rehydration emits `DISCREPANCY_HALT`; refuses cycles. |
| **V-10** | Session Identity Lineage | Verify complete session identity serialization | All fields present; `config_digest` validated. |
| **V-11** | Duplicate Intent | Re-submitting identical `intent_id` in same cycle | Deduplicated; zero duplicate broker orders dispatched. |
| **V-12** | Duplicate Client Order ID | Re-using `client_order_id` across cycles | Rejected by coordinator deduplication check. |
| **V-13** | Restart during UNKNOWN | Process killed while order in `UNKNOWN` state | Startup forces 6-D reconciliation before new cycles. |
| **V-14** | Restart after ACK before FILL | Process killed after ACK before fill event | Rehydrates pending status; awaits fill or queries broker. |
| **V-15** | Stale Feed with Open Position | Data feed drops while position exists | Suppresses rebalance / new dispatch; preserves current state; invokes existing Phase 9 risk/reconciliation policy. Runtime bridge never invents secondary stop-loss orders. |
| **V-16** | Broker/Ledger Divergence | Position or deal exists on broker without corresponding ACASH `intent_id` / `client_order_id` in ledger | Reconciler flags unmanaged external divergence via `MT5AuthoritativeReconciler` $\implies$ `DISCREPANCY_HALT`. (Legitimate asynchronous broker events matching open intents continue normal 6-D reconciliation). |
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

## 16. Weekday / Weekend Market Track Architecture (Formal Specification)

### 16.1 Operational Rationale & Market Context
Traditional financial markets traded via the primary Phase 13 MT5 Demo venue are closed through the Saturday/Sunday period. Under a strict single-track weekday architecture, the ACASH host, runtime scheduler, and network infrastructure would remain idle for ~48 hours every weekend. 

Conversely, digital-asset markets operate on a continuous 24/7/365 basis. In institutional market infrastructure, this paradigm was further consolidated when CME introduced 24/7 trading for cryptocurrency futures and options on May 29, 2026 (subject to a scheduled weekly maintenance window of at least 2 hours).

> [!IMPORTANT]
> **Market Context Citation Only:** Mention of CME 24/7 trading serves solely as empirical market evidence. It MUST NOT be construed as an implementation requirement or commitment to connect to CME infrastructure.

### 16.2 Conceptual Track Architecture
ACASH decouples continuous paper operations into two logically and experimentally isolated tracks:

```text
                           ACASH Paper Runtime
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
              WEEKDAY TRACK                   WEEKEND TRACK
                    │                               │
                MT5 Demo                       Crypto 24/7
                    │                               │
              Forward Paper                   Future Paper
                    │                               │
              Primary 90-Day               Separate Experiment
                 Dataset                         Dataset
```

### 16.3 Logical Separation of Tracks
| Dimension | Weekday Paper Track | Weekend Paper Track |
|---|---|---|
| **Market Type** | Traditional Financial Markets (FX / EURUSD) | 24/7 Digital Asset Markets (Crypto Spot / Derivatives) |
| **Primary Venue** | `METAQUOTES_MT5_DEMO` | Candidate Future Crypto Venue / Test Double |
| **Operational Purpose** | Primary Phase 13 canonical 90-day forward paper validation | Weekend forward-operation, soak, infrastructure validation |
| **Operating Window** | Monday 00:00 UTC through Friday 21:59 UTC | Friday 22:00 UTC through Sunday 23:59 UTC |
| **Experimental Dataset** | **Experiment A** (`PAPER-RUN-WEEKDAY-...`) | **Experiment B** (`PAPER-RUN-WEEKEND-...`) |
| **Phase 13 Status** | **ACTIVE SPECIFICATION** (5-file locked scope) | **ARCHITECTURALLY DEFINED / NOT IMPLEMENTED / NOT OPERATIONAL** |

### 16.4 Strict Experimental & Statistical Isolation
The runtime strictly enforces complete experimental isolation between Experiment A and Experiment B. Under no circumstances may metrics or statistical distributions be aggregated across tracks:

$$\mathcal{D}_{\text{Weekday}} \cap \mathcal{D}_{\text{Weekend}} = \emptyset$$

The runtime monitoring, telemetry, and reporting subsystems MUST NOT combine:
- Realized / Unrealized PnL
- Sharpe / Sortino / Information Ratios
- Maximum Drawdown & Drawdown Duration
- Win Rate & Trade Count
- Expectancy & Profit Factor
- Execution Latency & Network Round-Trip
- Fill Rates & Rejection Frequencies
- Realized Slippage & Market Impact
- Strategy Performance Attribution
- Market Regime Classifications

### 16.5 Strategy Separation & Independent Qualification
A strategy qualified for the traditional FX market MUST NOT be assumed to transfer to digital assets:
$$\text{Qualified}_{\text{FX}} \not\implies \text{Qualified}_{\text{Crypto}} \quad \text{and} \quad \text{Qualified}_{\text{Crypto}} \not\implies \text{Qualified}_{\text{FX}}$$

- The Weekend Track requires its own independent research hypothesis, backtesting, walk-forward analysis, Deflated Sharpe Ratio calculation, Bailey CSCV PBO estimation, and formal Phase 8.5 `AlphaQualificationGate` review.
- No synthetic dossiers will be created for crypto strategies.
- Each track binds its own distinct `strategy_id`, `strategy_version`, and `dossier_digest` in its session identity.

### 16.6 Execution Model Separation
The runtime architecture acknowledges that execution microstructure differs fundamentally between MT5 and digital asset venues:
- **MT5 Model:** Retail/institutional broker bridge, fixed contract lot sizing (0.01 lot step), broker quote-driven execution, single-account margin.
- **Crypto Model:** Centralized order book (CLOB) / AMM, fractional sizing ($10^{-8}$ satoshi precision), maker/taker tiered fees, funding rate payments (perpetual futures), maintenance windows (e.g. CME $\ge 2$h weekly maintenance), API key / signature authentication, websocket order-book feeds.

None of these crypto execution models are implemented in Rev 2.2.

### 16.7 Strict Scope Boundaries for Rev 2.2
| Permitted in Rev 2.2 (Architecture Only) | Strictly Forbidden in Rev 2.2 (No Implementation) |
|---|---|
| Architecture model definition | Implementing crypto exchange REST/Websocket APIs |
| Lifecycle state definition | Storing or configuring crypto exchange API credentials |
| Session identity schema definition | Implementing crypto broker adapters or venues |
| Experimental dataset isolation rules | Implementing crypto `OrderIntent` dispatch |
| Future interface and boundary specifications | Connecting to live crypto exchange endpoints |
| Independent qualification criteria | Executing crypto orders or simulated crypto trades |
| Operational scheduler segmentation rules | Altering runtime source code to add crypto logic |

---

## 17. File-Level Change Matrix

The implementation scope remains strictly locked to **4 runtime files and 1 unit test file**:

| Target File Path | Purpose | Allowed Classes & Functions | Consumed Contracts | Contracts NOT Allowed to Change | Test Coverage | Operational Risk | Rollback Impact |
|---|---|---|---|---|---|---|---|
| `src/acash/runtime/paper_bridge.py` | Order translation, volume quantization & dispatch seam | `PaperExecutionBridge`, `SimulatedMarketMatcher`, `PaperExecutionVenueType`, `ExecutionCostModel` | `AllocationDecision`, `OrderIntent`, `BrokerRawEvent`, `ExecutionCoordinator`, canonical `ExecutionManifest` | Zero secondary risk logic; zero sizing alterations; zero frozen core edits. | V-01, V-02, V-03, V-04, V-11, V-12, V-19, V-20 | Low (isolated translation layer) | Clean deletion; zero core regressions |
| `src/acash/runtime/feeder.py` | Market data feed pump & freshness | `ForwardMarketDataFeeder`, `MarketFeedStatus`, `FeedSourceType` | `IMarketDataProvider`, `Bar`, `MarketDataSnapshot`, `NativeMT5Transport` | Zero synthetic bar imputation; zero silent fallback on stale ticks. | V-05, V-06, V-15 | Low (read-only polling adapter) | Clean deletion; zero core regressions |
| `src/acash/runtime/rehydration.py` | Crash/restart recovery & reconciliation | `PortfolioStateRehydrator`, `RehydrationStatus`, `PortfolioSnapshotStore` | `OperationalLedger`, `OperationalCycleEvent`, `PortfolioState`, `MT5BrokerAdapter`, `MT5AuthoritativeReconciler` | Zero position fabrication; zero recovery on broken ledger hash. | V-07, V-08, V-09, V-10, V-13, V-14, V-16 | Medium (state reconstruction) | Revert to clean empty genesis |
| `src/acash/runtime/strategy_adapter.py` | Read/verify strategy adapter & session identity | `PaperStrategyAdapter`, `PaperTradingSessionIdentity` (new runtime contract) | `MultiHorizonMomentumStrategy`, `AlphaQualificationDossier`, `AlphaLifecycleState` | Zero lifecycle promotion; zero synthetic dossier creation. | V-17, V-18 | Low (read/verify wrapper) | Clean deletion; strategy stays blocked |
| `tests/unit/runtime/test_paper_bridge.py` | 4 hermetic test suites in 1 file | `TestPaperExecutionBridge`, `TestForwardMarketDataFeeder`, `TestPortfolioStateRehydrator`, `TestPaperStrategyAdapter` | Pytest fixtures, mock adapters, temporary file fixtures | No skipped tests; no assertions claiming unverified behavior. | V-01 through V-20 | None (test suite only) | Deletion of test file |

---

## 18. Frozen-Core Protection

The ACASH core architecture (Phases 1–12) is formally **FROZEN**. The implementation of Rev 2.2 MUST NOT modify:
- `ExecutionCoordinator` state machine or transition semantics (`src/acash/execution/coordinator.py`).
- `transition_order()` sole state authority (`src/acash/execution/state_machine.py`).
- `ExecutionManifest` canonical schema (`src/acash/execution/schema.py`).
- Phase 9 Sovereign Risk Engine contracts (`src/acash/risk/risk_engine.py`).
- Sovereign Kill Switch controller or persistence (`src/acash/risk/kill_switch.py`).
- Phase 12 MT5 Authoritative Reconciler (`src/acash/execution/mt5/reconciliation.py`).
- Phase 8.5 Alpha Qualification Gate contracts (`src/acash/research/qualification.py`).

If any implementation requirement appears to necessitate modifying frozen core files, work MUST halt immediately for architectural escalation (`BLOCKED / ESCALATION REQUIRED`).

---

## 19. Mandatory Acceptance Checklist (Rev 2.2 Contract)

- [ ] Rev2 findings #1–#9 addressed
- [ ] No synthetic dossier
- [ ] Strategy remains qualification-blocked (`STRAT-MOM-MULTI-HORIZON-V1`)
- [ ] Bridge is translation/dispatch only
- [ ] Multi-stage partial-fill lifecycle explicitly specified (`ACK` $\to$ `PARTIAL_FILL` $\to$ residual working $\to$ `FILLED`)
- [ ] Venue `volume_step` quantization pipeline formally specified with `ROUND_DOWN`, residual drop, and min-lot suppression
- [ ] Execution cost assumptions explicit and seeded deterministic
- [ ] Commission cost provenance explicitly classified as `DETERMINISTIC_TEST_CONFIGURATION`
- [ ] `config_digest` binds execution-cost parameters (including `prng_seed`)
- [ ] Rehydration authority is schema-grounded
- [ ] Local Simulator equity follows explicit simulator accounting model
- [ ] Timeout semantics preserve `UNKNOWN`
- [ ] MT5 forward feed separated from Parquet pump
- [ ] Lifecycle authority preserved
- [ ] `ExecutionManifest` consumes existing canonical Phase 7 contract
- [ ] `ExecutionManifest.execution_digest` uses non-circular preimage excluding itself
- [ ] Session identity complete (new Phase 13 runtime contract)
- [ ] Adversarial matrix expanded (20 vectors partitioned into 4 test suites)
- [ ] V-15 invokes existing risk policy without inventing secondary stop orders
- [ ] V-16 grounds divergence in `MT5AuthoritativeReconciler`
- [ ] Weekday track defined (MT5 Demo forward paper)
- [ ] Weekend track defined (architecturally defined, not implemented, not operational)
- [ ] Weekend track experimentally isolated (zero statistical mixing)
- [ ] Crypto NOT implemented
- [ ] No crypto credentials
- [ ] No crypto connectivity
- [ ] No frozen-core changes
- [ ] Live capital remains `$0.00`
- [ ] Live orders remain `0`

---

## 20. Implementation Gate & Next Steps

This document is submitted for **Human Plan Review**.

```text
CURRENT GATE: IMPLEMENTATION PLANNING GATE
STATUS:       LOCKED — AWAITING EXPLICIT HUMAN PLAN APPROVAL
```

Execution of source code implementation remains strictly blocked until the Human Auditor responds with the single, unambiguous authorization command:
```text
GO IMPLEMENTATION REV2.2
```

---

## 21. Explicit Non-Claims

1. Approval of this plan does NOT constitute approval to trade live capital.
2. Approval of this plan does NOT constitute an assertion that `MultiHorizonMomentumStrategy` has positive empirical alpha.
3. Passing unit tests on `test_paper_bridge.py` does NOT constitute completion of the 90-day paper trading validation.
4. Local simulator results under `SimulatedMarketMatcher` do NOT prove real-world MT5 execution quality.
5. Specification of the Weekend Paper Track does NOT constitute implementation or deployment of crypto trading capabilities.
