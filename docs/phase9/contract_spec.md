# Phase 9: Deterministic Risk Engine & Kill Switch
## Canonical Contract Specification (Contract v1.1 Locked)

> **Document:** `docs/phase9/contract_spec.md`  
> **Status:** 100% COMPLETE & LOCKED FOR IMPLEMENTATION  
> **Baseline Commit:** `9ce1365` (Phase 8.5 Frozen Baseline, 772/772 tests passing, 0 MyPy errors)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Single Authority, Strict Fail-Closed, Separation of Concerns)

---

## 1. Executive Summary & Core Architectural Invariants

Phase 9 establishes the **Runtime Sovereign Risk Control Plane** for the ACASH algorithmic trading platform. It operates deterministically between Phase 8 (Portfolio Allocation & Rebalance Planning) and Phase 7 (Pre-Live Risk Admission & Execution Coordination).

### Non-Negotiable Sovereign Invariants:
1. **Four-Way Sovereign Boundary:**
   $$\boxed{\mathbf{Research\ (8.5)} \neq \mathbf{Allocation\ (8)} \neq \mathbf{Risk\ (9)} \neq \mathbf{Execution\ (7)}}$$
2. **Sovereign Risk Veto:**
   $$\boxed{\mathbf{Risk\ Rejection} \implies \text{Execution Blocked (Fail-Closed, 0 Orders Transmitted)}}$$
3. **Zero Direct Execution Authority in Phase 9:**
   $$\boxed{\mathbf{Risk\ Approval} \neq \text{Execution Authorization} \quad \land \quad \mathbf{Phase\ 9} \nRightarrow \text{Direct Broker Wire Access}}$$
   *Phase 9 evaluates risk, derisks targets, and issues verdicts; Phase 7 remains the sole authority for cryptographic admission, order construction, and broker wire communication.*
4. **Emergency Intent Generation $\neq$ Flatten Completion:**
   $$\boxed{\mathbf{EmergencyFlattenIntent\ Emitted} \neq \mathbf{Positions\ Flattened}}$$
   *Phase 9 requests zero-target liquidation; only Phase 7 and authoritative broker fills prove position flattening.*
5. **Strict Fail-Closed Contract:**
   *Any missing data, non-nominal calculation status, non-finite arithmetic, clock skew, or unhandled exception immediately results in `RiskVerdict.REJECTED` or `KillSwitchState.TRIPPED`.*

---

## 2. Itemized Classification Ledger

| Component / Policy / Item | Classification | Rationale & Authority |
| :--- | :--- | :--- |
| **Sovereign Risk Veto** | `[LOCK]` | ADR-003: Risk Engine possesses non-negotiable software veto over all models. |
| **Zero Broker Wire Access in Phase 9** | `[LOCK]` | Separation of concerns: Phase 7 is the sole broker execution boundary. |
| **`EXACT_SCALE_DOWN` Sizing Algorithm** | `[LOCK]` | Monotonically proven uniform scale-down preserving long-only & cash floors. |
| **`BINARY_REJECT` Sizing Policy** | `[LOCK]` | Fail-closed immediate 100% Cash assignment upon any invariant breach. |
| **Kill Switch Controller (5-Stage Lifecycle)** | `[LOCK]` | `DETECT -> TRIP -> PERSIST -> BLOCK -> RESET` separated from trigger detection. |
| **Quorum Reset Contract** | `[LOCK]` | Pinned to existing Phase 7 `Ed25519TrustStore` multi-sig signature quorum. |
| **Emergency Flattening Boundary** | `[LOCK]` | Phase 9 emits `EmergencyFlattenIntent`; Phase 7 executes and reconciles. |
| **Risk-State Bridge Precision** | `[LOCK]` | Explicit finite Decimal conversion; zero silent casting or float drift. |
| **Risk Policy Thresholds** | `[CONFIGURABLE_GOVERNANCE_POLICY]` | Leverage, drawdown, concentration limits configured via typed policy. |
| **Intraday Loss Rollover Epoch** | `[CONFIGURABLE_GOVERNANCE_POLICY]` | Default: 00:00:00 UTC calendar day boundary. |

