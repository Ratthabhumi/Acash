# MEC-0015: Provider Qualification Contract

```text
[GOVERNANCE ARTIFACT: PROVIDER DATA QUALIFICATION CONTRACT]
[GENERATED: 2026-09-20]
[CANONICAL HEAD: 5b09ccadeccbc250a88f881b80b2845d5c2f7ec9]
[HYP_005: NOT CREATED]
[BACKTEST: NOT STARTED]
[STRATEGY P&L: NOT COMPUTED]
[NEW MARKET DATA AUTHORIZED: QUALIFICATION PROBE ONLY (6 historical sessions)]
[OOS BOUNDARY: >= 2024-05-01 STRICTLY NOT ACCESSED]
[2025-2026: NOT ACCESSED]
[CAPITAL: $0.00 | NO_REAL_ORDERS: true]
```

---

## 1. Provider Contract Overview

This document records the formally resolved and still-open provider data qualifications
for **MEC-0015** prior to registering `HYP_005`. The authoritative data source is
**Alpaca Markets Historical SIP** for US equities.

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

## 3. Bar Timestamp Semantics (RESOLVED)

### 3.1. Alpaca Bar Timestamp = LEFT EDGE of Interval

Per Alpaca Market Data FAQ:
> "A minute bar's timestamp represents the start of the 1-minute interval."

Formally:
$$\text{bar timestamp} = \text{LEFT EDGE of } [\text{timestamp}, \text{timestamp} + 1\text{min})$$

| Bar Timestamp (ET) | Interval Represented | Trades Captured |
| :--- | :--- | :--- |
| `09:30:00` | `[09:30:00, 09:31:00)` | First RTH minute |
| `09:59:00` | `[09:59:00, 10:00:00)` | Minute preceding 10:00 decision |
| `10:00:00` | `[10:00:00, 10:01:00)` | First exposure minute (post-10:00 decision) |
| `15:59:00` | `[15:59:00, 16:00:00)` | Last RTH bar (bar `BAR_1559`) |

**`BAR_TIMESTAMP_SEMANTICS = LEFT_EDGE_OF_ONE_MINUTE_INTERVAL`**

> [!IMPORTANT]
> Missing 1-minute bars: If no qualifying trades populate a given minute, Alpaca may omit the bar
> entirely. There is no synthesized OHLCV row for empty minutes. This motivates the
> **MISSING_REQUIRED_MINUTE_POLICY = FAIL_CLOSED_SESSION_EXCLUSION** (see Section 6).

### 3.2. Author Decision-Time to Alpaca Bar Timestamp Mapping (RESOLVED)

Author reference code evaluates decisions at **right-edge** conceptual timestamps (the end of
each 30-minute epoch). Alpaca labels bars by **left-edge**.

**Resolution:**

| Author Decision Epoch (Right-Edge Concept) | Signal Bar's Alpaca Timestamp (Left-Edge) | Next Exposure Bar Alpaca Timestamp |
| :--- | :--- | :--- |
| 10:00 ET (close of bar [09:59, 10:00)) | `09:59:00 ET` | `10:00:00 ET` |
| 10:30 ET (close of bar [10:29, 10:30)) | `10:29:00 ET` | `10:30:00 ET` |
| 11:00 ET (close of bar [10:59, 11:00)) | `10:59:00 ET` | `11:00:00 ET` |
| … | … | … |
| 15:30 ET (close of bar [15:29, 15:30)) | `15:29:00 ET` | `15:30:00 ET` |

**`AUTHOR_DECISION_TIME_TO_ALPACA_BAR_TIMESTAMP =`**
`AUTHOR_DECISION_AT_HH:MM_RIGHT_EDGE_EQUALS_ALPACA_TIMESTAMP_(HH:MM - 1min)`

---

## 4. Regular Trading Hours (RTH) Scope (RESOLVED)

