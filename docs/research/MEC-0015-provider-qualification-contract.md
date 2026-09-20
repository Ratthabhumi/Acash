# MEC-0015: Provider Qualification Contract

```text
[GOVERNANCE ARTIFACT: PROVIDER DATA QUALIFICATION CONTRACT]
[GENERATED: 2026-09-20]
[UPDATED: 2026-09-21]
[CANONICAL STARTING HEAD: dd249d54e59c471bfdc98bc3c6d17781cbc2a08e]
[HYP_005: NOT CREATED]
[BACKTEST: NOT STARTED]
[STRATEGY P&L: NOT COMPUTED]
[MARKET DATA ACCESS: QUALIFICATION PROBES COMPLETED (< 2024-05-01)]
[OOS BOUNDARY: >= 2024-05-01 STRICTLY NOT ACCESSED]
[2025-2026: NOT ACCESSED]
[CAPITAL: $0.00 | NO_REAL_ORDERS: true]
```

---

## 1. Provider Contract Overview

This document records the completed provider data qualifications for **MEC-0015** prior to registering `HYP_005`. The authoritative data source is **Alpaca Markets Historical SIP** for US equities.

All provider contracts (1-minute SIP bars, corporate actions cash dividends, and historical SIP NBBO quotes) are fully qualified and sealed with cryptographic manifests.

---

## 2. Bar Endpoint Contract (RESOLVED)

### 2.1. Endpoint Specification

| Parameter | Resolved Value | Authority |
| :--- | :--- | :--- |
| **API Base URL** | `https://data.alpaca.markets` | Alpaca documentation |
| **Endpoint Path** | `/v2/stocks/SPY/bars` | Alpaca documentation |
| **Feed** | `feed=sip` | MEC-0015 contract; SIP = consolidated US exchanges |
| **Timeframe** | `timeframe=1Min` | MEC-0015 contract |
| **Adjustment** | `adjustment=raw` | MEC-0015 contract; unadjusted prices preserve real execution boundaries |
| **Sort** | `sort=asc` | Required for temporal monotonicity |
| **Pagination** | Paginate to exhaustion (`next_page_token = null`) | ACASH contract; sub-limit page ≠ exhaustion |

**Implementation Reference:** `src/acash/data/qualification/mec_0015_bar_contract.py`  
**Status:** `RESOLVED`

---

## 3. Bar Qualification Manifest & Audit Trail Correction

### 3.1. Canonical Manifest Pin
- **Qualification Commit:** `dd249d54e59c471bfdc98bc3c6d17781cbc2a08e`
- **Manifest File:** `docs/research/manifests/MEC-0015-bar-provider-contract-manifest.json`
- **Manifest Digest:** `cc399c5df3c9970ff89a308f60036c0014f9152d9b280c57feb7b7e782fc7316`
- **Status:** `LIVE_PROVIDER_QUALIFICATION_COMPLETE`
- **Sessions Qualified (6/6 PASS):**
  - `2018-06-01`: 390 / 390 bars (missing 0)
  - `2019-06-03`: 390 / 390 bars (missing 0)
  - `2020-06-01`: 390 / 390 bars (missing 0)
  - `2021-06-01`: 390 / 390 bars (missing 0)
  - `2022-06-01`: 390 / 390 bars (missing 0)
  - `2024-03-01`: 390 / 390 bars (missing 0)
- **Total Bars:** 2,340 / 2,340 bars; missing = 0.

### 3.2. Audit Trail Correction
The live network qualification probe for 1-minute SIP bars involved two network retrieval attempts:
1. **Attempt 1:** The authorized six dates were fetched successfully across the network; the process crashed during terminal output rendering due to an unhandled Unicode checkmark (`✓`) on the Windows console.
2. **Attempt 2:** The probe was rerun with ASCII-safe console output, fetching the identical authorized dates, completing successfully, and generating the canonical manifest.

**Formal Classification:**
- `NETWORK_RETRIEVAL_ATTEMPTS = 2`
- `UNIQUE_MARKET_DATES_ACCESSED = 6`
- `UNAUTHORIZED_DATES_ACCESSED = 0`
- `MAX_ACCESSED_DATE = 2024-03-01`
- `EMPIRICAL_SCOPE_IMPACT = NONE`

The qualification is not described as a "single execution" in audit records; the empirical and cryptographic integrity of the manifest is intact.

---

