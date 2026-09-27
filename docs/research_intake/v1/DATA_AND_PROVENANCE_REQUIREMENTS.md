# ACASH Data Architecture & Provenance Requirements Standard

## 1. Overview & General Invariants

Before any quantitative candidate can advance from R0 intake to prospective empirical analysis, an authoritative data provenance contract must be established. No empirical data may be queried or ingested without satisfying the standards set forth in this document.

### General Data Invariants:
1. **Single Source Authority**: Every ingested series must trace back to a single authoritative publisher with immutable lineage.
2. **Point-in-Time Integrity**: Data must reflect exact information available as-of the execution decision timestamp. Zero future revision leakage (lookahead bias) is permitted.
3. **No Unverified Data Vendor Substitution**: Free web-scraped data or broker CFD feeds cannot be substituted for authoritative exchange feeds without explicit research governance ratification.
4. **Timestamp Precision**: Required timestamp precision: `SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT`.
5. **Exact Session Hours**: `EXACT_SESSION_HOURS: VERIFY_AT_FUTURE_DATA_CONTRACT_STAGE`.
6. **Settlement Style**: `SETTLEMENT_STYLE: VERIFY_PER_INSTRUMENT_AND_SERIES`.
7. **Rate Model**: `RATE_MODEL: NOT_YET_DETERMINED`.
8. **Pricing Model**: `PRICING_MODEL: NOT_YET_DETERMINED`.

---

## 2. Asset-Class Specific Provenance Contracts