| Boundary | Time (ET) | Notes |
| :--- | :--- | :--- |
| **RTH Open** | `09:30:00` | First bar: `BAR_0930` [09:30, 09:31) |
| **RTH Close** | `16:00:00` | Last eligible bar: `BAR_1559` [15:59, 16:00) |
| **Bar Count (Standard Session)** | 390 | `(16:00 - 09:30) = 390 minutes` |
| **Timezone Authority** | `America/New_York` | `ZoneInfo("America/New_York")` DST-aware |
| **Query End Parameter** | `15:59:59 ET` | Alpaca `end` is inclusive on bar start timestamp |

**`CALENDAR_AUTHORITY = NyseCa1Calendar (CA-1 Sovereign, 2013–2026)`**

---

## 5. Provider VWAP Rejection (RESOLVED)

Alpaca's `/v2/stocks/SPY/bars` response includes a `vw` (provider VWAP) field. This field
represents Alpaca's internal computation of VWAP and its exact numerator convention is
not contractually guaranteed to match the MEC-0015 required Typical Price $(H+L+C)/3$.

**ACASH Policy:**
- `PROVIDER_VWAP_FIELD_STATUS = AVAILABLE_BUT_REJECTED_FOR_MEC_0015_SIGNAL_VWAP`
- Provider-supplied VWAP is captured for provenance only.
- MEC-0015 requires VWAP computed independently from raw OHLCV using Typical Price $(H+L+C)/3$.
- `VWAP_NUMERATOR = RESOLVED_TYPICAL_PRICE_HLC3` (see strategy contract audit).

---

## 6. Missing-Bar Policy (RESOLVED)

**`MISSING_REQUIRED_MINUTE_POLICY = FAIL_CLOSED_SESSION_EXCLUSION`**

Rationale:
- Alpaca bars are trade aggregates; a minute with no qualifying trades produces no bar.
- Silent forward-fill of OHLC would fabricate execution state not grounded in actual market activity.
- A session with a missing required minute becomes `DATA_CONTRACT_EXCLUDED`.

Required minutes (any absence triggers session exclusion):
1. Session open bar (`09:30:00 ET`) — needed for `Open[t, 09:30]` sizing and gap anchor.
2. All bars in the cumulative VWAP path — needed for trailing VWAP stop evaluation.
3. All bars at decision epoch minutes (09:59, 10:29, …, 15:29 ET Alpaca labels) — needed for signal.
4. Next-period exposure bar (10:00, 10:30, …, 15:30 ET) — needed for P&L computation.
5. Last RTH bar (`15:59:00 ET`) — needed for EOD flat handling.

**Implementation:**
- `_qualify_session_bars()` counts missing bars vs expected session schedule.
- Any missing bar count > 0 → `status = FAIL_MISSING_BARS`.
- `ZERO_SILENT_IMPUTATION = ENFORCED`.

---

## 7. Dividend Data Contract (OPEN_BLOCKER)

MEC-0015 author reference code requires current-day cash dividend for the gap anchor:
$$\text{prev\_close\_adjusted} = \text{Close}[t-1, 16:00] - \text{dividend}[t]$$

### 7.1. Alpaca Corporate Actions Assessment
- Alpaca provides `/v2/corporate-actions` endpoint with cash dividends.
- However, the exact provenance, point-in-time corrections, and revision policy must be
  explicitly audited before they can be used as the authoritative dividend source.

**`DIVIDEND_PROVIDER_MAPPING = OPEN_BLOCKER`**

Requirements for resolution:
- Confirmed ex-date semantics (ex-date vs pay-date).
- Cash amount per share with correct decimal precision.
- Symbol mapping (SPY ticker).
- Point-in-time integrity (no look-ahead dividend revisions).
- Fallback if a historical dividend is unavailable.
- Do NOT derive dividend from adjusted-vs-raw price ratio; rounding errors corrupt the anchor.

---

## 8. Execution Fill Price Model (OPEN)

Literature reference backtest uses 1-minute exposure lag (`signal.shift(1)`), which is not
by itself an executable fill specification.

