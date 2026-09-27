# RI-05 — Dealer Gamma / GEX Regime

## 1. Intake Status
- Intake status: SUPPORTED_MECHANISM
- Candidate role: Satellite hold
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Dealer hedging under negative gamma may amplify price movements, while positive gamma may damp them.

## 3. Economic / Microstructure Rationale
Option market makers delta-hedge their option inventory. In a positive gamma regime, dealers buy underlying assets as prices fall and sell as prices rise, creating a stabilizing feedback loop. In a negative gamma regime, dealers sell as prices fall and buy as prices rise, amplifying directional price displacement.

## 4. Null Hypothesis
$H_0$: Aggregate estimated dealer gamma exposure has zero conditional relationship with realized underlying volatility or price continuation/reversal dynamics.

## 5. Alternative Hypothesis
$H_1$: Underlying volatility is significantly lower during positive GEX regimes than negative GEX regimes, and intraday mean reversion is significantly stronger when aggregate net dealer gamma is positive.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Literature on option market maker hedging channels and volatility feedback at the broad mechanism level.
- **Preprint / Preliminary**: Research on 0DTE options and their intraday hedging impact.
- **Source Claim Only**: Retail claims that GEX levels act as guaranteed support/resistance pivots or that touching a GEX level guarantees a tradeable bounce.

## 7. What Existing Evidence Does NOT Support
Literature does NOT support the claim that public Open Interest directly reveals exact dealer inventory sign. Retail GEX map != observed dealer inventory. Conceptual GEX is calculated as:
$$\text{GEX} \approx \text{OI} \times \text{option gamma} \times \text{multiplier} \times \text{inferred position sign}$$
Candidate GEX must be used primarily as REGIME / CONTEXT, not "touch level -> trade".

## 8. Source Claims That Motivated This Intake
- `SR-06`: Ninja GEX A+ checklist, positive gamma stabilization, negative gamma amplified movement.
- `SR-17`: MTraders OI/IV intraday zones, option dealer delta-neutral hedging claims.
- `SR-18`: Derivatives pricing and risk-neutral calibration discussions.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED (SPX, SPY, NDX, QQQ cited as ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: Complete option chain: strike, expiration, bid, ask, implied volatility, open interest.
- **Canonical Market Time Zone**: NOT_YET_DETERMINED_BY_INSTRUMENT (UTC storage required).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED.
- **Historical Coverage**: NOT_YET_DETERMINED.
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative exchange or clearinghouse archives.

## 10. Data Provenance Contract Required Before Empirical Work
Mandatory specification of the 7-point GEX provenance contract:
- `OI_SOURCE`: Authoritative clearinghouse / vendor.
- `OI_ASOF`: Exact publication timestamp.
- `OFFICIAL_OR_ESTIMATED`: Distinction between official clearinghouse OI and intraday estimated positioning.
- `DEALER_SIGN_METHOD`: Inferred net customer order flow sign / method.
- `GREEKS_MODEL`: Greeks calculation model.
- `OPTIONS_EXPIRY_SCOPE`: Near-month vs. full surface vs. 0DTE.
- `0DTE_INCLUDED`: Boolean flag.

## 11. Execution / Friction Requirements
- Executable underlying index / ETF friction.
- Not applicable for direct option execution under R0.

## 12. Confounders
- Unhedged institutional option positions.
- Inability to verify actual dealer book signs from anonymous clearing data.

## 13. Required Negative / Placebo Controls
- Shuffled strike open interest: Evaluating GEX calculations with permuted open interest across strikes.
- Random volatility regime control.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: LOW.
- **Rationale**: GEX has not been utilized in ACASH historical core strategies.

## 15. Falsification Concept
Falsified if realized intraday volatility and mean-reversion strength show zero statistically significant difference between positive and negative estimated GEX regimes across out-of-sample data.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No strike boundaries, zero-gamma levels, or indicator thresholds are authorized.

## 17. Metrics
Realized volatility conditional on GEX sign, autocorrelation of intraday returns, regime stability.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Satellite hold.

## 19. Open Questions
- What fraction of 0DTE option volume is hedged intraday vs. held to cash settlement?
- Does customer order flow classification significantly alter the estimated GEX sign?

## 20. Next Permitted Action
zero-outcome data feasibility audit.
