# ACASH — Multi-Asset Quantitative Research & Market Data Direction

**STATUS:** RESEARCH / FUTURE DIRECTION  
**AUTHORITY:** NON-GOVERNING  
**IMPLEMENTATION:** NOT AUTHORIZED  
**BACKTEST:** NOT AUTHORIZED  
**PAPER:** NOT AUTHORIZED  
**LIVE:** LOCKED  

---

## 1. Scope & Governance Boundary

This document records high-level research findings and architectural direction for ACASH's market-data ingestion and quantitative strategy research.

- **Non-Governing:** This document does NOT constitute governance approval, does NOT amend ratified governance records, and does NOT authorize strategy development or live trading.
- **No Hypothesis Creation:** This document does NOT create `HYP_003` or any other trading hypothesis.
- **No Gate Progression:** Research ideas and market-data integrations documented here do NOT unlock backtesting, paper trading, or live capital.
- **Capital & Order Invariants:** Canonical capital remains **$0.00**; `NO_REAL_ORDERS=true` remains enforced.
- **Active Runtime Invariance:** This document does not modify, restart, or interact with any active operational soak or container runtime.

---

## 2. Current Market-Data Architecture

ACASH's market-data feed layer is designed to be **provider-agnostic**. External data sources are ingested through provider adapters that normalize external market data into a canonical `FeedBar` contract before downstream journal, research, or paper execution infrastructure consumes it.

### Currently Verified Providers

1. **`BinancePublicKlinesFeed`**
   - Public cryptocurrency OHLCV market data (BTCUSDT).
   - Credential-free endpoint access via public REST API.
   - Currently utilized for Gate G7 / Stage S11 M1 operational infrastructure continuity testing.

2. **`StooqCsvFeed`**
   - Credential-free daily market data.
   - Intended for historical research across foreign exchange (FX), equities, and market indices.
   - Daily (D1) frequency only in the current implementation.

### Critical Ingestion vs. Execution Distinction

> **"ACASH can ingest market data for an asset" $\neq$ "ACASH fully supports trading that asset."**

The current paper execution path contains specific infrastructure-test assumptions, including synthetic instrument semantics and fixed simulation contracts. Full multi-asset paper execution is future work and requires separate data pipelines, execution adapters, and formal human certification.

---

## 3. Target Multi-Asset Market-Data Architecture

The long-term ACASH market-data architecture is designed to support multiple liquid asset classes across distinct provider channels:

- **Crypto:** BTC, ETH, and other sufficiently liquid digital assets.
- **Equity Index Futures:** ES (E-mini S&P 500 futures) and other major benchmark index futures.
- **FX:** EURUSD, USDJPY, and other major liquid currency pairs.
- **Metals / Commodities:** XAU (Gold), crude oil, and other liquid futures or spot proxies.
- **Equities:** Individual stocks, ETFs, and sector baskets.
- **Rates / Fixed Income:** Treasury / sovereign yield proxies and interest-rate futures where appropriate.

Each asset class may require a dedicated, specialized market-data provider. **Binance is not a universal data source.**

### Target Conceptual Topology

```text
                   ACASH Market Data Layer
                           |
         +-----------------+------------------+
         |                 |                  |
       Crypto              FX              TradFi
         |                 |                  |
      Binance         FX Provider      Equity/Futures Provider
         |                 |                  |
         +-----------------+------------------+
                           |
                    Canonical FeedBar
                           |
             Journal / Research / Paper
```

Strategies and research models must depend exclusively on normalized market-data contracts (`FeedBar`) rather than provider-specific representations whenever practical.

### Provider Adapter Responsibilities

Provider adapters must encapsulate all source-specific protocols and guarantee the canonical contract:
- Symbol normalization to ACASH canonical notation.
- Timeframe normalization.
- UTC timestamp alignment and ISO-8601 representation.
- OHLCV field normalization and decimal precision handling.
- Explicit declaration of missing or unavailable fields (never fabricate unavailable data).
- Data freshness verification and latency measurement.
- Deduplication of incoming bar records.
- Connection state tracking and explicit status reporting.
- Error classification (e.g., timeout vs. connection drop vs. rate limit vs. format error).
- Source provenance and audit lineage metadata.

