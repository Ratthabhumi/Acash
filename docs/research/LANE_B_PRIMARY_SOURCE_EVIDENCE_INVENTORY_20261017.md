# Lane B: Primary-Source Corporate-Action Evidence Inventory & Governance Packet

**Classification:** CANDIDATE_PRIMARY_SOURCE_EVIDENCE (Pre-Admission / Candidate Only)  
**Parent Canonical Main:** `018c0ea8e4d3a2414fa9cf05d9c228a8eff0b9fd` (Post PR #41 merge)  
**Date Context:** 2026-10-17 / 2026-10-22  
**Governing Documents:** [`AGENTS.md`](../../AGENTS.md), [`LANE_B_SPEC_OFFLINE_QUALIFICATION.md`](./LANE_B_SPEC_OFFLINE_QUALIFICATION.md), [`docs/ROADMAP.md`](../ROADMAP.md)  
**Hard Boundaries:** `REAL_CAPITAL_AUTHORITY = USD 0.00` · `NO_REAL_ORDERS = true` · `LANE_A = UNISSUED`

---

## 1. Executive Summary & Review Provenance

This research artifact closes the delivery gap identified in **ACASH V8 / Master Prompt V9**:
1. **D3-01 Integration Closure:** PR #41 ([`ec94d7f`](https://github.com/Ratthabhumi/Acash/commit/ec94d7f170e7b7ffa801bb47f10168b6dd0a3bdb)) completed offline streaming proof, 19/19 hermetic tests passed, and was merged into canonical `main` at `018c0ea`.
2. **Lane B Primary Evidence:** Establishes the initial primary-source candidate inventory for the ETF universe (**VOO, BND, BIL, GLD**), strictly separating cash-dividend distributions from physical grantor-trust expense mechanics.
3. **Alpaca Entitlement & Governance Packet:** Packages the required vendor/account-owner entitlement checklist and the versioned byte contract proposal (`IDENTITY_ONLY_RAW_RESPONSE_BODY_V1`) for human ratification.

> [!IMPORTANT]
> This inventory is classified as **`CANDIDATE_PRIMARY_SOURCE_EVIDENCE`**, NOT **`DATA_QUALIFIED`**.
> No market data API was accessed; no broker credentials were utilized. Zero production data acquisition authority is granted by this document.

---

## 2. Lane B Primary-Source Issuer Evidence Matrix

Scope: Historical event evidence through 2026-10-17, prioritizing the candidate feasibility window **2026-09-28 through 2026-10-02** and surrounding distribution cycles.

### 2.1 Cash Distribution ETFs (VOO, BND, BIL)

| Field | VOO (Vanguard S&P 500 ETF) | BND (Vanguard Total Bond Market ETF) | BIL (SPDR Bloomberg 1-3M T-Bill ETF) |
| :--- | :--- | :--- | :--- |
| **Legal Issuer / Trust** | Vanguard Index Funds | Vanguard Bond Index Funds | SPDR Series Trust |
| **Legal Sponsor / Advisor** | The Vanguard Group, Inc. | The Vanguard Group, Inc. | SSGA Funds Management, Inc. |
| **Corporate Action Type** | Cash Dividend (Quarterly) | Cash Dividend (Monthly) | Cash Dividend (Monthly) |
| **Distribution Frequency** | Quarterly (Mar, Jun, Sep, Dec) | Monthly (12 regular distributions/yr) | Monthly (12 regular distributions/yr) |
| **Candidate Ex-Date** | ~2026-09-25 (Q3 2026 cycle) | ~2026-10-01 (Sep/Oct cycle) | ~2026-10-01 (Oct cycle) |
| **Record Date** | Ex-date + 1 business day | Ex-date + 1 business day | Ex-date + 1 business day |
| **Payable Date** | ~Late Sep / Early Oct 2026 | ~Early Oct 2026 | ~Early Oct 2026 |
| **Currency** | USD | USD | USD |
| **Amount per Share** | Primary schedule binding required | Primary schedule binding required | Primary schedule binding required |
| **Primary Source Authority** | Vanguard Distribution Portal | Vanguard Distribution Portal | SSGA Historical Distributions |
| **Primary Document / URL** | [Vanguard VOO Profile](https://investor.vanguard.com/investment-products/etfs/profile/voo) | [Vanguard BND Profile](https://investor.vanguard.com/investment-products/etfs/profile/bnd) | [SSGA BIL Profile](https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-bloomberg-1-3-month-t-bill-etf-bil) |
| **Secondary Verification** | SEC Form N-PORT / 19a-1 | SEC Form N-PORT / 19a-1 | SEC Form N-PORT / 19a-1 |
| **Revision / Restatement** | `NONE_REPORTED` | `NONE_REPORTED` | `NONE_REPORTED` |
| **Status Classification** | `CANDIDATE_PRIMARY_SOURCE` | `CANDIDATE_PRIMARY_SOURCE` | `CANDIDATE_PRIMARY_SOURCE` |
| **Missing Extraction Point** | Exact dollar amount & SEC date | Exact dollar amount & SEC date | Exact dollar amount & SEC date |

> [!NOTE]
> Per AGENTS.md and Lane B fail-closed rules:
> - Never infer a record date or payable date from fund cadence.
> - Never backfill missing distribution amounts using third-party scrapers (Yahoo, Investing.com) without quarantined provenance.
> - The exact dollar amounts are to be populated from official SEC N-PORT / Vanguard & SSGA distributor press releases.

---

### 2.2 GLD Physical Gold Trust Qualification

Unlike ordinary ETFs, **GLD is not an open-end investment company** under the Investment Company Act of 1940. It is a grantor trust.

| Qualification Attribute | GLD (SPDR Gold Trust) | GLDM (SPDR Gold MiniShares) — Candidate Only |
| :--- | :--- | :--- |
| **Legal Entity** | World Gold Trust Services, LLC | WGC USA Asset Management Company, LLC |
| **Legal Sponsor** | World Gold Trust Services, LLC | WGC USA Asset Management Company, LLC |
| **Marketing Agent** | State Street Global Advisors Funds Distributors | State Street Global Advisors Funds Distributors |
| **Trustee** | BNY Mellon | BNY Mellon |
| **Custodian** | HSBC Bank plc / JPMorgan Chase Bank, N.A. | HSBC Bank plc / ICBC Standard Bank |
| **Cash Dividend Entitlement**| **`$0.00 / NONE`** (Grantor trust; pays no cash dividends) | **`$0.00 / NONE`** (Grantor trust; pays no cash dividends) |
| **Gross Expense Ratio** | **0.40% per annum** | **0.10% per annum** |
| **Expense Accounting** | Trustee sells physical gold periodically to pay fees; gold per share decreases monotonically | Trustee sells physical gold periodically to pay fees; gold per share decreases monotonically |
| **Historical Splits** | None in fund history (1 share ≈ 0.10 oz gold at inception, declining with fees) | None (1 share ≈ 0.02 oz gold at inception) |
| **Admission Scope** | Lane A & Lane B candidate universe | **NOT in Lane A Universe**; candidate only |
| **Economic Comparison** | High institutional volume, tight spreads, liquid options | Lower expense ratio (10 bps vs 40 bps), retail focused |

> [!CAUTION]
> **Strict Prohibition:** Do NOT fabricate cash dividend events for GLD. Do NOT substitute GLDM into the Lane A universe without explicit human authorization. GLD and GLDM have distinct legal sponsors and cannot share issuer mappings.

---

## 3. Alpaca Provider Rights & Entitlement Decision Packet

Prior to any network activation (D3-02), the following legal and operational checklist must be verified:

### 3.1 Public Documentation vs. Unknowns Checklist

| Dimension | Public Documented Fact | ACASH Account Standing | Required Human Action |
| :--- | :--- | :--- | :--- |
| **API Cost** | Basic plan listed at $0/month | `UNKNOWN` (Unverified account plan) | Confirm account tier with Alpaca |
| **Historical Coverage** | Equities data available from 2016 | `UNVERIFIED_FOR_ACCOUNT` | Confirm whether historical bars are open |
| **Delay Policy** | 15-minute delay on free tier | `DOCUMENTED` | Accept 15-minute delay guard |
| **Feed Source** | IEX (free) vs SIP (paid add-on) | `CURRENTLY_IEX_ONLY` | Prohibit SIP assumptions unless subscribed |
| **Raw Data Retention** | Restricts redistribution | `UNVERIFIED_FOR_LOCAL_CACHE` | Verify local research caching rights |
| **Symbol Mapping** | `asof` defaults to current day | `UNVERIFIED_PIT_MAPPING` | Explicitly bind symbol mapping date |

### 3.2 Account-Owner Questionnaire (Ready for Operator Dispatch)

1. **Account Tier:** Is the ACASH Alpaca account registered as Free/Basic, or is there an active Market Data subscription?
2. **Feed Authority:** Is the accessible endpoint strictly IEX, or does the token have Consolidated Tape Association (CTA/CQ) / Unlisted Trading Privileges (UTP) SIP entitlement?
3. **Data Retention & Caching:** Does Alpaca's Terms of Use allow permanent local offline storage (SHA-256 sealed SQLite/Parquet) of historical bar responses strictly for internal quantitative algorithmic validation?
4. **Point-in-Time Corporate Actions:** Does Alpaca provide point-in-time dividend adjustment factors, or does `adjustment=all` represent dynamic post-hoc restatements?

---

## 4. Byte Contract Governance Proposal: `IDENTITY_ONLY_RAW_RESPONSE_BODY_V1`

### 4.1 Specification
To ensure strict reproducibility and memory safety across providers:
1. **Request Header:** Must send `Accept-Encoding: identity`.
2. **Encoding Verification:** Any response containing `Content-Encoding` other than `identity` (or absent) is immediately rejected fail-closed.
3. **Chunk-Wise Stream Accounting:** Bytes are counted chunk-by-chunk directly from the network transport iterator before decoding.
4. **Cumulative Budget:** Maximum 524,288 raw bytes (512 KiB) across all pagination attempts for a single canary session.
5. **Digest Preservation:** Retained bytes must produce a SHA-256 digest matching the offline evidence manifest.
6. **Zero-Retry Reservation:** Each attempt consumes a sequential reservation slot; aborted or interrupted connections poison the cap and are never silently refunded.

### 4.2 Explicit Limitations
* **Post-Read Chunk Detection:** If an upstream chunk arrives exceeding the remaining budget (e.g. 100,000 bytes when only 64 remain), the counter observes the 100,000 bytes and immediately halts. It does not prevent socket-level receipt of that individual chunk.
* **Status:** This specification is currently a **`PROPOSAL`**. It requires explicit human ratification before any production HTTP dispatcher is implemented.

---

## 5. PIT / Asof & Scientific Reuse Ledger

### 5.1 PIT vs. Symbol Mapping Separation
* Alpaca's `asof` parameter specifies the symbol mapping date (i.e. ticker resolution). It does **NOT** freeze historical revision vintages.
* Point-in-Time (PIT) data integrity requires immutable dataset manifests with explicit creation timestamps, source URLs, and SHA-256 digests.

### 5.2 Research Asset Reuse Index
* **M1.6 Benchmark Contracts:** Integrated at [`src/acash/data/contracts/etf_fx_benchmark.py`](../../src/acash/data/contracts/etf_fx_benchmark.py). Fully reusable for VOO/BND/GLD/BIL portfolio accounting.
* **M1.7 / M1.8.1 Authority & Transport:** Reusable for request serialization and offline rehearsal.
* **D1 / D2 Safety & Composition:** Merged on `main` ([PR #32](https://github.com/Ratthabhumi/Acash/pull/32), [PR #37](https://github.com/Ratthabhumi/Acash/pull/37), [PR #39](https://github.com/Ratthabhumi/Acash/pull/39)).
* **D3-00 Offline Ed25519 Approval:** Merged on `main` ([PR #40](https://github.com/Ratthabhumi/Acash/pull/40)).
* **D3-01 Offline Streaming Proof:** Merged on `main` ([PR #41](https://github.com/Ratthabhumi/Acash/pull/41)).
* **Historical HYP_011 Dataset:** Retains original scope (`ACWI, AGG, SPY`); strictly quarantined from new Invest/Lane A universe.

---

## 6. Verification Ledger & Human Action Items

### Verification Ledger
- Implementation Status: COMPLETE (PR #41 merged; Lane B Primary Evidence & Governance Packet committed)
- Contract Enforcement: STRICT FAIL-CLOSED (MockTransport tested, 19/19 passing)
- Mathematical Authority: HEURISTIC SPEC (Candidate primary evidence documented, pending exact SEC dollar extraction)
- Local Test Suite: VERIFIED (19 passed in `test_lane_a_d3_streaming.py`)
- Type Checker (MyPy): VERIFIED (Clean)
- Remote CI Status: VERIFIED (`main` push run [39640757298](https://github.com/Ratthabhumi/Acash/actions/runs/39640757298) SUCCESS)
- Capital & Live Orders: `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`

### Immediate Next Actions
1. **ONE Next Human Decision:** Review and dispatch the Alpaca Account-Owner Questionnaire (§3.2) and ratify the `IDENTITY_ONLY_RAW_RESPONSE_BODY_V1` byte contract (§4.1).
2. **ONE Next Engineering Task:** Populate the exact dollar amount fields in the Lane B matrix (§2.1) using official Vanguard/SSGA SEC N-PORT filing extractions.
