# PPDS Read-Only Runtime Skeleton Pack — IMPLEMENTED_ON_REPAIR_BRANCH

**Status update 2026-10-02**: no longer PREPARED/NOT EXECUTED. Implemented:

- statement ingestion (`src/acash/ppds/statement_ingest.py`)
- PositionLot/CashLot (`src/acash/ppds/lots.py`)
- hash-chained NormalizedPortfolioLedger (`src/acash/ppds/ledger.py`)
- exact reconciliation (`src/acash/ppds/reconcile.py`)
- exposure / ETF overlap / FX exposure (`src/acash/ppds/exposure.py`)
- read-only surface (`src/acash/ppds/surface.py`)
- 12 tests (`tests/unit/ppds/test_ppds_readonly_ledger.py`)

**Authorization boundary** (unchanged): synthetic fixtures only. No broker
credentials, no real statements, no order endpoint, no capital movement.
Read-only decision-support direction.

**Still forbidden**: real statements, broker API, credentials, order
endpoint, capital movement.

**Authorization boundary**: synthetic fixtures only. No broker credentials,
no real statements, no order endpoint, no capital movement. Read-only
decision-support direction; real-statement runtime 0% until separately
authorized (the synthetic runtime below is implemented, not authorized
for real data).

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

## Skeleton components (IMPLEMENTED on repair branch — was "to be built")

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
