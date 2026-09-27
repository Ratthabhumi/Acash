# RI-13 — Relative-Value / Pairs Stat-Arb

## 1. Intake Status
- Intake status: SUPPORTED_MECHANISM
- Candidate role: Separate advanced sleeve
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
The relative price spread between two economically linked or cointegrated securities exhibits temporary divergence due to idiosyncratic liquidity shocks, followed by mean-reverting convergence driven by arbitrage capital.

## 3. Economic / Microstructure Rationale
Securities with shared fundamental cash flows, identical underlying collateral, or strong industry linkages share common factor risks. When temporary non-fundamental order flow forces their price ratio away from its long-run equilibrium, statistical arbitrageurs supply liquidity, profiting as the spread reverts.

## 4. Null Hypothesis
$H_0$: The price spread between economically linked pairs exhibits zero stationarity or mean-reverting predictability beyond random walk drift, and apparent convergence is an artifact of in-sample cointegration testing.

## 5. Alternative Hypothesis
$H_1$: Economically selected and cointegrated pairs exhibit statistically significant mean-reverting spread dynamics that generate positive risk-adjusted returns after full accounting for execution and short-borrow frictions.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Gatev, Goetzmann, and Rouwenhorst (2006, *Review of Financial Studies*) documenting landmark empirical results for pairs trading in US equities; extensive literature on cointegration (Engle-Granger, Johansen).
- **Preprint / Preliminary**: Machine learning and copula-based non-linear pairs trading models.
- **Source Claim Only**: Generic claims that any correlated assets can be traded profitably using simple Bollinger bands.

## 7. What Existing Evidence Does NOT Support
Literature does NOT support the claim that simple historical correlation implies cointegration or tradeability. Unanchored correlation pairs frequently decouple permanently (structural breaks), resulting in catastrophic divergence losses.

## 8. Source Claims That Motivated This Intake
- `SR-14`: Macro and statistical arbitrage strategy families.

## 9. Data Requirements
- **Instrument**: Highly liquid US Equities, ETF pairs (e.g., XOM vs. CVX, SPY vs. QQQ), or Futures spreads.
- **Frequency**: 1-minute to daily closing bars.
- **Data Types**: Synchronized trade and quote timestamps for both pair legs.
- **Time Zone**: America/New_York (UTC).
- **Vendor / Feed Semantics**: Consolidated Tape SIP.
- **Historical Coverage**: Minimum 15 years.
- **Authority Requirements**: Authoritative synchronized multi-asset archives.

## 10. Data Provenance Contract Required Before Empirical Work
Strict verification of synchronized timestamping to avoid synthetic lookahead bias caused by asynchronous closing prints.

## 11. Execution / Friction Requirements
- Dual-leg transaction costs: double commissions and double bid/ask spread crossing.
- Short borrow availability, borrow locate fees, and hard-to-borrow recall risk.
- Execution risk: one leg fills while the other leg slips or fails (leg-out risk).

## 12. Confounders
- Corporate actions (mergers, acquisitions, spin-offs, special dividends).
- Structural regime shifts breaking historical cointegration vectors.

## 13. Required Negative / Placebo Controls
- Random-pair bootstrap control: Evaluating spread trading logic on randomly paired, unrelated securities.
- Factor-neutralized residual control.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: LOW.
- **Rationale**: ACASH has never explored pairs trading or statistical arbitrage in historical core work.

## 15. Falsification Concept
Falsified if out-of-sample spread trading portfolios fail to cover dual-leg transaction costs and borrow fees across a diversified universe of liquid pairs.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No spread entry thresholds (e.g. 2.0 z-score), lookbacks, or exit rules are authorized at R0.

## 17. Metrics
Cointegration ADF / Johansen statistics, Half-life of mean reversion, Net Sharpe Ratio.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Separate advanced sleeve (NOT current core).

## 19. Open Questions
- What dynamic hedge ratio estimation method (Kalman filter vs. rolling OLS) minimizes divergence drag?
- How severe is the borrow availability constraint during market crisis periods?

## 20. Next Permitted Action
literature preservation only.
