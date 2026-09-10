# ACASH V5 - FREE DATA SOURCE AUDIT: DOLTHUB / POST-NO-PREFERENCE

**Document ID:** `docs/phase14/free_data_dolthub_source_audit.md`
**Object:** Documentation-only source-feasibility audit of public DoltHub repositories under owner `post-no-preference` (stocks / earnings / rates / options) for the ACASH Free-Data track.
**Status:** `[SOURCE AUDIT]` `[DOCUMENTATION-ONLY]` `[NOT REGISTRATION]` `[NOT EMPIRICAL VALIDATION]` `[NOT BACKTEST]`
**Date:** 2026-09-10

**This is a recommendation/evidence document. It is NOT automatic registration. It modifies NO repository, source registry, or candidate.**

---

## 0. HARD GOVERNANCE BOUNDARY (PRESERVED)

Current canonical state MUST remain unchanged by this audit:

```text
CAND-FREE-MACRO-001 = CONDITIONALLY READY
PRE-REGISTRATION = NOT FULLY FROZEN
EMPIRICAL VALIDATION = NOT AUTHORIZED
BACKTEST = NOT AUTHORIZED
```

Also preserved:

```text
HYP_003 = NOT AUTHORIZED
R1 = NOT AUTHORIZED
ResearchReInceptionGate = NOT INVOKED
TRADING = LOCKED
CAPITAL = $0.00
```

Not modified by this task:

- CAND-FREE-MACRO-001 specification
- MACRO-001 Human Binding Worksheet
- MACRO-001 Decision Surface
- F-1
- HYP_001 / HYP_002 / HYP_003 state
- R1 state
- Phase 5 / Phase 6
- gates, trading, broker, capital
- candidate registry
- `docs/phase14/free_data_research_registry.md`
- `docs/phase14/free_data_source_registry.md`

---

## 1. SAFETY RULE (FOLLOWED)

This task is a **documentation-only source feasibility audit**.

- No large dataset was downloaded or cloned.
- No multi-GB Dolt repository was cloned.
- Only lightweight metadata/schema inspection was performed via the public DoltHub read SQL API (system tables `dolt_log` / `dolt_docs`, `SHOW TABLES`, `SHOW CREATE TABLE`, `SHOW TABLE STATUS`, and small aggregate/row queries with `LIMIT`/`COUNT`).
- Points that could not be answered without downloading data are recorded as `UNVERIFIED`.

Known pre-existing untracked file, intentionally left untouched:

```text
docs/phase14/bootstrap_mechanism_governance_review.md
```

---

## 2. GIT BASELINE (RECORDED AT AUDIT START)

```text
HEAD:                  b022af55ea3c8da688cff445705146f6331704e0
origin/main:           1d7c7ecbc7c248f74bf6c14c4c03a8fdc6994f17
Branch:                main
Working tree:          clean at start (no untracked output)
```

---

## 3. SOURCE SCOPE (FOLLOWED)

Audited exclusively:

```text
post-no-preference/stocks
post-no-preference/earnings
post-no-preference/rates
post-no-preference/options
```

No other DoltHub repository was expanded to. No candidate ideas were created. No additional datasets were introduced into ACASH. Other repositories discovered incidentally would be recorded as `OUT-OF-SCOPE`; none required it.

---

## 4. AUDIT OUTPUT (FOLLOWED)

Exactly ONE new documentation file was created:

```text
docs/phase14/free_data_dolthub_source_audit.md
```

No canonical file with this purpose already existed (verified: no prior `free_data_dolthub_source_audit.md`). No duplicate was created. The Free Data Registry was NOT modified.

---

## 5. SOURCE IDENTITY

All four repositories exist on DoltHub (verified by live API calls on 2026-09-10). Default branch is `master` (not `main`). Each repository also has a secondary auto-generated `docs-*` branch (DoltHub docs/CI artifact; not a data branch).