## 4. Bar Timestamp Semantics & Mapping (RESOLVED)

### 4.1. Alpaca Bar Timestamp = LEFT EDGE of Interval
$$\text{bar timestamp} = \text{LEFT EDGE of } [\text{timestamp}, \text{timestamp} + 1\text{min})$$

| Bar Timestamp (ET) | Interval Represented | Trades Captured |
| :--- | :--- | :--- |
| `09:30:00` | `[09:30:00, 09:31:00)` | First RTH minute (`BAR_0930`) |
| `09:59:00` | `[09:59:00, 10:00:00)` | Minute preceding 10:00 decision |
| `10:00:00` | `[10:00:00, 10:01:00)` | First exposure minute (post-10:00 decision) |
| `15:59:00` | `[15:59:00, 16:00:00)` | Last RTH bar (`BAR_1559`) |

**`BAR_TIMESTAMP_SEMANTICS = LEFT_EDGE_OF_ONE_MINUTE_INTERVAL`**

### 4.2. Author Decision-Time to Alpaca Bar Timestamp Mapping
Author reference code evaluates decisions at right-edge conceptual timestamps (the end of each 30-minute epoch). Alpaca labels bars by left-edge:

$$\text{Alpaca Bar Timestamp for Decision at } HH:MM = (HH:MM - 1\text{min})$$

---

## 5. Regular Trading Hours (RTH) & Missing Bar Policy (RESOLVED)

- **RTH Open:** `09:30:00 ET` (first bar `BAR_0930`)
- **RTH Close:** `16:00:00 ET` (last bar `BAR_1559`)
- **Bar Count (Standard Session):** Exactly 390 bars.
- **Calendar Authority:** NYSE regular session calendar (`NyseCa1Calendar`).
- **Missing Bar Policy:** `MISSING_REQUIRED_MINUTE_POLICY = FAIL_CLOSED_SESSION_EXCLUSION`. Zero silent forward-fill or price imputation. Any missing bar in a standard session raises `DataContractError`.

---

## 6. Provider VWAP Rejection (RESOLVED)

- `PROVIDER_VWAP_FIELD_STATUS = AVAILABLE_BUT_REJECTED_FOR_MEC_0015_SIGNAL_VWAP`
- MEC-0015 strictly computes VWAP from raw OHLCV using Typical Price $(H+L+C)/3$.

---

## 7. Dividend Provider Contract (RESOLVED)

MEC-0015 author reference code requires current-day cash dividend for the gap anchor:
$$\text{prev\_close\_adjusted} = \text{Close}[t-1, 16:00] - \text{dividend}[t]$$

### 7.1. Corporate Actions Endpoint Specification
- **Endpoint:** `GET https://data.alpaca.markets/v1/corporate-actions`
- **Parameters:** `symbols=SPY`, `types=cash_dividend`, `data_quality=complete`
- **Allowed Query Range:** `2007-01-01` through `2024-04-30` (publication-exposed).
- **Prohibition:** Strictly zero access on or after `2024-05-01`.

### 7.2. Empirical Qualification Results
- **Manifest:** `docs/research/manifests/MEC-0015-dividend-provider-contract-manifest.json`
- **Raw Payload SHA-256:** `52bd4a98a1e5ec26fc9b9799e488a7487fa5ceb7135852a0f69bff985c24c0ad`
- **Actions Retrieved:** 31 SPY cash dividend actions.
- **Ex-Date Range:** Minimum ex-date `2016-06-17`, Maximum ex-date `2024-03-15`.
- **Ex-Date Distribution:** Zero records on or after `2024-05-01`.
- **Field Schema:** Symbol, action type, cash amount, ex-date, process date, record/payable date where available, source ID.
- **Do NOT derive dividend from adjusted price differences.**

### 7.3. Classifications & Fail-Closed Boundaries
- `DIVIDEND_PROVIDER_MAPPING = QUALIFIED_HISTORICAL_COMPLETE_SNAPSHOT`
- `DIVIDEND_POINT_IN_TIME_VINTAGE = NOT_GUARANTEED_BY_PROVIDER`
  *(Alpaca explicitly does not guarantee creation timing; acceptable for publication-exposed historical replication, but not point-in-time guaranteed for prospective live trading).*
- **Fail-Closed Rule:** If an ex-date dividend required by strategy is absent or ambiguous, raise `DATA_CONTRACT_EXCLUSION`. Never assume dividend = 0 under corporate action uncertainty.