**`REFERENCE_BACKTEST_EXPOSURE_LAG = RESOLVED_1_MINUTE`**

For the executable ACASH backtest fill model:

- **Preferred baseline (if NBBO feasible):**
  `PRIMARY_EXECUTION_MODEL_CANDIDATE = NBBO_MARKETABLE_FILL`
  - Long entry / buy: fill at Ask.
  - Long exit / sell: fill at Bid.
  - Short entry / sell: fill at Bid.
  - Short cover / buy: fill at Ask.
  - No separate half-spread deduction (spread is embedded in bid/ask separation).
  - NBBO reconstruction requires Alpaca `/v2/stocks/SPY/quotes` historical feed.
- **Fallback (if NBBO impractical):**
  `PRIMARY_EXECUTION_MODEL_CANDIDATE = NEXT_MINUTE_OPEN_PLUS_FRICTION`
  - Fill at bar Open of the minute immediately following the signal bar.
  - A separate spread/slippage penalty MUST be added (these models are mutually exclusive).

**`ACASH_EXECUTION_FILL_PRICE_MODEL = OPEN`** (requires separate qualification probe before HYP_005).

---

## 9. Spread Model (OPEN_BLOCKER)

**`ACASH_SPREAD_MODEL = OPEN_BLOCKER`**

- `FIXED_MINIMUM_HALF_SPREAD = NOT_A_VALID_UNIVERSAL_COST_MODEL`.
- Full Spread = $\$0.01$/share (one-tick in standard US equity market), Half-Spread = $\$0.005$/share.
- SEC Rule 612 amendments ($0.005 tick) compliance delayed to **November 2026**; historical data
  must use the $0.01 minimum tick.
- Preferred: contemporaneous historical NBBO spread from Alpaca quote history.
- Alternative: an explicitly audited conservative frozen proxy must be separately ratified.

---

## 10. Probe Authorization & OOS Guard

### 10.1. Authorized Probe Dates

| Session Date | Exposure Type | Status |
| :--- | :--- | :--- |
| `2018-06-01` | Publication-exposed historical | Authorized |
| `2019-06-03` | Publication-exposed historical | Authorized |
| `2020-06-01` | Publication-exposed historical | Authorized |
| `2021-06-01` | Publication-exposed historical | Authorized |
| `2022-06-01` | Publication-exposed historical | Authorized |
| `2024-03-01` | Publication-exposed historical | Authorized |

All dates are deliberately within the Zarattini et al. (2024) study period or its
documented replication range.

### 10.2. OOS Boundary (Fail-Closed)

```
OOS_FORBIDDEN_DATE = 2024-05-01
```

- No market data access is permitted on or after `2024-05-01`.
- No 2025 or 2026 data access is permitted.
- Guard is enforced in `_validate_probe_date_not_oos()` before any network call.
- `DataContractError` raised immediately on violation.

---

## 11. Open Provider Contracts Summary

| Contract Item | Status | Priority |
| :--- | :--- | :--- |
| Bar endpoint (`/v2/stocks/SPY/bars`, SIP, 1Min, raw) | `RESOLVED` | — |
| Bar timestamp left-edge semantics | `RESOLVED` | — |
| Author decision-time to Alpaca bar timestamp mapping | `RESOLVED` | — |
| RTH scope (09:30–15:59 ET, 390 bars standard) | `RESOLVED` | — |
| Missing-bar policy (FAIL_CLOSED_SESSION_EXCLUSION) | `RESOLVED` | — |
| Provider VWAP rejection | `RESOLVED` | — |
| Dividend data provider | `OPEN_BLOCKER` | Required before HYP_005 |
| Execution fill price model | `OPEN` | Required before HYP_005 |
| Spread model | `OPEN_BLOCKER` | Required before HYP_005 |
| Full provider probe (live network validation) | `PENDING_HUMAN_RATIFICATION` | Required before HYP_005 |
