# ACASH Research Intake v1 — Bibliography & Literature Lineage

## 1. Governance Note on Citations

This bibliography catalogs only the academic, foundational, and regulatory reference sources explicitly reviewed and approved by human research authority for ACASH Research Intake v1.
- In accordance with non-negotiable governance, no new external papers have been added via automated web research or agent memory.
- In accordance with R0 authority fidelity, exact bibliographic metadata (such as publication year, volume, issue, page ranges, and full co-author lists) is not reconstructed from model memory where not explicitly bound by source authority.
- All entries where exact bibliographic metadata has not been independently revalidated against canonical published records are explicitly marked with `STATUS: METADATA_NOT_REVALIDATED_IN_R0`.

---

## 2. Peer-Reviewed Academic Literature

### Market Opening, Intraday Momentum & Return Predictability
- **Gao / Han / Li / Zhou**
  - *Title*: Market Intraday Momentum
  - *Publication*: Journal of Financial Economics
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`
  - *Annotation*: Evaluates first-half-hour return predictability for the last-half-hour return in US equities. Context for `RI-01`.

### Microstructure, Order Flow Imbalance & Price Impact
- **Cont / Kukanov / Stoikov**
  - *Title*: The Price Impact of Order Book Events
  - *Publication*: Journal of Financial Econometrics
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`
  - *Annotation*: Defines Order Flow Imbalance (OFI) at best bid/ask and estimates short-horizon price impact. Foundation for `RI-03`.

### Time-Series Momentum & Trend Following
- **Moskowitz / Ooi / Pedersen**
  - *Title*: Time Series Momentum
  - *Publication*: Journal of Financial Economics
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`
  - *Annotation*: Documents time-series momentum across global futures contracts over intermediate horizons. Context for `RI-09`.

### Technical Analysis & Quantitative Pattern Evaluation
- **Lo / Mamaysky / Wang**
  - *Title*: Foundations of Technical Analysis
  - *Publication*: Journal of Finance
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`
  - *Annotation*: Evaluates technical chart patterns using non-parametric kernel regression and notes execution conditioning challenges. Context for `RI-15`.

### Transaction Costs, Trading Frequency & Performance
- **Barber / Odean**
  - *Title*: Trading Is Hazardous to Your Wealth
  - *Publication*: Journal of Finance
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`
  - *Annotation*: Documents the empirical impact of transaction costs on trading performance. Foundation for `METHODOLOGY_CONTROLS.md`.

### Multiple Testing, Data Snooping & Reality Checks
- **Sullivan / Timmermann / White**
  - *Title*: Data-Snooping, Technical Trading Rule Performance, and the Bootstrap
  - *Publication*: Journal of Finance
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`
  - *Annotation*: Establishes White's Reality Check to correct for data-snooping in technical trading rules. Foundation for trial count $K$ governance.
- **Bailey / López de Prado**
  - *Title*: The Deflated Sharpe Ratio
  - *Publication*: Journal of Portfolio Management
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`
  - *Annotation*: Introduces DSR to account for candidate trial count $K$, skewness, and kurtosis.
- **Bailey / López de Prado**
  - *Title*: Probabilistic Sharpe Ratio and Minimum Track Record Length
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`

### Calendar Anomalies
- **French**
  - *Title*: Stock Returns and the Weekend Effect
  - *Publication*: Journal of Financial Economics
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`
  - *Annotation*: Foundational empirical analysis of calendar weekday anomalies in US equities. Context for `RI-12`.

### Statistical Arbitrage & Pairs Trading
- **Gatev / Goetzmann / Rouwenhorst**
  - *Title*: Pairs Trading: Performance of a Relative-Value Arbitrage Rule
  - *Publication*: Review of Financial Studies
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`
  - *Annotation*: Empirical study of distance-based pairs trading in equity markets. Foundation for `RI-13`.

---

## 3. Literature Families & Preprints

### Opening Range Breakout in Futures
- *Opening Range Breakout / TORB index futures study*
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`. Context for `RI-02`.

### Overnight vs. Intraday Equity Return Decomposition
- *Research on overnight vs intraday equity return decomposition*
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`. Context for `SR-08` and `RI-09`.

### Foreign Exchange Technical & Intraday Rules
- *FX technical-rule literature referenced by human authority*
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`. Context for `SR-10`.

### Dealer Gamma Exposure, Option Hedging & Market Volatility
- *Option-market-maker gamma / volatility literature*
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`. Context for `RI-05`.
- *Net gamma exposure / hedging-channel research*
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`. Context for `RI-05`.
- *Option OI / future-return paper*
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0`. Context for `RI-06`.
- *Intraday option order imbalance preprint*
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0` (Preprint). Context for `RI-07`.

### Fair Value Gap (FVG) / Smart Money Concepts Preprints
- *The two conflicting 2026 FVG preprints referenced by human authority*
  - *Preprint A*: Reports price reaction but little/no tradeable edge after costs and highlights coarse-bar bias.
  - *Preprint B*: Reports large results over a short sample.
  - *Status*: `STATUS: METADATA_NOT_REVALIDATED_IN_R0` (Preprints). Foundation for designating `RI-14` as `NEGATIVE_CONTROL_CANDIDATE`.

---

## 4. Vendor, Exchange & Educational Technical Sources

- **CME Group**: Educational and technical reference materials supplied for OI/volatility context.
- **Alpaca Markets**: Vendor technical documentation supplied for option-data API limitation context.
- **Cboe**: Exchange technical documentation supplied for historical options data specifications.
