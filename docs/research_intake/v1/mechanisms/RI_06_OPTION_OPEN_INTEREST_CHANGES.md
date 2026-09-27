# RI-06 — Option Open Interest Changes

## 1. Intake Status
- Intake status: PROMISING_UNVERIFIED
- Candidate role: Satellite hold
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Daily changes in aggregate call and put open interest across strike distributions may convey incremental information regarding institutional positioning, hedging demand, or informed expectations of future underlying returns.

## 3. Economic / Microstructure Rationale
Substantial changes in open interest reflect the creation or closing of option contracts. Because informed participants and large hedgers frequently utilize options for non-linear payoff structures or leverage, net positioning changes across strikes may predict underlying price drift over multi-day horizons.

## 4. Null Hypothesis
$H_0$: Daily changes in option open interest contain zero predictive power regarding future underlying stock or index returns over horizons from 1 to 20 trading days.

## 5. Alternative Hypothesis
$H_1$: Net changes in call open interest relative to put open interest (or strike-specific clusters) exhibit a statistically significant relationship with subsequent underlying returns.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Literature documenting that option open interest changes predict underlying stock returns, particularly prior to major corporate announcements.
- **Preprint / Preliminary**: Studies on option pinning and open interest concentration near major expiration cycles.
- **Source Claim Only**: Claims that large open interest at a strike represents a guaranteed market-maker target or ceiling.

## 7. What Existing Evidence Does NOT Support
Evidence does NOT support the assertion that open interest equals directional buying. Every open option contract has both a long buyer and a short seller; open interest does not identify which counterparty was the aggressor or informed market participant.

## 8. Source Claims That Motivated This Intake
- `SR-17`: MTraders claims on open interest levels acting as price magnets or support/resistance zones.

## 9. Data Requirements
- **Instrument**: US Equities and Index Options (SPX, SPY, QQQ).
- **Frequency**: Daily clearinghouse open interest updates.
- **Data Types**: Official clearinghouse open interest, closing volume, and settlement prices by strike.
- **Time Zone**: America/New_York (UTC).
- **Vendor / Feed Semantics**: OCC (Options Clearing Corporation) or Cboe official EOD files.
- **Historical Coverage**: Minimum 5 years.
- **Authority Requirements**: Authoritative clearinghouse EOD data.

## 10. Data Provenance Contract Required Before Empirical Work
- Verification of exact clearinghouse publication timestamp (`OI_ASOF`).
- Absolute prohibition against using intraday volume as "intraday open interest" without explicit labeling.

## 11. Execution / Friction Requirements
- Underlying equity/ETF transaction fees and borrow costs if shorting.

## 12. Confounders
- Dividend play trades (box spreads, dividend capture volume inflating open interest).
- Offsetting spreads and multi-leg delta-neutral positions.

## 13. Required Negative / Placebo Controls
- Shuffled open interest distribution control.
- Random strike assignment baseline.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: LOW.
- **Rationale**: Not previously tested in ACASH hypotheses.

## 15. Falsification Concept
Falsified if portfolio sorting based on open interest changes yields zero risk-adjusted excess returns over an index buy-and-hold baseline.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No open interest thresholds, strike horizons, or lookback days are frozen.

## 17. Metrics
Fama-French factor alpha, Information Ratio, turnover.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Satellite hold.

## 19. Open Questions
- How does the explosion of 0DTE trading affect the informational content of traditional EOD open interest?
- Can dividend capture open interest be mechanically filtered from genuine directional positioning?

## 20. Next Permitted Action
remain on hold.
