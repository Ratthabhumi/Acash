# V24 External Research Brief (for delegated web research)

**Date:** 2026-10-25
**Status:** `RESEARCH_REQUEST` — questions only; no conclusions are asserted here.
**Boundaries:** No Alpaca requests, no credentials, no subscription purchase, no inquiry sent.
`REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`, Lane A/B `UNISSUED`,
`D5_REAL_DATA_NOT_ADMITTED`.

Each answer must cite the primary source URL, the retrieval date, and the exact quoted
passage. Mark every conclusion `PROVEN`, `PROVEN_WITH_LIMITATIONS`, `UNKNOWN` or `DENIED`.
Public API behavior is not proof of this account's contractual rights.

## R1 — Alpaca rights matrix (P2)

Baseline: `docs/governance/ALPACA_RIGHTS_MATRIX_20261023.md`.

Sources to read first:
- https://docs.alpaca.markets/us/docs/about-market-data-api
- https://docs.alpaca.markets/us/docs/market-data-faq
- https://docs.alpaca.markets/us/v1.1/reference/stockbars
- https://docs.alpaca.markets/us/reference/corporateactions-1
- https://alpaca.markets/support/redistribute-alpaca-api
- Alpaca Customer Agreement / Market Data Agreement (current version and effective date)

Questions:
1. Basic plan: historical US equities/ETF bars since 2016 — exact plan wording and any
   feed restriction (`sip` vs `iex`) for bars older than the recent-data cutoff.
2. Exact recent-data restriction for SIP on Basic (15 minutes or other).
3. Does any agreement permit indefinite local retention of raw API payloads for private
   research? Quote the clause, or record `UNKNOWN`.
4. Derived-data rights: may private research outputs (returns, statistics) derived from
   the data be stored and published without redistributing raw data?
5. Redistribution: exact prohibition scope (raw bars, derived series, charts).
6. Corporate Actions API: confirm the statement that original creation timestamps /
   historical availability at decision time are not guaranteed (affects PIT use).
7. Pagination: confirm symbol-then-timestamp ordering and that `limit` counts bars across
   all symbols (not per symbol).
8. Output: one targeted inquiry text covering only items still `UNKNOWN` (not to be sent).

## R2 — Corporate-action census 2016-01-01 .. 2025-12-31 (P3)

Universe: `VOO`, `BND`, `GLD`, `BIL`. Existing 30-event panel covers roughly
2025-10 .. 2026-10 only and cannot establish coverage for the ten-year window.

For each fund, from issuer primary sources (Vanguard, State Street/SPDR, SPDR Gold Trust):
1. Every cash distribution: ex-date, record date, payable date, amount per share,
   distribution type (income / short-term / long-term capital gain / return of capital).
2. Every split or reverse split, with effective date and ratio.
3. Fund inception date and any ticker/CUSIP change inside the window.
4. Source URL, file/page identity, retrieval date, and whether the source states a
   publication or revision date (vintage). Do not present a live table as a historical
   PIT vintage.
5. Known gaps, issuer revisions, and contradictions between sources.
6. Confirm GLD pays no cash distributions; its expense mechanism (gold sold per share)
   is not a dividend.
7. Expected event-count sanity check per fund per year (e.g. BND/BIL monthly, VOO
   quarterly) and any year where the count deviates.

Deliver as a CSV-ready table plus a source ledger.

## R3 — D6 small-account economics inputs (P5)

1. Historical expense ratios for VOO, BND, GLD, BIL across 2016–2025 with effective dates
   (confirm that ETF prices already reflect expenses, so no second deduction is applied).
2. Alpaca historical commission and fractional-share policy for US ETFs, 2016–2025, with
   dates of change; minimum fractional order notional.
3. Regulatory fees on sells (SEC Section 31 fee rates by period, FINRA TAF) applicable to
   a retail broker account.
4. A documented, citable cash-yield proxy for an uninvested USD cash scenario.
5. Any primary-source guidance on USD/THB conversion cost assumptions for a Thai retail
   investor (scenario input only, not tax advice).

## Return format

Write results to `docs/research/V24_EXTERNAL_RESEARCH_RESULTS_<date>.md` with the source
ledger. Results are inputs to owner decisions; they do not change any authority state.
