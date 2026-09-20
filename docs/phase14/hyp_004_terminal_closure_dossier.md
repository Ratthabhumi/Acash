# Phase 14 HYP_004: Terminal Research Closure Dossier

```text
[STATUS: TERMINALLY_CLOSED_NOT_SUPPORTED_ON_2017_2022_REPLICATION_SAMPLE]
[MECHANISM BASELINE: MEC_0014A_BASELINE_REPLICATION = TERMINALLY_NOT_SUPPORTED]
[PRIMARY REPLICATION OUTCOME: PRIMARY_REPLICATION_NOT_ACCEPTED]
[INTERNAL OOS DIAGNOSTIC: R2_OS = -4.8358% (UNFAVORABLE TO MODEL)]
[LOG-RETURN ROBUSTNESS: p = 0.508409 (CONSISTENT WITH PRIMARY NON-ACCEPTANCE)]
[EXTERNAL HOLDOUT (2023-2026): SEALED & UNREAD (CONSUMED = false)]
[CAPITAL: $0.00 | NO_REAL_ORDERS: true | TRADING: LOCKED]
```

- **Document ID:** `docs/phase14/hyp_004_terminal_closure_dossier.md`
- **Hypothesis ID:** `HYP_004` (Market Intraday Momentum: Gao Baseline Replication on `SPY`)
- **Mechanism ID:** `MEC-0014A`
- **Registered Ordinal:** 4
- **Terminal Decision Manifest:** `docs/phase14/manifests/terminal_decision_HYP_004.json`
- **Terminal Decision Manifest SHA-256:** `05f9b3ccf3cdf476ee24b0f2329458cfcf63ff183331ef22a8a39e610a2d4128`
- **Reconciliation Base Commit:** `38310091a2a8588ee22aea139b606e0e6d02df6d`
- **Next Research Action:** `RETURN_TO_NEW_MECHANISM_INCEPTION`

---

## 1. Research Identity

Phase 14 investigated `HYP_004` / `MEC-0014A`, evaluating the baseline econometric claim of Gao, Han, Li, and Zhou (2018), *"Market Intraday Momentum"*, Journal of Financial Economics:
Specifically, that the first half-hour simple return of the SPDR S&P 500 ETF Trust (`SPY`) positively predicts the final half-hour simple return of the same trading session.

---

## 2. Frozen Hypothesis & Acceptance Contract

The hypothesis and preregistration were frozen ex-ante in Step R1 under human ratification:
- **Hypothesis Specification:** `docs/phase14/hypotheses/HYP_004.json` (SHA: `fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d`)
- **Preregistration Document:** `docs/research/MEC-0014A-statistical-preregistration-draft.md` (SHA: `1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce`)
- **Search Space Cardinality:** $K = 1$ (Single univariate OLS regression with intercept).
- **Inference Specification:** Newey-West HAC with Bartlett triangular kernel and plug-in lag rule $L = \lfloor 4 \cdot (T/100)^{2/9} \rfloor = 7$.
- **Binding Primary Replication Rule:** $\hat{\beta} > 0 \text{ AND } p < 0.05$ (two-sided HAC test at 5% nominal significance level).

---

## 3. Data Qualification Lineage

The in-sample replication dataset spanning 2017-01-01 through 2022-12-31 was constructed from raw historical SIP tick trades (68,100 pages, 673,451,966 trades) under strict qualification contracts:
- **R2 Session Endpoints Dataset:** `data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet` (SHA: `096e1c254897747f39b63b6b4125cb29bf94461ddf3f76f3d620f0bd36e05776`)
- **R2 Session Ledger:** `data/manifests/research/HYP_004_R2_session_ledger.json` (SHA: `2d07419b1dc9ba34f600e484df17eef90724fc6cbfeb65aa29484b50d8a8ffc2`)
- **Total Calendar Sessions:** 1,498
- **Primary-Regression Eligible Sessions:** 1,489
- **Preregistered Excluded Sessions:** 9 (`2017-01-03` [first session]; `2017-03-31`, `2017-06-02`, `2022-02-14` [P1 ambiguous]; `2017-06-07`, `2017-08-08`, `2017-08-23`, `2017-09-12`, `2021-03-24` [P12 ambiguous]).

