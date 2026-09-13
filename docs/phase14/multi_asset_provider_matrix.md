# ACASH V5 — Multi-Asset Data Provider Matrix

**Document ID:** `docs/phase14/multi_asset_provider_matrix.md`  
**STATUS: NON-GOVERNING**  
**AUTHORITY: NONE**  
**EMPIRICAL AUTHORIZATION: NONE**  
**BACKTEST AUTHORIZATION: NONE**  
**PAPER AUTHORIZATION: NONE**  
**LIVE AUTHORIZATION: NONE**  
**Canonical Source Registries:** `docs/phase14/free_data_source_registry.md` (Primary Registry), `docs/phase14/free_data_research_registry.md`  
**Canonical Architectural Context:** `AGENTS.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/phase14/historical_data_qualification_spec.md`, `docs/architecture/asset_market_agnostic_research_direction.md`

---

> [!CAUTION]
> ### STRICT GOVERNANCE & REGISTRY INTEGRITY BOUNDARIES
> - **COMPARISON VIEW ONLY — NOT A CANONICAL SOURCE REGISTRY:** This document is a cross-asset synthesis and comparison matrix. It does **not** create or replace authoritative source registries. All canonical source facts reside exclusively in [free_data_source_registry.md](./free_data_source_registry.md).
> - **ZERO DUPLICATION OF CANONICAL IDENTIFIERS:** All provider entries explicitly cite their upstream registry ID (`S-01` through `S-28`) or formal Phase 14 audit reference.
> - **FAIL-CLOSED STATUS DISCIPLINE:** Evidence status admits only five strictly defined values: `VERIFIED`, `PARTIALLY VERIFIED`, `UNVERIFIED`, `NOT SUITABLE`, `NOT APPLICABLE`. Every status requires explicit factual rationale.
> - **NO EMPIRICAL TESTING AUTHORIZED:** Presence in this matrix indicates research visibility, **not** data acquisition approval, strategy qualification, or backtest authorization.

---

## 1. Executive Summary & Objective

In alignment with [asset_market_agnostic_research_direction.md](../architecture/asset_market_agnostic_research_direction.md), the ACASH quantitative research engine is designed to evaluate systematic hypotheses across multiple asset classes (Crypto, Foreign Exchange, Commodities, Equity Index Futures, Equities, and Fixed Income).

The objective of this matrix is to:
1. Provide a single, normalized comparative view across candidate data providers for all major asset domains.
2. Cross-reference every candidate against existing authoritative registries.
3. Rigorously surface structural data gaps, survivorship limitations, licensing boundaries, and corporate action deficiencies prior to research intake.
4. Answer the decisive research question:  
   *"If ACASH selects a given research question, which provider evidence already exists, what is missing, and what must be qualified before empirical use?"*

---

## 2. Multi-Asset Comparative Provider Matrix

The table below compiles and normalizes provider evidence across candidate research domains:

