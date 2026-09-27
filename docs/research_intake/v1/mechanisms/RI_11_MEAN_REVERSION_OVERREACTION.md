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
Extreme short-horizon price displacements driven by temporary liquidity shortages, order execution imbalances, or investor overreaction contain a transitory component that subsequently mean-reverts toward equilibrium.

## 3. Economic / Microstructure Rationale
Large institutional block trades or liquidity sweeps can temporarily push market prices beyond fundamental values, consuming all available resting depth. As liquidity providers replenish the book and aggressive pressure dissipates, prices tend to snap back toward the pre-displacement level.

## 4. Null Hypothesis
$H_0$: Extreme short-horizon price deviations from rolling moving averages or equilibrium bands exhibit zero tendency toward mean reversion beyond what is expected from a geometric random walk.

## 5. Alternative Hypothesis
$H_1$: Normalized price excursions beyond extreme statistical thresholds exhibit negative autocorrelation and positive expected return in the counter-displacement direction, net of execution frictions.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Literature on short-term return reversals and bid-ask bounce (Jegadeesh 1990; Lehmann 1990).
- **Preprint / Preliminary**: High-frequency mean reversion conditioned on order book replenishment.
- **Source Claim Only**: Claims that "prices always return to the mean" or that specific indicator thresholds (e.g., RSI < 30 or Bollinger 2 SD) guarantee high-probability rebounds.

## 7. What Existing Evidence Does NOT Support
Theory and empirical evidence do NOT support the claim that prices "always" return to the mean. Extreme price displacement can reflect genuine permanent information; counter-trend trading without strict risk controls risks severe tail losses during structural regime shifts.

## 8. Source Claims That Motivated This Intake
- `SR-14`: Broad macro strategy families (mean reversion).
- `SR-17`: MTraders zone mean-reversion narratives and 1 SD abnormal price bounce claims.

## 9. Data Requirements
- **Instrument**: US Equities (S&P 500 constituents) and Index Futures.
- **Frequency**: 1-minute to daily bars.
- **Data Types**: High-precision trade and quote data.
- **Time Zone**: America/New_York (UTC).
- **Vendor / Feed Semantics**: Consolidated Tape SIP / CME direct.
- **Historical Coverage**: Minimum 10 years.
- **Authority Requirements**: Authoritative exchange data.

## 10. Data Provenance Contract Required Before Empirical Work
Corporate action adjustments (splits, cash dividends) must be verified to prevent artificial price gap signals.

## 11. Execution / Friction Requirements
- Asymmetric slippage: buying into falling knives often incurs severe negative execution slippage.
- Short borrow availability and borrow fees for overbought short candidates.

## 12. Confounders
- Structural momentum regimes where mean-reversion strategies suffer catastrophic drawdowns.
- Market-wide factor shocks (macro beta shocks).

## 13. Required Negative / Placebo Controls
- Matched price displacement control: Comparing extreme moves with and without liquidity replenishment.
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
Gain-to-Pain ratio, Tail Risk (Expected Shortfall), Maximum Adverse Excursion (MAE).
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Potential family.

## 19. Open Questions
- What conditioning variable (e.g., volume exhaustion, OFI flip) best separates transitory noise from permanent fundamental re-pricing?
- How does mean reversion decay across different intraday time windows?

## 20. Next Permitted Action
remain on hold.
