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
Supply and demand imbalance at the best bid and ask (and across immediate market depth) exerts short-horizon mechanical price impact on subsequent trade prices.

## 3. Economic / Microstructure Rationale
In order-driven markets, prices change when aggressive market orders consume resting limit order book depth or when limit orders are cancelled. Net changes in bid and ask depth (Order Flow Imbalance) reflect real-time order queue dynamics that drive immediate price formation.

## 4. Null Hypothesis
$H_0$: Contemporaneous and lagged Order Flow Imbalance exhibits zero predictive information regarding subsequent mid-price changes over horizons from 100 milliseconds to 5 minutes.

## 5. Alternative Hypothesis
$H_1$: Order Flow Imbalance has a statistically significant positive relationship with contemporaneous and short-horizon future mid-price changes.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Cont, Kukanov, and Stoikov (2014, *Journal of Financial Econometrics*) mathematically formulate OFI and prove a strong, linear relationship between OFI and price impact in US equity markets.
- **Preprint / Preliminary**: Multi-level OFI incorporating deeper book layers (Level 2 depth) across futures and foreign exchange.
- **Source Claim Only**: Retail claims that "volume > 400" denotes a "whale" or guaranteed institutional entry.

## 7. What Existing Evidence Does NOT Support
Microstructure literature does NOT support the claim that an arbitrary raw volume threshold (e.g., 400 contracts) identifies a specific institutional trader or guarantees a profitable reversal/continuation without dynamic normalization.

## 8. Source Claims That Motivated This Intake
- `SR-02`: Footprint chart claims, volume profile balance/unbalance, "whale" threshold >400, delta flip.
- `SR-06`: Claims that volume spikes prove institutional accumulation.
- `SR-12`: Volume spike breakout settings.

## 9. Data Requirements
- **Instrument**: CME Index Futures (ES, NQ) or US Equities.
- **Frequency**: Order-by-order (L3) or top-of-book tick events (L1/L2).
- **Data Types**: Nanosecond-timestamped bid size, ask size, bid price, ask price, trade price, and trade size.
- **Time Zone**: UTC.
- **Vendor / Feed Semantics**: Direct exchange feeds (CME MDP 3.0, NASDAQ TotalView).
- **Historical Coverage**: Minimum 3 years high-resolution tick archives.
- **Authority Requirements**: CME or SIP direct historical files.

## 10. Data Provenance Contract Required Before Empirical Work
Deterministic timestamp sequencing, trade-to-quote matching latency bounds, and immutable feed checksums.

## 11. Execution / Friction Requirements
- Ultra-low latency execution simulation (queue position priority, cancel latency).
- Bid/ask spread crossing costs.
- Exchange clearing and regulatory fees.

## 12. Confounders
- High-frequency quote cancellations (spoofing / flickering liquidity).
- Latency between observation timestamp and order arrival timestamp.

## 13. Required Negative / Placebo Controls
- Shuffled order flow control: Permuting the trade/quote arrival sequence while holding total volume constant.
- Matched unconditional volume control.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: LOW.
- **Rationale**: ACASH has not previously researched order flow imbalance or L1/L2 microstructure signals in historical hypotheses.

## 15. Falsification Concept
Falsified if out-of-sample regressions of future mid-price changes on normalized OFI yield regression coefficients that are statistically indistinguishable from zero after transaction costs.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No arbitrary volume thresholds (e.g. 400) or lookback horizons are frozen.

## 17. Metrics
Linear impact coefficient ($R^2$), information coefficient (IC), realization after half-spread crossing.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
SATELLITE SHORTLIST B.

## 19. Open Questions
- What is the decay half-life of OFI predictive power across 1-second vs. 1-minute bars?
- How does book depth beyond the top tier (Level 2) improve OFI predictive content?

## 20. Next Permitted Action
zero-outcome data feasibility audit.
