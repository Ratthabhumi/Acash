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
- **Imputed payable dates:** 101 of them (BIL 38, BND 47, VOO 16), all with ex-dates
  in 2016–2019. For these records Alpaca returns no `payable_date` or `record_date`,
  and `process_date` equals `ex_date`, so it cannot stand in for the payment date.
  The primary run sets payable = ex-date + the largest lag observed for that symbol
  (BIL 7, BND 6, VOO 6 days), labelled per row as `IMPUTED_EX_PLUS_<n>D_MAX_OBSERVED_LAG`.
  No imputed date is labelled as provider-reported. NAV already includes receivables;
  imputation only changes when cash becomes spendable.
- **Same-ex-date pairs:** BND has 4 pairs (8 events) with distinct provider ids
  (2020-12-23, 2021-04-01, 2021-12-23, 2022-04-01). The primary run keeps both
  events of each pair. Whether each pair is two distributions or a provider correction
  is **unverified**; see the sensitivity table.
- **SHA-256 of the V32 local CSVs** (V32 format, provider id appended to the type):
  - `bars_raw.csv` `b86f73a69eff2cb9a81131dfa8b4b6d4cf32979be0a2ffcb8cd5e02058b0ff91`
  - `distributions.csv` `3741f8e0bf89282d8837e68a46fef9faa92890fcda4ffb783201844b459510a3`
  - `splits.csv` `31283918db9d893f71d9434716042d1e5665069b9a0a55d5202f1242ee328fe8`

## V33 data-integrity check (2026-10-25)

- **Raw pages sealed.** The three V32 pages now have a manifest recording SHA-256,
  byte count and pagination chain. It is marked `sealed_after_fetch` with
  `asof_status=UNPINNED_PROVIDER_DEFAULT`; the original request record is unchanged.
  - `bars_page_01.json` 1,081,806 B `17023dd84e81a253ae00dcd86823eac2ba7c6887082a0dc52293382025bcde94`
  - `bars_page_02.json` 6,311 B `b4cbcdc2b64d84f64568d567af19531ac8bdd24b3975f42602124435bb8ccb29`
  - `corporate_actions_page_01.json` 52,401 B `ea4481a389121ddc7a22dfe39650e3480aef33405066c6de6de3ba793d553ee3`
- **Offline re-conversion.** `bars_raw.csv` is byte-identical to V32 (`b86f73a6…`).
  `distributions.csv` and `splits.csv` changed format only. Provider identity is now
  a separate `event_id` column and the type is `DIVIDEND_CASH`.
  - max-lag policy: `c83fc87bb367a9621d58243ae91ae73c113136f0d0130285708f163a003707f0`
  - splits: `c9b9d95cedd8479118b2a0489f665d81f035d790739a56dc7f844fca5001588d`
- **Capital gains (F08).** One additional read-only request was made:
  - `/v1/corporate-actions`
  - types `cash_dividend,capital_gains_distribution,forward_split,reverse_split`
  - `start=2016-01-01`, `end=2026-01-31`. This window filters on `process_date`, so
    the extra month catches late-December ex-dates processed in January.
  - The result was 1 page, 52,401 bytes, **byte-identical** to the V32 page.
  - Alpaca returned **0 capital-gains events** and no event beyond the original 250.
    That is what the provider returned, not a completeness proof: historical
    backfill of this type is UNKNOWN, and the 250 events are not an issuer census.
- **BIL reverse split.** The State Street IRS Form 8937 (BIL, CUSIP 78468R663,
  2017-11-30, 1 new for 2 old) matches the provider's ratio 0.5.
  - Raw bars: close 45.74 on 2017-11-29, open 91.50 on 2017-11-30 (ratio about 2.000).
  - Accounting test `tests/unit/research/test_d6_bil_reverse_split.py`: shares halve,
    NAV is continuous, the pre-split receivable is unchanged and nothing is adjusted
    twice.
- **Recomputed results.** The primary results below were recomputed from the sealed
  raw pages and are **unchanged** from V32 to the cent.

## Sensitivity (same raw bars; labelled assumptions, not broker costs or tax)

The base case is the max-lag policy with 2 bps slippage and regulatory fees. Each row
changes one assumption.

| Scenario | BIL_100 | VOO_100 | VOO_BND_60_40 | 50/30/10/10 | 60/40 vs 50/30/10/10 |
|---|---|---|---|---|---|
| Payable lag = min observed (BIL 3, BND 2, VOO 2 d) | 1218.88 | 3982.17 | 2541.39 | 2565.58 | 50/30/10/10 higher |
| Payable lag = median_low observed | 1218.88 | 3983.32 | 2541.68 | 2565.79 | 50/30/10/10 higher |
| **Payable lag = max observed (primary)** | 1218.88 | 3983.32 | 2541.70 | 2565.80 | 50/30/10/10 higher |
| BND pairs read as corrections (smaller dropped, −4 events) | 1218.88 | 3983.32 | 2537.52 | 2562.62 | 50/30/10/10 higher |
| Zero cost (upper bound) | 1219.16 | 3984.23 | 2542.76 | 2567.06 | 50/30/10/10 higher |
| Slippage 10 bps | 1217.76 | 3979.70 | 2538.45 | 2562.39 | 50/30/10/10 higher |
| Commission 0.005/share, min 1.00 | 1209.65 | 3959.97 | 2507.57 | 2499.66 | **60/40 higher** |
| Withholding 15% scenario | 1183.77 | 3890.03 | 2467.28 | 2499.48 | 50/30/10/10 higher |

- **Payable-date uncertainty interval** across the observed lag range: VOO_100
  3982.17–3983.32, 60/40 2541.39–2541.70, 50/30/10/10 2565.58–2565.80, BIL_100
  unchanged. Rankings are unchanged.
- **Year-end and rebalance boundary.** Only under the max-lag policy is a receivable
  still outstanding at a rebalance execution: 0.20 in BIL_100 and 0.02 in 50/30/10/10.
- **Not robust.** The 60/40 vs 50/30/10/10 gap (about 24 on a 1,000 start) reverses
  under the commission scenario, which penalises the four-fund mix's 40 trades. No
  uncertainty analysis supports calling either one superior.
- Full table with turnover, mean cash share and rank:
  `scripts/run_d6_local_sensitivity.py` (output stays local under `data/`).

## Open research brief (for ChatGPT Research; public documents only, no bulk scraping)

1. **BND same-ex-date pairs.** For 2020-12-23, 2021-04-01, 2021-12-23 and 2022-04-01,
   Alpaca rates are 0.1471819 + 0.1436, 0.0534 + 0.139053, 0.140851 + 0.13, and
   0.138738 + 0.0593. Does Vanguard's published BND distribution history show two
   distributions (e.g. income plus capital gain) or one? Cite the page and state which
   amounts match.
2. **Payable dates for 2016–2019** (101 events: BIL 38, BND 47, VOO 16). Find the
   issuer-published payable dates where a lawful single-page source exists (e.g. the
   fund's distribution history page or annual tax documents). Report the date per
   event, or `NOT_FOUND`.
3. **Capital gains 2016–2025.** Did VOO, BND or BIL pay any capital-gain distribution
   in the period, according to issuer tax documents? Alpaca returned none, and its
   historical backfill of `capital_gains_distribution` is unknown.

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
