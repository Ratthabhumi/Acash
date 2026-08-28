# ACASH — Phase 6 Design Proposal: Statistical Validation & Overfitting Controls (OOS Hard Gate)

**Document:** `docs/PHASE_6_DESIGN_PROPOSAL.md`  
**Version:** 1.0.0  
**Date:** 2026-08-28  
**Status:** **PENDING HUMAN REVIEW & APPROVAL**  
**Phase Objective:** Establish an uncompromising mathematical validation gate that prevents backtest overfitting, selection bias, and data-snooping from contaminating capital allocation.

---

> [!IMPORTANT]
> **Epistemic Principle: Statistical Significance $\neq$ Tradeable Alpha**
> A hypothesis passing statistical significance ($p < 0.05$ or $\text{DSR} > 0.95$) proves only that its historical pattern was non-random under the null hypothesis of no effect.
> **Tradeable Alpha** requires satisfying four additional non-negotiable criteria:
> 1. **Economic Edge Net of All Friction:** $\mathbb{E}[R_{\text{net}}] > \text{Hurdle Rate}$ under realistic Level-2 matching.
> 2. **Low Probability of Backtest Overfitting:** $\text{PBO} < 0.25$ across all CPCV combinatorial paths.
> 3. **Parameter Stability & Flat Curvature:** Zero knife-edge parameter sensitivity ($\nabla_\theta SR(\theta)$ remains stable across $\pm 25\%$ perturbations).
> 4. **True Out-of-Sample (OOS) Survival:** Out-of-sample Sharpe $\ge 0.50 \cdot \text{In-Sample Sharpe}$ without re-tuning.

---

## 1. System Architecture & Validation Pipeline

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PHASE 4 & 5 INPUTS                                     │
│  - Pre-Registered Hypothesis Specifications       - Event Backtest Simulation Fills    │
│  - Effective Trials Ledger (K Trials Recorded)    - Reference Microstructure Data      │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     1. COMBINATORIAL PURGED CROSS-VALIDATION (CPCV)                    │
│  - Contiguous N-Group Partitioning             - Exhaustive (N choose k) Path Slicing  │
│  - Strict Label Purging [t+1, t+H]             - Post-Test Embargo Buffer (>= max(H))  │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        2. MULTIPLE-TESTING & SELECTION BIAS CORRECTION                 │
│  - Total Trial Accounting (K Trials)           - Expected Max Sharpe under Null (SR0)  │
│  - Holm-Bonferroni Step-Down (FWER)            - Benjamini-Hochberg False Discovery    │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      3. DEFLATED SHARPE RATIO (DSR) & MIN TRL ENGINE                   │
│  - Unbiased Higher Moments (Skew/Kurt)         - Non-Normal Asymptotic DSR P-Value    │
│  - Minimum Track Record Length (MinTRL)        - Haircut Sharpe Ratio Adjustment       │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                    4. OVERFITTING & PARAMETER FRAGILITY EVALUATION                     │
│  - Probability of Overfitting (PBO)            - Parameter Surface Hessian / Curvature │
│  - Friction Multiplier Monotonic Decay         - Time-Regime Stability Profile        │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     5. DURABLE OUT-OF-SAMPLE (OOS) GOVERNANCE GATE                     │
│  - Sealed Blind OOS Split Verification         - Re-Tuning Lock (EVALUATED -> EXHAUST) │
│  - Validation Verdict & Manifest Lineage       - PASS / REJECT Decision Emission       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Mathematical Specifications

### 2.1 Combinatorial Purged Cross-Validation (CPCV)
Given a time series of $T$ observations partitioned into $N$ contiguous groups, we select $k$ groups as the testing set for each combination:
- **Total Combinations:** $C = \binom{N}{k}$
- **Total Pseudo-OOS Backtest Paths:** $\phi = \frac{k}{N} \binom{N}{k}$

#### Strict Purging and Embargo Rules:
1. **Purging:** For every test window $[T_{\text{test\_start}}, T_{\text{test\_end}}]$, any training sample $t$ whose forward return evaluation interval $[t+1, t+H]$ overlaps with $[T_{\text{test\_start}}, T_{\text{test\_end}}]$ is strictly purged:
   $$\text{Purge Condition: } (t+1 \le T_{\text{test\_end}}) \land (t+H \ge T_{\text{test\_start}})$$
2. **Embargoing:** Immediately following each test window $[T_{\text{test\_start}}, T_{\text{test\_end}}]$, training samples in $[T_{\text{test\_end}}, T_{\text{test\_end}} + \text{embargo\_bars}]$ are removed to eliminate serial correlation autoregressive leakage.

---

### 2.2 Deflated Sharpe Ratio (DSR)
The Deflated Sharpe Ratio (Bailey & López de Prado, 2014) adjusts the estimated annualized Sharpe Ratio $\widehat{SR}$ for:
1. Non-normal returns (Skewness $\hat{\gamma}_3$, Excess Kurtosis $\hat{\gamma}_4$)
2. Multiple testing search bias across $K$ parameter trials
3. Track record length $T$

