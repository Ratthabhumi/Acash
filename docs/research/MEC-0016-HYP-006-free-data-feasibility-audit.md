# MEC-0016 / HYP_006: Free-Data Provider Feasibility Audit

```text
[RESEARCH GOVERNANCE ARTIFACT: PROVIDER FEASIBILITY AUDIT]
[MECHANISM_ID: MEC-0016]
[CANDIDATE_HYPOTHESIS_ID: HYP_006]
[SUBJECT: POST-2016 FREE-DATA REPLICATION FEASIBILITY FOR SPY INTRADAY MOMENTUM]
[PRIMARY_DATA_PROVIDER_CANDIDATE: ALPACA_HISTORICAL_SIP]
[SECONDARY_BAR_CROSS_CHECK_CANDIDATE: HF_DATA_LIBRARY]
[PRIMARY_DIVIDEND_AUTHORITY: STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS]
[PROPOSED_M1_WINDOW: 2016-01-01 THROUGH 2024-04-30]
[OPERATIONAL_BUDGET: $0.00 (ZERO_COST_CONSTRAINT)]
[FEASIBILITY_VERDICT: FREE_DATA_FEASIBILITY_CONDITIONAL]
[HYP_006_STATUS: PREINCEPTION_READY_FOR_HUMAN_REVIEW (R1 NOT CREATED)]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/research/MEC-0016-HYP-006-free-data-feasibility-audit.md`
- **Governing Standard:** ACASH `AGENTS.md` (Implementation Correctness $\neq$ Contract Correctness, Zero Unverified Claims, Strict Fail-Closed).
- **Target Asset:** SPDR S&P 500 ETF Trust (`SPY`, CUSIP: `78462F103`).

---

## 1. Context & Operational Motivation

Hypothesis `HYP_005` investigated the full academic publication window (`2007-05-01` through `2024-04-30`), which requires 17 years of minute bars and nanosecond execution quotes. Under the operator's operational budget constraint ($\text{RESEARCH\_DATA\_BUDGET} = \$0.00$), `HYP_005` is formally classified as `BLOCKED_NON_FALSIFIED_BY_PRIMARY_DATA_ENTITLEMENT` because complete historical access prior to 2016 requires commercial subscriptions (~$199/month for Massive Stocks Advanced).

To enable rigorous quantitative research under zero-cost constraints without compromising scientific execution models, `HYP_006` is proposed as a distinct, independent hypothesis evaluating the identical economic strategy mechanism over the **post-2016 sample** (`2016-01-01` through `2024-04-30`).

This audit evaluates the empirical feasibility and integrity of candidate zero-cost data sources before any formal inception or registration of `HYP_006`.

---

## 2. Primary Market-Data Candidate: Alpaca Markets Historical SIP

### 2.1 Historical Coverage & Endpoint Inventory
- **Established Historical Coverage:** US equities data begins on **`2016-01-01`**.
- **1-Minute Bars (`/v2/stocks/SPY/bars`):**
  - Parameter: `feed=sip`, `timeframe=1Min`, `adjustment=raw`.
  - Prior qualification (`MEC-0015-bar-provider-contract-manifest.json`) empirically established that 1-minute SIP bars have:
    - 100% RTH session completeness ($390 / 390$ bars on qualified dates);
    - Strictly monotonic timestamps;
    - Left-edge labeling convention: bar at `09:59:00 ET` represents completed minute `[09:59:00, 10:00:00)`.
  - **Bar Feasibility Status:** `CREDIBLE_PASS`.

### 2.2 Historical Quotes & Execution Contract (`/v2/stocks/quotes`)
- **Execution Contract Requirement:** `FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY`
  - Requires retrieving top-of-book SIP quotes around discrete decision boundaries (`10:00, 10:30, ..., 15:30 ET`).
- **Prior Qualification Evidence:**
  - `MEC-0015-quote-provider-contract-manifest.json` demonstrated that narrow quote queries around `10:00, 12:00, 15:30 ET` were valid and retrieved consolidated SIP NBBO quotes with sub-15ms latency on `2019-06-03`, `2022-06-01`, and `2024-03-01`.
- **Open Blocker 1 — Unprobed 2016–2018 Depth:**
  - The repository's canonical evidence tested dates from 2019 forward. Historical SIP quote retrieval for the earliest M1 segment (`2016-01-01` through `2018-12-31`) has **not been empirically probed** in ACASH.
