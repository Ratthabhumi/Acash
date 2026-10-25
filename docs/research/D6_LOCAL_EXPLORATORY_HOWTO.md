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
uv run python scripts/fetch_alpaca_d6_local_data.py --feed sip --impute-missing-payable
```

What the fetch does:

- Sends read-only market-data GETs: raw daily bars and corporate actions. No trading
  endpoint is called. There are no retries and no feed fallback, and credential
  values are never printed.
- Saves the raw pages to `data/local_research/raw/` and writes `bars_raw.csv`,
  `distributions.csv`, `splits.csv` and `fetch_manifest.json`.
- `--from-raw` re-converts the saved pages without a network call.
- Alpaca returns no payable dates before 2020. Without `--impute-missing-payable`
  the conversion fails. With the flag, each missing payable date becomes ex-date
  plus the symbol's largest observed lag, and the row is labelled `IMPUTED_EX_PLUS_<n>D`.
- When a symbol has several events on the same ex-date, each one is kept and tagged
  with its provider id.

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
