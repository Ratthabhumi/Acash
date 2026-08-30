# ACASH Quantitative Statistical Validation & Methodology Contract

This document provides the canonical mathematical specifications, literature foundations, and governance contracts for the **ACASH Statistical Validation Gate (Gate 6)**.

---

## 1. Stacked Defense-in-Depth Governance Architecture

Gate 6 implements four stacked, complementary quantitative layers to prevent backtest overfitting and false discovery in quantitative strategy research:

```text
               ┌──────────────────────────────────────────────────────────┐
               │          Primary Candidate Strategy Returns             │
               └────────────────────────────┬─────────────────────────────┘
                                            │
                                            ▼
               ┌──────────────────────────────────────────────────────────┐
               │ Layer 1: Selection Bias & Non-Normality Hurdle (DSR)     │
               │   DSR_prob >= 0.95, TRL >= MinTRL                        │
               └────────────────────────────┬─────────────────────────────┘
                                            │
                                            ▼
               ┌──────────────────────────────────────────────────────────┐
               │ Layer 2: Family-Wise Error Rate Control (Holm Step-Down) │
               │   p_Holm(primary) <= alpha (0.05)                        │
               └────────────────────────────┬─────────────────────────────┘
                                            │
                                            ▼
               ┌──────────────────────────────────────────────────────────┐
               │ Layer 3: Non-Linear Economic Hurdle (Haircut Sharpe)     │
               │   Haircut_SR >= 1.0                                      │
               └────────────────────────────┬─────────────────────────────┘
                                            │
                                            ▼
               ┌──────────────────────────────────────────────────────────┐
               │ Layer 4: Combinatorial Backtest Overfitting (CSCV / PBO) │
               │   Balanced CSCV (C=252, M), PBO <= 0.25                  │
               └────────────────────────────┬─────────────────────────────┘
                                            │
                                            ▼
               ┌──────────────────────────────────────────────────────────┐
               │ Auxiliary Layers: OOS Retention, Fragility, Friction     │
               │   OOS_SR >= 0.5, Retention >= 50%, Curvature <= 0.50     │
               └────────────────────────────┬─────────────────────────────┘
                                            │
                                            ▼
                               [ PASS_TRADEABLE_ALPHA ]
```

---

## 2. Mathematical Formulations & Literature Foundations

### Layer 1: Deflated Sharpe Ratio (DSR)
* **Literature Reference**: Bailey, D. H., & López de Prado, M. (2014). *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality*. Journal of Portfolio Management, 40(5), 94-107.
* **Formulation**:
  $$\text{DSR} = \Phi\left( \frac{(\widehat{SR} - SR_0)\sqrt{T - 1}}{\sqrt{1 - \hat{\gamma}_3 \widehat{SR} + \frac{\hat{\gamma}_4 - 1}{4}\widehat{SR}^2}} \right)$$
  where the expected maximum null Sharpe hurdle $SR_0$ is derived under Extreme Value Theory (EVT):
  $$SR_0 = \mu_{SR} + \sqrt{V} \left( (1 - \gamma) \Phi^{-1}\left(1 - \frac{1}{K}\right) + \gamma \Phi^{-1}\left(1 - \frac{1}{K e}\right) \right)$$
  where $K = \text{declared trial count}$, $V = \text{variance across candidate trials}$, and $\gamma \approx 0.5772156649$ (Euler-Mascheroni constant).
* **Governance Contract**:
  - DSR probability must satisfy $\text{DSR} \ge 0.95$.
  - Sample length must satisfy $T \ge \text{MinTRL}$.
  - Strictly fail-closed on zero trial variance ($\operatorname{Var}(\widehat{SR}) \le 10^{-12} \implies SR_0 = 0.0$).

---

### Layer 2: Family-Wise Error Rate Control (Holm-Bonferroni)
* **Literature Reference**: Holm, S. (1979). *A Simple Sequentially Rejective Multiple Test Procedure*. Scandinavian Journal of Statistics, 6(2), 65-70.
* **Formulation**:
  Sort all $K$ exploratory candidate $p$-values: $p_{(1)} \le p_{(2)} \le \dots \le p_{(K)}$.
  Adjusted $p$-value for candidate at rank $i$:
  $$p_{\text{adj},(i)} = \min\left(1.0, \max_{j \le i} \left[ (K - j + 1) p_{(j)} \right]\right)$$
* **Governance Contract**:
  - The pre-registered primary strategy candidate (Index 0 in ledger) must satisfy $p_{\text{adj}}(\text{primary}) \le 0.05$.

---

### Layer 3: Bonferroni Haircut Sharpe Ratio
* **Literature Reference**: Harvey, C. R., & Liu, Y. (2015). *Backtesting*. Journal of Portfolio Management, 42(1), 13-28.
* **Formulation**:
  $$p_{\text{Bonferroni}} = \min(1.0, K \cdot p_{\text{primary}})$$
  $$\text{Haircut\_SR} = \Phi^{-1}\left(1 - \frac{p_{\text{Bonferroni}}}{2}\right) \cdot \sqrt{\frac{252}{T}}$$
