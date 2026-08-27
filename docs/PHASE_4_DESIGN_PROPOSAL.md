# ACASH — Phase 4: Alpha Research Engine & Hypothesis Contract Design Proposal

**Document:** `docs/PHASE_4_DESIGN_PROPOSAL.md`  
**Version:** 1.2.0  
**Date:** 2026-08-28  
**Status:** **PROPOSED — FINAL METHODOLOGICAL LOCK (Awaiting Formal Sign-Off)**  

---

## 1. Executive Summary & Epistemic Paradigm

In institutional quantitative finance, **the primary cause of failure is not computational error, but epistemic self-deception**: confusing statistical noise, data-snooping artifacts, or frictionless paper profits with genuine market alpha.

```
                           CANONICAL FEATURES (3C)
                                       │
                                       ▼ (PIT Stream)
                       ┌───────────────────────────────┐
                       │    FORMAL HYPOTHESIS SPEC     │
                       │ - Structural Economic Theory  │
                       │ - Pre-registered Falsification│
                       │ - Versioned Specification     │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │    FORWARD OUTCOME ENGINE     │
                       │ - Discrete Bar Index Horizon  │
                       │ - Next-Bar Open Entry Price   │
                       │ - Purging & Embargo Windows   │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │    STATISTICAL EVALUATION     │
                       │ - Primary: OLS Beta HAC Infer │
                       │ - Association: Pearson/Rank IC│
                       │ - Bandwidth Robustness Matrix │
                       └───────────────┬───────────────┘
                                       │
                 ┌─────────────────────┴─────────────────────┐
                 ▼                                           ▼
      3-TIERED TRANSACTION COSTS                   MULTI-TESTING & SEARCH REGISTRY
   - Tier 1: Raw Predictive Edge                - Search Degrees of Freedom Record
   - Tier 2: Spread & Fee Net                   - Train / Val / Embargo / OOS Partitions
   - Tier 3: Slippage & Latency Economic Edge   - Blind OOS State Machine
                 │                                           │
                 └─────────────────────┬─────────────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │    RESEARCH MANIFEST &        │
                       │  REPRODUCIBILITY LEDGER       │
                       └───────────────────────────────┘
```

> [!IMPORTANT]
> **Strict Epistemic Distinctions in Phase 4:**
> 
> $$\text{Predictive Statistical Association (IC)} \quad \not\equiv \quad \text{Tradeable Economic Edge (Net Alpha)} \quad \not\equiv \quad \text{Production Profitability (Live Strategy)}$$
> 
> 1. **Predictive Association (IC / $\hat{\beta}_H$):** Quantifies whether a feature has non-random correlation with forward returns. It does NOT prove money can be extracted.
> 2. **Tradeable Economic Edge:** Quantifies whether predictive association survives roundtrip bid/ask spread, exchange fees, execution slippage, and latency drag.
> 3. **Production Profitability:** Reserved for Phase 5+, subject to dynamic portfolio optimization, execution routing, and real-world infrastructure constraints.
> 4. **Alpha Research $\neq$ Strategy Backtesting:** Phase 4 does NOT search for profitable trading bots. It tests whether quantitative features contain **statistically significant, economically viable predictive information** before any strategy is formed.

---

## 2. Formal Hypothesis Specification Contract

Every quantitative inquiry in ACASH must be formally registered as an immutable `HypothesisSpecification` with pre-declared falsification criteria:

```python
class ExpectedDirection(str, Enum):
    LONG = "LONG"          # Feature positively correlated with forward return (+1)
    SHORT = "SHORT"        # Feature negatively correlated with forward return (-1)
    DISPERSION = "DISPERSION" # Feature predicts volatility / magnitude rather than direction


class InvalidationCriteria(BaseModel):
    """Pre-registered statistical falsification criteria."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    min_in_sample_rank_ic: Decimal = Field(default=Decimal("0.025"), ge=Decimal("0.0"))
    min_hac_t_stat: Decimal = Field(default=Decimal("2.00"), ge=Decimal("1.5"))
    max_feature_autocorrelation: Decimal = Field(default=Decimal("0.98"), le=Decimal("1.0"))
    min_cost_adjusted_spread_ratio: Decimal = Field(default=Decimal("1.50"), ge=Decimal("1.0"))


class HypothesisSpecification(BaseModel):
    """Formal, immutable pre-registered scientific hypothesis specification."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    hypothesis_id: str               # e.g. "HYP-001-OBI-SHORT-MOMENTUM-V1"
    hypothesis_version: str          # e.g. "1.2.0"
    parent_hypothesis_id: Optional[str] = None # Lineage tracking for iterations
    
    # Structural Economic Theory (Why does this anomaly exist in market microstructure?)
    economic_rationale: str
    
    # Feature Dependencies & Target Instruments
    target_symbol: str
    feature_dependencies: List[str]  # e.g. ["obi_top5", "micro_price_skew"]
    parameter_config_json: str       # Exact parameters used in feature generation
    
    # Statistical Expectations
    expected_direction: ExpectedDirection
    target_horizons: List[int]       # Discrete bar horizons e.g. [1, 5, 15, 60]
    primary_horizon: int             # e.g. 5 bars
    
    # Falsification Bounds
    invalidation_criteria: InvalidationCriteria
    
    registered_at_utc: str
    author: str
```

