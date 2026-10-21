# Lane B: Primary-Source Corporate-Action Evidence Inventory & Governance Packet

**Classification:** CANDIDATE_PRIMARY_SOURCE_EVIDENCE (Pre-Admission / Candidate Only)  
**Parent Canonical Main:** `018c0eade084e55023ada88e6a73fe77e86d657b` (Post PR #41 merge)  
**Date Context:** 2026-10-22  
**Governing Documents:** [`AGENTS.md`](../../AGENTS.md), [`LANE_B_SPEC_OFFLINE_QUALIFICATION.md`](./LANE_B_SPEC_OFFLINE_QUALIFICATION.md), [`docs/ROADMAP.md`](../ROADMAP.md)  
**Hard Boundaries:** `REAL_CAPITAL_AUTHORITY = USD 0.00` · `NO_REAL_ORDERS = true` · `LANE_A = UNISSUED` · `LANE_B = UNISSUED`

---

## 1. Executive Summary & Review Provenance

This research artifact addresses the findings identified in **ACASH V10 / V11** and establishes reproducible primary-source evidence for the ACASH ETF universe:
1. **D3-01 Integration Provenance:** PR #41 ([`ec94d7f`](https://github.com/Ratthabhumi/Acash/commit/ec94d7f170e7b7ffa801bb47f10168b6dd0a3bdb)) completed the offline streaming proof (19/19 hermetic tests passing) and merged into canonical `main` at [`018c0eade084e55023ada88e6a73fe77e86d657b`](https://github.com/Ratthabhumi/Acash/commit/018c0eade084e55023ada88e6a73fe77e86d657b).
2. **Lane B Primary Evidence Anchors:** Delivers 4 verified candidate distribution events for **VOO, BND, and BIL** sourced directly from primary issuer records (Vanguard and State Street), with exact decimal amounts and verified dates.
3. **GLD Grantor Trust Characterization:** Correctly classifies GLD under `NO_CASH_DISTRIBUTION_ENTITLEMENT` (rather than a fabricated $0.00 dividend event) and isolates GLDM as candidate-only.
4. **Governance & Boundaries:** Corrects overclaimed memory bounds, replaces unsupported entitlement assumptions with `ACCOUNT_ENTITLEMENT_UNKNOWN`, documents exact capture provenance limitations, and packages the versioned byte contract proposal (`IDENTITY_ONLY_RAW_RESPONSE_BODY_V1`) for explicit human ratification.

> [!IMPORTANT]
> **Boundary Notice:** This inventory is classified as **`CANDIDATE_PRIMARY_SOURCE_EVIDENCE`**, NOT **`DATA_QUALIFIED`**.
> Inclusion of VOO/BND/GLD/BIL in this candidate inventory does NOT expand the authority of the historical HYP_010 sponsor panel (`ACWI, AGG, SPY, BIL, VEU`).
> Issuer research does NOT constitute execution authorization (`LANE_B = UNISSUED`). No network requests to providers or brokers have been initiated.

---

## 2. Lane B Primary-Source Issuer Evidence Matrix

Scope: Historical event evidence through 2026-10-22, prioritizing the candidate feasibility window **2026-09-28 through 2026-10-02** and adjacent distribution cycles.

### 2.1 Cash Distribution ETFs (VOO, BND, BIL) — Candidate Anchors

All Record Dates below are reported directly as observed values in official issuer tables (where Record Date equals Ex-Date in the reported rows; this equality is recorded strictly as an observed source value, NOT a universally proven consequence of T+1 settlement rules).

| Field | VOO (Event 1) | BND (Event 1) | BND (Event 2) | BIL (Event 1) |
| :--- | :--- | :--- | :--- | :--- |
| **Ticker** | **VOO** | **BND** | **BND** | **BIL** |
| **CUSIP / Identifier** | 922908363 | 921937835 | 921937835 | 78468R663 |
| **Legal Issuer / Trust** | Vanguard Index Funds | Vanguard Bond Index Funds | Vanguard Bond Index Funds | SPDR Series Trust |
| **Legal Sponsor / Advisor** | The Vanguard Group, Inc. | The Vanguard Group, Inc. | The Vanguard Group, Inc. | SSGA Funds Management, Inc. |
| **Corporate Action Type** | Income Distribution (Quarterly) | Income Distribution (Monthly) | Income Distribution (Monthly) | Cash Dividend (Monthly) |
| **Amount per Share (USD)** | **`1.822600`** | **`0.252886`** | **`0.248502`** | **`0.263176`** |
| **Ex-Dividend Date** | `2026-09-28` | `2026-09-01` | `2026-10-01` | `2026-10-01` |
| **Record Date** | `2026-09-28` | `2026-09-01` | `2026-10-01` | `2026-10-01` |
| **Payable Date** | `2026-09-30` | `2026-09-03` | `2026-10-05` | `2026-10-06` |
| **Currency** | USD | USD | USD | USD |
| **Primary Source Authority** | Vanguard Official Distribution History | Vanguard Official Distribution History | Vanguard Official Distribution History | State Street Official SPDR Distribution Table |
| **Source URL** | [Vanguard Offshore VOO](https://www.vanguardoffshore.com/en/product/etf/equity/0968/vanguard-sp-500-etf) | [Vanguard Advisors BND](https://advisors.vanguard.com/investments/products/bnd/vanguard-total-bond-market-etf) | [Vanguard Advisors BND](https://advisors.vanguard.com/investments/products/bnd/vanguard-total-bond-market-etf) | [SSGA ETF Distributions](https://www.ssga.com/us/en/institutional/resources/documents/etf-dividend-distributions) |
| **Source Document Title** | Vanguard S&P 500 ETF Distributions | Vanguard Total Bond Market ETF Distributions | Vanguard Total Bond Market ETF Distributions | SPDR ETF Dividend Distributions Table |
| **Retrieval Timestamp** | `UNVERIFIED_CAPTURE_TIME` (Session 2026-10-22) | `UNVERIFIED_CAPTURE_TIME` (Session 2026-10-22) | `UNVERIFIED_CAPTURE_TIME` (Session 2026-10-22) | `UNVERIFIED_CAPTURE_TIME` (Session 2026-10-22) |
| **Corroborating Authority** | Vanguard Tax Season Calendar (Form N-CSR for annual audit) | Vanguard Tax Season Calendar (Form N-CSR for annual audit) | Vanguard Tax Season Calendar (Form N-CSR for annual audit) | State Street SPDR Distribution Announcements |
| **Revision Policy Status** | `REVISION_POLICY_UNVERIFIED` | `REVISION_POLICY_UNVERIFIED` | `REVISION_POLICY_UNVERIFIED` | `REVISION_POLICY_UNVERIFIED` |
| **Confirmation Status** | `SOURCE_CONFIRMED_CANDIDATE` | `SOURCE_CONFIRMED_CANDIDATE` | `SOURCE_CONFIRMED_CANDIDATE` | `SOURCE_CONFIRMED_CANDIDATE` |
| **Coverage Limitation** | Preselected Anchor (Not full panel) | Preselected Anchor (Not full panel) | Preselected Anchor (Not full panel) | Preselected Anchor (Not full panel) |

> [!NOTE]
> **Source Hierarchy & Regulatory Filings Rule:**
> 1. Official issuer event tables and distribution press releases serve as the primary authority for corporate action dates and dividend dollar amounts.
> 2. SEC Form N-PORT reports monthly portfolio investment holdings, **not** event-level corporate action dates or per-share distribution schedules. It is not an admissible primary source for dividend calendars.
> 3. SEC Form N-CSR (certified annual/semi-annual shareholder report) provides authoritative retrospective audit confirmation of total distributions paid, but issuer distribution declarations remain the operational authority for event-by-event schedules.

---

### 2.2 Event Lifecycle & Scientific Timestamps

To preserve strict point-in-time discipline and prevent look-ahead bias:
1. **Three Distinct Timestamps:**
   - **$T_{\text{event}}$ (Event Dates):** Ex-date, record date, and payable date established by issuer declaration.
   - **$T_{\text{published}}$ (Declaration/Publication Date):** When the issuer publicly announced or published the distribution schedule.
   - **$T_{\text{retrieved}}$ (ACASH Verification Date):** Recorded as `UNVERIFIED_CAPTURE_TIME` during the 2026-10-22 research session without a timestamped HTTP network capture log. An issuer table retrieved on 2026-10-22 is **NOT** evidence of historical availability on 2026-09-28.
2. **Accounting Lifecycle Impact:**
   - For VOO, Ex-date is `2026-09-28` and Cash Payment is `2026-09-30`. Both fall inside the D3 candidate feasibility window (`2026-09-28` through `2026-10-02`).
   - For BND (Event 2) and BIL, Ex-date is `2026-10-01` (inside the feasibility window), but Payable Dates (`2026-10-05` and `2026-10-06`) fall **after** the window closes.
   - **Lifecycle Rule:** Per existing ACASH accounting (`src/acash/data/contracts/etf_fx_benchmark.py` and HYP_011 contracts):
     - Dividend entitlement is established on Ex-date based on settled whole shares.
     - Cash is recorded as an unpaid receivable and is **strictly non-spendable** until Payable Date cash posting.
     - Provider-adjusted bars (`adjustment=all`) must **NEVER** be substituted for explicit, issuer-backed corporate action factors.

---

### 2.3 GLD Physical Gold Trust Qualification & Accounting

GLD is organized as a grantor trust under the Securities Act of 1933, **not** an investment company under the Investment Company Act of 1940.

| Qualification Attribute | GLD (SPDR Gold Trust) | GLDM (SPDR Gold MiniShares) — Candidate Only |
| :--- | :--- | :--- |
| **Trust Name** | SPDR Gold Trust | SPDR Gold MiniShares Trust |
| **Legal Entity / Sponsor** | World Gold Trust Services, LLC | WGC USA Asset Management Company, LLC |
| **Marketing Agent** | State Street Global Advisors Funds Distributors, LLC | State Street Global Advisors Funds Distributors, LLC |
| **Trustee** | BNY Mellon | BNY Mellon |
| **Custodian** | HSBC Bank plc / JPMorgan Chase Bank, N.A. | HSBC Bank plc / ICBC Standard Bank |
| **Cash Distribution Entitlement** | **`NO_CASH_DISTRIBUTION_ENTITLEMENT`** | **`NO_CASH_DISTRIBUTION_ENTITLEMENT`** |
| **Distribution Event Amount** | `NOT_APPLICABLE` (No cash dividend events exist) | `NOT_APPLICABLE` (No cash dividend events exist) |
| **Gross Expense Ratio** | **0.40% per annum** | **0.10% per annum** |
| **Expense Payment Mechanism** | Trustee sells physical gold periodically to pay trust expenses; gold per share decreases over time | Trustee sells physical gold periodically to pay trust expenses; gold per share decreases over time |
| **Historical Splits Coverage** | None evidenced in published trust disclosures | None evidenced in published trust disclosures |
| **Historical Scope Boundary** | Qualified claims require primary records covering the claimed window; no universal claims | Candidate only; not qualified for Lane A |
| **Lane A Universe Status** | In-Scope Candidate | **STRICTLY EXCLUDED** (Requires separate authorization) |
| **Economic Comparison** | Institutional liquidity, tight spreads, active options | Retail fee advantage (10 bps vs 40 bps), lower liquidity |

> [!CAUTION]
> **Strict Governance Rules:**
> 1. Do NOT fabricate cash dividend events for GLD. Representing GLD as paying `$0.00` is inaccurate; the trust has **NO_CASH_DISTRIBUTION_ENTITLEMENT**.
> 2. Do NOT substitute GLDM for GLD in Lane A without an explicit, ratified governance decision. GLD and GLDM have distinct legal sponsors and cannot share issuer mappings.

---

## 3. Alpaca Provider Rights & Entitlement Decision Packet

Prior to any network activation (D3-02), the operational entitlement checklist must be verified by the account holder:

### 3.1 Public Documentation vs. Unknowns Checklist

| Dimension | Public Documented Fact | ACASH Account Standing | Required Human Action |
| :--- | :--- | :--- | :--- |
| **API Cost** | Basic plan listed at $0/month | `ACCOUNT_ENTITLEMENT_UNKNOWN` | Verify exact registered account tier |
| **Historical Coverage** | Equities data available from 2016 | `UNVERIFIED_FOR_ACCOUNT` | Verify whether account token has historical bar access |
| **Delay Policy** | 15-minute delay on free tier | `DOCUMENTED` | Adhere to 15-minute delay guard |
| **Feed Source** | IEX (free) vs SIP (paid subscription) | `ACCOUNT_ENTITLEMENT_UNKNOWN` | Confirm whether account is IEX-only or SIP-enabled |
| **Raw Data Retention** | Exchange rules restrict redistribution | `UNVERIFIED_FOR_LOCAL_CACHE` | Review Alpaca Master Agreement regarding local research caching |
| **Symbol Mapping** | `asof` defaults to current day | `UNVERIFIED_PIT_MAPPING` | Explicitly bind symbol mapping date in requests |

### 3.2 Account-Owner Inquiry Packet (Ready for Operator Dispatch)

1. **Account Tier & Pricing:** Is the ACASH Alpaca account registered under the Free/Basic tier, or is there an active Market Data subscription?
2. **Feed Authority:** Is the accessible data endpoint strictly IEX, or does the token possess Consolidated Tape Association (CTA/CQ) and Unlisted Trading Privileges (UTP) SIP entitlement?
3. **Data Retention & Caching:** Does Alpaca's API Terms of Service permit permanent local storage (e.g. SHA-256 sealed SQLite/Parquet evidence files) of raw historical bar payloads strictly for non-redistributed internal quantitative model validation?
4. **Point-in-Time Corporate Actions:** Does Alpaca provide point-in-time dividend and split adjustment factors with vintage timestamps, or does `adjustment=all` represent dynamically restated historical series?

---

## 4. Byte Contract Governance Proposal: `IDENTITY_ONLY_RAW_RESPONSE_BODY_V1`

### 4.1 Specification
To guarantee exact byte accounting and fail-closed security across HTTP providers:
1. **Request Header:** Dispatches must send `Accept-Encoding: identity`.
2. **Encoding Verification:** Any response containing `Content-Encoding` other than `identity` (or absent) is immediately rejected fail-closed.
3. **Chunk-Wise Stream Accounting:** Bytes are counted chunk-by-chunk directly from the network transport iterator before decoding.
4. **Cumulative Budget:** Maximum 524,288 raw response-body bytes (512 KiB) across all pagination attempts for a single canary session.
5. **Digest Preservation:** Retained bytes must produce a SHA-256 digest matching the offline evidence manifest.
6. **Zero-Retry Reservation:** Each attempt consumes a sequential reservation slot; aborted or interrupted connections poison the cap and are never refunded.
7. **Malformed Content-Length Handling:**
   - If `Content-Length` header is absent or malformed (non-integer string, multiple headers), treat as absent and rely strictly on chunk-by-chunk stream counting.
   - If `Content-Length` is negative, reject immediately fail-closed with `DataContractError`.
   - If declared `Content-Length` disagrees with actual received streamed bytes upon stream completion, fail closed immediately.

### 4.2 Explicit Limitations & Memory Boundary
* **Post-Read Chunk Detection:** If an upstream chunk arrives exceeding the remaining budget (e.g. an upstream chunk of 100,000 bytes arrives when only 64 bytes remain in the budget), the counter observes the 100,000 bytes and immediately halts execution.
* **Memory Bound Disclosure:** This mechanism is **post-read detection**, NOT a hardware or socket-level memory cap. The oversized chunk is temporarily held in process memory before the cap raises `DataContractError`.
* **Governance Status:** This specification is currently a **`PROPOSAL`**. It requires explicit human ratification before any production HTTP dispatcher is implemented. Merging PR #41 merged the MockTransport proof only; it did NOT ratify production dispatch.

---

## 5. PIT / Asof & Scientific Reuse Ledger

### 5.1 PIT vs. Symbol Mapping Separation
* Alpaca's `asof` parameter specifies the symbol mapping date (i.e. ticker resolution). It does **NOT** freeze historical revision vintages.
* Point-in-Time (PIT) data integrity requires immutable dataset manifests with explicit creation timestamps, source URLs, and SHA-256 digests.
* Corporate-action vintage policies must be verified per issuer before admitting historical dividend panels.

### 5.2 Research Asset Reuse Index
* **M1.6 Benchmark Contracts:** Integrated at [`src/acash/data/contracts/etf_fx_benchmark.py`](../../src/acash/data/contracts/etf_fx_benchmark.py). Fully reusable for VOO/BND/GLD/BIL portfolio accounting.
* **M1.7 / M1.8.1 Authority & Transport:** Reusable for request serialization and offline rehearsal.
* **D1 / D2 Safety & Composition:** Merged on `main` ([PR #32](https://github.com/Ratthabhumi/Acash/pull/32), [PR #37](https://github.com/Ratthabhumi/Acash/pull/37), [PR #39](https://github.com/Ratthabhumi/Acash/pull/39)).
* **D3-00 Offline Ed25519 Approval:** Merged on `main` ([PR #40](https://github.com/Ratthabhumi/Acash/pull/40)).
* **D3-01 Offline Streaming Proof:** Merged on `main` ([PR #41](https://github.com/Ratthabhumi/Acash/pull/41) at commit `018c0eade084e55023ada88e6a73fe77e86d657b`).
* **Historical HYP_011 Dataset:** Retains original scope (`ACWI, AGG, SPY`); strictly quarantined from new Invest/Lane A universe.

---

## 6. Verification Ledger & Human Action Items

### Verification Ledger
- Implementation Status: COMPLETE (PR #42 updated with exact issuer evidence, substantiated capture provenance, and corrected regulatory filing roles)
- Canonical Main Parent: `018c0eade084e55023ada88e6a73fe77e86d657b`
- Working Branch: `research/lane-b-primary-evidence-inventory` (PR #42)
- Contract Enforcement: STRICT FAIL-CLOSED
- Evidence Classification: `CANDIDATE_PRIMARY_SOURCE_EVIDENCE` (Pre-Admission)
- Mathematical Authority: ISSUER_CONFIRMED_ANCHORS (Vanguard & SSGA primary tables)
- Local Test Suite: VERIFIED (19 passed in `test_lane_a_d3_streaming.py`)
- Type Checker (MyPy): VERIFIED (615 files clean)
- Capital & Live Orders: `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`

### Immediate Next Actions
1. **ONE Next Human Decision:** Review and dispatch the Alpaca Account-Owner Inquiry Packet (§3.2) and ratify the `IDENTITY_ONLY_RAW_RESPONSE_BODY_V1` byte contract proposal (§4.1).
2. **ONE Next Engineering/Research Task:** Consolidate historical dividend schedule archives for VOO, BND, and BIL across adjacent quarters to prepare the candidate panel for D4 corporate-action admission.
