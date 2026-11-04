# Market-Data Warehouse, Daily Collector and BOT Contracts

Status (2026-11-04, V99): **implemented, exercised with real provider data, and now permitted to persist
private bars under a bounded retention decision; still not deployed on the Homelab (Ubuntu reinstall pending).** No order, no transfer, `NO_REAL_ORDERS=true`, real capital authority
USD 0.00.

## 1. What exists now

| Component | Module | Behaviour |
| --- | --- | --- |
| Bar warehouse | `src/acash/market_data/warehouse.py` | Partitioned Parquet per symbol, atomic `os.replace`, SHA-256 in the manifest, refuses conflicting duplicates, source/rights/lineage per partition |
| Session index | same | Dates only (no prices), so missing-session detection works even when retention is not permitted |
| Collector | `src/acash/market_data/collector.py` | Per-symbol isolation, checkpoint/resume, request budget, rate-limit pause/retry, access-denied hard stop |
| Daily entry point | `scripts/daily_market_collector.py` | Idempotent pass over the held US universe; writes `data/private/market_warehouse/health.json` |
| Backfill + panel | `scripts/backfill_massive_universe.py` | Bounded Massive range → coverage matrix → existing `research_proposal` engine |
| BOT FX | `providers.BOTReferenceFXProvider` | Live-verified contract (see §4) |
| BOT holidays | `providers.BOTFinancialHolidaysProvider` | Live-verified contract (see §4) |

Reused rather than rebuilt: `MassiveEODMarketDataProvider.historical_daily` (b6c0872), `RateLimiter`,
`urllib_transport` + endpoint allowlist, `research_proposal`, `market_authority` credential stores,
`local_research` (D6). HYP_003/004/007/009/011 evidence and the HYP_011 systemd units are untouched.

## 2. The retention gate (why the Parquet path is still unused)

`storage_permitted(provider_id)` requires **both** `cache_permitted is True` **and**
`retention_policy_verified is True` in the ODR-004 scope entry. `MASSIVE_BASIC` currently records
`cache_permitted: null` and `retention_policy_verified: null` (personal research, display/calculation/
derived attested only).

Consequences, by design:

- `BarWarehouse.commit()` raises `STORAGE_RIGHTS_UNESTABLISHED` — it does not write a partition.
- The collector still completes a real pass and reports coverage; it stores the **session index** (dates,
  `contains_prices: false`) and nothing else.
- The research report persists only **derived** output (coverage, eligibility, proposal) and reports
  `storage_rights: UNESTABLISHED`.
- `--persist` demands durable storage and fails closed.

To turn persistence on, the Owner must record a retention decision in ODR-004 for `MASSIVE_BASIC`
(`cache_permitted`, `retention_policy_verified`, and the retention period). No agent may assert that.

## 3. Real evidence (Massive Basic, 2-year window)

Run: `2024-11-04 → 2026-11-04`, 26 held US securities, 5 requests/minute.

- **26/26 symbols completed, 0 failed, 31 budgeted attempts, 26 provider calls.** The 5 extra attempts are
  limiter refusals: the pass paused 305 s in total rather than dropping a symbol.
- Union calendar: **501 sessions**; 23 symbols fully covered, 3 partially (`CRWV` 403 since 2025-03-28,
  `SPCX` 454, `NASA` 151 since 2026-03-31), 0 missing.
- Aligned panel: **356 sessions, 2025-03-28 → 2026-11-03**, 25 eligible instruments, `NASA` excluded
  (`SESSION_COVERAGE_BELOW_MINIMUM`). `SCBSET50`/`MTS-GOLD` are never requested from a US feed.
- Idempotence check: a second pass for an already-covered range did **0 requests**, 26 skipped,
  `NO_WORK`.

Research output (research only, execution authority `NONE`):

| Strategy | Rank score | Constraints | Hurdle | Selected |
| --- | --- | --- | --- | --- |
| CASH | −0.5000 | satisfied | **not cleared** | no |
| BUY_AND_HOLD | 0.0927 | **not satisfied** | cleared | no |
| EQUAL_WEIGHT | −0.0197 | satisfied | cleared | **yes** |

Chosen policy: 5% modelled cash, 248 in-sample / 107 out-of-sample periods, modelled OOS Sharpe 0.206,
OOS CVaR 95% 0.0411, modelled cost 0.0059, turnover 0.4103, 25 proposed weight changes. The higher raw
score of BUY_AND_HOLD is **not** an endorsement: it violates the portfolio constraints, and a rank score
is not a return.

