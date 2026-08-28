# ACASH — Phase 6 Design Proposal: Statistical Validation & Overfitting Controls

**Document:** `docs/PHASE_6_DESIGN_PROPOSAL.md`  
**Version:** 1.0.0  
**Date:** 2026-08-28  
**Status:** **PROPOSED — AWAITING ARCHITECTURAL REVIEW & SIGN-OFF**  
**Phase Objective:** Eliminate data-snooping bias, selection bias, and backtest overfitting by subjecting candidate alpha strategies to rigorous post-backtest econometric validation gates—including Combinatorial Purged Cross-Validation (CPCV), Probability of Backtest Overfitting (PBO), Deflated Sharpe Ratio (DSR), Haircut Sharpe Ratio, and Parameter Sensitivity Stress-Testing—before capital allocation.

---

## 1. Epistemic Architecture & Quantitative Validation Workflow

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   PHASE 5: SIMULATION SUBSTRATE (BacktestManifest)                │
│  - Replayed Execution Fills                  - Sovereign Dual-View Ledger        │
│  - Chronological Equity Curves               - Reality-Gap Telemetry             │
└─────────────────────────┬────────────────────────────────────────────────────────┘
                          │ Raw Equity Curves & Execution Events
                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│             PHASE 6: STATISTICAL VALIDATION & OVERFITTING ENGINE (Gate 6)        │
│                                                                                  │
│  ┌─────────────────────────────────┐   ┌──────────────────────────────────────┐  │
│  │ 1. Combinatorial Cross-Validation│   │ 2. Multiple-Testing Correction       │  │
│  │    - CPCV (N groups, k test)     │   │    - Deflated Sharpe Ratio (DSR)     │  │
│  │    - Boundary Purging & Embargo  │   │    - Haircut Sharpe Ratio (Harvey)   │  │
│  │    - PBO (Prob Backtest Overfit) │   │    - Family-Wise Error Rate (FWER)   │  │
│  └────────────────┬────────────────┘   └──────────────────┬───────────────────┘  │
│                   │                                       │                      │
│  ┌────────────────┴────────────────┐   ┌──────────────────┴───────────────────┐  │
│  │ 3. Sensitivity & Fragility Suite│   │ 4. Durable Validation Manifest       │  │
│  │    - Parameter Stability Surface │   │    - Content-Derived Determinism     │  │
│  │    - 1x - 5x Slippage/Latency    │   │    - Strict Binary Gate 6 Verdict   │  │
│  └─────────────────────────────────┘   └──────────────────────────────────────┘  │
└─────────────────────────┬────────────────────────────────────────────────────────┘
                          │ Validated & Non-Overfitted Alpha Strategies
                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 7–8: REGIME ENGINE & PORTFOLIO ENGINE                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Quantitative Formulations & Specifications

### 2.1 Combinatorial Purged Cross-Validation (CPCV)
- Given $T$ chronological observations, partition into $N$ contiguous blocks.
- Generate all $\binom{N}{k}$ combinations where $k$ blocks form the test set and $N-k$ blocks form the training set.
- Apply **Purging** across train-test boundaries for labels spanning horizon $H$.
- Apply **Embargo** of length $E \ge \max(H)$ immediately following each test block to prevent post-test autoregressive leakage.
- Generate $M = \binom{N}{k}$ out-of-sample equity paths $\mathcal{P}_1, \dots, \mathcal{P}_M$.

### 2.2 Probability of Backtest Overfitting (PBO)
- Evaluate relative ranking of in-sample optimized strategies vs out-of-sample realized performance across all CPCV combinations.
- Compute the probability distribution of relative rank logits:
  $$\text{PBO} = P(\text{SR}_{\text{OOS}} \le 0) = \int_{-\infty}^0 f(\lambda) \, d\lambda$$
- **Hard Gate 6 Requirement:** $\text{PBO} < 0.20$ (Strategy must have $< 20\%$ probability of underperforming due to selection bias).

