# V29 Evidence Closure — Decision Packet

Boundaries unchanged: `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`,
`LANE_A = UNISSUED`, `LANE_B = UNISSUED`, `D5_REAL_DATA_NOT_ADMITTED`,
`V2_FORMAL_RATIFICATION = PENDING`, `D5_ADMISSION_TRUST_ANCHORS = EMPTY`,
`HYP_003 = TERMINALLY_FALSIFIED`. No issuer extraction, provider call or communication
was performed.

## 1. Integrity fixes (OFFLINE_TEST_VERIFIED)

| Finding | Result |
|---|---|
| V29-F05 negative cash | Confirmed by fail-first test: a minimum commission larger than a small rebalance sale drove cash below zero. Fix: uneconomic sells are skipped (`UNECONOMIC_SELL_SKIPPED`), unfundable buys are skipped (`INSUFFICIENT_CASH_SKIPPED`), both recorded in `skipped_orders`; per-session `D6_NEGATIVE_CASH` guard; final cash must equal cash rebuilt from the trade and entitlement ledgers. Runs are pure: a failure returns no partial state. Tests: `tests/unit/research/test_d6_v29_cash_integrity.py` |
| V29-F06 census trust | Confirmed overclaim: `CENSUS_COMPLETE_VERIFIED` was reachable from caller strings. Ledger V3: status renamed `CENSUS_CLAIM_STRUCTURALLY_VALID`; evidence binds `cell_year`, requires reviewer ≠ acquisition operator and only `RETRIEVED_NOW_PIT_UNKNOWN` vintage; `assess_census_trust` reaches `SOURCE_BYTES_RECONCILED` only from actual bytes (hash match + exact record re-derivation); identity authentication, independent review and admission are unreachable while D5 trust anchors are empty and no census admission verifier exists. Tests: `tests/unit/data/test_census_trust_v29.py` |

## 2. Issuer sources and terms (OPERATOR_REPORTED, retrieved 2026-10-25)

| Field | VOO / BND (Vanguard) | BIL (State Street) | GLD (World Gold Trust Services) |
|---|---|---|---|
| SOURCE_URL | advisors.vanguard.com product pages, distribution-history export | ssga.com ETF dividend distributions, "SPDR Historical Distributions XLSX" | spdrgoldshares.com/usa/gld |
| TERMS_URL | investor.vanguard.com/terms-conditions | ssga.com/us/en/footer/terms-and-conditions | spdrgoldshares.com/terms-and-conditions |
| PERMITTED_USE (public terms) | personal, informational, noncommercial viewing/downloading | reasonable copies for internal use under conditions | save/print for personal noncommercial use |
| UNKNOWN_RIGHTS | automated export, raw retention, normalization into a research ledger, derived metrics | bulk extraction, normalization, retention | derivative works, publication |
| EARLIEST / LATEST_VERIFIED_EVENT | UNKNOWN / UNKNOWN ("up to 10 years" ≠ verified 2016-01-01 start) | UNKNOWN / UNKNOWN (workbook not opened) | n/a (no cash distributions) |
| ACTUAL_COVERAGE / MISSING_YEARS | UNKNOWN / 2016–2025 all unverified | UNKNOWN / 2016–2025 all unverified | cash: policy only; split: UNKNOWN |
| CAPITAL_GAIN_COVERAGE | UNKNOWN | columns for ST/LT gains exist; values unverified | n/a |
| SPLIT_COVERAGE | UNKNOWN | UNKNOWN | secondary sites report no splits; no issuer/SEC census → UNKNOWN |
| PIT_VINTAGE / PUBLICATION_DATE | UNKNOWN / UNKNOWN | UNKNOWN / UNKNOWN | UNKNOWN / UNKNOWN |

Coverage 2016–2025: 0 of 40 symbol-year cells pass cash + split census. Bulk extraction
is not authorized under the evidence found.

## 3. Rights clarification drafts (not sent; contact details UNKNOWN)

Common text, issuer name substituted:

> May a single-user, noncommercial quantitative research project export historical
> distribution records for [VOO and BND | BIL | GLD], retain the original export privately
> with integrity hashes, normalize event dates and amounts into a local research ledger,
> and use derived results internally without redistributing the underlying records?
> Please identify any retention duration, attribution, automated-access or separate
> license restrictions[, and any official record of share splits for GLD 2016–2025].