---

## 4. Primary In-Sample Econometric Replication Result

Step R3 executed the frozen univariate OLS regression on simple returns:
$$r_{13, t} = \alpha + \beta \cdot r_{1, t} + \epsilon_t$$

- **Sample Size ($T$):** 1,489 eligible sessions
- **Slope ($\hat{\beta}$):** $+0.022488683629000000$
- **HAC Standard Error:** $0.035253777057000000$
- **HAC $t$-Statistic:** $+0.637908488282000000$
- **Two-Sided Asymptotic $p$-Value:** $0.523533251922000000$
- **Unadjusted $R^2$:** $0.002641292938333817$ ($0.264\%$)
- **Primary Outcome:** **`PRIMARY_REPLICATION_NOT_ACCEPTED`**
  While the slope estimate is positive, the test fails to reject the null hypothesis of zero predictive relation at the nominal 5% level ($p = 0.5235 \gg 0.05$).

---

## 5. Internal Recursive Out-of-Sample (OOS) Diagnostic Result

Step R4 executed the preregistered Campbell-Thompson (2008) predictive diagnostic over the 2020–2022 window (750 evaluation sessions, 36 monthly expanding OLS re-estimations against an expanding historical-mean benchmark):
- **Initial Estimation Window (2017–2019):** $T_{\text{train}} = 739$ sessions
- **Evaluation Window (2020–2022):** $T_{\text{eval}} = 750$ sessions
- **$\text{SSE}_{\text{model}}$:** $0.016487341748067845$
- **$\text{SSE}_{\text{benchmark}}$:** $0.015726822954313234$
- **Out-of-Sample $R^2$ ($R^2_{\text{OS}}$):** **$-0.048358069265733747$** ($-4.8358\%$)
- **Predictive Interpretation:** The expanding linear model forecast squared error exceeded the naive historical-mean benchmark by 4.84%, providing zero evidence of out-of-sample predictive superiority.

---

## 6. Single Log-Return Robustness Characterization

To verify that the primary non-acceptance was not an artifact of return compounding conventions, a single one-dimension-at-a-time log-return robustness check was executed holding sample ($T=1,489$) and inference kernel ($L=7$, Bartlett) constant:
$$\ln(p_{13, t} / p_{12, t}) = \alpha_{\log} + \beta_{\log} \cdot \ln(p_{1, t} / p_{0, t}) + \epsilon_t$$

- **Slope ($\hat{\beta}_{\log}$):** $+0.023451449509000000$
- **HAC Standard Error:** $0.035461704650000000$
- **HAC $t$-Statistic:** $+0.661317602770000000$
- **Two-Sided Asymptotic $p$-Value:** $0.508408655057000000$
- **Unadjusted $R^2_{\log}$:** $0.002909813254966642$ ($0.291\%$)
- **Significance Thresholds:**
  - $p < 0.10$: NO
  - $p < 0.05$: NO
  - $p < 0.01$: NO
- **Classification:** Robustness evidence is entirely consistent with the primary simple-return finding.

---

## 7. Exclusion-Lineage Reconciliation

At commit `38310091a2a8588ee22aea139b606e0e6d02df6d`, an audit-only reconciliation verified:
1. Exact tripartite date set equality: $\text{Log Dates} == \text{R3 Admitted Dates} == \text{R2 Eligible Dates}$ ($T=1,489$).
2. The 9 quarantined sessions in R2 Parquet and Session Ledger match identically.
3. The discrepancy was isolated to a text template error in `phase14_r3_primary_replication_audit_HYP_004.md`.
4. All empirical calculations filtered directly on `primary_regression_eligible == True`; **`EMPIRICAL_NUMERICAL_RESULTS_IMPACT = NONE`**.

