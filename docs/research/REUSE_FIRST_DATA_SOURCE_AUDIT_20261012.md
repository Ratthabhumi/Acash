# ACASH — Reuse-First Data Source Qualification Audit

**Document ID:** `DOC-ACASH-DATA-REUSE-AUDIT-20261012`  
**Classification:** Research Feasibility & Data Provenance Audit (Offline / Pre-Acquisition)  
**Governing Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Single Authority)  
**Effective Date:** 2026-10-12  
**HTTP Data Acquisition Status:** `NO_NEW_MARKET_DATA_HTTP = true`; Zero external API calls made during this task.  

---

## 1. Executive Summary & Reuse Principle

Rather than prematurely inventing new third-party data connectors or purchasing costly market data feeds, ACASH conducts a **Reuse-First Audit** across:
1. Previously audited public sources from `docs/phase14/free_data_source_registry.md` and `docs/phase14/free_data_dolthub_source_audit.md`.
2. Existing qualified Alpaca historical schemas (`daily_models.py`, `mec_0015_dividend_contract.py`, `mec_0014_transaction_contract.py`).
3. Official provider technical documentation and broker tariff schedules.

---

## 2. Comprehensive Data Source Qualification Matrix

| Source ID | Candidate Data Stream | Official Provider / Endpoint | Depth & Scope | Inception / Boundary | License / Terms | ACASH Qualification Classification | Rationale & Critical Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DS-01** | **Alpaca 1Day Historical Bars** | `GET /v2/stocks/bars?timeframe=1Day` | 2016–Present (SIP/IEX) | Per-asset listing date | Developer / Trading account ToS; redistribution restricted. | **OFFICIALLY_DOCUMENTED** | Supports `adjustment=raw,split,dividend,all`. However, `adjustment=all` is a retroactive snapshot, **NOT point-in-time guaranteed**. Revisions occur without published vintage manifests. |
| **DS-02** | **Alpaca SPY 1-Min Bars (RI-01)** | `GET /v2/stocks/bars?timeframe=1Min` | 2021-06-01 (Canary 1) | 390 RTH grid verified on disk | External disk artifact `page_0000.bin` | **QUALIFIED_FOR_ANOTHER_SCOPE_ONLY** | Fully verified for opening state measurement (Canary 1), but strictly inappropriate for multi-year daily macro ETF portfolio rebalancing. |
| **DS-03** | **Alpaca Corporate Actions** | `GET /v1/corporate-actions` | 2007–2024 (SPY evaluated in MEC-0015) | Ex-date bounded | Internal research permitted; redistribution restricted. | **OFFICIALLY_DOCUMENTED** | Historical complete snapshot available; point-in-time announcement timestamp is unverified. Ex-date vs. Pay-date lag must be strictly modeled. |
| **DS-04** | **Vanguard Historical ETF Data (VOO)** | Vanguard Institutional / EDGAR N-PORT | Daily NAV & distributions | **Inception: 2010-09-07** | Public regulatory filings & prospectus | **OFFICIALLY_DOCUMENTED** | **Hard Inception Boundary**: VOO did not exist prior to September 7, 2010. Any request for VOO price data prior to this date must fail closed. Simulating pre-2010 requires an index proxy (`SPX_SYNTHETIC_PROXY`) explicitly labeled as synthetic. |
| **DS-05** | **iShares Historical ETF Data (AGG / IAU)** | BlackRock iShares / EDGAR | Daily NAV & distributions | AGG: 2003-09-22<br>IAU: 2005-01-21 | Public fund reporting | **OFFICIALLY_DOCUMENTED** | Long history covering 2008 GFC. Distributions are monthly for AGG; NAV returns differ from secondary market trade prices due to creation/redemption premium/discount. |
| **DS-06** | **SPDR Historical ETF Data (GLD / BIL)** | State Street Global Advisors | Daily NAV & distributions | GLD: 2004-11-18<br>BIL: 2007-05-25 | Public fund reporting | **OFFICIALLY_DOCUMENTED** | BIL serves as primary cash/T-Bill proxy ETF. Reinvestment of monthly dividend distributions must be modeled accurately to compute Total Return. |
| **DS-07** | **Bank of Thailand (BOT) FX API** | `portal.api.bot.or.th` (Daily Weighted Average THB/USD) | Multi-decade daily fixings | Daily banking days | Free registration API key required; official central bank publication. | **OFFICIALLY_DOCUMENTED** | Authoritative reference rate for Thai macroeconomic accounting. **Limitation**: Official fixing $\neq$ retail broker commercial exchange rate. Broker FX spread markup (20–50 bps) must be deducted for THB conversions. |
| **DS-08** | **Federal Reserve / FRED** | `fred.stlouisfed.org` (`DTB3`, `DGS10`, `VIXCLS`) | 1960s/1990s–Present | Daily macro time series | Federal public data; free API with key. | **ALREADY_QUALIFIED_FOR_THIS_USE** | Registered as S-04 in Phase 14 Free-Data Registry. Verified for macro regime signals and risk-free hurdle baselines. |
| **DS-09** | **Kenneth French Data Library** | Dartmouth / Kenneth French web portal | 1926–Present (Monthly/Daily) | Factor portfolio returns | Academic free access for research. | **QUALIFIED_FOR_ANOTHER_SCOPE_ONLY** | Excellent for post-hoc factor attribution (testing if strategy is disguised beta), but **NOT SUITABLE** for portfolio execution since factor portfolios are theoretical and non-tradable. |
| **DS-10** | **Stooq Daily OHLCV** | `stooq.com/db/h/` | 30+ years active US equities | Active symbols only | Personal non-commercial only; commercial prohibited. | **LICENSE_OR_ENTITLEMENT_UNKNOWN** | Registered as S-10. Useful for exploratory checks, but survivorship-biased (delisted equities purged) and licensing prohibits commercial integration. |
| **DS-11** | **Interactive Brokers (IBKR) Fee Tariffs** | IBKR Official Pricing Schedule | Current live schedule | Order minimums | Contract tariff | **OFFICIALLY_DOCUMENTED** | Tiered: $0.35/order min; Fixed: $1.00/order min. **Critical for $1,000 Portfolio**: A $0.35 fee on a $70 rebalance ticket equals **0.50% friction**; a $1.00 fee equals **1.43% friction**. Low-turnover monthly rebalance is mandatory to survive this drag. |

