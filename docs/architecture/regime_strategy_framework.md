# ACASH Quantitative Market State & Regime-Strategy Framework
## Multi-Dimensional Market State Modeling, Price Structure Feature Engineering & Strategy × Regime Governance

> **Document ID:** `ACASH-SPEC-REGIME-STRATEGY-v1.0`  
> **Status:** Approved Architecture Specification (Phase 17 Rev 4.1)  
> **Parent Governance:** ADR-022 (Market-Adaptive Trading Governance), ADR-023 (Strategy Admission & Bounded Allocation)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Evidence > Belief)  
> **Date:** 2026-09-04  
> **Version:** 1.0.0  

---

> [!IMPORTANT]
> **GOVERNANCE DEMARCATION:**
> - This specification defines data contracts, feature engineering mathematics, and governance models.
> - **THIS SPECIFICATION DOES NOT IMPLEMENT AN AUTONOMOUS LIVE REGIME-SWITCHING ENGINE.** (Production empirical regime detection engines belong to **Phase 19**).
> - Live capital authority remains strictly `$0.00`.

---

## 1. Executive Summary & Quant Candlestick Architecture

A fundamental tenet of the ACASH quantitative engine is that **Quants do observe candle and bar representations, but not as subjective graphical patterns** (e.g. "hammer", "pin bar"). To ACASH, a candlestick bar is a structured, timestamped numerical vector of market observations:

$$\text{Bar}(t) = \big(\text{Open}, \text{High}, \text{Low}, \text{Close}, \text{Tick Volume}, \text{Real Volume}, \text{Spread}\big)$$

These raw observations are mathematically mapped into continuous geometric and structural features:
$$\begin{aligned}
\text{Body/Range Ratio} &= \frac{|\text{Close} - \text{Open}|}{\text{High} - \text{Low}} \in [0.0, 1.0] \\
\text{Wick Asymmetry} &= \frac{\text{Upper Wick} - \text{Lower Wick}}{\text{High} - \text{Low}} \in [-1.0, 1.0] \\
\text{Close Location} &= \frac{\text{Close} - \text{Low}}{\text{High} - \text{Low}} \in [0.0, 1.0] \\
\text{Range / ATR Ratio} &= \frac{\text{High} - \text{Low}}{\text{ATR}_{20}(t)} \\
\text{Gap Ratio} &= \frac{\text{Open}(t) - \text{Close}(t-1)}{\text{ATR}_{20}(t)}
\end{aligned}$$

> [!CAUTION]
> **MANDATORY GOVERNANCE INVARIANT: CANDLE-DERIVED FEATURES $\neq$ TRADING SIGNALS**  
> Candle-derived geometric metrics are market observations/features. They are **never** inherent trading signals. ACASH strictly prohibits discretionary visual pattern-matching (e.g. "Hammer detected $\to$ BUY"). Features feed the upstream feature engineering layer to form the `MarketStateVector`.

---

## 2. The Multi-Tier Quantitative Data Hierarchy

```
                 RAW MARKET DATA
                        │
        ┌───────────────┼────────────────┐
        │               │                │
      OHLCV         TICK/QUOTE       EVENT DATA
        │               │                │
        └───────────────┼────────────────┘
                        │
                        ▼
              FEATURE ENGINEERING
                        │
        ┌───────────────┼─────────────────────┐
        │               │                     │
 Price Structure   Market Dynamics      Microstructure
        │               │                     │
        ├─ Returns      ├─ Trend              ├─ Spread
        ├─ Range        ├─ Momentum           ├─ Liquidity
        ├─ Body/Wick    ├─ Volatility         ├─ Depth
        ├─ Geometry     ├─ Volume             ├─ Order Flow
        ├─ Gap          └─ Correlation        └─ Execution Latency
        └─ Expansion
                        │
                        ▼
               MARKET STATE VECTOR
              + DATA PROVENANCE
                        │
                        ▼
              REGIME CLASSIFICATION
              + CONFIDENCE & UNCERTAINTY
                        │
                        ▼
               STRATEGY × REGIME
              CONDITIONAL EVIDENCE
                        │
                        ▼
                ADMISSION & RISK
```

### 2.1 Fast vs. Slow Strategy Data Requirements
- **Slow Strategies (H1, H4, D1):** OHLCV, normalized returns, realized volatility, ATR, and macro correlation are often sufficient.
- **Execution-Sensitive / Microstructure Strategies (Scalping, Market Making, Arbitrage):** Require tick-level bid/ask, instantaneous spread, order book depth (L2), order flow delta, and execution latency telemetry.

### 2.2 MT5 Volume Provenance Discipline
In MetaTrader 5, `MqlRates` provides distinct fields:
- `tick_volume`: Count of price changes received during the bar.
- `real_volume`: Number of actual traded contracts or lots (available on centralized exchanges or certain ECN feeds).
- `spread`: Instantaneous spread in points.

ACASH enforces the `VolumeType` enum:
- `TICK_VOLUME`: OTC broker tick counts (not actual traded volume).
- `REAL_VOLUME`: Verified broker/exchange volume.
- `EXCHANGE_VOLUME`: Centralized exchange match volume.
- `UNKNOWN`: Unverified or synthetic volume.

---

## 3. Decoupling Continuous Measurements from Discrete Interpretations

ACASH maintains a strict architectural separation:

