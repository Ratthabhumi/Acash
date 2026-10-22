# Lane B: Candidate Corporate-Action Panel & Evidence Analysis (2025-10 to 2026-10)

**Classification:** CANDIDATE_PRIMARY_SOURCE_EVIDENCE (Pre-Admission / Candidate Only)  
**Parent Canonical Main:** `0f949ad03d9c862bc19f55c69b15cb8dabb97fb3`  
**Date Context:** 2026-10-22  
**Governing Documents:** [`AGENTS.md`](../../AGENTS.md), [`LANE_B_SPEC_OFFLINE_QUALIFICATION.md`](./LANE_B_SPEC_OFFLINE_QUALIFICATION.md)  
**Hard Boundaries:** `REAL_CAPITAL_AUTHORITY = USD 0.00` · `NO_REAL_ORDERS = true` · `LANE_A = UNISSUED` · `LANE_B = UNISSUED`

---

## 1. Executive Overview & Event Census

This artifact fulfills Phase B, Phase C, and Phase F of the **ACASH V12 / V13** sprint:
1. **Accurate Event Census:** Evaluates exactly **30 cash distribution events** across the 1-year window (`2025-10-01` to `2026-10-22`):
   - **VOO (Vanguard S&P 500 ETF):** 4 quarterly distributions (4 confirmed).
   - **BND (Vanguard Total Bond Market ETF):** 13 monthly distributions (13 confirmed, 0 partial).
   - **BIL (SPDR Bloomberg 1-3M T-Bill ETF):** 13 monthly distributions (13 confirmed, 0 partial).
   - **GLD (SPDR Gold Trust):** 1 physical grantor trust record (`NO_CASH_DISTRIBUTION_ENTITLEMENT`).
2. **Evaluation Status:** The candidate panel achieves **`SOURCE_VERIFIED_CANDIDATE`** because every cash row is now bound to a captured issuer source. This is source verification of event facts, **not** dataset admission and **not** PIT-vintage qualification.
3. **GLD Grantor Trust Characterization:** Formulates physical gold accounting mechanics, fees deducted via physical gold sales, and confirms `NO_CASH_DISTRIBUTION_ENTITLEMENT`.

---

## 2. Primary-Source Discrepancy Ledger (Resolved)

Independent verification against primary issuer tables (Vanguard and State Street) identified and corrected the following discrepancies between earlier candidate estimates and official declarations:

| Symbol | Period / Date | Prior Candidate Value | Official Issuer Declared Value | Primary Source Reference | Resolution Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **VOO** | Q4 2025 | $1.838400, pay 2025-12-26 | **$1.771000, pay 2025-12-24** | Vanguard Official VOO Distribution History | `AMENDED_TO_OFFICIAL` |
| **VOO** | Q1 2026 | $1.542800, ex 2026-03-23 | **$1.872400, ex 2026-03-27, pay 03-31** | Vanguard Official VOO Distribution History | `AMENDED_TO_OFFICIAL` |
| **VOO** | Q2 2026 | $1.667700, ex 2026-06-29 | **$1.962200, ex 2026-06-26, pay 06-30** | Vanguard Official VOO Distribution History | `AMENDED_TO_OFFICIAL` |
| **BND** | Dec 2025 Extra | $0.253000, ex 2025-12-22 | **$0.246638, ex 2025-12-18, pay 12-22** | Vanguard BND Distribution History | `AMENDED_TO_OFFICIAL` |
| **BND** | Jul 2026 | $0.253500 | **$0.244470, ex 2026-07-01, pay 07-06** | Vanguard BND Distribution History | `AMENDED_TO_OFFICIAL` |
| **BND** | Aug 2026 | $0.254000 | **$0.251550, ex 2026-08-03, pay 08-05** | Vanguard BND Distribution History | `AMENDED_TO_OFFICIAL` |
| **BIL** | Sep 2026 | $0.261000 | **$0.279771, ex 2026-09-01, pay 09-04** | State Street SPDR Historical Table | `AMENDED_TO_OFFICIAL` |

