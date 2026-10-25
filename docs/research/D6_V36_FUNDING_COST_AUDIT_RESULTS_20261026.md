# D6 V36 — Funding, Cost Audit, Tax Scenarios, Attribution, Subperiods: Results (2026-10-26)

Label: `LOCAL_EXPLORATORY` under the frozen
[V36 spec](D6_V36_FUNDING_COST_AUDIT_SPEC_20261026.md). Not tax or investment
advice. `REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`. Produced by
`uv run python -m scripts.run_d6_v36_study`. The CSVs are written to the
git-ignored `data/local_research/v36/out/`. A second run produced byte-identical
output.

## Inputs (FACT)

| Input | sha256 |
|-------|--------|
| `v36/reconciled_max/bars_raw.csv` | `b86f73a69eff2cb9a81131dfa8b4b6d4cf32979be0a2ffcb8cd5e02058b0ff91` |
| `v36/reconciled_max/distributions.csv` | `9885fcb8258dcd6dc8f944776834d49f3c6f914d260e5bdc7cd29ae1a1726ca0` |
| `v36/reconciled_max/splits.csv` | `c9b9d95cedd8479118b2a0489f665d81f035d790739a56dc7f844fca5001588d` |
| H.10 Thailand page | `3dc41fe0255d50cb14272d645b262023278f2705e84379a26696eaf38d0c5ee1` |
| V35 `v35_grid.csv` snapshot | `f2efde508ac353dafaa4a0817e4f1e5df7a325f25ccd3b7bd356256f92d4249a` |

Dataset delta vs V34/V35: one label only. BND 2021-12-23 LT capital gain 0.13
is promoted to `OCC_MEMO_CORROBORATED` (OCC Information Memo #49819: LT capital
gain $0.13, ex 2021-12-23, record 2021-12-27, payable 2021-12-29, CUSIP
921937835). This is OCC data, not a Vanguard issuer document. Amounts and dates
are unchanged.

## P0 IBKR cost audit

**Regression (FACT):** R2, R3, R4 and R5 on the V36 dataset equal the V35
snapshot on every metric in all 80 cells (0 differing fields). The V35 numbers
stand.

**Source conflict (FACT):**

- The US table gives a 1% cap for Fixed and Tiered.
- The general North America note says "Tiered commissions will be capped at 0.5%".
- Fractional footnote 11 can be read either as "general formula + $0.01 floor"
  (R2) or literally as "1% of value on every fractional trade" (R2F). The page's
  own fractional examples are identical under both readings.

Effect on TWR annualized (FACT; full grid in `v36_cost_audit.csv`):

| Portfolio | C | R2 | R2F literal | R3 (1%) | R3H (0.5%) | R3M (+ARCA open 0.0015) | R3R (+0.0030) |
|-----------|---|----|-------------|---------|------------|--------------------------|---------------|
| 60/40 | C0 | 9.72% | 9.63% | 9.76% | 9.77% | 9.76% | 9.76% |
| 60/40 | C1 | 9.62% | 9.50% | 9.66% | 9.75% | 9.66% | 9.66% |
| 60/40 | C3 | 9.55% | 9.34% | 9.75% | 9.75% | 9.75% | 9.74% |
| VOO_100 | C3 | 14.77% | 14.46% | 14.86% | 14.86% | 14.86% | 14.86% |

- **R2F (literal fractional 1%):** costs 0.06–0.31 pp a year more than R2. The
  cost rises with contribution size, because large fractional orders pay 1%
  instead of about $1.
- **R3H (0.5% Tiered cap):** helps only when orders are under about $70 (up to
  +0.10 pp at C1). It is identical to R3 at C3.
- **ARCA venue fees:** they move TWR by ≤ 0.01 pp at every size tested. The
  printed open does not prove an auction fill or venue, so R3L, R3M and R3R
  are sensitivities, not historical costs.
- **Double counting:** Fixed rows carry regulatory fees only. Tiered rows add
  clearing and pass-through, and venue fees only in R3L, R3M and R3R.
- **Rounding and fills:** commissions are not rounded to cents, since no rule is
  published. One order per symbol per session means no repeated minimum.

## P0 Fractional eligibility

- **Public feature (FACT):** the IBKR page lists 10,500+ US stocks and ETFs and
  a minimum of USD 1, and mentions "eligibility requirements".
- **Region/entity eligibility for a Thailand-resident IBKR Pro individual:** not
  stated on public pages.
