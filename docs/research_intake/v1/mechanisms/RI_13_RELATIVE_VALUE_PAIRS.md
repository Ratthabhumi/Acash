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
Relative prices of economically related securities may exhibit temporary divergence and subsequent convergence.

## 3. Economic / Microstructure Rationale
Securities with shared fundamental cash flows or strong economic linkages share common factor risks. When temporary non-fundamental order flow forces their relative price away from long-run equilibrium, statistical arbitrage capital supplies liquidity, profiting as the spread reverts.

## 4. Null Hypothesis
$H_0$: The price spread between economically linked pairs exhibits zero stationarity or mean-reverting predictability beyond random drift.

## 5. Alternative Hypothesis
$H_1$: Economically selected and cointegrated pairs exhibit statistically significant mean-reverting spread dynamics that generate positive risk-adjusted returns after full accounting for execution and short-borrow frictions.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Gatev, Goetzmann, and Rouwenhorst (2006, *Review of Financial Studies*) documenting legitimate research family results for pairs trading in US equities; cointegration literature.
- **Preprint / Preliminary**: Machine learning and copula-based pairs trading models.
- **Source Claim Only**: Generic claims that any correlated assets can be traded profitably using simple Bollinger bands.

## 7. What Existing Evidence Does NOT Support
Correlation alone is insufficient. Literature does NOT support the claim that simple historical correlation implies cointegration or tradeability. Required issues include: cointegration/stationarity, hedge-ratio stability, borrow availability, short costs, corporate actions, common-factor exposure, execution, and structural break.

## 8. Source Claims That Motivated This Intake
- `SR-14`: Macro and statistical arbitrage strategy families.

## 9. Data Requirements
- **Instrument**: NOT_YET_DETERMINED.
- **Frequency**: NOT_YET_DETERMINED.
- **Data Types**: Synchronized trade and quote timestamps for both pair legs.
- **Time Zone**: America/New_York (UTC storage).
- **Vendor / Feed Semantics**: NOT_YET_DETERMINED.
- **Historical Coverage**: NOT_YET_DETERMINED.
- **Provider**: NOT_YET_DETERMINED.
- **Timestamp Precision**: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT.
- **Authority Requirements**: Authoritative synchronized multi-asset archives.

## 10. Data Provenance Contract Required Before Empirical Work
Strict verification of synchronized timestamping to avoid synthetic lookahead bias caused by asynchronous closing prints.

## 11. Execution / Friction Requirements
- Dual-leg transaction costs: double commissions and double spread crossing.
- Short borrow availability, borrow locate fees, and hard-to-borrow recall risk.
- Execution risk: one leg fills while the other leg slips or fails (leg-out risk).

## 12. Confounders
- Corporate actions (mergers, acquisitions, spin-offs, special dividends).
- Structural regime shifts breaking historical cointegration vectors.

## 13. Required Negative / Placebo Controls
- Random/matched-pair bootstrap control is important: Evaluating spread trading logic on randomly paired securities.
- Factor-neutralized residual control.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: LOW.
- **Rationale**: ACASH has never explored pairs trading or statistical arbitrage in historical core work.

## 15. Falsification Concept
Falsified if out-of-sample spread trading portfolios fail to cover dual-leg transaction costs and borrow fees across a diversified universe of pairs.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No spread entry thresholds, lookbacks, or exit rules are authorized at R0.

## 17. Metrics
Cointegration test statistics, half-life of mean reversion, Net Sharpe Ratio.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
Separate advanced sleeve (NOT current core).

## 19. Open Questions
- What dynamic hedge ratio estimation method minimizes divergence drag?
- How severe is the borrow availability constraint during market crisis periods?

## 20. Next Permitted Action
literature preservation only.