| Repo | URL | Tables (verified) | Default branch | Documented license | Access method |
|------|-----|-------------------|-----------------|--------------------|----------------|
| `post-no-preference/stocks` | `https://www.dolthub.com/repositories/post-no-preference/stocks` | `symbol`, `ohlcv`, `split`, `dividend` | `master` | CC BY-SA 4.0 (`dolt_docs` > `LICENSE.md`) | Public read SQL API + `dolt clone` |
| `post-no-preference/earnings` | `https://www.dolthub.com/repositories/post-no-preference/earnings` | `earnings_calendar`, `eps_estimate`, `eps_history`, `sales_estimate`, `income_statement`, `balance_sheet_assets`, `balance_sheet_equity`, `balance_sheet_liabilities`, `cash_flow_statement`, `rank_score` | `master` | CC BY-SA 4.0 (`dolt_docs` > `LICENSE.md`) | Public read SQL API + `dolt clone` |
| `post-no-preference/rates` | `https://www.dolthub.com/repositories/post-no-preference/rates` | `us_treasury` | `master` | CC BY-SA 4.0 (`dolt_docs` > `LICENSE.md`) | Public read SQL API + `dolt clone` |
| `post-no-preference/options` | `https://www.dolthub.com/repositories/post-no-preference/options` | `option_chain`, `volatility_history` | `master` | CC BY-SA 4.0 (`dolt_docs` > `LICENSE.md`) | Public read SQL API + `dolt clone` |

Repository description as rendered by DoltHub: generic (`View <owner>'s database <name>`); no custom prose description beyond table/data names was found.

---

## 6. STOCKS AUDIT (`post-no-preference/stocks`)

### Verified schema

`symbol` (24,138 rows): `act_symbol` PK, `security_name`, `listing_exchange`, `market_category`, `is_etf`, `round_lot_size`, `is_test_issue`, `financial_status`, `cqs_symbol`, `nasdaq_symbol`, `is_next_shares`, `last_seen`.

`ohlcv` (29,003,097 rows): PK `(date, act_symbol)`; `open`/`high`/`low`/`close` decimal(14,4); `volume` bigint. Date range observed: `2011-01-03` to `2026-09-08`.

`split`: PK `(act_symbol, ex_date)`; `to_factor`, `for_factor` (decimal(10,5)). Total 4,041 rows.

`dividend`: PK `(act_symbol, ex_date)`; `amount` decimal(10,5). Total 496,467 rows.

Engine-reported table status (uncompressed bytes, approximate engine metadata, not verified download size):

| Table | Rows |
|-------|------|
| `symbol` | 24,138 |
| `ohlcv` | 29,003,097 |
| `split` | 4,041 |
| `dividend` | 496,467 |

### A. Universe

- Exchange distribution observed (from `symbol.listing_exchange`): NASDAQ 11,429; NYSE 6,106; NYSE ARCA 3,833; BATS 2,050; NYSE MKT 716; IEXG 3; CHX 1.
- `is_etf` flag exists (16,829 rows with `is_etf = 0`; ETF rows present).
- Ticker semantics: `act_symbol` (active symbol string). Active-vs-history determination via `last_seen` (see D).

### B. Price

- Daily OHLCV; `date` (date) + `act_symbol` (PK); volume present. Historical depth observed `2011-01-03` (oldest shared-date query boundary) to `2026-09-08`.
- `COUNT(DISTINCT act_symbol)` over full `ohlcv` could not complete within API limits (`UNVERIFIED`).
- Distinct symbols observed in one 2011 week: 3,945; in one 2026 week: 12,950.

### C. Corporate actions

- `split` and `dividend` tables present with ex-date keys and factors/amounts.
- Adjustment semantics in the `ohlcv` series are NOT documented in-repo (no methodology doc).

### D. Survivorship

