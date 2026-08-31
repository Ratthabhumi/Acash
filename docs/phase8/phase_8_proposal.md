# Phase 8: Portfolio Engine Canonical Contract Specification

> **Document:** `docs/phase8/phase_8_proposal.md`  
> **Status:** FINAL CONTRACT DRAFT / READY FOR FREEZE REVIEW (DOCS-ONLY, ZERO CODE MUTATION)  
> **Version:** 2.2.0 (Precision Pass: Decoupled Estimators & Rigorous Notional Sizing Semantics)  
> **Authority:** `docs/ROADMAP.md` §Phase 8 + `docs/architecture/portfolio_architecture.md`  
> **Core Architectural Invariants:**  
> $$\boxed{\text{Candidate} \neq \text{Evaluation} \neq \text{Decision}} \quad \land \quad \boxed{\text{Ranking} \neq \text{Approval}} \quad \land \quad \boxed{\text{100\% Cash is a Sovereign Decision}}$$

---

## 0. Executive Summary & Audit Grounding

This document establishes the canonical mathematical and architectural contract for the **ACASH Phase 8 Portfolio Engine**. It strictly defines domain data models, allocator extension seams, out-of-sample evaluation rules, sovereign risk gates, and the execution boundary interfacing with Phase 7.

### 0.1 Grounding in Audit Reality (Audit A–E Synthesis)
1. **Input Data Requirement:** Phase 8 is a discrete-time multi-asset capital allocation system consuming **`AssetReturnPanel` ($T \times N$)** simple period returns and risk state metrics.
2. **L2/L3 Non-Blocking Reality:** High-frequency orderbook reconstruction (L2/MBP) and queue-level packets (L3/MBO) are microstructural execution concerns (Phases 3/10/12), **not blockers for Phase 8 portfolio allocation matrices**.
3. **Data Capability vs Dataset Distinction:** ACASH possesses verified Arrow schema, DuckDB/Parquet storage, and ingestion pipelines for OHLCV bars, trades, and BBO quotes. However, empirical production historical research datasets are not pre-packaged in the repository. Phase 8 contract designs must not assume pre-existing historical datasets.
4. **Existing Portfolio Domain Reuse:** The pure accounting models ([`PortfolioState`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/src/acash/core/domain/portfolio.py), `AccountState`, and transition functions in [`src/acash/core/domain/transitions.py`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/src/acash/core/domain/transitions.py)) are mathematically verified and will be reused directly.
5. **Legacy Interface Deprecation:** The Phase 1 legacy interface `IPortfolioOptimizer` ([`src/acash/core/interfaces/portfolio.py`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/src/acash/core/interfaces/portfolio.py)) is architecturally insufficient because `Signal -> TargetAllocation` bypasses the required `Candidate -> Evaluation -> Decision` governance boundary.
6. **Dependency State:** The current runtime environment runs Python 3.14.3, NumPy 2.5.2, and SciPy 1.18.1. `skfolio` and `cvxpy` are **NOT INSTALLED**; their compatibility is unverified. Phase 8 establishes a pure NumPy/SciPy baseline layer that operates deterministically without external optimizer packages.

---

## 1. System Architecture & Information Flow

The Portfolio Engine enforces strict separation between **candidate weight proposals**, **out-of-sample economic evaluation**, **sovereign capital authorization**, and **execution planning**:

