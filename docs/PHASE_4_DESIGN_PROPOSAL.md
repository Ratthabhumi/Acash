# ACASH — Phase 4: Alpha Research Engine & Hypothesis Contract Design Proposal

**Document:** `docs/PHASE_4_DESIGN_PROPOSAL.md`  
**Version:** 1.1.0  
**Date:** 2026-08-28  
**Status:** **PROPOSED — METHODOLOGICAL REFINEMENTS (Awaiting Formal Sign-Off)**  

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
                       │ - Next-Bar Open Entry Rules   │
                       │ - Multi-Horizons H={1,5,15,60}│
                       │ - Purging & Embargo Boundaries│
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │    STATISTICAL EVALUATION     │
                       │ - Pearson IC & Rank IC        │
                       │ - Configurable HAC Inference  │
                       │ - Robustness Bandwidth Matrix │
                       └───────────────┬───────────────┘
                                       │
                 ┌─────────────────────┴─────────────────────┐
                 ▼                                           ▼
      3-TIERED TRANSACTION COSTS                   MULTI-TESTING & SEARCH REGISTRY
   - Tier 1: Raw Predictive Edge                - Parameter & Variant Accounting
   - Tier 2: Spread & Fee Net                   - Train / Val / Embargo / OOS Partitions
   - Tier 3: Slippage & Latency Economic Edge   - Blind OOS Exposure State Tracking
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
> 1. **Predictive Association (IC):** Quantifies whether a feature has non-random correlation with forward returns. It does NOT prove money can be extracted.
> 2. **Tradeable Economic Edge:** Quantifies whether predictive association survives roundtrip bid/ask spread, exchange fees, market impact slippage, and latency drag.
> 3. **Production Profitability:** Reserved for Phase 5+, subject to dynamic portfolio allocation, execution routing, and real-world infrastructure constraints.
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
    hypothesis_version: str          # e.g. "1.1.0"
    parent_hypothesis_id: Optional[str] = None # Lineage tracking for iterations
    
    # Structural Economic Theory (Why does this anomaly exist in market microstructure?)
    economic_rationale: str
    
    # Feature Dependencies & Target Instruments
    target_symbol: str
    feature_dependencies: List[str]  # e.g. ["obi_top5", "micro_price_skew"]
    parameter_config_json: str       # Exact parameters used in feature generation
    
    # Statistical Expectations
    expected_direction: ExpectedDirection
    target_horizons: List[int]       # e.g. [1, 5, 15, 60] bars
    primary_horizon: int             # e.g. 5 bars
    
    # Falsification Bounds
    invalidation_criteria: InvalidationCriteria
    
    registered_at_utc: str
    author: str
```

---

## 3. Forward Outcome, Temporal Purging & Embargo Contract

### 3.1 Exact Price Source & Entry/Exit Semantics
To prevent lookahead bias and unrealistic execution timing:

$$\text{Forward Return } R_{t, H} = \frac{P_{\text{exit}, t+H} - P_{\text{entry}, t}}{P_{\text{entry}, t}}$$

1. **Bar-Level Trade Features:**
   - **Signal Decision Time:** Bar $t$ Close ($T_{\text{decision}} = \text{bar\_end\_utc}_t$).
   - **Entry Price ($P_{\text{entry}, t}$):** Strictly evaluated at the **Next Bar Open** ($P_{\text{open}, t+1}$) or simulated with explicit execution latency:
     $$T_{\text{entry}} = T_{\text{decision}} + \tau_{\text{latency}}$$
   - **Exit Price ($P_{\text{exit}, t+H}$):** Evaluated at Bar $t+H$ Close ($P_{\text{close}, t+H}$).
2. **Missing Labels & End-of-Session Behavior:**
   - If bar $t+H$ exceeds the daily session boundary or contains missing data, $R_{t, H}$ evaluates to `None` (null in Parquet) with status `INVALID_MISSING_FORWARD_BAR`.
   - Missing labels are **strictly excluded** from correlation calculations, never imputed with zero or forward-filled.

---

### 3.2 Temporal Purging & Embargo Boundary Semantics
When evaluating forward horizons $H > 1$, overlapping label intervals span multiple bars. Without strict purging and embargoing, observations near partition boundaries leak information across Train, Validation, and OOS gates.

```
Train Interval                      Embargo          Validation Interval            Embargo        Held-Out OOS Interval
[T_train_start ─────── T_train_end] ──[H-bars]──►    [T_val_start ─────── T_val_end] ──[H-bars]──► [T_oos_start ─────── T_oos_end]
      │                                                     │                                            │
  (Purged if                                            (Purged if                                   (Strictly Blind
   Label > T_train_end)                                  Label > T_val_end)                           Evaluation Gate)
