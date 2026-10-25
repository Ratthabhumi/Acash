# D6 V36 — Funding, Cost Audit, Tax Scenarios, Attribution, Subperiods: Frozen Spec (2026-10-26)

Status: FROZEN before any V36 run. Label `LOCAL_EXPLORATORY`. Not D5-admitted or
PIT-verified research, not a strategy hypothesis, not tax advice.
`REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`,
`HYP_003 = TERMINALLY_FALSIFIED`. V34/V35 documents and results stay unchanged
as dated baselines.

## 0. Inputs

- Primary dataset `data/local_research/v36/reconciled_max` (git-ignored). It is
  rebuilt with the reconcile script from `v33/max` plus the SSGA BIL file plus
  [`bnd_capital_gain_reclassification_v36.csv`](evidence/bnd_capital_gain_reclassification_v36.csv).
- Delta vs V34: one label only. BND 2021-12-23 LT capital gain 0.13 changes
  `SECONDARY_INDICATION_ONLY` → `OCC_MEMO_CORROBORATED` (OCC Information Memo
  #49819 via MIAX, payable 2021-12-29). Amounts and dates are unchanged.
  Distributions sha256 is `9885fcb8…`; bars and splits are unchanged (`b86f73a6…`,
  `c9b9d95c…`).
- H.10 Thailand page sha256 `3dc41fe0…` (V35). No provider refetch.
- Engine, timing, contribution rules C0–C3 and the V35 cost rows R0–R7 are as
  frozen in the V35 spec.

## 1. P0 IBKR commission audit (source retrieved 2026-10-25/26)

Facts on the US stocks/ETFs page:

- The table gives a maximum per order of 1% of trade value for both Fixed and
  Tiered (footnotes 4 and 8).
- Footnote 8: when the maximum is below the minimum, the maximum applies. The
  Fixed examples are 100@25 = 1.00, 1000@25 = 5.00 and 1000@0.25 = 2.50.
- Footnote 11 (fractional): "same commission rates as whole share trades, with a
  minimum commission of USD 0.01. For each fractional share trade, you will be
  charged the greater of 1% of the trade value or USD 0.01". Its examples are
  0.5@10 = 0.05 and 0.05@15 = 0.01.
- The general North America notes say "Tiered commissions will be capped at 0.5%
  of trade value". The Canada table shows 0.5%. The US table shows 1%. The page's
  Tiered examples do not render.

The source is irreconcilable without account confirmation, so labelled
interpretations are kept side by side:

| Row | Interpretation |
|-----|----------------|
| R2 | Fixed; fractional = general formula with 1% cap + USD 0.01 floor (V35) |
| R2F | Fixed; any non-integer order charged `max(0.01, 1% × value)` (literal footnote 11) |
| R3 | Tiered ex-venue; 1% cap (V35, US table) |
| R3H | Tiered ex-venue; 0.5% cap (North America note) |
| R3L | R3 + ARCA Opening Auction Limit Order fee 0.0006/share |
| R3M | R3 + ARCA "At the Open" fee 0.0015/share |
| R3R | R3 + ARCA remove-liquidity fee 0.0030/share (marketable order after the open) |

ARCA fees come from the IBKR ARCA exchange fee page (`index.php?f=938`). They
are venue-fee **sensitivities**: the printed daily open does not prove an
executable MOO fill or the routing venue. Venue fees apply to Tiered rows only,
because Fixed includes exchange and clearing fees. They are added per share,
are not capped, and are excluded from the pass-through base. No cent rounding is
applied, since the page states no rounding rule. One order is placed per symbol
per session, so a multiple-fill minimum is never charged twice. Regression: R2,
R3, R4 and R5 must equal the V35 `v35_grid.csv` snapshot on every metric, and any
difference must be explained.

## 2. P1 Funding from Thailand (current published fees; retrospective feasibility only)

Sources retrieved 2026-10-26:

- **KBank K PLUS SWIFT SHAR:** THB 250 per transaction (promotional, 2026-01-01..2026-12-31).
  The KBank partner route does not list investment as a purpose. The page says
  Thai nationals cannot transfer to their own account abroad. Eligibility is
  therefore UNVERIFIED.
- **Bangkok Bank SWIFT BEN:** THB 400. Rate is BBL "Selling Rate – TT". Purpose
  documents are required by the BoT.
- **SCB SWIFT BEN:** THB 550, plus a receiving-bank deduction. The page also
  advertises "no fees" via the SCB EASY app, with scope UNVERIFIED.
- **IBKR funding page:** IBKR is "not responsible for any fees charged by your
  or any other financial institution". A credit period applies.

Model (pure, `src/acash/research/d6/funding.py`):

1. Savings: on each V35 contribution date the investor sets aside
   `THB = USD amount × H.10(date)`. The same THB savings series is used for every
   funding scenario within a C level.
2. Cadence: F1 remits after every saving; F2 after every 3rd; F3 after every 12th,
   counted from the first saving. Unremitted THB stays outside the broker and
   earns nothing.
3. Remittance on its date `t` (H.10 of `t`, or the latest prior rate within 7
   days, so no future rate is used):
   `USD = (THB balance − sender fee) / (H.10 × (1 + spread)) − intermediary fee`,
   rounded down to the cent. The remittance is skipped (balance carried) if the
   result is ≤ 0.
4. The USD is credited to the broker `d` NYSE sessions after `t` (d ∈ {0, 1, 3};
   NYSE sessions proxy business days, hypothetical). It is deployed by the V35
   buy-only rule. USD credited after the window is reported as in-transit.
5. F0 is the V35 frictionless baseline (exact USD amounts, no delay).
   A control row `F1_CTRL` (no fee, no spread, no delay) must reproduce F0 to the cent.
6. Household terminal wealth = broker NAV + in-transit USD + unremitted THB.
   It is valued at the H.10 rate on the last session, with no liquidation cost.
   It is reported in USD and THB. Household THB XIRR uses the identical THB
   savings flows (and the initial USD 1,000 at the H.10 rate on day one) across
   cadences.

Frozen funding rows, applied for each cadence F1/F2/F3:

- fees THB {0, 250, 400, 550} at spread 0.5%;
- fee 400 with spread 0% and with spread 1.0%;
- fee 400 with delay 1 and with delay 3;
- fee 400 with intermediary USD 15.

Spreads and intermediary fees are hypothetical. Each row runs for C1–C3 × the
five portfolios × R2 costs. The comparison is made within a C level only.

## 3. P1 US withholding scenarios (not tax advice)

`D6CostModel.withholding_overrides` gives rates by (symbol, distribution type).

| Row | VOO dividends | BND/BIL ordinary distributions | BND capital-gain legs |
|-----|---------------|-------------------------------|-----------------------|
| W0 | 0 | 0 | 0 (V35 baseline, upper bound) |
| W15 | 15% | 15% | 15% (naive treaty rate on everything) |
| W30 | 30% | 30% | 30% (no treaty documentation, naive) |
| WT_LOW | 15% | 0% (assumes 100% interest-related designation and exemption) | 0% |
| WT_MID | 15% | 15% (no interest-related relief applied) | 0% |
| WT_NOTREATY | 30% | 30% | 0% |

Evidence: Thailand–US treaty dividend article (RD), IRS Pub 515 ("certain
interest-related dividends and short-term capital gain dividends paid by a ...
RIC are exempt from chapter 3 withholding"), and Pub 519. Per-year designation
percentages for BND and BIL are UNVERIFIED, so WT rows are bounds. Thai tax on
remitted foreign income (2024+ rules, foreign tax credit) is NOT computed,
because taxpayer facts are not verified. Run for C0 and C1 × R2 × five portfolios.

## 4. P2 Attribution (accounting, not causal)

Broker identity, exact in Decimal and checked every run:

`NAV_T = initial + contributions + Σ_s price P&L at open_s + Σ_s gross distributions_s − Σ_s withholding_s − slippage − commissions − regulatory fees`

Here price P&L at open is `MV_T,s − Σ buys q×open + Σ sells q×open`; it includes
the split effects that the raw prices carry.

Household identity:

`Household_USD = initial + Σ savings at saving-date H.10 + FX translation − sender fees − FX spread − intermediary − cent rounding + broker P&L`

It must hold within Decimal division precision (|residual| ≤ 1e-18 USD).

Idle broker cash (mean cash share) and awaiting-remittance THB (mean balance) are
reported as exposures, not as P&L components. Attribution is reported for C0
and C1 × {F0, F1/F2/F3 at fee 400, spread 0.5%} × R2.

## 5. P2 Subperiods

Windows 2016–2019, 2020–2022, 2023–2025 and 2016–2025. Each window starts fresh
with USD 1,000 (no carry-over), C0 and C1 (F0), R2 costs, and the V36 dataset.
Reported per window:

- cumulative TWR, session count, annualized TWR (252) with the window length disclosed;
- volatility and max drawdown on the TWR index;
- XIRR (C1 only);
- turnover (Σ traded notional / mean NAV);
- commissions plus regulatory fees;
- ranking by TWR, with ties broken by name.

No bootstrap: a block-bootstrap design would need a frozen block length, and a
single 10-year path gives no independent evidence. It is skipped rather than
reported as a confidence interval.

## 6. Out of scope

New engine, optimizer, dashboard, admitter, live executor, tax filing, homelab,
HYP_003 variants, DSR/PBO.