---

## 3. Epistemic Gap Analysis: PIT Availability vs. Retroactive Adjustment

A primary vulnerability in retail quantitative backtesting is confusing **retroactive adjustment** with **point-in-time observability**:

1. **Retroactive Split / Dividend Adjustment (`adjustment=all`)**:
   - Compounding historical prices backwards by current adjustment factors creates look-ahead bias if corporate action announcements were delayed or revised.
   - Backtests using retroactively adjusted bars assume that the dividend amount and ex-date were known with 100% certainty years in advance.

2. **Point-in-Time (PIT) Observable Pricing**:
   - On trading date $t$, an investor observes only the unadjusted closing price $P_t$ and previously credited cash dividends $D_{\le t}$.
   - Corporate action announcements have an announcement timestamp, ex-dividend date, record date, and payable date.
   - ACASH data contracts must explicitly separate:
     - `raw_price`: The actual unadjusted execution price on day $t$.
     - `split_factor`: Multiplier applicable on or after the ex-split date.
     - `dividend_cash`: Cash distribution amount credited per share on payable date.
     - `total_return_factor`: The compounding capital growth factor reflecting exact reinvestment.

---

## 4. Operational Boundaries
- Acquisition of live/historical datasets requires explicit operator authorization via a separate data ingestion manifest.
- Zero network requests were dispatched during this audit.