Variants: Vanguard (VOO, BND); State Street Global Advisors (BIL); World Gold Trust
Services (GLD, including the split-record clause). Sending requires explicit owner
authorization.

## 4. Alpaca acquisition proposal (UNISSUED)

Public capability (`PUBLIC_DOCUMENTATION_ONLY`): Basic is free, US stocks/ETFs historical
since 2016, latest-15-minute restriction; IEX and SIP are distinct. SIP is the preferred
candidate if entitled; IEX bars are not equivalent to consolidated SIP OHLC. No paid
plan is needed for 2016–2025 daily bars on current evidence.

| Frozen parameter | Proposed value |
|---|---|
| symbols / timeframe | VOO, BND, GLD, BIL / 1Day |
| window | 2016-01-01 .. 2025-12-31 (end inclusivity: UNKNOWN, verify before issuance) |
| adjustments / limit | raw, split / 1000 |
| feed / asof | explicit rights-confirmed feed / explicit frozen date |
| max_requests / max_observed_bytes | 32 / 8,388,608 (proposed) |
| retries / fallback | 0 / forbidden |

Offline budget (`simulate_bars_budget`, 2,514 NYSE sessions, 10,056 bars per
adjustment): 22 requests at the planning floor, 24 requests and 2.5–4.1 MB for 120–200
bytes per bar plus overhead. These are estimates, not measured bytes; the ceiling is
adequate under them.

Human checklist before any issuance: account tier and feed entitlement; verbatim raw
retention and duration; internal derived research; controlling agreement version;
rights after account closure; `end` inclusivity and `asof` symbol-mapping effect;
independent admitter and D5 trust anchor appointed; Lane A authority record signed.

## 5. Source-to-D6 integration contract

| Step | Required evidence | Authority | Existing code | Failure | Allowed classification |
|---|---|---|---|---|---|
| Rights-verified artifact | controlling terms + owner decision | owner / provider | — | stop | none |
| Structural parse | source bytes | code | `parse_census_source_bytes`, `parse_distribution_rows` | `LEDGER_*` | extracted |
| Source authenticity | bytes ↔ SHA-256 ↔ records | code | `assess_census_trust` | `CENSUS_SOURCE_BYTES_MISMATCH` | `SOURCE_BYTES_RECONCILED` |
| Corporate-action coverage | cash + split census per cell | code | `coverage_report`, `require_complete_coverage` | `LEDGER_COVERAGE_INCOMPLETE` | structural claim |
| Independent review | anchored admission record | independent admitter | D5 admission (`lane_b_d5_rehearsal`) | unanchored | none until anchors exist |
| D5 admission | admitted bundle | D5 | `evaluate_d5_real_admission` | not admitted | `D5_REAL_INPUT_ADMITTED` |
| D6 adapter | admitted prices + ledger records | code | `run_d6_portfolio` accepts `EtfDistributionRecord` directly | `D6_*` | descriptive only |
| Evaluation | ratified A1/A2 | owner | D6 metrics | blocked | preregistered descriptive |

No new workflow engine is introduced; the missing piece is an anchored independent
admitter, which is a human appointment, not code.

## 6. D6 A1/A2 ratification packet

| Item | A1 descriptive comparison | A2 causal timing |
|---|---|---|
| Affected section | D6 contract §7 ("stated risk limit") | §3 rebalancing timing, §4 accounting |
| Change | descriptive after-cost comparison; no numeric risk threshold | prior-close decision, next-open execution primary; same-open sizing as sensitivity |
| Conflict check | replaces an undefined threshold; no other section changed | consistent with §3 "only information available at that session"; adds that initial construction occurs at the second admitted session (clarification to disclose) |
| Rationale | avoids a post-hoc threshold | removes knowledge of the open at order time |
| Prohibited post-hoc | adding thresholds after data access; switching primary timing after results | same |
| Approval | dated owner decision record naming A1/A2 file hashes | same |
| If not approved | no empirical D6 run | no empirical D6 run |

Status stays `PROPOSED_UNRATIFIED` for both.

## 7. Status lines

- D7: unwired from D6 by policy; available for future sealed strategy research only.
- HYP_007 correction: additive record; verdict unchanged; impact is an analytical bound,
  not a trade-level rerun.
- Next authorized milestone: owner ratifies A1/A2, confirms provider and issuer rights,
  and appoints an independent admitter; then a bounded, possibly partial, labelled
  acquisition pilot.