```
                       ┌─────────────────────────┐
                       │    Data Health Gate     │
                       │ (PIT, Missing, Station) │
                       └────────────┬────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  AssetReturnPanel   │  (T x N Decimal Returns)
                         └──────────┬──────────┘
                                    │
       ┌────────────────────────────┴────────────────────────────┐
       │                                                         │
       ▼                                                         ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│     Baseline Allocators      │              │     Advanced Allocators      │
│  - 100% Cash                 │              │  - Hierarchical Risk Parity  │
│  - Equal Weight (1/N)        │              │  - Equal Risk Contribution   │
│  - Inverse Volatility (1/σ)  │              │  - Minimum CVaR (Optional)   │
└──────────────┬───────────────┘              └──────────────┬───────────────┘
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │    AllocationCandidate    │  (Raw Weight Proposals)
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   AllocationEvaluator     │
                        │ (Phase 6 CPCV, Turnover,  │
                        │  Friction, OOS Metrics)   │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   AllocationEvaluation    │  (Scorecard & RankScore)
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │  PortfolioGovernanceGate  │
                        │ (Hurdle, Risk, Drawdown,  │
                        │  Margin Buffer, Leverage) │
                        └─────────────┬─────────────┘
                                      │
                       ┌──────────────┴──────────────┐
                       │ FAIL / REJECT               │ PASS / AUTHORIZED
                       ▼                             ▼
              ┌─────────────────┐       ┌───────────────────────────┐
              │   100% CASH     │       │    AllocationDecision     │
              │(Sovereign Rej.) │       │  (Authorized Allocation)  │
              └─────────────────┘       └─────────────┬─────────────┘
                                                      │
                                                      ▼
                                        ┌───────────────────────────┐
                                        │     RebalancePlanner      │
                                        │ (Desired Notional & Delta)│
                                        └─────────────┬─────────────┘
                                                      │
══════════════════════════════════════════════════════╪══════════════════════════════
                                                      │ [Phase 7 Boundary]
                                                      ▼
                                        ┌───────────────────────────┐
                                        │   ExecutionCoordinator    │
                                        │  (OrderIntent, Routing,   │
                                        │   Fill Reconciliation)    │
                                        └───────────────────────────┘
```

---

## 2. Canonical Data Entities & Specifications

All domain models are immutable (frozen), strictly typed using `Decimal` for financial quantities, and bound by cryptographic lineage digests.

### 2.1 `PortfolioUniverse`
- **Purpose:** Authoritative definition of candidate tradable instruments for an allocation epoch.
- **Fields:**
  - `universe_id: str` — Unique identifier (e.g. `"UNIV_US_EQUITY_TOP10"`).
  - `assets: tuple[str, ...]` — Lexicographically sorted unique ticker symbols.
  - `as_of: datetime` — UTC-aware point-in-time timestamp.
  - `universe_digest: str` — Canonical SHA-256 digest computed over `sorted(assets)` and `as_of`.
- **Invariants:** `len(assets) >= 1`, all symbols alphanumeric uppercase, no duplicates.
- **Fail-Closed:** Empty assets or duplicate symbols raises `DataContractError`.

### 2.2 `AssetReturnPanel`
- **Purpose:** Immutable observation matrix of historical asset period returns.
- **Fields:**
  - `universe_id: str` — Must match `PortfolioUniverse.universe_id`.
  - `timestamps: tuple[datetime, ...]` — Monotonically strictly increasing UTC timestamps of length $T$.
  - `symbols: tuple[str, ...]` — Must match `PortfolioUniverse.assets` of length $N$.
  - `returns_matrix: tuple[tuple[Decimal, ...], ...]` — Array of shape $T \times N$ containing simple period returns ($r_{t, i} = (P_{t, i} - P_{t-1, i}) / P_{t-1, i}$).
  - `frequency: str` — Bar resolution (`"1D"`, `"1h"`).
  - `panel_digest: str` — SHA-256 digest over timestamps and return values.
- **Invariants:** $T \ge T_{\text{min}}$ (minimum history threshold), zero `NaN`/`Inf` entries, strictly synchronous timestamps across all $N$ assets.
- **Fail-Closed:** Missing data, non-finite values, or length mismatch raises `DataContractError`.

### 2.3 `PortfolioConstraints`
- **Purpose:** Explicit mathematical boundaries defining the feasible allocation space.
- **Fields:**
  - `min_weight: Decimal` — Lower bound per asset (default `Decimal("0.0")` for long-only).
  - `max_weight: Decimal` — Upper bound per asset concentration ceiling (e.g. `Decimal("0.30")`).
  - `max_gross_leverage: Decimal` — Maximum permitted gross leverage ($\sum |w_i| \le L_{\text{max}}$, default `Decimal("1.0")`).
  - `min_cash_buffer: Decimal` — Mandatory unallocated liquidity buffer ($w_{\text{cash}} \ge B_{\text{cash}}$, default `Decimal("0.05")`).
  - `max_turnover_per_rebalance: Optional[Decimal]` — Hard turnover ceiling ($\frac{1}{2}\sum |w_i - w_{i,\text{current}}| \le \Delta w_{\text{max}}$).
- **Invariants:** $0 \le \text{min\_weight} \le \text{max\_weight} \le 1.0$, $B_{\text{cash}} \in [0.0, 1.0]$, $L_{\text{max}} = 1.0$ (in non-leveraged Phase 8).
- **Fail-Closed:** Inconsistent bounds (e.g. $N \times \text{min\_weight} > 1.0 - B_{\text{cash}}$) raises `DomainValidationError`.

