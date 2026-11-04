# Portfolio headline semantics

Three different numbers exist and must never be merged or substituted for one another.

| Number | Meaning | Where it belongs |
|---|---|---|
| Latest broker-displayed total | What the Dime! app showed at one timestamp | Portfolio headline (labelled `BROKER_DISPLAYED_OBSERVATION`) |
| ACASH computed valuation | `quantity × eligible price + settled cash` from the saved snapshot, at its valuation date | Portfolio headline, separate card with the basis date |
| Total best evidence | Computed NAV plus observed value-only items and any unidentified residual | Advanced diagnostics only |

Rules:

- The broker headline states its source, timestamp and that PPDS did not compute it; it may lag the
  holdings valuation.
- The computed card always shows the valuation date and "subset of the portfolio".
- A market-refresh subtotal replaces the computed card only while a valid refresh exists, with its
  coverage; it is labelled "priced holdings subtotal", never NAV.
- Total best evidence is not a headline. It stays in the allocation/evidence area where its
  denominator and residual are visible.
- External bank cash never enters any of these three numbers. It appears only in the consolidated
  wealth figure, labelled mixed evidence.
- A cross-date gap between the broker observation and the computed valuation is
  `TIME_MISALIGNED`; it is not evidence of a missing transaction and never triggers balancing
  entries.

## Reserve and cash numbers

- External cash actual (all declared accounts) ≠ designated emergency reserve ≠ external-cash
  target ≠ expense-derived reserve requirement.
- Designation is the Owner's decision per account; eligibility is only a suggestion. KBank spending
  cash is not designated reserve.
- The capacity input carries the designated reserve, so the expense-derived shortfall is computed
  against the designated amount and is not reduced by the cash target.

## Residual contract (V92)

`total_best_evidence` now equals **qualified** components only: computed NAV plus evidenced
value-only positions. A broker-total residual is recorded separately as
`unreconciled_broker_difference` with `residual_classification: UNQUALIFIED_NOT_IN_TOTAL` and never
enters the total, the allocation denominator or any weight. For a totals-only snapshot with no
qualified value the total is `0.00` and the coverage fields report `NOT_APPLICABLE_*` instead of
dividing by zero.

The classification registry also carries optional `sector` and `theme` fields, kept separate from
the economic asset class so an aerospace ETF can be EQUITY with a theme without merging the two
dimensions.
