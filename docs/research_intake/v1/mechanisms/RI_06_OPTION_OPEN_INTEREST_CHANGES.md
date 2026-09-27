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
Changes in call and put open interest may contain incremental information regarding future underlying returns or positioning state.

## 3. Economic / Microstructure Rationale
Changes in open interest reflect the net creation or destruction of option contracts. Because informed participants and large hedgers frequently utilize options, aggregate positioning shifts across strikes may contain informational content.

## 4. Null Hypothesis
$H_0$: Changes in option open interest contain zero predictive power regarding future underlying stock or index returns over any holding horizon beyond unconditional baselines.

## 5. Alternative Hypothesis
$H_1$: Net changes in call open interest relative to put open interest (or strike-specific clusters) exhibit a statistically significant relationship with subsequent underlying returns.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Literature documenting that option open interest changes predict underlying stock returns in moderate literature support.
- **Preprint / Preliminary**: Studies on option pinning and open interest concentration near major expiration cycles.
- **Source Claim Only**: Claims that large open interest at a strike represents a guaranteed market-maker target or ceiling.

## 7. What Existing Evidence Does NOT Support
Critical distinctions: OI != directional bullish exposure. Every open contract has both long and short parties. OI does not directly identify market-maker side. Official CME OI is not magical real-time intraday dealer inventory. If "intraday OI" is estimated, it MUST be labeled model-estimated positioning.

## 8. Source Claims That Motivated This Intake
- `SR-17`: MTraders claims on open interest levels acting as price magnets or support/resistance zones.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED (Equities and Index Options cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: Official clearinghouse open interest, closing volume, and settlement prices where execution semantics require them.
- **Canonical Market Time Zone**: NOT_YET_DETERMINED_BY_INSTRUMENT (UTC storage required).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED.
- **Historical Coverage**: NOT_YET_DETERMINED.
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative clearinghouse EOD data.

## 10. Data Provenance Contract Required Before Empirical Work
Verification of exact clearinghouse publication timestamp (`OI_ASOF`) and official clearinghouse designation.

## 11. Execution / Friction Requirements
- Underlying equity/ETF transaction fees and borrow costs if shorting.

## 12. Confounders
- Dividend play trades inflating open interest artificially.
- Offsetting multi-leg delta-neutral positions.

## 13. Required Negative / Placebo Controls
- Shuffled open interest distribution control.
- Random strike assignment baseline.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: LOW.
- **Rationale**: Not previously tested in ACASH hypotheses.

## 15. Falsification Concept
Falsified if portfolio sorting based on open interest changes yields zero risk-adjusted excess returns over an index baseline.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No open interest thresholds, strike horizons, or lookback days are authorized.

## 17. Metrics
Factor alpha, Information Ratio, turnover.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Satellite hold.

## 19. Open Questions
- How does 0DTE trading affect the informational content of traditional EOD open interest?
- Can dividend capture open interest be mechanically separated from directional positioning?

## 20. Next Permitted Action
remain on hold.
