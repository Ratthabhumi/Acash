# D6 V37B — Research Evidence Overlay & Integrity Closure (2026-10-30)

**Governance label:** `LOCAL_EXPLORATORY`. Not investment, legal or tax advice.
`REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`, `LANE_A/B = UNISSUED`,
D5 real admission `NOT_ADMITTED`. The overlay is read-only and is not wired into the D6
engine; no V35–V37A input, NAV or ledger changes.

**Artifacts** (canonical order: `economic_event_id`; LF line endings pinned in `.gitattributes`):
- [v37b_evidence_overlay_20261030.json](evidence/v37b_evidence_overlay_20261030.json) — SHA-256
  `6a93cab9624b2c36731bac4671a3fc589ca370d0a3ad682f27349ac5fd906570` (equals the overlay digest)
- [v37b_evidence_overlay_20261030.csv](evidence/v37b_evidence_overlay_20261030.csv) — same records, same order
- [v37b_proposed_payable_deltas_20261030.csv](evidence/v37b_proposed_payable_deltas_20261030.csv) — header only; no payable date changed

Regeneration (needs the git-ignored local dataset):
`reconcile_provider_distributions(rows, build_v37b_evidence_overlay(rows))` over
`data/local_research/v36/reconciled_max/distributions.csv`, then `export_overlay_to_json` / `export_overlay_to_csv`.

## 1. Integrity closure (supersedes the first PR #70 head `4230d9c`)

Digest lineage: `7500046c…ec8f` (78 records, head `4230d9c`) → `ae2e2c87…20f9` (87 records, head
`bf652f7`, integrity closure) → `6a93cab9…6570` (87 records, primary-source closure in §1A). The integrity
closure corrected these defects:

| Defect in `4230d9c` | Correction |
|---|---|
| Matched counts came from `evidence_class`, not provider rows | `reconcile_provider_distributions` computes every match from provider rows: provider event ID must exist (else `OVERLAY_UNKNOWN_PROVIDER_EVENT_ID`), then symbol, CUSIP/share class when present, ex-date, payable date (when known), component and exact amount. A declared match the data does not support fails with `OVERLAY_CLAIMED_MATCH_UNSUPPORTED`. |
| `MATCHED_ISSUER_DATE` on annual rows without event dates (FY2019, FY2022–2025, QSG rows) | Only event-scope records with a known ex-date and independent event evidence can match. Issuer → `MATCHED_ISSUER_DATE`; OCC → `MATCHED_OCC_EVENT`. |
| FY2021 annual $0.1834 placed on ex-date 2021-12-23 | Annual totals (`ANNUAL_FINANCIAL_TOTAL`) carry no event dates or provider IDs; events are separate `EVENT_FINANCIAL_COMPONENT` records. |
| FY2020/FY2021 totals labelled `QUALIFIED_SHORT_TERM_GAIN` | QSG is allowed only on `TAX_YEAR_DESIGNATION` records (fund-level, no cash). Annual totals and events carry `UNKNOWN` tax character. |
| FY2016–2018 annual rows labelled `CAPITAL_GAIN_LONG_TERM` / `LONG_TERM_CAPITAL_GAIN` | Annual statements do not prove ST/LT designation; now `FINANCIAL_STATEMENT_ANNUAL_TOTAL` with `UNKNOWN` tax character. |
| Publication times `2019-04-24`, `2026-01-01`, `{year+1}-02-01`, OCC `= ex-date` | EDGAR index pages read 2026-10-30: 0000932471-19-006953 accepted `2019-04-25T17:35:43` ET (filed 2019-04-26); 0000794105-26-000106 accepted `2026-04-27T17:36:08` ET (filed 2026-04-28). All others `UNKNOWN`. |
| FY2019 sourced to a filing accepted 2019-04-25 | Impossible (FYE 12-31). Now sourced to 0001683863-21-002757 (§1A). |
| `capture_time = 2026-10-30T11:00:00Z` hard-coded | `UNKNOWN`: no documented capture event exists. Capture before publication is rejected. |
| `RIGHTS_PERMITTED` for public documents | Removed from the schema (`OVERLAY_RIGHTS_PERMITTED_UNSUPPORTED`). Public documents are `RIGHTS_UNVERIFIED`; Vanguard web tables stay `RIGHTS_RESTRICTED`. |
| Exports preserved caller order; test asserted order-dependence | One canonical sort for JSON, CSV and digest; the test asserts byte-identical output under permutation. Duplicate economic events and CUSIP/symbol conflicts are rejected. |
| Payable backlog tagged `ORDINARY_DIVIDEND` | Tax character `UNKNOWN`; component is the provider label. |

