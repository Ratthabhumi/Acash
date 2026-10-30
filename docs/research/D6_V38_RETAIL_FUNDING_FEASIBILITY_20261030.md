# D6 V38 — Retail Funding Route Feasibility (THB → IBKR, read-only)

Date verified: 2026-10-30. Scope: documented public sources only. No account,
transfer, deposit, quote request, purchase or order was made. Nothing here
confirms that any route has funded the owner's account.
`REAL_CAPITAL_AUTHORITY = USD 0.00`, `NO_REAL_ORDERS = true`, Lane A/B UNISSUED.

Deliverables: route matrix
[`evidence/v38_funding_route_matrix_20261030.csv`](evidence/v38_funding_route_matrix_20261030.csv)
(27 fields, 10 routes), cost rule `src/acash/research/d6/route_cost.py` with
tests `tests/unit/research/test_d6_v38_route_cost.py`.

## 1. Regulatory and eligibility position (seven layers)

| Layer | Status | Evidence |
|---|---|---|
| 1. Legal ability to invest abroad | VERIFIED_DOCUMENTED | BoT circular ธปท.ว. 564/2569 ([PDF](https://www.bot.or.th/content/dam/bot/fipcs/documents/FOG/2569/ThaiPDF/25690017.pdf)) replaces the online overseas-investment notice with a self-certification letter given to the bank; effective 2026-01-27 per [Baker McKenzie](https://www.bakermckenzie.com/en/insight/publications/2026/02/thailand-repatriation-exemption-for-foreign-sourced-funds). Cap USD 5 million per person per year without an onshore agent. The BoT English [exchange-control page](https://www.bot.or.th/en/our-roles/financial-markets/foreign-exchange-regulations/exchange-control-regulation.html) still describes registration and is treated as outdated. |
| 2. Bank's permitted outward purposes | ACCOUNT_SPECIFIC_UNVERIFIED | Bank pages list SWIFT outward transfers; none of the retrieved pages states an "overseas portfolio investment" purpose option in the app. |
| 3. Channel usage | ACCOUNT_SPECIFIC_UNVERIFIED | App limits documented (BBL THB 2,000,000/day; SCB Ripple THB 1,500,000); investment purpose in app not documented. |
| 4. Broker funding instructions | VERIFIED_DOCUMENTED (general) | [IBKR Fund My Account](https://www.interactivebrokers.com/en/support/fund-my-account.php): routing details come from a Client Portal deposit notification; IBKR is not responsible for bank or correspondent fees; one wire cannot be split across accounts. |
| 5. Beneficiary and sender-name compatibility | CONDITIONALLY_ELIGIBLE | IBKR generally rejects third-party deposits, so the sending Thai account must be in the IBKR account holder's name. Partner-network and Ripple routes have no evidence of IBKR beneficiary support. |
| 6. Country and currency | CONDITIONALLY_ELIGIBLE | SWIFT routes send USD; the KBank partner network delivers only the destination's local currency. The IBKR receiving entity for a Thai resident is UNKNOWN. |
| 7. Account-specific eligibility | ACCOUNT_SPECIFIC_UNVERIFIED | Not checked; it requires the owner's own accounts. |

## 2. Route summary (fees as published; matrix CSV holds full fields)

| Route | Sender fee (THB) | Payer basis | Documented gaps | Status |
|---|---|---|---|---|
| KBank K PLUS SWIFT SHAR | 250 (promotion 2026-01-01 to 2026-12-31) | foreign fees deducted | spread, intermediary, receiving, 2027 fee | COST_INCOMPLETE, ACCOUNT_SPECIFIC_UNVERIFIED |
| KBank K PLUS SWIFT DEBT/OUR | 950 (same promotion) | foreign charges may still be deducted | residual charges, spread | COST_INCOMPLETE, ACCOUNT_SPECIFIC_UNVERIFIED |
| KBank K PLUS SWIFT CRED/BEN | 0 + USD 12 deducted | beneficiary | foreign charges, spread | COST_INCOMPLETE, ACCOUNT_SPECIFIC_UNVERIFIED |
| KBank partner network | 250 | full amount stated | US/USD coverage, IBKR beneficiary | ACCOUNT_SPECIFIC_UNVERIFIED |
| Bangkok Bank mobile SHA | 300 (normally 400; end date not stated) | foreign fees deducted | promotion end, spread, intermediary | COST_INCOMPLETE, ACCOUNT_SPECIFIC_UNVERIFIED |
| Bangkok Bank mobile OUR | 1,050 (normally 1,150) | more may be collected | residual charges, spread | COST_INCOMPLETE, ACCOUNT_SPECIFIC_UNVERIFIED |
| SCB SWIFT BEN/SHA | 550 | foreign fees deducted | spread, intermediary | COST_INCOMPLETE, ACCOUNT_SPECIFIC_UNVERIFIED |
| SCB SWIFT OUR (USD) | 1,350 (550 + 800) | additional charges possible | residual charges, spread | COST_INCOMPLETE, ACCOUNT_SPECIFIC_UNVERIFIED |
| SCB EASY Ripple (US, USD) | 199–399 | full amount stated | exact fee, IBKR beneficiary, purpose | ACCOUNT_SPECIFIC_UNVERIFIED |
| Wise / e-wallets / other MTOs | not researched | — | everything | SOURCE_UNAVAILABLE |

No route is `VERIFIED_DOCUMENTED` for all-in cost, because no retrieved
source discloses an executable THB/USD retail spread, correspondent
deductions or the IBKR receiving charge. No route is declared cheapest. The
lowest *published sender fee* among SWIFT routes is KBank SHAR (THB 250,
until 2026-12-31); that is a fee fact, not a cost ranking.

Foreign-currency-deposit (FCD) commissions in lieu (Bangkok Bank 0.125%,
minimum THB 500; SCB USD 0.25%) apply to same-currency FCD payments, not to a
THB-sourced transfer.

## 3. Prospective cost rule (specification)

Symbols: amount \(A\) (THB), fixed sender fee \(F\), variable fee rate \(v\)
with minimum \(M\), FX spread \(s\) against a reference rate \(r\), deducted,
intermediary and receiving fees \(D, I, R\) (USD).

\[
\text{cost share} \le \frac{F + \max(vA, M) + (D + I + R)\,r}{A} + s
\]

This additive form is an upper bound on the exact share under both the V36
conversion \(A/(r(1+s))\) and a proportional haircut, so the threshold below
is sufficient, not exact. For a fixed fee and a known spread:

\[
A \ge \frac{F}{c - s}, \qquad c > s
\]

where \(c\) is the user-selected cost ceiling. If any component is unknown,
`assess_transfer` lists it and returns `LOWER_BOUND_ONLY`; it never returns
an all-in status with an unknown fee. Ineligible purpose or beneficiary,
currency mismatch, amounts outside limits, a fee at or above the amount, and
negative or non-finite inputs raise `DataContractError`. After a promotion
ends, the standard fee is used if documented; otherwise the fee is listed as
unknown.

### Break-even amounts (fee-only, illustrative ceiling c = 1%)

| F (THB) | s = 0 (fee-only lower bound) | s = 0.5% (V36 hypothetical spread) |
|---|---|---|
| 199 | 19,900 | 39,800 |
| 250 | 25,000 | 50,000 |
| 300 | 30,000 | 60,000 |
| 550 | 55,000 | 110,000 |
| 950 | 95,000 | 190,000 |
| 1,050 | 105,000 | 210,000 |
| 1,350 | 135,000 | 270,000 |

With unknown intermediary or receiving fees these are lower bounds on the
required \(A\). The spread \(s = 0.5\%\) is the V36/V37A hypothetical, not a
quote, and H.10 is only a reference rate.

### Household examples (illustrative V37A amounts, not the owner's budget)

Months of saving needed per transfer to meet c = 1% (`minimum_batch_months`):

| Monthly saving | F=199, s=0 | F=250, s=0 | F=300, s=0 | F=550, s=0 | F=250, s=0.5% |
|---|---|---|---|---|---|
| THB 1,000 | 20 | 25 | 30 | 55 | 50 |
| THB 3,000 | 7 | 9 | 10 | 19 | 17 |
| THB 5,000 | 4 | 5 | 6 | 11 | 10 |
| THB 10,000 | 2 | 3 | 3 | 6 | 5 |

Monthly transfers with F = 250 cost 25%, 8.3%, 5% and 2.5% of the transfer
in fees alone, for THB 1,000 / 3,000 / 5,000 / 10,000 respectively. Batching
\(k\) months leaves money outside the broker for \((k-1)/2\) months on
average. With F = 250, that is 12 / 4 / 2 / 1 months at the 1% threshold.

## 4. Cost of waiting (symbolic sensitivity)

Saving \(m\) THB per month and transferring every \(k\) months costs about

\[
C(k) \approx \frac{F}{k} + \frac{m\,\mu\,(k-1)}{2} + s\,m
\]

per month. Here \(\mu\) is the *assumed* monthly expected excess return of
the invested asset over the THB deposit rate. It is an input, not a fact,
and it may be zero or negative. When \(\mu > 0\), the minimum is at
\(k^* = \sqrt{2F/(m\mu)}\). When \(\mu \le 0\), the model has no interior
optimum, and batching is limited by liquidity and risk rather than by
expected return. FX moves while waiting and market-return risk are two-sided
and are not in \(C(k)\). The deposit interest on held THB is account-specific
and UNKNOWN. Emergency-fund needs take precedence.

| \(k^*\) for F = 250 | m = 1,000 | 3,000 | 5,000 | 10,000 |
|---|---|---|---|---|
| \(\mu\) = 0.25%/month (assumed) | 14.1 | 8.2 | 6.3 | 4.5 |
| \(\mu\) = 0.50%/month (assumed) | 10.0 | 5.8 | 4.5 | 3.2 |

These figures show sensitivity only. They are not a recommended interval and
are not inferred from the 2016–2025 sample.

## 5. Recommendation and falsification conditions

- Transfer size, not route choice, is the first-order cost driver at
  household amounts. Any SWIFT route with a THB 250–550 fee needs roughly
  THB 25,000–55,000 per transfer for fees alone to stay under 1%, before
  unknown deductions.
- The recommendation is to confirm the missing route facts (section 7) before
  any funding decision. No route is endorsed.
- **Falsifiers:**
  - A documented correspondent or receiving fee of USD ≥ 10 materially raises
    SHA thresholds; at r ≈ 32 each USD 10 adds about THB 320 to F.
  - A live TT spread s ≥ c makes the ceiling unreachable for that route.
  - IBKR or the bank rejecting the purpose or beneficiary turns the route
    into NOT_ELIGIBLE.
  - KBank's 2027 standard fee replaces the THB 250 promotion.

## 6. Research utilization matrix

| # | Area | Status | Already implemented | Newly verified (V37B/V38) | Still unverified | Next decision |
|---|---|---|---|---|---|---|
| 1 | Alpaca bars and corporate actions | IMPLEMENTED, EMPIRICALLY_RECONCILED (local), RETROSPECTIVE_ONLY | local adapters, reconciled frozen inputs (V34–V36) | frozen hashes re-checked | data rights, PIT | owner data-rights decision |
| 2 | BIL 1-for-2 reverse split 2017-11-30 | IMPLEMENTED, SOURCE_VERIFIED | split ledger; Form 8937 (V33/V34) | — | — | none |
| 3 | BND capital gains 2016–2025 | SOURCE_VERIFIED, EMPIRICALLY_RECONCILED (3 components) | V37B overlay | SEC annual totals; OCC/MIAX events | 5 event memos, FY2020 basis | optional memo lookup |
| 4 | Vanguard payable-date backlog | UNVERIFIED | 63 records preserved | — | all 63 dates | needs a licensed or official source |
| 5 | QSG and withholding tax | SOURCE_VERIFIED (fund-level TY2020–2021), RETROSPECTIVE_ONLY | V36 withholding scenarios; V37B tax records | 1042-S text | per-event QSG, TY2022–2024, publication dates | tax-advisor question |
| 6 | H.10 reference FX | IMPLEMENTED, RETROSPECTIVE_ONLY | `h10_rate` in V36/V37A | — | not an executable quote | live TT quotes |
| 7 | Fixed-THB funding | IMPLEMENTED, RETROSPECTIVE_ONLY | V37A ledger | V38 prospective rule | real spreads and deductions | section 7 items |
| 8 | IBKR commission and fractional shares | IMPLEMENTED (R2/R2F readings), UNVERIFIED reading | V36 | — | footnote-11 interpretation | IBKR clarification |
| 9 | Thai international remittance | SOURCE_VERIFIED (fees, partial) | V36 fee scenarios | BoT ว.564/2569; KBank, BBL, SCB fees | spreads, deductions, eligibility | section 7 items |
| 10 | D5 data licensing and PIT | NOT_AUTHORIZED | — | — | rights, PIT; 0/40 cells admitted | owner decision |
| 11 | D7 strategy readiness | NOT_AUTHORIZED | — | — | blocked by D5 | HOLD_FOR_DATA_RIGHTS |
| 12 | ATrain IV Walls intake | UNVERIFIED (archived intake only) | intake record only; not in the engine | — | everything | none until D5 |

## 7. Open research (for external research or the owner)

1. The executable KBank, Bangkok Bank and SCB THB→USD TT selling rate at the
   same timestamp as a reference rate, giving the actual spread.
2. USD correspondent and intermediary deductions on SHA wires to IBKR's
   receiving bank, and whether OUR fully covers them.
3. The IBKR entity for Thai residents, its receiving bank, and any incoming
   wire fee.
4. Whether each bank's app offers an overseas-investment purpose code and
   accepts IBKR as beneficiary (self-certification under ว.564/2569).
5. Whether SCB Ripple and the KBank partner network can pay into an IBKR USD
   receiving account in the sender's own name.
6. The KBank standard fee from 2027-01-01, and the end date of Bangkok
   Bank's promotion.
7. Wise or other MTOs, only if bank routes remain materially worse and IBKR
   documents acceptance.