---

## 3. Runtime Authority Chain & Detailed Boundary Mapping

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 8.5: Alpha Research & Evidence Validation                         │
│ - Authority: Empirical evidence admissibility only                      │
│ - Output: AlphaQualificationDossier (RESEARCH_QUALIFIED)                │
│ - Invariant: Capital Authority === $0.00, Live Order Authority === None │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Candidate Strategy Inputs
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 8: Portfolio Engine & Rebalance Planning                          │
│ - Authority: Capital allocation optimization & rebalance delta planning │
│ - Gate: PortfolioGovernanceGate (Hurdle, DSR, Long-only, 100% Cash)    │
│ - Output: AllocationDecision -> RebalancePlan (Target Qtys & Deltas)    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ RebalancePlan / Candidate Allocations
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 9: Deterministic Risk Engine & Kill Switch (SOVEREIGN CONTROL)   │
│ - Authority: Sovereign veto over all allocations; Real-time risk gate   │
│ - Evaluator: DeterministicRiskEngine (implements IRiskEngine)           │
│ - Actions: APPROVED (100%) | REDUCED (Scaled down) | REJECTED (0% Cash) │
│ - Global Override: KillSwitchEvent (CANCEL_ORDERS, EMERGENCY_FLATTEN)  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ RiskEvaluationReport / Safe Targets
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 7: Pre-Live Risk Admission & Execution Coordinator                │
│ - Authority: Cryptographic ticket verification, BMAP, state machine     │
│ - Admission: construct_order_intent() (Active Auth, RiskState, Limits)  │
│ - Coordinator: ExecutionCoordinator (Reconciliation, Idempotency, Dedup)│
│ - Driver: AlpacaPaperAdapter / MockBroker -> Paper Broker Venue         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Authoritative Phase 9 Domain Contracts & Output Models

### 4.1 Enumerations
```python
class RiskVerdict(str, Enum):
    APPROVED = "APPROVED"                      # 100% of candidate weights clear all risk gates
    REDUCED = "REDUCED"                        # Scaled down monotonically via EXACT_SCALE_DOWN policy
    REJECTED = "REJECTED"                      # Failed risk gates; 100% Cash assigned (0 orders)
    KILL_SWITCH_BLOCKED = "KILL_SWITCH_BLOCKED"# Blocked due to active/tripped kill switch

class DeriskPolicy(str, Enum):
    EXACT_SCALE_DOWN = "EXACT_SCALE_DOWN"      # Proportional scale-down preserving cash buffer
    BINARY_REJECT = "BINARY_REJECT"            # Any breach immediately forces REJECTED (100% Cash)

class KillSwitchState(str, Enum):
    ACTIVE = "ACTIVE"                          # Normal operations permitted
    TRIPPED = "TRIPPED"                        # Hard breach tripped; immediate admission lockout
    PERSISTENTLY_BLOCKED = "PERSISTENTLY_BLOCKED" # Persisted to disk ledger; surviving restarts
    RESET_PENDING = "RESET_PENDING"            # Quorum signatures submitted, validating
```

### 4.2 `RiskPolicyConfig`
Immutable, frozen configuration defining sovereign risk boundaries:
```python
class RiskPolicyConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_version: str = Field(default="v1.0.0")
    derisk_policy: DeriskPolicy = Field(default=DeriskPolicy.EXACT_SCALE_DOWN)
    max_gross_leverage: Decimal = Field(default=Decimal("1.00"))
    max_asset_concentration: Decimal = Field(default=Decimal("0.25"))
    min_cash_buffer: Decimal = Field(default=Decimal("0.05"))
    max_drawdown_limit_pct: Decimal = Field(default=Decimal("15.00"))
    max_daily_loss_usd: Decimal = Field(default=Decimal("10000.00"))
    min_margin_buffer_usd: Decimal = Field(default=Decimal("5000.00"))
    max_market_data_age_ms: int = Field(default=1500)
    max_clock_drift_ms: int = Field(default=500)
    evaluation_ttl_seconds: int = Field(default=60)
```