- `symbol.last_seen` is populated for every row (24,138); observed range `2017-10-26` to `2026-09-05`.
- Delisted-name retention to date: 8,720 rows with `last_seen < 2025-01-01` (observed). Example: `TWTR` present in `symbol` with `last_seen = 2022-10-23`.
- `TWTR` historical OHLCV rows verified present (`2015-06-15`; `2022-10-21`, near delisting) - evidence that at least some post-delisting price history is retained.
- Names delisted/renamed earlier are NOT present in the `symbol` table (probed `SCTY`, `YHOO`, `ERTS`, `LEH` - no rows). `YHOO` also returned 0 rows in `ohlcv` on `2017-06-14`.
- Conclusion: delisted-price coverage is REAL for at least some names, but the `symbol` table does NOT cover the full historical universe. Security identity as a historical universe is `UNVERIFIED`.

### E. PIT

- Dolt version history (commit graph, 2,114 commits on `master`) exists and provides snapshot/diff/reproducibility capability.
- **Dolt versioning != PIT.** Whether the `ohlcv` values reflect as-of historical truth, and whether historical universe membership can be reconstructed PIT-safe, is `UNVERIFIED`. No revision/vintage policy is documented in-repo.

### F. Reproducibility

- Dolt commit hashes, branch/ref addressing, and SQL queryability provide strong reproducibility mechanics (CONDITIONAL/VERIFIED at the infra level).
- Schema reproducibility: schemas stable and addressable per-ref (VERIFIED).

### G. Licensing

- `dolt_docs` > `LICENSE.md` = Creative Commons **Attribution-ShareAlike 4.0 International** (verified header text).
- No separate provenance/addendum file: only `LICENSE.md` (CC BY-SA 4.0) and `AGENT.md` (generic Dolt operations guide) exist in `dolt_docs`. No README, no methodology, no data-provenance, no update-policy, no coverage-policy document exists in-repo.

---

## 7. EARNINGS AUDIT (`post-no-preference/earnings`)

### Verified schema (selected tables)

`earnings_calendar` (117,704 rows): PK `(act_symbol, date)`; `when` (free text). Content of `when` (observed counts): `After market close` 49,666; `Before market open` 38,435; NULL 29,603. Date range `2020-01-22` to `2026-10-16`. Distinct symbols: 7,363.

`eps_estimate` (7,090,000 rows): PK `(date, act_symbol, period)`; `period_end_date`, `consensus`, `recent`, `count`, `high`, `low`, `year_ago`. Earliest `date` observed `2017-10-26`.

`eps_history` (168,659 rows): PK `(act_symbol, period_end_date)`; `reported` decimal(16,2), `estimate` decimal(16,2). `period_end_date` range `2016-07-31` to `2026-07-31`.

`sales_estimate` (7,090,000 rows): similar estimate structure (consensus/count/high/low/year_ago; bigint).

Plus `income_statement` (275,188), `balance_sheet_assets` (288,604), `balance_sheet_equity` (288,949), `balance_sheet_liabilities` (288,947), `cash_flow_statement` (178,847), `rank_score` (1,772,500).

### Findings

- Event date exists, but **release timestamp is only coarse** (`Before market open` / `After market close` / NULL). Actual release time (e.g. HH:MM:SS ET) is `UNVERIFIED`/absent.
- Estimate vs actual: `eps_history` stores `estimate` and `reported` per period. Restatement/revision/vintage semantics: `UNVERIFIED` (no revision columns; no as-published versioning documented).
- Whether `eps_estimate`/`sales_estimate` rows are point-in-time estimate snapshots (as of the given `date`) vs final/current values: `UNVERIFIED` from documentation; the `date`-keyed schema is consistent with snapshot-style storage but this is not proven.
- Survivorship: symbol identity via `act_symbol` (consistent with stocks repo); historical-member reconstruction `UNVERIFIED`.
- Licensing: CC BY-SA 4.0 (verified in `dolt_docs`).
- **Do NOT claim PIT earnings data without source support. None was established.**

---

## 8. RATES AUDIT (`post-no-preference/rates`)

### Verified schema

`us_treasury` (9,165 rows): PK `date`; columns `1_month`, `2_month`, `3_month`, `6_month`, `1_year`, `2_year`, `3_year`, `5_year`, `7_year`, `10_year`, `20_year`, `30_year` (decimal(5,2)).