| Asset / Market | Provider | Upstream Registry Ref | Official / 3rd-Party | Hist. Depth | Intraday (M1) | Real-time | Earliest Coverage | Available Timeframes | OHLC | Volume Semantics | Bid/Ask & Depth | Trades / Ticks | Funding / Rollover | Corporate Actions | PIT Quality | Revision Risk | Auth & Rate Limits | Cost | License & Redistribution | Bulk Archive & Checksums | Timezone & Calendar | Known Limitations & Biases | Evidence Status & Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BTC** (Crypto Spot) | Binance Vision | Phase 14 Wave D | Official Exchange | Deep | Yes | T-1 Day | 2017-08 | 1s, 1m, 3m, 5m, 15m, 1h, 1d | Yes | Traded base & quote vol | Absent (klines); Sep. book dump | Avail. (aggTrades / trades) | N/A (Spot) | N/A | High (Exact millis) | Low (Append only) | Public HTTP/S3; standard 429 | $0.00 | Research / Personal; no commercial resale | Yes (Monthly ZIPs + SHA-256) | UTC; 24/7 continuous | Single-venue concentration; stablecoin peg risk | **VERIFIED** (Direct official archive + checksums) |
| **BTC** (Crypto Spot) | Kraken Public | Phase 14 Wave D | Official Exchange | Deep | Derived | Yes | 2013-10 | Ticks (M1 synthesizable) | Via ticks | Base traded volume | Absent (trade dump); L2 REST | Raw trade prints | N/A (Spot) | N/A | High (Exact nanos) | Low (Static dumps) | Public Web/REST; 1–2 req/s | $0.00 | Personal research; terms of use apply | Yes (Quarterly CSV dumps) | UTC; 24/7 continuous | Tick aggregation required; lower spot volume than Binance | **VERIFIED** (Official historical dumps available) |
| **ETH** (Crypto Spot) | Binance Vision | Phase 14 Wave D | Official Exchange | Deep | Yes | T-1 Day | 2017-08 | 1s, 1m, 5m, 15m, 1h, 1d | Yes | Traded base & quote vol | Absent (klines); Sep. book dump | Avail. (aggTrades / trades) | N/A (Spot) | N/A | High (Exact millis) | Low (Append only) | Public HTTP/S3; standard 429 | $0.00 | Research / Personal; no commercial resale | Yes (Monthly ZIPs + SHA-256) | UTC; 24/7 continuous | High correlation to BTC regime; gas fee spikes | **VERIFIED** (Official archive structure identical to BTC) |
| **EURUSD** (FX Major) | Stooq | `S-10` | Commercial Secondary | Deep | Shallow | None | ~1990s | Daily (Intraday paid/restricted) | Yes | Tick volume only (Unreliable) | Absent | Absent | N/A (Spot) | N/A | Low (Mutable DB) | Moderate (Vendor restatement) | Web download; rate throttled | $0.00 | Personal use only; commercial resale prohibited | Yes (Daily ZIP downloads) | UTC / NY Close (5 PM); Sun-Fri session | OTC market lacks centralized tape; tick volume != contract size | **PARTIALLY VERIFIED** (Daily verified; intraday unavailable at $0) |
| **EURUSD** (FX Major) | Federal Reserve (FRED) | `S-04` | Authoritative Secondary | Deep | None | None | 1999-01 | Daily (`DEXUSEU`) | Close only | None | Absent | Absent | N/A | N/A | High (Vintage history) | Low (ALFRED vintages) | Public REST API; free key | $0.00 | US Federal Data / FRED ToS free | Yes (CSV batch download) | Daily noon fixing; US business days | Daily close only; noon buying rate in NY; no trading execution | **VERIFIED** (Authoritative daily macro benchmark) |
| **XAU** (Gold Spot / Fix) | Stooq (`XAUUSD`) | `S-10` | Commercial Secondary | Deep | Shallow | None | ~1980s | Daily | Yes | Synthetic / Tick count | Absent | Absent | N/A | N/A | Low (Mutable DB) | Moderate | Web download; rate throttled | $0.00 | Personal use only | Yes (Daily ZIP) | London / NY sessions | OTC pricing; London bullion fix vs NY cash mismatch | **PARTIALLY VERIFIED** (Daily verified; OTC pricing ambiguities) |
| **ES** (E-mini S&P Futures) | CME Group | Phase 14 Backlog | Official Exchange | Deep | Yes | Paid | 1997-09 | 1m, tick | Yes | Centralized contracts traded | Yes | Yes | Quarterly rolls (H, M, U, Z) | N/A | High (Exchange clock) | Zero (Official audit) | CME DataMine login required | Paid ($$$) | Strict commercial license; redistribution locked | Yes (Paid S3 / SFTP) | US Central / ET; Globex Sunday-Friday | **NOT FREE:** Official tick/M1 data requires expensive licensing | **NOT SUITABLE AT $0** (Requires human budget authorization) |
| **ES** (E-mini Futures Proxy) | Stooq (`^SPX` / `SPY`) | `S-10`, `S-18` | Secondary Aggregator | Deep | None | None | 1950s (`^SPX`) | Daily only | Yes | Index vol (SPX) / ETF vol (SPY) | Absent | Absent | N/A (Continuous proxy) | Div/Split (SPY) | Low (Unversioned) | Moderate | Web / REST | $0.00 | Personal use only; Yahoo ToS risk | No checksums | ET; US Equity hours (9:30–16:00) | SPX cash index is non-tradable; SPY has tracking drag and dividends | **PARTIALLY VERIFIED** (Cash/ETF proxy only, not futures contract) |
| **US Equities** (Active Universe) | Stooq | `S-10` | Commercial Secondary | Deep | None | None | ~30 Years | Daily OHLCV | Yes | Share volume traded | Absent | Absent | N/A | Vendor adjusted (Unverified) | None (Mutable) | Moderate | Web ZIP download | $0.00 | Personal use only; commercial resale prohibited | Yes (US panel ZIP ~500MB) | US ET; NYSE/NASDAQ calendar | **SURVIVORSHIP BIAS:** Delisted stocks pruned from DB | **PARTIALLY VERIFIED** (Active names verified; delisted missing) |
| **US Equities** (Delisted Roster) | SEC EDGAR Form 25 | `S-02` | Authoritative Primary | 2006+ | None | Event | 2006-05 | Event timestamp | None | None | None | None | N/A | Official delisting event | High (Accession timestamp) | None (Immutable) | Public SEC API; 10 req/s | $0.00 | Public domain / US Government | Yes (EDGAR direct) | US ET; Event dates | Identifies delisted CIKs/dates, but provides zero price history | **VERIFIED** (Authoritative delisting roster authority) |
| **US Equities** (Delisted Prices) | Kaggle / Web Scraper | `S-23`, `S-19` | Community Aggregator | Shallow | None | None | Variable | Daily OHLCV | Yes | Unverified | Absent | Absent | N/A | Unverified | Unproven | Extreme | Scraper / Torrent | $0.00 | **UNVERIFIED LICENSE** (Unrenderable terms) | None | Unspecified | Survivorship holes; unlicensed; non-reproducible | **NOT SUITABLE** (Violates strict licensing & data contract) |
| **ETFs** (`SPY`, `QQQ`, `IWM`) | Stooq / Alpha Vantage | `S-10`, `S-11` | Secondary Aggregators | Deep | Shallow | None | 1993+ (`SPY`) | Daily (Intraday paid) | Yes | Traded share volume | Absent | Absent | N/A | Adjusted for splits/dividends | Low | Moderate | API key (AV: 25 req/day free) | $0.00 | Personal use; commercial redistribution barred | Yes (Stooq ZIP) | US ET; NYSE Arca calendar | Dividend reinvestment conventions vary; intraday locked at $0 | **PARTIALLY VERIFIED** (Daily verified; intraday requires paid tier) |
| **Rates / Yields** | FRED / US Treasury | `S-04`, `S-06` | Authoritative Primary | Very Deep | None | Daily | 1962+ (DGS10) | Daily constant maturity | Yield % | N/A (Yield quote) | N/A | N/A | Daily yield fixings | N/A | High (Official publication) | Low (ALFRED vintages) | Public API / CSV download | $0.00 | US Government / Public Domain | Yes (Batch CSV) | Daily Treasury release (3:30 PM ET) | Yield levels only; not direct tradable bond prices or futures | **VERIFIED** (Authoritative macro discount factor baseline) |
| **NQ** (E-mini Nasdaq Futures) | CME Group | Phase 14 Backlog | Official Exchange | Deep | Yes | Paid | 1999-06 | 1m, tick | Yes | Centralized contracts | Yes | Yes | Quarterly rolls (H, M, U, Z) | N/A | High | Zero | CME DataMine login | Paid ($$$) | Commercial license locked | Yes (Paid SFTP) | US Central / ET; Globex | **NOT FREE:** Official CME data requires human budget authorization | **NOT SUITABLE AT $0** (Requires human budget authorization) |
| **DXY** (US Dollar Index) | Intercontinental Exchange (ICE) | Phase 14 Backlog | Official Exchange | Deep | Yes | Paid | 1973-03 | 1m, tick | Yes | ICE contracts traded | Yes | Yes | Quarterly futures rolls | N/A | High | Zero | ICE Data Services | Paid ($$$) | Commercial license locked | Yes (Paid) | NY / London session | ICE proprietary index; free sources provide only delayed daily closes | **NOT SUITABLE AT $0** (Requires commercial data subscription) |
| **Treasury Futures** (`ZN`, `ZB`) | CME Group / CBOT | Phase 14 Backlog | Official Exchange | Deep | Yes | Paid | 1982+ (`ZB`) | 1m, tick | Yes | Centralized contracts | Yes | Yes | Quarterly rolls; conversion factors | N/A | High | Zero | CME DataMine | Paid ($$$) | Commercial license locked | Yes (Paid) | Chicago / ET; Globex | Non-linear yield-to-price conversion; cheapest-to-deliver dynamics | **NOT SUITABLE AT $0** (Requires human budget authorization) |