---

## 3. Forward Outcome, Temporal Purging & Embargo Contract

### 3.1 Exact Price Source & Bar-Indexed Return Semantics
To eliminate off-by-one timing ambiguities, forward horizons are defined strictly by **Discrete Bar Index ($t$)**, not wall-clock duration:

1. **Discrete Bar Coordinates:**
   - **Signal Evaluation Time:** Bar $t$ Close ($T_{\text{decision}} = \text{bar\_end\_utc}_t$).
   - **Entry Bar:** Bar $t + 1$ (Evaluated strictly at **Next Bar Open**: $P_{\text{entry}, t} = P_{\text{open}, t+1}$, timestamp $T_{\text{open}, t+1}$).
   - **Exit Bar:** Bar $t + H$ (Evaluated strictly at **Horizon Close**: $P_{\text{exit}, t+H} = P_{\text{close}, t+H}$, timestamp $T_{\text{close}, t+H}$).
2. **Exact Forward Return Formula:**
   $$R(t, H) = \frac{P_{\text{close}, t+H} - P_{\text{open}, t+1}}{P_{\text{open}, t+1}}$$
3. **Exact Label Interval:**
   $$\text{label\_interval}(t, H) = \left[ T_{\text{open}, t+1}, \; T_{\text{close}, t+H} \right]$$
4. **Missing Labels & End-of-Session Behavior:**
   - If bar $t+H$ exceeds the trading session or bar sequence contains gaps/missing bars, $R(t, H)$ evaluates to `None` (null in Parquet) with status `INVALID_MISSING_FORWARD_BAR`.
   - Missing labels are **strictly excluded** from correlation calculations, never imputed with zero or forward-filled.

---

### 3.2 Temporal Purging & Embargo Boundary Semantics
When evaluating forward horizons $H > 1$, overlapping label intervals span multiple bars.

```
Train Interval                      Embargo Window       Validation Interval            Embargo Window       Held-Out OOS Interval
[T_train_start ─────── T_train_end] ──[H-bars Buffer]──► [T_val_start ─────── T_val_end] ──[H-bars Buffer]──► [T_oos_start ─────── T_oos_end]
      │                                                        │                                              │
  (Purged if                                               (Purged if                                     (Strictly Blind
   Label > T_train_end)                                     Label > T_val_end)                             Evaluation Gate)
```

1. **Purging Definition & Invariant:**
   - Any training observation whose `label_interval` ($[T_{\text{open}, t+1}, T_{\text{close}, t+H}]$) extends beyond $T_{\text{train\_end}}$ is **strictly purged** from the training set to prevent cross-boundary outcome leakage.
2. **Embargo Definition & Invariant:**
   - An unallocated embargo window $\Delta T_{\text{embargo}} \ge \max(H) \text{ bars}$ is inserted after the end of Train before Validation begins, and after Validation before OOS begins.
3. **Methodological Scope of Embargo:**
   - Purging and Embargo **reduce boundary contamination** caused by overlapping labels and dependent observations across partition splits.
   - Embargo does **NOT** eliminate serial correlation within the time series. Residual autocorrelation and serial dependence are handled by the specified **HAC inference estimator**.

---

## 4. Statistical Inference Estimator & Configurable HAC Policy

### 4.1 Primary Statistical Inference Estimator
To avoid ambiguity between descriptive association metrics and formal hypothesis testing, ACASH defines the primary regression model:

$$R(t, H) = \alpha_H + \beta_H X_t + \epsilon_t$$

Where:
- $X_t$: The normalized feature value or standardized percentile at decision bar $t$.
- $R(t, H)$: The discrete forward return from bar $t+1$ Open to bar $t+H$ Close.
- $\hat{\beta}_H$: The estimated predictive slope coefficient:
  $$\hat{\beta}_H = \frac{\sum_{t=1}^N (X_t - \bar{X})(R(t, H) - \bar{R})}{\sum_{t=1}^N (X_t - \bar{X})^2}$$