Date range observed: `1990-01-02` to `2026-09-09` (daily; 9,165 trading-day rows consistent with a long daily par-yield series).

### Findings

- Structure is consistent with the US Treasury Daily Par Yield Curve Rates release (all standard tenors present, decimal percent format). Structure match: VERIFIED at schema level.
- Rate definitions/interpolation methodology document: `UNVERIFIED` (no methodology doc in-repo).
- Revisions / PIT / vintage: `UNVERIFIED`. One value per (date, tenor); no revision marker column.
- Commit cadence observed: daily `us_treasury <date> update` messages at ~23:00 UTC.
- Licensing: CC BY-SA 4.0 (verified in `dolt_docs`).
- Not used for MACRO-001. No macro factors created. No conditional analysis run.

---

## 9. OPTIONS AUDIT (`post-no-preference/options`)

### Verified schema

`option_chain` (117,247,058 rows): PK `(date, act_symbol, expiration, strike, call_put)`; `bid`, `ask` decimal(7,2); `vol` decimal(5,4); `delta`, `gamma`, `theta`, `vega`, `rho` decimal(5,4). Date range observed `2019-02-09` to `2026-09-08`.

`volatility_history` (1,927,553 rows): PK `(date, act_symbol)`; `hv_current`, `hv_week_ago`, `hv_month_ago`, `hv_year_high(_date)`, `hv_year_low(_date)`, `iv_current`, `iv_week_ago`, `iv_month_ago`, `iv_year_high(_date)`, `iv_year_low(_date)`. Date range observed `2019-02-09` to `2026-09-08`.

Sample row (2026-09-08, AAPL, exp 2026-09-23, strike 250): call bid 65.75 / ask 69.15, `vol` 0.6470, delta 0.9670, gamma 0.0016, theta -0.0875, vega 0.0456, rho 0.0999; put bid 0.01 / ask 0.71, `vol` 0.6822, delta -0.0380.

### Findings

- Underlying identifiers: `act_symbol`. Option identity: expiration + strike + call_put.
- Snapshot timestamp: `date` only (no intraday timestamp). **Snapshot semantics (EOD vs intraday; market vs settlement quote) `UNVERIFIED`.**
- `vol` (IV) and Greeks are stored per snapshot; these are computed/derived fields and their methodology is `UNVERIFIED`.
- Historical depth observed from `2019-02-09`.
- Revisions / PIT: `UNVERIFIED`. Do NOT claim historical option-chain PIT integrity merely because the database is version-controlled.
- Licensing: CC BY-SA 4.0 (verified in `dolt_docs`).
- No options analysis, IV/Greeks calculations, P&L, or strategy statistics were performed.

---

## 10. DOLTHUB / DOLT CAPABILITY AUDIT

Evaluated separately from financial-data provenance.

| Capability | Assessment (evidence-based) |
|------------|------------------------------|
| A. Versioning | VERIFIED - commit graph, branches, refs; all four repos commit continuously |
| B. Commit history | VERIFIED - `dolt_log` queryable; e.g. stocks has 2,114 commits, options 2,095, per-dataset daily messages |
| C. Diff capability | VERIFIED (Dolt provides table/row diffs via system tables) - mechanics present |
| D. SQL queryability | VERIFIED - public unauthenticated read SQL API used successfully for all schema/aggregate queries |
| E. Reproducibility | VERIFIED (mechanism) - ref/commit-pinned queries; `UNVERIFIED` at data-vintage level |
| F. Snapshot identification | VERIFIED (mechanism) - commit hashes + branch refs + `dolt_log` |
| G. Schema visibility | VERIFIED - `SHOW CREATE TABLE` / `SHOW TABLES` |
| H. API accessibility | VERIFIED - `GET /api/v1alpha1/{owner}/{db}/{ref}?q=` unauthenticated read; no token required for public repos |
| I. Clone accessibility | VERIFIED (mechanism) - `dolt clone` documented; clone sizes NOT verified in this audit (no clone performed) |
| J. Cost/access | VERIFIED - public read API at $0 observed working; no payment observed |
| K. Reliability/documentation | CONDITIONAL - heavy aggregates sometimes exceeded server limits (timeouts); layer docs generic (`AGENT.md`); per-dataset methodology absent |