### Operational Realities Across Venues

- **Crypto Markets:**
  - Binance public spot klines provide accessible, credential-free OHLCV data suitable for initial infrastructure testing.
  - Rate limits, geographic availability, and exchange uptime constraints still apply.
  - A successful Binance G7 soak validates only the **Binance $\to$ ACASH** pipeline, not all providers or asset classes.
- **Traditional Finance (TradFi) Markets:**
  - Futures data (e.g., CME ES futures) involves licensing, entitlement fees, and non-trivial regulatory compliance.
  - Real-time TradFi futures data cannot be assumed to be freely available like public crypto data.
  - Equities, FX, commodities, and fixed income require separate vendor agreements, broker feeds, or licensed public aggregators depending on latency and timeframe requirements.
  - Low-frequency daily research data and real-time execution-grade streaming data have fundamentally different architectural and licensing profiles.

---

## 4. Contemporary Quantitative Markets & Strategy Families

Modern systematic and quantitative trading firms operate across multiple liquid electronic asset classes:
- Equities & ETFs
- Options & Volatility Products
- Commodity & Financial Futures
- Fixed Income, Sovereign Debt & Money Markets
- Foreign Exchange (G10 & Liquid EM)
- Digital Assets / Cryptocurrencies

### Quantitative Strategy Families (Research Taxonomy)

The following taxonomy outlines standard industry quantitative strategy families. **ACASH does NOT claim to implement all of these; they are categorized for research reference only:**

1. **Trend / CTA / Momentum:** Systematic trend-following and time-series momentum across multi-asset futures, FX, and crypto.
2. **Equity Market Neutral (EMN) / Statistical Arbitrage:** Cross-sectional mean reversion, pair trading, and cointegration arbitrage on equities.
3. **Factor / Systematic Equity:** Multi-factor equity selection models (value, momentum, quality, low volatility, size).
4. **Systematic Macro:** Quantitatively evaluated macro models allocating across rates, FX, equity indices, and commodities.
5. **Market Making / High-Frequency Trading (HFT):** Continuous quoting, bid-ask spread capture, and order-book liquidity provision.
6. **Options / Volatility Arbitrage:** Variance risk premia, volatility surface arbitrage, and delta-neutral dispersion.
7. **Fixed-Income Relative Value:** Yield curve modeling, basis trading, and swap-spread arbitrage.
8. **Crypto Quant:** Cross-exchange funding-rate arbitrage, cross-venue basis, and multi-token momentum.
9. **Cross-Sectional Relative Strength:** Ranking instruments within an asset class to long leaders and short laggards.
10. **Mean Reversion / Relative Value:** Statistical spread trading between economically cointegrated instruments.
11. **Regime Models:** Hidden Markov models, volatility clustering, and macro-state classifiers guiding capital allocation.

---

## 5. Homelab-Practical Future Research Priorities

Given ACASH's current single-node homelab architecture, bandwidth constraints, and computational profile, **high-frequency trading (HFT) and latency-sensitive market making are explicitly NOT near-term priorities.** Competitive HFT requires co-location, FPGA/kernel-bypass hardware, specialized market-microstructure feeds, full L2/L3 order-book reconstruction, and heavy inventory-risk capital facilities.

The most viable and practical research directions for ACASH include:

1. **Multi-Asset Trend / Momentum:**
   - Evaluated on daily (D1) and high-timeframe intraday bars.
   - Universe: ES, BTC, EURUSD, XAU, and sovereign bond proxies.
2. **Cross-Sectional / Relative Strength:**
   - Multi-asset ranking models identifying relative momentum across equity sectors, liquid stocks, and top-tier crypto assets.
3. **Mean Reversion / Statistical Relative Value:**
   - Spread and cointegration modeling across correlated pairs, futures spreads, or index-component baskets.
4. **Regime Modeling:**
   - Macro and volatility classification guiding position sizing and strategy participation:
     - Volatility Regimes (e.g., ATR / realized volatility state)
     - USD Dollar Regime (e.g., DXY / EURUSD directional state)
     - Rate / Yield Regime (e.g., bond proxy directional trend)
     - Broad Equity Risk Appetite (e.g., ES trend state)
     - Crypto Speculative Risk Appetite (e.g., BTC volume and trend state)