### 1A. Primary-source closure (2026-10-30)

Each filing was read directly from EDGAR, using the "Vanguard Total Bond Market Index Fund ETF Shares" financial-highlights table and the "Distributions from Realized Capital Gains" row (3 dp):

| Filing | Accepted (ET) | Columns | ETF-share capital-gain distributions |
|---|---|---|---|
| [0000932471-19-006953](https://www.sec.gov/Archives/edgar/data/794105/000093247119006953/bondindex485bfinal.htm) | 2019-04-25 17:35:43 | FY2014–2018 | 2018 .019 · 2017 .037 · 2016 .036 |
| [0001683863-21-002757](https://www.sec.gov/Archives/edgar/data/794105/000168386321002757/bondindex-20210429.htm) | 2021-04-28 17:37:00 (filed 04-29) | FY2016–2020 | 2020 0.143 · 2019 — · 2018–2016 unchanged |
| [0000794105-26-000106](https://www.sec.gov/Archives/edgar/data/794105/000079410526000106/f45031d1.htm) | 2026-04-27 17:36:08 (filed 04-28) | FY2021–2025 | 2025 — · 2024 — · 2023 — · 2022 .059 · 2021 .183 |

- **FY2020 precision:** OCC components sum to 0.1436, but the filing shows 0.143. FY2016 (0.0357 shown as .036) indicates rounding, yet FY2020 income/total (1.954 / 2.097 against provider 1.95417 / 2.09777) looks truncated. This stays an **unresolved presentation/basis difference**: `ANNUAL_TOTAL_INCONSISTENT` under the unchanged 0.0005 tolerance, with no cash change.
- **FY2016–2018:** these are now `ANNUAL_CLASSIFICATION_DIFFERENCE`. The annual total is reproduced within rounding only after adding the provider row that the provider labels `DIVIDEND_CASH`, so the difference is in classification and no cash differs.
- **[OCC 48045](https://infomemo.theocc.com/infomemos?number=48045)** (memo dated 2020-12-22): LT 0.1064 + ST 0.0372, record 2020-12-24, payable 2020-12-29, CUSIP 921937835.
- **[MIAX/OCC 49819](https://www.miaxglobal.com/sites/default/files/alert-files/BND_Distribution_49819.pdf)** (memo dated 2021-12-22): LT 0.13, record 2021-12-27, payable 2021-12-29.
- OCC describes both memos as unofficial summaries. The memo date is a displayed date, and the time it became available to an automated strategy is UNKNOWN.
- **1042-S supplements TY2020–2024** (read 2026-10-30): the Total Bond Market Index Fund is listed for TY2020 and TY2021 and was not found in the TY2022–2024 text. Each supplement states that 100% of a listed fund's short-term capital-gain distributions for that year are QSG, and refers to year-end statements for amounts. PDF creation metadata (Feb of the following year) is not publication evidence.
- No primary event memo was located for 2016-12-22, 2017-12-26, 2018-04-02, 2021-04-01 or 2022-04-01 (bounded check: memo numbers unknown). These gaps are retained.

## 2. Record inventory (87)

| Scope | Records | Result |
|---|---|---|
| `ANNUAL_FINANCIAL_TOTAL` FY2016–2025 | 10 | 6 consistent within 3-dp rounding (FY2019, FY2021–2025); 3 classification differences (FY2016–2018); 1 inconsistent (FY2020 presentation/basis, 0.0006) |
| `EVENT_FINANCIAL_COMPONENT` (7 BND candidate events, 9 components) | 9 | 3 `MATCHED_OCC_EVENT`; 6 unresolved; 0 conflicts |
| `TAX_YEAR_DESIGNATION` TY2020–2024 | 5 | not a match question; QSG listing fund-level only |
| `EVENT_CASH_ENTITLEMENT` imputed payable backlog | 63 | 0 resolved (BND 47, VOO 16) |

## 3. BND candidate events

| Ex-date | Component (provider) | Amount | Evidence | Result |
|---|---|---|---|---|
| 2016-12-22 | `DIVIDEND_CASH` | 0.0357 | annual FY2016 only | UNRESOLVED |
| 2017-12-26 | `DIVIDEND_CASH` | 0.037 | annual FY2017 only | UNRESOLVED |
| 2018-04-02 | `DIVIDEND_CASH` | 0.01916 | annual FY2018 only | UNRESOLVED |
| 2020-12-23 | ST / LT | 0.0372 / 0.1064 | OCC memo 48045 | MATCHED_OCC_EVENT ×2 |
| 2021-04-01 | ST / LT | 0.0034 / 0.05 | dividend.com (secondary) | UNRESOLVED ×2 |
| 2021-12-23 | LT | 0.13 | MIAX alert relaying OCC 49819 (not Vanguard issuer data) | MATCHED_OCC_EVENT |
| 2022-04-01 | LT | 0.0593 | dividend.com (secondary) | UNRESOLVED |

Real event-level matches: **3 components across 2 economic events**. Zero cash delta is
supported by exact amount identity only for those 3; for 2016–2018 no additional cash
entitlement has been established, which is weaker than a proven zero delta.

## 4. Source index and rights

All annual figures, OCC/MIAX memo terms and 1042-S listings were read from the sources on
2026-10-30 (§1A). Only dividend.com rows remain secondary and were not re-read.

| Source | Acceptance / publication | Rights |
|---|---|---|
| SEC 485BPOS 0000932471-19-006953 | accepted 2019-04-25 17:35:43 ET | RIGHTS_UNVERIFIED |
| SEC 485BPOS 0001683863-21-002757 | accepted 2021-04-28 17:37:00 ET | RIGHTS_UNVERIFIED |
| SEC 485BPOS 0000794105-26-000106 | accepted 2026-04-27 17:36:08 ET | RIGHTS_UNVERIFIED |
| OCC 48045, MIAX/OCC 49819 | memo dates 2020-12-22 / 2021-12-22; time UNKNOWN | RIGHTS_UNVERIFIED |
| Vanguard 1042-S supplements TY2020–2024 | UNKNOWN | RIGHTS_UNVERIFIED |
| dividend.com BND history | UNKNOWN | RIGHTS_UNVERIFIED |
| Vanguard BND/VOO distribution web tables | UNKNOWN | RIGHTS_RESTRICTED |

Rights dimensions: public read access is the only observed property of the public
documents. Internal use, raw-byte retention, automated retrieval, derived-data use and
public redistribution are unverified for every source. SEC public-record status does not
license embedded third-party works. Only URLs and short authored observations are committed.

PIT status: every record is `RETROSPECTIVE_CORROBORATION_ONLY` or `UNAVAILABLE`. No record
establishes contemporaneous availability.

## 5. Verification layers

1. **Executed local-data verification** (this machine, 2026-10-30): the frozen inputs hash to
   the V37A values (bars `b86f73a69eff…0ff91`, distributions `9885fcb8258d…26ca0`, splits
   `c9b9d95cedd8…1588d`). The overlay reconciled against the real 63-imputed-row ledger gives the
   counts in §2, and the committed JSON/CSV are byte-identical to the regenerated output.
2. **Hermetic synthetic verification** (CI): 19 tests on synthetic rows. The two local-data
   tests skip with `LOCAL_DATA_UNAVAILABLE` in CI, so CI does **not** prove the empirical reconciliation.
   Synthetic fixtures mirror the overlay's own claims; they test logic, not the research findings.
3. **Source-document corroboration**: SEC tables, EDGAR acceptance times, OCC/MIAX memos and 1042-S listings were read 2026-10-30 (§1A).
4. **Conclusions**: no NAV, ledger or V35–V37A result changes. Tax character remains a withholding-scenario question (V36 W-rows), not a cash question.

## 6. D7 readiness and next milestone (PROPOSAL)

Existing tooling: `acash.validation.deflated_sharpe` (DSR and HAC variance),
`acash.validation.multiple_testing` (CSCV/PBO), `acash.validation.cpcv`, `acash.portfolio.tournament`.
D7 remains `SCIENTIFICALLY_BLOCKED` for new candidates: it needs PIT data with verified use
rights, prospective capture and a separately ratified hypothesis.

**Proposed next milestone: A — retail funding feasibility.** V36/V37A show that remittance
frictions dominate allocation differences at retail sizes (C1 60/40 household XIRR 8.65% → 5.05% at
monthly 400 THB). The missing inputs are current, quotable facts: which Thai-to-broker routes
are usable, their sender, intermediary and FX costs, and the minimums. These are cheap to obtain and
directly change the owner's funding decision. B (D7 preparation) cannot produce decision value
before PIT data rights exist. Scope of A: dated current quotes kept separate from historical
hypotheticals, and a prospective break-even rule (remit when fixed fee / balance + spread ≤ a
chosen cost ceiling). No re-optimisation of the 2016–2025 path and no new fee grids without new
quotes. This is a proposal only: no D5 admission, no HYP ID.
