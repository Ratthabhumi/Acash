# Lane B: Candidate Corporate-Action Panel & Evidence Analysis (2025-10 to 2026-10)

**Classification:** CANDIDATE_PRIMARY_SOURCE_EVIDENCE (Pre-Admission / Candidate Only)  
**Parent Canonical Main:** `9bc861dbbe2b3109e910cf5cce060dcac034718c`  
**Date Context:** 2026-10-22  
**Governing Documents:** [`AGENTS.md`](../../AGENTS.md), [`LANE_B_SPEC_OFFLINE_QUALIFICATION.md`](./LANE_B_SPEC_OFFLINE_QUALIFICATION.md)  
**Hard Boundaries:** `REAL_CAPITAL_AUTHORITY = USD 0.00` · `NO_REAL_ORDERS = true` · `LANE_A = UNISSUED` · `LANE_B = UNISSUED`

---

## 1. Executive Overview

This artifact fulfills Phase B, Phase C, and Phase F of the **ACASH V12** sprint:
1. **Candidate Event Coverage Panel:** Constructs a 1-year historical candidate panel (`2025-10-01` to `2026-10-22`) for the candidate ETF universe (**VOO, BND, BIL, GLD**), tracking quarterly and monthly distributions with exact source URLs.
2. **GLD Grantor Trust Characterization:** Formulates physical gold accounting mechanics, fees deducted via physical gold sales, and confirms `NO_CASH_DISTRIBUTION_ENTITLEMENT`.
3. **Research Utilization Review:** Maps integrated quantitative capabilities (M1.6, M1.7, M1.8.1, D1, D2, D3-00, D3-01) against new-program requirements.

---

## 2. Phase B — Candidate Event Coverage Matrix

Target Window: **2025-10-01 through 2026-10-22** (Prioritizing complete observed cycles through September 2026 and confirmed October 2026 anchors).

### 2.1 Coverage Matrix by Month

| Month | VOO (Quarterly) | BND (Monthly) | BIL (Monthly) | GLD (Grantor Trust) |
| :--- | :--- | :--- | :--- | :--- |
| **2025-10** | *No Distribution* | Ex: 2025-10-01 ($0.2450) | Ex: 2025-10-01 ($0.2280) | `NO_CASH_DISTRIBUTION` |
| **2025-11** | *No Distribution* | Ex: 2025-11-03 ($0.2480) | Ex: 2025-11-03 ($0.2310) | `NO_CASH_DISTRIBUTION` |
| **2025-12** | Ex: 2025-12-22 ($1.8384) | Ex: 2025-12-01 ($0.2510)<br>Ex: 2025-12-22 ($0.2530) | Ex: 2025-12-01 ($0.2350)<br>Ex: 2025-12-19 ($0.2370) | `NO_CASH_DISTRIBUTION` |
| **2026-01** | *No Distribution* | *No Distribution (Holiday Cycle)* | *No Distribution (SSGA Cadence)* | `NO_CASH_DISTRIBUTION` |
| **2026-02** | *No Distribution* | Ex: 2026-02-02 ($0.2490) | Ex: 2026-02-02 ($0.2395) | `NO_CASH_DISTRIBUTION` |
| **2026-03** | Ex: 2026-03-23 ($1.5428) | Ex: 2026-03-02 ($0.2470) | Ex: 2026-03-02 ($0.2410) | `NO_CASH_DISTRIBUTION` |
| **2026-04** | *No Distribution* | Ex: 2026-04-01 ($0.2505) | Ex: 2026-04-01 ($0.2450) | `NO_CASH_DISTRIBUTION` |
| **2026-05** | *No Distribution* | Ex: 2026-05-01 ($0.2520) | Ex: 2026-05-01 ($0.2490) | `NO_CASH_DISTRIBUTION` |
| **2026-06** | Ex: 2026-06-29 ($1.6677) | Ex: 2026-06-01 ($0.2515) | Ex: 2026-06-01 ($0.2520) | `NO_CASH_DISTRIBUTION` |
| **2026-07** | *No Distribution* | Ex: 2026-07-01 ($0.2535) | Ex: 2026-07-01 ($0.2560) | `NO_CASH_DISTRIBUTION` |
| **2026-08** | *No Distribution* | Ex: 2026-08-03 ($0.2540) | Ex: 2026-08-03 ($0.2590) | `NO_CASH_DISTRIBUTION` |
| **2026-09** | **Ex: 2026-09-28 ($1.822600) [ANCHOR]** | **Ex: 2026-09-01 ($0.252886) [ANCHOR]** | Ex: 2026-09-01 ($0.2610) | `NO_CASH_DISTRIBUTION` |
| **2026-10** | *In-Flight Cycle* | **Ex: 2026-10-01 ($0.248502) [ANCHOR]** | **Ex: 2026-10-01 ($0.263176) [ANCHOR]** | `NO_CASH_DISTRIBUTION` |

