# RI-14 — FVG / SMC (Fair Value Gap / Smart Money Concepts)

## 1. Intake Status
- Intake status: NEGATIVE_CONTROL_CANDIDATE
- Candidate role: NEGATIVE_CONTROL_CANDIDATE / LOW PRIORITY
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Mechanism under test: Does a mechanically defined three-candle gap contain incremental information beyond an ordinary matched price displacement?

## 3. Economic / Microstructure Rationale
Retail discretionary discourse claims that an FVG represents an "unbalanced institutional footprint" where price moved rapidly, omitting liquidity and creating an attraction for price to revisit the gap.

## 4. Null Hypothesis
$H_0$: Mechanically defined Fair Value Gaps exhibit zero incremental predictive power, retest frequency, or post-retest continuation edge compared to size-matched price displacements lacking the three-candle non-overlapping geometry.

## 5. Alternative Hypothesis
$H_1$: Prices revisit mechanically identified Fair Value Gaps with statistically significant excess frequency and exhibit directional bounces that survive transaction costs.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: No mature peer-reviewed evidence establishing the supplied FVG trading interpretation is present in the human-reviewed R0 corpus.
- **Preprint / Preliminary**: WEAK / CONFLICTING. There are 2026 preprints with conflicting conclusions. One reports reaction but little/no tradeable edge after costs and highlights coarse-bar bias. Another reports large results over a short sample. No mature literature consensus.
- **Source Claim Only**: Widespread promotional claims that FVGs offer effortless daily 1:2 RR setups.

## 7. What Existing Evidence Does NOT Support
Do not call "institutional imbalance" unless independently established. Scientific evidence does NOT support the claim that FVGs represent institutional balance sheets or guaranteed support/resistance levels.

## 8. Source Claims That Motivated This Intake
- `SR-01`: 9:30 open breakout combined with 1-minute FVG momentum.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED.
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: High-precision price bars and quote data.
- **Time Zone**: America/New_York (UTC storage).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED.
- **Historical Coverage**: NOT_YET_DETERMINED.
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative exchange data.

## 10. Data Provenance Contract Required Before Empirical Work
Strict machine-deterministic geometric specification of the FVG condition before accessing any market data.

## 11. Execution / Friction Requirements
- Full spread crossing and slippage modeling.
- Resolution of intrabar bar-path ambiguity when price enters the gap.

## 12. Confounders
- Coarse-bar bias: testing FVG rules on coarse bars without evaluating intrabar tick sequencing leads to massive overestimation of fill rates.
- Unconditional price drift.

## 13. Required Negative / Placebo Controls
- Required control: matched displacement without FVG geometry.
- Random gap placement control.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: HIGH.
- **Rationale**: Massive retail exposure and widespread post-hoc cherry-picking in online media.

## 15. Falsification Concept
Falsified if the conditional forward return following an FVG fill is statistically indistinguishable from a matched price displacement control, or if net returns are negative after transaction costs.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No gap size thresholds, timeframe selections, or take-profit rules are authorized.

## 17. Metrics
Retest probability vs. placebo, net expectancy after friction, bar-path sensitivity.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
NEGATIVE_CONTROL_CANDIDATE / LOW PRIORITY.

## 19. Open Questions
- Is the FVG phenomenon entirely explained by standard bid/ask bounce and coarse-bar discretization?
- Does conditioning on order flow imbalance at the gap boundary eliminate any apparent edge?

## 20. Next Permitted Action
remain on hold.
