# Findings: evidence-driven, not unconditional

Each reason code must be derived from the evidence actually present in the report. A finding is a
statement about a specific instrument or account, with a category, a cause and a next action — never
a fixed sentence emitted because a report exists.

## Current rules

| Code | Emitted when | Not emitted when |
|---|---|---|
| `BROKER_TOTAL_RECONCILIATION_DIFFERENCE` | the broker total exceeds identified lines by a non-zero residual | the residual is zero |
| `UNCLASSIFIED_HOLDINGS_PRESENT` (legacy) | retired: the residual is now a reconciliation difference, not an asset | — |
| `UNKNOWN_CLASSIFICATION_PRESENT` | the strategy-class allocation still has UNKNOWN **and** the economic registry is not complete for every held instrument | every held instrument has a non-unknown economic class (the owner snapshot currently qualifies) |
| `SECURITY_IDENTITY_UNVERIFIED` | names the exact instruments still lacking an owner-confirmed identifier | 26 holdings with confirmed FIGIs are mapped; a missing venue MIC is reported separately and does not count as an unknown identity |
| `ACCOUNT_TOTALS_NOT_FULLY_RECONCILED` | an account comparison is not reconciled at the same time basis | a cross-date observation is a timing limitation, not an accounting failure |
| `RESERVE_SHORTFALL` | the designated reserve is below the expense-derived requirement | never suppressed, because the shortfall is real |
| `PERFORMANCE_NOT_ESTABLISHED` | there is no qualified dated cash-flow and valuation history | a qualified history exists |
| `OVERLAP_NOT_ESTABLISHED` | no dated, source-backed constituent weights exist | qualified constituents exist |
| `MARKET_SESSION_NOT_VERIFIED` | the pack applies no exchange calendar for the held venues | venue calendar evidence covers the held instruments |
| `V38_ROUTE_EVIDENCE_INCOMPLETE` | fee/FX evidence is missing for a cost-bearing route | the route's cost evidence is recorded |

## Numeric meaning

The residual is not an asset and is excluded from allocation, concentration and NAV. It stays visible
in `valuation_basis` as `unreconciled_broker_difference` with
`residual_classification: UNQUALIFIED_NOT_IN_TOTAL`, and the finding text states that explicitly.

Warnings that remain are genuine: reserve shortfall, performance history, ETF look-through, venue
calendars and V38 cost evidence are still unresolved, and closing them requires evidence that does
not yet exist locally.
