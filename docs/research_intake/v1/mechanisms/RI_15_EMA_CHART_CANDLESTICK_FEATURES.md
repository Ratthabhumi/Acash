# RI-15 — EMA / Chart / Candlestick Features

## 1. Intake Status
- Intake status: UNSUPPORTED_HEURISTIC
- Candidate role: FEATURE ONLY
- CORE-002 promotion authorized? NO
- Empirical testing authorized? NO
- Market-data access authorized? NO
- Parameter sweep authorized? NO
- Paper/live authority? NO
- Real capital authority: $0.00
- NO_REAL_ORDERS: true

## 2. Research-Grade Mechanism
Mechanically codified geometric price patterns, moving average crossovers, and candlestick sequences are evaluated as potential low-level conditioning features (not standalone alpha theses) to determine if they convey statistically significant distributional information.

## 3. Economic / Microstructure Rationale
Widespread technical analysis usage by retail and systematic chart-based participants may generate localized, self-fulfilling liquidity clusters or behavioral reactions around widely observed chart patterns and moving average boundaries.

## 4. Null Hypothesis
$H_0$: Technical chart patterns and moving average configurations provide zero incremental predictive information regarding future conditional return distributions when conditioned on market volatility, volume, and momentum.

## 5. Alternative Hypothesis
$H_1$: Algorithmic codifications of specific geometric patterns exhibit statistically significant non-linear conditioning value when combined with order flow and volume state features.

## 6. What Existing Evidence Actually Supports
- **Peer-Reviewed / Established**: Lo, Mamaysky, and Wang (2000, *Journal of Finance*) demonstrate that certain technical patterns (e.g., head-and-shoulders, double bottoms) provide non-trivial empirical conditioning information, though they caution against naive trading rule implementation.
- **Preprint / Preliminary**: Machine learning studies utilizing candlestick encoding matrices.
- **Source Claim Only**: Claims that candlestick patterns like "three white soldiers", "bullish engulfing", "hammer", or specific moving average stacks (EMA 9/21/50, EMA 8/21, EMA 12) act as guaranteed confirmation signals.

## 7. What Existing Evidence Does NOT Support
Literature does NOT support the claim that visual, subjective chart reading ("clean level", "respecting the moving average", "obvious compression") provides consistent trading edge without deterministic mathematical codification.

## 8. Source Claims That Motivated This Intake
- `SR-03`: Personal preference for EMA 8 and 21.
- `SR-04`: First 5-minute EMA 12 momentum.
- `SR-06`: Ninja GEX checklist emphasizing daily/intraday EMA 9/21/50 stacks, flags, compressions, three white soldiers, bullish engulfing, and hammer candles.

## 9. Data Requirements
- **Instrument**: US Equities and Index Futures.
- **Frequency**: 1-minute, 5-minute, and daily bars.
- **Data Types**: Deterministic OHLCV bars.
- **Time Zone**: America/New_York (UTC).
- **Vendor / Feed Semantics**: Consolidated Tape SIP / CME MDP 3.0.
- **Historical Coverage**: Minimum 10 years.
- **Authority Requirements**: Authoritative exchange data.

## 10. Data Provenance Contract Required Before Empirical Work
Exact mathematical algorithms for pattern identification must be pre-registered (e.g., kernel regression or formal geometry). Subjective discretionary definitions are strictly prohibited.

## 11. Execution / Friction Requirements
- Full transaction cost modeling. Naive technical trading rules incur high turnover that rapidly destroys gross returns.

## 12. Confounders
- Subjectivity in pattern identification (different chartists define patterns differently).
- Data snooping from millions of potential indicator/parameter combinations.

## 13. Required Negative / Placebo Controls
- Shuffled candlestick order control.
- Random pattern matching benchmark.

## 14. Contamination / Prior-Exposure Risk
- **Risk Level**: HIGH.
- **Rationale**: Extensive retail literature and extreme degrees of freedom in technical indicators.

## 15. Falsification Concept
Falsified if machine-deterministic pattern definitions provide zero incremental predictive information beyond simple linear momentum and volatility controls.

## 16. Parameters
PARAMETERS_NOT_PREREGISTERED.
No specific moving average lengths (8, 9, 12, 21, 50), candlestick rules, or chart thresholds are authorized.

## 17. Metrics
Information Coefficient (IC), feature importance in non-linear models, net Sharpe Ratio after costs.
NO_SINGLE_METRIC_IS_DECISIVE.

## 18. Candidate Classification
FEATURE ONLY. Prohibited from serving as a standalone thesis at R0.

## 19. Open Questions
- Can classical candlestick patterns be encoded into continuous mathematical features rather than fragile binary flags?
- Does retail attention on moving average crosses create predictable counter-liquidity opportunities for institutions?

## 20. Next Permitted Action
literature preservation only.
