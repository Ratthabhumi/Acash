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

## V100 â€” evidence integrity, BOT calendar scope and research labelling

### Massive: three separate evidence states

The record now distinguishes what was actually observed:

| Field | Value | Meaning |
| --- | --- | --- |
| `PUBLIC_2026_REVISION_OBSERVED` | `true` | an official Terms page dated 2026-11-03 was seen in indexed public content |
| `DIRECT_PAGE_VERSION_CONFLICT` | `true` | a direct fetch also returned the 2025-08-28 revision |
| `EFFECTIVE_ACCOUNT_REVISION_UNVERIFIED` | `true` | the revision governing this account is **not** established |
| `agent_verified_current_revision` | `false` | unchanged on purpose |
| `subscriber_classification_inspected` | `false` | the signed-in plan and subscriber class were not inspected |

Rights were **not** widened: private warehouse only, redistribution denied, no public derived benchmark,
no model training. The record adds the backup exception (an inactive backup may be kept up to 90 days,
but it may not be restored or used once the licence ends) and states that source-specific terms override
Owner authorisation. The existing 26 partitions are preserved while their use remains supported; no
automatic deletion was triggered by an older cached page.

### BOT_HOLIDAYS: narrow scope, caching denied

Amendment 005 adds one provider for one purpose: reading and privately displaying the published Thai
financial-institutions holiday calendar, with the source URL and date. `cache_permitted` and
`retention_policy_verified` stay `null`, so the warehouse refuses to store it, and the calendar is never
used as a US exchange calendar. It does not authorise any other BOT product. With the credential alias
(`BOT_HOLIDAYS â†’ BOT_OTHERS`) and the live-verified contract, its status is now `READY` with
`cache_permitted: false`.

### Research labels

`build_proposal` and the FX decomposition now carry explicit labels, surfaced in the dashboard:

`HYPOTHETICAL_HISTORICAL_BASKET`, `PRICE_RETURN_ONLY`, `CURRENT_WEIGHTS_APPLIED_HISTORICALLY`,
`NOT_TRANSACTION_RECONSTRUCTED`, `NOT_REALIZED_PORTFOLIO_PERFORMANCE`, `BOT_REFERENCE_FX_NOT_EXECUTABLE`,
`PARTIAL_UNIVERSE_RESEARCH`, `EXECUTION_AUTHORITY_NONE`.

The +13.20% THB figure is a fixed-weight basket replayed over historical observations using today's
observed weights. It is not realized portfolio performance: no transaction history, cash flows or
historical positions exist in ACASH yet. `realized_performance` is `false` and
`weights_are_current_not_historical` is `true` in the payload.

### Data integrity (no network)

One offline check over the private warehouse: **26/26 partitions** present, SHA-256 matching the
manifest, **12,531 rows**, `first`/`last` dates matching, source tag `MASSIVE_BASIC`, retention record
present with terms revision `2026-11-03`. The BOT series still holds 142 points and the decomposition
97 sessions, regenerated with `--reuse-series` (zero provider calls).

### Browser acceptance: NOT_RUN

The authenticated matrix could not be executed by the agent. The launcher issues a single-use nonce
(60 s) that is exchanged for an HttpOnly `SameSite=Strict` session cookie; the agent's browser context
cannot inherit that cookie without the nonce being written into a tool call, and the same instruction
set forbids printing the nonce or session value. The gate itself remains verified by contract tests
(unauthenticated requests are rejected; Origin/Host/Cookie checks unchanged), and nothing was weakened
to obtain a session. Marked **NOT_RUN** rather than reported as passing.

## V101 â€” owner evidence, corrected weights, and what remains

### The weight-source defect (silent zero weights)

The panel and the FX decomposition derived weights from a position's `observed_market_value`. `HOOD` has
a quantity and a cost basis but no broker-displayed market value in the 2026-11-02 snapshot, so it was
dropped: the proposal then gave it **weight 0 without saying so**, and the FX decomposition reported
"excluded: HOOD". A zero weight is a silent change to the portfolio that was evaluated.

Fixed with one authority, `acash.invest.research_panel`:

- weights come from the authoritative position rows (`value_local` per pricing currency, quantity x price
  on the valuation date), never from `observed_market_value` and never from a sub-portfolio share;
- a symbol with no qualified value is **excluded with a reason**, not zeroed;
- when the eligible subset is smaller than the portfolio, weights are renormalised **and**
  `weights_renormalised_to_panel: true` is reported.

Offline rebuild (`scripts/research_panel.py`, **0 provider calls**) from the 26 stored partitions:

| Item | Before | After |
| --- | --- | --- |
| Instruments in the proposal | 25, HOOD weight 0 | 25, **HOOD weight 1.96%** |
| Instruments in the FX decomposition | 25, HOOD excluded | **26, no exclusions** |
| USD price return | +10.19% | **+9.06%** |
| FX translation | +2.73% | +2.73% |
| Cross term | +0.28% | **+0.25%** |
| THB result | +13.20% | **+12.04%** |

The earlier +13.20% was therefore distorted by a missing weight; the corrected figure remains a
**hypothetical fixed-weight basket**, not realized performance.

### Dated broker-display observations

`acash.invest.broker_positions` stores a broker screenshot as its own dated capture
(`ACASH_BROKER_POSITION_OBSERVATIONS_V1`):

- it never modifies the snapshot, so `observed_at 2026-11-02T22:41+07` and the 2026-11-02 valuation stay
  truthful;
- there is no quantity, trade or cash field, so a capture cannot create a transaction;
- `displayed_subportfolio_weight` is stored as metadata only. The 2026-11-05 Newwave capture records
  META 6,190.83 / GE 3,637.46 / HOOD 3,401.60 / ACHR 3,338.04 THB and marks
  `subportfolio_rows_complete: false`, because the fifth asset's value was not visible â€” the four visible
  rows imply 20.53% for HOOD, not the displayed 17.21%, which is exactly why a displayed share is never
  reused as a global weight;
- `GE` and `GEV` stay separate securities (distinct rows, distinct FIGIs); a duplicate `security_id` in
  one capture is refused.

### Browser acceptance

The authenticated smoke test (real launcher, one-time sign-in, HTTP 200 with 28 rows, reload 200, a fresh
browser 401) was executed by the Owner against `df3d67d` and is recorded as **BROWSER_SMOKE_PASS**. The
focused UI matrix (search, sorting, narrow viewport, every decision-panel state) was **NOT_RUN** in this
cycle: re-running the login flow was explicitly out of scope, and no repeatable in-repo browser harness
exists yet. Nothing about authentication was weakened to obtain a session.

### Homelab

SSH to `mew@homelab` still times out and the previous Tailscale node (100.116.167.3) is offline, so the
reinstalled host is unqualified: **HOMELAB_WAITING_FOR_TAILSCALE_REENROLLMENT**. No remote command was
attempted and no disk was touched. Re-enrolment and preflight steps live in
`docs/operations/homelab-rebuild-v101.md`.
