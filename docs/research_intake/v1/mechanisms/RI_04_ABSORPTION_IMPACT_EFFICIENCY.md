# RI-04 — Absorption / Impact Efficiency

## 1. Intake Status
- Intake status: PROMISING_UNVERIFIED
- Candidate role: microstructure satellite
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
For extreme aggressive flow, low price response may represent a different liquidity state than high price response.

## 3. Economic / Microstructure Rationale
When large aggressive market orders are executed without producing proportional price displacement, passive market participants are absorbing the flow at resting limit levels (absorption/liquidity-state candidate). Conversely, large flow with strong price response represents a continuation-type state candidate.

## 4. Null Hypothesis
$H_0$: The ratio of price displacement to order flow volume contains zero predictive information regarding subsequent price continuation or mean reversion beyond unconditional controls.

## 5. Alternative Hypothesis
$H_1$: Abnormally low price response during large aggressive flow predicts subsequent price stall or reversal, whereas abnormally high price response predicts directional continuation.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Literature on price impact of order flow and state-dependent market liquidity.
- **Preprint / Preliminary**: Microstructure studies examining liquidity absorption near support/resistance levels.
- **Source Claim Only**: Footprint claims that "absorption at footprint pivots guarantees a reversal".

## 7. What Existing Evidence Does NOT Support
Literature does NOT support the claim that discretionary footprint delta numbers alone guarantee profitable trading signals without conditioning on depth and volatility regimes. Exact profitable signal is UNVERIFIED.

## 8. Source Claims That Motivated This Intake
- `SR-02`: Footprint delta flip, large volume with no follow-through interpreted as absorption.
- `SR-06`: High-volume stall near resistance levels.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED (Index Futures cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: Executed aggressive trade volume vs. resting limit depth changes.
- **Time Zone**: UTC.
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED.
- **Historical Coverage**: NOT_YET_DETERMINED.
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative tick data with depth snapshots.

## 10. Data Provenance Contract Required Before Empirical Work
Explicit verification of trade aggressor classification methods.

## 11. Execution / Friction Requirements
- Passive execution queue modeling.
- Half-spread crossing penalty on failed absorption signals.
- Exchange clearing fees.

## 12. Confounders
- Hidden iceberg orders that disguise true resting liquidity.
- Cross-market arbitrage flows between cash index and futures.

## 13. Required Negative / Placebo Controls
- Volume-matched random price displacement control.
- Time-shuffled order book depth events.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: LOW.
- **Rationale**: Novel microstructure mechanism within ACASH research corpus.

## 15. Falsification Concept
Falsified if the conditional distribution of post-absorption returns is symmetric and identical to unconditional price drift.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
The conceptual diagnostic $\text{impact\_efficiency} \approx |\Delta P| / |\text{OFI}|$ is a theoretical construct; no window or numerical threshold is frozen.

## 17. Metrics
Conditional return asymmetry, probability of stall, execution survival rate.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
microstructure satellite.

## 19. Open Questions
- Can absorption be measured reliably on aggregated bars or is sub-second depth mandatory?
- How frequently does passive absorption turn into aggressive breakthrough?

## 20. Next Permitted Action
remain on hold.
