# ODR_UPI_OWNER_TRANSACTION_CORRECTIONS_006 — Correcting recorded local transactions (PROPOSED, NOT RATIFIED)

## 1. Capability

`OWNER_LOCAL_TRANSACTION_CORRECTION_AUTHORIZED`: the loopback Dashboard may append a correction
event that voids or supersedes an already recorded `ACASH_CANONICAL_TRANSACTIONS_V1` event.

Status: `PROPOSED_NOT_RATIFIED`. No correction authoring path exists yet and none is activated by
this record.

## 2. Why a separate decision

ODR-005 (as narrowed by `ODR_UPI_LOCAL_TRANSACTION_AUTHORING_005_AMENDMENT_001`) authorizes only
appending completed events. Corrections change the effective journal projection, so they need
their own capability, schema version and accounting rules.

## 3. Methodology

`APPEND_ONLY_SUPERSEDE_BY_ID`.

| Included | Excluded |
|---|---|
| `VOID_ENTERED_EVENT` and `SUPERSEDE_ENTERED_EVENT` referencing an existing event id | Editing or deleting recorded evidence in place |
| Reason, owner confirmation, revision lineage, timestamps | Representing a mistaken BUY as a real SELL |
| Deterministic replay through `acash.ppds.transactions` | A second accounting engine |
| Backward-compatible reading of V1 history | Silent expansion of `ACASH_CANONICAL_TRANSACTIONS_V1` |

A correction is an amendment to recorded evidence, not an executed trade. Replays must reject a
nonexistent target, a cycle, conflicting supersessions of the same target, and double application
of one correction id.

## 4. Ratify, revoke, rollback

The Owner sets `status` to `RATIFIED`, `ratified_by` to `OWNER` and `ratified_on` to the date, in a
commit that also names the chosen schema version. Any other status disables correction authoring;
journals remain readable under ODR-002 and ODR-005. Revert the commit to roll back.

## 5. Not authorized by this record

Trading (paper or live), broker connectivity or credentials, capital or currency transfers,
market-data retrieval, native broker import and D5 admission.
