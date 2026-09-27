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
Option-implied volatility (IV) reflects market-wide risk-neutral expectations of underlying asset dispersion, establishing conditional regimes that alter the probability distributions of mean reversion versus trend continuation.

## 3. Economic / Microstructure Rationale
Implied volatility reflects the price of insurance against market fluctuations. A mathematical property of annualized implied volatility is the first-order daily expected move approximation:
$$	ext{Expected Move}_{	ext{daily}} pprox S 	imes rac{	ext{IV}}{\sqrt{252}}$$
For example, with an annualized IV of 24%, the daily expected move is approximately $24\% / \sqrt{252} pprox 1.51\%$. Extreme price deviations relative to this expected dispersion may condition market participant risk appetite and inventory constraints.

## 4. Null Hypothesis
$H_0$: Conditioning intraday or multi-day trading rules on option-implied volatility levels or expected-move boundaries provides zero incremental risk-adjusted performance over unconditional models.

## 5. Alternative Hypothesis
$H_1$: Conditioning price excursion strategies on option-implied expected-move boundaries significantly improves the Sortino ratio or tail-loss profile of mean-reversion or volatility-expansion models.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: The Variance Risk Premium (VRP) literature (Carr and Wu, Bollerslev) establishing that implied volatility systematically exceeds realized volatility on average.
- **Preprint / Preliminary**: Research on intraday volatility cones and expected-move containment.
- **Source Claim Only**: Claims that price touching a 1-standard-deviation IV boundary guarantees a 65–75% probability of reversal, or that open retests succeed 65% of the time.

## 7. What Existing Evidence Does NOT Support
Academic and mathematical theory does NOT support the claim that risk-neutral option-implied distributions represent physical real-world probabilities. A 1-standard-deviation boundary derived from risk-neutral option pricing does NOT imply a 68% or 65–75% physical probability of reversal.

## 8. Source Claims That Motivated This Intake
- `SR-17`: MTraders claims that IV 24 gives ~1.51% daily movement, open retest has 65% probability, and 1 SD boundaries have 65–75% reversal advantage.
- `SR-18`: Discussion of derivatives pricing and volatility surface calibration.

## 9. Data Requirements
- **Instrument**: Cboe VIX Index, SPX/SPY/QQQ ATM and OTM Implied Volatility surfaces.
- **Frequency**: Daily and intraday 1-minute IV snapshots.
- **Data Types**: Black-Scholes / binomial implied volatility surfaces, underlying prices.
- **Time Zone**: America/New_York (UTC).
- **Vendor / Feed Semantics**: Cboe live / EOD volatility indexes or direct options surface feeds.
- **Historical Coverage**: Minimum 10 years.
- **Authority Requirements**: Authoritative Cboe or OptionMetrics data.

## 10. Data Provenance Contract Required Before Empirical Work
Explicit validation of the implied volatility calculation engine and interest rate / dividend assumptions.

## 11. Execution / Friction Requirements
- Underlying trading frictions (bid/ask spread, commissions, borrow costs).

## 12. Confounders
- Macroeconomic announcements (CPI, FOMC) that cause sudden shifts in IV surfaces.
- Skewness and kurtosis deviations from lognormality.

## 13. Required Negative / Placebo Controls
- Realized volatility control: Compare implied volatility regimes against backward-looking historical realized volatility regimes.
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
Conditional Sortino ratio, tail drawdown reduction, calibration error.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Satellite contextual feature.

## 19. Open Questions
- Does 0DTE implied volatility provide more responsive intraday regime detection than 30-day VIX?
- How does the variance risk premium vary across intraday session hours?

## 20. Next Permitted Action
remain on hold.