### 2.3 Deflated Sharpe Ratio (DSR)
- Corrects the sample Sharpe ratio $\widehat{\text{SR}}$ for non-normality (skewness $\hat{\gamma}_3$, kurtosis $\hat{\gamma}_4$), sample length $T$, and total number of tested model configurations $K$:
  $$\text{DSR} = \Phi\left(\frac{(\widehat{\text{SR}} - \text{SR}^*) \sqrt{T - 1}}{\sqrt{1 - \hat{\gamma}_3 \widehat{\text{SR}} + \frac{\hat{\gamma}_4 - 1}{4} \widehat{\text{SR}}^2}}\right)$$
  where the expected maximum Sharpe ratio under the null hypothesis is:
  $$\text{SR}^* = \sqrt{2 \ln K} \left( (1 - \gamma) Z^{-1}\left(1 - \frac{1}{K}\right) + \gamma Z^{-1}\left(1 - \frac{1}{K e}\right) \right) \cdot \sigma_{\text{SR}}$$
  ($\gamma \approx 0.5772156649$ is the Euler-Mascheroni constant).
- **Hard Gate 6 Requirement:** $\text{DSR} \ge 0.95$ ($p < 0.05$ significance under multiple testing).

### 2.4 Haircut Sharpe Ratio & False Discovery Rate
- Adjusts Sharpe ratios based on the search history recorded in the research governance ledger (`governance_ledger.json`).
- Applies Bonferroni and Benjamini-Hochberg-Yekutieli (BHY) penalization for correlated trial dependencies.

### 2.5 Parameter Stability Surface & Neighborhood Flatness
- Evaluates strategy performance across contiguous parameter grids ($\pm 10\%, \pm 25\%, \pm 50\%$).
- Quantifies the **Parameter Stability Index (PSI)**: ratio of profitable contiguous neighborhood volume to total parameter space volume.
- **Hard Gate 6 Requirement:** $\text{PSI} \ge 0.70$ (Razor-thin parameter spikes with negative surrounding neighborhoods are strictly disqualified).

### 2.6 Execution Friction Stress-Testing Matrix
- Simulates strategy returns across a stress-testing multiplier matrix:
  - Base Friction ($1.0\times$)
  - Elevated Spread ($1.5\times, 2.0\times, 3.0\times$)
  - Adverse Latency Slip ($2.0\times, 5.0\times$)
- **Hard Gate 6 Requirement:** Net Sharpe Ratio must remain $\ge 0.50$ and total PnL must remain positive under $2.0\times$ aggregate friction multiplier.

### 2.7 Durable Validation Manifest (`ValidationManifest`)
- Emits canonical immutable JSON manifest:
  ```json
  {
    "validation_id": "val_HYP01_CPCV_abcdef1234567890",
    "hypothesis_id": "HYP-01",
    "backtest_manifest_id": "bkt_NAUTILUS_ES_...",
    "trials_tested_count": 42,
    "cpcv_combinations": 16,
    "pbo_score": 0.082,
    "deflated_sharpe_ratio": 0.974,
    "haircut_sharpe_ratio": 1.42,
    "parameter_stability_index": 0.85,
    "friction_stress_survival": true,
    "gate_6_verdict": "PASSED",
    "computed_at_utc": "2026-08-28T00:00:00Z"
  }
  ```

---

## 3. Implementation Plan & Package Structure

```
src/acash/validation/
├── __init__.py           # Public API exports
├── schema.py             # ValidationConfig, ValidationMetrics, ValidationManifest
├── cpcv.py               # Combinatorial Purged Cross-Validation (Purging, Embargo, Path Combiner)
├── overfitting.py        # PBO, Logits Distribution, Rank Analysis
├── multiple_testing.py   # Deflated Sharpe Ratio (DSR), Haircut Sharpe Ratio, FDR controls
├── stress_testing.py     # Parameter Stability Surface & Friction Multiplier Fragility Suite
└── pipeline.py           # End-to-end Phase 6 Validation Pipeline & Manifest Storage
```

---

## 4. Gate 6 Acceptance Criteria
1. **Zero Lookahead in CPCV:** Purging and embargo buffers strictly prevent boundary leakage across all combinatorial test paths.
2. **Exact Mathematical Grounding:** DSR, Haircut Sharpe, and PBO implementations match gold-standard reference literature with hand-calculated unit test verification.
3. **Reproducible Validation Manifests:** Content-derived validation identity binds all backtest manifests, search logs, and hyperparameter matrices.
4. **Falsification Enforcement:** Overfitted toy models (e.g. random noise fitting, peak cherry-picking) are strictly rejected by Gate 6.
5. **Full Test & Lint Integrity:** 100% test pass rate, strict `mypy` zero error enforcement.
