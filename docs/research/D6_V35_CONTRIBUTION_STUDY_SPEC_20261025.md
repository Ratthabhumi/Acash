# D6 V35 Contribution Study — Frozen Pre-Execution Specification (2026-10-25)

Status: FROZEN before any V35 run. Label: `LOCAL_EXPLORATORY` personal research.
Not a strategy hypothesis, not a gate input, not paper/live authorization.
`REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.

## 1. Inputs (unchanged from V34)

- Bars: `data/local_research/v34/reconciled_max/bars_raw.csv` (raw, unadjusted;
  sha256 `b86f73a6…`), distributions `d36c79e4…`, splits `c9b9d95c…`
  (git-ignored; hashes printed by the runner).
- Window 2016-01-01 .. 2025-12-31 (NYSE calendar), initial capital USD 1,000.
- Portfolios: the five registered D6 portfolios (no new portfolio, no optimizer).
- Timing: `PRIOR_CLOSE_DECISION_NEXT_OPEN` only (contributions fail closed under
  the idealized same-open sensitivity).

## 2. Contribution scenarios (scenario values, not owner income assumptions)

| ID | USD per month |
|----|---------------|
| C0 | 0 (must reproduce V34 primary to the cent) |
| C1 | 50 |
| C2 | 100 |
| C3 | 250 |

Rules (frozen):

1. A contribution is credited to spendable cash at the **start** of the first
   admitted NYSE session of each calendar month **after** the month of the first
   admitted session (initial-investment month). None after 2025-12-31.
   2016-02 .. 2025-12 gives 119 contributions.
2. Contributions are external flows, recorded in a separate ledger
   (`D6Result.contributions`); they are never distributions or receivables.
3. Deployment is **causal**: the deployment decision is taken at the close of
   the contribution session (cash already present) and executed at the open of
   the next admitted session. No same-open hindsight, no foreknowledge.
4. Deployment is **buy-only**: target add-on per symbol =
   `weight × spendable cash at decision close / close price`, quantized down
   (fractional 0.000001 or whole shares). All spendable cash (contribution,
   carried cash, settled distributions) is eligible; receivables are not.
5. Annual rebalance (first session of each year, decided at prior close) is
   unchanged and takes precedence if a deployment and a rebalance would fall on
   the same session (cannot occur on this calendar; covered by tests).
6. Insufficient funds: buys scale down pro rata so that notional + commission
   never exceeds cash; an unfundable buy is skipped (`INSUFFICIENT_CASH_SKIPPED`).
   No borrowing, no negative cash, no phantom fills.
7. Minimum trade: an order whose notional is below `min_order_notional` is
   skipped (`BELOW_MIN_NOTIONAL_SKIPPED`); its cash is carried. An uneconomic
   sell remains skipped as before.
8. Cash carry: undeployed cash earns nothing (no sweep interest assumed).
9. Reconciliation identity (enforced every run, fail-closed):
   `initial + contributions − buys − buy commissions + sells − sell commissions
   − regulatory fees + settled net distributions = ending cash`.

## 3. Broker cost scenarios (present-day feasibility, NOT historical tariffs)

Source: IBKR "Commissions — Stocks, ETFs and Warrants" page,
<https://www.interactivebrokers.com/en/pricing/commissions-stocks.php>,
retrieved 2026-10-25 (US, IBKR Pro, ≤300,000 shares/month tier). Applied
unchanged to 2016–2025 as a **present-day scenario**; not account-verified;
eligibility of a Thailand-resident account for fractional trading is
UNVERIFIED.

| Field | Pro Fixed | Pro Tiered |
|-------|-----------|------------|
| Per share | 0.005 | 0.0035 |
| Minimum per order | 1.00 | 0.35 |
| Maximum per order | 1% of trade value (overrides minimum, footnote 8) | 1% of trade value |
| Fractional floor | USD 0.01 (footnote 11) | USD 0.01 |
| Third-party fees | Regulatory only | Regulatory + clearing + pass-through + exchange |
| Clearing (NSCC/DTC) | included | 0.00020/share, max 0.5% of trade value |
| NYSE pass-through | included | 0.000175 × commission |
| FINRA pass-through | included | 0.00056 × commission |
| Exchange/venue fees | included | **EXCLUDED (venue-dependent, unverified)** → Tiered rows are a lower bound |

Commission formula (single authority `D6CostModel.commission`):
`max(floor, min(max(minimum, per_share × q), max_rate × notional))`, plus
Tiered clearing `min(clearing_per_share × q, clearing_max_rate × notional)` and
pass-through `rate × base commission`. Regulatory fees reuse
`acash.execution.regulatory_fees` (historical SEC §31 and FINRA TAF schedules;
CAT fee not modelled — at ≤ a few hundred shares per order it is < USD 0.01).
No double charging: Fixed rows set clearing/pass-through to zero.

IBKR Lite (USD 0) is listed only as unavailable for non-US residents per the
same page (footnote 2) and is represented solely by the zero-commission rows.

Predeclared cost grid (applied to every contribution scenario and portfolio):

| Row | Commission | Slippage | Reg. fees | Shares | Min notional |
|-----|------------|----------|-----------|--------|--------------|
| R0 `V34_PRIMARY` | 0 | 2 bps | yes | fractional | 0 |
| R1 `ZERO_COST_UPPER_BOUND` | 0 | 0 | no | fractional | 0 |
| R2 `IBKR_PRO_FIXED_FRAC` | Fixed | 2 bps | yes | fractional | 0 |
| R3 `IBKR_PRO_TIERED_EX_VENUE_FRAC` | Tiered (ex venue) | 2 bps | yes | fractional | 0 |
| R4 `IBKR_PRO_FIXED_WHOLE` | Fixed | 2 bps | yes | whole | 0 |
| R5 `IBKR_PRO_TIERED_EX_VENUE_WHOLE` | Tiered (ex venue) | 2 bps | yes | whole | 0 |
| R6 `IBKR_PRO_FIXED_FRAC_SLIP10` | Fixed | 10 bps | yes | fractional | 0 |
| R7 `ZERO_COMM_MIN_NOTIONAL_1USD_FRAC` | 0 | 2 bps | yes | fractional | 1.00 (hypothetical, Alpaca-like) |

Whole-share rows that hit the BIL 2017 reverse split with an odd holding
report `NOT_RUN` (`D6_SPLIT_CASH_IN_LIEU_UNSUPPORTED`); the cash-in-lieu price
remains UNVERIFIED and is not imputed.

Payable-lag boundary check (only for R2 × C0..C3): `reconciled_min` vs
`reconciled_max` distributions, to test whether monthly deployment makes the
63 remaining imputed payable dates material.

## 4. Metrics (flow-aware; never on flow-contaminated NAV)

- **TWR**: daily `r_t = NAV_t / (NAV_{t−1} + CF_t) − 1` with `CF_t` credited at
  the start of session `t`; index chained from the initial NAV. Annualized
  (252), volatility (252) and max drawdown are computed on the TWR index with
  the existing `local_exploratory` metric definitions. For C0, TWR ≡ V34.
- **XIRR**: ACT/365, flows `−initial`, `−contributions` on their session dates,
  `+terminal NAV` on the last session. Root by bisection on [−0.99, 10];
  fail closed when no sign change (undefined). Reported where defined.
- **Wealth**: terminal NAV, total contributed, net gain = terminal − initial −
  contributions. Dollar wealth is never compared across contribution levels as
  a skill measure.
- **Frictions**: commissions, regulatory fees, slippage cost, trades, skipped
  orders by reason, mean cash share of NAV, terminal uninvested cash.
- **Ranking stability**: rank portfolios by TWR per (C, R) cell; ties broken
  by portfolio name; report reversals versus R0/C0.
- No DSR, no PBO, no significance claims. More VOO exposure ≠ skill.

## 5. USD/THB (P1)

- Source: Federal Reserve Board H.10 historical rates for Thailand
  (<https://www.federalreserve.gov/releases/h10/hist/dat00_th.htm>, noon buying
  rates in New York, THB per USD, release of 2026-10-19; the same series FRED
  publishes as `DEXTHUS`). FRED itself timed out / returned HTTP 500 on
  2026-10-25, so the Board page (text rendering) was stored once in
  `data/local_research/fx/` (git-ignored); sha256 is recorded by the runner.
  `ND` rows are treated as no published rate.
- Translation: each USD flow and the terminal NAV are converted at the H.10
  rate of that date; if H.10 has no rate on an NYSE session, the latest prior
  published H.10 rate within 7 calendar days is used and the count is reported
  (`PRIOR_H10_RATE`); a longer gap fails closed.
  No present-day rate is applied to history.
- Spread scenarios (HYPOTHETICAL, not bank-verified): THB→USD funding spread
  and USD→THB liquidation spread each ∈ {0%, 0.5%, 1.0%}. Bank, remittance and
  wire fees and Thai taxes are NOT modelled (unverified) and are not zero claims.
- Reported for R2 only: THB terminal value, THB contributed, THB XIRR. USD
  performance is never presented as a THB return.

## 6. Out of scope

Governance gates, admitter, signing, dashboard, optimizer, live executor, new
strategy hypotheses, homelab, DSR/PBO, any broker connection.
