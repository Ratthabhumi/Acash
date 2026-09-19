# MEC-0014: SPY Primary Closing Auction Coverage Census (2017–2022)

**Audit Timestamp (UTC):** `2026-09-19T01:53:35.669856+00:00`<br>
**Source Git Commit SHA:** `3aa87e26655789d10a028b5ec7cab9ad5dd1b870`<br>
**Governing Calendar:** `NyseCa1Calendar` (Sovereign Authority)<br>
**Target Symbol:** `SPY` (Primary Listing: NYSE Arca, Exchange `P`)<br>
**Qualified Normal Candidate Semantic:** Closing Auction `c=6` on Exchange `P` (`x=P, c=6`)<br>
**Data Source:** Alpaca Market Data API v2 (`/v2/stocks/SPY/auctions`, `feed=sip`)

---

## 1. Executive Summary & Decision Ruling

> [!IMPORTANT]
> **CENSUS VERDICT: COMPLETE NORMAL PATH (100% COVERAGE)**
> Every single qualified regular trading session from 2017-01-01 through 2022-12-31 (1498/1498 sessions) contains **exactly one qualifying NYSE Arca primary closing auction cross** (`x=P, c=6`).
> 
> - **`SPY_PRIMARY_CLOSE_COVERAGE_2017_2022`**: `COMPLETE_NORMAL_PATH`
> - **`HISTORICAL_EXCEPTIONAL_CLOSE_FALLBACK`**: `NOT_REQUIRED_FOR_OBSERVED_2017_2022_SPY_SESSIONS`
> - **`PREVIOUS_CLOSE_FALLBACK_POLICY`**: Preserved as `OPEN_REGIME_DEPENDENT` for unobserved/future exceptional sessions, but **not required for the 2017–2022 SPY research partition**.
> 
> **Architectural Consequence:** Reconstruction and implementation of the complex NYSE Arca AOCP fallback engine (NBBO midpoint TWAP + consolidated last sale weighting) is **strictly bypassed for observed MEC-0014A dataset preparation**, eliminating historical regime emulation risk.

---

## 2. Census Metrics & Coverage Breakdown

| Metric | Value | Compliance Status |
| :--- | :---: | :--- |
| **Total Qualified Regular Sessions (NyseCa1Calendar)** | `1498` | Regular 390m sessions only (excluding early closes) |
| **Total Sessions Queried & Matched** | `1498` | Exact match with calendar authority |
| **Unique Primary Auction Crosses (`x=P, c=6`)** | `1498` | Primary candidate identified |
| **Missing Primary Auction Sessions** | `0` | CLEAN (0) |
| **Ambiguous Primary Auction Sessions (>1 print)** | `0` | CLEAN (0) |
| **Effective Sample Coverage Percentage** | `100.0000%` | 100.0000% COMPLETE |

---

## 3. Anomalous Sessions Enumeration

**Zero Anomalous Sessions Detected.**
- Missing Sessions: `[]`
- Ambiguous Sessions: `[]`

Every regular session in 2017–2022 resolved to a unique, deterministic NYSE Arca closing cross.

---

## 4. Cryptographic Provenance & Evidence Manifest

- **Tracked Manifest:** [`docs/research/manifests/MEC-0014-spy-close-coverage-manifest.json`](file:///docs/research/manifests/MEC-0014-spy-close-coverage-manifest.json)
- **Raw Payload SHA-256 Hashes:**
  - `auctions_SPY_2017_p1.json`: `899221dde496d77a77eaf2f80f954c6ae6c5f0929449114195dccd564ac5e937`
  - `auctions_SPY_2018_p1.json`: `5ca0c3f888baa0c6c9a2cff90753563f3da5b23d4855c812717761e0a582dad1`
  - `auctions_SPY_2019_p1.json`: `169e22a1dc5e5fba184ba6fb751089336e2cff5e340842283716dc14a39d1a79`
  - `auctions_SPY_2020_p1.json`: `9f983c997356224999b0a901effa8cb7a29076a2b63ac97710d168c5871fe434`
  - `auctions_SPY_2021_p1.json`: `144d2c32d2bb9c461f9b28a3ecee2efb57ae712f9f751358e9e3e617c9fb6b4c`
  - `auctions_SPY_2022_p1.json`: `e9f7a6621c3b6a77ab9fa1ce6f460fa2eb7999ea9de5b9d925a87ca0fe5d8a9a`

> [!NOTE]
> **Governance Invariants:**
> - Zero Out-of-Sample (OOS 2023–2026) data was accessed.
> - Zero returns ($r_1, r_{13}$), regressions, correlations, Sharpe, or signals were computed.
> - `HYP_004` remains strictly ABSENT; `ResearchReInceptionGate` NOT invoked.
> - Sovereign capital remains `$0.00`; `NO_REAL_ORDERS = true`.