```

1. **Feature Interval:** $[T_{\text{feature\_start}}, T_{\text{decision}}]$
2. **Label Interval:** $[T_{\text{entry}}, T_{\text{exit}}]$, where $T_{\text{exit}} = T_{\text{entry}} + H \cdot \Delta t$
3. **Partition Intervals:**
   - $\text{Train Interval} = [T_{\text{train\_start}}, T_{\text{train\_end}}]$
   - $\text{Validation Interval} = [T_{\text{val\_start}}, T_{\text{val\_end}}]$
   - $\text{OOS Interval} = [T_{\text{oos\_start}}, T_{\text{oos\_end}}]$
4. **Purging Invariant:** Any training observation whose `label_interval` overlaps beyond $T_{\text{train\_end}}$ is **strictly purged** from the training set.
5. **Embargo Invariant:** An embargo window $\Delta T_{\text{embargo}} \ge \max(H) \cdot \Delta t + \tau_{\text{latency}}$ is inserted between partition boundaries to eliminate serial correlation leakage.

---

## 4. Statistical Evaluation & Configurable HAC Policy

### 4.1 Pearson IC vs. Spearman Rank IC
1. **Pearson Information Coefficient ($\text{IC}_{\text{linear}}$):** Linear correlation between continuous feature values and forward returns.
2. **Spearman Rank Information Coefficient ($\text{IC}_{\text{rank}}$):** Rank correlation between feature percentiles and forward return percentiles (robust against fat-tailed microstructure noise).
3. **Zero Variance & Constant Inputs:** If $\sigma(X) == 0$ or $\sigma(Y) == 0$, $\text{IC} = \text{None}$ with status `ZERO_VARIANCE`.
4. **Minimum Sample Requirement:** Minimum $N \ge 250$ valid non-overlapping equivalent observations per evaluation window.

---

### 4.2 Configurable HAC Estimator & Bandwidth Selection Policy

> [!IMPORTANT]
> **Methodological Invariant on HAC Inference:**
> Lag length $L = H - 1$ is a **baseline reference heuristic**, NOT a universal mathematical truth. In empirical finance, inference on overlapping returns is sensitive to predictor persistence, sample size, and bandwidth selection.

ACASH models HAC inference via a versioned, configurable **`HacInferencePolicy`**:

```python
class HacBandwidthMethod(str, Enum):
    FIXED_HORIZON_MINUS_ONE = "FIXED_HORIZON_MINUS_ONE" # Baseline: L = H - 1
    FIXED_LAG = "FIXED_LAG"                             # Explicit user-specified lag L
    NEWEY_WEST_PLUGIN = "NEWEY_WEST_PLUGIN"             # L = floor(4 * (T / 100)^(2/9))
    ANDREWS_AR1_PLUGIN = "ANDREWS_AR1_PLUGIN"           # Automatic AR(1) plug-in bandwidth


class HacInferencePolicy(BaseModel):
    """Configurable Heteroskedasticity and Autocorrelation Consistent (HAC) inference policy."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    bandwidth_method: HacBandwidthMethod = Field(default=HacBandwidthMethod.FIXED_HORIZON_MINUS_ONE)
    fixed_lag_value: Optional[int] = None
    kernel_type: str = Field(default="bartlett")        # "bartlett", "parzen", "quadratic_spectral"
    run_bandwidth_robustness_check: bool = Field(default=True)
    robustness_lags: List[int] = Field(default_factory=lambda: [1, 5, 10, 20])
```

- **Robustness Check Matrix:** When `run_bandwidth_robustness_check=True`, the engine reports t-statistics across multiple bandwidths to verify inference stability against kernel specification.

---

## 5. 3-Tiered Transaction Cost & Economic Feasibility Model

Every candidate signal is evaluated through a strict 3-tiered waterfall:

```
┌─────────────────────────────────────────────────────────────┐
│ TIER 1: RAW SIGNAL EDGE (Frictionless)                      │
│ E[R_fwd * Direction]                                        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 2: SPREAD & FEE ADJUSTED                               │
│ Raw Edge - (Quoted Spread / Price) - Exchange Roundtrip Fee │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 3: SLIPPAGE & LATENCY ADJUSTED (Economic Edge)         │
│ Net Edge - Market Impact(Size, Depth) - Latency Drag        │
└─────────────────────────────────────────────────────────────┘
```

```python
class CostModelConfig(BaseModel):
    """Versioned friction and execution cost configuration."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    quoted_spread_bps: Decimal = Field(default=Decimal("1.0"), ge=Decimal("0.0"))
    roundtrip_broker_fee_bps: Decimal = Field(default=Decimal("0.5"), ge=Decimal("0.0"))
    fixed_slippage_bps: Decimal = Field(default=Decimal("0.5"), ge=Decimal("0.0"))
    latency_delay_ms: int = Field(default=50, ge=0)