**Explicit distinction (mandatory):** DATASET VERSIONING (commit graph + refs, excellent) is NOT SOURCE DATA VINTAGE / PIT TRUTH (whether values equal as-published historical reality, `UNVERIFIED`).

---

## 11. FREE-DATA CLASSIFICATION (PER REPOSITORY)

Question answered: *"Can ACASH responsibly treat this as a free research data source for future work?"* - NOT *"Can this data make money?"*

| Repo | Classification | Primary evidence basis |
|------|---------------|------------------------|
| `stocks` | **CONDITIONAL** | Real daily OHLCV 2011+; delisted price history demonstrated for at least some names (TWTR); but security-master starts 2017, pre-2017 survivorship unproven, PIT unproven, methodology undocumented |
| `earnings` | **CONDITIONAL** | Rich estimate/actual/calendar structure; but release time coarse (BMO/AMC/NULL), vintage/PIT unproven, no revision semantics documented |
| `rates` | **CONDITIONAL** | Clean long daily treasury par-yield table 1990-2026, schema matches official release shape; but rate definitions/vintage/revisions unproven in-repo |
| `options` | **CONDITIONAL** (tightest) | Date-snapshot chain + derived Greeks/IV present 2019+; but snapshot semantics, derived-field methodology, and PIT all UNVERIFIED; very large table |

None approved as `ACCEPT`. None rejected outright. Classification is NOT automatic registration.

---

## 12. REQUIRED DIMENSIONS

Status codes: `VERIFIED` / `CONDITIONAL` / `UNVERIFIED` / `N/A`.

| # | Dimension | Stocks | Earnings | Rates | Options |
|---|-----------|--------|----------|-------|---------|
| 1 | Cost/access | VERIFIED ($0 read API) | VERIFIED | VERIFIED | VERIFIED |
| 2 | Coverage | CONDITIONAL (US equities, active + some delisted) | CONDITIONAL (7,363 symbol-level calendar) | VERIFIED (daily, 1990-2026) | CONDITIONAL (2019+, symbols only) |
| 3 | Historical depth | VERIFIED 2011-2026 daily | VERIFIED 2017-2026 estimates / 2016-2026 actuals | VERIFIED 1990-2026 | VERIFIED 2019-2026 |
| 4 | Data granularity | VERIFIED daily OHLCV | VERIFIED daily snapshot-style | VERIFIED daily | VERIFIED daily-date snapshots |
| 5 | Security identity | VERIFIED `act_symbol` | VERIFIED `act_symbol` | N/A | VERIFIED `act_symbol` |
| 6 | Delisted coverage | CONDITIONAL (evidence for some; not all eras) | CONDITIONAL | N/A | UNVERIFIED |
| 7 | Survivorship | UNVERIFIED (master starts 2017) | UNVERIFIED | N/A | UNVERIFIED |
| 8 | Corporate actions | VERIFIED split/dividend tables; adjustment semantics UNVERIFIED | N/A | N/A | N/A |
| 9 | PIT/vintage | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| 10 | Revision semantics | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| 11 | Timestamp quality | VERIFIED daily date; no intraday | CONDITIONAL (BMO/AMC only, no time) | VERIFIED date | CONDITIONAL (date only, no intraday time) |
| 12 | Source provenance | UNVERIFIED (no doc) | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| 13 | Reproducibility | VERIFIED mechanism / UNVERIFIED vintage | same | same | same |
| 14 | Versioning | VERIFIED (Dolt commit graph) | VERIFIED | VERIFIED | VERIFIED |
| 15 | Schema transparency | VERIFIED | VERIFIED | VERIFIED | VERIFIED |
| 16 | API/query access | VERIFIED | VERIFIED | VERIFIED | VERIFIED |
| 17 | Licensing | VERIFIED CC BY-SA 4.0 (terms: attribution + share-alike; see section 17) | VERIFIED CC BY-SA 4.0 | VERIFIED CC BY-SA 4.0 | VERIFIED CC BY-SA 4.0 |
| 18 | Reliability | CONDITIONAL (API timeouts on heavy scans; Dolt layer stable) | CONDITIONAL | CONDITIONAL | CONDITIONAL |
| 19 | ACASH research relevance | CONDITIONAL - potential OHLCV/CA event source | CONDITIONAL - potential event-data source | CONDITIONAL - potential macro source | CONDITIONAL - potential options/volatility source |
| 20 | Major unresolved blockers | Pre-2017 security master; PIT; adjustment methodology; provenance doc | Release timestamp precision; estimate vintage; PIT | Rate definition/vintage/revision; PIT | Snapshot semantics; derived-field methodology; PIT |

