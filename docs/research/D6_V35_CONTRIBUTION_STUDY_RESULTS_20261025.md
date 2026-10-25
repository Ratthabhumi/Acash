# D6 V35 Contribution Study — Results (2026-10-25)

Label: `LOCAL_EXPLORATORY` personal research under the frozen
[V35 spec](D6_V35_CONTRIBUTION_STUDY_SPEC_20261025.md). Not a strategy
hypothesis, gate input, or trading authorization.
`REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`.

## Inputs (FACT)

| Input | sha256 |
|-------|--------|
| `v34/reconciled_max/bars_raw.csv` | `b86f73a69eff2cb9a81131dfa8b4b6d4cf32979be0a2ffcb8cd5e02058b0ff91` |
| `v34/reconciled_max/distributions.csv` | `d36c79e4eb3cf265f0728db89a11ab0e843726b4f6aafc31e8cb62ef8be0a2cf` |
| `v34/reconciled_max/splits.csv` | `c9b9d95cedd8479118b2a0489f665d81f035d790739a56dc7f844fca5001588d` |
| `v34/reconciled_min/distributions.csv` (boundary) | `0de2837e0000a8ee0c5e5c7960e6bc76c6db422fe2f928070ce17a875455e7c5` |
| H.10 Thailand page (text, release 2026-10-19) | `3dc41fe0255d50cb14272d645b262023278f2705e84379a26696eaf38d0c5ee1` |

The data files are git-ignored. Window 2016-01-01..2025-12-31, USD 1,000 initial,
119 monthly contributions (2016-02..2025-12).

## Baseline reproduction (FACT)

C0 × R0 terminal NAV equals V34 primary to the cent: CASH 1000.00, BIL_100
1218.88, VOO_100 3983.32, VOO_BND_60_40 2541.70, VOO_BND_GLD_BIL_50_30_10_10
2565.80. Every run passed the engine cash-conservation check and the independent
`reconcile_cash` identity.

## IBKR Pro Fixed, fractional (R2) — TWR / XIRR / costs (FACT)

TWR is annualized over 252 sessions on the flow-neutral index. MaxDD is measured on
the TWR index. XIRR uses ACT/365.

| C | Portfolio | Terminal | Contributed | TWR ann | Vol | MaxDD | XIRR | Mean cash | Comm |
|---|-----------|---------:|------------:|--------:|----:|------:|-----:|----------:|-----:|
| C0 | BIL_100 | 1,215.79 | 0 | 1.98% | 0.26% | 0.21% | 1.97% | 0.88% | 2.69 |
| C0 | VOO_100 | 3,973.85 | 0 | 14.84% | 17.78% | 33.92% | 14.80% | 0.70% | 3.81 |
| C0 | 60/40 | 2,522.68 | 0 | 9.72% | 10.98% | 21.17% | 9.70% | 0.90% | 11.69 |
| C0 | 50/30/10/10 | 2,538.93 | 0 | 9.79% | 9.28% | 17.95% | 9.77% | 0.80% | 15.15 |
| C1 | BIL_100 | 7,997.60 | 5,950 | 1.81% | 0.27% | 0.50% | 2.43% | 0.25% | 70.52 |
| C1 | VOO_100 | 17,139.71 | 5,950 | 14.74% | 17.85% | 33.96% | 15.14% | 0.16% | 69.96 |
| C1 | 60/40 | 12,439.52 | 5,950 | 9.62% | 11.03% | 21.21% | 9.87% | 0.21% | 84.80 |
| C1 | 50/30/10/10 | 12,735.39 | 5,950 | 9.68% | 9.32% | 17.99% | 10.26% | 0.20% | 93.94 |
| C2 | BIL_100 | 14,793.32 | 11,900 | 1.76% | 0.28% | 0.82% | 2.52% | 0.27% | 122.41 |
| C2 | VOO_100 | 30,293.91 | 11,900 | 14.68% | 17.84% | 33.97% | 15.20% | 0.18% | 123.16 |
| C2 | 60/40 | 22,347.24 | 11,900 | 9.56% | 11.03% | 21.21% | 9.89% | 0.23% | 151.61 |
| C2 | 50/30/10/10 | 22,931.25 | 11,900 | 9.63% | 9.32% | 17.99% | 10.35% | 0.22% | 161.99 |
| C3 | BIL_100 | 35,359.84 | 29,750 | 1.88% | 0.27% | 0.55% | 2.68% | 0.30% | 123.80 |
| C3 | VOO_100 | 70,110.21 | 29,750 | 14.77% | 17.84% | 33.97% | 15.34% | 0.22% | 126.68 |
| C3 | 60/40 | 52,220.24 | 29,750 | 9.55% | 11.03% | 21.22% | 9.97% | 0.27% | 257.55 |
| C3 | 50/30/10/10 | 53,602.18 | 29,750 | 9.59% | 9.32% | 18.00% | 10.45% | 0.25% | 315.15 |

CASH_NO_TRADE ends at exactly initial + contributions in every cell. The full
8-row cost grid, the skipped-order counts and the per-run CSV are produced by
`scripts/run_d6_contribution_study.py` into the git-ignored `data/local_research/v35/`.

## Cost sensitivity, 60/40 TWR annualized (FACT)

