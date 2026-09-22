# MEC-0017 HYP_007 Step R2 Session Completeness Report

[GOVERNANCE ARTIFACT: TRACKED SCIENTIFIC DATASET QUALIFICATION REPORT]
[HYPOTHESIS_ID: HYP_007]
[MECHANISM_ID: MEC-0017]
[AUTHORIZATION: AUTHORIZE_HYP_007_R2_DATASET_CONSTRUCTION]
[STATUS: QUALIFIED_SEALED]
[VERDICT: PASS]

## 1. Census & Calendar Coverage

- **Calendar Authority:** `NyseCa1Calendar (CA-1)`
- **Warm-Up Earliest Date:** `2021-06-09`
- **Warm-Up End Date:** `2021-06-30`
- **Warm-Up Expected Sessions:** `16`
- **Warm-Up Observed Sessions:** `16` (100% complete)
- **M1 Start Date:** `2021-07-01`
- **M1 End Date:** `2024-04-30`
- **M1 Expected Standard Sessions:** `708`
- **M1 Observed Standard Sessions:** `708` (100% complete)
- **M1 Excluded Early Closes:** `4` sessions:
  - `2021-11-26`: `EARLY_CLOSE` (EXCLUDE_NON_STANDARD_REGULAR_SESSIONS)
  - `2022-11-25`: `EARLY_CLOSE` (EXCLUDE_NON_STANDARD_REGULAR_SESSIONS)
  - `2023-07-03`: `EARLY_CLOSE` (EXCLUDE_NON_STANDARD_REGULAR_SESSIONS)
  - `2023-11-24`: `EARLY_CLOSE` (EXCLUDE_NON_STANDARD_REGULAR_SESSIONS)
- **M1 Sessions By Year:**
  - **2021:** 127 eligible regular sessions
  - **2022:** 250 eligible regular sessions
  - **2023:** 248 eligible regular sessions
  - **2024:** 83 eligible regular sessions

## 2. 1-Minute SIP Bar Contract Qualification

- **Primary Bar Provider:** `ALPACA_HISTORICAL_SIP` (`/v2/stocks/SPY/bars`, `feed=sip`, `timeframe=1Min`, `adjustment=raw`)
- **Total Primary Bar Records:** `281,970` qualified strategy bars
- **Warm-Up Bars Count:** `6,240` bars (`16 sessions × 390 bars`)
- **M1 Bars Count:** `275,730` bars (`707 complete sessions × 390 bars`)
- **Complete 390-Bar Sessions:** `723 / 724` (99.86%)
- **Incomplete Sessions:** `1`
- **Missing Bar Dates:** `2023-06-05`
- **Excluded Sessions from Trading:** `2023-06-05`
- **Proportion of M1 Affected:** `0.141%`
- **Missing Bar Details:**
  - Session `2023-06-05`: 4 missing bars (09:52, 09:53, 09:54, 09:55 ET) — FAIL_CLOSED_SESSION_EXCLUSION under frozen missing-bar contract
- **Duplicate Bar Count:** `0`
- **Extended Hours Bars Admitted:** `0` (strictly rejected)
- **Structural Integrity:** 100% monotonic timestamps, O/H/L/C > 0, H >= max(O,C,L), L <= min(O,C,H), V >= 0.
- **Provider VW Field Authority:** `REJECTED` (signal authority strictly prohibited; raw HLC3 independently calculated).

## 3. Daily Close & Volatility Input Lineage

- **Daily Close Input Authority:** Completed RTH session `15:59` bar Close price.
- **Total Lineage Sessions:** `724` sessions.
- **Warm-Up Closes Available for First M1 Day (`2021-07-01`):** `16 prior completed closes`.
- **Close-to-Close Returns Available for Day 1:** `15 daily returns`.
- **Noise Area Lookback State for Day 1:** `14 completed sessions`.
- **Lineage Integrity Status:** `COMPLETE_UNINTERRUPTED_LINEAGE`.

## 4. SSGA Dividend Authority Reconciliation

- **Primary Authority:** `STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS`
- **Upstream Reference:** `docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json` (SHA: `0f99ab26884e8767d2bade35039770a342e66c0628dbd2b8ff1e03075cc871bc`)
- **M1 Relevant Distributions:** `11` distributions
- **Rate Equality Against Alpaca Snapshot:** `11 / 11 PASS` (100% rate equality)
- **Reconciliation Status:** `ESTABLISHED_PINNED`

## 5. M1 Execution Quote Evidence Qualification

- **Primary Quote Provider:** `ALPACA_HISTORICAL_SIP` (`/v2/stocks/quotes`, `feed=sip`, `sort=asc`)
- **Quote Boundaries Per Session:** `13`
- **Total Expected Quote Boundaries:** `9,204` (`708 sessions × 13 boundaries`)
- **Total Qualified Quote Boundaries:** `9,204` (100%)
- **Quote Boundary Failures:** `0`
- **Executable Condition 'R' Count:** `9,204` (`100.0%`)
- **Unresolved Condition '?' Count:** `0` (strictly zero in direct-SIP era)
- **Unknown Conditions Count:** `0`
- **Locked Quotes Admitted (`bid == ask`):** `62`
- **Crossed Quotes (`bid > ask`):** `0` (strictly rejected)
- **Quote Delay Distribution (from boundary ET to selected first-valid timestamp):**
  - **Min:** `0.002 ms`
  - **Median:** `4.719 ms`
  - **Mean:** `14.613 ms`
  - **P95:** `14.949 ms`
  - **Max:** `79941.843 ms`

## 6. Provider Telemetry & Governance

- **Provider HTTP 401 Count:** `0`
- **Provider HTTP 403 Count:** `0`
- **Provider HTTP 429 Count:** `0`
- **Provider Retries Count:** `0`
- **M2 Access Probes:** `0` (hard firewalled before network)
- **Secondary HF Data Library Cross-Check:** `SECONDARY_CROSSCHECK_NOT_EXECUTED` (operational independence preserved)
- **Raw Market Data Committed to Git:** `NO` (strictly local in `.gitignored /data/`)
