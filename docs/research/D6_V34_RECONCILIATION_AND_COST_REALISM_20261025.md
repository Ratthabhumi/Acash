# D6 V34 — Distribution Reconciliation and Cost Realism (2026-10-25)

**Label: LOCAL_EXPLORATORY.** Personal retrospective research; not D5-admitted, not
PIT-verified, no trading recommendation. Parent main `2cfc1d1`. No bars or corporate
actions were fetched again; one issuer workbook was saved locally (see E3).

Labels: **FACT** = measured by executed code; **EVIDENCE** = inspectable source;
**INFERENCE** = reasoned, not directly verified; **HYPOTHESIS** = unproven
explanation; **PROPOSAL** = possible next step.

## 1. Data quality and reconciliation coverage

| Item | Result | Label |
|---|---|---|
| Bars | 10,056, i.e. 2,514 NYSE sessions × 4 ETFs; `bars_raw.csv` `b86f73a6…` unchanged since V32 | FACT |
| Provider cash events | 250 in the provider file, 252 rows after splitting the BND 2020-12-23 and 2021-04-01 gains into two legs each | FACT |
| BIL vs State Street workbook | All 87 provider events match on ex-date and exact amount, with CUSIP 78468R663. The 49 provider payable dates all agree; 38 imputed dates were replaced by issuer dates. No non-zero issuer event is missing from the provider. The 33 issuer rows without a provider event are all $0.000000. | FACT (from E3) |
| Payable dates now | 151 provider, 38 issuer file, **63 still imputed** (BND 47, VOO 16) | FACT |
| BND capital gains | 2020-12-23 0.1436 = 0.1064 LT + 0.0372 ST, payable 2020-12-29 | EVIDENCE E1 (OCC, unofficial summary, not issuer certification) |
| BND 2021-04-01 0.0534, 2021-12-23 0.13, 2022-04-01 0.0593 | Classified as capital gains (0.0034 ST + 0.05 LT; LT; LT) | EVIDENCE E2 (secondary only; Vanguard original not inspected) |
| How Alpaca represents BND gains | As `cash_dividend` rows; the `capital_gains_distribution` type returned nothing for 2016–2025 | FACT plus E1 |
| Double-count guard | Converter rejects a capital gain reported under both types (same symbol, ex-date and total). Reclassified components must sum exactly to the provider amount; each component is one engine entitlement. | FACT (tests) |
| BIL 1-for-2 reverse split 2017-11-30 | Preserved; Form 8937 (V33) | EVIDENCE |

Evidence:

- E1: <https://infomemo.theocc.com/infomemos?number=48045>
- E2: <https://www.dividend.com/etfs/bnd-vanguard-total-bond-market-etf/>
- E3: State Street historical distributions workbook (581,216 B, sha256
  `6b65cbf956b5d25705d08470006a0e97e6a7d2a0d5cfd08b63f6f79783b06320`, Last-Modified
  2026-10-16). Saved once to the git-ignored `data/`; not redistributed.

Reconciled `distributions.csv` (local): `d36c79e4eb3cf265f0728db89a11ab0e843726b4f6aafc31e8cb62ef8be0a2cf`.
The cited BND facts are committed in
`docs/research/evidence/bnd_capital_gain_reclassification_v34.csv`.

## 2. Five portfolio results

Primary setup: reconciled inputs, max-lag imputation for the 63 remaining events, 2 bps
slippage, regulatory fees, fractional shares, causal timing, 2016-01-01..2025-12-31.

| Portfolio | Terminal NAV | Max DD | Change vs V33 |
|---|---|---|---|
| CASH_NO_TRADE | 1000.00 | 0.00% | 0 |
| BIL_100 | 1218.88 | 0.21% | 0 |
| VOO_100 | 3983.32 | 33.92% | 0 |
| VOO_BND_60_40 | 2541.70 | 21.15% | 0 |
| VOO_BND_GLD_BIL_50_30_10_10 | 2565.80 | 17.94% | 0 |

Why nothing changed (FACT, checked rather than assumed):

- **BND relabelling.** It changes labels only; cash amounts and payable dates are
  identical. A test shows the engine's gross distributions are equal before and after.
- **BIL issuer payable dates.** They differ from the imputed dates by −3 to +4 days;
  14 of 38 are later than the max-lag imputation. Only one event spans a year end:
  ex 2016-12-28, imputed payable 2017-01-04, issuer payable 2017-01-06. Both are after
  the 2017-01-03 rebalance, so spendable cash at every execution is identical.
- **Integrity.** The engine's negative-cash guard, cash-reconstruction check and
  causal-timing rules ran on every scenario without error.

## 3. Cost and settlement uncertainty

- **Cost grid.** Fixed before execution. Commission shapes are **hypothetical**, not
  verified current fees of any broker. Execution cost = commissions + regulatory
  fees + slippage.

| Scenario | VOO_100 | 60/40 | 50/30/10/10 | BIL_100 | Rank (excl. cash) |
|---|---|---|---|---|---|
| G0 zero cost, fractional | 3984.23 | 2542.76 | 2567.06 | 1219.16 | VOO > 50/30 > 60/40 > BIL |
| G1 0 comm, 2 bps, fractional | 3983.32 | 2541.70 | 2565.80 | 1218.88 | VOO > 50/30 > 60/40 > BIL |
| G4 0.005/sh min 1, 2 bps, fractional | 3959.97 | 2507.57 | 2499.66 | 1209.65 | VOO > **60/40 > 50/30** > BIL |
| G2 0 comm, 2 bps, whole | 3490.76 | 2238.05 | 1954.36 | NOT_RUN | VOO > 60/40 > 50/30 |
| G3 0 comm, 10 bps, whole | 3490.02 | 2236.41 | 1952.57 | NOT_RUN | VOO > 60/40 > 50/30 |
| G5 0.005/sh min 1, 2 bps, whole | 3489.76 | 2227.17 | 1944.36 | NOT_RUN | VOO > 60/40 > 50/30 |
| G6 1.00 per order, 2 bps, whole | 3489.76 | 2227.17 | 1944.36 | NOT_RUN | VOO > 60/40 > 50/30 |