* **Governance Contract**:
  - Requires $\text{Haircut\_SR} \ge 1.0$.

---

### Layer 4: Combinatorially Symmetric Cross-Validation (CSCV) & PBO
* **Literature Reference**: Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2016). *The Probability of Backtest Overfitting*. Journal of Computational Finance, 20(4), 39-69.
* **Formulation**:
  - Partition $T$ observations into $N=10$ contiguous blocks with purged boundary labels and embargo buffers ($T \ge 2N$).
  - Form all $C = \binom{N}{N/2} = \binom{10}{5} = 252$ balanced train/test combinations ($|IS| = |OOS| = 5$ blocks).
  - Compute in-sample Sharpe matrix $\mathbf{R}_{IS} \in \mathbb{R}^{252 \times M}$ and out-of-sample Sharpe matrix $\mathbf{R}_{OOS} \in \mathbb{R}^{252 \times M}$.
  - Identify IS winner $m_c^* = \operatorname{argmax}_m \mathbf{R}_{IS}[c, m]$ with tie-symmetric mid-rank policy.
  - Calculate OOS relative mid-rank $\omega_c \in (0, 1)$ and logit $\lambda_c = \ln\left(\frac{\omega_c}{1 - \omega_c}\right)$.
  - Probability of Backtest Overfitting:
    $$\text{PBO} = \frac{1}{C} \sum_{c=1}^C \mathbb{I}(\lambda_c < 0) = \frac{1}{252} \sum_{c=1}^{252} \mathbb{I}(\mathbf{R}_{OOS}[c, m_c^*] < \operatorname{median}(\mathbf{R}_{OOS}[c, :]))$$
* **Governance Contract**:
  - Requires $\text{PBO} \le 0.25$.
  - Partition geometry strictly validated: uniform $k=5$, combination uniqueness, contiguous group labels $\{0, \dots, 9\}$, and exact $C=252$ combinations.

---

### Layer 5: Dependence-Aware Primary Inference (Newey-West HAC)
* **Literature Reference**: Newey, W. K., & West, K. D. (1987). *A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix*. Econometrica, 55(3), 703-708.
* **Formulation**:
  $$\hat{\sigma}_{LR}^2 = \hat{\gamma}_0 + 2\sum_{l=1}^L \left(1 - \frac{l}{L+1}\right)\hat{\gamma}_l$$
  $$t_{\text{HAC}} = \frac{\bar{r}}{\sqrt{\hat{\sigma}_{LR}^2 / T}}, \quad p_{\text{HAC}} = \operatorname{erfc}\left(\frac{|t_{\text{HAC}}|}{\sqrt{2}}\right)$$
* **Bandwidth Specification**:
  - When `max_lags=None`, ACASH uses a fixed $T^{2/9}$-type heuristic lag truncation rule:
    $$L = \lfloor 4(T/100)^{2/9} \rfloor$$
  - *Methodological Boundary*: This is a fixed asymptotic rate heuristic inspired by Newey & West (1994), not the full data-dependent automatic plug-in bandwidth algorithm.
* **Governance Contract**:
  - Strictly fails closed on sample size $T < 2$, non-finite observations, zero sample variance ($\gamma_0 \le 10^{-12}$), non-positive long-run variance ($\hat{\sigma}^2_{LR} \le 10^{-12}$), or invalid lag specifications ($L < 0$ or $L \ge T$).

---

## 3. Epistemological Boundaries & Methodological Stance

1. **Statistically Dependent + Distinct & Complementary Controls**:
   - DSR and PBO evaluate the same underlying strategy returns, sample horizon, and candidate search universe; they are **statistically dependent** estimands.
   - However, they act as **complementary controls** because they address distinct failure modes:
     - In **Diverse Exploratory Search**: DSR acts as the primary restrictive filter because high trial dispersion $V$ elevates the hurdle $SR_0$, while PBO readily passes ($P(\text{PBO} \mid S_3) = 100\%$).
     - In **Collinear Parameter Sweeps**: DSR is lenient ($V \to 0 \implies SR_0 \to 0$), but PBO acts as the decisive filter ($P(\text{PBO} \mid S_3) = 13.4\%$) due to combinatorial rank instability across near-identical models.
2. **Policy Compliance $\neq$ Future Profitability**:
   - The verdict $\text{PASS\_TRADEABLE\_ALPHA}$ certifies strictly that the candidate strategy has passed pre-registered statistical and economic risk hurdles under historical observations. It is NOT a mathematical guarantee of future profitability, market stationarity, or absence of structural regime change.
3. **Binomial Uncertainty & Confidence Intervals**:
   - All empirical approval and detection rates are reported with exact **Wilson Score 95% Confidence Intervals**.
   - For $k=0$ counts, the lower bound is canonicalized to $0.00\%$ via boundary post-normalization.
