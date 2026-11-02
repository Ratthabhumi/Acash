# ODR_UPI_PRIVATE_TRANSACTIONS_002 — Owner-private transaction histories (PROPOSED, NOT RATIFIED)

## 1. Capability

`OWNER_PRIVATE_TRANSACTIONS_AUTHORIZED`: the owner may replay their own transaction
history, typed or mapped by hand into `ACASH_CANONICAL_TRANSACTIONS_V1`, through
`acash.ppds.transactions` and `acash.invest.performance`, locally and offline.

## 2. Why a separate decision

Transaction histories are more sensitive than a point-in-time snapshot (full trading
behaviour, income, tax withholding). `ODR_UPI_PRIVATE_OBSERVATION_001` does not cover
them, and ratifying 001 does not ratify this record.

## 3. Scope

| Included | Excluded |
|---|---|
| Canonical JSON batches the owner prepares | Native Dime!/Webull CSV/PDF parsers (`BROKER_NATIVE_IMPORT_NOT_ESTABLISHED`), OCR, screenshots |
| Replay, FIFO analytical lots, reconciliation to a snapshot, TWR/XIRR | Tax computation, orders, transfers, FX conversion |
| Private output under `data/private/` | Publishing, syncing or uploading |

## 4. Storage, retention, privacy

Same as ODR 001: inputs and outputs live outside the repository or under the git-ignored
`data/private/`. The location is checked after resolving symlinks, errors carry no amounts,
and inputs are size-bounded. Retention and deletion stay with the owner. Hashes of private
inputs are not safe to publish.

## 5. Ratify, revoke, rollback

To ratify, the owner sets `status` to `RATIFIED`, `ratified_by` to `OWNER` and `ratified_on`
to the date, then commits. To revoke, any other status closes the gate immediately. To roll
back, revert that commit.

## 6. Not authorized by this record

D5 admission, trading (paper or live), broker connectivity or credentials, market-data
subscriptions, capital or currency transfers, and native broker import.