Caveats that stay attached to the result: price-return basis (no dividend/corporate-action series),
modelled (not observed) brokerage costs, 25 of 28 held instruments, and a provider-default (unpinned)
as-of window.

## 4. BOT contracts — verified against live responses (2026-11-04)

| Product | Verified request | Verified response |
| --- | --- | --- |
| Exchange rates | `GET https://gateway.api.bot.or.th/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/?start_period=&end_period=` | `result.data.data_detail[]` with `period`, `currency_id`, `buying_sight`, `buying_transfer`, `selling`, `mid_rate`; unit "(Baht / 1 Unit of Foreign Currency)" |
| Holidays | `GET https://gateway.api.bot.or.th/financial-institutions-holidays/?year=YYYY` | `result.data[]` with `Date` (ISO) and `HolidayDescription` |

Findings worth keeping:

- The documented `/get` suffix **404s**; the working resource ends with a trailing slash. The gateway's own
  404 body leaked the upstream route, which is how the path was identified.
- The exchange-rate response contains **one row per currency per day** (95 rows for five days); the parser
  filters `currency_id == "USD"` and refuses a payload with no USD row.
- Both use the raw `Authorization` header (no `Bearer`).
- Live values on 2026-11-03: USD/THB weighted-average interbank mid **33.7325**; 2026 has **20** Thai
  financial-institution holidays.
- Reference/average rates are **not** executable brokerage rates, and the Thai calendar is **not** a US
  equity calendar.

Governance state: `BOT_REFERENCE_FX` and `BOT_HOLIDAYS` are now `contract_verified` in the registry, but
neither is in the ODR-004 scope with display/calculation/derived attestations, so both stay unusable for a
portfolio value (`CREDENTIALS_REQUIRED`/`GOVERNANCE_REQUIRED`, then `DISPLAY_RIGHTS_UNVERIFIED`). The
adapter is proven; use is not authorised yet.

## 5. Dashboard

- `ResearchDecisionPanel` (planning tab) reads `GET /api/upi/market/research`, which projects **only**
  derived fields (coverage, eligibility/exclusions, proposal, evaluated strategies, health). Raw bars can
  never reach the browser because they are never stored.
- `marketSession()` renders the US session state and the next change in Bangkok time using IANA zones, so
  the ICT time moves with US daylight saving. Exchange holidays are explicitly `US_HOLIDAYS_NOT_VERIFIED`
  rather than guessed.
- The panel has no order control, carries `execution authority: NONE`, and states that the research does
  not cover the whole portfolio.

## 6. Homelab

See `docs/operations/market-data-collector-homelab.md`. Units exist as templates only:
`acash-market-collector.service` (oneshot, hardened, `EnvironmentFile=/etc/acash/market-data.env`) and
`acash-market-collector.timer` (`Mon..Fri 18:30 America/New_York`, `Persistent=true`).
**NOT deployed, NOT verified**: remote HEAD, disk, services and credentials on `mew@homelab` were not
inspected in this cycle, and no Windows secret was copied.

## 7. Tests

- `tests/unit/market_data/test_market_warehouse.py` — storage gate, idempotent commit, conflicting
  duplicate, invalid bars, dates-only index, coverage gaps, rate-limit pause, per-symbol failure isolation,
  access-denied stop, request budget + resume.
- `tests/unit/invest/test_market_data_refresh.py` — BOT parser (currency filter, unit direction, rate
  limit), holiday parsing/validation, allowlist, research route projection.
- `tests/unit/invest/test_credential_store.py` — POSIX environment store and aliases.
- `dashboard/test/market_session.test.mjs` — DST, after-close, weekend, holiday-unknown.

Full local suite at this commit: 5220 passed, 22 skipped; MyPy clean; dashboard typecheck, tests and build
clean.

## V99 â€” storage right, real persistence, FX, calendar and position rows

### Storage decision and the bug it uncovered

ODR-004 amendment 004 (`ODR_UPI_MARKET_DATA_004_AMENDMENT_004_PRIVATE_STORAGE`) records the Owner's
private, non-commercial storage decision: private warehouse only, no redistribution, no public derived
benchmark, no model training, and **purge within 30 days** of the terms or plan ending. It is an Owner
attestation of a research summary of the 2026-11-03 terms revision, not an agent browse, and the record
says so (`agent_verified_current_revision: false`). Third-party provider and exchange terms still apply.