- **Security eligibility of VOO, BND, GLD and BIL:** not listed publicly.
- **Account-enabled status:** requires login.
- Status: `ACCOUNT_ELIGIBILITY_UNVERIFIED`. Whole-share rows (R4/R5) remain the
  conservative bound.

## P1 Funding from Thailand

Sources (FACT, retrieved 2026-10-26):

- **KBank SWIFT SHAR:** 250 THB, a promotion valid only through 2026-12-31. The
  page lists no investment purpose and says Thai nationals cannot send to their
  own account abroad, so the route's eligibility is doubtful.
- **Bangkok Bank SWIFT BEN:** 400 THB at the BBL TT selling rate. Purpose
  documents are required.
- **SCB SWIFT BEN:** 550 THB, and the receiving bank deducts its fee. The page
  also claims "no fees" in the SCB EASY app, with scope unverified.
- **IBKR:** does not cover other banks' fees, and a credit period applies.

Household results (C1 = $50/month, R2, household = broker + in-transit + unremitted THB):

| Funding | 60/40 household USD | 60/40 THB XIRR | VOO THB XIRR | Frictions USD |
|---------|--------------------:|---------------:|-------------:|--------------:|
| F0 frictionless (V35) | 12,439.52 | 8.65% | 13.89% | 0 |
| F1 monthly, 400 THB, 0.5% | 10,019.30 | 5.05% | 10.51% | 1,453.82 |
| F2 quarterly, 400 THB, 0.5% | 11,569.02 | 7.45% | 12.78% | 495.21 |
| F3 annual, 400 THB, 0.5% | 11,936.65 | 7.97% | 12.95% | 136.21 |
| F1 monthly, 400 THB + USD 15 intermediary | 7,048.10 | −0.98% | 5.00% | 3,238.82 |

- At C1, a monthly SWIFT remittance costs about 23% of each transfer
  (400 THB ≈ $11 on ≈ $50). It cuts 60/40 household THB XIRR by about 3.6 pp.
  Annual remittance cuts it by about 0.7 pp.
- C2 keeps the C1 ordering: monthly 6.66%, quarterly 8.01%, annual 8.10%. At C3
  ($250/month) the order changes to monthly 7.89%, quarterly 8.49%, annual
  8.21%. Quarterly beats annual at C3 because a year of idle THB costs more
  than the extra fees.
- A hypothetical USD 15 intermediary fee per wire is the single largest
  uncertainty at small sizes.
- Spread (0 / 0.5 / 1%) and settlement delay (0 / 1 / 3 sessions) move results
  by ≤ 0.2 pp. Delay matters most for annual lumps.
- `F1_CTRL` (no fee, no spread) reproduced F0 broker NAV to the cent in every
  cell. All 119 savings dates had a same-day H.10 rate.
- Inference: for small savings, how often money is transferred dominates which
  ETF is bought. Fees are current published tariffs applied retrospectively, not
  2016–2025 history.

## P1 US withholding scenarios (not tax advice)

Evidence (FACT):