FACT, from the grid:

- **Execution costs.** At most 0.69 over ten years under G1. Under G4 they rise to
  20.57 for 60/40 and 38.66 for 50/30/10/10 (40 orders, mostly $1 minimums), with 2
  orders skipped as uneconomic.
- **Whole shares** cut terminal NAV by about 12% (VOO, 60/40) and about 24%
  (50/30/10/10). Mean idle cash rises to 10.2%, 14.2% and 28.6%: at $1,000, the
  10% GLD and BIL sleeves buy at most one or two shares.
- **G5 = G6.** At these quantities the per-share charge never exceeds the $1
  minimum.
- **BIL_100 with whole shares is NOT_RUN.** An odd BIL holding at the 1-for-2 split
  leaves a fractional share paid as cash in lieu, at a price the data does not
  contain; the engine fails closed. 50/30/10/10 ran only because it held an even
  number of BIL shares (2).

Settlement uncertainty (FACT, scenarios mode, same bars):

- **Payable policy for the remaining 63 events (min to max).** VOO 3982.17–3983.32,
  60/40 2541.39–2541.70, 50/30/10/10 2565.58–2565.80. Rankings unchanged.
- **COUNTERFACTUAL:** dropping the six reclassified BND gain components gives 60/40
  2537.52 and 50/30/10/10 2562.62. Not an equally likely reading after E1.
- **Withholding 15% (scenario, not tax advice).** 60/40 2467.28, 50/30/10/10 2499.48.

## 4. Ranking changes

- **FACT:** VOO_100 ranks first and CASH last in every scenario that ran.
- **FACT:** the order of 60/40 and 50/30/10/10 depends on assumptions. With fractional
  shares and no commission, 50/30/10/10 is higher by about 24. With a $1-minimum
  commission it is lower by about 8. With whole shares it is lower by about 280.
- **INFERENCE:** for a $1,000 account, whether fractional shares are available matters
  more than commission, spread, payable dates or the BND classification.

## 5. Cash benchmark

- **FACT:** CASH_NO_TRADE stays at 1000.00, and BIL_100 reaches 1218.88 (+21.9%,
  max DD 0.21%).
- **INFERENCE:** BIL is the realistic "cash" alternative; idle cash inside the
  whole-share portfolios earns nothing in this model.

## 6. Sources of return differences

- **FACT:** the gaps follow the equity weight: 100%, then 60%, then 50% VOO. Max
  drawdown falls in the same order: 33.9%, 21.2%, 17.9%.
- **HYPOTHESIS:** the 50/30/10/10 edge over 60/40 under fractional shares comes from
  GLD's 2016–2025 path and lower-volatility rebalancing. Per-sleeve attribution was
  not computed.

## 7. Limitations of the registered rule

- Annual rebalancing only. Distributions sit as cash until the next rebalance; there
  is no dividend reinvestment and no contributions.
- One historical path (2016–2025) and five fixed comparators. These are not
  independent tests and not a strategy search: no DSR, PBO or significance claim.
- 63 payable dates are still imputed. Three BND classifications rest on secondary
  evidence. Fees are hypothetical shapes. There is no real THB/USD FX history and no
  account-specific tax treatment.

## 8. What the evidence does and does not establish

- **Establishes (FACT):**
  - The provider cash amounts for BIL are issuer-consistent.
  - The BND 2020 extra payment is a capital gain counted once.
  - Corrected labels and BIL dates do not change any NAV.
  - Share granularity changes conclusions more than any other tested assumption.
- **Does not establish:**
  - That any portfolio is "best".
  - Future returns.
  - That the three secondary-evidence BND classifications are issuer-certified.
  - Real broker costs.

## 9. Is another study justified?

**PROPOSAL:** only a narrow one, chosen before running it. For example, the same five
comparators under a documented, real broker fee schedule and fractional-share policy
available to the owner, plus a contribution schedule. A new strategy hypothesis
would need its own preregistration, separate from HYP_003 (terminally falsified)
and from D7.

## Research brief for ChatGPT Research (public documents only)

1. **Vanguard confirmation.** Confirm from Vanguard documents (tax center or the BND
   distribution history) the types and amounts for BND 2021-04-01 (0.0534),
   2021-12-23 (0.13) and 2022-04-01 (0.0593).
2. **Vanguard payable dates for 2016–2019.** BND 47 and VOO 16 events. Report the
   source URL per date or `NOT_FOUND`.
3. **Broker terms.** For brokers the owner can actually use, give current published
   commission, minimum ticket charge, fractional-share availability for
   VOO/BND/GLD/BIL, and USD/THB conversion fee. Cite each with a date.
4. **BIL 2017 cash in lieu.** The cash-in-lieu price for fractional BIL shares at the
   2017-11-30 reverse split, if published.

REAL_CAPITAL_AUTHORITY = USD 0.00 · NO_REAL_ORDERS = true · paper/live = false.