The first attempt to use it exposed a real defect in this module: `storage_permitted()` read
`doc["state"]` while the ratified record stores `doc["status"]`, so the gate silently refused every
provider â€” which is why V98 reported `UNESTABLISHED`. The gate now reads `status` (falling back to
`state` for old fixtures), and a regression test reads the **repository record** rather than a fixture.

Consequences now in force:

- `BarWarehouse.commit()` persists parts only where the record permits it; Alpaca remains memory-only.
- `purge(reason)` / `scripts/purge_market_data.py` empty the warehouse and write, in `purge_log.json`,
  only counts, the reason and the removed filenames â€” never the data. Dry-run is the default.
- A durable pass (`plan(..., durable=True)`) resumes from partitions, not from the session index; the
  V98 checkpoint could otherwise "remember" a range that was never stored.

### Real persistent run

`scripts/backfill_massive_universe.py --persist` with the same universe and window as V98:

- 26/26 symbols stored, **26 provider calls**, 31 budgeted attempts, 0 failures, `storage_rights: PERMITTED`.
- **26 Parquet partitions** (about 0.6 MB total) with SHA-256, source, adjustment basis, retention terms
  and terms revision in `manifest.json`; the values are decimal strings, never floats.
- A second durable pass over the same window issues **0 requests** (it resumes from the partitions).

### BOT reference FX (bounded, chunked, no fill)

- The reference-rate endpoint refuses a window wider than about a month (HTTP 400 at 91 days), so the
  series is built in **31-day chunks** â€” about 19 requests for two years, inside the 200/hour product limit.
- Observed series: **142 points, 2026-03-31 â†’ 2026-11-03**, 14 weekday gaps. Earlier windows returned no
  rows; that is reported as the series' first date, never back-filled with a proxy.
- Rate orientation is fixed at **THB per USD**, `reference` only, `executable: false`.

### THB decomposition (real numbers)

On the 97 sessions where both prices and an FX rate exist (2026-03-31 â†’ 2026-11-03), constant weights,
daily rebalanced, 25 instruments:

| Term | Value |
| --- | --- |
| USD price return | +10.19% |
| FX translation | +2.73% |
| Cross term | +0.28% |
| **THB return** | **+13.20%** |

`(1 + R_THB) = (1 + R_USD)(1 + R_FX)` holds; the three terms add to the THB return and the residual is
reported (`identity_residual`) rather than hidden. `HOOD` is excluded because no established weight
exists for it â€” an exclusion, not a zero. Sessions without an FX rate are dropped, never forward-filled.

### US calendar

The existing XNYS fixture already carried the 2026 calendar, so nothing was re-transcribed. What was
missing was exposure and use:

- `session_view()` returns the venue state, the next session, the 2026 early closes and both the ET and
  Bangkok times, all derived from the fixture plus IANA zones.
- 2026-11-04 regular session = **21:30 â†’ 04:00 ICT**; 2026-11-26 closed; 2026-11-27 and 2026-12-24
  early close at 13:00 ET (01:00 ICT next day); 2026-12-25 closed. July sessions open at 20:30 ICT.
- The collector prints `NO_SESSION` and makes no request on a non-session date.
- Thai financial-institutions holidays are a separate dataset and are never applied to a US session.

### Position rows and the Holdings table

`evidence_report()` now emits `ACASH_POSITION_ROWS_V1`: one row per held line with account, security,
FIGI/ISIN, instrument type, economic class, quantity, price and currency, qualified value and weight,
cost basis and unrealised P&L with an explicit status, source and valuation date. Rules enforced:

- cash and the unqualified broker residual are **not** rows, so they cannot be counted twice;
- a missing cost basis leaves P&L `null` with `COST_BASIS_NOT_ESTABLISHED`, never zero;
- value-only lines carry `quantity: null` and `price: null`;
- rows are sorted deterministically, so a permuted input produces an identical pack.

Live result for the owner snapshot: **28 rows, 181,818.24 THB = 87.10% of the 208,740.01 THB total best
evidence** (the remainder is cash plus the reconciliation residual, by design).

The dashboard renders these rows in a sortable, searchable, per-account table with expandable
FIGI/ISIN/source details; sorting compares decimal strings, so nothing is converted to floating point.