### 4.3 `RiskEvaluationReport`
The authoritative cryptographic evidence artifact emitted by `DeterministicRiskEngine`:
- **`evaluation_id`**: Deterministic unique identifier `RISK_EVAL_<timestamp_ms>`.
- **`verdict`**: `RiskVerdict` (`APPROVED`, `REDUCED`, `REJECTED`, `KILL_SWITCH_BLOCKED`).
- **`original_allocation_digest`**: SHA-256 digest of input candidate allocation.
- **`portfolio_state_digest`**: SHA-256 digest of input `PortfolioState`.
- **`account_state_digest`**: SHA-256 digest of input `AccountState`.
- **`risk_policy_digest`**: SHA-256 digest of active `RiskPolicyConfig`.
- **`adjusted_weights`**: Mapping of asset symbols to final approved/derisked `Decimal` weights.
- **`cash_weight`**: Realized `Decimal` cash weight ($\ge \text{min\_cash\_buffer}$).
- **`evaluated_at_utc`**: Strict UTC evaluation timestamp.
- **`expires_at_utc`**: Evaluation expiration timestamp ($\text{evaluated\_at\_utc} + \text{ttl}$).
- **`rejection_reason`**: `Optional[str]` containing machine-readable failure reason.
- **`report_digest`**: 64-hex SHA-256 digest over canonical sorted JSON representation.

---

## 5. Mathematical Invariants & Derisking Sizing Specification

### 5.1 Exact Invariant Definitions

1. **Long-Only Asset Domain:**
   $$\forall i \in \text{Assets}, \quad w_i \ge 0, \quad w_i \text{ is finite Decimal}$$
2. **Exact Cash Conservation:**
   $$\sum_{i=1}^N w_i + w_{\text{cash}} \equiv 1.0$$
3. **Gross Leverage Formulation:**
   $$\text{Gross Leverage} = \sum_{i=1}^N w_i \le \text{MaxGrossLeverage} \quad (\text{Default: } 1.00)$$
4. **Single-Asset Concentration Formulation:**
   $$\forall i \in \text{Assets}, \quad w_i \le \text{MaxAssetConcentration} \quad (\text{Default: } 0.25)$$
5. **Mandatory Cash Buffer Floor:**
   $$w_{\text{cash}} \ge \text{MinCashBuffer} \quad (\text{Default: } 0.05)$$
6. **Peak-to-Trough Drawdown Formulation:**
   $$\text{Peak Equity} = \max_{t' \le t} \text{Total Equity}(t')$$
   $$\text{Drawdown Pct} = \frac{\text{Peak Equity} - \text{Current Equity}}{\text{Peak Equity}} \times 100.0 < \text{MaxDrawdownLimitPct}$$
7. **Intraday Loss Formulation:**
   $$\text{Daily P&L} = \text{Realized P&L}_{\text{today}} + \text{Unrealized P&L} > -\text{MaxDailyLossUSD}$$

### 5.2 Derisking Sizing Mathematics (`EXACT_SCALE_DOWN`)

Given candidate risky weights $\mathbf{w} = (w_1, \dots, w_N)$ where $w_i \ge 0$:

1. **If already safe:** If $\sum w_i \le \text{MaxGrossLeverage}$, $\max_i w_i \le \text{MaxAssetConcentration}$, and $1.0 - \sum w_i \ge \text{MinCashBuffer}$, then $\alpha = 1.0$, $\mathbf{w}' = \mathbf{w}$, and verdict is `APPROVED`.
2. **If breaching leverage, concentration, or cash buffer:**
   $$\alpha_{\text{lev}} = \frac{\text{MaxGrossLeverage}}{\sum_{i=1}^N w_i}$$
   $$\alpha_{\text{conc}} = \min_{i} \left( \frac{\text{MaxAssetConcentration}}{w_i} \right)$$
   $$\alpha_{\text{cash}} = \frac{1.0 - \text{MinCashBuffer}}{\sum_{i=1}^N w_i}$$
   $$\alpha = \min\left(1.0, \alpha_{\text{lev}}, \alpha_{\text{conc}}, \alpha_{\text{cash}}\right)$$

   $$\forall i, \quad w_i' = \alpha \cdot w_i$$
   $$w_{\text{cash}}' = 1.0 - \sum_{i=1}^N w_i'$$
   $$\text{Verdict} = \text{REDUCED}$$