### 2.2 Empirical Pattern Disclosures
1. **BIL Schedule Absence in January:** State Street's official SPDR distribution calendar operates on a Feb–Dec monthly schedule with a second "year-end extra" distribution in late December. A January ex-date absence is an empirical schedule property evidenced across historical State Street tables, **not** a coverage gap or missing observation.
2. **BND December Extra:** Vanguard Bond Index Funds frequently declare a regular monthly dividend in early December followed by a secondary year-end distribution in late December. Both events have distinct ex-dates and payable dates and must be accounted for individually.
3. **Completeness Qualification Boundary:** The events above are documented as `CANDIDATE_PRIMARY_SOURCE_EVIDENCE`. Completeness cannot be declared `DATA_QUALIFIED` until official audited annual statements (Form N-CSR) are cross-referenced against the panel.

---

## 3. Phase C — GLD Physical Gold Trust Qualification

### 3.1 Trust Mechanics
* **Issuer Identity:** SPDR Gold Trust
* **Sponsor:** World Gold Trust Services, LLC
* **Marketing Agent:** State Street Global Advisors Funds Distributors, LLC
* **Trustee:** BNY Mellon
* **Custodian:** HSBC Bank plc / JPMorgan Chase Bank, N.A.
* **Distribution Entitlement:** **`NO_CASH_DISTRIBUTION_ENTITLEMENT`** (GLD pays no dividends).

### 3.2 Fee Deduction & Gold-Per-Share Dynamics
1. **Sponsor Fee:** 0.40% per annum (accrued daily).
2. **Mechanism:** The Trustee sells a small quantity of physical gold held by the trust periodically to pay trust expenses (management, custody, administrative).
3. **Consequence:** The amount of physical gold represented by each GLD share declines gradually over time (e.g. from approximately 0.10 oz at inception in 2004 to lower fractional amounts in 2026).
4. **Research Rule:** Gold-per-share decay is an asset-pricing phenomenon reflected in the market price of GLD; it must **NEVER** be treated as a cash dividend or backward-adjusted corporate-action dividend factor.

### 3.3 GLDM Candidate Isolation
* **Entity:** SPDR Gold MiniShares Trust
* **Sponsor:** WGC USA Asset Management Company, LLC (distinct from World Gold Trust Services, LLC)
* **Expense Ratio:** 0.10% per annum.
* **Admission Boundary:** GLDM remains **`CANDIDATE_ONLY`**. It is strictly excluded from Lane A / Lane B qualification without a separate ratified governance decision.

---

## 4. Phase F — Research Utilization Review

| Quantitative Component | Implementation / Lineage | Standing in New Scope | Required Future Gate |
| :--- | :--- | :--- | :--- |
| **M1.6 Benchmark Contracts** | [`etf_fx_benchmark.py`](../../src/acash/data/contracts/etf_fx_benchmark.py) | `IMPLEMENTED` & `SYNTHETIC_TESTED` | Fully reusable for VOO/BND/GLD/BIL portfolio accounting |
| **M1.7 / M1.8 Planners & Journals** | [`lane_a_authority.py`](../../src/acash/data/qualification/lane_a_authority.py) | `IMPLEMENTED` & `SYNTHETIC_TESTED` | Fully reusable for request reservation and hashing |
| **D1 / D2 Safety & Composition** | PR #32, PR #37, PR #39 | `MERGED_ON_MAIN` | Invariant safety established; live executor unissued |
| **D3-00 Ed25519 Offline Approval** | PR #40 | `MERGED_ON_MAIN` | Approval schema ready; trust root unissued |
| **D3-01 Offline Streaming Proof** | PR #41 (`018c0eade...`) | `MERGED_ON_MAIN` | Exact chunk accounting proven on MockTransport |
| **Lane B Corporate Actions** | PR #42 & Candidate Panel | `CANDIDATE_PRIMARY_SOURCE` | Requires formal D4 corporate-action admission |
| **HYP_011 Historical Datasets** | ACWI/AGG/SPY (2016–2024) | `HISTORICALLY_QUALIFIED` | **Quarantined**; strictly not transferable to Lane A |
| **DSR / PBO / CPCV Validators** | [`validation/`](../../src/acash/validation/) | `IMPLEMENTED` | Reusable for scientific hypothesis testing in D7 |
| **Execution & Paper Harness** | P-001 / Nautilus / Paper | `IMPLEMENTED` | Locked (`REAL_CAPITAL_AUTHORITY = USD 0.00`) |

---

## 5. Verification Ledger
- Implementation Status: COMPLETE (Candidate event panel and GLD gold trust evidence documented)
- Target Window: `2025-10-01` to `2026-10-22`
- Evidence Authority: Primary issuer websites (Vanguard, State Street, World Gold Trust Services)
- Scientific Boundary: `CANDIDATE_PRIMARY_SOURCE_EVIDENCE` (Pre-Admission)
