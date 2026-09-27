# RI-11 — Mean Reversion / Overreaction

## 1. Intake Status
- Intake status: PROMISING_UNVERIFIED
- Candidate role: Potential family
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Some extreme short-horizon price displacement may contain a temporary component that subsequently reverses.

## 3. Economic / Microstructure Rationale
Large orders or temporary liquidity imbalances can push market prices temporarily away from short-term equilibrium. As passive liquidity providers replenish the book and aggressive pressure subsides, prices may exhibit mean-reverting tendencies.

## 4. Null Hypothesis
$H_0$: Extreme short-horizon price deviations exhibit zero tendency toward mean reversion beyond what is expected from unconditional price drift.

## 5. Alternative Hypothesis
$H_1$: Normalized price excursions beyond extreme statistical thresholds exhibit negative autocorrelation and positive expected return in the counter-displacement direction, net of execution frictions.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Empirical literature on short-term return reversals and bid-ask bounce; evidence is regime- and horizon-dependent.
- **Preprint / Preliminary**: Studies on intraday mean reversion conditioned on order book replenishment.
- **Source Claim Only**: Claims that "prices always return to the mean" or that specific indicator thresholds guarantee high-probability rebounds.

## 7. What Existing Evidence Does NOT Support
Do NOT state: "prices always return to the mean". Mean reversion and momentum can coexist at different horizons. Extreme price displacement can reflect genuine permanent information; counter-trend trading without strict risk controls risks severe tail losses during structural regime shifts.

## 8. Source Claims That Motivated This Intake
- `SR-14`: Broad macro strategy families (mean reversion).
- `SR-17`: MTraders zone mean-reversion narratives and 1 SD abnormal price bounce claims.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED.
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: Executed trades, quotes, and order book data.
- **Canonical Market Time Zone**: NOT_YET_DETERMINED_BY_INSTRUMENT (UTC storage required).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED.
- **Historical Coverage**: NOT_YET_DETERMINED.
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative exchange data.

## 10. Data Provenance Contract Required Before Empirical Work
Corporate action adjustments must be verified to prevent artificial price gap signals.

## 11. Execution / Friction Requirements
- Asymmetric slippage: buying into falling momentum often incurs severe execution drag.
- Short borrow availability and borrow fees for overbought short candidates.

## 12. Confounders
- Structural momentum regimes where mean-reversion strategies suffer severe drawdowns.
- Market-wide factor shocks.

## 13. Required Negative / Placebo Controls
- Required controls: matched extreme moves, volatility, market beta, time-of-day, regime.
- Shuffled sequence control.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: LOW.
- **Rationale**: Not directly researched in ACASH historical core strategies.

## 15. Falsification Concept
Falsified if out-of-sample counter-trend strategies experience negative risk-adjusted returns or excessive tail risk that cannot be mitigated by volatility scaling.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No RSI parameters, Bollinger Band widths, or lookback windows are authorized at R0.

## 17. Metrics
Gain-to-Pain ratio, Tail Risk, Maximum Adverse Excursion (MAE).
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Potential family.

## 19. Open Questions
- What conditioning variable best separates transitory noise from permanent fundamental re-pricing?
- How does mean reversion decay across different intraday time windows?

## 20. Next Permitted Action
remain on hold.