### 2.4 `RiskSnapshot`
- **Purpose:** Current account financial state and risk limits from the live execution/broker ledger.
- **Fields:**
  - `snapshot_id: str`
  - `timestamp: datetime` (UTC-aware)
  - `account_equity: Decimal` ($\text{Balance} + \text{Unrealized PnL}$)
  - `cash_balance: Decimal`
  - `margin_used: Decimal`
  - `margin_headroom: Decimal` ($\text{Free Margin}$)
  - `margin_buffer_threshold: Decimal` (Safety margin headroom requirement)
  - `current_drawdown_pct: Decimal`
  - `max_drawdown_limit_pct: Decimal`
  - `is_kill_switch_active: bool`
- **Invariants:** `account_equity > 0` (otherwise fail-closed), all monetary fields finite `Decimal`.

### 2.5 `AllocationCandidate` (Weight Proposals)
- **Purpose:** Raw weight proposal generated by an individual allocator algorithm before risk, feasibility normalization, and hurdle validation.
- **Semantics:** Allocators produce relative asset weights. Allocators are **not required** to fully solve cash buffer math internally; cash may be explicitly declared or derived during governance normalization.
- **Fields:**
  - `candidate_id: str` — Unique identifier (e.g. `"CAND_HRP_20260901"`).
  - `allocator_name: str` — Canonical algorithm name (`"CASH"`, `"EQUAL_WEIGHT"`, `"INVERSE_VOL"`, `"HRP"`, `"ERC"`, `"MIN_CVAR"`).
  - `asset_weights: Mapping[str, Decimal]` — Proposed weights per risky asset ($w_i \ge 0$).
  - `cash_weight: Optional[Decimal]` — Proposed unallocated cash weight if explicitly provided by allocator; if `None`, derived as $1.0 - \sum w_i$ during normalization.
  - `in_sample_metrics: Mapping[str, Decimal]` — In-sample variance, expected return, diversification ratio.
  - `candidate_digest: str` — SHA-256 over asset weights and allocator metadata.
- **Invariants:** $\sum w_i \le \text{Decimal("1.0")}$; all asset symbols match `PortfolioUniverse`.

### 2.6 `AllocationEvaluation` (Scorecard & Ranking)
- **Purpose:** Objective out-of-sample economic and friction scorecard for a candidate.
- **Semantics:** **$\text{Ranking} \neq \text{Approval}$**. A candidate receiving the highest `rank_score` is the top-ranked proposal, but it remains unapproved until it clears the `PortfolioGovernanceGate`.
- **Fields:**
  - `candidate_id: str`
  - `normalized_weights: Mapping[str, Decimal]` — Fully feasible portfolio weights ($\sum w_i + w_{\text{cash}} = 1.0$).
  - `normalized_cash_weight: Decimal` ($w_{\text{cash}} \ge B_{\text{cash}}$).
  - `oos_sharpe_ratio: Optional[Decimal]` — Out-of-sample annualized Sharpe ratio across Phase 6 CPCV test folds.
  - `oos_cvar_95: Optional[Decimal]` — Out-of-sample Conditional Value at Risk at 95% confidence.
  - `turnover_required: Decimal` — Total one-way turnover against current portfolio state: $\frac{1}{2}\sum |w_{i, \text{norm}} - w_{i, \text{current}}|$.
  - `estimated_transaction_cost: Decimal` — Dollar cost friction (commissions + half-spread + slippage).
  - `net_expected_excess_return: Decimal` — Expected portfolio return net of friction and benchmark rate: $\mathbf{w}^T \boldsymbol{\mu} - \mathcal{F} - r_f$.
  - `hurdle_rate_cleared: bool` — True if net expected excess return exceeds Hurdle Margin.
  - `constraints_satisfied: bool` — True if candidate satisfies all `PortfolioConstraints`.
  - `rank_score: Decimal` — Scalar comparative selection metric.
  - `evaluation_digest: str` — SHA-256 hash over evaluation payload.

