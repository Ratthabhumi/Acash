# RI-03 — Order Flow Imbalance (OFI)

## 1. Intake Status
- Intake status: SUPPORTED_MECHANISM
- Candidate role: SATELLITE SHORTLIST B
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Supply and demand imbalance at the best bid and ask (and across immediate market depth) may explain or predict short-horizon price impact.

## 3. Economic / Microstructure Rationale
In order-driven markets, prices change when aggressive market orders consume resting limit order book depth or when limit orders are cancelled. Net changes in bid and ask depth (Order Flow Imbalance) reflect real-time queue dynamics that drive immediate price formation.

## 4. Null Hypothesis
$H_0$: Order Flow Imbalance contains zero incremental short-horizon price information beyond appropriate matched controls.

## 5. Alternative Hypothesis
$H_1$: Order Flow Imbalance contains incremental short-horizon price information beyond appropriate matched controls.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Cont, Kukanov, and Stoikov (2014, *Journal of Financial Econometrics*) mathematically formulate OFI and document/estimate a strong, approximately linear relationship between OFI and short-horizon price impact, with impact depending on depth.
- **Preprint / Preliminary**: Multi-level OFI incorporating deeper book layers (Level 2 depth) across futures and equities.
- **Source Claim Only**: Retail claims that "volume > 400" denotes a "whale" or guaranteed institutional entry.

## 7. What Existing Evidence Does NOT Support
Microstructure literature does NOT support the claim that an arbitrary raw volume threshold (e.g., 400 contracts) identifies a specific participant or guarantees a profitable reversal/continuation. Volume must be normalized by instrument, time-of-day, depth, and volume regime.

## 8. Source Claims That Motivated This Intake
- `SR-02`: Footprint chart claims, volume profile balance/unbalance, "whale" threshold >400, delta flip.
- `SR-06`: Claims that volume spikes indicate institutional accumulation.
- `SR-12`: Volume spike breakout settings.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED (Index Futures or Equities cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: Historical quote/L1 event data, bid size, ask size, bid price, ask price, and trade prints.
- **Canonical Market Time Zone**: NOT_YET_DETERMINED_BY_INSTRUMENT (UTC storage required).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED (direct exchange order-book feeds cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Historical Coverage**: NOT_YET_DETERMINED.
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative exchange or consolidated tape archives.

## 10. Data Provenance Contract Required Before Empirical Work
Deterministic timestamp sequencing, trade-to-quote matching latency bounds, and immutable feed checksums.

## 11. Execution / Friction Requirements
- Latency execution modeling (queue position priority, cancel latency).
- Bid/ask spread crossing costs.
- Exchange clearing and regulatory fees.

## 12. Confounders
- High-frequency quote cancellations (flickering liquidity).
- Latency between observation timestamp and order arrival timestamp.

## 13. Required Negative / Placebo Controls
- Shuffled or permuted order flow control: Permuting the trade/quote arrival sequence while holding total volume constant.
- Matched-flow control.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: LOW.
- **Rationale**: ACASH has not previously researched order flow imbalance or L1/L2 microstructure signals in historical hypotheses.

## 15. Falsification Concept
Falsified if out-of-sample regressions of future mid-price changes on normalized OFI yield coefficients statistically indistinguishable from zero after transaction costs.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No arbitrary volume thresholds (e.g. 400), normalization constants, or predictive horizons are authorized at R0; predictive horizon remains NOT_YET_PREREGISTERED.

## 17. Metrics
Linear impact coefficient, information coefficient (IC), realization after spread crossing.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
SATELLITE SHORTLIST B.

## 19. Open Questions
- What is the empirical decay half-life of OFI information content across different aggregation frequencies?
- How does book depth beyond top of book enhance OFI predictive content?

## 20. Next Permitted Action
zero-outcome data feasibility audit.