### 4.2 HAC Variance and Test Statistics
The variance of $\hat{\beta}_H$ is evaluated using Heteroskedasticity and Autocorrelation Consistent (HAC) covariance:

$$\widehat{\text{Var}}_{\text{HAC}}(\hat{\beta}_H) = (X'X)^{-1} \hat{\Omega}_{\text{HAC}} (X'X)^{-1}$$

$$\hat{\Omega}_{\text{HAC}} = \hat{\Gamma}_0 + \sum_{l=1}^L w(l, L) \left( \hat{\Gamma}_l + \hat{\Gamma}_l' \right)$$

$$\text{SE}_{\text{HAC}}(\hat{\beta}_H) = \sqrt{\widehat{\text{Var}}_{\text{HAC}}(\hat{\beta}_H)}, \quad t_{\text{stat, HAC}} = \frac{\hat{\beta}_H}{\text{SE}_{\text{HAC}}(\hat{\beta}_H)}, \quad p_{\text{value}} = 2 \cdot \left( 1 - \Phi(|t_{\text{stat, HAC}}|) \right)$$

### 4.3 Descriptive Association Statistics
Alongside formal regression inference, the engine reports standard non-parametric metrics:
1. **Pearson Information Coefficient ($\text{IC}_{\text{linear}}$):** Linear sample correlation $\rho(X_t, R(t, H))$.
2. **Spearman Rank Information Coefficient ($\text{IC}_{\text{rank}}$):** Rank sample correlation $\rho(\text{rank}(X_t), \text{rank}(R(t, H)))$.
3. **Zero Variance Handling:** If $\sigma(X) == 0$ or $\sigma(R) == 0$, $\text{IC} = \text{None}$ with status `ZERO_VARIANCE`.
4. **Minimum Sample Requirement:** Minimum $N \ge 250$ valid non-overlapping equivalent observations per evaluation window.

---

### 4.4 Configurable HAC Estimator & Bandwidth Policy

```python
class HacBandwidthMethod(str, Enum):
    FIXED_HORIZON_MINUS_ONE = "FIXED_HORIZON_MINUS_ONE" # Baseline heuristic: L = H - 1
    FIXED_LAG = "FIXED_LAG"                             # Explicit user-specified lag L
    NEWEY_WEST_PLUGIN = "NEWEY_WEST_PLUGIN"             # L = floor(4 * (T / 100)^(2/9))
    ANDREWS_AR1_PLUGIN = "ANDREWS_AR1_PLUGIN"           # Automatic AR(1) plug-in bandwidth


class HacInferencePolicy(BaseModel):
    """Configurable HAC inference policy with robustness check matrix."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    bandwidth_method: HacBandwidthMethod = Field(default=HacBandwidthMethod.FIXED_HORIZON_MINUS_ONE)
    fixed_lag_value: Optional[int] = None
    kernel_type: str = Field(default="bartlett")        # "bartlett", "parzen", "quadratic_spectral"
    run_bandwidth_robustness_check: bool = Field(default=True)
    robustness_lags: List[int] = Field(default_factory=lambda: [1, 5, 10, 20])
```

- **Robustness Check Matrix:** When `run_bandwidth_robustness_check=True`, the engine calculates and reports $t_{\text{stat, HAC}}$ across multiple lag bandwidths to verify inference stability against kernel specification.

---

## 5. 3-Tiered Transaction Cost & Economic Feasibility Model

Every candidate signal is evaluated through a dimensionally explicit 3-tiered waterfall:

```
┌─────────────────────────────────────────────────────────────┐
│ TIER 1: RAW SIGNAL EDGE (Frictionless)                      │
│ E[R(t, H) * Signal_t]                                       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 2: SPREAD & FEE ADJUSTED                               │
│ Raw Edge - (Quoted Spread + Roundtrip Fees)                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 3: SLIPPAGE & LATENCY ADJUSTED (Economic Edge)         │
│ Net Edge - Fixed Slippage Proxy - Latency Drag              │
└─────────────────────────────────────────────────────────────┘
```

### 5.1 Dimensionally Explicit Conversion & Parameters
Basis points ($\text{bps}$) are converted to decimal return units via:

$$\text{Cost}_{\text{decimal}} = \frac{\text{Cost}_{\text{bps}}}{10{,}000}$$

```python
class CostModelConfig(BaseModel):
    """Versioned friction and execution cost configuration."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    quoted_spread_bps: Decimal = Field(default=Decimal("1.0"), ge=Decimal("0.0"))
    roundtrip_broker_fee_bps: Decimal = Field(default=Decimal("0.5"), ge=Decimal("0.0"))
    fixed_slippage_bps: Decimal = Field(default=Decimal("0.5"), ge=Decimal("0.0"))
    latency_delay_ms: int = Field(default=50, ge=0)
```

- **Spread Convention:** `quoted_spread_bps` is defined as the **full roundtrip quoted bid-ask spread** in basis points ($10{,}000 \times \frac{P_{\text{ask}} - P_{\text{bid}}}{P_{\text{mid}}}$).
- **Roundtrip Fee:** `roundtrip_broker_fee_bps` covers both entry and exit exchange/clearing fees.
- **Phase 4 Slippage Scope:** Phase 4 models execution friction via a **fixed slippage proxy** (`fixed_slippage_bps`) and **latency delay** (`latency_delay_ms`). Non-linear dynamic market impact modeling ($f(\text{size}, \text{book\_depth})$) is explicitly deferred to Phase 5/10.

$$\text{Cost}_{\text{roundtrip, decimal}} = \frac{\text{quoted\_spread\_bps} + \text{roundtrip\_broker\_fee\_bps} + \text{fixed\_slippage\_bps}}{10{,}000}$$

$$\text{Edge}_{\text{economic}} = \mathbb{E}\left[ R(t, H) \cdot \text{Signal}_t \right] - \text{Cost}_{\text{roundtrip, decimal}} \cdot |\text{Turnover}|$$

---

## 6. Multiple Testing Accounting & Out-of-Sample (OOS) Discipline

### 6.1 Configurable Split Policy & Blind OOS State Machine
- **Default Baseline Split Policy:** 60% In-Sample (IS), 20% Validation (VAL), 20% Held-Out OOS.
- **Strict Blind OOS Governance:**
  1. OOS dataset is evaluated strictly ONCE during final Gate verification.
  2. **Zero OOS Re-Tuning:** If an evaluation on OOS fails, the hypothesis is marked **REJECTED**. The OOS dataset must **NEVER** be used to retune parameters or refine the hypothesis and reported as untouched OOS.

```
UNEXPOSED ──► EVALUATED_LOCKED ──► EXHAUSTED (if re-tuned)
```

```python
class OosExposureState(str, Enum):
    UNEXPOSED = "UNEXPOSED"             # OOS data never accessed
    EVALUATED_LOCKED = "EVALUATED_LOCKED" # OOS evaluated once; permanently locked
    EXHAUSTED = "EXHAUSTED"             # OOS compromised/spent
```

---

### 6.2 Full Search & Multiple-Testing Accounting (`ResearchSearchRecord`)
To prevent unrecorded degrees of freedom (p-hacking / data mining), the engine tracks all research trials:

```python
class ResearchSearchRecord(BaseModel):
    """Comprehensive accounting of research search space and multiple-testing exposure."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    experiment_id: str
    hypothesis_id: str
    
    # Degrees of Freedom Tracking
    parameter_variants_count: int
    feature_variants_tried: List[str]
    label_variants_tried: List[str]
    model_variants_tried: List[str]
    dataset_window_variants_tried: List[str]
    
    # Selection Governance
    selection_procedure: str            # e.g. "max_in_sample_rank_ic"
    selected_candidate_id: str
    total_effective_trials: int
    oos_exposure_state: OosExposureState
```

---

## 7. Baseline Research Strategies (Evaluation Vehicles Only)

These strategies serve strictly as transparent vehicles to benchmark feature predictive value. **Zero production trading logic.**

1. **Baseline 1: Microstructure Imbalance & Micro-Price Alpha:**
   - Evaluates whether Top-$N$ OBI and Micro-Price skew predict discrete forward returns across $H \in \{1, 5\}$ bars.
2. **Baseline 2: Session VWAP Mean Reversion:**
   - Evaluates whether price excursions beyond $\pm 2\sigma$ dispersion bands predict discrete mean reversion across $H \in \{5, 15\}$ bars.
3. **Baseline 3: Multi-Horizon Time-Series Momentum (TSMOM):**
   - Evaluates multi-horizon return momentum across $H \in \{5, 15, 60\}$ bars.

---

## 8. Golden Mathematical Reference Tests (Hand-Calculated Vectors)

To eliminate shared implementation bias between code and test suite:
- **Hand-calculated reference matrix** for 5-period discrete forward returns with next-bar open entry.
- **Hand-calculated OLS slope $\hat{\beta}_H$ and HAC standard errors** on discrete numerical test vectors.
- **Hand-calculated Pearson IC and Spearman Rank IC** on discrete test vectors.
- **Hand-calculated 3-tier transaction cost adjustments** with explicit decimal basis point conversions.

---

## 9. Complete Research Manifest Protocol (`ResearchManifest`)

Every research trial produces an immutable `ResearchManifest` from which the complete evaluation protocol can be fully reconstructed:

```python
class ResearchManifest(BaseModel):
    """Immutable provenance record documenting complete research run lineage and results."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_id: str
    experiment_id: str
    hypothesis_id: str
    hypothesis_version: str
    symbol: str
    
    # Protocol & Estimator Lineage
    inference_estimator: str             # e.g. "OLS_SLOPE_BETA_HAC"
    forward_return_definition: str       # e.g. "NEXT_BAR_OPEN_TO_HORIZON_CLOSE_V1"
    hac_bandwidth_method: str            # e.g. "FIXED_HORIZON_MINUS_ONE"
    hac_bandwidth_value: int             # e.g. 4
    hac_kernel: str                      # e.g. "bartlett"
    cost_model_version: str              # e.g. "3_TIER_FIXED_PROXY_V1"
    purging_policy_version: str          # e.g. "LABEL_INTERVAL_PURGING_V1"
    embargo_policy_version: str          # e.g. "MAX_HORIZON_EMBARGO_V1"
    
    # Cryptographic Provenance
    input_feature_hashes: List[str]      # feature_output_sha256 from Phase 3C
    parameter_config_hash: str
    search_record_hash: str
    
    # Temporal Partitions & Embargo
    train_window: Tuple[str, str]
    validation_window: Tuple[str, str]
    oos_window: Tuple[str, str]
    embargo_bars: int
    purged_train_rows_count: int
    
    # Statistical Results Summary
    in_sample_beta: Decimal
    in_sample_hac_t_stat: Decimal
    in_sample_rank_ic: Decimal
    oos_beta: Optional[Decimal]
    oos_hac_t_stat: Optional[Decimal]
    oos_rank_ic: Optional[Decimal]
    tier3_economic_edge_bps: Decimal
    is_hypothesis_accepted: bool
    oos_exposure_state: OosExposureState
    
    software_version: str
    computed_at_utc: str
```

---

## 10. Prohibited Anti-Patterns

1. **Lookahead Bias:** Using any information knowable after $T_{\text{decision}}$ to compute signals.
2. **Data Snooping / P-Hacking:** Running multiple trials and picking the best performing configuration without search accounting.
3. **OOS Contamination & Re-cycling:** Re-tuning parameters after observing poor OOS results.
4. **Boundary Leakage:** Failing to purge overlapping label intervals or apply embargoes between train and validation.
5. **Frictionless Delusion:** Claiming alpha based on raw returns without deducting spread, fees, slippage, and latency.
6. **Backtest Over-Interpretation:** Treating a positive historical backtest as proof of alpha.

---

## 11. Gate 4 Acceptance Criteria & Verification Matrix

- [ ] **Hypothesis Specification Contract:** Formal Pydantic models enforcing pre-registered falsification criteria.
- [ ] **Hand-Calculated Golden Math:** 100% agreement between manual mathematical vectors and engine calculations for Discrete Forward Return, OLS Slope $\hat{\beta}_H$, HAC t-stat, Pearson IC, Spearman Rank IC, and 3-Tier Costs.
- [ ] **Discrete Bar-Indexed Alignment:** Verifies signals at bar $t$ enter strictly at bar $t+1$ Open with zero lookahead.
- [ ] **Temporal Purging & Embargo:** Verifies boundary label overlapping records are purged and embargo periods enforced.
- [ ] **Configurable HAC Inference:** Verifies bandwidth selection policy and robustness matrix calculation.
- [ ] **Dimensionally Explicit 3-Tier Costs:** Verifies raw edge, net edge, and economic edge calculations under variable spread and fee configurations.
- [ ] **Search Accounting & Blind OOS State Machine:** Verifies `ResearchSearchRecord` tracks trial degrees of freedom and locks OOS exposure (`UNEXPOSED` $\to$ `EVALUATED_LOCKED`).
- [ ] **ResearchManifest Reproducibility:** Recomputing research trials yields identical results and cryptographic fingerprints.
- [ ] **Zero Production Trading Logic Audit:** Confirms absence of live execution triggers or broker adapters.
- [ ] **Full Regression Suite:** 100% pytest pass rate (all 122 existing tests + Phase 4 tests), 0 mypy errors across all source files.
