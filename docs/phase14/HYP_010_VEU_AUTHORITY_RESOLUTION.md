# HYP_010 R2 VEU Sponsor-Authority Resolution Pass (BLOCK RETAINED)

```text
[AUTHORIZATION: VEU_AUTHORITY_RESOLUTION_PASS (human research handoff)]
[OUTCOME: BLOCKED_VEU_DIVIDEND_AUTHORITY_NO_RECORDS_RETAINED]
[OVERALL_R2: R2_PROVIDER_QUALIFIED_SPONSOR_AUTHORITY_BLOCKED_RETAINED]
```

- **Manifest:** `docs/phase14/manifests/HYP_010_VEU_AUTHORITY_RESOLUTION.json`
- **Starting SHA:** `cd4d7b8b763147e57def53f2c8da6cc2b262181f`
- **Method:** verify each human-supplied lead against primary evidence; qualify
  only exact U.S.-share record-level tuples; no inference, no substitution.

## 1. Current Vanguard U.S. Product Page — Limitation Reproduced

- URL: `https://advisors.vanguard.com/investments/products/veu/...` (fetched
  prior session, HTTP 200, re-verified from saved artifact).
- Embedded string: `"tenYearsMessage":"Use this table to view or export up to
  ten years of distributions for this fund."` — REPRODUCED verbatim.
- Consequence: at Sep 2026 the interactive table cannot supply Mar/Jun 2016
  rows by its own structure. No older rows fabricated. The page's tax-center
  link covers 2025 year-end capital gains only, not a historical archive.

## 2. March 2016 Issuer-Origin Evidence — Amount Verified, Dates Unusable

- Retrieved: `https://www.asx.com.au/asxpdf/20160412/pdf/436gkphsb8vkch.pdf`
  ("Distribution FX Rate Announcement", dated 12 April 2016).
- Local evidence (gitignored): `data/hyp_010/evidence/veu_asx_fx_rate_20160412.pdf`
  SHA-256 `4b0aa5ac3e32306dd3bfcde483436c73e22179dd0a3e157e6313df3ae1b8dbf0`.
- Verified content: announced 14 March 2016, **VEU US$0.148 per unit** for CDI
  holders; AUD conversion + AU payment date 18 April 2016.
- Issuer: Vanguard Investments Australia Ltd, wholly owned subsidiary of The
  Vanguard Group, Inc. — issuer-origin amount evidence ACCEPTED as
  corroboration.
- U.S.-share ex/record/payable dates: ABSENT (FX notice for an already-announced
  distribution; CDI context throughout). NOT substituted.

## 3. June 2016 Issuer-Origin Evidence — Amount Verified, Dates Unusable

- Retrieved: `https://announcements.asx.com.au/asxpdf/20160614/pdf/437w6k5s88djln.pdf`
  ("Final Distribution (VEU, VTS) 2016.06.14").
- Local evidence (gitignored): `data/hyp_010/evidence/veu_asx_final_distribution_20160614.pdf`
  SHA-256 `b5b6af0dfb0114117fb48036d04fc8e501efd0c77fa5e42d833c74ddb84a27c9`.
- Verified content: **VEU US$0.53 per unit**; timetable explicitly for CDI
  holders (Ex 15 JUN 2016 / Record 16 JUN / Payment 14 JUL 2016) with the
  document itself stating US/Australia timezone-settlement differences require
  a separate timetable.
- U.S.-share dates: ABSENT. CDI dates MUST NOT be mapped/translated/shifted
  into U.S. dates. NOT substituted.

## 4. SEC / Other Vanguard U.S. Properties

- SEC EDGAR full-text API check attempted → HTTP 403 (bot protection); no
  evidence obtained either way. N-CSR-family filings report aggregate
  distributions, not per-distribution U.S. ex/record/payable tuples; no
  record-level filing located.
- fund-docs/institutional/personal Vanguard properties: no fixed-source
  machine-readable 2016 distribution artifact identified; undocumented-API
  discovery not pursued (out of fixed-source scope).
- SEC identity (Series/Class/VEU) stands as supplied corroboration only, not
  date authority.

## 5. Adjudication

- Amount evidence (issuer-origin): Mar-2016 $0.148, Jun-2016 $0.53 — CORROBORATED.
- U.S.-share ex-date / record-date / payable-date tuples for Mar/Jun 2016:
  STILL ABSENT from any qualifying sponsor authority.
- Amount-only sources are NOT sufficient where dates are required.
- Verdict: **BLOCKED_VEU_DIVIDEND_AUTHORITY_NO_RECORDS RETAINED**;
  overall **R2_PROVIDER_QUALIFIED_SPONSOR_AUTHORITY_BLOCKED RETAINED**.
- Full historical acquisition: NOT executed. Momentum/performance: NOT computed.
- Paper NOT_AUTHORIZED, live LOCKED, capital $0.00, NO_REAL_ORDERS=true.

## 6. What Would Unblock

A Vanguard-U.S.-official (or SEC-filed record-level) artifact supplying exact
U.S.-share ex-date + record-date + payable-date (+ amount) for the missing
2016 VEU distributions, sealed under separate human research authorization.
Third-party consensus, CDI-date shifting, calendar inference, and D=0 remain
prohibited.