---

## 8. Terminal Scientific Interpretation

- **Terminal Hypothesis Status:**
  `HYP_004 = TERMINALLY_CLOSED_NOT_SUPPORTED_ON_2017_2022_REPLICATION_SAMPLE`
- **Mechanism Baseline Status:**
  `MEC_0014A_BASELINE_REPLICATION = TERMINALLY_NOT_SUPPORTED_ON_2017_2022_REPLICATION_SAMPLE`

### What This Decision Means:
1. The frozen primary replication criterion was not satisfied ($p = 0.5235 \ge 0.05$).
2. Internal recursive predictive diagnostic was unfavorable ($R^2_{\text{OS}} = -4.84\%$).
3. Preregistered log-return robustness was qualitatively consistent with the primary finding ($p = 0.5084$).
4. No further statistical rescue analysis or parameter tuning is justified for this sealed baseline specification.

### What This Decision Does NOT Mean:
1. The true coefficient $\beta$ is mathematically proven to equal zero.
2. Market intraday momentum is universally disproven in all asset classes or historical eras.
3. Gao et al. (2018) is globally invalidated across other sampling frequencies, quotes, or universe definitions.
4. All possible intraday momentum mechanisms are rejected.

---

## 9. Analyses Deliberately Not Executed

The following potential analyses were deliberately **NOT EXECUTED** and are not needed for closure:
- $r_{12}$ predictor
- Joint regression ($r_1 + r_{12}$)
- Bid, ask, or midpoint returns
- VIX conditioning
- Volume or dispersion conditioning
- Macro-event / FOMC day exclusions
- Dividend-adjusted variants
- Ex-dividend exclusions
- Overnight-reversal decomposition
- Cross-sectional extensions
- MEC-0014B strategy translation

These are recorded as unexecuted rather than falsified; they were intentionally omitted to prevent post-hoc data mining.

---

## 10. External Holdout Preservation

- **External Holdout Period:** `2023-01-01` through `2026-12-31`
- **Holdout Status:** **`SEALED_UNREAD_FOR_HYP_004_BASELINE`**
- **`HYP_004_EXTERNAL_HOLDOUT_CONSUMED = false`**
The baseline replication line is closed cleanly on 2017–2022 evidence without burning or unsealing the 2023–2026 holdout dataset.

---

## 11. Trading & Capital Invariants

- **Paper Trading:** LOCKED (`paper_authorized = false`)
- **Live Trading:** LOCKED (`live_authorized = false`)
- **Capital Allocation:** **`$0.00`**
- **Execution Safety:** **`NO_REAL_ORDERS = true`** strictly enforced.

---

## 12. Future Research Boundary & Resurrection Protection

- `HYP_004` is registered in `TERMINAL_HYPOTHESIS_REGISTRY` in `src/acash/research/reinception.py`.
- Any attempt to resurrect `HYP_004` via `ResearchReInceptionGate` will fail closed immediately with `BLOCKED_MUTATION_VIOLATION`.
- `HYP_004` must **never** be reopened by parameter tuning, threshold relaxation, alternate significance levels, selective subsampling, or new conditioning variables.
- Any future intraday research must be initiated as:
  - A de novo mechanism;
  - A separately registered de novo hypothesis; or
  - A separately authorized `MEC-0014B` research program with independent preregistration.
- **Next Research State:** **`RETURN_TO_NEW_MECHANISM_INCEPTION`**.

---

## 13. Terminal Decision Manifest Lineage

- **Canonical Manifest Path:** `docs/phase14/manifests/terminal_decision_HYP_004.json`
- **Canonical Manifest SHA-256:** `bc6d99bb69373acd9fd2964fa603e91dfa47f5d0e574ce56cc0f662e79893853`
- **Terminal Decision Manifest Type:** `TERMINAL_RESEARCH_DECISION_MANIFEST`
