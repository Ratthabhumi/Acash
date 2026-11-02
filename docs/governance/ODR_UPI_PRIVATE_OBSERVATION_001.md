# ODR_UPI_PRIVATE_OBSERVATION_001 — Owner-Private Portfolio Observation

Status: **PROPOSED_NOT_RATIFIED** (machine record: `docs/governance/ODR_UPI_PRIVATE_OBSERVATION_001.json`).
Prepared by an AI engineering agent. AI agents cannot ratify this record.

## 1. Proposed capability

`OWNER_PRIVATE_OBSERVATION_AUTHORIZED`: the owner may run the UPI snapshot,
capacity and pack code (`src/acash/ppds/private_observation.py`,
`src/acash/invest/capacity_plan.py`, `src/acash/invest/wealth_pack.py`) on their
own portfolio snapshot and financial-capacity figures, locally and offline, to
produce a private read-only decision-support report.

## 2. Existing restriction

`docs/audit/PPDS_READONLY_RUNTIME_SKELETON_PACK.md`: "real-statement runtime 0%
until separately authorized". This record would narrow that restriction for
owner snapshots only. The PPDS statement-import path (`provenance.py`,
`statement_ingest.py`) stays synthetic-only.

## 3. Scope

| Included | Excluded |
|---|---|
| Owner-typed snapshots (`ACASH_PRIVATE_PORTFOLIO_SNAPSHOT_V1_1`, `_V1_2`) and capacity files (`ACASH_PRIVATE_CAPACITY_V1`), exactly the schemas listed in `scope_schemas` | Broker statements imported by an adapter, OCR and screenshots |
| Valuation, allocation, concentration, broker-total reconciliation, illustrative stress, capacity scenarios | Orders, transfers, FX conversion, recurring plans |
| — | Transaction histories (`ACASH_CANONICAL_TRANSACTIONS_V1`): separate proposal `ODR_UPI_PRIVATE_TRANSACTIONS_002` |

The runtime gate accepts a ratified record only for the input schemas it lists.
Proposal history: on 2026-11-02, before any ratification, the proposed scope added V1_2
(owner-typed broker-displayed totals, value-only positions and identifiers).
| Private JSON/Markdown report under `data/private/` | Publishing, syncing or uploading the report |

## 4. Storage boundary

Inputs and outputs must resolve (after symlinks) outside the repository or under
`data/private/`, which is git-ignored independently of `/data/`. A path outside
the repository is not automatically secure. The owner must not point outputs at
cloud-synced or shared folders.

## 5. Data retention

Files stay on the owner's machine. ACASH keeps no copy, cache or log of them. The
owner deletes them by removing `data/private/`.

## 6. Privacy controls

Opaque account and broker references; decimal-string amounts; error messages
carry codes and references, never amounts; 2 MB input bound; no network calls;
owner-private outputs are blocked from tracked paths. Hashes of private files must
not be published (hashing is not anonymisation).

## 7. Evidence classification

Outputs are `OWNER_PRIVATE_OBSERVATION`. They are never `QUALIFIED_MARKET_DATA`,
never D5 research data, and never evidence for strategy admission.

## 8. Security risks

The local machine may be compromised; files may be misplaced into a synced folder;
the owner may mistype figures; values in the report are only as accurate as what
the owner enters. None of these risks touches trading or capital, which stay
locked independently.

## 9. Independent authorities (unchanged by this record)

`D5_DATA_ADMITTED`, `TRADING_AUTHORIZED`, broker connectivity, credentials,
market-data subscriptions and capital transfer remain separate decisions.
`NO_REAL_ORDERS = true`, `REAL_CAPITAL_AUTHORITY = USD 0.00`, `D5_REAL_ADMISSION =
NOT_ADMITTED`, `LANE_A/B = UNISSUED`, `HYP_003 = TERMINALLY_FALSIFIED`.

## 10. Ratification, revocation, rollback

- Ratify: the owner edits the JSON record to `"status": "RATIFIED"`,
  `"ratified_by": "OWNER"`, `"ratified_on": "<YYYY-MM-DD>"` and commits the change themselves.
- Revoke: set the status back to `PROPOSED_NOT_RATIFIED` or `REVOKED`. The runtime
  gate (`private_observation_authorized`) then refuses owner-private data again.
- Roll back: delete `data/private/`.

## 11. Acceptance criteria

1. Synthetic test suite green in CI with the gate closed.
2. With the gate closed, owner-private data fails with `PRIVATE_OBSERVATION_NOT_AUTHORIZED`.
3. The owner confirms that the storage location is not synced or shared.
