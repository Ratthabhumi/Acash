# RI-07 — Intraday Option Flow

## 1. Intake Status
- Intake status: PROMISING_UNVERIFIED
- Candidate role: Research watchlist
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Signed option order imbalance may contain informed-flow information beyond end-of-day open interest.

## 3. Economic / Microstructure Rationale
Informed market participants with short-lived private information may trade in the option market to obtain leverage. Market makers filling these orders may hedge in the underlying market, creating mechanical price transmission.

## 4. Null Hypothesis
$H_0$: Intraday signed option order imbalance provides zero incremental forecast power for underlying asset price movements beyond underlying order flow.

## 5. Alternative Hypothesis
$H_1$: Aggressive option volume imbalance significantly predicts short-horizon underlying price drift.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Literature on informed option trading and lead-lag dynamics between option order flow and underlying stocks.
- **Preprint / Preliminary**: 2026 preprints analyzing intraday option order imbalance and underlying price impact.
- **Source Claim Only**: Claims that scanning for "unusual option sweeps" produces instant high-probability directional edges.

## 7. What Existing Evidence Does NOT Support
Critical distinction: ORDER FLOW != OPEN INTEREST. Flow represents current aggressive trading activity; OI represents outstanding aggregate inventory. Order flow does not automatically equal directional conviction, as large blocks often represent delta-neutral hedging.

## 8. Source Claims That Motivated This Intake
- `SR-17`: MTraders intraday option flow and market-maker reaction narratives.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED.
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: Option trade and quote prints.
- **Canonical Market Time Zone**: NOT_YET_DETERMINED_BY_INSTRUMENT (UTC storage required).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED (OPRA cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Historical Coverage**: NOT_YET_DETERMINED.
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative consolidated option tape.

## 10. Data Provenance Contract Required Before Empirical Work
Trade-to-quote matching algorithms must be formally validated and locked before empirical evaluation.

## 11. Execution / Friction Requirements
- Executable underlying transaction costs and market impact.
- Option data infrastructure bandwidth and storage costs.

## 12. Confounders
- Complex multi-leg spread trades misclassified as outright directional sweeps.
- Hedging activity by market makers in competing venues.

## 13. Required Negative / Placebo Controls
- Randomly signed option volume control.
- Time-permuted option flow series.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: LOW.
- **Rationale**: Completely unresearched within ACASH historical archives.

## 15. Falsification Concept
Falsified if out-of-sample forward underlying returns conditional on signed option flow fail to exceed underlying transaction costs.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No trade size filters, premium thresholds, or expiration filters are authorized at R0.

## 17. Metrics
Information Coefficient (IC), cumulative return net of spread, Sharpe Ratio.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Research watchlist.

## 19. Open Questions
- What is the data burden and computational overhead of reconstructing signed option flow?
- Does option flow offer incremental information beyond what is already visible in cash market order flow?

## 20. Next Permitted Action
remain on hold.
