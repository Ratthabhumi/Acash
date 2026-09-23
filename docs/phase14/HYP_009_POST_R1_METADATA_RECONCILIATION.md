# HYP_009 Post-R1 Canonical Metadata Reconciliation

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_POST_R1_METADATA_RECONCILIATION]
[TYPE: SURGICAL_LIFECYCLE_METADATA_RECONCILIATION_ONLY]
[SCIENTIFIC_CONTRACT_CHANGED = false]
[R1_VERDICT_UNCHANGED]
```

- **Document ID:** `docs/phase14/HYP_009_POST_R1_METADATA_RECONCILIATION.md`
- **Canonical HEAD at reconciliation:** `65e0b09fe9d19826a8b627ee1ac2ff1aaae70dd5`
- **Target file:** `docs/phase14/hypotheses/HYP_009.json`

---

## 1. Audited Issue

After the R1 seal (`R1_PREREGISTERED_SEALED`, manifest `manifest_r1_HYP_009.json`),
two PRE-R1 lifecycle metadata structures in the canonical hypothesis record were
stale:

- A: `invalidation_criteria.status = "NOT_PREREGISTERED_NO_NUMERICAL_GATES_AUTHORIZED"`
  — false after G1–G6 were formally preregistered.
- B: `open_before_r1` — still listed the five items R1 had resolved.

A downstream R2 reader would face a semantic conflict: `state` says sealed while
these fields say "not preregistered / unresolved".

## 2. Authorized Transition (Metadata Only)

| Field | Before | After |
|---|---|---|
| `invalidation_criteria.status` | `NOT_PREREGISTERED_NO_NUMERICAL_GATES_AUTHORIZED` | `R1_NUMERICAL_GATES_SEALED` |
| `invalidation_criteria.authority` | (absent) | `docs/phase14/manifests/manifest_r1_HYP_009.json` |
| `invalidation_criteria.gate_contract_hash` | (absent) | `052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b` |
| `invalidation_criteria.logical_conjunction` | (absent) | `G1 AND G2 AND G3 AND G4 AND G5 AND G6` |
| `open_before_r1` | 5 items | `[]` |
| `resolved_before_r1` | (absent) | 5 historical items (audit lineage preserved) |
| `r1_resolution_authority` | (absent) | `docs/phase14/manifests/manifest_r1_HYP_009.json` |

Canonical gate values remain exclusively those in the R1 manifest and the
frozen preregistration document. Nothing is duplicated or reinterpreted here.

## 3. Seal Consequence

- Prior HYP_009 file SHA: `f927ccd7b2a3adec18d8097fb09eea90a7bbeebe9872c9f563811bdb6b4842fa`
- New HYP_009 file SHA: `fb855542e86aa91139a0c7cdbedaad60de113ccbf679fe3e12a7465bcae13f2d`
- `scientific_contract_changed = false` (strategy/provider/sample/gate contract
  hashes unchanged; `parameter_config_json` untouched).
- R1 verdict unchanged. Historical R1 manifest and registration record are
  preserved byte-for-byte (NOT mutated).

## 4. Fields Verified Identical

`economic_rationale`, `target_symbol`, `feature_dependencies`,
`parameter_config_json`, `expected_direction`, `target_horizons`,
`primary_horizon`, `registered_at_utc`, `inception_token_id`,
`proposal_sha256`, `preregistration_sha256`, `r1_manifest`, `state`.

## 5. Governance Boundary

Zero market-data access. Zero signal/P&L computation. Zero backtest.
M2/M3/prospective remain locked. Paper `NOT_AUTHORIZED`, live `LOCKED`,
capital `$0.00`, `NO_REAL_ORDERS=true`.

## 6. Next Human Action

`AUTHORIZE_CORE_001_HYP_009_R2_M1_DATA_QUALIFICATION_AND_EXECUTION`
