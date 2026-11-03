# ODR_UPI_LOCAL_TRANSACTION_AUTHORING_005 — Recording completed transactions from the Dashboard (RATIFIED 2026-11-03, narrowed to V1 by AMENDMENT_001)

## 1. Capability

`OWNER_LOCAL_TRANSACTION_AUTHORING_AUTHORIZED`: the loopback Dashboard may append Owner-entered,
already-executed events (buy, sell, deposit, withdrawal, dividend, fee) as
`ACASH_CANONICAL_TRANSACTIONS_V1` batches under `data/private/transactions/`, after Python
validation and explicit confirmation, and replay them with `acash.ppds.transactions`.

## 2. Why a separate decision

ODR-002 covers reading canonical histories only; ODR-003 covers only `snapshot.json` and
`capacity.json`. Neither extends to writing transaction files.

## 3. Scope

| Included | Excluded |
|---|---|
| Appending confirmed events with unique ids; idempotent resubmission | Editing or deleting recorded events in place |
| Corrections as new reversing or superseding events that keep the original | Orders to any broker, paper or live |
| Revision checks, journal and backups like ODR-003 | Broker sync, credentials, transfers, FX execution |
| Local replay and read-only reports | Uploads; CSV/PDF parsing (`BROKER_NATIVE_IMPORT`) |

Execution prices, fees and dates are what the Owner enters from broker evidence; ACASH never
substitutes a market quote. Analytical FIFO is not a tax method.

## 4. Ratify, revoke, rollback

The Owner sets `status` to `RATIFIED`, `ratified_by` to `OWNER` and `ratified_on` to the date,
then commits. Any other status stops writes immediately; recorded files stay readable under
ODR-002. Revert the commit to roll back.

## 5. Not authorized by this record

Trading (paper or live), broker connectivity or credentials, capital or currency transfers,
market-data retrieval, native broker import and D5 admission.
