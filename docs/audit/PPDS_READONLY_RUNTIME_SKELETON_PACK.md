# PPDS Read-Only Runtime Skeleton Pack (PREPARED — NOT EXECUTED)

**Authorization boundary**: synthetic fixtures only. No broker credentials,
no real statements, no order endpoint, no capital movement. Read-only
decision-support direction; runtime 0% until separately authorized.

## Pipeline (synthetic fixtures only)

```text
CSV / synthetic statement
  -> AccountSnapshot
  -> PositionLot / CashLot
  -> NormalizedPortfolioLedger
  -> reconciliation (statement vs ledger)
  -> exposure / ETF overlap / FX exposure
  -> read-only decision surface
```

## Skeleton components (to be built post-authorization)

1. `statement_ingest.py` — parse synthetic CSV into `AccountSnapshot`
   (holdings, cash balances, as-of timestamp). Reject malformed rows
   fail-closed; never coerce.
2. `lots.py` — `PositionLot` / `CashLot` with acquisition date, quantity,
   cost basis (synthetic cost only).
3. `ledger.py` — `NormalizedPortfolioLedger`: append-only, hash-chained,
   positions + cash lots.
4. `reconcile.py` — statement-vs-ledger reconciliation report
   (match/mismatch with exact Decimal tolerance, no silent rounding).
5. `exposure.py` — exposure by asset/currency, ETF overlap decomposition
   (holdings-based, synthetic holdings only), FX exposure.
6. `surface.py` — read-only decision surface renderer (text/JSON):
   positions, exposure, reconciliation status. NO order controls.

## Invariants

- `$0 real capital` always; no order endpoint may exist in this package.
- Fixtures live under test/tmp paths only; real statements never enter
  the repository.
- Every derived number traces to a fixture row + code SHA.