### 2.1 V20 BND Issuer-Table Capture (2026-10-22)

The eight previously `SOURCE_PARTIAL` BND rows are now bound to the issuer
distribution table embedded in the Vanguard BND product page. Capture artifact:

- URL: `https://investor.vanguard.com/investment-products/etfs/profile/bnd`
- Retrieved: 2026-10-22 (HTTP 200, 226,062 raw bytes)
- SHA-256: `d09560f58834be2b1297f782969410aba07adab08f1a537a366f3dcd916d3abd`
- Row identity: `vanguard_bnd_distribution_history:recordDate=MM/DD/YYYY`
- Extraction: HTML-unescaped embedded JSON array; `recordDate`, `reInvestDate`,
  `payableDate`, `share`.

| Ex-Date | Prior Candidate | Issuer Value | Payable | Status After |
| :--- | :--- | :--- | :--- | :--- |
| 2025-10-01 | $0.245000 | **$0.237328** | 2025-10-03 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2025-11-03 | $0.248000 | **$0.243631** | 2025-11-05 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2025-12-01 | $0.251000 | **$0.238572** | 2025-12-03 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2026-02-02 | $0.249000 | **$0.245470** | 2026-02-04 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2026-03-02 | $0.247000 | **$0.227824** | 2026-03-04 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2026-04-01 | $0.250500 | **$0.250016** | 2026-04-06 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2026-05-01 | $0.252000 | **$0.241713** | 2026-05-05 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2026-06-01 | $0.251500 | **$0.247259** | 2026-06-03 | `SOURCE_CONFIRMED_CANDIDATE` |

The issuer table also confirms the previously bound rows (2025-12-18, 2026-07-01,
2026-08-03, 2026-09-01, 2026-10-01) without amount or payable changes. All 13 BND
rows now carry `retrieval_status = CAPTURED_LIVE_ISSUER_TABLE_2026-10-22`.

**Boundary:** the captured page is a live historical table, not the original
2025/2026 publication vintage. `publication_date = UNKNOWN` and
`revision_status = REVISION_POLICY_UNVERIFIED` are retained. The capture is
metadata-level binding, not a cryptographic seal, and is not dataset admission.

### 2.2 V14 Evidence-Integrity Corrections (code)

Three P1 integrity defects were fixed in `lane_b_candidate_evaluator.py`:

1. **Unsafe confirmation default** — `from_dict()` no longer defaults missing `confirmation_status` to confirmed; it resolves to `SOURCE_PARTIAL`, and unknown statuses are rejected as malformed.
2. **Domain-is-not-evidence** — confirmation now requires a non-empty `source_row_ref`; an authorized issuer domain without a row/document binding is **downgraded to `SOURCE_PARTIAL`**. URL checks now also enforce `https`, reject userinfo and explicit ports, and reject lookalike hosts.
3. **Incomplete evidence digest** — the evidence manifest digest now binds `source_row_ref`, `retrieval_status`, `publication_date`, `revision_status`, `cusip`, source document and fund identity, using canonical JSON (no `|` delimiter collisions). The economic digest remains unchanged, preserving the economic-vs-evidence separation.

**Limitation:** `source_row_ref` and the digest are metadata-level provenance bindings. They do **not** cryptographically seal the issuer artefact and do **not** constitute automated primary-source verification.

### 2.3 V17 BIL Official-Workbook Reconciliation (2026-10-22)

All 11 BIL `SOURCE_PARTIAL` rows were bound to the official
`spdr-etf-historical-distributions.xlsx` workbook (sheet `dividend`, row identity =
ticker `BIL` + ex-date). One candidate date was wrong: `2025-12-19` is officially
`2025-12-18`. Amounts and payable dates were replaced with the issuer row values.

