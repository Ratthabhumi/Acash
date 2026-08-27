# ACASH — Phase 4: Alpha Research Engine & Hypothesis Contract Design Proposal

**Document:** `docs/PHASE_4_DESIGN_PROPOSAL.md`  
**Version:** 1.0.0  
**Date:** 2026-08-28  
**Status:** **PROPOSED — AWAITING ARCHITECTURAL REVIEW & SIGN-OFF**  

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
                       │ - Falsification Criteria      │
                       │ - Lineage & Versioning        │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │   FORWARD OUTCOME ENGINE      │
                       │ - Exact Next-Bar Entry Rules  │
                       │ - Horizons H={1,5,15,60}      │
                       │ - Overlapping Variance Correc │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │    STATISTICAL EVALUATION     │
                       │ - Pearson IC & Rank IC        │
                       │ - Newey-West Adjusted t-Stats │
                       │ - Feature Decay Profiles      │
                       └───────────────┬───────────────┘
                                       │
                 ┌─────────────────────┴─────────────────────┐
                 ▼                                           ▼
      3-TIERED TRANSACTION COSTS                   MULTI-TESTING & OOS GATE
   - Raw Signal Edge                            - In-Sample (60%)
   - Half-Spread & Fee Net                      - Validation (20%)
   - Slippage & Latency Economic Edge           - Strict Held-Out OOS (20%)
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
> **Core Philosophy of Phase 4:**
> 1. **Alpha Research $\neq$ Strategy Backtesting:** Phase 4 does NOT search for profitable trading bots. It tests whether quantitative features contain **statistically significant, economically viable predictive information** before any strategy is formed.
> 2. **Pre-Registered Falsification:** Every hypothesis must declare explicit invalidation criteria *before* running evaluations. If the metric fails the threshold, the hypothesis is formally rejected.
> 3. **3-Tier Friction Realism:** No signal is considered viable based on raw returns. It must survive spread, execution fees, slippage, and latency penalties.

---

## 2. Formal Hypothesis Specification Contract

Every quantitative inquiry in ACASH must be formally registered as an immutable `HypothesisSpecification`:

