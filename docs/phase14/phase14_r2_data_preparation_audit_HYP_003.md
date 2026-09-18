# Phase 14 Step R2 Data Preparation & Qualification Audit: HYP_003

```text
[HUMAN-RATIFIED LINEAGE]
[STEP R2 COMPLETE]
[IN-SAMPLE ONLY: 2017-01-01 TO 2022-12-31]
[OUT-OF-SAMPLE SEALED: 2023-01-01 TO 2026-12-31]
[FEED: CONSOLIDATED SIP (RAW)]
[CALENDAR AUTHORITY: NYSE CA-1]
[STEP R3 LOCKED]
[ZERO BACKTEST CALCULATIONS]
```

- **Document ID:** `docs/phase14/phase14_r2_data_preparation_audit_HYP_003.md`
- **Target Hypothesis:** `HYP_003` (Opening Range Breakout on `SPY` under MEC-0013 Price-Only Mechanics)
- **Mechanism ID:** `MEC-0013`
- **Upstream Governance Basis:**
  - `docs/phase14/mec_0013_price_only_preregistration.md` (SHA-256: `3c04f617b9877a85a07043e67b7554034ebd703fe823d3d2de777a7722a3150c`)
  - `docs/phase14/hypotheses/HYP_003.json` (SHA-256: `f59010d14f466e9681325a314fd3e7ef30af43ffd69bc6cecbad1b5e6aab4ee0`)
  - `docs/phase14/manifests/manifest_r1_HYP_003.json` (SHA-256: `27952f476cf96f75dc47ca0eb68a4b74d1f8dc6bf2f0848d1a877740cc32b372`)
  - `docs/phase14/phase14_r1_semantic_conformance_record_HYP_003.md` (Commit: `9b12040e2d4654da32f737be5b4ba84123b23e58`)
- **Step R2 Durable Manifest:** `docs/phase14/manifests/manifest_r2_HYP_003.json`
- **Session Ledger:** `data/manifests/research/HYP_003_session_ledger.json`
- **Canonical Parquet:** `data/parquet/research/HYP_003_SPY_1Min_IS_canonical.parquet`
- **Canonical Dataset SHA-256:** `2a70922156f3d724fffbf7030d791d0da3b0fa1c44f839eea794c2fb2d689ddc`
- **Raw Evidence Aggregate SHA-256:** `a3d03ea208d65de68d07d377b4b2321173036fd8112ad245353f097992fbe093`
- **Execution Date:** `2026-09-18 23:16:03 UTC`

---

## 1. Executive Summary

Under the explicit Human authorization for Step R2 execution, the quantitative historical dataset for hypothesis `HYP_003` has been ingested, validated, and sealed strictly within the In-Sample temporal window (`2017-01-01` to `2022-12-31`).

- **Total Calendar Days in Window:** 2191
- **Weekend Days Excluded:** 626
- **Official Exchange Holidays Excluded:** 55
- **Official Early-Close Sessions Excluded:** 12
- **Regular Sessions Expected (390-min):** 1498
- **Regular Sessions Qualified:** 1492
- **Total Incomplete Sessions:** 6
- **Total Canonical 1-Minute Bars:** 581,880
- **First Bar Timestamp (UTC):** `2017-01-03T14:30:00+00:00`
- **Last Bar Timestamp (UTC):** `2022-12-30T20:59:00+00:00`

Zero strategy signals, zero breakout calculations, zero trades, and zero PnL/Sharpe calculations were performed during this step. Out-of-Sample data (`2023-01-01` through `2026-12-31`) remains strictly unread, unopened, and sealed.

---

## 2. Calendar Authority & Session Census (CA-1)

Sovereign calendar authority `NyseCa1Calendar` was used to classify all 2191 days in the In-Sample period:

| Category | Count | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Regular Sessions (390m)** | 1498 | Qualified (1492 passed) | Monotonic 1m bars from 09:30 to 15:59 ET |
| **Early Close Sessions (210m)** | 12 | Excluded | Day after Thanksgiving, Christmas Eve, etc. |
| **Official Holidays** | 55 | Excluded | Full market closures |
| **Weekend Days** | 626 | Excluded | Saturdays and Sundays |
| **Total Calendar Days** | 2191 | 100% Accounted | Complete partition coverage |

---

## 3. Data Ingestion & Validation Integrity

- **Provider:** Alpaca Markets Historical Data API v2 (`/v2/stocks/SPY/bars`)
- **Feed:** Consolidated Tape (`feed=sip`)
- **Price Adjustment:** Raw unadjusted (`adjustment=raw`)
- **Bar Invariant:** Exactly 390 bars per regular session. Every bar validated for:
  1. Time alignment strictly within regular trading hours (`09:30:00` to `15:59:00` America/New_York)
  2. Timestamp strict monotonicity (strictly increasing, zero duplicates)
  3. Price positivity (`open > 0`, `high > 0`, `low > 0`, `close > 0`)
  4. OHLC geometric consistency (`high >= low`, `high >= open`, `high >= close`, `low <= open`, `low <= close`)
  5. Non-negative volume (`volume >= 0`)
- **Arrow Canonical Schema:** `CANONICAL_ARROW_SCHEMA` (`timestamp[us, tz=UTC]`, `decimal128(38,18)`, `int64`)

---

## 4. Cryptographic Lineage & Sealing

- **Canonical Parquet SHA-256:** `2a70922156f3d724fffbf7030d791d0da3b0fa1c44f839eea794c2fb2d689ddc`
- **Raw Evidence Aggregate SHA-256:** `a3d03ea208d65de68d07d377b4b2321173036fd8112ad245353f097992fbe093`
- **Manifest Location:** `docs/phase14/manifests/manifest_r2_HYP_003.json`
- **Session Ledger Location:** `data/manifests/research/HYP_003_session_ledger.json`

---

## 5. Boundary Preservation & Governance Invariants

```markdown
### Verification Ledger
- Implementation Status: COMPLETE
- Contract Enforcement: STRICT FAIL-CLOSED
- Mathematical Authority: NyseCa1Calendar (CA-1) & SEC SIP Consolidated Tape
- Temporal Scope: 2017-01-01 to 2022-12-31 (In-Sample ONLY)
- Out-of-Sample Window: 2023-01-01 to 2026-12-31 (SEALED / UNREAD / FORBIDDEN)
- Step R3 Status: LOCKED (NOT INVOKED)
- Backtest Calculations: NONE (ZERO SIGNALS / ZERO TRADES)
- Capital Authority: $0.00
- Execution Policy: NO_REAL_ORDERS=true
```