| Ex-Date | Prior Candidate | Issuer Value | Payable | Status After |
| :--- | :--- | :--- | :--- | :--- |
| 2025-10-01 | $0.228000 | **$0.310508** | 2025-10-06 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2025-11-03 | $0.231000 | **$0.303301** | 2025-11-06 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2025-12-01 | $0.235000 | **$0.281225** | 2025-12-04 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2025-12-19 (wrong date) | $0.237000 | **$0.365425** (ex 2025-12-18) | 2025-12-23 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2026-02-02 | $0.239500 | **$0.273931** | 2026-02-05 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2026-03-02 | $0.241000 | **$0.243106** | 2026-03-05 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2026-04-01 | $0.245000 | **$0.263657** | 2026-04-06 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2026-05-01 | $0.249000 | **$0.269910** | 2026-05-06 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2026-06-01 | $0.252000 | **$0.269202** | 2026-06-04 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2026-07-01 | $0.256000 | **$0.267622** | 2026-07-07 | `SOURCE_CONFIRMED_CANDIDATE` |
| 2026-08-03 | $0.259000 | **$0.272951** | 2026-08-06 | `SOURCE_CONFIRMED_CANDIDATE` |

The two previously-confirmed BIL rows (2026-09-01 `0.279771`, 2026-10-01 `0.263176`)
agree with the same workbook. December 2025 does contain two distinct issuer-declared
events (2025-12-01 and 2025-12-18); January 2026 contains none in the workbook.

**Boundary:** this is event-level source binding, not a cryptographic seal. The
workbook revision/vintage policy and the extraction capture time remain unverified.

---

## 3. Phase B — Candidate Event Coverage Matrix

Target Window: **2025-10-01 through 2026-10-22**

### 3.1 Coverage Matrix by Month

| Month | VOO (Quarterly) | BND (Monthly) | BIL (Monthly) | GLD (Grantor Trust) |
| :--- | :--- | :--- | :--- | :--- |
| **2025-10** | *No Distribution* | Ex: 2025-10-01 ($0.237328) [PARTIAL] | **Ex: 2025-10-01 ($0.310508) [CONFIRMED]** | `NO_CASH_DISTRIBUTION` |
| **2025-11** | *No Distribution* | Ex: 2025-11-03 ($0.243631) [PARTIAL] | **Ex: 2025-11-03 ($0.303301) [CONFIRMED]** | `NO_CASH_DISTRIBUTION` |
| **2025-12** | **Ex: 2025-12-22 ($1.771000) [CONFIRMED]** | Ex: 2025-12-01 ($0.238572) [PARTIAL]<br>**Ex: 2025-12-18 ($0.246638) [CONFIRMED]** | **Ex: 2025-12-01 ($0.281225) [CONFIRMED]**<br>**Ex: 2025-12-18 ($0.365425) [CONFIRMED]** | `NO_CASH_DISTRIBUTION` |
| **2026-01** | *No Distribution* | *No Distribution (Holiday Cadence)* | *No Distribution (SSGA Cadence)* | `NO_CASH_DISTRIBUTION` |
| **2026-02** | *No Distribution* | Ex: 2026-02-02 ($0.245470) [PARTIAL] | **Ex: 2026-02-02 ($0.273931) [CONFIRMED]** | `NO_CASH_DISTRIBUTION` |
| **2026-03** | **Ex: 2026-03-27 ($1.872400) [CONFIRMED]** | Ex: 2026-03-02 ($0.227824) [PARTIAL] | **Ex: 2026-03-02 ($0.243106) [CONFIRMED]** | `NO_CASH_DISTRIBUTION` |
| **2026-04** | *No Distribution* | Ex: 2026-04-01 ($0.250016) [PARTIAL] | **Ex: 2026-04-01 ($0.263657) [CONFIRMED]** | `NO_CASH_DISTRIBUTION` |
| **2026-05** | *No Distribution* | Ex: 2026-05-01 ($0.241713) [PARTIAL] | **Ex: 2026-05-01 ($0.269910) [CONFIRMED]** | `NO_CASH_DISTRIBUTION` |
| **2026-06** | **Ex: 2026-06-26 ($1.962200) [CONFIRMED]** | Ex: 2026-06-01 ($0.247259) [PARTIAL] | **Ex: 2026-06-01 ($0.269202) [CONFIRMED]** | `NO_CASH_DISTRIBUTION` |
| **2026-07** | *No Distribution* | **Ex: 2026-07-01 ($0.244470) [CONFIRMED]** | **Ex: 2026-07-01 ($0.267622) [CONFIRMED]** | `NO_CASH_DISTRIBUTION` |
| **2026-08** | *No Distribution* | **Ex: 2026-08-03 ($0.251550) [CONFIRMED]** | **Ex: 2026-08-03 ($0.272951) [CONFIRMED]** | `NO_CASH_DISTRIBUTION` |
| **2026-09** | **Ex: 2026-09-28 ($1.822600) [CONFIRMED]** | **Ex: 2026-09-01 ($0.252886) [CONFIRMED]** | **Ex: 2026-09-01 ($0.279771) [CONFIRMED]** | `NO_CASH_DISTRIBUTION` |
| **2026-10** | *In-Flight Cycle* | **Ex: 2026-10-01 ($0.248502) [CONFIRMED]** | **Ex: 2026-10-01 ($0.263176) [CONFIRMED]** | `NO_CASH_DISTRIBUTION` |