$$\boxed{\text{MarketStateVector (Continuous Measurements)} \quad \neq \quad \text{RegimeClassificationEstimate (Discrete Interpretation)}}$$

### 3.1 MarketStateVector (Continuous Measurements Only)
The `MarketStateVector` is an immutable, strictly numerical DTO containing zero regime labels:
```python
class MarketStateVector(BaseModel):
    provenance: DataProvenance
    price_structure: PriceStructureMeasurements
    market_dynamics: MarketDynamicsMeasurements
    microstructure: MicrostructureMeasurements
```
It records empirical reality (e.g. `realized_volatility = 0.0085`, `spread_bps = 2.1`, `trend_intensity = 0.74`). It does not assert whether the market is "BULLISH" or "CRISIS".

### 3.2 RegimeClassificationEstimate (Interpretation & Uncertainty)
The classification engine takes the `MarketStateVector` as input and produces an interpretation DTO:
```python
class RegimeClassificationEstimate(BaseModel):
    status: ClassificationStatus          # CLASSIFIED | UNCLASSIFIED | INSUFFICIENT_EVIDENCE
    confidence_score: Decimal             # 0.0 to 1.0
    confidence_assessment: ConfidenceAssessment # ACCEPTABLE | LOW
    provisional_label: str                # e.g. "TREND_HIGH_VOL" (provisional research label)
    probabilities: Mapping[str, Decimal]  # Probability distribution across candidate states
    threshold_provenance: ParameterProvenance # Provenance of confidence thresholds
```

---

## 4. Regime Classification Methodology & Uncertainty Governance

### 4.1 Candidate Classification Approaches
ACASH evaluates regime classification candidates based on empirical rigor, lag, and stability:
1. **Rule-Based State Boundaries:** Fixed thresholds on volatility and trend metrics. Highly interpretable; vulnerable to parameter rigidity.
2. **Statistical Clustering (k-Means, GMM):** Unsupervised grouping of continuous feature vectors. Adaptive; vulnerable to cluster instability and label drift.
3. **Hidden Markov Models (HMM):** Probabilistic transitions between latent states. Captures regime persistence; vulnerable to overfitting and state-label ambiguity.
4. **Supervised Regime Classifiers:** Machine-learning models trained on historical economic eras.

> [!IMPORTANT]
> **Provisional Taxonomy Invariant:**  
> Concrete regime taxonomies (e.g. "TRENDING_HIGH_VOL", "RANGE_LOW_VOL") are **provisional research hypotheses**. Formal empirical validation of regime models belongs to **Phase 19**.

### 4.2 Handling Uncertainty and Low Confidence
1. **`INSUFFICIENT_EVIDENCE`:** Emitted when lookback windows are incomplete, data feeds are disrupted, or observations are sparse. Fails closed immediately to **$0.00 capital allocation / observe-only**.
2. **`UNCLASSIFIED`:** Emitted when the market state vector does not fit any known cluster or model probability is split ambiguously. Fails closed to capital throttling.
3. **`ConfidenceAssessment.LOW`:** Emitted when confidence falls below the provenanced threshold. Blocks capital shifts and prevents aggressive rebalancing.

---

## 5. Strategy × Regime Evidence Matrix

ACASH models trading edge conditionally:
$$P(\text{Strategy Excess Return } > 0 \mid \text{Market State } S_k) \quad \neq \quad P(\text{Strategy Excess Return } > 0)$$

### Empirical Matrix Structure
For every admitted strategy, ACASH tracks an observational cell matrix across observed market states:

| Strategy ID | Market State $S_k$ | Effective Sample $N_{\text{eff}}$ | Net Expectancy (bps) | Realized Sharpe | Max Floating DD | Peak Margin | Evidence Status |
|---|---|---|---|---|---|---|---|
| `STRAT_01` | `TREND_EXPANSION` | 142.5 | +8.4 bps | 1.85 | 3.2% | 15% | `SUPPORTIVE` |
| `STRAT_01` | `RANGE_LOW_VOL` | 85.0 | -2.1 bps | -0.45 | 5.8% | 22% | `FAILED` |
| `STRAT_01` | `LIQUIDITY_SHOCK` | 12.0 | -14.5 bps | -1.90 | 11.2% | 38% | `PRELIMINARY` |
| `STRAT_01` | `UNCLASSIFIED` | 4.0 | 0.0 bps | N/A | 0.0% | 0% | `INSUFFICIENT_TO_DETERMINE` |

### Detecting Regime Tailwinds
If a strategy demonstrates spectacular historical returns exclusively during a prolonged macro trend (e.g., USD bull run of 2022) but collapses under sideways or choppy regimes, ACASH classifies the performance as **Regime Tailwind**, not unconstrained alpha. The strategy cannot receive universal allocation.

---

## 6. Crisis & Risk-Off Governance

When the classification engine detects acute market distress:
- Spread spikes $> 5\times$ median
- Order book depth drops $> 80\%$
- High-impact economic news window active
- Classification status is `UNCLASSIFIED` or `INSUFFICIENT_EVIDENCE`

**Governance Actions:**
1. Block all new strategy entries (`can_dispatch = False`).
2. Transition active allocation proposals to **`allocation = Decimal("0.0")`**.
3. Activate Event-Aware holding, halt, or emergency flatten policies as defined in ADR-022.
