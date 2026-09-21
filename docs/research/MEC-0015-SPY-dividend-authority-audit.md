# MEC-0015: SPY Official Dividend Authority Audit (SSGA Sovereign Distributions)

```text
[GOVERNANCE AUDIT ARTIFACT: SPY DIVIDEND AUTHORITY AUDIT]
[GENERATED: 2026-09-21]
[CANONICAL STARTING HEAD: 886db67bf88241929a2a32557e3c0ef9bffcc693]
[PRIMARY_DIVIDEND_AUTHORITY: STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS]
[M1_WINDOW: 2007-05-01 THROUGH 2024-04-30]
[SPY_DISTRIBUTIONS_COUNT_IN_M1: 68]
[PRE_2016_DISTRIBUTION_COUNT: 35]
[POST_2016_DISTRIBUTION_COUNT: 33]
[ALPACA_PRESENT_RATE_RECONCILIATION: 31/31 PASS]
[ALPACA_UNVERIFIED_COUNT: 37 (35 PRE-2016 + 2 POST-2016: 2016-03-18, 2018-06-15)]
[PRECEDING_FIRST_VERIFIED_ALPACA_EVENT: 36 (PRIOR TO 2016-06-17)]
[FULL_POST_2016_ALPACA_COVERAGE: NOT_ESTABLISHED]
[SSGA_FULL_M1_DIVIDEND_AUTHORITY: ESTABLISHED]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/research/MEC-0015-SPY-dividend-authority-audit.md`
- **Subject:** Formal audit and establishment of sovereign historical cash distribution authority for `SPY` across the full `HYP_005` M1 replication window (`2007-05-01` through `2024-04-30`).
- **Governing Standard:** ACASH `AGENTS.md` (Zero Unverified Claims, Single Canonical Authority, Strict Fail-Closed).
- **Machine-Readable Manifest:** `docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json`.
- **Target Asset:** SPDR S&P 500 ETF Trust (`SPY`, CUSIP: `78462F103`).

---

## 1. Context & Authority Hierarchy

In `HYP_005` (Noise-Area Intraday Momentum Strategy), daily gap calculation requires dividend adjustment:
$$\text{prev\_close\_adjusted} = \text{previous\_regular\_close} - \text{current\_day\_cash\_dividend}$$
$$\text{UpperAnchor} = \max(\text{current\_open}, \text{prev\_close\_adjusted})$$
$$\text{LowerAnchor} = \min(\text{current\_open}, \text{prev\_close\_adjusted})$$

### 1.1 The Provider Coverage Deficit
- **Alpaca Snapshot Limitation:** The original Alpaca corporate actions probe (`MEC-0015-dividend-provider-contract-manifest.json`) contained **31 distributions**, with its earliest record on `2016-06-17`. It lacked all 35 pre-2016 distributions (May 2007 through December 2015) as well as 2 post-2016 distributions (`2016-03-18` and `2018-06-15`), totaling 37 unverified distributions against Alpaca. Prior to the first verified Alpaca distribution (`2016-06-17`), there are 36 preceding M1 distributions.
- **Massive / Polygon Limitation:** Massive's reference corporate actions generally extend back to approximately 2008, leaving the May–December 2007 distributions unverified.

### 1.2 Sovereign Authority Resolution
Rather than relying on third-party broker snapshots or secondary data vendor estimates, ACASH establishes:
```text
PRIMARY_DIVIDEND_AUTHORITY = STATE_STREET_SSGA_OFFICIAL_HISTORICAL_DISTRIBUTIONS
```
**Rationale:** State Street Global Advisors (SSGA) is the fund sponsor and State Street Bank and Trust Company is the trustee for the SPDR S&P 500 ETF Trust (SPY). Official distribution records published by the fund sponsor constitute sovereign primary legal and financial truth.

---

## 2. Official SSGA Source & File Identification

- **Sovereign Source Authority:** State Street Global Advisors (SSGA) / SPDR ETF Distribution Portal.
- **Source Resource:** `SPDR ETF Historical Distributions` (`spdr-etf-historical-distributions.xlsx`).
- **Fund Name:** SPDR S&P 500 ETF Trust (`SPY`).
- **CUSIP:** `78462F103`.
- **Distribution Frequency:** Quarterly ordinary income dividends.

