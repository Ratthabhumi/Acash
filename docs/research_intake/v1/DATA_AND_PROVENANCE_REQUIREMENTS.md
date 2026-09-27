# ACASH Data Architecture & Provenance Requirements Standard

## 1. Overview & General Invariants

Before any quantitative candidate can advance from R0 intake to prospective empirical analysis, an authoritative data provenance contract must be established. No empirical data may be queried or ingested without satisfying the standards set forth in this document.

### General Data Invariants:
1. **Single Source Authority**: Every ingested series must trace back to a single authoritative publisher with immutable SHA-256 lineage.
2. **Point-in-Time Integrity**: Data must reflect exact information available as-of the execution decision timestamp. Zero future revision leakage (lookahead bias) is permitted.
3. **No Unverified Data Vendor Substitution**: Free web-scraped data or broker CFD feeds cannot be substituted for authoritative exchange feeds without explicit research governance ratification.

---

## 2. Asset-Class Specific Provenance Contracts

### A. US Equities & ETFs
- **Instruments**: Single-stock equities (e.g., NVDA, AAPL) and exchange-traded funds (e.g., SPY, QQQ).
- **Authoritative Venues**: Primary listings on NASDAQ, NYSE, Cboe.
- **Feed Semantics**: Consolidated Tape Association (CTA) / Unlisted Trading Privileges (UTP) SIP feeds, or direct proprietary feeds (NASDAQ TotalView, NYSE Integrated).
- **Corporate Actions**: Fully documented split and dividend adjustment history. Explicit separation between raw unadjusted execution prices and adjusted historical series for return calculations.
- **Timestamps & Calendar**: Microsecond-resolution UTC timestamps with canonical mapping to America/New_York. Handling of early closes (13:00 ET) and regulatory halts (LULD).

### B. US Index Futures
- **Instruments**: E-mini and Micro E-mini index futures (CME: ES, MES; CME: NQ, MNQ).
- **Authoritative Venues**: Chicago Mercantile Exchange (CME Globex).
- **Contract & Roll Specifications**:
  - Explicit contract month symbols (e.g., ESH26, NQM26).
  - Roll method specification: calendar volume crossover roll vs. fixed days-to-expiration roll.
  - Price adjustment: backwards-ratio adjusted, backwards-difference adjusted, or raw unadjusted front-month contract with explicit roll event logging.
- **Trading Hours**: CME Globex 23-hour trading cycle (18:00 ET to 17:00 ET next day with 15-minute maintenance halt).

### C. Foreign Exchange (FX)
- **Instruments**: G10 currency pairs (e.g., USD/JPY, EUR/USD).
- **Authoritative Venues**: Over-The-Counter (OTC) interbank market (e.g., EBS, Currenex, Refinitiv Matching).
- **Feed Semantics**:
  - Retail broker quote feeds represent dealer pricing, NOT a single centralized exchange.
  - Strict documentation of quote spread, dealer markup, and asymmetric slippage.
- **Calendar & Session Semantics**: Continuous 24/5 trading. Explicit definition of session boundaries (e.g., London 08:00–16:30 GMT, New York 08:00–17:00 ET, Tokyo 09:00–17:00 JST). Strict handling of European vs. US DST misalignment.

### D. Listed Options
- **Instruments**: US Equity and Index Options (e.g., SPX, SPY, QQQ, NVDA options).
- **Authoritative Venues**: OPRA (Options Price Reporting Authority) consolidating 16 US option exchanges.
- **Data Granularity**:
  - End-of-Day (EOD) closing quotes vs. high-frequency tick/quote OPRA data.
  - Exact strike, expiration date, settlement style (AM cash-settled for SPX vs. PM physical-settled for SPY).
- **Greeks & Pricing Calibration**: Exact specification of implied volatility solver, risk-free discount curve (SOFR/Treasury), dividend yield assumptions, and early exercise models (American vs. European).

### E. Microstructure Order Flow & Market Depth
- **Instruments**: CME Index Futures and US Equities.
- **Feed Semantics**: Level 1 (Top of Book / NBBO) vs. Level 2 (Market Depth / Aggregate Price Levels) vs. Level 3 (Order-by-order, e.g., CME ITCH).
- **Order Flow Imbalance (OFI)**:
  - Exact algorithm for signing trades (Lee-Ready tick test vs. quote-rule matching).
  - Explicit timestamp matching: trades matched strictly against preceding quotes with documented network dissemination latency buffers.

### F. Option Open Interest (OI) & Gamma Exposure (GEX)
Due to pervasive confusion in retail discourse regarding open interest and dealer positioning, any empirical research utilizing OI or GEX must strictly document the distinction between official vs estimated OI:

```
OI_SOURCE:                  [Authoritative Clearinghouse / Vendor, e.g., CME Clearing, OCC, Cboe]
OI_ASOF:                    [Exact settlement date and publication timestamp, e.g., 07:00 ET next day]
OFFICIAL_OR_ESTIMATED:      [OFFICIAL_CLEARINGHOUSE / MODEL_ESTIMATED_INTRADAY]
DEALER_SIGN_METHOD:         [Inferred net customer order flow sign / Fixed assumption]
GREEKS_MODEL:               [Black-76 / Bjerksund-Stensland / American Binomial]
OPTIONS_EXPIRY_SCOPE:       [Near-month / 0DTE / All active expiries]
0DTE_INCLUDED:              [TRUE / FALSE]
```

- **Critical Governance Rule**: Public clearinghouse Open Interest is reported once daily after overnight clearing. Any real-time "intraday OI" signal is a model-estimated quantity and must be labeled `MODEL_ESTIMATED_INTRADAY` (official vs estimated OI).
- **OI != GEX**: Open Interest is a static contract count. Gamma Exposure (GEX) is a model-dependent derivative estimate that requires strong assumptions regarding market-maker inventory dealer sign.

### G. CFD Feeds & Retail Platforms
- **Feed Nature**: Contract for Difference (CFD) broker feeds reflect localized broker liquidity pools and internal pricing engines.
- **Volume Semantics**: CFD "tick volume" measures broker quote updates, NOT actual exchange turnover or financial volume.
- **Policy**: CFD feeds are prohibited as primary empirical research sources for CME index futures or US equities.