| Row | C0 | C1 | C2 | C3 |
|-----|----|----|----|----|
| R1 zero cost (upper bound) | 9.81% | 9.88% | 9.87% | 9.86% |
| R0 V34 primary (2 bps + reg. fees) | 9.81% | 9.87% | 9.86% | 9.85% |
| R3 IBKR Tiered ex-venue, fractional | 9.76% | 9.66% | 9.68% | 9.75% |
| R2 IBKR Fixed, fractional | 9.72% | 9.62% | 9.56% | 9.55% |
| R6 IBKR Fixed, fractional, 10 bps | 9.71% | 9.59% | 9.53% | 9.51% |
| R4 IBKR Fixed, whole shares | 8.37% | 8.16% | 8.42% | 9.40% |
| R5 IBKR Tiered ex-venue, whole | 8.40% | 8.29% | 8.54% | 9.49% |
| R7 0 comm + USD 1 min notional | 9.81% | 9.87% | 9.86% | 9.85% |

## Whole-share NOT_RUN cells (FACT)

These cells raise `D6_SPLIT_CASH_IN_LIEU_UNSUPPORTED` at the BIL 2017 reverse
split, so the cash-in-lieu price remains unverified:

- BIL_100: R4 and R5 under C0 and C1; R4 under C2.
- 50/30/10/10: R4 and R5 under C1.

## Ranking stability (FACT)

Portfolios are ranked by TWR, with ties broken by name. The reference order
(C0/R0) is VOO_100 > 50/30/10/10 > 60/40 > BIL_100 > CASH, and it holds in
every fractional cell (R0–R3, R6, R7 × C0–C3). Reversals occur only in
whole-share cells: 60/40 overtakes 50/30/10/10 in C0/R4, C0/R5, C3/R4 and C3/R5.
In C1/R4–R5 the 50/30/10/10 cell is NOT_RUN, and in C2/R4–R5 there is no
reversal.

## Payable-lag boundary (FACT)

For R2, max-lag minus min-lag terminal NAV ranges from −2.99 to +1.15 USD
across all cells (largest: C3 VOO_100, about 0.004% of terminal). The 63
remaining imputed payable dates are not material under monthly deployment.

## THB view (R2; H.10 noon rates; FACT for the arithmetic, HYPOTHETICAL spreads)

THB XIRR is 1.1–1.6 percentage points below USD XIRR for every portfolio at zero
spread. Example: C1 60/40 is 9.87% in USD and 8.65% in THB. The cause is THB
appreciation versus USD over the window: H.10 moved from 36.15 on 2016-01-04 to
31.49 on 2025-12-31 THB per USD. Each hypothetical 0.5% spread, applied on
both the funding and the liquidation leg, costs about another 0.1–0.2 pp per
year. All 119+2 flow dates had a published H.10 rate (0 prior-rate uses). Bank
or remittance fees and Thai taxes are not modelled and are not claimed to be
zero.

## Inference (labelled)

- Under IBKR Pro Fixed with fractional shares, each monthly order is charged
  `min($1, 1% of order)`, which is 0.4–1% of the order. Measured as the TWR
  reduction from R1 to R2, 60/40 loses 0.09 pp a year at C0 and 0.26–0.31 pp a
  year at C1–C3. Tiered (ex venue) helps little at C1 (0.22 pp), because orders
  under $35 hit the 1% cap anyway; it helps more at C3 (0.11 pp). Venue fees are
  excluded, so the Tiered figures are a lower bound.
- Whole shares are the dominant friction at small balances. Against R2, 60/40 TWR
  falls by 1.1–1.5 pp a year at C0–C2 and by 0.15 pp at C3, as larger balances
  make share rounding relatively small. Fractional eligibility matters more than
  the choice of commission schedule.
- XIRR exceeds TWR under contributions because more money was invested later in a
  rising market. This is flow timing, not skill.
- Dollar wealth grows with contribution size by construction. The cells are not
  comparable as performance.

## Limitations

- IBKR pricing is a present-day scenario retrieved on 2026-10-25 and applied to
  2016–2025. It is not account-verified. Thailand-resident fractional
  eligibility is unverified, and IBKR Lite is unavailable to non-US residents.
- Tiered rows exclude venue fees. The CAT fee is not modelled. Commission is not
  rounded to cents.
- Slippage is a fixed bps scenario. Opening-auction fills are assumed at the
  printed open.
- No sweep interest is earned on idle cash. No dividend reinvestment program is
  modelled (dividends are deployed with the next contribution or rebalance).
- Issuer-level items are still open: the Vanguard originals for three BND
  capital-gain reclassifications, 63 imputed payable dates (BND 47, VOO 16), and
  the BIL 2017 cash-in-lieu price.
- There is a single historical path. There is no DSR, no PBO and no
  significance claim.

## ChatGPT research brief

1. Does IBKR offer fractional US ETF trading to Thailand-resident IBKR Pro
   individual accounts, and does the 1% cap with a $0.01 floor apply per
   fractional order? Cite IBKR pages.
2. Which typical NYSE Arca opening-auction (MOO) venue fees apply under IBKR
   Tiered for VOO, BND, GLD and BIL? Cite the IBKR exchange-fee tables.
3. What are the current Thai bank THB→USD outward remittance fees and FX spreads
   (e.g., Bangkok Bank, KBank, SCB) for retail investment transfers? What
   intermediary fees does IBKR charge on incoming wires? Cite official fee
   schedules.
4. For Thai tax residents, how are foreign-source dividends and capital gains
   remitted into Thailand taxed (2024+ rules)? What US withholding applies to
   ETF dividends for non-US persons without a treaty rate below 30%? (The
   Thailand–US treaty gives 15%/10%; confirm.)
5. Vanguard BND: find the originals for the 2021-04-01, 2021-12-23 and
   2022-04-01 capital-gain distributions, and the 47 BND / 16 VOO payable dates
   in 2016–2019.
6. BIL 1-for-2 reverse split, 2017: the cash-in-lieu price per fractional share.