### 2.7 `AllocationDecision` (Authoritative Capital Authorization)
- **Purpose:** Authoritative, governance-approved target portfolio allocation ready for rebalance planning.
- **Fields:**
  - `decision_id: str`
  - `selected_candidate_id: str`
  - `allocator_name: str`
  - `authorized_weights: Mapping[str, Decimal]` (Sum of weights + cash = 1.0 exactly)
  - `cash_weight: Decimal`
  - `authorization_timestamp: datetime` (UTC-aware)
  - `is_fallback_baseline: bool` — True if baseline was selected over advanced optimizer or forced by gate.
  - `gate_verdict: str` (`"AUTHORIZED"`, `"FORCED_CASH_RISK"`, `"FORCED_CASH_HURDLE"`, `"FORCED_CASH_DATA"`, `"FORCED_CASH_CONSTRAINT"`)
  - `rationale: str`
  - `decision_digest: str` — SHA-256 binding universe, candidate, evaluation, risk snapshot, and decision fields.
- **Invariants:** If `gate_verdict.startswith("FORCED_CASH")` $\implies w_{\text{cash}} = 1.0$ and $\forall i: w_i = 0.0$.

### 2.8 `RebalancePlan` (Portfolio Sizing & Execution Intent Interface)
- **Purpose:** Translation of `AllocationDecision` into desired portfolio position deltas and reference notional values.
- **Notional Semantics:** `desired_notional_delta` and `reference_prices` represent **portfolio sizing reference quantities at decision time**, **NOT execution prices**. Phase 8 does not own execution pricing or broker fill mechanics.
- **Phase 7 Boundary:** Phase 8 calculates desired position deltas ($\Delta q_i$). Phase 7 `ExecutionCoordinator` owns order type, TIF, live BBO price matching, broker transport wire dispatch, and authoritative fill reconciliation.
- **Fields:**
  - `plan_id: str`
  - `decision_id: str`
  - `as_of: datetime`
  - `current_weights: Mapping[str, Decimal]`
  - `target_weights: Mapping[str, Decimal]`
  - `desired_notional_delta: Mapping[str, Decimal]` ($\Delta D_i = D_{i, \text{target}} - D_{i, \text{current}}$, portfolio sizing reference)
  - `desired_position_delta: Mapping[str, Decimal]` ($\Delta q_i = q_{i, \text{target}} - q_{i, \text{current}}$, desired share change)
  - `reference_prices: Mapping[str, Decimal]` (Snapshot BBO mid-price reference at decision time)
  - `estimated_rebalance_friction: Decimal`
  - `plan_digest: str`

---

## 3. Four Core Architectural Boundaries & Governance Rules

### 3.1 Boundary 1: Candidate $\neq$ Evaluation $\neq$ Decision
$$\boxed{\text{AllocationCandidate (Proposal)} \longrightarrow \text{AllocationEvaluation (Scorecard)} \longrightarrow \text{AllocationDecision (Authority)}}$$
1. **Allocators propose weights:** An allocator is a mathematical transformation with zero authority to commit funds.
2. **Evaluators score candidates out-of-sample:** The `AllocationEvaluator` uses Phase 6 CPCV splits to compute out-of-sample metrics, friction, and `rank_score`.
3. **Governance Gate authorizes the decision:** The `PortfolioGovernanceGate` evaluates feasibility, risk limits, and hurdles.

