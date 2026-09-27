# ACASH Research Intake v1 — Bibliography & Literature Lineage

## 1. Governance Note on Citations

This bibliography catalogs only the academic, foundational, and regulatory reference sources explicitly reviewed and approved by human research authority for ACASH Research Intake v1.
- In accordance with non-negotiable governance, no new external papers have been added via automated web research.
- Entries where full bibliographic metadata has not been independently revalidated in the local environment are explicitly marked with `METADATA_NOT_REVALIDATED_IN_R0`.

---

## 2. Peer-Reviewed Academic Literature

### Market Opening, Intraday Momentum & Return Predictability
- **Gao, S., Han, Y., Li, K. Z., & Zhou, G.** (2018). *Market Intraday Momentum*. **Journal of Financial Economics**, 129(2), 394–414.
  - *Annotation*: Demonstrates that the first half-hour return of the US equity market predicts the last half-hour return; effect is intensified during high volatility and volume states. Foundation for `RI-01`.

### Microstructure, Order Flow Imbalance & Price Impact
- **Cont, R., Kukanov, I., & Stoikov, S.** (2014). *The Price Impact of Order Book Events*. **Journal of Financial Econometrics**, 12(1), 47–88.
  - *Annotation*: Defines Order Flow Imbalance (OFI) at the best bid and ask levels and establishes linear short-horizon price impact dynamics. Foundation for `RI-03`.

### Time-Series Momentum & Trend Following
- **Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H.** (2012). *Time Series Momentum*. **Journal of Financial Economics**, 104(2), 228–250.
  - *Annotation*: Documents persistent momentum across global futures contracts across 1- to 12-month horizons. Context for `RI-09`.

### Technical Analysis & Quantitative Pattern Evaluation
- **Lo, A. W., Mamaysky, H., & Wang, J.** (2000). *Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation*. **Journal of Finance**, 55(4), 1705–1765.
  - *Annotation*: Evaluates technical chart patterns using kernel regression and demonstrates non-trivial conditioning information, while warning against naive execution. Context for `RI-15`.

### Transaction Costs, Trading Frequency & Performance
- **Barber, B. M., & Odean, T.** (2000). *Trading Is Hazardous to Your Wealth: The Common Stock Investment Performance of Individual Investors*. **Journal of Finance**, 55(2), 773–806.
  - *Annotation*: Documents the empirical destruction of gross performance caused by transaction costs and overtrading. Foundation for `METHODOLOGY_CONTROLS.md`.

### Multiple Testing, Data Snooping & Reality Checks
- **Sullivan, R., Timmermann, A., & White, H.** (1999). *Data-Snooping, Technical Trading Rule Performance, and the Bootstrap*. **Journal of Finance**, 54(5), 1647–1691.
  - *Annotation*: Establishes White's Reality Check to correct for data-snooping in technical trading rules. Foundation for trial count $K$ governance.
- **Bailey, D. H., & López de Prado, M.** (2014). *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality*. **Journal of Portfolio Management**, 40(5), 94–107.
  - *Annotation*: Introduces DSR to account for candidate trial count $K$, skewness, and kurtosis. Required metric in ACASH.
- **Bailey, D. H., & López de Prado, M.** (2012). *The Sharpe Ratio Efficient Frontier*. **Journal of Risk**, 15(2), 13–44.
  - *Annotation*: Establishes the Probabilistic Sharpe Ratio (PSR) and Minimum Track Record Length (MinTR).

### Calendar Anomalies
- **French, K. R.** (1980). *Stock Returns and the Weekend Effect*. **Journal of Financial Economics**, 8(1), 55–69.
  - *Annotation*: Foundational empirical analysis of calendar weekday anomalies in US equities. Context for `RI-12`.

### Statistical Arbitrage & Pairs Trading
- **Gatev, E., Goetzmann, W. N., & Rouwenhorst, K. G.** (2006). *Pairs Trading: Performance of a Relative-Value Arbitrage Rule*. **Review of Financial Studies**, 19(3), 797–808.
  - *Annotation*: Landmark empirical study of distance-based pairs trading in equity markets. Foundation for `RI-13`.

---

## 3. Working Papers, Preprints & Literature Lineage

### Opening Range Breakout in Futures
- *Opening Range Breakout / Time-of-Day Breakout (TORB) in Index Futures*. [Literature Family Reference].
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0`. Context for `RI-02`.

### Overnight vs. Intraday Equity Return Decomposition
- *Decomposition of Equity Returns into Overnight Drift and Daytime Trading Cycles*. [Literature Family Reference].
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0`. Context for `SR-08` and `RI-09`.

### Foreign Exchange Technical & Intraday Rules
- *Empirical Performance of Technical Trading Rules in Foreign Exchange Markets*. [Literature Family Reference].
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0`. Context for `SR-10`.

### Dealer Gamma Exposure, Option Hedging & Market Volatility
- *Market-Maker Net Gamma Exposure and Volatility Dampening/Amplification Channels*. [Literature Family Reference].
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0`. Foundational mechanics for `RI-05`.
- *Option Open Interest and Future Underlying Stock Return Predictability*. [Literature Family Reference].
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0`. Context for `RI-06`.
- *Intraday Option Order Imbalance and Information Transmission* (2026 Preprint Lineage).
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0` (Preprint). Context for `RI-07`.

### Fair Value Gap (FVG) / Smart Money Concepts Preprints
- *Conflicting Preprints on Fair Value Gaps in Financial Markets* (2026).
  - *Preprint A*: Reports price reaction at FVG boundaries but demonstrates that economic edge collapses after transaction costs and execution latency; highlights severe coarse-bar path bias.
  - *Preprint B*: Reports substantial gross profitability over a limited, short-duration sample.
  - *Classification*: `WEAK_CONFLICTING_EVIDENCE`. Foundation for designating `RI-14` as a `NEGATIVE_CONTROL_CANDIDATE`.

---

## 4. Vendor, Exchange & Educational Technical Sources

- **Chicago Mercantile Exchange (CME Group)**: *Open Interest, Volume, and Volatility Specifications in CME Futures and Options*. Educational and technical clearing references.
- **Alpaca Markets**: *Market Data Documentation and Historical Option Data Availability Boundaries*. Vendor technical documentation.
- **Chicago Board Options Exchange (Cboe)**: *Cboe Options Exchange Specifications and Historical Market Data Characteristics*. Exchange technical documentation.
