# RI-08 — IV / Expected-Move Regime

## 1. Intake Status
- Intake status: SUPPORTED_MECHANISM
- Candidate role: Satellite contextual feature
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Option-implied uncertainty may alter conditional probabilities of continuation versus mean reversion.

## 3. Economic / Microstructure Rationale
Implied volatility reflects market pricing of uncertainty. An established mathematical example is:
$$\text{annualized IV } 24\% / \sqrt{252} \approx 1.51\% \text{ daily volatility}$$
as a first-order square-root-of-time approximation. Option-implied dispersion may condition market participant risk appetite and inventory constraints.

## 4. Null Hypothesis
$H_0$: Conditioning intraday or multi-day trading rules on option-implied volatility levels or expected-move boundaries provides zero incremental risk-adjusted performance over unconditional baselines.

## 5. Alternative Hypothesis
$H_1$: Conditioning price excursion strategies on option-implied expected-move boundaries significantly improves the risk-adjusted profile of mean-reversion or volatility-expansion models.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Established option pricing and implied volatility literature supplied by human authority.
- **Preprint / Preliminary**: Research on intraday volatility regimes and dispersion boundaries.
- **Source Claim Only**: Claims that open retest = 65%, 1 SD sell = 65–75% reversal advantage, or that IV levels reveal directional trajectory.

## 7. What Existing Evidence Does NOT Support
This mathematical property DOES NOT imply:
- touch +1 SD -> reverse
- $\pm 1$ SD -> 68% reversal
- IV high -> direction known
Risk-neutral option-implied distribution != direct physical probability. Claims such as open retest = 65% or 1 SD sell = 65–75% are purely `EXTERNAL_UNVERIFIED_CLAIM`.

## 8. Source Claims That Motivated This Intake
- `SR-17`: MTraders claims that IV 24 gives ~1.51% daily movement, open retest has 65% probability, and 1 SD boundaries have 65–75% reversal advantage.
- `SR-18`: Discussion of derivatives pricing and volatility surface calibration.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED (VIX, SPX, SPY, QQQ cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Frequency**: NOT_YET_DETERMINED (1-minute IV snapshots cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Data Types**: Implied volatility measures and underlying prices.
- **Time Zone**: America/New_York (UTC storage).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED.
- **Historical Coverage**: NOT_YET_DETERMINED (10 years cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Provider**: NOT_YET_DETERMINED (OptionMetrics cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative exchange volatility data.

## 10. Data Provenance Contract Required Before Empirical Work
Explicit validation of the implied volatility calculation engine and interest rate / dividend assumptions.

## 11. Execution / Friction Requirements
- Underlying trading frictions (bid/ask spread, commissions, borrow costs).

## 12. Confounders
- Macroeconomic announcements that cause sudden shifts in IV surfaces.
- Deviations from lognormality (skewness and kurtosis).

## 13. Required Negative / Placebo Controls
- Realized volatility control: Compare implied volatility regimes against historical realized volatility regimes.
- Random boundary placement control.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: LOW.
- **Rationale**: IV regimes have not been utilized in ACASH active core strategies.

## 15. Falsification Concept
Falsified if strategies conditioned on option-implied expected-move boundaries demonstrate zero improvement in risk-adjusted performance compared to unconditional or historical-volatility baselines.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No arbitrary deviation boundaries (e.g. $\pm 1$ SD) or win-rate assumptions (e.g. 65%) are authorized.

## 17. Metrics
Conditional risk-adjusted return, tail drawdown reduction, calibration error.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Satellite contextual feature.

## 19. Open Questions
- Does short-dated implied volatility provide more responsive intraday regime detection than 30-day index IV?
- How does the variance risk premium behave across intraday session hours?

## 20. Next Permitted Action
remain on hold.