---

## 3. Full M1 Coverage Census & Reconciliation Discipline

### 3.1 Total Distribution Census
- Across the 17-year M1 replication sample (`2007-05-01` through `2024-04-30`), there are **exactly 68 quarterly cash distributions**.
- Chronological breakdown:
  - **Pre-2016 Window (2007-05-01 to 2015-12-31):** 35 distributions (all absent from Alpaca snapshot; 100% supplied by SSGA).
  - **Post-2016 Window (2016-01-01 to 2024-04-30):** 33 distributions in SSGA:
    - **31 Alpaca-present / verified events:** Exact cash rate match against SSGA (`Decimal(SSGA cash_distribution) == Decimal(alpaca_rate)`).
    - **2 Alpaca-unverified events:** `2016-03-18` ($1.049604) and `2018-06-15` ($1.245568) are not marked verified in the Alpaca snapshot, classified neutrally as `ALPACA_CROSS_CHECK_ABSENT_OR_UNVERIFIED`.
  - **Preceding First Verified Alpaca Distribution (before 2016-06-17):** 36 distributions.
  - **Total Unverified in Alpaca:** 37 distributions (35 pre-2016 + 2 post-2016).

### 3.2 Reconciliation Status & Scope Discipline
- `FULL_POST_2016_ALPACA_COVERAGE = NOT_ESTABLISHED` (31 of 33 post-2016 SSGA distributions present/verified).
- `ALPACA_PRESENT_RATE_RECONCILIATION = 31/31 PASS` (100% rate agreement for all 31 Alpaca-present records).
- `SSGA_FULL_M1_DIVIDEND_AUTHORITY = ESTABLISHED` (all 68 distributions authoritative from sovereign fund sponsor).
- **Date Match Scope:** The manifest records ex-date, record date, and payable date from SSGA, alongside `alpaca_rate` and `alpaca_overlap_verified`. Row-by-row Alpaca record and payable dates were not individually retained in the manifest; therefore, no claim of identical record/payable dates is asserted beyond the 31/31 rate reconciliation.

### 3.3 Historical 2007 Census (First Year of M1)
The four quarterly distributions affecting 2007:
1. `2007-03-16` (Pre-M1 baseline reference: `$0.613300`)
2. `2007-06-15` (First M1 distribution: `$0.655800`)
3. `2007-09-21` (Second M1 distribution: `$0.718720`)
4. `2007-12-21` (Third M1 distribution: `$0.775410`)

All 68 distribution records are cataloged in `docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json`.

---

## 4. Secondary Provider Role

- **Massive / Polygon Reference Dividends:** Designated as `SECONDARY_CROSS_CHECK` (deferred until provider credentials configured; SSGA remains sovereign).
- **Alpaca Corporate Actions:** Designated as `SECONDARY_CROSS_CHECK`.
- **Conflict Rule:** In the event of any discrepancy between a broker/aggregator feed and official SSGA fund distribution notices, the official SSGA record strictly governs.

---

## 5. Governance Audit Ledger

| Audit Check | Requirement | Result |
| :--- | :--- | :--- |
| Sovereign Fund Sponsor Identified | State Street Global Advisors (SSGA) | `VERIFIED` |
| Full M1 Coverage Established | 2007-05-01 through 2024-04-30 | `VERIFIED` (68 distributions) |
| Pre-2016 Census Established | 35 pre-2016 records supplied by SSGA | `VERIFIED` (35 events) |
| Post-2016 Census Established | 33 post-2016 records in SSGA | `VERIFIED` (33 events) |
| Alpaca-Present Rate Match | 31 Alpaca-present events match SSGA rate | `VERIFIED (31/31 PASS)` |
| Unverified Events Accounted | 35 pre-2016 + 2 post-2016 = 37 total | `VERIFIED (37 events)` |
| Post-2016 Unverified Rows | 2016-03-18 and 2018-06-15 classified neutrally | `ALPACA_CROSS_CHECK_ABSENT_OR_UNVERIFIED` |
| Preceding First Verified Alpaca | Distributions prior to 2016-06-17 | `36 events` |
| Machine-Readable Manifest Created | Valid JSON with cryptographic digest | `VERIFIED` |
| Price Data Accessed | Zero strategy price data loaded | `VERIFIED` |
