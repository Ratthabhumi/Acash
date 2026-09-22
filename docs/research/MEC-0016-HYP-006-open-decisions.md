# MEC-0016 / HYP_006: Pre-Inception Decisions Ledger

```text
[GOVERNANCE DECISION ARTIFACT: PRE-INCEPTION DECISIONS LEDGER]
[MECHANISM_ID: MEC-0016]
[CANDIDATE_HYPOTHESIS_ID: HYP_006]
[SUBJECT: PRE-INCEPTION ARCHITECTURAL, METHODOLOGICAL, AND PROVIDER DECISIONS]
[CURRENT_STATUS: PREINCEPTION_ACTIVE]
[EXACT_OPEN_BLOCKERS: 2]
[FEASIBILITY_VERDICT: FREE_DATA_FEASIBILITY_CONDITIONAL]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/research/MEC-0016-HYP-006-open-decisions.md`
- **Governing Standard:** ACASH `AGENTS.md` (Single Canonical Authority, Strict Fail-Closed Contract, Statistical Dependence Awareness).

---

## 1. Decision Records Summary Table

| Decision ID | Topic | Status | Selected Option | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **MEC-0016-D01** | Replication Sample Window | `PROPOSED` | **Option A** (`2016-01-01` to `2024-04-30`) | Aligns with Alpaca inception date and preserves publication terminal date |
| **MEC-0016-D02** | Primary Market Data Provider | `PROPOSED` | **Option A** (`ALPACA_HISTORICAL_SIP`) | Zero-cost broker candidate with SIP bars & historical quotes |
| **MEC-0016-D03** | Secondary Bar Cross-Check | `PROPOSED` | **Option A** (`HF_DATA_LIBRARY`) | Independent 1m OHLCV bar comparison without quote splicing |
| **MEC-0016-D04** | Dividend Authority | `RESOLVED` | **Option A** (`STATE_STREET_SSGA_OFFICIAL`) | Sovereign sponsor distribution notices covering all 33 post-2016 events |
| **MEC-0016-D05** | Minimum Trade Count Gate | `PROPOSED` | **Option A** (Preserve $N \ge 100$) | Prevents opportunistic post-hoc relaxation for shorter sample |
| **MEC-0016-D06** | Alpaca 2016–2018 Quote Depth | `OPEN_BLOCKER` | Awaiting empirical probe | Quotes probed only $\ge 2019$; pre-2019 depth unverified |
| **MEC-0016-D07** | Zero-Cost SIP Rate & Entitlement | `OPEN_BLOCKER` | Awaiting credential audit | Confirm whether ~25k quote queries trigger 403 or throttling |

---

## 2. Detailed Decision Records

### MEC-0016-D01: Replication Sample Window Selection
- **Context:** `HYP_005` M1 was frozen at `2007-05-01` to `2024-04-30`. Under zero-cost data constraints, pre-2016 data is unavailable via free institutional sources.
- **Options:**
  - *Option A (Recommended):* `2016-01-01` through `2024-04-30` (~8.3 years).
  - *Option B:* Truncate further to `2020-01-01` through `2024-04-30`.
- **Verdict:** **Option A**. Preserves maximum available free data history while maintaining the strict publication-exposed terminal boundary.

---

### MEC-0016-D02: Primary Market Data Provider Selection
- **Context:** Selection of primary market-data candidate for SPY 1-minute bars and execution quotes.
- **Options:**
  - *Option A (Recommended):* Alpaca Historical SIP.
  - *Option B:* Yahoo Finance / YFinance (Reject: Non-SIP, no tick quotes, no nanosecond execution fills).
  - *Option C:* Alpha Vantage (Reject: Extreme rate throttling, incomplete NBBO quotes).
- **Verdict:** **Option A**. Alpaca remains the sole candidate capable of providing consolidated SIP bars and execution quotes at zero additional cost.

---

### MEC-0016-D03: Secondary Bar Cross-Check Provider
- **Context:** Independent sanity checking for OHLCV bars.
- **Options:**
  - *Option A (Recommended):* HF Data Library (`hfdatalibrary.com` / Hugging Face).
  - *Option B:* Splicing HF Data Library into execution quotes (Reject: Violates execution model).
- **Verdict:** **Option A**. HF Data Library is ratified strictly for bar-level cross-validation.

---

### MEC-0016-D04: Corporate Action & Dividend Authority
- **Context:** Daily gap calculation requires cash dividends.
- **Options:**
  - *Option A (Recommended):* State Street Global Advisors (SSGA) Official Historical Distributions.
  - *Option B:* Broker corporate action feeds.
- **Verdict:** **Option A (RESOLVED)**. Sovereign fund sponsor notices govern. All 33 post-2016 quarterly distributions cataloged.

---

### MEC-0016-D05: Minimum Completed Trade Count Gate
- **Context:** Acceptance gate G4 in `HYP_005` required completed trades $N \ge 100$.
- **Options:**
  - *Option A (Recommended):* Preserve $N \ge 100$ unchanged.
  - *Option B:* Lower to $N \ge 50$ due to shorter sample.
- **Verdict:** **Option A**. In a 8.3-year intraday strategy sample, 100 completed trades ($\approx 12$ trades/year) is a minimal statistical requirement to reject small-sample luck. Lowering it would constitute unprincipled post-hoc relaxation.

---

### MEC-0016-D06: Alpaca Historical SIP Quote Depth for 2016–2018 (OPEN BLOCKER)
- **Problem Statement:** In prior research audits (`MEC-0015-quote-provider-contract-manifest.json`), Alpaca SIP quotes were probed only on `2019-06-03`, `2022-06-01`, and `2024-03-01`. Quote availability for `2016-01-01` through `2018-12-31` has not been empirically verified.
- **Required Pre-Inception Action:** Conduct a deliberate, narrow historical probe on early dates (e.g. `2016-06-17`, `2017-06-01`, `2018-06-01`) before formal Step R1 inception.

---

### MEC-0016-D07: Zero-Cost SIP Rate Limits & Entitlement Gating (OPEN BLOCKER)
- **Problem Statement:** Alpaca official documentation designates SIP market data as an "Unlimited" ($9/mo) or Broker API feature, while Basic accounts receive IEX data. If the current environment credential is a Basic/Free key, full-dataset execution may trigger HTTP 403 or rate throttling when executing ~25,000 quote queries.
- **Required Pre-Inception Action:** Audit account entitlement behavior under current environment keys before initiating dataset construction.
