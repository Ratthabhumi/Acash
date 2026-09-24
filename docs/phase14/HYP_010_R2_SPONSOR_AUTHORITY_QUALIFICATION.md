# HYP_010 R2 Sponsor Distribution-Authority Qualification

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_010_R2_PROVIDER_AND_SPONSOR_AUTHORITY_QUALIFICATION]
[REQUIRED_SCOPE: 2016-01-01 .. 2024-12-31]
[OVERALL: R2_PROVIDER_QUALIFIED_SPONSOR_AUTHORITY_BLOCKED]
```

- **Manifest:** `docs/phase14/manifests/HYP_010_R2_SPONSOR_AUTHORITY_QUALIFICATION.json`
- **Qualification code:** `src/acash/data/qualification/hyp_010_sponsor_authority.py`
- **No unofficial aggregators. No Yahoo. No inferred distributions. No D=0 inference.**

## 1. SPY — QUALIFIED (Sealed Composite, No Network)

- Authority: sealed MEC-0015 SSGA manifest (through 2024-03-15) PLUS sealed
  HYP_009 2024 supplement (Q2/Q3/Q4 2024) = 36 quarterly records, all with
  ex-date/amount/payable.
- Workbook cross-check (official SSGA historical-distributions xlsx, fetched
  this session): all 33 overlapping amounts agree (5 display-precision-only
  trailing-zero diffs, economically immaterial).
- Classification: `SPY_DIVIDEND_AUTHORITY_QUALIFIED`.

## 2. BIL — QUALIFIED (Official SSGA Workbook)

- Authority: official SPDR ETF Historical Distributions workbook
  (`spdr-etf-historical-distributions.xlsx`, fetched this session from ssga.com;
  file SHA pinned in the BIL authority manifest).
- 108 in-scope records (Feb–Dec monthly + December extra each year), all with
  payable dates. 33 affirmed-zero-amount months (2016/2020/2021/2022,
  near-zero-rate regimes) accepted as valid D=0 authority with explicit
  `affirmed_zero` flags — records exist with full lineage, not missing data.
- Januarys systematically absent across the full 2007–2026 history: documented
  Feb–Dec schedule, not a scope gap (schedule-contradiction guard armed).
- Sealed as `docs/research/manifests/HYP_010_BIL_SSGA_DIVIDEND_AUTHORITY.json`.
- Classification: `BIL_DIVIDEND_AUTHORITY_QUALIFIED`.

## 3. AGG — QUALIFIED (Official iShares Page-Embedded Dataset)

- Authority: official iShares AGG fund page embedded distributions table
  (full history back to 2003, fetched this session; page SHA pinned).
- 108 in-scope records (Feb–Dec monthly + December extra), all with payable
  dates. Same documented Feb–Dec schedule (zero Januarys in 2003–2026).
- Sealed as `docs/research/manifests/HYP_010_AGG_ISHARES_DIVIDEND_AUTHORITY.json`.
- Classification: `AGG_DIVIDEND_AUTHORITY_QUALIFIED`.

## 4. VEU — BLOCKED (No Obtainable Official Machine-Readable Authority)

- Vanguard VEU page fetched (HTTP 200): interactive fund app only, zero file
  links, zero embedded distribution datasets, zero API endpoints in static HTML.
- The interface states ten-year export availability, so 2016–2019 coverage
  cannot be proven from the current interactive source.
- No unofficial supplementation performed. No VXUS substitution. No inference.
- Classification: `BLOCKED_VEU_DIVIDEND_AUTHORITY_NO_RECORDS`
  (reported as `BLOCKED_VEU_DIVIDEND_AUTHORITY_COVERAGE_GAP` family).
- Historical progression STOPS until Vanguard-official 2016-covering artifacts
  are researched and sealed under separate human authority.

## 5. Overall Sponsor Classification

SPY PASS + BIL PASS + AGG PASS + VEU BLOCKED → sponsor authority INCOMPLETE.
Combined with provider PASS (§17 rule) →

**`R2_PROVIDER_QUALIFIED_SPONSOR_AUTHORITY_BLOCKED`**
