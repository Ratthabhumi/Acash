# RI-12 — Calendar / Weekday Seasonality

## 1. Intake Status
- Intake status: PROMISING_UNVERIFIED
- Candidate role: Low priority
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Conditional return distributions across specific days of the week or calendar cycles exhibit non-random variations due to institutional settlement schedules, cash flow allocations, and systematic rebalancing flows.

## 3. Economic / Microstructure Rationale
Institutional fund flows, payroll allocations, option expiration cycles (e.g., Triple Witching), and treasury auction schedules occur on structured calendar frequencies, creating recurrent liquidity asymmetries on specific weekdays.

## 4. Null Hypothesis
$H_0$: Daily and intraday return distributions are identically distributed across days of the week, exhibiting zero statistically significant calendar-dependent expected return differences.

## 5. Alternative Hypothesis
$H_1$: Specific weekday holding periods exhibit statistically significant positive or negative expected returns that persist across multiple independent macroeconomic regimes.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: French (1980, *Journal of Financial Economics*) documenting the weekend effect in US equities; subsequent literature on turn-of-the-month and holiday effects.
- **Preprint / Preliminary**: Contemporary studies showing decay or reversal of classical calendar anomalies due to algorithmic arbitrage.
- **Source Claim Only**: Claims that buying Monday morning when below a 25-day SMA and holding through Tuesday produces guaranteed 57.5% win rates and 1.49 profit factors.

## 7. What Existing Evidence Does NOT Support
Literature does NOT support the claim that an arbitrary static rule (such as the "Turnaround Tuesday" Dow rule below SMA 25) maintains consistent, stable outperformance across modern electronic trading decades without severe regime decay.

## 8. Source Claims That Motivated This Intake
- `SR-09`: Dow Turnaround Tuesday (Monday 01:05 broker time below SMA25, hold through Tuesday 23:50).
- `SR-14`: Macro and seasonality strategy families.

## 9. Data Requirements
- **Instrument**: Dow Jones Industrial Average (DJI / YM futures), S&P 500 (SPY / ES).
- **Frequency**: Daily and hourly bars.
- **Data Types**: Cash index closes and continuous rolled futures prices.
- **Time Zone**: America/New_York (UTC).
- **Vendor / Feed Semantics**: CME Globex and NYSE/NASDAQ consolidated archives.
- **Historical Coverage**: Minimum 30 years (covering multi-decade calendar shifts).
- **Authority Requirements**: Authoritative long-horizon continuous historical data.

## 10. Data Provenance Contract Required Before Empirical Work
Explicit calendar definition accounting for exchange holiday observances, Monday holidays, and shortened trading sessions.

## 11. Execution / Friction Requirements
- Multi-day financing / overnight swap fees (holding across multiple nights).
- Execution costs at non-standard session opens (e.g., 01:05 broker time spreads).

## 12. Confounders
- Structural equity market upward beta drift.
- Evolving market structure (electronic 24/5 futures diminishing traditional weekend gaps).

## 13. Required Negative / Placebo Controls
- Day-of-week permuted control: Shuffling weekday labels across historical bars.
- Matched holding-period random entry baseline.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: HIGH.
- **Rationale**: Calendar anomalies are notorious for post-publication decay and severe data snooping.

## 15. Falsification Concept
Falsified if out-of-sample forward weekday returns exhibit zero statistically significant deviation from unconditional daily equity drift after accounting for financing and transaction costs.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No moving average lengths (e.g. SMA 25) or day-of-week timing rules are authorized at R0.

## 17. Metrics
Regime stability t-statistic, sub-period Sharpe ratio consistency, excess return over equity beta.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Low priority.

## 19. Open Questions
- Has the institutional shift to passive indexing and daily ETF creations permanently eliminated the classic Tuesday reversal effect?
- Does the anomaly survive when benchmarked against an unconditional buy-and-hold index baseline?

## 20. Next Permitted Action
remain on hold.