---

## 3. Surface Data-Authority Gaps & Research Roadblocks

Systematic review of the multi-asset universe reveals several critical data-authority gaps that prevent unconstrained empirical research at `$0.00`:

```
+---------------------------------------------------------------------------------------------------+
|                                  CRITICAL DATA-AUTHORITY GAPS AT $0                               |
+---------------------------------------------------------------------------------------------------+
| 1. Equity Survivorship Gap:     Active names are free (Stooq); delisted prices are $0-absent.     |
| 2. Futures Microstructure Gap:  ES/NQ/ZN tick & M1 history is strictly commercial (CME DataMine). |
| 3. FX Decentralization Gap:     EURUSD has no centralized tape; tick volume != traded contracts.  |
| 4. Continuous Futures Roll Gap: No authoritative $0 continuous roll methodology (proportional/diff). |
| 5. Corporate Action Provenance: Free split/dividend databases lack cryptographic point-in-time stamps.|
| 6. XAU Physical/Paper Mismatch: Spot OTC fix vs COMEX futures introduces unmodelled basis spread. |
+---------------------------------------------------------------------------------------------------+
```

### 3.1 Equity Survivorship-Free Price Gap (`B2` Blocker)
- **Problem:** While active US equities are freely downloadable via Stooq (`S-10`), bankrupt, acquired, or delisted equities are silently pruned from the database. 
- **Consequence:** Backtesting cross-sectional momentum, mean-reversion, or long-short factor models on active-only data introduces severe upward return bias (`SURVIVORSHIP_LIMITED`).
- **Resolution Path:** SEC EDGAR (`S-02`) identifies delisted companies by CIK and date, but acquiring their historical daily OHLCV prices requires commercial academic/vendor data (e.g. CRSP, Norgate, EODHD delisted archive) requiring Human Governance budget authorization.

