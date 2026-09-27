# ACASH Research Intake v1 — Bibliography & Literature Lineage

## 1. Governance Note on Citations

This bibliography catalogs only the academic, foundational, and regulatory reference sources explicitly reviewed and approved by human research authority for ACASH Research Intake v1.
- In accordance with non-negotiable governance, no new external papers have been added via automated web research or agent memory.
- Entries where full bibliographic metadata has not been independently revalidated in the local environment are explicitly marked with `METADATA_NOT_REVALIDATED_IN_R0`.

---

## 2. Peer-Reviewed Academic Literature

### Market Opening, Intraday Momentum & Return Predictability
- **Gao, Han, Li, Zhou** — US intraday opening/closing predictability.
  - *Reference*: Gao, S., Han, Y., Li, K. Z., & Zhou, G. (2018). *Market Intraday Momentum*. **Journal of Financial Economics**.
  - *Annotation*: Demonstrates that the first-half-hour return of the US equity market predicts the last-half-hour return; relation is stronger in higher volatility, volume, and macro-news states. Foundation for `RI-01`.

### Microstructure, Order Flow Imbalance & Price Impact
- **Cont, Kukanov, Stoikov** — Order-flow imbalance / price impact.
  - *Reference*: Cont, R., Kukanov, I., & Stoikov, S. (2014). *The Price Impact of Order Book Events*. **Journal of Financial Econometrics**.
  - *Annotation*: Defines Order Flow Imbalance (OFI) at best bid/ask and estimates short-horizon price impact. Foundation for `RI-03`.

### Time-Series Momentum & Trend Following
- **Moskowitz, Ooi, Pedersen** — Time Series Momentum.
  - *Reference*: Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). *Time Series Momentum*. **Journal of Financial Economics**.
  - *Annotation*: Documents time-series momentum across global futures contracts over 1- to 12-month horizons. Context for `RI-09`.

### Technical Analysis & Quantitative Pattern Evaluation
- **Lo, Mamaysky, Wang** — Systematic technical pattern information.
  - *Reference*: Lo, A. W., Mamaysky, H., & Wang, J. (2000). *Foundations of Technical Analysis*. **Journal of Finance**.
  - *Annotation*: Evaluates technical chart patterns and demonstrates non-trivial conditioning information, while noting execution challenges. Context for `RI-15`.

### Transaction Costs, Trading Frequency & Performance
- **Barber, Odean** — Transaction costs / active trading.
  - *Reference*: Barber, B. M., & Odean, T. (2000). *Trading Is Hazardous to Your Wealth*. **Journal of Finance**.
  - *Annotation*: Documents the empirical impact of transaction costs on trading performance. Foundation for `METHODOLOGY_CONTROLS.md`.

### Multiple Testing, Data Snooping & Reality Checks
- **Sullivan, Timmermann, White** — Data snooping / Reality Check.
  - *Reference*: Sullivan, R., Timmermann, A., & White, H. (1999). *Data-Snooping, Technical Trading Rule Performance, and the Bootstrap*. **Journal of Finance**.
  - *Annotation*: Establishes White's Reality Check to correct for data-snooping in technical trading rules. Foundation for trial count $K$ governance.
- **Bailey, López de Prado** — Deflated Sharpe Ratio.
  - *Reference*: Bailey, D. H., & López de Prado, M. (2014). *The Deflated Sharpe Ratio*. **Journal of Portfolio Management**.
  - *Annotation*: Introduces DSR to account for candidate trial count $K$, skewness, and kurtosis.
- **Bailey, López de Prado** — Probabilistic Sharpe / Minimum Track Record.
  - *Reference*: Bailey, D. H., & López de Prado, M. *Probabilistic Sharpe Ratio and Minimum Track Record Length*.
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0`.

### Calendar Anomalies
- **French** — Weekday/weekend effects.
  - *Reference*: French, K. R. (1980). *Stock Returns and the Weekend Effect*. **Journal of Financial Economics**.
  - *Annotation*: Foundational empirical analysis of calendar weekday anomalies in US equities. Context for `RI-12`.

### Statistical Arbitrage & Pairs Trading
- **Gatev, Goetzmann, Rouwenhorst** — Pairs trading.
  - *Reference*: Gatev, E., Goetzmann, W. N., & Rouwenhorst, K. G. (2006). *Pairs Trading: Performance of a Relative-Value Arbitrage Rule*. **Review of Financial Studies**.
  - *Annotation*: Landmark empirical study of distance-based pairs trading in equity markets. Foundation for `RI-13`.

---

## 3. Literature Families & Preprints

### Opening Range Breakout in Futures
- *Opening Range Breakout / TORB index futures study*.
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0`. Context for `RI-02`.

### Overnight vs. Intraday Equity Return Decomposition
- *Research on overnight vs intraday equity return decomposition*.
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0`. Context for `SR-08` and `RI-09`.

### Foreign Exchange Technical & Intraday Rules
- *FX technical-rule literature referenced by human authority*.
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0`. Context for `SR-10`.

### Dealer Gamma Exposure, Option Hedging & Market Volatility
- *Option-market-maker gamma / volatility literature*.
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0`. Context for `RI-05`.
- *Net gamma exposure / hedging-channel research*.
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0`. Context for `RI-05`.
- *Option OI / future-return paper*.
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0`. Context for `RI-06`.
- *2026 intraday option order imbalance preprint*.
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0` (Preprint). Context for `RI-07`.

### Fair Value Gap (FVG) / Smart Money Concepts Preprints
- *The two conflicting 2026 FVG preprints referenced by human authority*.
  - *Preprint A*: Reports price reaction but little/no tradeable edge after costs and highlights coarse-bar bias.
  - *Preprint B*: Reports large results over a short sample.
  - *Status*: `METADATA_NOT_REVALIDATED_IN_R0` (Preprints). Foundation for designating `RI-14` as `NEGATIVE_CONTROL_CANDIDATE`.

---

## 4. Vendor, Exchange & Educational Technical Sources

- **CME Group**: *CME OI/volatility educational/reference sources supplied*. Educational and technical references.
- **Alpaca Markets**: *Alpaca historical option-data limitation source supplied*. Vendor technical documentation.
- **Cboe**: *Cboe historical-options-data source supplied*. Exchange technical documentation.