---

## 6. Conceptual Cross-Asset Regime Inputs (Future Research Direction)

As a **future research direction (NOT an active hypothesis)**, ACASH may explore using signals across multiple liquid markets as state inputs to contextualize asset regimes:

| Asset / Instrument | Conceptual Regime Indicator Role |
| :--- | :--- |
| **BTC** | Crypto market sentiment / speculative retail risk appetite proxy |
| **ES** | Broad institutional equity risk appetite / equity market trend |
| **EURUSD** | Global US Dollar liquidity and foreign exchange regime |
| **XAU** | Real-rate proxy, inflation sensitivity, defensive/safe-haven regime |
| **Rates / Bonds** | Monetary policy stance, yield curve regime, cost-of-capital state |
| **Equities / Sectors** | Cross-sectional dispersion, cyclical vs. defensive sector rotation |

> **Important Boundary:** This conceptual mapping does **NOT** assert statistical predictive power. Any proposed relationship must be formally articulated as a hypothesis, subjected to multiple-testing corrections, and evaluated under rigorous out-of-sample testing before admission.

---

## 7. Governance Progression & Admission Interlock

All quantitative research and engineering in ACASH must adhere strictly to the sequential human-governed research lifecycle:

```text
Idea
  |
  v
Research Question
  |
  v
Data Qualification & Stationarity Audit
  |
  v
Human-Authorized Hypothesis (e.g. HYP_XXX)
  |
  v
Backtest Authorization (Gate G1 / R1)
  |
  v
Out-of-Sample Validation & PBO / DSR Checks
  |
  v
Robustness, Transaction Cost & Slippage Sensitivity Tests
  |
  v
Paper Trading Authorization (Gate G4)
  |
  v
Operational Soak & Telemetry Validation (Gate G7 / Stage S11)
  |
  v
Human Governance Review & Capital Ratification
```

### Strict Fail-Closed Invariants:
1. **Data Ingestion $\neq$ Backtest Authorization:** Adding a data provider or ingesting bars does NOT authorize running backtests.
2. **Backtest Qualification $\neq$ Paper Authorization:** Qualifying statistical tests (Sharpe, DSR, PBO) does NOT grant paper trading authority.
3. **Paper Soak $\neq$ Live Trading Authorization:** Qualifying operational soaks does NOT grant live capital deployment authority.
4. **Capital Remains Zero:** Canonical capital remains **$0.00** until explicit, human-ratified production governance approval.

---

## 8. Purpose and Boundaries of Active Gate G7 / Stage S11 Soak

The currently executing Gate G7 / Stage S11 soak test validates **operational infrastructure continuity** of the Binance BTCUSDT M1 feed pipeline.

### What the G7 Soak Audits:
- Continuous M1 bar ingestion over $\ge 21,600$ uninterrupted seconds (6.00 continuous hours).
- Bar timestamp uniqueness and duplicate-detection integrity.
- In-memory and journal timestamp freshness tracking.
- Chained SHA-256 cryptographic journal persistence and event sequence integrity.
- Observability and fail-closed handling during feed disconnects.
- Container stability with zero unexpected restarts (`RestartCount == 0`).
- Bounded container memory usage ($< 512$ MiB RSS).
- Prometheus/VictoriaMetrics metric scraping continuity.
- Complete absence of real order submissions (`NO_REAL_ORDERS=true`, 0 orders).

### What the G7 Soak Does NOT Prove:
- It does **NOT** evaluate strategy profitability or market edge.
- It does **NOT** calculate or assert trading alpha.
- It does **NOT** qualify Sharpe ratio or expected return.
- It does **NOT** evaluate live broker order execution quality or slippage.
- It does **NOT** demonstrate multi-asset or multi-provider execution capability.

The active soak must remain completely untouched during documentation updates.

---

## 9. Binding Legal & Governance Statement

This document records research and architecture direction only.

It does not create a trading hypothesis.  
It does not authorize backtesting.  
It does not authorize paper trading.  
It does not authorize live trading.  
It does not change canonical capital.  
It does not modify G7/S11 acceptance criteria.  
All implementation and governance transitions require separate explicit human authorization.  