---

## 8. Historical SIP Quotes Qualification & Execution Fill Contract (RESOLVED)

### 8.1. SIP Quotes Endpoint Specification
- **Endpoint:** `GET https://data.alpaca.markets/v2/stocks/quotes`
- **Parameters:** `symbols=SPY`, `feed=sip`, `sort=asc`, `limit=50`
- **Probe Sessions:** `2019-06-03`, `2022-06-01`, `2024-03-01` (narrow publication-exposed probe only).
- **Decision Epochs Probed:** `10:00:00 ET`, `12:00:00 ET`, `15:30:00 ET`.

### 8.2. Empirical Qualification Results
- **Manifest:** `docs/research/manifests/MEC-0015-quote-provider-contract-manifest.json`
- **Raw Payload SHA-256:** `593b8aa6f51be0e588ea7bdf4164b3ef658c1482f3efc29aa4f0612c6a46132a`
- **Windows Evaluated:** 9 / 9 decision boundaries valid.
- **Latency Distribution (`quote_timestamp - execution_boundary`):**
  - Minimum: `0.466 ms`
  - Median: `1.668 ms`
  - Mean: `4.700 ms`
  - Maximum: `14.982 ms`
- **Spread & Invariant Validation:**
  - `bid > 0`, `ask > 0`, `ask >= bid` across 100% of probe windows.
  - Zero crossed or locked market quotes observed.

### 8.3. Execution Fill Model (RESOLVED)
- **`PRIMARY_EXECUTION_MODEL = FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY`**
- Execution Semantics:
  - For a BUY: `fill_price = ask`
  - For a SELL: `fill_price = bid`
- Rationale: The signal depends on the completed preceding minute bar (ending at $T$). The first quote with `timestamp >= T` guarantees quote timestamp is not earlier than the completed signal information, preventing look-ahead and realistically capturing the spread crossing.
- Rejection Criteria: Reject quote if `bid <= 0`, `ask <= 0`, `ask < bid`, or required NBBO fields are missing.

---

## 9. Spread & Friction Contract Integration (RESOLVED)

- **`ACASH_SPREAD_MODEL = EMBEDDED_IN_NBBO_FILL`**
  - BUY at Ask; SELL at Bid.
  - **`EXPLICIT_HALF_SPREAD_DEDUCTION_WITH_NBBO = PROHIBITED`** (Zero additional half-spread deduction).
- **`BASELINE_STANDALONE_SLIPPAGE = $0.001/share`** per executed side (adverse direction: BUY at $\text{Ask} + \$0.001$, SELL at $\text{Bid} - \$0.001$).
- **2× Friction Stress Specification:** Retain observed NBBO bid/ask fill, multiply non-spread explicit costs by 2.0, plus add an adverse slippage stress equal to one observed half-spread per side ($(\text{Ask} - \text{Bid})/2$).

---

## 10. Summary of Provider Qualifications

| Contract Item | Status | Supporting Manifest / Hash |
| :--- | :--- | :--- |
| Bar endpoint (`/v2/stocks/SPY/bars`, SIP, 1Min, raw) | `RESOLVED` | `MEC-0015-bar-provider-contract-manifest.json` (`cc399c5...`) |
| Bar timestamp left-edge semantics | `RESOLVED` | Pinned in Section 4 |
| Author decision-time mapping | `RESOLVED` | Pinned in Section 4 |
| RTH scope (09:30–15:59 ET, 390 bars) | `RESOLVED` | Pinned in Section 5 |
| Missing-bar policy (`FAIL_CLOSED_SESSION_EXCLUSION`) | `RESOLVED` | Pinned in Section 5 |
| Provider VWAP rejection | `RESOLVED` | Pinned in Section 6 |
| Dividend data provider (`/v1/corporate-actions`) | `RESOLVED` | `MEC-0015-dividend-provider-contract-manifest.json` (`52bd4a9...`) |
| Historical SIP Quotes (`/v2/stocks/quotes`) | `RESOLVED` | `MEC-0015-quote-provider-contract-manifest.json` (`593b8aa...`) |
| Execution fill price model (First valid NBBO $\ge T$) | `RESOLVED` | Pinned in Section 8 |
| Spread model (Embedded in NBBO; double-counting prohibited)| `RESOLVED` | Pinned in Section 9 |

**TOTAL REMAINING OPEN PROVIDER BLOCKERS: 0**