- The Thailand–US treaty limits ordinary dividends (RD treaty text, via the
  owner's research).
- IRS Pub 515: "Certain interest-related dividends and short-term capital gain
  dividends paid by a mutual fund or other RIC are exempt from chapter 3
  withholding."
- The per-year BND/BIL designation percentages are UNVERIFIED, so the WT rows
  are bounds.

60/40 TWR annualized (withholding USD):

| C | W0 | W15 all | W30 all | WT_LOW | WT_MID | WT_NOTREATY |
|---|----|---------|---------|--------|--------|-------------|
| C0 | 9.72% (0) | 9.40% (49.35) | 9.07% (97.18) | 9.56% (23.82) | 9.40% (48.92) | 9.07% (96.35) |
| C1 | 9.62% (0) | 9.28% (176.01) | 8.95% (347.45) | 9.45% (80.75) | 9.29% (174.46) | 8.95% (344.43) |

- **BIL_100:** ranges from 1.98% (WT_LOW, interest-related relief) to 1.39% (30%).
  For a T-bill ETF, the withholding classification matters about as much as the
  whole commission question.
- **Naive 15% on everything (W15):** it overstates 60/40 withholding by about
  2× versus WT_LOW at C0.
- **Thai tax:** not computed. That would need verified residence, the
  acquisition date of the foreign income, remittance facts (2024+ rules) and a
  foreign tax credit calculation.

## P2 Accounting attribution (identity-verified; accounting, not causal)

C1, R2, USD:

| Funding | Portfolio | Price VOO | Price BND | Price GLD | Distributions | Comm+Reg | Bank fees+spread | FX translation | Household |
|---------|-----------|----------:|----------:|----------:|--------------:|---------:|-----------------:|---------------:|----------:|
| F0 | 60/40 | 4,674.18 | −286.26 | — | 1,188.90 | −84.99 | 0 | 0 | 12,439.52 |
| F0 | 50/30/10/10 | 3,857.33 | −200.98 | 1,160.42 | 1,065.92 | −94.25 | 0 | 0 | 12,735.39 |
| F1 | 60/40 | 3,845.13 | −232.28 | — | 980.49 | −68.35 | −1,453.82 | 0 | 10,019.30 |
| F3 | 60/40 | 4,246.40 | −262.15 | — | 1,075.27 | −33.44 | −136.21 | +98.71 | 11,936.65 |

Observations:

- BND's price change is negative over 2016–2025; its return comes from
  distributions.
- The 50/30/10/10 edge over 60/40 under F0 comes from GLD's price gain
  (+1,160) more than offsetting less VOO. This is an accounting decomposition of
  one path, not evidence of a causal or persistent effect.
- FX translation under annual funding is positive because THB appreciated while
  savings waited. That is currency luck, not a strategy.

## P2 Subperiods (fresh $1,000 per window, R2, C0)

| Window (sessions) | VOO_100 ann | 60/40 ann | 50/30/10/10 ann | 60/40 MaxDD | 50/30/10/10 MaxDD | Ranking (60/40 vs 50/30/10/10) |
|-------------------|------------:|----------:|----------------:|------------:|------------------:|-------------------------------|
| 2016–2019 (1006) | 14.70% | 10.23% | 9.34% | 11.57% | 9.33% | 60/40 ahead |
| 2020–2022 (756) | 7.47% | 3.47% | 3.69% | 21.02% | 17.89% | 50/30/10/10 ahead |
| 2023–2025 (752) | 22.87% | 15.32% | 16.38% | 11.03% | 8.93% | 50/30/10/10 ahead |
| 2016–2025 (2514) | 14.84% | 9.72% | 9.79% | 21.17% | 17.95% | 50/30/10/10 ahead |

- VOO_100 has the highest TWR in every   window, at about 1.6–1.7× the volatility
  of 60/40. More equity exposure is not skill.
- The 60/40 versus 50/30/10/10 order reverses across windows (2016–2019). The
  difference is window-dependent. 50/30/10/10 had lower volatility and drawdown
  in every window.
- The windows are 3–4 years long. Annualized figures assume 252 sessions per
  year and should be read with that length in mind.
- A block bootstrap was skipped by design (spec §5).

## Limitations

- Every fee is a current published schedule applied to 2016–2025. Eligibility of
  bank routes for brokerage funding is unverified. Retail FX spreads and
  intermediary fees are hypothetical. H.10 is not a retail rate.
- Thai income tax is not modelled. The withholding rows are bounds, and the RIC
  designation percentages are unverified.
- There is a single historical path. There is no DSR/PBO and no significance
  claims.
- Still open: Vanguard originals for BND 2020/2021/2022, 63 imputed payable dates
  (BND 47, VOO 16; immaterial per V35), and the BIL 2017 cash-in-lieu price.

## ChatGPT research brief

1. Does IBKR's US Tiered commission cap equal 1% (US table) or 0.5% (North
   America note) for US ETFs today? Does footnote 11 mean 1% of value on any
   order containing a fractional share? Cite IBKR knowledge-base articles.
2. Can Thailand-resident IBKR Pro individual accounts trade VOO, BND, GLD and
   BIL fractionally? Are these ETFs on IBKR's fractional-eligible list?
3. Which Thai bank channels permit a Thai national to remit THB→USD to their
   own foreign brokerage account (BoT purpose code for investment)? What are the
   current fees, the TT selling-rate markup over mid, and typical intermediary
   or receiving deductions for USD wires to IBKR? Are there cheaper lawful
   channels (e.g., FCD account, licensed money-transfer operators)?
4. What were the annual qualified interest income (QII) and short-term
   capital-gain designation percentages for BIL and BND in 2016–2025 (issuer
   tax supplements)? Do brokers apply the §871(k) exemptions at payment time for
   non-US persons?
5. How are remitted foreign dividends, capital gains and principal treated for
   Thai residents under the 2024+ remittance rule (Por. 161/162/2566), including
   the foreign tax credit for US withholding?