### 3.2 Futures Microstructure & Licensing Gap
- **Problem:** E-mini futures (`ES`, `NQ`) and Treasury futures (`ZN`, `ZB`) are traded on CME/CBOT. CME vigorously protects its proprietary data; free intraday or historical tick datasets with verified provenance do not exist in the public domain.
- **Consequence:** Research on futures intraday alpha cannot be conducted under the Free-Data Bootstrap Program without purchasing official CME DataMine history.
- **Resolution Path:** Defer direct futures execution research; focus initial bootstrap research on domains with verified `$0.00` official archives (e.g. Crypto `BTCUSDT` via Binance Vision).

### 3.3 Foreign Exchange Reference Authority Gap
- **Problem:** Spot FX (`EURUSD`) is traded over-the-counter (OTC) across interbank electronic communication networks (ECNs: EBS, Reuters Matching, Currenex). There is no single centralized volume tape or official close.
- **Consequence:** "Volume" reported by secondary aggregators is merely tick count (number of quote updates), which correlates poorly with actual transacted liquidity.
- **Resolution Path:** FX research must treat prices as indicative quotes and volume as unverified; execution slippage models must incorporate wide OTC bid/ask spreads.

### 3.4 Continuous Futures Roll Authority
- **Problem:** Futures contracts expire quarterly. Stitching individual contracts (`ESH23`, `ESM23`, `ESU23`) into a continuous series requires choosing a roll convention (volume crossover, open interest crossover, calendar days before expiry) and an adjustment method (backward ratio, backward difference, forward difference).
- **Consequence:** Different roll methods introduce artificial trend or volatility distortions. No free provider publishes an authoritative, point-in-time continuous roll master.
- **Resolution Path:** ACASH must implement its own deterministic, rule-based roll engine rather than relying on pre-rolled vendor series.

### 3.5 Corporate Action Adjustment Provenance
- **Problem:** Free equity data sources apply proprietary, undocumented split and dividend adjustments to historical prices.
- **Consequence:** Distorts point-in-time price levels and creates look-ahead leakage if ex-dividend adjustments are applied before the actual ex-date.
- **Resolution Path:** Require raw unadjusted prices + discrete corporate action event records (SEC EDGAR) rather than pre-adjusted vendor series.