### 3.2 Confirmation Status Breakdown
- **SOURCE_CONFIRMED_CANDIDATE:** 30 events (VOO 4, BND 13, BIL 13) — each carries a `source_row_ref`.
- **SOURCE_PARTIAL:** 0 events.
- **Overall Result:** `SOURCE_VERIFIED_CANDIDATE` (all cash rows are issuer-source-bound; this is not dataset admission or PIT-vintage qualification).

> **Counting rule:** the total candidate panel (30) equals the number of source-bound
> records. `admission_status` remains `NOT_ADMITTED`. A row not present in an
> accessible issuer table would not be evidence of a zero distribution.

---

## 4. Phase C — GLD Physical Gold Trust Qualification

### 4.1 Trust Mechanics
* **Issuer Identity:** SPDR Gold Trust
* **Sponsor:** World Gold Trust Services, LLC
* **Marketing Agent:** State Street Global Advisors Funds Distributors, LLC
* **Trustee:** BNY Mellon
* **Custodian:** HSBC Bank plc / JPMorgan Chase Bank, N.A.
* **Distribution Entitlement:** **`NO_CASH_DISTRIBUTION_ENTITLEMENT`** (GLD pays no dividends).

### 4.2 Fee Deduction & Gold-Per-Share Dynamics
1. **Sponsor Fee:** 0.40% per annum (accrued daily).
2. **Mechanism:** The Trustee sells a small quantity of physical gold held by the trust periodically to pay trust expenses (management, custody, administrative).
3. **Consequence:** The amount of physical gold represented by each GLD share declines gradually over time.
4. **Research Rule:** Gold-per-share decay is an asset-pricing phenomenon reflected in the market price of GLD; it must **NEVER** be treated as a cash dividend or backward-adjusted corporate-action dividend factor.

### 4.3 GLDM Candidate Isolation
* **Entity:** SPDR Gold MiniShares Trust
* **Sponsor:** WGC USA Asset Management Company, LLC (distinct from World Gold Trust Services, LLC)
* **Expense Ratio:** 0.10% per annum.
* **Admission Boundary:** GLDM remains **`CANDIDATE_ONLY`**. It is strictly excluded from Lane A / Lane B qualification without a separate ratified governance decision.

---

## 5. Phase F — Research Utilization Review