#### Expected Maximum Sharpe under Null Hypothesis ($SR_0$):
$$SR_0 = \sqrt{V} \left( (1 - \gamma_E) Z^{-1}\left(1 - \frac{1}{K}\right) + \gamma_E Z^{-1}\left(1 - \frac{1}{K \cdot e}\right) \right)$$
where $\gamma_E \approx 0.5772156649$ is the Euler-Mascheroni constant, $V$ is the variance of Sharpe ratios across all $K$ trials, and $Z^{-1}$ is the inverse standard normal CDF.

#### DSR Test Statistic:
$$\text{DSR} = \Phi \left( \frac{(\widehat{SR} - SR_0)\sqrt{T-1}}{\sqrt{1 - \widehat{\gamma}_3 \widehat{SR} + \frac{\widehat{\gamma}_4 - 1}{4}\widehat{SR}^2}} \right)$$
- **Acceptance Gate:** $\text{DSR} \ge 0.95$ ($p \le 0.05$).

---

### 2.3 Minimum Track Record Length (MinTRL)
The minimum observation period (in number of bars / sample size $T$) required for $\widehat{SR}$ to be statistically distinguishable from $SR_0$ at significance level $\alpha$:
$$\text{MinTRL} = 1 + \left(1 - \widehat{\gamma}_3 \widehat{SR} + \frac{\widehat{\gamma}_4 - 1}{4}\widehat{SR}^2\right) \left(\frac{Z_\alpha}{\widehat{SR} - SR_0}\right)^2$$
- **Acceptance Gate:** $T_{\text{actual}} \ge \text{MinTRL}$. If $T_{\text{actual}} < \text{MinTRL}$, the strategy is rejected for insufficient statistical power.

---

### 2.4 Probability of Backtest Overfitting (PBO)
Given $M$ candidate model configurations evaluated across $C$ CPCV paths:
1. Determine the in-sample optimal configuration $m^* = \arg\max_{m} SR_{\text{IS}}(m, c)$.
2. Calculate the rank-based relative performance of $m^*$ in the out-of-sample slice:
   $$\bar{\omega}_c = \text{Rank}\left(SR_{\text{OOS}}(m^*, c)\right) / (M + 1)$$
3. Log-odds distribution:
   $$\lambda_c = \ln \left( \frac{\bar{\omega}_c}{1 - \bar{\omega}_c} \right)$$
4. $\text{PBO} = \frac{1}{C} \sum_{c=1}^C \mathbb{I}(\lambda_c < 0) = \mathbb{P}(\lambda < 0)$.
- **Acceptance Gate:** $\text{PBO} < 0.25$ (Probability of OOS underperformance below median is strictly under 25%).

---

### 2.5 Parameter Fragility & Surface Curvature
A robust quantitative alpha must occupy a wide, flat region in parameter space $\Theta$. A sharp spike surrounded by degradation indicates data snooping.
$$\text{Curvature Penalty} = \max_{\theta_j} \left| \frac{SR(\theta_0 + \Delta \theta_j) - 2 SR(\theta_0) + SR(\theta_0 - \Delta \theta_j)}{\Delta \theta_j^2} \right|$$
- **Acceptance Gate:** Performance degradation when perturbing parameters by $\pm 25\%$ must not exceed $30\%$ of peak Sharpe.

---

## 3. Package & Module Architecture (`src/acash/validation/`)

```
src/acash/validation/
├── __init__.py               # Public API exports
├── schema.py                 # Pydantic schemas (ValidationConfig, DSRResult, ValidationReport)
├── cpcv.py                   # Combinatorial Purged Cross-Validation generator
├── deflated_sharpe.py        # DSR, MinTRL, and higher-moment inference engine
├── multiple_testing.py       # Holm-Bonferroni, Benjamini-Hochberg, Haircut Sharpe
├── overfitting.py            # PBO computation, parameter curvature, stress decay
└── gate.py                   # Sovereign Statistical Validation Orchestrator & Governance
```

---

## 4. Phase 6 Gate 6 Verification Criteria

| Verification Item | Acceptance Standard | Method of Verification |
| :--- | :--- | :--- |
| **Purging & Embargo Invariance** | Zero training samples overlap with test label windows or post-test embargo buffers | Adversarial unit test asserting $T_{\text{train\_label}} \cap T_{\text{test}} = \emptyset$ |
| **DSR Mathematical Reference** | DSR and MinTRL match Bailey & López de Prado (2014) published analytical benchmark vectors to 8 decimal places | Unit tests against known closed-form vectors |
| **Multiple Testing Search Ledger** | Every exploratory parameter run increments trial counter $K$ in search ledger; zero untracked trials | Integration test verifying search accounting |
| **PBO Distribution Integrity** | PBO correctly detects overfit synthetic strategies ($PBO \to 1.0$) vs true edge ($PBO \to 0.0$) | Synthetic calibration unit tests |
| **Blind OOS State Invariance** | Sealed OOS data cannot be accessed more than once; re-tuning attempts raise `DataContractError` | State machine regression test on `governance_ledger.json` |
| **Test Suite Pass Rate** | 100% pass rate across unit and validation tests; `mypy` zero type errors | `pytest` + `mypy` |