---

## 4. Research Question Decision Guide

To determine data readiness for any proposed quantitative research question, apply this decision guide:

| If ACASH chooses to investigate... | What Provider Evidence Already Exists? | What is Structurally Missing? | What Must Be Qualified Before Empirical Backtesting? |
| :--- | :--- | :--- | :--- |
| **Hypothesis 1: BTC Intraday Momentum / Regime** | Verified Binance Vision M1 archives (`2017–Present`); verified Kraken historical trade dumps. | Live top-of-book bid/ask recording (spread evidence). | Run Phase 14 Data Qualification Suite (`historical_data_qualification_spec.md`); dual-source reconciliation. |
| **Hypothesis 2: Macro Announcement Volatility** | Verified Federal Reserve / BLS release calendars (`S-05`, `S-08`); daily FRED rates (`S-04`). | Intraday VIX quotes at 1-second resolution around announcements. | Event-date point-in-time timestamp sealing; release calendar verification. |
| **Hypothesis 3: US Equity Cross-Sectional Drift** | Active-name daily OHLCV (`S-10`); SEC Form 25 delisting roster (`S-02`). | **Delisted equity price history**; corporate action adjustment provenance. | Must declare candidate `SURVIVORSHIP_LIMITED`; or acquire licensed delisted price history. |
| **Hypothesis 4: Equity Index Futures (`ES`) Alpha** | Indicative cash index (`^SPX`) and ETF (`SPY`) daily data (`S-10`). | **Licensed CME intraday contract data**; official tick tape; roll methodology. | Cannot commence at `$0.00`; requires Human Governance budget authorization for CME DataMine. |
| **Hypothesis 5: Systematic FX Trend Following** | Indicative daily quotes (`S-10`, `S-04`). | Centralized transacted volume; institutional ECN order book depth. | Formulate spread crossing cost model for OTC liquidity; verify 5 PM NY rollover conventions. |

---

## 5. Summary of Evidence Status by Domain

| Domain | Primary Asset | Available at $0.00? | Evidence Status | Research Readiness Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Crypto Assets** | `BTC`, `ETH` | **Yes** (Binance Vision / Kraken) | **`VERIFIED`** | **Ready for Data Qualification & Decision Ratification** |
| **Macro / Calendar** | `CPI`, `FOMC`, `NFP` | **Yes** (BLS / Fed / Treasury) | **`VERIFIED`** | **Ready for Announcement Calendar Compilation** |
| **Fixed Income / Rates**| `DGS10`, `DGS2` | **Yes** (FRED / Treasury) | **`VERIFIED`** | **Ready for Macro Regime Conditioning** |
| **FX Spot** | `EURUSD` | Daily Yes / Intraday No | **`PARTIALLY VERIFIED`** | **Constrained to Daily Macro / Trend Analysis** |
| **Metals / Commodities**| `XAU` (Gold) | Daily Indicative Yes | **`PARTIALLY VERIFIED`** | **Constrained by OTC Basis & Cash-Futures Discrepancies** |
| **US Equities** | Large-Cap Panel | Active Yes / Delisted No | **`PARTIALLY VERIFIED`** | **Blocked from Equal-Footing Cross-Section by Survivorship Bias** |
| **Index Futures** | `ES`, `NQ` | **No** (CME Proprietary) | **`NOT SUITABLE AT $0`** | **Blocked; Requires Human Budget Authorization** |

---

### Verification Ledger
- Implementation Status: COMPLETE (Multi-asset provider comparison matrix)
- Contract Enforcement: STRICT FAIL-CLOSED (No competing registry, no license inferred, zero backtest authority)
- Mathematical Authority: CANONICAL SPEC (Inherits from `free_data_source_registry.md` and `asset_market_agnostic_research_direction.md`)
- Local Test Suite: NOT RUN (Documentation-only deliverable)
- Type Checker (MyPy): NOT RUN (Documentation-only deliverable)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: Comparison statuses reflect current public data accessibility as of September 2026. Commercial exchange licenses (CME, ICE) are explicitly classified as not suitable at $0.00.
