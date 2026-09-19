# MEC-0014A Statistical Replication — Final Pre-Registration (Revision 3)

```text
[GOVERNANCE ARTIFACT: STATISTICAL PRE-REGISTRATION — RATIFIED CHOICES]
[PREREGISTRATION_STATUS: FINAL_PENDING_HYPOTHESIS_REGISTRATION]
[CANONICAL BASE COMMIT: 542d9954befb962e23906df8d1b2880e6775e19f]
[HYP_004: NOT CREATED]
[EMPIRICAL EXECUTION: NOT AUTHORIZED]
[MARKET DATA RETRIEVAL: ZERO OPERATIONS THIS DOCUMENT]
[OOS ACCESS: STRICTLY FORBIDDEN (>= 2023-01-01)]
[CAPITAL AUTHORITY: $0.00 / NO_REAL_ORDERS=true]
[PAPER TRADING: NOT AUTHORIZED]
[LIVE TRADING: LOCKED]
```

- **Document ID:** `docs/research/MEC-0014A-statistical-preregistration-draft.md`
- **Mechanism:** `MEC-0014A` — Market Intraday Momentum: Gao Baseline Predictive-Relation Econometric Replication
- **Revision:** 3 (Human-Ratified Statistical Preregistration — 2026-09-19)
- **Base Canonical Commit:** `542d9954befb962e23906df8d1b2880e6775e19f`
- **Governing Standard:** ACASH AGENTS.md (Zero Unverified Claims; Strict Fail-Closed)
- **Upstream Intake:** [`docs/research/MEC-0014-market-intraday-momentum-research-intake.md`](docs/research/MEC-0014-market-intraday-momentum-research-intake.md)
- **Upstream Close Authority:** [`docs/research/MEC-0014-close-auction-contract-audit.md`](docs/research/MEC-0014-close-auction-contract-audit.md)
- **Upstream Transaction Contract Audit:** [`docs/research/MEC-0014-transaction-contract-audit.md`](docs/research/MEC-0014-transaction-contract-audit.md) (Manifest SHA-256: `d1ebb09dc3103054bc5b9da09dfb4a8d4d84ff61f02f254583689cac64cd537c`)
- **Literature Primary Authority:** Gao, Lei; Han, Yufeng; Li, Sophia Zhengzi; Zhou, Guofu (2018). "Market Intraday Momentum." *Journal of Financial Economics*, Vol. 129, Iss. 2, August 2018, pp. 394–414. DOI: [10.1016/j.jfineco.2018.05.009](https://doi.org/10.1016/j.jfineco.2018.05.009)

---

## 1. Research Identity and Scope

**MEC-0014A is strictly:**

> Econometric replication of the Gao et al. (2018) predictive relation between the first-half-hour SPY return (including overnight) and the final-half-hour SPY return, applied to a contemporary post-publication ACASH replication sample.

**MEC-0014A is NOT:**

- A trading strategy implementation, a market-timing backtest, or a Sharpe/P&L evaluation.
- MEC-0014B (executable market-timing strategy translation with institutional friction; defined separately and not authorized).
- A new hypothesis. No `HYP_004` is created by this document.

---

## 2. Partition Contract (Ratified)

> [!IMPORTANT]
> `HYP_004_PARTITION_POLICY = RATIFIED`
> The partition below is ratified as the governing data boundary for MEC-0014A. No empirical execution is authorized until formal hypothesis registration.

### 2.1 Replication Sample

| Parameter | Value | Classification |
| :--- | :--- | :--- |
| **Label** | `MEC_0014A_MECHANISM_SPECIFIC_REPLICATION_SAMPLE` | RATIFIED |
| **Date Range** | `2017-01-01` through `2022-12-31` | RATIFIED |
| **Calendar Authority** | `NyseCa1Calendar` regular 390-minute sessions only | LITERATURE_DERIVED |
| **Regular Sessions (Calendar)** | 1,498 confirmed by coverage census | VERIFIED |
| **Regression Observations (Maximum)** | ≤ 1,497 (first session has no prior-close anchor; see §9.1) | DERIVED |

**Mandatory Prior-Exposure Disclosure:**

> [!WARNING]
> The calendar period `2017-01-01` through `2022-12-31` was previously consumed as the In-Sample window for `HYP_003` (MEC-0013, Price-Only Opening Range Breakout). The following disclosures apply:
>
> 1. **Mechanism & Hypothesis Distinction:** `HYP_003` and MEC-0014A are mechanically, statistically, and theoretically distinct hypotheses (`HYP_003` evaluated local price breakout from the 09:30–09:34 opening range; MEC-0014A evaluates the predictive relation between the first-half-hour return including overnight and the final-half-hour return).
> 2. **Temporal Overlap Disclosure:** Their observed market-time intervals are **NOT disjoint**. The MEC-0014A $r_{1,t}$ predictor interval (previous market close through 10:00 ET) temporally contains the 09:30–09:34 opening-range window previously observed by `HYP_003`.
> 3. **Independence from Prior Results:** `HYP_003` is permanently `TERMINALLY_FALSIFIED_REJECTED` and sealed. No `HYP_003` return, parameter, optimization result, signal, or outcome is used to construct or tune MEC-0014A.
> 4. **Zero Prior MEC-0014 Return Computation:** Zero MEC-0014-specific returns, regressions, or signals have been computed on this period. The close-contract and transaction-contract qualification probes executed date-isolated API calls solely to qualify auction and endpoint semantics.
> 5. **Sample Purity Classification:** Despite the absence of prior MEC-0014 computation, the shared historical price path and prior aggregate market exposure mean this partition is **NOT** labeled a globally pristine discovery sample.

### 2.2 Holdout

| Parameter | Value | Classification |
| :--- | :--- | :--- |
| **Label** | `MEC_0014_STRATEGY_UNEXPOSED_HOLDOUT / TECHNICALLY_PROBED_IN_ISOLATED_INFRASTRUCTURE_SESSIONS` | RATIFIED |
| **Date Range** | `2023-01-01` through `2026-12-31` | SEALED |
| **Access Authorization** | STRICTLY FORBIDDEN until all four conditions in §2.3 are satisfied | SEALED |

**Mandatory Infrastructure-Probe Disclosure:**

> [!WARNING]
> The canonical repository provides evidence that the following isolated date(s) within the 2023–2026 period were accessed in non-strategy data-qualification probes:
>
> - `2023-09-15` — Isolated SIP infrastructure qualification session. Manifest reference: `SIP-QUAL-SPY-19647058`.
> - `2026-09-15` — Infrastructure availability probe (separate session).
>
> These constitute **technical infrastructure qualification**, not MEC-0014 strategy exposure. The canonical holdout label is therefore:
>
> `MEC_0014_STRATEGY_UNEXPOSED_HOLDOUT / TECHNICALLY_PROBED_IN_ISOLATED_INFRASTRUCTURE_SESSIONS`
>
> The claim "never technically accessed" is **NOT used** anywhere in this document. Zero OOS market-data access is authorized.

### 2.3 Holdout Release Conditions (ALL FOUR REQUIRED)

1. MEC-0014A statistical specification frozen and sealed (this document ratified by Human Operator).
2. `HYP_004` formally created through `ResearchReInceptionGate`.
3. MEC-0014A in-sample result produced under the frozen specification.
4. Explicit Human Operator authorization for OOS evaluation granted as a separate authorization event.

---

## 3. Return Variable Definitions & Endpoint Contracts

### 3.1 Primary Return Convention

**`GAO_BASELINE_RETURN_CONVENTION = SIMPLE_RETURN`**
**Authority: `LITERATURE_EXPLICIT`**

Gao et al. (2018) define the half-hour returns explicitly using simple (discrete) returns. The working paper states in the Data section (Equation 1):

$$r_{j,t} = \frac{p_{j,t}}{p_{j-1,t}} - 1$$

where $p_{j,t}$ denotes the transaction price at the $j$-th half-hour boundary on session $t$.

**`LOG_RETURN = SECONDARY_ROBUSTNESS_ONLY`**

The paper states that log returns yield similar results. Log-return calculations are therefore a secondary robustness analysis, not the primary specification. Log returns must not substitute for simple returns in the primary MEC-0014A regression.

### 3.2 Primary Price Type

**`GAO_BASELINE_PRICE_TYPE = TAQ_TRANSACTION_PRICE`**
**Authority: `LITERATURE_EXPLICIT`**

The Gao et al. baseline uses intraday SPY transaction prices drawn from TAQ. Quote-based alternatives (bid-to-bid, ask-to-ask, midquote-to-midquote) are reported by Gao et al. as robustness analyses, not the baseline.

| Price Type | Role | Authority |
| :--- | :--- | :--- |
| TAQ transaction price | **Baseline** | LITERATURE_EXPLICIT |
| Bid-to-bid | Secondary robustness | LITERATURE_EXPLICIT |
| Ask-to-ask | Secondary robustness | LITERATURE_EXPLICIT |
| Midquote-to-midquote | Secondary robustness | LITERATURE_EXPLICIT |

### 3.3 Half-Hour Boundary Prices & Endpoint Extraction Rule

**`GAO_ENDPOINT_SEMANTIC = RESOLVED_POINT_PRICE_AT_HALF_HOUR_BOUNDARY`**
**Authority: `LITERATURE_EXPLICIT`**

Gao et al. define prices at each half-hour boundary as follows for a regular-session day $t$:

| Symbol | Description | Literature Semantic |
| :--- | :--- | :--- |
| $p_{0,t}$ | Transaction price at previous regular-session market close (16:00 ET on session $t-1$) | Closing auction |
| $p_{1,t}$ | Transaction price at 10:00 ET on session $t$ | Point transaction price |
| $p_{12,t}$ | Transaction price at 15:30 ET on session $t$ | Point transaction price |
| $p_{13,t}$ | Transaction price at market close (16:00 ET on session $t$) | Closing auction |

The primary return variables are:

$$r_{1,t} = \frac{p_{1,t}}{p_{0,t}} - 1 \qquad \text{(Predictor: previous market close through 10:00 ET)}$$

$$r_{13,t} = \frac{p_{13,t}}{p_{12,t}} - 1 \qquad \text{(Target: 15:30 ET through 16:00 ET market close)}$$

**Critical semantic note:** $r_{1,t}$ explicitly spans the overnight non-trading period. It is **not** merely a 09:30–10:00 ET intraday return.

**ACASH Intraday Endpoint Implementation ($p_{1,t}$ at 10:00 ET and $p_{12,t}$ at 15:30 ET):**

**`ALPACA_INTRADAY_ENDPOINT_MAPPING = QUALIFIED_LAST_SIP_TRANSACTION_PRICE_AT_OR_BEFORE_BOUNDARY`**
**Authority: Canonical Transaction Contract Qualification — Commit `0590301b180389a15f598903425132b9b0386897`**

For boundary $B \in \{\text{10:00:00 ET}, \text{15:30:00 ET}\}$:
1. Identify maximal trade timestamp at or before boundary:
   $$T^* = \max(\{t \mid t \le B\})$$
2. Collect all raw SIP trade records occurring at timestamp $T^*$.
3. Ambiguity evaluation:
   - If all records at $T^*$ have exactly **one distinct price**: the deterministic boundary price is that unique price (`UNIQUE_BOUNDARY_PRICE` or `UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE`).
   - If multiple records at $T^*$ have **more than one distinct price**: the boundary is classified as `AMBIGUOUS_BOUNDARY_PRICE`, and the contract **fails closed** by rejecting the session from the regression sample.
4. Tie-breaking prohibition:
   $$\text{Never break a price tie using } \texttt{trade\_id}\text{, exchange, size, record order, or averaging.}$$
   `TRADE_ID_ORDERING_AUTHORITY = NOT_ESTABLISHED`.

> [!NOTE]
> **Scope Distinction (Qualified Provider Rule vs. Full-Sample Census):**
> The 6-session probe qualified the deterministic provider mapping rule and fail-closed handling (11 unique microsecond boundaries, 1 same-price tie, 0 distinct-price ambiguities). It does **NOT** prove that all 1,498 replication sessions will be non-ambiguous. During full-dataset construction, every session must evaluate this rule individually and fail closed on any ambiguity.

### 3.4 Market-Close Authority ($p_{0,t}$ and $p_{13,t}$)

**`ACASH_SPY_PROVIDER_PRIMARY_CLOSE = RESOLVED_NYSE_ARCA_QUALIFYING_CLOSING_AUCTION`**
**Authority: ACASH close-auction contract — Commit `793f018b0a06167599a37986c8f280459cf9f120`**

| Contract Parameter | Value | Classification |
| :--- | :--- | :--- |
| Provider endpoint | Alpaca SIP Historical Auctions — unique `x=P, c=6` print | RESOLVED |
| `SPY_PRIMARY_CLOSE_COVERAGE_2017_2022` | `COMPLETE_NORMAL_PATH` (1,498 / 1,498 unique primary auction sessions) | VERIFIED |
| `PREVIOUS_CLOSE_FALLBACK_POLICY` | `OPEN_REGIME_DEPENDENT` — not required for observed 2017–2022 sessions | OPEN for unobserved regimes |

---

## 4. Daily Session Eligibility Filter

### 4.1 Literature Trade-Count Filter

**`GAO_DAILY_TRADE_FILTER = DAILY_SPY_TRADE_COUNT >= 500`**
**Authority: `LITERATURE_EXPLICIT`**

Gao et al. (2018) explicitly state in the Data section that trading days with fewer than 500 trades are excluded from the sample. Independent replication literature (Limkriangkrai et al. 2023) confirms this filter was applied as described. This is a **primary sample eligibility rule**, not a secondary robustness filter.

### 4.2 Alpaca Provider Trade-Count Mapping

**`ALPACA_DAILY_TRADE_COUNT_MAPPING = QUALIFIED_PROVIDER_OPERATIONALIZATION`**
**Authority: Canonical Transaction Contract Qualification — Commit `0590301b180389a15f598903425132b9b0386897`**

Count raw Alpaca historical SIP trade records inside the canonical NYSE regular session satisfying:

$$\text{09:30:00} \le \text{timestamp} \le \text{16:00:00} \quad (\text{America/New\_York})$$

- **Predicate Classification:** `ACASH_PROVIDER_OPERATIONALIZATION_CHOICE`
- **TAQ Equivalence Limitation:** Exact record-for-record equivalence with Gao's historical TAQ extraction is **NOT claimed** (`NOT_ESTABLISHED`). Gao et al. define the regular session (9:30–16:00) and trading-day cutoff ($\ge 500$) without an endpoint inclusivity rule. The inclusive close boundary ($\le 16:00:00$) is an explicit ACASH operationalization choice to capture scheduled closing prints.
- **Empirical Probe Confirmation:** All 6 inspected sessions comfortably exceeded the threshold ($N \in [224090, 677263] \ge 500$). Exactly 0 trades were stamped at $16:00:00.000000$ across all 2.3M probed records.

---

## 5. Primary Regression Specification

### 5.1 Primary Equation

**Authority: `LITERATURE_EXPLICIT`**

$$r_{13,t} = \alpha + \beta \cdot r_{1,t} + \varepsilon_t$$

| Component | Specification | Authority |
| :--- | :--- | :--- |
| Dependent variable | $r_{13,t}$ (final-half-hour simple return, session $t$) | LITERATURE_EXPLICIT |
| Primary predictor | $r_{1,t}$ (first-half-hour simple return including overnight, session $t$) | LITERATURE_EXPLICIT |
| Intercept | Included ($\alpha$) | LITERATURE_EXPLICIT |
| Primary coefficient | $\hat{\beta}_{r_1}$ | LITERATURE_EXPLICIT |
| Primary directional claim | $\hat{\beta}_{r_1} > 0$ | LITERATURE_EXPLICIT |
| Model form | OLS | LITERATURE_EXPLICIT |

**`r12 = NOT INCLUDED IN PRIMARY REGRESSION`**

$r_{12,t}$ (15:00–15:30 ET return) and the joint specification $r_{1,t} + r_{12,t}$ are secondary literature analyses. They must not enter the primary MEC-0014A regression. Secondary specifications may only be analyzed as explicitly labeled robustness analyses, authorized separately, after the primary result is produced.

### 5.2 Primary Claim

**Primary MEC-0014A econometric claim:**

> On the preregistered contemporary SPY replication sample (`MEC_0014A_MECHANISM_SPECIFIC_REPLICATION_SAMPLE`, `NyseCa1Calendar` regular sessions, 2017-01-01 through 2022-12-31), the first-half-hour simple return measured from the previous market close positively predicts the last-half-hour simple return under the Gao et al. (2018) baseline predictive regression.

**This claim does NOT include:** trading profitability, Sharpe ratio, P&L, transaction costs, market-on-close execution, or position sizing. Those belong exclusively to MEC-0014B.

---

## 6. Inference Specification

### 6.1 Standard Error Estimator

**`GAO_INFERENCE_FAMILY = NEWEY_WEST_1987_HAC`**
**Authority: `LITERATURE_EXPLICIT`**

Gao et al. (2018) explicitly state the use of Newey-West (1987) robust standard errors throughout the paper.

### 6.2 Deterministic Lag Truncation Rule

**`GAO_NEWEY_WEST_LAG = NOT_STATED_IN_AUDITED_TEXT`**
**`ACASH_PRIMARY_NW_LAG_RULE = floor(4 * (T / 100)^(2/9))`**
**Classification: `ACASH_PREREGISTRATION_CHOICE`**

Because Gao et al. do not state the exact numerical lag truncation parameter $L$ in the audited methodology text, ACASH freezes a standard deterministic non-parametric lag selection rule prior to observing any return data:

$$L = \left\lfloor 4 \cdot \left(\frac{T}{100}\right)^{2/9} \right\rfloor$$

where $T$ is the final number of eligible sessions included in the primary regression.
- For $T \approx 1,480$, $L = \lfloor 4 \cdot (14.8)^{2/9} \rfloor = \lfloor 4 \cdot 1.815 \rfloor = 7$.
- This formula is frozen before any empirical return or regression result is observed.
- $L$ will **never be altered** or post-hoc tuned after viewing empirical results.

### 6.3 Primary Acceptance Criterion

**`MEC_0014A_PRIMARY_ACCEPTANCE = beta_r1 > 0 AND two-sided Newey-West-HAC p-value < 0.05`**
**Classification: `ACASH_PREREGISTRATION_CHOICE` (Human-Ratified)**

The primary econometric replication is accepted if and only if both conditions hold:
1. Directional consistency: $\hat{\beta}_{r_1} > 0$
2. Statistical significance: Two-sided $p$-value from Newey-West (1987) HAC standard error $< 0.05$ (equivalent to $t > 1.96$ asymptotically).

**Reporting Requirements (Regardless of Outcome):**
The final report must transparently disclose:
- Estimated intercept $\hat{\alpha}$
- Estimated slope $\hat{\beta}_{r_1}$
- Newey-West HAC standard error
- Newey-West HAC $t$-statistic
- Two-sided $p$-value
- In-sample $R^2$
- Final eligible observation count $T$
- Complete enumeration of excluded sessions with reason codes
- Descriptive reference significance levels (evaluated against 1% and 10% thresholds)

> [!IMPORTANT]
> The threshold $p < 0.05$ is permanently locked. No alternative threshold (e.g., $p < 0.10$ or one-sided test) may be substituted post-hoc to convert an inconclusive result into a pass. Economic profitability is NOT part of MEC-0014A acceptance.

---

## 7. Out-of-Sample Specification (Secondary Diagnostic)

### 7.1 Role of OOS Analysis

**`MEC_0014A_INTERNAL_OOS = SECONDARY_PREREGISTERED_DIAGNOSTIC`**
**Classification: `ACASH_PREREGISTRATION_CHOICE` (Human-Ratified)**

Internal OOS analysis is a **secondary diagnostic evaluation** consistent with Gao et al. §3. It is **NOT required** for the primary binary acceptance decision of MEC-0014A, which evaluates contemporary in-sample econometric replication ($r_{13} \sim r_1$).

### 7.2 Frozen Internal OOS Scheme

- **Initial Estimation Window:** `2017-01-01` through `2019-12-31` (3 calendar years, ~750 sessions)
- **Forecast Evaluation Window:** `2020-01-01` through `2022-12-31` (3 calendar years, ~750 sessions)
- **Method:** Recursive / expanding estimation window.
- **Re-estimation Frequency:** Monthly (at each month boundary, the regression sample expands by one month).
- **Point-in-Time Discipline:** The forecast for day $t$ uses information available strictly through session $t-1$.
- **Benchmark:** Historical mean of $r_{13}$ calculated over observations available through session $t-1$.
- **Evaluation Metric:** Gao-style out-of-sample $R^2_{OS}$ (Campbell & Thompson 2008):
  $$R^2_{OS} = 1 - \frac{\sum_{t} (r_{13,t} - \hat{r}_{13,t})^2}{\sum_{t} (r_{13,t} - \bar{r}_{13,t})^2}$$
- **OOS Boundary Preservation:** Zero data from $\ge \text{2023-01-01}$ may enter this analysis. The initialization and split parameters may not be altered after viewing results.

---

## 8. Corporate Action and Distribution Treatment

**`GAO_CORPORATE_ACTION_TREATMENT = NOT_EXPLICITLY_DOCUMENTED_IN_AUDITED_TEXT`**
**`GAO_CORPORATE_ACTION_PRIMARY_BASELINE = RAW_OBSERVED_TRANSACTION_PRICE_SEMANTICS`**

The audited Gao et al. methodology text states only that TAQ intraday trading prices are used; no dividend adjustment, total-return construction, or ex-dividend exclusion is documented.

- **Primary Baseline:** Raw observed transaction-price returns without dividend adjustment.
- **Prohibitions:** Do not dividend-adjust. Do not exclude ex-dividend dates. Do not use provider `adjustment=all`.
- **Secondary Robustness:** Any adjusted or ex-dividend-excluded variant must be preregistered separately as a secondary sensitivity analysis and cannot overwrite the primary result.

---

## 9. Session Eligibility & Fail-Closed Exclusion Rules

### 9.1 First Session
- $r_{1,t}$ requires $p_{0,t}$ (prior session close). The first calendar session in the replication sample (2017-01-03) has no qualified prior session within the sample.
- **Rule:** Session 2017-01-03 is **excluded** from regression observations (`LITERATURE_DERIVED`).

### 9.2 Early-Close Sessions
- `NyseCa1Calendar` identifies early-close (non-390-minute) sessions within 2017–2022.
- **Rule:** Early-close sessions are **excluded** from regression observations (`ACASH_PREREGISTRATION_CHOICE`).

### 9.3 Daily Trade-Count Ineligible Sessions
- Sessions with fewer than 500 raw regular-session SIP trades ($09:30:00 \le t \le 16:00:00$) are **excluded** (`GAO_DAILY_TRADE_FILTER >= 500`).

### 9.4 Missing Required Endpoint
- **`MISSING_REQUIRED_ENDPOINT = EXCLUDE_SESSION_FAIL_CLOSED`** (`ACASH_PREREGISTRATION_CHOICE`).
- If data lacks a qualifying price at any required endpoint ($p_{0,t}$, $p_{1,t}$, $p_{12,t}$, $p_{13,t}$), the session is excluded.
- Zero interpolation, zero forward/back fill, zero bar substitution, zero synthetic prices. Every exclusion must be explicitly enumerated in the audit log.

### 9.5 Ambiguous Boundary Price
- If more than one distinct price exists at maximal timestamp $T^* \le B$ for 10:00 ET or 15:30 ET, the session is classified as `AMBIGUOUS_BOUNDARY_PRICE` and **excluded** (`STRICT_FAIL_CLOSED`).
- No tie-breaking by trade ID, venue, or averaging.

### 9.6 Ambiguous Closing Auction
- Sessions with more than one qualifying `x=P, c=6` print are **excluded** (0 observed in 2017–2022).

---

## 10. Secondary Specifications — Quarantine Registry

The following specifications are quarantined from the primary MEC-0014A preregistered claim. They may only be analyzed as explicitly labeled robustness analyses, authorized separately, after the primary result is produced.

| Quarantined Specification | Quarantine Reason |
| :--- | :--- |
| Log-return return convention | Gao secondary robustness only |
| $r_{12}$ predictor inclusion; joint $r_{1,t} + r_{12,t}$ | Gao secondary specification; adds a selection degree of freedom |
| Bid-to-bid / ask-to-ask / midquote returns | Gao robustness; not baseline transaction price |
| VIX quintile conditioning | Additional data contract; post-hoc selection risk |
| High-volume day conditioning | Parameter optimization risk |
| Macro-news day subsample (FOMC/CPI/NFP) | Requires separate event calendar contract |
| Dividend-adjusted or ex-date-excluded analysis | Not established as Gao baseline; must be separately preregistered |
| Overnight-reversal decomposition of $r_1$ | Distinct mechanism (Iwanaga & Sakemoto 2026) |
| Cross-sectional extension | MEC-0015+ family |

---

## 11. Anti-P-Hacking Contract

After empirical execution begins, the following primary choices are **immutably frozen**. Any post-hoc modification to rescue, explain, or alter the result automatically reclassifies the modified analysis as a **distinct, separately labeled robustness study or new hypothesis**:

1. **Sample Partition:** 2017-01-01 through 2022-12-31 (`MEC_0014A_MECHANISM_SPECIFIC_REPLICATION_SAMPLE`).
2. **Return Convention:** Simple returns ($r_{j,t} = p_{j,t} / p_{j-1,t} - 1$).
3. **Endpoint Rule:** Last SIP transaction price at or before boundary with fail-closed ambiguity handling.
4. **Closing Authority:** Unique NYSE Arca closing auction (`x=P, c=6`).
5. **Trade-Count Definition:** Raw regular-session SIP count in $[09:30:00, 16:00:00]$.
6. **Eligibility Threshold:** Daily trade count $\ge 500$.
7. **Regression Formula:** $r_{13,t} = \alpha + \beta r_{1,t} + \varepsilon_t$.
8. **NW Lag Formula:** $L = \lfloor 4 \cdot (T / 100)^{2/9} \rfloor$.
9. **Significance Threshold:** Two-sided $p < 0.05$ and $\hat{\beta}_{r_1} > 0$.
10. **Corporate-Action Baseline:** Raw observed transaction prices (no dividend adjustment).
11. **Missing-Data Rule:** Fail-closed session exclusion.

---

## 12. Open Items Resolution & Final Pre-Registration Ledger

All previous open items are formally **RESOLVED** and ratified:

| ID | Description | Resolution Status | Authoritative Basis |
| :--- | :--- | :--- | :--- |
| **[OPN-END-01]** | Alpaca SIP intraday endpoint mapping for $p_{1,t}$ and $p_{12,t}$ | **RESOLVED** | `QUALIFIED_LAST_SIP_TRANSACTION_PRICE_AT_OR_BEFORE_BOUNDARY` (Commit `0590301`) |
| **[OPN-TCF-01]** | Alpaca provider daily trade-count mapping for $\ge 500$ filter | **RESOLVED** | `QUALIFIED_PROVIDER_OPERATIONALIZATION` in $[09:30:00, 16:00:00]$ (Commit `0590301`) |
| **[OPN-INF-01]** | Newey-West HAC lag truncation rule | **RESOLVED** | $L = \lfloor 4 \cdot (T / 100)^{2/9} \rfloor$ (`ACASH_PREREGISTRATION_CHOICE`) |
| **[OPN-INF-02]** | Binary acceptance criterion | **RESOLVED** | $\hat{\beta}_{r_1} > 0 \text{ AND } p < 0.05$ (`ACASH_PREREGISTRATION_CHOICE`) |
| **[OPN-OOS-01]** | Internal OOS initialization and estimation scheme | **RESOLVED** | `SECONDARY_PREREGISTERED_DIAGNOSTIC` (2017–2019 init, 2020–2022 eval, monthly expanding) |
| **[OPN-PART-01]** | Sample partition ratification | **RESOLVED** | 2017–2022 Replication Sample / 2023–2026 Holdout (`RATIFIED`) |

**Remaining Methodological Open Blockers for Primary MEC-0014A Test: NONE (0 OPEN).**

---

## 13. Governance Invariants

| Invariant | Status |
| :--- | :--- |
| `HYP_004` | NOT CREATED |
| `ResearchReInceptionGate` | NOT INVOKED |
| Empirical execution (any $r_{1,t}$, $r_{13,t}$, regression) | NOT AUTHORIZED |
| Market data retrieval (any new Alpaca API call) | ZERO |
| OOS access ($\ge 2023-01-01$) | STRICTLY FORBIDDEN |
| Capital | `$0.00` |
| `NO_REAL_ORDERS` | `true` |
| HYP_003 sealed artifacts | NOT MODIFIED |
| `docs/research/RESEARCH-INTAKE-MARKET-STRUCTURE-001.md` | NOT MODIFIED |
| Paper trading | NOT AUTHORIZED |
| Live trading | LOCKED |

---

## 14. Authoritative References

1. **Gao, Lei; Han, Yufeng; Li, Sophia Zhengzi; Zhou, Guofu (2018).** Market Intraday Momentum. *Journal of Financial Economics*, Vol. 129, Iss. 2, August 2018, pp. 394–414. DOI: [10.1016/j.jfineco.2018.05.009](https://doi.org/10.1016/j.jfineco.2018.05.009) — **Authority for: simple return convention (Eq. 1), log-return as robustness, transaction-price baseline, $\ge 500$ daily trade filter, regression form, NW1987 HAC, OOS recursive algorithm, positive $\beta$ direction, three-tier significance reporting.**

2. **Limkriangkrai, M., Chai, D., & Zheng, G. (2023).** Market intraday momentum: APAC evidence. *Pacific-Basin Finance Journal*, 80, 102086. DOI: [10.1016/j.pacfin.2023.102086](https://doi.org/10.1016/j.pacfin.2023.102086) — **Authority for: independent US replication confirming $\ge 500$ trade filter and baseline specification.**

3. **Newey, W.K., and West, K.D. (1987).** A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix. *Econometrica*, 55(3), 703–708. — **Inference estimator authority.**

4. **Campbell, J.Y., and Thompson, S.B. (2008).** Predicting Excess Stock Returns Out of Sample: Can Anything Beat the Historical Average? *Review of Financial Studies*, 21(4), 1509–1531. — **OOS $R^2$ metric authority.**

---

```text
PREREGISTRATION_STATUS = FINAL_PENDING_HYPOTHESIS_REGISTRATION
HYP_004 = NOT_CREATED
EMPIRICAL_EXECUTION = NOT_AUTHORIZED
OPEN_METHODOLOGICAL_BLOCKERS = 0
```