```python
class ExpectedDirection(str, Enum):
    LONG = "LONG"          # Feature positively correlated with forward return (+1)
    SHORT = "SHORT"        # Feature negatively correlated with forward return (-1)
    DISPERSION = "DISPERSION" # Feature predicts volatility / magnitude rather than direction


class InvalidationCriteria(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    min_in_sample_rank_ic: Decimal = Field(default=Decimal("0.025"), ge=Decimal("0.0"))
    min_newey_west_t_stat: Decimal = Field(default=Decimal("2.00"), ge=Decimal("1.5"))
    max_feature_autocorrelation: Decimal = Field(default=Decimal("0.98"), le=Decimal("1.0"))
    min_cost_adjusted_spread_ratio: Decimal = Field(default=Decimal("1.50"), ge=Decimal("1.0"))


class HypothesisSpecification(BaseModel):
    """Formal, immutable pre-registered scientific hypothesis specification."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    hypothesis_id: str               # e.g. "HYP-001-OBI-SHORT-MOMENTUM-V1"
    hypothesis_version: str          # e.g. "1.0.0"
    parent_hypothesis_id: Optional[str] = None # Lineage tracking for iterations
    
    # Structural Economic Theory (Why does this anomaly exist?)
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

## 3. Forward Outcome & Temporal Alignment Contract

### 3.1 Exact Price Source & Entry/Exit Semantics
To prevent lookahead bias and unrealistic execution assumptions:

$$\text{Forward Return } R_{t, H} = \frac{P_{\text{exit}, t+H} - P_{\text{entry}, t}}{P_{\text{entry}, t}}$$

1. **Bar-Level Trade Features:**
   - **Signal Evaluation Time:** Bar $t$ Close ($T_{\text{decision}} = \text{bar\_end\_utc}_t$).
   - **Entry Price ($P_{\text{entry}, t}$):** Strictly evaluated at the **Next Bar Open** ($P_{\text{open}, t+1}$) or Bar $t$ Close with simulated entry latency:
     $$T_{\text{entry}} = T_{\text{decision}} + \tau_{\text{latency}}$$
   - **Exit Price ($P_{\text{exit}, t+H}$):** Evaluated at Bar $t+H$ Close ($P_{\text{close}, t+H}$).
2. **Tick/Order-Book Microstructure Features:**
   - **Entry Price:** Effective Ask for Buy / Effective Bid for Sell at $T_{\text{decision}} + \tau_{\text{latency}}$.
   - **Exit Price:** Effective Bid for Buy / Effective Ask for Sell at $T_{\text{decision}} + H \cdot \Delta t$.

### 3.2 Missing Labels & End-of-Session Behavior
- If bar $t+H$ exceeds the daily session boundary or contains missing data, $R_{t, H}$ evaluates to `None` (or null in Parquet) with status `INVALID_MISSING_FORWARD_BAR`.
- Missing labels are **strictly excluded** from correlation calculations, never imputed with zero or forward-filled.

### 3.3 Overlapping Horizons & Statistical Variance Correction
When evaluation horizon $H > 1$, forward returns $R_{t, H}$ and $R_{t+1, H}$ share $H-1$ overlapping bars, inducing artificial moving-average autocorrelation in residuals.
- **Mandatory Newey-West HAC Correction:** Standard errors of the mean IC must use the Newey-West kernel with lag truncation $L = H - 1$:

$$\sigma_{\text{HAC}}^2 = \hat{\gamma}_0 + 2 \sum_{l=1}^{H-1} \left(1 - \frac{l}{H}\right) \hat{\gamma}_l$$

$$t_{\text{stat, adjusted}} = \frac{\overline{\text{IC}}}{\sigma_{\text{HAC}} / \sqrt{N}}$$

---

## 4. Statistical Evaluation Metrics

### 4.1 Pearson IC vs. Spearman Rank IC
1. **Pearson Information Coefficient ($\text{IC}_{\text{linear}}$):**
   $$\text{IC}_{\text{linear}}(t, H) = \frac{\sum (X_i - \bar{X})(Y_{i, H} - \bar{Y}_H)}{\sqrt{\sum (X_i - \bar{X})^2 \sum (Y_{i, H} - \bar{Y}_H)^2}}$$
2. **Spearman Rank Information Coefficient ($\text{IC}_{\text{rank}}$):**
   $$\text{IC}_{\text{rank}}(t, H) = \text{PearsonCorrelation}\left(\text{rank}(X), \text{rank}(Y_H)\right)$$
   *(Robust against non-linear scaling and microstructure outliers).*
3. **Zero Variance & Constant Inputs:**
   If $\sigma(X) == 0$ or $\sigma(Y) == 0$, $\text{IC} = \text{None}$ with status `ZERO_VARIANCE`.

### 4.2 Feature Decay & Autocorrelation Profile
1. **Feature Autocorrelation:** $\rho(X_t, X_{t-k})$ for $k \in \{1, 5, 15, 60\}$ to measure signal persistence vs turnover.
2. **Decay Half-Life:** The horizon $H^*$ where $\text{IC}(H^*) \le 0.5 \times \text{IC}(1)$.

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

### 5.1 Cost Parameter Specifications
$$\text{Cost}_{\text{roundtrip}} = \frac{P_{\text{ask}} - P_{\text{bid}}}{P_{\text{mid}}} + 2 \cdot \text{Fee}_{\text{broker}} + \text{Slippage}_{\text{model}}(\text{Volume}, \text{Depth})$$

$$\text{Edge}_{\text{net}} = \mathbb{E}\left[ R_{\text{fwd}} \cdot \text{Signal} \right] - \text{Cost}_{\text{roundtrip}} \cdot |\text{Turnover}|$$

---

## 6. Multiple Testing & Out-of-Sample (OOS) Discipline

### 6.1 Strict 3-Way Temporal Partitioning
To eliminate data-snooping and overfitting:

```
├── In-Sample (IS: 60%) ──┤── Validation (VAL: 20%) ──┤── Held-Out Out-of-Sample (OOS: 20%) ──┤
│    Exploration & Fit    │   Parameter Selection     │      Locked Blind Final Gate          │
```

1. **In-Sample (IS - 60%):** Used for initial hypothesis exploration, IC calculation, and baseline fitting.
2. **Validation (VAL - 20%):** Used to test parameter sensitivity and select candidate configurations.
3. **Held-Out OOS (20%):** **Strictly locked.** Accessed exactly ONCE at formal Gate evaluation. Any re-tuning after looking at OOS immediately invalidates the research run.

### 6.2 Experiment Registry & Trial Lineage
Every query, test run, or parameter iteration produces an immutable `ResearchTrialRecord`:
- Logs total number of trials $K$ for Family-Wise Error Rate (FWER) and Deflated Sharpe Ratio (DSR) tracking.

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
- **Hand-calculated Pearson IC and Spearman Rank IC** on discrete 5-sample data vectors.
- **Hand-calculated Newey-West HAC variance** for 2-bar overlapping return sequences.
- **Hand-calculated 3-tier transaction cost adjustments**.

---

## 9. Research Manifest Specification (`ResearchManifest`)

```python
class ResearchManifest(BaseModel):
    """Immutable provenance record documenting complete research run lineage and results."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_id: str                 # e.g. "RES-MANIFEST-HYP001-20260828-ABC123"
    experiment_id: str
    hypothesis_id: str
    hypothesis_version: str
    symbol: str
    
    # Dataset Provenance
    input_feature_hashes: List[str]  # feature_output_sha256 from Phase 3C
    parameter_config_hash: str
    
    # Temporal Partitions
    in_sample_window: Tuple[str, str]
    validation_window: Tuple[str, str]
    oos_window: Tuple[str, str]
    
    # Statistical Results Summary
    in_sample_rank_ic: Decimal
    in_sample_t_stat: Decimal
    oos_rank_ic: Optional[Decimal]
    oos_t_stat: Optional[Decimal]
    tier3_economic_edge_bps: Decimal
    is_hypothesis_accepted: bool
    
    software_version: str
    computed_at_utc: str
```

---

## 10. Prohibited Anti-Patterns

1. **Lookahead Bias:** Using any information knowable after $T_{\text{decision}}$ to compute signals.
2. **Data Snooping / P-Hacking:** Running hundreds of parameter combinations and picking the best performing one without multiple-testing penalty.
3. **OOS Contamination:** Re-tuning parameters after observing poor OOS results.
4. **Frictionless Delusion:** Claiming alpha based on raw returns without deducting bid/ask spread, exchange fees, slippage, and execution latency.
5. **Backtest Over-Interpretation:** Treating a positive historical equity curve as mathematical proof of future profitability.

---

## 11. Gate 4 Acceptance Criteria & Verification Matrix

- [ ] **Hypothesis Specification Contract:** Formal Pydantic models enforcing pre-registered falsification criteria.
- [ ] **Hand-Calculated Golden Math:** 100% agreement between manual mathematical vectors and engine calculations for Forward Return, Pearson IC, Spearman Rank IC, Newey-West HAC t-stat, and 3-Tier Costs.
- [ ] **Next-Bar Entry Alignment:** Verifies signals at bar $t$ enter strictly at bar $t+1$ Open with zero lookahead.
- [ ] **Overlapping Horizon Correction:** Verifies Newey-West HAC adjusts variance correctly for $H > 1$.
- [ ] **3-Tier Cost Waterfall:** Verifies raw edge, net edge, and economic edge calculations under variable spread and fee configurations.
- [ ] **OOS Partition Discipline:** Verifies strict isolation of train, validation, and held-out OOS datasets.
- [ ] **ResearchManifest Reproducibility:** Recomputing research trials yields identical results and cryptographic fingerprints.
- [ ] **Zero Production Trading Logic Audit:** Confirms absence of live execution triggers or broker adapters.
- [ ] **Full Regression Suite:** 100% pytest pass rate (all 122 existing tests + Phase 4 tests), 0 mypy errors across all source files.