### 3.2 Boundary 2: Ranking Metric $\neq$ Acceptance Gate
$$\boxed{\text{Top-Ranked Candidate } (\text{Rank \#1}) \quad \neq \quad \text{Authorized Decision}}$$
- A candidate may be ranked #1 by `rank_score` (e.g. high relative Sharpe), but **fail absolute hurdle or risk constraints** (e.g. expected net excess return $< 0$, or margin headroom insufficient).
- When the top-ranked candidate fails governance criteria, the gate **strictly defaults to 100% Cash**.

### 3.3 Boundary 3: Sovereign 100% Cash Decision ("NOWHERE")
100% Cash is an active, first-class decision outcome. It is triggered under three deterministic conditions:
1. **Pre-Allocation Risk Rejection:**
   - Kill Switch is active (`is_kill_switch_active == True`).
   - Account Drawdown $\ge$ `max_drawdown_limit_pct`.
   - Free Margin $<$ `margin_buffer_threshold`.
   - Data Health Failure ($T < T_{\text{min}}$, non-stationary flags, stale timestamps).
   $$\implies \text{Immediate Return: } \mathbf{w}^* = \mathbf{w}_{\text{cash}} = 1.0 \quad (\text{Verdict: } \texttt{FORCED\_CASH\_RISK})$$
2. **Post-Evaluation Hurdle Rejection:**
   - Best candidate net expected return fails hurdle rate:
     $$\mathbb{E}[R_p] - \mathcal{F} < r_f + \text{Hurdle Margin } H_0$$
   $$\implies \text{Immediate Return: } \mathbf{w}^* = \mathbf{w}_{\text{cash}} = 1.0 \quad (\text{Verdict: } \texttt{FORCED\_CASH\_HURDLE})$$
3. **Constraint / Infeasibility Rejection:**
   - Solver convergence failure or constraint violation across all candidates.
   $$\implies \text{Fallback: } \mathbf{w}^* = \mathbf{w}_{\text{cash}} = 1.0 \quad (\text{Verdict: } \texttt{FORCED\_CASH\_CONSTRAINT})$$

### 3.4 Boundary 4: Sovereign Baseline Preference
$$\boxed{\text{Rank Score}(\text{Baseline}) \ge \text{Rank Score}(\text{Advanced Optimizer}) \implies \text{SELECT BASELINE}}$$
ACASH never biases capital towards complexity. If naive Equal Weight ($1/N$) or Inverse Volatility ($1/\sigma$) produces equivalent or superior out-of-sample risk-adjusted net return after turnover costs, the system **MUST** select the baseline.

---

## 4. Estimation Mathematics, Hurdle Rate & RankScore

### 4.1 Separation of Expected Return and Covariance Estimators
To maintain strict mathematical discipline, Expected Return ($\boldsymbol{\mu}$) and Covariance ($\mathbf{\Sigma}$) estimation contracts are decoupled:

```
┌─────────────────────────────────────────────────────────────┐
│                 ESTIMATION CONTRACT LAYER                   │
├──────────────────────────────┬──────────────────────────────┤
│  EXPECTED RETURN (μ)         │  COVARIANCE MATRIX (Σ)       │
│  - Historical Sample Mean    │  - Empirical Sample Cov      │
│  - Empirical OOS Mean        │  - Ledoit-Wolf Shrinkage Cov │
│  - Explicit Unit/Horizon/T   │  - Well-conditioned (λ_min>0)│
└──────────────────────────────┴──────────────────────────────┘
```

1. **Expected Return Estimator (`ExpectedReturnEstimator`):**
   - Produces expected return vector $\boldsymbol{\mu} \in \mathbb{R}^N$.
   - **Contract Requirements:** Provenance, estimation horizon ($T$), return space (simple period returns), and annualization factor ($\sqrt{252}$ for daily) must be explicitly recorded in metadata.
   - *Note:* Ledoit-Wolf shrinkage is a covariance technique and is **NOT** an expected return estimator.
2. **Covariance Estimator (`CovarianceEstimator`):**
   - Produces symmetric positive semi-definite covariance matrix $\mathbf{\Sigma} \in \mathbb{R}^{N \times N}$.
   - **Canonical Methods:**
     - Empirical Sample Covariance: $\mathbf{\Sigma}_{\text{sample}} = \frac{1}{T-1} (\mathbf{R} - \bar{\mathbf{R}})^T (\mathbf{R} - \bar{\mathbf{R}})$.
     - Ledoit-Wolf Shrinkage Covariance: $\mathbf{\Sigma}_{\text{LW}} = \delta^* \mathbf{F} + (1 - \delta^*) \mathbf{\Sigma}_{\text{sample}}$ (where $\mathbf{F}$ is structured target and $\delta^*$ is optimal shrinkage intensity).

### 4.2 Portfolio-Level Hurdle Formulation
$$\text{Net Expected Portfolio Return } \mathbb{E}[R_p] = \mathbf{w}^T \boldsymbol{\mu} - \mathcal{F}(\mathbf{w}, \mathbf{w}_{\text{current}})$$

$$\text{Hurdle Condition: } \mathbb{E}[R_p] \ge r_f + \text{Hurdle Margin } H_0$$

Where:
- $\boldsymbol{\mu}$: Expected return vector from authorized `ExpectedReturnEstimator`.
- $r_f$: Risk-Free rate over horizon (e.g. US 3-Month T-Bill yield in identical annualization space).
- $H_0$: Non-negative hurdle margin (e.g. `Decimal("0.02")` annualized).
- $\mathcal{F}$: Rebalance friction penalty.

### 4.3 Turnover & Friction Model
$$\text{Turnover } \mathcal{T} = \frac{1}{2} \sum_{i=1}^N |w_{i, \text{target}} - w_{i, \text{current}}|$$

$$\mathcal{F} = \mathcal{T} \times \left( c_{\text{fee}} + \frac{\text{Spread}_{\text{bps}}}{2 \times 10^4} + \text{Slippage}_{\text{bps}} \right)$$

### 4.4 Canonical RankScore Formulation
The comparative ranking metric evaluates relative out-of-sample performance:

$$\text{Rank Score} = \text{Annualized Sharpe}(r_{\text{oos}}) - \lambda_{\text{TO}} \cdot \mathcal{T} - \lambda_{\text{Tail}} \cdot \text{CVaR}_{95}(r_{\text{oos}})$$

Where:
- $r_{\text{oos}}$: Out-of-sample return series aggregated across Phase 6 CPCV test folds.
- $\mathcal{T}$: Rebalance turnover required from current portfolio state.
- $\lambda_{\text{TO}}$: Turnover penalty coefficient (penalizes high-churn optimizers).
- $\lambda_{\text{Tail}}$: Tail risk penalty coefficient.
- **Deterministic Tie-Breaking:** If two candidates produce identical rank scores within numerical precision ($10^{-8}$), the simpler candidate is strictly selected:
  $$\text{CASH} > \text{EQUAL\_WEIGHT} > \text{INVERSE\_VOL} > \text{HRP} > \text{ERC} > \text{CVAR}$$

---

## 5. Allocator Interfaces & Extensions

### 5.1 Allocator Interface (`PortfolioAllocator`)
```python
class PortfolioAllocator(Protocol):
    @property
    def allocator_name(self) -> str: ...

    def compute_candidate(
        self,
        panel: AssetReturnPanel,
        constraints: PortfolioConstraints,
        current_weights: Mapping[str, Decimal],
    ) -> AllocationCandidate:
        """Compute candidate weight proposal in Decimal space. Fail-closed on invalid state."""
        ...
```

### 5.2 Mandatory Transparent Baselines (Level 1 Foundation)
1. **100% Cash (`CASH`):** $w_i = 0.0 \quad \forall i \in \mathcal{U}, \quad w_{\text{cash}} = 1.0$.
2. **Equal Weight ($1/N$) (`EQUAL_WEIGHT`):** $w_i = \frac{1.0 - B_{\text{cash}}}{N} \quad \forall i \in \mathcal{U}, \quad w_{\text{cash}} = B_{\text{cash}}$.
3. **Inverse Volatility ($1/\sigma$) (`INVERSE_VOL`):**
   $$w_i = (1.0 - B_{\text{cash}}) \cdot \frac{\frac{1}{\sigma_i}}{\sum_{j=1}^N \frac{1}{\sigma_j}}$$
   *Fail-Closed Contract:* If any $\sigma_i \le 0$ or undefined, raises `DataContractError` immediately (no magic floors).

### 5.3 Advanced Allocator Extension Points (Level 2 & Level 3)
1. **Hierarchical Risk Parity (`HRP` — Level 2):** Native Python/SciPy tree clustering and recursive bisection quasi-diagonalization.
2. **Equal Risk Contribution (`ERC` — Level 2):** Native cyclical coordinate descent equalizing marginal risk contributions: $w_i (\mathbf{\Sigma} \mathbf{w})_i = w_j (\mathbf{\Sigma} \mathbf{w})_j$.
3. **`skfolio` / CVXPY Adapters (Level 3 — Optional Extension Point):**
   - Minimum CVaR, CDaR, and Shrinkage Mean-Variance.
   - **Conditional Loading Policy:** Loaded only if `skfolio` is present in the environment. If absent, the core Portfolio Engine functions 100% on Baselines, HRP, and ERC without errors or warnings.

---

## 6. Phase 7 Execution Boundary Protection

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      PHASE 8: PORTFOLIO LAYER                           │
│  AllocationDecision -> RebalancePlan                                    │
│  - target_weights, current_weights                                      │
│  - desired_notional_delta (sizing reference)                            │
│  - desired_position_delta (Δq_i)                                        │
│  (Pure Mathematical Target Allocation; NO Order Execution Logic)        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼  [Desired Position Delta Intent]
┌─────────────────────────────────────────────────────────────────────────┐
│                      PHASE 7: EXECUTION LAYER                           │
│  ExecutionCoordinator -> BrokerAdapter -> Alpaca Paper / Venue Wire     │
│  (Order Type, TIF, Live BBO Routing, SSE Stream, Fills, Reconciliation) │
└─────────────────────────────────────────────────────────────────────────┘
```

1. **Phase 8 Ownership:** Calculates target portfolio weights, evaluates OOS risk/return, applies governance gates, and computes desired position delta ($\Delta q_i$) and notional sizing reference ($\Delta D_i$).
2. **Phase 7 Ownership:** Takes delta requests, constructs `OrderIntent`, selects order types (Market, Limit), validates market session (`/v2/clock`), executes across broker transport, normalizes SSE/REST fills, and verifies broker parity reconciliation.
3. **Invariant:** Phase 8 **NEVER** interacts directly with broker APIs, never handles SSE streams, and never mutates broker order state.

---

## 7. Summary Ledgers & Gate 8 Requirements

### 7.1 Verified Facts
1. Phase 7 is frozen at commit `a092b88` with verified Paper Checkpoint `P-001` ($P = 1$) and flat account.
2. Return Matrix $T \times N$ plus Risk Snapshot are sufficient input data for Phase 8. L2/L3 orderbook data is out-of-scope for portfolio allocation.
3. Core domain models (`PortfolioState`, `AccountState`) and pure transition mathematics are verified and reusable.
4. Python 3.14.3, NumPy 2.5.2, and SciPy 1.18.1 are available in the local environment.
5. Phase 6 CPCV, DSR, and Multiple Testing engines exist and are reusable for OOS candidate evaluation.

### 7.2 Unknowns / Open Items
1. Compatibility and solver stability of `skfolio` / `cvxpy` in Python 3.14.3 (will be tested in a dedicated read-only dependency spike prior to Level 3 development).
2. Production historical multi-asset return panel dataset availability and storage path for full-scale empirical studies.

### 7.3 Non-Blocking Future Capabilities
1. Intraday continuous multi-asset rebalancing feeds (Phase 10/12).
2. High-frequency microstructure alpha signal generation (Phase 14).
3. Non-linear derivatives / multi-currency cross-venue margin accounts.

### 7.4 Gate 8 Acceptance Criteria
Gate 8 will be accepted only when:
- [ ] 1. **Baseline Invariants Verified:** $1/N$, $1/\sigma$, and 100% Cash produce deterministic, closed-form numerical weights passing golden benchmarks.
- [ ] 2. **Sovereign Cash Gate Enforced:** Pre-allocation risk distress, margin deficiency, or post-evaluation hurdle shortfall forces 100% Cash deterministically.
- [ ] 3. **Candidate $\neq$ Decision Enforced:** No allocator can directly mutate portfolio state or create orders without governance approval.
- [ ] 4. **Ranking $\neq$ Approval Enforced:** Top-ranked candidate is rejected if it fails absolute hurdle or risk limits.
- [ ] 5. **Friction & Turnover Bound:** OOS selection penalizes turnover and selects simpler baselines when advanced optimizers overfit.
- [ ] 6. **Phase 7 Boundary Preserved:** `RebalancePlan` outputs desired position deltas and reference notionals; Phase 7 owns execution and reconciliation.
- [ ] 7. **Full Test Suite & Typing Clean:** 100% pass on all new unit/adversarial tests, full repository test suite (>= 610 tests), MyPy clean (0 new errors).
- [ ] 8. **Live Execution Remains HARD-LOCKED (OFF).**

### 7.5 Implementation Prerequisites (Order of Operations)
```text
1. Operator Sign-off on this Canonical Contract Draft
        ↓
2. Dedicated skfolio / CVXPY Compatibility Check (Read-Only Scratch Spike)
        ↓
3. Implementation Plan (docs/phase8/implementation_plan.md)
        ↓
4. Unit & Adversarial Tests First (TDD in tests/unit/portfolio/)
        ↓
5. Implement Domain Entities (src/acash/portfolio/schema.py)
        ↓
6. Implement Baseline Allocators (src/acash/portfolio/baselines.py)
        ↓
7. Implement Evaluation & Governance Gate (src/acash/portfolio/gate.py)
        ↓
8. Implement Rebalance Planner (src/acash/portfolio/planner.py)
        ↓
9. Full Test Suite & Verification Ledger Sign-off
```
