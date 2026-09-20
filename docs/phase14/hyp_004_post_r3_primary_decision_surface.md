# HYP_004 Post-R3 Primary Decision Surface

```text
[STATUS: PRIMARY DECISION SURFACE SEALED & IMMUTABLE]
[PRIMARY OUTCOME: PRIMARY_REPLICATION_NOT_ACCEPTED]
[PREREGISTERED MODEL: r13_t = alpha + beta * r1_t + eps_t]
[ESTIMATION PERIOD: 2017-01-01 to 2022-12-31 | SPY In-Sample]
[CAPITAL: $0.00 | NO_REAL_ORDERS: true | TRADING: LOCKED]
```

- **Document ID:** `docs/phase14/hyp_004_post_r3_primary_decision_surface.md`
- **Hypothesis ID:** `HYP_004` (Market Intraday Momentum: Gao Baseline Replication on `SPY`)
- **Mechanism ID:** `MEC-0014A`
- **Canonical Starting Base Commit:** `9bec736729b1ab9d59b6ee872cb31f5be56a8929`
- **Ratification Date (UTC):** `2026-09-20`
- **Authority:** Human Contributor Governance

---

## 1. Sealed Primary Econometric Replication Result

Phase 14 Step R3 executed the single authorized preregistered primary econometric model:
$$r_{13, t} = \alpha + \beta \cdot r_{1, t} + \epsilon_t$$
where:
- $r_{1, t} = \frac{p_{1, 10:00, t}}{p_{0, \text{prev close}, t}} - 1$ (Simple return from previous primary close to 10:00:00 ET)
- $r_{13, t} = \frac{p_{13, \text{curr close}, t}}{p_{12, 15:30, t}} - 1$ (Simple return from 15:30:00 ET to current primary close)
- Sample Size: $T = 1,489$ qualified in-sample regular sessions on `SPY` (2017-01-04 to 2022-12-30)
- Excluded Sessions: Exactly 9 sessions quarantined under preregistered rules (1 first-session, 8 boundary price ambiguity)

### Official Realized Estimates

| Econometric Parameter | Realized Point Estimate | Canonical Methodology |
| :--- | :---: | :--- |
| **Sample Size ($T$)** | **1,489** | Sovereign `NyseCa1Calendar` regular sessions meeting all R2 data contract gates |
| **Newey-West Bandwidth ($L$)** | **7** | Rule-of-thumb plug-in: $\lfloor 4(T/100)^{2/9} \rfloor = \lfloor 7.2868 \rfloor = 7$ |
| **Kernel Weighting** | **Bartlett** | Triangular lag kernel: $w(l, L) = 1 - \frac{l}{L+1}$ |
| **Intercept ($\hat{\alpha}$)** | **-0.000125752897293718** | OLS analytical intercept: $\bar{r}_{13} - \hat{\beta} \bar{r}_1$ |
| **Slope ($\hat{\beta}$)** | **+0.022488683629000000** | OLS univariate slope coefficient |
| **HAC Standard Error** | **0.035253777057000000** | Asymptotic square root of Bartlett Newey-West covariance matrix |
| **HAC $t$-statistic** | **0.637908488282000000** | $\hat{\beta} / \text{HAC SE}(\hat{\beta})$ |
| **Two-Sided Asymptotic $p$-value** | **0.523533251922000000** | $2(1 - \Phi(|t|))$ |
| **In-Sample $R^2$** | **0.002641292938333817** | Unadjusted ordinary least squares $1 - \text{SSE}/\text{SST}$ ($0.264\%$) |

---

## 2. Binding Decision Rule Evaluation & Outcome

Under Section 6.2 of the ratified preregistration (`docs/research/MEC-0014A-statistical-preregistration-draft.md`), the primary replication acceptance criterion is:
$$\hat{\beta} > 0 \quad \text{AND} \quad p < 0.05 \quad (\text{two-sided Newey-West HAC, } L=7, T=1489)$$

- **Direction Criterion ($\hat{\beta} > 0$):** **PASS** ($\hat{\beta} = +0.022489 > 0$)
- **Statistical Significance Criterion ($p < 0.05$):** **FAIL** ($p = 0.523533 \ge 0.05$)
- **Primary Binary Decision Outcome:** **`PRIMARY_REPLICATION_NOT_ACCEPTED`**

