# D6 Local Exploratory Results — 2016-2025 (2026-10-25)

**Label: LOCAL_EXPLORATORY.** This is retrospective personal research. It is not
D5-admitted, not PIT-verified, not a performance claim and carries no trading
authority. Raw provider data stays local in the git-ignored `data/` tree; only
summary statistics are recorded here.

## Inputs

- **Source:** the owner's Alpaca account, market-data GETs only, fetched on
  2026-10-25. The request used:
  - `/v2/stocks/bars`
  - symbols BIL, BND, GLD, VOO
  - `timeframe=1Day`, `adjustment=raw`, `feed=sip`
  - `start=2016-01-01T00:00:00Z`, `end=2025-12-31T23:59:59Z`
  - `asof` not pinned
  - `/v1/corporate-actions` (cash dividends, forward splits, reverse splits)
- **Pages:** 3 (2 bars, 1 corporate actions). Raw bytes: 1,140,518.
- **Coverage:** 10,056 bars, which is 2,514 NYSE sessions for each of the four symbols.
  No missing sessions. No possible unrecorded splits were flagged.
- **Corporate actions:** 250 cash distributions (BIL 87, BND 123, VOO 40, GLD 0) and
  one split: BIL 1-for-2 reverse split on 2017-11-30 (ratio 0.5).
- **Imputed payable dates:** 101 of them (BIL 38, BND 47, VOO 16). Alpaca returns
  no payable dates for 2016–2019. Each was set to ex-date + the largest lag observed
  for that symbol (BIL 7, BND 6, VOO 6 days) and labelled per row. This only affects
  when a receivable becomes spendable cash; NAV already includes receivables.
- **Same-ex-date pairs:** BND has 4 pairs (8 events) kept as separate provider events
  (2020-12-23, 2021-04-01, 2021-12-23, 2022-04-01). The December pairs look like a
  dividend plus a capital-gain distribution. The April pairs are **unverified**.
- **SHA-256 of the local CSVs:**
  - `bars_raw.csv` `b86f73a69eff2cb9a81131dfa8b4b6d4cf32979be0a2ffcb8cd5e02058b0ff91`
  - `distributions.csv` `3741f8e0bf89282d8837e68a46fef9faa92890fcda4ffb783201844b459510a3`
  - `splits.csv` `31283918db9d893f71d9434716042d1e5665069b9a0a55d5202f1242ee328fe8`

## Run

- Unchanged D6 engine, causal timing `PRIOR_CLOSE_DECISION_NEXT_OPEN`.
- Rebalanced on the first session of each year. Initial construction on 2016-01-05.
- Initial NAV 1,000. Fractional shares.
- Costs: 2 bps adverse slippage, statutory SEC Section 31 and FINRA TAF fees,
  no commission, no withholding.

| Portfolio | Terminal NAV | Total return | Ann. return (252) | Ann. vol (252) | Max drawdown | Net distributions | Reg. fees | Trades |
|---|---|---|---|---|---|---|---|---|
| CASH_NO_TRADE | 1000.00 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00 | 0.00 | 0 |
| BIL_100 | 1218.88 | 21.89% | 2.00% | 0.26% | 0.21% | 219.00 | 0.00 | 9 |
| VOO_100 | 3983.32 | 298.33% | 14.87% | 17.78% | 33.92% | 328.97 | 0.00 | 10 |
| VOO_BND_60_40 | 2541.70 | 154.17% | 9.81% | 10.97% | 21.15% | 335.83 | 0.16 | 20 |
| VOO_BND_GLD_BIL_50_30_10_10 | 2565.80 | 156.58% | 9.91% | 9.27% | 17.94% | 293.07 | 0.26 | 40 |

No orders were skipped.

## Sanity check (external, approximate)

Compounding published S&P 500 calendar-year total returns for 2016–2025 gives about
+296%. VOO_100 shows +298.3%. It starts at the 2016-01-05 open instead of the
2015-12-31 close, and it holds distributions as cash until the next annual
rebalance. The 33.9% drawdown matches the February–March 2020 decline. This is a
plausibility check, not verification.

## Limitations

- Retrospective data, not point-in-time verified, not D5-admitted. Corporate actions
  come from a single provider and are unverified.
- Distributions sit in cash until the next annual rebalance. This cash drag is part
  of the registered rule, not a total-return index.
- Annualized figures use a 252-session convention. Volatility is the sample standard
  deviation of daily simple NAV returns. No DSR, no PBO, no significance testing.
  Five comparators over one shared history are not independent.
- Statutory regulatory fees, not account-verified broker pass-through. Expense ratios
  are already reflected in prices.
- History does not predict future returns. REAL_CAPITAL_AUTHORITY = USD 0.00,
  NO_REAL_ORDERS = true.