3. **Infeasibility Guard:** If $\text{MinCashBuffer} > 1.0$ or $\text{MaxGrossLeverage} \le 0.0$, scaling is impossible; engine fail-closes to `REJECTED` ($w_{\text{cash}} = 1.0$).

### 5.3 Mathematical Proof of `EXACT_SCALE_DOWN` Invariants:
- **Monotonicity:** $\alpha \le 1.0 \land w_i \ge 0 \implies w_i' \le w_i$. No position is ever increased.
- **No Short Creation:** $\alpha \ge 0 \land w_i \ge 0 \implies w_i' \ge 0$.
- **No Leverage Increase:** $\sum w_i' = \alpha \sum w_i \le \frac{\text{MaxGrossLeverage}}{\sum w_i} \sum w_i = \text{MaxGrossLeverage}$.
- **No Concentration Increase:** $\forall i, w_i' = \alpha w_i \le \frac{\text{MaxAssetConcentration}}{w_i} w_i = \text{MaxAssetConcentration}$.
- **Cash Floor Preservation:** $w_{\text{cash}}' = 1.0 - \alpha \sum w_i \ge 1.0 - (1.0 - \text{MinCashBuffer}) = \text{MinCashBuffer}$.
- **Idempotency:** $\text{scale}(\mathbf{w}') \implies \alpha' = 1.0 \implies \mathbf{w}'' \equiv \mathbf{w}'$.

---

## 6. Kill Switch Controller State Machine & Quorum Reset

```
      ┌────────────────────────────────────────────────────────┐
      │                                                        │
      ▼                                                        │
┌──────────────┐   Critical Breach Detected    ┌──────────────┐│ Ed25519 Multi-Sig
│    ACTIVE    │ ────────────────────────────> │   TRIPPED    ││ Quorum Reset
└──────────────┘   (Trip & Persist Ledger)     └──────────────┘│ Verified
      │                                                │       │
      │ Unknown / Stale State                          ▼       │
      │ ────────────────────────> ┌─────────────────────────┐ │
      │                           │ PERSISTENTLY_BLOCKED    │ ─┘
      └─────────────────────────> └─────────────────────────┘
```

### 6.1 State Transition Rules:
1. **`ACTIVE -> TRIPPED`**: Triggered immediately upon any critical breach emitted by telemetry trigger detection (`BROKER_DISCONNECTED`, `STALE_MARKET_DATA`, `CLOCK_SKEW_DETECTED`, `MAX_DAILY_LOSS`, `MAX_DRAWDOWN`).
2. **`TRIPPED -> PERSISTENTLY_BLOCKED`**: State and event digest are synchronously flushed to disk (`data/risk/kill_switch_state.json`).
3. **Crash Recovery**: Upon process boot, `KillSwitchController` reads the disk state. If `PERSISTENTLY_BLOCKED` or `TRIPPED`, it boots directly into `PERSISTENTLY_BLOCKED`.
4. **`PERSISTENTLY_BLOCKED -> ACTIVE`**: Requires verified `KillSwitchResetEvent` signed by authorized keys in `Ed25519TrustStore` meeting `required_approvals` quorum.

### 6.2 Quorum Reset Specification:
- **`KillSwitchResetEvent`**:
  - `event_id`: Unique identifier.
  - `kill_switch_event_id`: Bound to the specific trip event being reset.
  - `root_cause_summary`: Mandatory non-empty forensic explanation.
  - `actor_approvals`: Sequence of `AuthorizationApproval` records.
  - `reset_digest`: SHA-256 digest over canonical payload.
- **Verification Rule**: Every signature verified via `trust_store.verify()`. $|\text{Verified Signatures}| \ge \text{required\_approvals}$.

---

## 7. Emergency Flattening Protocol (Intent vs Execution Boundary)

$$\boxed{\text{Phase 9 (Emergency Intent)} \xrightarrow{\text{Zero Target Specification}} \text{Phase 7 (Order Construction \& Admission)} \xrightarrow{\text{Wire}} \text{Broker}}$$

1. **`EmergencyFlattenIntent` Model**:
   - `intent_id`: Unique identifier.
   - `kill_switch_event_id`: Linked trip event digest.
   - `target_positions`: $\forall \text{symbol}, q_{\text{target}} \equiv \text{Decimal("0.0")}$.
   - `closing_deltas`: $\forall \text{symbol}, \Delta q_i = -q_{\text{current}, i}$.
   - `issued_at_utc`: Strict UTC timestamp.
   - `intent_digest`: SHA-256 canonical digest.
2. **Execution & Reconciliation Boundary**:
   - Phase 9 emits `EmergencyFlattenIntent` and marks its state as `FLATTEN_REQUESTED`.
   - Phase 7 converts deltas into market liquidation orders, executes them against the broker, and updates `PortfolioState` via `ExecutionCoordinator`.
   - **Completion Condition**: Phase 9 transitions to `FLATTEN_COMPLETED` **only** when `PortfolioState.gross_exposure == Decimal("0.00")` and all positions are verified flat by Phase 7 reconciliation.

---

## 8. Type-Safe Risk-State Bridge Specification

The bridge guarantees deterministic, loss-less conversion into Phase 9 mathematical domain:

| Source Type | Target Type | Conversion & Validation Contract |
| :--- | :--- | :--- |
| `float` (Phase 1 TargetAllocation) | `Decimal` | `Decimal(str(v))` + assert `v.is_finite()` + assert `0.0 <= v <= 1.0` |
| `Decimal` (Phase 8 AllocationDecision) | `Decimal` | Assert `v.is_finite()` + assert `v >= Decimal("0.0")` |
| `PortfolioState.total_equity` | `Decimal` | Direct pass + assert `v.is_finite()` + assert `v > Decimal("0.0")` |
| `RiskState.data_age_ms` | `int` | `int(v)` + assert `v >= 0` |
| `RiskState.is_broker_connected` | `bool` | Strict boolean pass |

*Invariant: Any `NaN`, `Infinity`, or negative equity immediately raises `DataContractError` and halts evaluation.*

---

## 9. Replay & Staleness Protection for Risk Verdicts

A `RiskEvaluationReport` is valid for execution admission if and only if:
1. **Current Time within TTL:**
   $$\text{Current UTC} \le \text{report.expires\_at\_utc} \quad (\text{TTL: } 60\text{s})$$
2. **Digest Matching:**
   $$\text{recompute\_digest}(\text{report}) \equiv \text{report.report\_digest}$$
3. **State Consistency:**
   $$\text{report.portfolio\_state\_digest} \equiv \text{current\_portfolio\_state.digest}$$
4. **Policy Consistency:**
   $$\text{report.risk\_policy\_digest} \equiv \text{active\_policy\_config.digest}$$

If any condition fails, Phase 7 admission treats the verdict as expired and rejects order construction.

---

## 10. Verification Ledger

```markdown
### Verification Ledger
- Contract Version: CONTRACT v1.1 (LOCKED)
- Mathematical Invariants: Defined & Proven (Leverage, Concentration, Drawdown, Loss, Derisking)
- Separation of Concerns: Preserved (Phase 8.5 != Phase 8 != Phase 9 != Phase 7)
- Emergency Flattening: Bounded (Phase 9 Intent -> Phase 7 Execution & Verification)
- Kill Switch Controller: Defined (ACTIVE -> TRIPPED -> PERSISTENTLY_BLOCKED -> RESET)
- Quorum Reset: Bound to Phase 7 Ed25519TrustStore
- Production Code Written: ZERO
- Status: READY FOR IMPLEMENTATION PLAN
```