- **Open Blocker 2 — Entitlement Tier & Throttling Limits:**
  - Alpaca official documentation states that SIP data access typically requires an active brokerage account or an "Unlimited Market Data" plan ($9/mo), whereas basic free tier accounts default to IEX data.
  - Furthermore, querying quotes across 2,096 trading days at 12 decision epochs per day requires $\approx 25,152$ API requests. At Alpaca's standard free limit (200 requests/minute), retrieval requires over 2 hours of rate-limited pagination.
  - Whether a strictly zero-cost Alpaca credential can execute full 2016–2024 quote downloads without HTTP 403 or server throttling remains **unverified**.
- **Quote Feasibility Status:** `CONDITIONAL_PENDING_EMPIRICAL_PROBE`.

---

## 3. Secondary Bar Candidate: HF Data Library

### 3.1 Overview & Identification
- **Project Identity:** HF Data Library (`hfdatalibrary.com` / Hugging Face `elkassabgi/hfdatalibrary`).
- **Target Asset Coverage:** SPY 1-minute OHLCV bars available from 2002 to present.
- **Data Format:** Downloadable Parquet / CSV files and REST API.
- **License / Terms:** Permitted for academic, non-commercial research.

### 3.2 Methodological Evaluation
| Dimension | HF Data Library Reality | ACASH Execution Requirement |
| :--- | :--- | :--- |
| **Data Type** | 1-Minute OHLCV aggregate bars | Bar inputs + Tick-level top-of-book quotes |
| **Historical NBBO** | **ABSENT** (No bid/ask quote stream) | **MANDATORY** for realistic fill modeling |
| **Adjustment Semantics** | Mixed / Provider-dependent | Raw unadjusted prices required |
| **Source Lineage** | Aggregated from third-party vendor flat files | Single authoritative consolidated exchange tape |
| **Fill Simulation** | Only coarse bar approximations (e.g. Next-Bar Open) | `FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY` |

### 3.3 Authorized Role
```text
HF_DATA_LIBRARY_ROLE = SECONDARY_INDEPENDENT_BAR_CROSS_CHECK_ONLY
```
- **Prohibited Uses:**
  - MUST NOT be used for trade execution fills.
  - MUST NOT be used to fabricate synthetic bid/ask quotes.
  - MUST NOT be spliced into primary execution feeds.
- **Permitted Uses:**
  - Independent OHLCV bar reconciliation against Alpaca.
  - Detecting missing minutes, abnormal trading session halts, or volume anomalies.
  - Cross-validating volatility sizing inputs.

---

## 4. Corporate Action & Dividend Authority

- **Sovereign Authority:** `STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS`.
- **Coverage for Proposed M1 (`2016-01-01` to `2024-04-30`):** Exactly **33 quarterly cash distributions**.
- **Reconciliation:**
  - 31 distributions cross-reconciled with exact rate equality against Alpaca corporate actions snapshot.
  - 2 post-2016 events (`2016-03-18`, `2018-06-15`) authoritative from official SSGA fund notices.
- **Status:** `FULLY_ESTABLISHED_AT_ZERO_COST`.

---

## 5. Feasibility Evaluation & Verdict

```text
FEASIBILITY_VERDICT: FREE_DATA_FEASIBILITY_CONDITIONAL
```

### 5.1 Criteria Assessment
1. **Alpaca 1-min Bar Coverage (2016–2024):** `PASS` (Documented and partially probed).
2. **SSGA Sovereign Dividend Coverage (2016–2024):** `PASS` (33 distributions verified).
3. **HF Data Library Bar Cross-Validation:** `PASS` (Independent 1m bars available).
4. **Alpaca Quote Availability for 2016–2018:** `OPEN_BLOCKER` (Unprobed in canonical repository).
5. **Zero-Cost Entitlement Confirmation:** `OPEN_BLOCKER` (Need to verify current API credentials sustain SIP quote queries across proposed M1).

### 5.2 Mandatory Pre-Inception Resolution Order
Before `HYP_006` can be authorized for Step R1 Inception:
1. Conduct a narrow, non-strategy historical quote probe on Alpaca for early M1 dates (e.g. `2016-06-17`, `2017-06-01`, `2018-06-01`).
2. Confirm whether current account credentials permit historical SIP quote pagination without 403 authorization failures.
3. If confirmed, promote feasibility to `PASS`. If blocked, report failure and preserve zero capital.
