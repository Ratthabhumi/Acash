# Candidate Technical Ideas & Empirical Deconstruction

**Status:** UNVERIFIED_SOCIAL_MEDIA_CLAIM — Candidate Research & Falsification Protocols  
**Canonical Governance Authority:** Non-Executable Research Reference. Does NOT authorize backtest, paper trading, or live execution. Does NOT create HYP_003. Preserves Canonical Capital = $0.00 and NO_REAL_ORDERS = true.

---

## 1. Purpose & Epistemic Warning

This document preserves candidate discretionary concepts, technical trading claims, and social-media-derived pattern methodologies.

> [!CAUTION]
> **Strict Epistemic Warning:**
> - Ideas catalogued here are **UNVERIFIED SOCIAL-MEDIA CLAIMS**.
> - They are **NOT** active ACASH strategies.
> - They are **NOT** evidence of alpha.
> - Claims of "predicting the next candle with 90% accuracy" or identifying "institutional manipulation" are treated with extreme quantitative skepticism.
> - **The ACASH Mandate:** Do not implement discretionary lore. Translate candidate ideas into **objective, machine-verifiable mathematical formulations**, then subject them to brutal statistical falsification.

---

## 2. Case Study: The Engulfing Bar / Fibonacci Quadrant Claim

### 2.1 The Discretionary Claim (As Sourced)
Social-media technical analysis sources claim a deterministic pattern based on an engulfing candle:
1. Identify a prior reference candle $B_{t-1}$.
2. Identify an engulfing candle $B_t$ whose range completely envelopes $B_{t-1}$.
3. Subdivide the range of $B_t$ into four equal quadrants (Fibonacci-style retracements):
   $$\{0.00, 0.25, 0.50, 0.75, 1.00\}$$
4. Assert that price action entering the $0.50–0.75$ quadrant represents *"manipulation"* or *"liquidity grabbing"*.
5. Assert that an entry at this quadrant predicts that the next candle will reverse and reach the low of the engulfing candle.

---

## 3. Quantitative Translation: From Narrative Lore to Measurable Variables

To evaluate this candidate idea without falling victim to subjective interpretation, the discretionary narrative must be converted into rigorous, unambiguous mathematical logic:

```text
DISCRETIONARY CLAIM:
"Look for an engulfing candle and manipulation in the upper quadrant"
                     ↓
MATHEMATICAL SPECIFICATION:
1. Previous Bar: O_{t-1}, H_{t-1}, L_{t-1}, C_{t-1}
2. Current Bar:  O_t, H_t, L_t, C_t
3. Engulfing Condition:
   (H_t > H_{t-1}) ∧ (L_t < L_{t-1}) ∧ (C_t < O_t)
4. Volatility Threshold:
   (H_t - L_t) > k · ATR(N)_t  (where k is a parameter)
5. Quadrant Retracement Window:
   Threshold_50 = L_t + 0.50 · (H_t - L_t)
   Threshold_75 = L_t + 0.75 · (H_t - L_t)
6. Retracement Event:
   H_{t+1} ∈ [Threshold_50, Threshold_75]
7. Target Variable:
   Forward return or hitting L_t prior to hitting H_t
```

---

## 4. Mandatory Empirical Falsification Protocols

Before any candidate idea derived from technical lore can be registered as a formal ACASH hypothesis (e.g., HYP_00X), it must pass an exhaustive empirical battery:

```text
CANDIDATE IDEA
      ↓
OBJECTIVE FORMULATION
      ↓
IN-SAMPLE EVALUATION (N >= 500 events)
      ↓
TRANSACTION FRICTION DEDUCTION (2.5x spread + fees)
      ↓
OUT-OF-SAMPLE (OOS) VALIDATION (>= 3 independent market regimes)
      ↓
WALK-FORWARD ROBUSTNESS
      ↓
FALSIFICATION CHECK:
[ t-stat < 2.5 OR Sharpe < 1.0 OR MaxDD > 15% ] → DISCARD IMMEDIATELY
```

### Required Metrics for Candidate Qualification:
1. **Sample Size ($N$):** Must generate $\ge 500$ distinct historical non-overlapping setups across multi-year data.
2. **Win Rate & Payoff Ratio:** Unbiased calculation of true empirical win rate vs. risk-reward ratio.
3. **Expected Value per Trade ($EV$):** Net return per trade after deducting 2.5x bid-ask spread and exchange fees.
4. **Statistical Significance ($t$-statistic):** Return distribution $t$-statistic must exceed $2.5$ ($p < 0.01$).
5. **Drawdown Duration & Tail Risk:** Maximum consecutive losses and recovery time under regime shifts.
6. **Regime Sensitivity:** Candidate must not fail completely when shifting between trending and mean-reverting macro regimes.

---

## 5. Core Methodological Takeaway

> **"Turn discretionary TA language into reproducible, machine-testable variables."**

The objective of preserving candidate ideas is not to endorse them, but to ensure that when quantitative researchers encounter popular market theories, they have a clear, pre-defined scientific protocol to test, falsify, and permanently discard or rigorously qualify them.
