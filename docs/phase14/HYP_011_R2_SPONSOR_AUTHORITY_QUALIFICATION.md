# HYP_011 R2 Sponsor Distribution-Authority Qualification (ALL THREE PASS)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_011_R2_PROVIDER_AND_SPONSOR_QUALIFICATION]
[REQUIRED_SCOPE: 2016-01-01 .. 2024-12-31]
[OVERALL_SPONSOR: ALL_QUALIFIED]
```

- **Manifest:** `docs/phase14/manifests/HYP_011_R2_SPONSOR_AUTHORITY_QUALIFICATION.json`
- **Qualification code:** `src/acash/data/qualification/hyp_010_sponsor_authority.py`
  (+ ACWI semiannual branch; HYP_010 quarterly/Feb-Dec rules reused unchanged)
- **No unofficial aggregators. No Yahoo. No inferred distributions. No D=0 inference.**

## 1. SPY — QUALIFIED (Sealed Composite, No Network)

- Sealed MEC-0015 SSGA manifest (33 quarterly through 2024-03-15) PLUS sealed
  HYP_009 2024 supplement (Q2/Q3/Q4 2024) = 36 quarterly records, all with
  ex-date/amount/payable. Reuse satisfies §13 A–F (identity, sponsor-official,
  full coverage, payable complete, hash-verifiable, no forbidden reads).
- Classification: `SPY_DIVIDEND_AUTHORITY_QUALIFIED`.

## 2. AGG — QUALIFIED (Sealed HYP_010 Manifest Reuse)

- Sealed `HYP_010_AGG_ISHARES_DIVIDEND_AUTHORITY.json` (official iShares
  page-embedded dataset): 108 monthly records, Feb–Dec schedule with December
  extra, all payable complete.
- Reuse satisfies the same six conditions; re-qualified through the shared
  module in this session's tests.
- Classification: `AGG_DIVIDEND_AUTHORITY_QUALIFIED`.

## 3. ACWI — QUALIFIED (Official iShares Page Dataset, Fetched This Session)

- Authority: official iShares ACWI fund page embedded distributions table
  (HTTP 200, 1,693,019 bytes; full history to 2008; 39 total records).
- 20 in-scope records covering all 18 halves (2016-H1..2024-H2), ex-date +
  amount + payable (+record) complete; specials accepted as extras.
- Sealed as `docs/research/manifests/HYP_011_ACWI_ISHARES_DIVIDEND_AUTHORITY.json`.
- Classification: `ACWI_DIVIDEND_AUTHORITY_QUALIFIED`.

## 4. Overall Sponsor Classification

SPY PASS + AGG PASS + ACWI PASS → sponsor authority COMPLETE.
Combined with provider PASS →

**`R2_PROVIDER_AND_SPONSOR_AUTHORITIES_QUALIFIED_HISTORICAL_BUILD_NOT_EXECUTED`**