---

## 13. ACASH MAPPING (INFRASTRUCTURE-ONLY)

```text
stocks   -> potential Free Data Track OHLCV + corporate-actions source (infrastructure)
earnings -> potential event-data (earnings calendar / estimates) source
rates    -> potential macro/rates (treasury yields) source
options  -> potential options/volatility source
```

No candidate IDs, no HYP IDs, no mechanisms, no signals were created. Candidate registry unchanged.

---

## 14. MACRO-001 ISOLATION (MANDATORY)

> This audit does not modify CAND-FREE-MACRO-001.
> No DoltHub source is automatically added to MACRO-001.
> No event-window, return definition, baseline, K, IS/OOS, blind period, cost model, statistical protocol, or acceptance criterion is changed.
> MACRO-001 remains CONDITIONALLY READY and empirically unauthorized.

If any of these sources later appears relevant to MACRO-001, it is recorded as **FUTURE DATA OPTION ONLY**; the candidate is not altered.

---

## 15. NO NEW RESEARCH QUESTIONS (FOLLOWED)

This audit did not become anomaly/factor/event/earnings/options/macro/alpha research. Only broad future infrastructure categories are identified (event data, OHLCV, rates, options). No trading strategies proposed.

---

## 16. NO EMPIRICAL CONTENT (FOLLOWED)

This document contains ZERO calculated returns, Sharpe, IC, alpha estimates, p-values, t-statistics, backtest results, performance charts, trade statistics, hypothetical P&L, or signal results. No Python/R/SQL analysis was run against financial datasets. Only metadata/schema inspection and minimal aggregate/identity queries were performed.

---

## 17. LICENSE / LEGAL CAUTION

- Each repository ships a `LICENSE.md` = Creative Commons **Attribution-ShareAlike 4.0 International** (CC BY-SA 4.0). This is an explicit license grant for the licensed material.
- CC BY-SA 4.0 requirements include: attribution when sharing; any adaptation/distribution must be licensed under BY-SA (share-alike); it includes Sui Generis Database Rights; "publicly accessible" does NOT imply "unrestricted commercial use".
- ACASH MUST NOT assume unrestricted commercial/research use. Attribution and share-alike obligations apply when the material or derivatives/adaptations are shared.
- Underlying data provenance (who published / where it was sourced from) is not disclosed in-repo; whether the publisher's upstream data supports the applied license is `UNVERIFIED`.
- This document provides no legal conclusion; Human Governance / legal review is required before any use.

---

## 18. FINAL RECOMMENDATION / OVERALL RANKING

Ranked by: ACASH infrastructure usefulness, data accessibility, reproducibility, provenance, PIT feasibility, survivorship feasibility, licensing clarity. NOT by expected trading performance.

