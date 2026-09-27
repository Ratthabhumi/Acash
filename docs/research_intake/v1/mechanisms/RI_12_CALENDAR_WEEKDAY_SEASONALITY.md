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
Conditional weekday/time distributions may differ due to recurring market flows or institutional behavior.

## 3. Economic / Microstructure Rationale
Institutional settlement schedules, cash flow allocations, and systematic rebalancing flows occur on structured calendar frequencies, creating recurrent liquidity asymmetries on specific weekdays.

## 4. Null Hypothesis
$H_0$: Daily and intraday return distributions are identically distributed across days of the week, exhibiting zero statistically significant calendar-dependent expected return differences.

## 5. Alternative Hypothesis
$H_1$: Specific weekday holding periods exhibit statistically significant positive or negative expected returns that persist across multiple independent macroeconomic regimes.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Historical weekday effects exist (French 1980, *Journal of Financial Economics*). Stability is weak and regime-dependent.
- **Preprint / Preliminary**: Contemporary studies showing decay or reversal of classical calendar anomalies due to algorithmic arbitrage.
- **Source Claim Only**: Claims that buying Monday morning when below a 25-day SMA and holding through Tuesday produces guaranteed 57.5% win rates and 1.49 profit factors.

## 7. What Existing Evidence Does NOT Support
Exact Monday below SMA25 buy, Tuesday exit is NOT scientific authority. It belongs strictly to `SR-09`. Literature does NOT support the claim that an arbitrary static rule maintains consistent outperformance across modern electronic trading decades.

## 8. Source Claims That Motivated This Intake
- `SR-09`: Dow Turnaround Tuesday (Monday 01:05 broker time below SMA25, hold through Tuesday 23:50).
- `SR-14`: Macro and seasonality strategy families.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED.
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: Closing prices and continuous rolled futures prices.
- **Time Zone**: America/New_York (UTC storage).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED.
- **Historical Coverage**: NOT_YET_DETERMINED.
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative long-horizon continuous historical data.

## 10. Data Provenance Contract Required Before Empirical Work
Explicit calendar definition accounting for exchange holiday observances and shortened trading sessions.

## 11. Execution / Friction Requirements
- Multi-day financing / overnight swap fees.
- Execution costs at non-standard session opens.

## 12. Confounders
- Structural equity market upward beta drift.
- Evolving market structure diminishing traditional weekend gaps.

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
No moving average lengths (e.g. SMA25) or day-of-week timing rules are authorized at R0.

## 17. Metrics
Regime stability t-statistic, sub-period consistency, excess return over equity beta.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Low priority.

## 19. Open Questions
- Has the institutional shift to passive indexing permanently eliminated the classic Tuesday reversal effect?
- Does the anomaly survive when benchmarked against an unconditional buy-and-hold index baseline?

## 20. Next Permitted Action
remain on hold.
