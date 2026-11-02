# ODR_UPI_LOCAL_INPUT_AUTHORING_003 — Owner-directed local input authoring

Status: **PROPOSED_NOT_RATIFIED**. Machine record:
[`ODR_UPI_LOCAL_INPUT_AUTHORING_003.json`](ODR_UPI_LOCAL_INPUT_AUTHORING_003.json).
Capability: `OWNER_LOCAL_INPUT_AUTHORING_AUTHORIZED`. Amends and requires
[ODR-001](ODR_UPI_PRIVATE_OBSERVATION_001.md).

## 1. Why an amendment

ODR-001 authorizes reading and analysing Owner-typed snapshot and capacity files that the
Owner places under `data/private/`. It does not mention a local service that writes those
files on the Owner's behalf. The Setup Wizard adds such a service, so the write authority is
proposed separately instead of being read into ODR-001.

## 2. Scope

| Included | Excluded |
|---|---|
| Creating or replacing exactly `data/private/snapshot.json` (`ACASH_PRIVATE_PORTFOLIO_SNAPSHOT_V1_2`) and `data/private/capacity.json` (`ACASH_PRIVATE_CAPACITY_V1`) after an explicit Save by the Owner | Any other path, file type or schema |
| Backups of the replaced file under `data/private/backups/` | Deleting the only valid observation; syncing or uploading |
| Loopback service on `127.0.0.1` with a per-start session token, Host and Origin checks | Broker connectivity, credentials, orders, transfers, FX conversion |

Validation and report generation stay under ODR-001 and need no new authority.

## 3. Runtime enforcement

`acash.dashboard_api.private_input_server` writes only while both ODR-001 and this record
are RATIFIED; every write request re-reads both records. While this record is unratified,
the wizard can still validate a draft in memory, and the Owner can keep editing the two
files directly. The wizard never offers a browser download of private data.

## 4. Ratification

Only the Owner ratifies. Set `status` to `RATIFIED`, `ratified_by` to `OWNER` and
`ratified_on` to the date, update the header of this document and commit. An agent must not
ratify this record on its own initiative; if the Owner directs an agent to apply the edit,
record that in a `ratification_lineage` block as for ODR-001.