| Rank | Repo | Rationale |
|------|------|-----------|
| 1 | `rates` | Cleanest evidence: long daily official-shaped table, mature 1990-2026 horizon, small footprint, daily commits, low ambiguity |
| 2 | `stocks` | Highest infrastructure value (OHLCV + CA), demonstrated delisted price retention; penalized by security-master start (2017), pre-2017 survivorship gap, PIT/adjustment unproven |
| 3 | `earnings` | Rich estimate/actual structure; penalized by coarse release timing and unproven vintage/PIT |
| 4 | `options` | Useful snapshot chain + derived Greeks; lowest provenance confidence (snapshot semantics, derived fields, PIT all unproven), largest table |

Overall recommendation: **all four CONDITIONAL; candidate registry change NOT recommended yet. A follow-up verification/dedicated registry-integration review is required before any promotion.**

---

## 19. FUTURE AUDIT QUEUE

| Source | Minimum unresolved question to answer before ACASH could use it |
|--------|-----------------------------------------------------------------|
| `stocks` | Delisted/security-history/PIT verification: does `symbol` ever cover pre-2017 eras; is historical universe membership reconstructable PIT-safe; is `ohlcv` split/dividend-adjusted and by what rule |
| `earnings` | Announcement timestamp + vintage verification: is `when`/`date` the actual release time; are estimates point-in-time snapshots; are restatements versioned |
| `rates` | Source/revision/PIT verification: does the series match official US Treasury par-yield as-published; are back-dated values revised |
| `options` | Historical snapshot/PIT verification: at what intraday time/quote are snapshots taken; methodology of `vol`/Greeks; are revisions versioned |

These are NOT resolved in this task (evidence insufficient).

---

## 20. REGISTRY POLICY (FOLLOWED)

`docs/phase14/free_data_research_registry.md` was NOT modified. No source was registered or promoted. The audit recommends further Human Governance review before any canonical registry change. Reason: Human Governance should review this audit before changing the canonical source registry.

---

## 21. FILE SCOPE (FOLLOWED)

Changed in this task:

```text
ONE NEW FILE ONLY: docs/phase14/free_data_dolthub_source_audit.md
```

No source code, no tests, no schema, no registry, no roadmap, no candidate, no governance changes.

---

## 22-25. GIT SAFETY / COMMIT / PUSH (EXECUTED BELOW)

See the execution log at the end of this document (filled in at commit time).

---

## 26. FINAL SAFETY CHECK ITEMS (APPLICABLE)

- [x] No empirical analysis
- [x] No backtest
- [x] No candidate generation
- [x] No HYP creation
- [x] No R1
- [x] No ResearchReInceptionGate
- [x] No MACRO-001 changes
- [x] No F-1 changes
- [x] No Phase5 / Phase6 changes
- [x] No trading / broker / capital changes
- [x] No registry mutation
- [x] No secrets
- [x] No large dataset accidentally downloaded (only metadata/schema queries via API)
- [ ] Only intended audit file staged (verified at commit time)

---

## VERIFICATION LEDGER (this audit)

- Implementation Status: COMPLETE (documentation-only audit; no code, no ingestion)
- Contract Enforcement: STRICT - fail-closed on every PIT/license/provenance claim; nothing promoted to registry
- Mathematical Authority: N/A (no statistical claims made)
- Local Test Suite: NOT RUN (no code changed)
- Type Checker (MyPy): NOT RUN (no code changed)
- Remote CI Status: NOT AVAILABLE (documentation-only convention)
- Methodological Caveats:
  - All coverage/depth figures are observed from live read SQL API queries on 2026-09-10; API may reflect the then-current `master` state.
  - Row counts come from `SHOW TABLE STATUS` (engine metadata) and are approximate.
  - `COUNT(DISTINCT act_symbol)` over full large tables could not complete within server limits (recorded `UNVERIFIED`).
  - Dolt versioning is reproducibility infrastructure, NOT proof of PIT truth.
  - CC BY-SA 4.0 is explicit but imposes attribution/share-alike; no legal conclusion rendered.

---

STOP - SOURCE FEASIBILITY AUDIT COMPLETE. NO REGISTRATION. NO RESEARCH. NO BACKTEST. NO MACRO-001 CHANGES.