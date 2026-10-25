# D6 Local Exploratory Mode — How To Run

Workflow: permitted historical data → local validation → D6 backtest of the five
registered portfolios → Markdown report and NAV CSVs.

## 1. Data you need (put the files under `data/local_research/`, which is git-ignored)

| File | Columns | Notes |
|---|---|---|
| `bars_raw.csv` (required) | `symbol,session,open,close,adjustment` | Daily bars for VOO, BND, GLD and BIL. Prices must be **unadjusted**, with `adjustment=raw` on every row. Use one feed (IEX or SIP) throughout and do not mix them. |
| `distributions.csv` | `symbol,ex_date,payable_date,gross_amount[,distribution_type]` | Cash distributions for VOO, BND and BIL: gross amount per share as of the ex-date. **GLD must have none.** |
| `splits.csv` | `symbol,session,ratio` | Only if a split occurred. The ratio is new shares per old share. |

`distributions.csv` may also carry a `payable_date_source` column. Rows marked
`IMPUTED…` are counted in the report.

Dates are ISO `YYYY-MM-DD`. Without distributions, the income of BND and BIL is
missing, so their results understate return. The report shows the distribution
counts so this is visible.

## 2. Permitted sources (check the current terms yourself before downloading)

- **Bars:** your own Alpaca account, Historical Bars API, `adjustment=raw`, one
  fixed `feed`. Alpaca prohibits redistribution, so keep the data local. Public
  pages do not state a retention period.
- **Distributions and splits:** Alpaca's corporate-actions data from the same
  account, or a manual personal download from the issuer pages (Vanguard for
  VOO/BND, State Street for BIL). The issuer terms allow personal noncommercial
  download but restrict automated bulk access, so do not scrape them. GLD pays no
  cash distributions, so no WGTS data is needed.

## 3. Fetch from Alpaca (optional; uses your own account credentials)

```bash
# one request series per NEW raw directory (bars need an explicit asof)
uv run python scripts/fetch_alpaca_d6_local_data.py fetch --kind bars --feed sip --asof 2026-10-25 --raw-dir data/local_research/raw_bars_v1
uv run python scripts/fetch_alpaca_d6_local_data.py fetch --kind corporate_actions --end 2026-01-31 --raw-dir data/local_research/raw_actions_v1
# offline: verify page digests and pagination chain, then write CSVs to a NEW directory
uv run python scripts/fetch_alpaca_d6_local_data.py convert --bars-raw data/local_research/raw_bars_v1 --actions corporate_actions=data/local_research/raw_actions_v1 --out data/local_research/conv_max --payable-lag-policy max
```

What the script does:

- **Fetch.** Sends read-only market-data GETs only; no trading endpoint is called.
  - No retries and no feed fallback.
  - Limits: at most 32 requests and 8,388,608 response bytes per series.
  - HTTP error bodies and credential values are never printed.
  - Each raw page is written with `raw_manifest.json` (SHA-256, bytes, page tokens).
    An existing raw directory is never overwritten.
- **Corporate-action window.** `start` and `end` filter on `process_date`. Fetch a
  little past the study end; `convert` windows by `ex_date` and lists every excluded
  event in `conversion_manifest.json`.
- **Convert.** Never opens a network connection. It rejects missing, extra or altered
  pages and broken or looping page chains.
- **seal-legacy.** Records digests for pages fetched before manifests existed. It
  keeps their original unpinned-asof status.
- **Missing payable dates.** Alpaca returns none before 2020. Without
  `--payable-lag-policy` the conversion fails. With `min`, `median` or `max`, each one
  becomes ex-date plus that statistic of the symbol's observed provider lags. The row
  is labelled `IMPUTED_EX_PLUS_<n>D_<POLICY>_OBSERVED_LAG`.
- **Event identity.** It is the `event_id` column. `distribution_type` is the economic
  class: `DIVIDEND_CASH`, `SPECIAL_CASH`, `RETURN_OF_CAPITAL_CASH`, `INTEREST_CASH`,
  `CAPITAL_GAIN_LONG_TERM` or `CAPITAL_GAIN_SHORT_TERM`. A capital-gain event with
  both legs becomes two rows, `<id>#long_term` and `<id>#short_term`.
- **Duplicates.** An exact duplicate inside a page is rejected. The same id seen
  twice across fetches must be identical, otherwise it is rejected as a revision.
- **Reconcile (offline).** `scripts/reconcile_d6_local_distributions.py` writes a new
  directory. It splits the cited BND capital gains using
  `docs/research/evidence/bnd_capital_gain_reclassification_v34.csv`, with the cash
  total unchanged. With `--ssga-xlsx`, it matches every BIL event against State
  Street's historical-distributions workbook, a single file you saved yourself under
  `data/`. Issuer payable dates replace imputed ones; any disagreement fails closed.
- **Sensitivity.** `scripts/run_d6_local_sensitivity.py scenarios` compares payable
  policies, the counterfactual "gains were corrections" reading and single cost
  changes. `... grid` runs the fixed V34 cost grid, including whole shares.

## 4. Run

```bash
uv run python scripts/run_d6_local_exploratory.py \
    --bars data/local_research/bars_raw.csv \
    --distributions data/local_research/distributions.csv \
    --start 2016-01-01 --end 2025-12-31 \
    --slippage-bps 2 --regulatory-fees
```

Options:

- `--splits`: path to the splits file.
- `--commission-per-share` and `--commission-minimum`: commission scenario.
- `--withholding-rate`: dividend withholding scenario.
- `--whole-shares`: trade whole shares only.
- `--timing sensitivity`: the idealized same-open sizing. The default is the causal
  rule (decide on the prior close, execute at the next open).
- `--out`: output directory, default `data/local_research/out`.

If no cost flag is given, the cost scenario is labelled `ZERO_COST_UPPER_BOUND`.

Outputs are `report.md`, which contains the input SHA-256 digests, the coverage
table, the results table and any missing inputs, plus one `nav_<portfolio>.csv`
per portfolio that ran.

## 5. What the checks do

- Rejects:
  - a bar on a day that is not an NYSE session (`NyseCa1Calendar`, which covers
    2013–2026);
  - adjusted bars;
  - non-positive, NaN or infinite prices;
  - unparseable dates or numbers;
  - duplicate bars;
  - duplicate events;
  - an ex-date or split date that is not a bar session (otherwise the event would
    be silently dropped);
  - cash distributions for GLD.
- A portfolio missing any official NYSE session in the window is **NOT_RUN**, and its
  exact missing inputs are listed. Nothing is filled in.
- A close-to-next-open move larger than 1.5× in either direction without a split
  row is flagged as a possible unrecorded split. It is not corrected.
- Accounting is the unchanged D6 engine: causal timing, rebalancing on the first
  session of each year, distributions recognised on the ex-date and settled on the
  payable date, no negative cash, and an independent cash reconstruction check.

## 6. Limitations (printed in every report)

- Retrospective data, not point-in-time verified, not D5-admitted.
- Corporate actions are whatever you supplied and are unverified. The report counts
  imputed payable dates and same-ex-date events.
- Years outside 2013–2026 are rejected because the calendar does not cover them.
- Annualized figures use a 252-session convention. Volatility is the sample standard
  deviation of daily simple NAV returns. Neither the DSR nor the PBO is computed.
- Regulatory fees are statutory rates, not your broker's actual pass-through.
  Expense ratios are already reflected in ETF prices.
- A result is a description of history, not evidence of future returns, and it
  carries no trading authority.
