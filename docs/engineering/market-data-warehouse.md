# Market-Data Warehouse, Daily Collector and BOT Contracts

Status (2026-11-04): **implemented and exercised with real provider data; not deployed on the Homelab;
raw-bar retention is still gated.** No order, no transfer, `NO_REAL_ORDERS=true`, real capital authority
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