| Quantitative Component | Implementation / Lineage | Standing in New Scope | Required Future Gate |
| :--- | :--- | :--- | :--- |
| **M1.6 Benchmark Contracts** | [`etf_fx_benchmark.py`](../../src/acash/data/contracts/etf_fx_benchmark.py) | `IMPLEMENTED` & `SYNTHETIC_TESTED` | Fully reusable for VOO/BND/GLD/BIL portfolio accounting |
| **M1.7 / M1.8 Planners & Journals** | [`lane_a_authority.py`](../../src/acash/data/qualification/lane_a_authority.py) | `IMPLEMENTED` & `SYNTHETIC_TESTED` | Fully reusable for request reservation and hashing |
| **D1 / D2 Safety & Composition** | PR #32, PR #37, PR #39 | `MERGED_ON_MAIN` | Invariant safety established; live executor unissued |
| **D3-00 Ed25519 Offline Approval** | PR #40 | `MERGED_ON_MAIN` | Approval schema ready; trust root unissued |
| **D3-01 Offline Streaming Proof** | PR #41 (`018c0eade...`) | `MERGED_ON_MAIN` | Exact chunk accounting proven on MockTransport |
| **Lane B Corporate Actions** | PR #42 & PR #43 Candidate Panel | `CANDIDATE_PRIMARY_SOURCE` | Requires formal D4 corporate-action admission |
| **HYP_011 Historical Datasets** | ACWI/AGG/SPY (2016–2024) | `HISTORICALLY_QUALIFIED` | **Quarantined**; strictly not transferable to Lane A |
| **DSR / PBO / CPCV Validators** | [`validation/`](../../src/acash/validation/) | `IMPLEMENTED` | Reusable for scientific hypothesis testing in D7 |
| **Execution & Paper Harness** | P-001 / Nautilus / Paper | `IMPLEMENTED` | Locked (`REAL_CAPITAL_AUTHORITY = USD 0.00`) |

---

## 6. Verification Ledger
- Implementation Status: COMPLETE (30 candidate cash events + 1 physical trust record documented)
- Target Window: `2025-10-01` to `2026-10-22`
- Evaluator Status: `SOURCE_VERIFIED_CANDIDATE` (30 confirmed, 0 partial)
- BND Artifact: 226,062 bytes, SHA-256 `d09560f58834be2b1297f782969410aba07adab08f1a537a366f3dcd916d3abd`
- Confirmation Authority: missing/unknown status never confirms; confirmed requires `source_row_ref`
- Evidence Digest: binds retrieval/publication/revision/cusip/row-ref via canonical JSON (economic digest unchanged)
- Targeted Tests: 33 passed (`tests/unit/data/test_lane_b_candidate_qualification.py`)
- Type Checker: MyPy clean on evaluator + test module
- Scientific Boundary: `CANDIDATE_PRIMARY_SOURCE_EVIDENCE` (Pre-Admission)

### 6.1 Remaining Unverified Gaps
- BND rows are bound to a live issuer table captured 2026-10-22, not to the original
  2025/2026 publication vintage. `publication_date` and `revision_status` remain
  `UNKNOWN` / `REVISION_POLICY_UNVERIFIED`.
- The 2026-10-22 advisors-page retrieval (161,898 bytes) exposed no dataset/export;
  the successful capture came from the investor product page embedded table.
- BIL rows were extracted from the official SPDR historical-distributions workbook
  (2026-10-22); the workbook revision policy and exact capture timestamp are still
  unverified.
- Artifact captures are metadata-level provenance bindings, not cryptographic seals,
  and do not constitute D4 admission.
- `publication_date` / `revision_status`: issuer correction/vintage policy not disclosed/recorded.
- GLD: `NO_CASH_DISTRIBUTION_ENTITLEMENT`; gold-per-share decay is not a dividend.
- GLDM: excluded from the authorized universe (`CANDIDATE_ONLY`).