```

$$\text{Edge}_{\text{economic}} = \mathbb{E}\left[ R_{\text{fwd}} \cdot \text{Signal} \right] - \left( \text{Spread}_{\text{bps}} + \text{Fees}_{\text{bps}} + \text{Slippage}_{\text{bps}} \right) \cdot |\text{Turnover}|$$

---

## 6. Multiple Testing Accounting & Out-of-Sample (OOS) Discipline

### 6.1 Configurable Split Policy & Blind OOS Gate
- **Default Baseline:** 60% In-Sample (IS), 20% Validation (VAL), 20% Held-Out OOS.
- **Configurable Policy:** Split proportions and chronological partition dates are controlled via `SplitPolicy`.
- **Strict Blind OOS Invariant:**
  1. OOS data is evaluated strictly ONCE during final Gate verification.
  2. **Zero OOS Re-Tuning:** If an evaluation on OOS fails, the hypothesis is marked **REJECTED**. The OOS dataset must **NEVER** be used to retune parameters or refine the hypothesis and reported as untouched OOS.

```python
class OosExposureState(str, Enum):
    UNEXPOSED = "UNEXPOSED"             # OOS data never accessed
    EVALUATED_LOCKED = "EVALUATED_LOCKED" # OOS evaluated once; locked
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
   - Evaluates whether Top-$N$ OBI and Micro-Price skew predict 1-bar to 5-bar forward mid-price changes.
2. **Baseline 2: Session VWAP Mean Reversion:**
   - Evaluates whether price excursions beyond $\pm 2\sigma$ dispersion bands predict mean reversion to session VWAP.
3. **Baseline 3: Multi-Horizon Time-Series Momentum (TSMOM):**
   - Evaluates multi-horizon return momentum across $H \in \{5, 15, 60\}$ bars.

---

## 8. Golden Mathematical Reference Tests (Hand-Calculated Vectors)

To eliminate shared implementation bias between code and test suite:
- **Hand-calculated reference matrix** for 5-period forward returns with next-bar open entry.
- **Hand-calculated Pearson IC and Spearman Rank IC** on discrete numerical test vectors.
- **Hand-calculated Newey-West HAC variance** across baseline and custom bandwidths.
- **Hand-calculated 3-tier transaction cost adjustments**.

---

## 9. Research Manifest Specification (`ResearchManifest`)

```python
class ResearchManifest(BaseModel):
    """Immutable provenance record documenting complete research run lineage and results."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_id: str
    experiment_id: str
    hypothesis_id: str
    hypothesis_version: str
    symbol: str
    
    # Dataset Provenance
    input_feature_hashes: List[str]  # feature_output_sha256 from Phase 3C
    parameter_config_hash: str
    search_record_hash: str
    
    # Temporal Coordinates & Embargo
    train_window: Tuple[str, str]
    validation_window: Tuple[str, str]
    oos_window: Tuple[str, str]
    embargo_bars: int
    
    # Statistical Results Summary
    in_sample_rank_ic: Decimal
    in_sample_hac_t_stat: Decimal
    oos_rank_ic: Optional[Decimal]
    oos_hac_t_stat: Optional[Decimal]
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
- [ ] **Hand-Calculated Golden Math:** 100% agreement between manual mathematical vectors and engine calculations for Forward Return, Pearson IC, Spearman Rank IC, Newey-West HAC t-stat, and 3-Tier Costs.
- [ ] **Next-Bar Entry Alignment:** Verifies signals at bar $t$ enter strictly at bar $t+1$ Open with zero lookahead.
- [ ] **Temporal Purging & Embargo:** Verifies boundary label overlapping records are purged and embargo periods enforced.
- [ ] **Configurable HAC Inference:** Verifies bandwidth selection policy and robustness matrix calculation.
- [ ] **3-Tier Cost Waterfall:** Verifies raw edge, net edge, and economic edge calculations under variable spread and fee configurations.
- [ ] **Search Accounting & OOS Discipline:** Verifies `ResearchSearchRecord` tracks trial degrees of freedom and locks OOS exposure.
- [ ] **ResearchManifest Reproducibility:** Recomputing research trials yields identical results and cryptographic fingerprints.
- [ ] **Zero Production Trading Logic Audit:** Confirms absence of live execution triggers or broker adapters.
- [ ] **Full Regression Suite:** 100% pytest pass rate (all 122 existing tests + Phase 4 tests), 0 mypy errors across all source files.
