# CAND-FREE-MACRO-001 — D18 Reproducibility Manifest Specification & Schema Template

**Document ID:** `docs/phase14/macro_001_d18_manifest_specification.md`  
**Classification:** `[DOCUMENTATION-ONLY]` · `[NON-EMPIRICAL]` · `[UNSEALED TEMPLATE]` · `[DEPENDENCY-BLOCKED ON D17-E]`  
**Status:** `OPEN / GROUP C / READY FOR DATA-PLANE INTEGRATION`  
**Applicable Candidate:** `CAND-FREE-MACRO-001` (Scheduled Macro-Announcement Premium Conditioning)  
**Parent Governance:** AGENTS.md §1 Core Principles; `cand_free_macro_001_human_specification_decision_surface.md` §25, §28  

---

## 1. Executive Summary & Governance Contract

1. **Non-Empirical Contract:** This document defines the formal, deterministic data structure and cryptographic sealing protocol for the CAND-FREE-MACRO-001 Reproducibility Manifest (**D18**). It contains **zero empirical results**, performs no backtest, and calculates no strategy performance statistics.
2. **Strict Unsealed State:** The manifest schema is formally specified below, but the actual manifest instance remains **UNSEALED** and **OPEN (Group C)** because its upstream prerequisite—**D17 SPX Close Data Authority**—remains blocked under human-ratified state **D17-E** ($0 data authority blocker).
3. **Single Canonical Authority (AGENTS.md #4, #13):** When sealed post-D17 resolution, the manifest produces a single authoritative cryptographic root (`manifest_sha256`) that immutably binds:
   - Exact Git code tree and dependency lockfiles.
   - Exact specification documents and pre-registered protocol parameters.
   - Exact raw and Parquet data source artifacts and row-level hashes.
   - Exact numerical execution environment and fail-closed error boundaries.
4. **Zero Silent Fallback (AGENTS.md #3):** Missing bytes, digest mismatches, unversioned proxy substitutions, or modified parameters cause an immediate, fail-closed `DataContractError` or `IntegrityError`.

---

## 2. Manifest Cryptographic Architecture

```
                                  CANDIDATE LINEAGE
         ┌───────────────────────────────┼───────────────────────────────┐
         ▼                               ▼                               ▼
Specification Artifacts           Code & Dependencies            Data Sources (S-01..S-05)
(Decision Surface, Round 4,      (Git commit, pyproject,        (Raw files, Parquet parts,
 Binding Worksheet)              uv.lock, environment)          vintage metadata, row counts)
   SHA-256 digests                 SHA-256 digests                 SHA-256 digests
         │                               │                               │
         └───────────────────────┬───────┴───────────────────────────────┘
                                 ▼
                     CANONICAL JSON MANIFEST
                     (Deterministic UTF-8,
                      Keys Sorted, Whitespace Stripped)
                                 │
                                 ▼
                         manifest_sha256
                                 │
                                 ▼
                 SEALED PRE-REGISTRATION STATE
                 (Requires Human Authorization to Run)
```

---

## 3. Manifest Field Taxonomy & Specifications

### 3.1 Metadata & Identity
- `manifest_id`: Unique identifier formatted as `MANIFEST_MACRO_001_<VINTAGE_DATE>_<HEX8>`.
- `schema_version`: Must strictly match `"v1.0.0"`.
- `candidate_id`: Strictly `"CAND-FREE-MACRO-001"`.
- `status`: One of `["DRAFT_UNSEALED", "SEALED_PRE_REGISTRATION", "SUPERSEDED", "REVOKED"]`. Current state: `"DRAFT_UNSEALED"`.
- `created_at_utc`: ISO-8601 UTC timestamp of initial template assembly.
- `sealed_at_utc`: ISO-8601 UTC timestamp when all hashes are computed (must be `null` while unsealed).

### 3.2 Specification Lineage (Frozen Documentation)
- `specification_version`: Must match the frozen specification version (`"v1.0-round5"`).
- `decision_surface_sha256`: SHA-256 digest of `./docs/phase14/cand_free_macro_001_human_specification_decision_surface.md`.
- `round4_specification_sha256`: SHA-256 digest of `./docs/phase14/cand_free_macro_001_round4_specification.md`.
- `binding_worksheet_sha256`: SHA-256 digest of `./docs/phase14/cand_free_macro_001_human_binding_worksheet.md`.

### 3.3 Code & Toolchain Provenance (Readiness BK)
- `git_commit_hash`: 40-character hex SHA-1 of the exact commit.
- `git_tree_dirty`: Boolean flag; must be `false` at sealing time.
- `pyproject_toml_sha256`: SHA-256 of `./pyproject.toml`.
- `uv_lock_sha256`: SHA-256 of `./uv.lock`.
- `python_version`: Verbatim string from `sys.version`.
- `platform_system`: Operating system identifier (`"Windows"`, `"Linux"`, etc.).

### 3.4 Data Sources Manifest (D17 & S-9 Binding)
Array of source items. Every source must specify:
- `source_id`: Canonical ID (`"S-01"` FOMC, `"S-02"` CPI, `"S-03"` NFP, `"S-04"` SPX Close, `"S-05"` NYSE Calendar).
- `authority_status`: `"RATIFIED_AUTHORITATIVE"` or `"DATA_AUTHORITY_BLOCKED"`.
- `retrieval_timestamp_utc`: ISO-8601 UTC timestamp of retrieval.
- `vintage_policy`: Pinned release date or as-published archive timestamp.
- `raw_artifact_sha256`: SHA-256 of the untouched downloaded raw file.
- `canonical_parquet_sha256`: SHA-256 of the canonical Arrow/Parquet part generated.
- `row_count`: Exact integer count of parsed valid records.

> [!WARNING]
> **D17 Status Notice:** In this unsealed template, `S-04` (SPX Close) is marked `authority_status: "DATA_AUTHORITY_BLOCKED"` with null hashes, reflecting ratified Human Decision **D17-E**. Real data must not be sealed until D17 is resolved.

### 3.5 Frozen Protocol Parameters (Rounds 0–5 Bindings)
- `event_universe`: `["FOMC", "CPI", "NFP"]` (Batch A1).
- `timezone`: `"America/New_York"` / US Eastern Time (Batch A2).
- `event_window`: `"W-1"` (post-announcement observation window; Round 1 D3).
- `return_formula`: `"R-EC"` exact logarithmic return $\ln(P_{\text{close}} / P_{\text{open}})$ (Round 1 D4).
- `baseline`: `"B-A"` unconditioned matched-session baseline (Round 2 D7).
- `overlap_rule`: `"O-2"` drop later event by chronological timestamp (Round 2 D8).
- `tie_break_rule`: `"TR-1"` secondary key `(calendar_date ASC, family_order ASC)` where `CPI < NFP < FOMC` (Round 4 TR-1).
- `calendar_authority`: `"CA-1"` NYSE official calendar (Round 4 CA-1).
- `parameter_grid`: `[{"cell_id": "G1_1H", "horizon_hours": 1}, {"cell_id": "G1_2H", "horizon_hours": 2}, {"cell_id": "G1_4H", "horizon_hours": 4}]` (Round 3A D11).
- `trial_count_k`: `3` (Round 3A D12).
- `is_start_date`: `"2013-12-01"` (Round 4 D14).
- `is_end_date`: `"2021-12-31"` (Round 4 D14).
- `oos_start_date`: `"2022-01-01"` (Round 4 D15).
- `oos_end_date`: `"2024-12-31"` (Round 4 D15).
- `blind_start_date`: `"2025-01-01"` (Round 4 D16).
- `blind_end_date`: `"2026-09-10"` (Round 4 D16).
- `statistical_test`: `"TWO_WAY_CLUSTERED_T_TEST"` with quarterly calendar blocks (T2) and variance-ratio effective observation formula (F2) (Round 3B S-2/S-7).
- `degrees_of_freedom`: `"G-1"` where $G$ is cluster count (Round 3B S-2).
- `alpha_significance_level`: `0.05` (Round 5 D20).
- `primary_hypothesis`: `"H0: E[D] = 0 vs H1: E[D] != 0 (Two-Sided)"` (Batch A3 / Round 5 D20).

### 3.6 Execution & Integrity Semantics
- `kill_conditions`: Ratified D19 protocol/integrity catalog (5 triggers; threshold zero-tolerance; result INVALID).
- `census_semantics`: Ratified D6 / Batch A5 (K=3 census members; mixed census fails closed; no dynamic grid expansion).
- `invalid_policy`: INVALID is not negative evidence; failures logged with non-zero failure reason code.
- `numerical_precision`: Prices stored as exact Python `Decimal`; statistical estimators evaluated in IEEE-754 64-bit float; zero artificial floors (`max(1e-12, ...)`); fail-closed on non-finite values.

---

## 4. Formal JSON Schema Specification (Draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://acash.quant/schemas/v1/macro_001_reproducibility_manifest.json",
  "title": "Macro001ReproducibilityManifest",
  "type": "object",
  "required": [
    "manifest_id",
    "schema_version",
    "candidate_id",
    "status",
    "created_at_utc",
    "specification_lineage",
    "code_provenance",
    "data_sources",
    "protocol_parameters",
    "execution_semantics",
    "manifest_sha256"
  ],
  "properties": {
    "manifest_id": { "type": "string", "pattern": "^MANIFEST_MACRO_001_[0-9]{8}_[0-9a-f]{8}$" },
    "schema_version": { "type": "string", "const": "v1.0.0" },
    "candidate_id": { "type": "string", "const": "CAND-FREE-MACRO-001" },
    "status": { "type": "string", "enum": ["DRAFT_UNSEALED", "SEALED_PRE_REGISTRATION", "SUPERSEDED", "REVOKED"] },
    "created_at_utc": { "type": "string", "format": "date-time" },
    "sealed_at_utc": { "type": ["string", "null"], "format": "date-time" },
    "specification_lineage": {
      "type": "object",
      "required": ["specification_version", "decision_surface_sha256", "round4_specification_sha256", "binding_worksheet_sha256"],
      "properties": {
        "specification_version": { "type": "string" },
        "decision_surface_sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "round4_specification_sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "binding_worksheet_sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" }
      }
    },
    "code_provenance": {
      "type": "object",
      "required": ["git_commit_hash", "git_tree_dirty", "pyproject_toml_sha256", "uv_lock_sha256", "python_version"],
      "properties": {
        "git_commit_hash": { "type": "string", "pattern": "^[0-9a-f]{40}$" },
        "git_tree_dirty": { "type": "boolean" },
        "pyproject_toml_sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "uv_lock_sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "python_version": { "type": "string" }
      }
    },
    "data_sources": {
      "type": "array",
      "minItems": 5,
      "items": {
        "type": "object",
        "required": ["source_id", "authority_status", "retrieval_timestamp_utc", "vintage_policy", "raw_artifact_sha256", "canonical_parquet_sha256", "row_count"],
        "properties": {
          "source_id": { "type": "string", "enum": ["S-01", "S-02", "S-03", "S-04", "S-05"] },
          "authority_status": { "type": "string", "enum": ["RATIFIED_AUTHORITATIVE", "DATA_AUTHORITY_BLOCKED"] },
          "retrieval_timestamp_utc": { "type": ["string", "null"], "format": "date-time" },
          "vintage_policy": { "type": "string" },
          "raw_artifact_sha256": { "type": ["string", "null"], "pattern": "^[0-9a-f]{64}$" },
          "canonical_parquet_sha256": { "type": ["string", "null"], "pattern": "^[0-9a-f]{64}$" },
          "row_count": { "type": ["integer", "null"], "minimum": 0 }
        }
      }
    },
    "protocol_parameters": {
      "type": "object",
      "required": ["event_universe", "timezone", "event_window", "return_formula", "baseline", "overlap_rule", "tie_break_rule", "calendar_authority", "parameter_grid", "trial_count_k", "is_start_date", "is_end_date", "oos_start_date", "oos_end_date", "blind_start_date", "blind_end_date", "statistical_test", "degrees_of_freedom", "alpha_significance_level", "primary_hypothesis"],
      "properties": {
        "event_universe": { "type": "array", "items": { "type": "string" } },
        "timezone": { "type": "string" },
        "event_window": { "type": "string" },
        "return_formula": { "type": "string" },
        "baseline": { "type": "string" },
        "overlap_rule": { "type": "string" },
        "tie_break_rule": { "type": "string" },
        "calendar_authority": { "type": "string" },
        "parameter_grid": { "type": "array" },
        "trial_count_k": { "type": "integer", "const": 3 },
        "is_start_date": { "type": "string", "format": "date" },
        "is_end_date": { "type": "string", "format": "date" },
        "oos_start_date": { "type": "string", "format": "date" },
        "oos_end_date": { "type": "string", "format": "date" },
        "blind_start_date": { "type": "string", "format": "date" },
        "blind_end_date": { "type": "string", "format": "date" },
        "statistical_test": { "type": "string" },
        "degrees_of_freedom": { "type": "string" },
        "alpha_significance_level": { "type": "number", "const": 0.05 },
        "primary_hypothesis": { "type": "string" }
      }
    },
    "execution_semantics": {
      "type": "object",
      "required": ["kill_conditions", "census_semantics", "invalid_policy", "numerical_precision"],
      "properties": {
        "kill_conditions": { "type": "array" },
        "census_semantics": { "type": "string" },
        "invalid_policy": { "type": "string" },
        "numerical_precision": { "type": "string" }
      }
    },
    "manifest_sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" }
  }
}
```

---

## 5. Unsealed Manifest Instance Template (MACRO-001)

```json
{
  "manifest_id": "MANIFEST_MACRO_001_20260911_00000000",
  "schema_version": "v1.0.0",
  "candidate_id": "CAND-FREE-MACRO-001",
  "status": "DRAFT_UNSEALED",
  "created_at_utc": "2026-09-11T03:45:00Z",
  "sealed_at_utc": null,
  "specification_lineage": {
    "specification_version": "v1.0-round5",
    "decision_surface_sha256": "TO_BE_COMPUTED_AT_FREEZE",
    "round4_specification_sha256": "TO_BE_COMPUTED_AT_FREEZE",
    "binding_worksheet_sha256": "TO_BE_COMPUTED_AT_FREEZE"
  },
  "code_provenance": {
    "git_commit_hash": "TO_BE_PINNED_AT_SEALING",
    "git_tree_dirty": false,
    "pyproject_toml_sha256": "TO_BE_COMPUTED_AT_SEALING",
    "uv_lock_sha256": "TO_BE_COMPUTED_AT_SEALING",
    "python_version": "3.14.0"
  },
  "data_sources": [
    {
      "source_id": "S-01",
      "authority_status": "RATIFIED_AUTHORITATIVE",
      "retrieval_timestamp_utc": null,
      "vintage_policy": "OFFICIAL_FED_SCHEDULE_ARCHIVE",
      "raw_artifact_sha256": null,
      "canonical_parquet_sha256": null,
      "row_count": null
    },
    {
      "source_id": "S-02",
      "authority_status": "RATIFIED_AUTHORITATIVE",
      "retrieval_timestamp_utc": null,
      "vintage_policy": "OFFICIAL_BLS_CPI_SCHEDULE_ARCHIVE",
      "raw_artifact_sha256": null,
      "canonical_parquet_sha256": null,
      "row_count": null
    },
    {
      "source_id": "S-03",
      "authority_status": "RATIFIED_AUTHORITATIVE",
      "retrieval_timestamp_utc": null,
      "vintage_policy": "OFFICIAL_BLS_NFP_SCHEDULE_ARCHIVE",
      "raw_artifact_sha256": null,
      "canonical_parquet_sha256": null,
      "row_count": null
    },
    {
      "source_id": "S-04",
      "authority_status": "DATA_AUTHORITY_BLOCKED",
      "retrieval_timestamp_utc": null,
      "vintage_policy": "BLOCKED_ON_D17_E_RESOLUTION",
      "raw_artifact_sha256": null,
      "canonical_parquet_sha256": null,
      "row_count": null
    },
    {
      "source_id": "S-05",
      "authority_status": "RATIFIED_AUTHORITATIVE",
      "retrieval_timestamp_utc": "2026-09-10T12:00:00Z",
      "vintage_policy": "NYSE_OFFICIAL_CALENDAR_2013_2026",
      "raw_artifact_sha256": null,
      "canonical_parquet_sha256": null,
      "row_count": null
    }
  ],
  "protocol_parameters": {
    "event_universe": ["FOMC", "CPI", "NFP"],
    "timezone": "America/New_York",
    "event_window": "W-1",
    "return_formula": "R-EC",
    "baseline": "B-A",
    "overlap_rule": "O-2",
    "tie_break_rule": "TR-1",
    "calendar_authority": "CA-1",
    "parameter_grid": [
      { "cell_id": "G1_1H", "horizon_hours": 1 },
      { "cell_id": "G1_2H", "horizon_hours": 2 },
      { "cell_id": "G1_4H", "horizon_hours": 4 }
    ],
    "trial_count_k": 3,
    "is_start_date": "2013-12-01",
    "is_end_date": "2021-12-31",
    "oos_start_date": "2022-01-01",
    "oos_end_date": "2024-12-31",
    "blind_start_date": "2025-01-01",
    "blind_end_date": "2026-09-10",
    "statistical_test": "TWO_WAY_CLUSTERED_T_TEST",
    "degrees_of_freedom": "G-1",
    "alpha_significance_level": 0.05,
    "primary_hypothesis": "H0: E[D] = 0 vs H1: E[D] != 0 (Two-Sided)"
  },
  "execution_semantics": {
    "kill_conditions": [
      "duplicate_admitted_event > 0",
      "source_binding_integrity_violation > 0",
      "calendar_session_mapping_violation > 0",
      "non_finite_statistical_input > 0",
      "protocol_invariant_violation > 0"
    ],
    "census_semantics": "D6_FROZEN_CENSUS_K3_MIXED_FAILS_CLOSED",
    "invalid_policy": "NON_NEGATIVE_EVIDENCE_FAIL_CLOSED_LOGGED",
    "numerical_precision": "DECIMAL_PRICES_FLOAT64_STATS_ZERO_MAGIC_FLOORS"
  },
  "manifest_sha256": "0000000000000000000000000000000000000000000000000000000000000000"
}
```

---

## 6. Sealing & Verification Protocol (Execution Instructions)

Once a **Human Decision** resolves D17 (selecting an authoritative SPX close data path and providing budget or source authorization):

1. **Step 1 (Source Ingestion):** Download raw data files for S-01, S-02, S-03, S-04, and S-05 into the immutable storage directory. Compute SHA-256 digests on the exact byte streams.
2. **Step 2 (Parquet Canonicalization):** Ingest raw files via `ParquetStorageEngine`, generating partitioned Parquet parts according to `CANONICAL_ARROW_SCHEMA`. Compute SHA-256 for each generated part.
3. **Step 3 (Lineage Binding):** Compute SHA-256 for `pyproject.toml`, `uv.lock`, and specification markdown files. Verify working tree is clean (`git diff --quiet`). Record `git_commit_hash`.
4. **Step 4 (Digest Sealing):**
   - Populate all fields in the JSON manifest, setting `status` to `"SEALED_PRE_REGISTRATION"` and `sealed_at_utc` to the current UTC timestamp.
   - Set `"manifest_sha256"` field to `""`.
   - Canonicalize the JSON structure (UTF-8 encoded, keys sorted alphabetically, zero extraneous whitespace: `json.dumps(obj, sort_keys=True, separators=(',', ':'))`).
   - Compute `SHA-256` of this byte sequence.
   - Store the computed hex string into `"manifest_sha256"`.
   - Write the sealed manifest to `docs/phase14/manifests/manifest_macro_001_sealed.json`.
5. **Step 5 (Checklist Gate):** With D18 manifest sealed, update checklist item 20 to checked (`[x] Manifest schema frozen → D18 sealed`).
6. **Step 6 (Pre-Registration Draft Freeze):** Submit Draft Freeze Candidate to Human Governance for Anti-HARKing review and explicit authorization.

---

## 7. Gating Invariants (Strictly Preserved)

- Pre-registration status remains: **NOT FULLY FROZEN** (24/26 items checked; D18 unsealed; Human authorization pending).
- Empirical validation status remains: **NOT AUTHORIZED**.
- Backtest status remains: **LOCKED**.
- Capital authority remains: **$0.00**.