---

## 3. Immutability & Epistemic Boundaries

1. **Outcome Immutability:**
   The outcome **`PRIMARY_REPLICATION_NOT_ACCEPTED`** is final and permanently sealed. No secondary diagnostic, robustness study, conditioning analysis, or internal out-of-sample (OOS) evaluation may overwrite, change, rescue, or relabel this primary finding as accepted.
2. **Epistemic Characterization:**
   - Failure to achieve statistical significance ($p = 0.5235$) confirms that the empirical data on `SPY` (2017–2022) does not reject the null hypothesis of zero linear predictive relation at the preregistered $\alpha = 0.05$ boundary.
   - This finding is **NOT** equivalent to mathematical or econometric proof that $\beta \equiv 0.0$. It establishes only that the baseline Gao predictive effect is statistically undetectable from sampling noise in the qualified in-sample dataset.
3. **No Causal Claim:**
   Regression estimates represent empirical linear associations under a specific data contract. No causal inference or structural market claims are asserted.
4. **Secondary Analyses Role:**
   Any authorized secondary analyses (e.g., Internal OOS Diagnostic, alternate return specifications) serve strictly for empirical characterization of market behavior. They possess **zero authority** to modify or override the primary statistical decision.
5. **External Holdout & Execution Constraints:**
   - External Holdout ($\ge \text{2023-01-01}$) remains strictly **SEALED & UNREAD**.
   - No strategy qualification, trading signal generation, backtesting, Paper trading, or Live execution is authorized.
   - Capital allocation remains strictly **$0.00**, with `NO_REAL_ORDERS = true`.

---

## 4. Governance Record of Upstream Correctness Fix

During Step R3 pre-execution numerical validation, an inspection of [`src/acash/research/evaluation.py`](file:///c:/Users/MewMew/Desktop/Co-op/Acash/src/acash/research/evaluation.py) revealed an unintended boolean falsiness trap in `compute_ols_beta_and_hac`:
```python
# PREVIOUS IMPLEMENTATION:
return (
    to_decimal18(Decimal(f"{beta_hat:.12f}")) or Decimal("0"),
    to_decimal18(Decimal(f"{se_beta:.12f}")) or Decimal("0"),
    to_decimal18(Decimal(f"{t_stat:.12f}")) or Decimal("0"),
    to_decimal18(Decimal(f"{p_val:.12f}")) or Decimal("1.0"),
)
```
In Python, `Decimal("0")` evaluates to `False` in a boolean expression. Consequently, whenever asymptotic $p = 0.0$, the expression `Decimal("0") or Decimal("1.0")` erroneously evaluated the right-hand fallback `Decimal("1.0")`, replacing an exact zero $p$-value with 1.0.

This was corrected to explicit None-coalescing:
```python
# CORRECTED IMPLEMENTATION:
dec_beta = to_decimal18(Decimal(f"{beta_hat:.12f}"))
dec_se = to_decimal18(Decimal(f"{se_beta:.12f}"))
dec_t = to_decimal18(Decimal(f"{t_stat:.12f}"))
dec_p = to_decimal18(Decimal(f"{p_val:.12f}"))

return (
    dec_beta if dec_beta is not None else Decimal("0"),
    dec_se if dec_se is not None else Decimal("0"),
    dec_t if dec_t is not None else Decimal("0"),
    dec_p if dec_p is not None else Decimal("1.0"),
)
```

- **Classification:** `NUMERICAL_CORRECTNESS_FIX_NON_MATERIAL_TO_OBSERVED_R3_RESULT`
- **Reason:** In the realized empirical Step R3 execution, the asymptotic $p$-value was $0.523533251922000000$ (well above zero), $\hat{\beta} = 0.022488683629$, and $\text{HAC SE} = 0.035253777057$. Because all values were strictly nonzero, the fix did not alter the realized point estimates, $t$-statistic, $p$-value, or the resulting `PRIMARY_REPLICATION_NOT_ACCEPTED` outcome.