### A. Equities & ETFs
- **Instruments**: Single-stock equities and exchange-traded funds (exact universe: `NOT_YET_DETERMINED`).
- **Authoritative Venues**: Primary listings or direct consolidated feeds (ILLUSTRATIVE_ONLY — NOT PREREGISTERED: NASDAQ, NYSE, Cboe).
- **Feed Semantics**: Consolidated SIP feeds or direct proprietary feeds (ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
- **Corporate Actions**: Fully documented split and dividend adjustment history. Explicit separation between raw unadjusted execution prices and adjusted historical series for return calculations.
- **Timestamps & Calendar**: `EXACT_SESSION_HOURS: VERIFY_AT_FUTURE_DATA_CONTRACT_STAGE`. Canonical market timezone bound by instrument at data-contract stage with `UTC_STORAGE: REQUIRED`. Handling of early closes and regulatory halts.

### B. Index Futures
- **Instruments**: Index futures (exact contracts: `NOT_YET_DETERMINED`).
- **Authoritative Venues**: Regulated futures exchanges (ILLUSTRATIVE_ONLY — NOT PREREGISTERED: CME Globex).
- **Contract & Roll Specifications**:
  - Roll method specification: calendar volume crossover roll vs. fixed days-to-expiration roll (`NOT_YET_PREREGISTERED`).
  - Price adjustment: backwards-ratio adjusted, backwards-difference adjusted, or raw unadjusted front-month contract with explicit roll event logging.
- **Trading Hours**: `EXACT_SESSION_HOURS: VERIFY_AT_FUTURE_DATA_CONTRACT_STAGE`. Exact exchange session and maintenance schedule must be verified against the canonical exchange calendar during the future data-contract stage.

### C. Foreign Exchange (FX)
- **Instruments**: Currency pairs (exact pairs: `NOT_YET_DETERMINED`).
- **Authoritative Venues**: Over-The-Counter (OTC) interbank market.
- **Feed Semantics**:
  - Retail broker quote feeds represent dealer pricing, NOT a single centralized exchange.
  - Strict documentation of quote spread, dealer markup, and asymmetric slippage.
- **Trading Hours & Sessions**: `EXACT_SESSION_HOURS: VERIFY_AT_FUTURE_DATA_CONTRACT_STAGE`. Session definitions and liquidity shifts must be audited against canonical interbank conventions without freezing arbitrary retail clock windows. Continuous 24/5 trading semantics with handling of European vs. US DST misalignment.

### D. Listed Options
- **Instruments**: Equity and Index Options (exact contracts: `NOT_YET_DETERMINED`).
- **Authoritative Venues**: Regulated option exchanges / reporting authorities (ILLUSTRATIVE_ONLY — NOT PREREGISTERED: OPRA).
- **Data Granularity**:
  - End-of-Day (EOD) closing quotes vs. high-frequency tick/quote option data (`NOT_YET_DETERMINED`).
  - Strike and expiration rules.
- **Settlement Style**: `SETTLEMENT_STYLE: VERIFY_PER_INSTRUMENT_AND_SERIES` (Settlement conventions vary by product, series, and expiration; settlement style must not be universally oversimplified).
- **Greeks & Pricing Calibration**:
  - `PRICING_MODEL: NOT_YET_DETERMINED` (models such as Black-76, Bjerksund-Stensland, or Binomial are ILLUSTRATIVE_ONLY — NOT PREREGISTERED).
  - `RATE_MODEL: NOT_YET_DETERMINED` (discount curves, interest rate proxies, and dividend yield assumptions must be formally preregistered at the data-contract stage).

### E. Microstructure Order Flow & Market Depth
- **Instruments**: Index Futures and Equities (`NOT_YET_DETERMINED`).
- **Feed Semantics**: Top of Book (L1) vs. Market Depth (L2) vs. Order-by-order (L3) direct order-book feeds. Exact venue feed implementation: `NOT_YET_DETERMINED`.
- **Order Flow Imbalance (OFI)**:
  - Exact algorithm for signing trades (Lee-Ready tick test vs. quote-rule matching).
  - Explicit timestamp matching: trades matched strictly against preceding quotes with documented network dissemination latency buffers.
- **Timestamp Precision**: `TIMESTAMP_PRECISION: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT`.

### F. Option Open Interest (OI) & Gamma Exposure (GEX)
Due to pervasive confusion in retail discourse regarding open interest and dealer positioning, any empirical research utilizing OI or GEX must strictly document the distinction between official vs estimated OI:

```
OI_SOURCE:                  [Authoritative Clearinghouse / Vendor (ILLUSTRATIVE_ONLY: CME Clearing, OCC, Cboe)]
OI_ASOF:                    [Exact settlement date and publication timestamp]
OFFICIAL_OR_ESTIMATED:      [OFFICIAL_CLEARINGHOUSE / MODEL_ESTIMATED_INTRADAY]
DEALER_SIGN_METHOD:         [Inferred net customer order flow sign / Fixed assumption — NOT_YET_PREREGISTERED]
GREEKS_MODEL:               [PRICING_MODEL: NOT_YET_DETERMINED (ILLUSTRATIVE_ONLY: Black-76 / Bjerksund-Stensland)]
RATE_MODEL:                 [RATE_MODEL: NOT_YET_DETERMINED]
SETTLEMENT_STYLE:           [SETTLEMENT_STYLE: VERIFY_PER_INSTRUMENT_AND_SERIES]
OPTIONS_EXPIRY_SCOPE:       [Near-month / 0DTE / All active expiries — NOT_YET_PREREGISTERED]
0DTE_INCLUDED:              [TRUE / FALSE]
```

- **Critical Governance Rule**: Public clearinghouse Open Interest is reported once daily after overnight clearing. Any real-time "intraday OI" signal is a model-estimated quantity and must be labeled `MODEL_ESTIMATED_INTRADAY` (official vs estimated OI).
- **OI != GEX**: Open Interest is a static contract count. Gamma Exposure (GEX) is a model-dependent derivative estimate that requires strong assumptions regarding market-maker inventory dealer sign.

### G. CFD Feeds & Retail Platforms
- **Feed Nature**: Contract for Difference (CFD) broker feeds reflect localized broker liquidity pools and internal pricing engines.
- **Volume Semantics**: CFD volume semantics differ materially from centralized exchange volume. CFD tick volume measures broker quote updates, NOT actual exchange turnover or financial volume.
- **Policy**: CFD feeds are NOT authorized as primary empirical research sources for CME index futures or US equities at R0.
