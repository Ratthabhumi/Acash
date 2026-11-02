# ODR_UPI_LOCAL_INPUT_AUTHORING_003 — Owner-directed local input authoring

Status: **RATIFIED** by the Owner on 2026-11-02. The Owner approved conditionally on the P0
security and integrity tests passing, and the agent applied the edit at the Owner's direction
after they passed ([acceptance record](ODR_UPI_LOCAL_INPUT_AUTHORING_003_ACCEPTANCE.json)). The
scope is unchanged. Machine record:
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

`acash.dashboard_api.private_input` (served by `private_view_server`) writes only while
ODR-001 and this record are RATIFIED. The check reads both records again on every write
request and once more before each file replacement. It refuses this record unless all of the
following hold:

- `decision_id` and `capability` are exact;
- `ratified_on` is an ISO date;
- `requires` is exactly ODR-001;
- `scope_schemas` and `scope_files` equal the two entries in section 2.

A broader, narrower or malformed record counts as not ratified. Revocation stops the write
before the next file is replaced.

A save is one request (`PUT /api/upi/input/inputs`) carrying both documents. The steps are:

1. Both documents are validated, the request must confirm the replacement, and both base
   revisions must match the files on disk.
2. Both files are staged next to their targets, and the current files are copied to
   `data/private/backups/`.
3. A transaction journal (`data/private/.input_transaction.json`) is written.
4. Each file is replaced atomically.

A failure after the first replacement restores both files from the journal. A journal left
by a crash is recovered before any later write or report generation. If recovery is not
possible, writes and generation are refused (`INPUT_RECOVERY_REQUIRED`). Two separate file
replacements are not one atomic operation; the journal makes a partial pair recoverable and
blocks its use, but does not make it impossible.

Writes are refused if `data`, `data/private`, its subdirectories or the target file is a
symbolic link or junction. A directory swapped between this check and the replacement is a
residual risk; it needs local write access to the Owner's profile.

Report generation (ODR-001) builds the pack and view in a new directory under
`data/private/out/generations/`, verifies the view hash, publishes `upi_view.json`, and then
publishes `report_generation.json`. The record holds the input revisions and hashes. On any
failure the previous view stays in place.

While this record is unratified, the wizard can still validate a draft in memory, and the
Owner can keep editing the two files directly. The wizard never offers a browser download of
private data.

## 4. Ratification

Only the Owner ratifies. Set `status` to `RATIFIED`, `ratified_by` to `OWNER` and
`ratified_on` to the date, update the header of this document and commit. An agent must not
ratify this record on its own initiative; if the Owner directs an agent to apply the edit,
record that in a `ratification_lineage` block as for ODR-001.
