# ACASH Line Ending & Cryptographic Hash Convention Register

**Date Context**: 2026-09-30  
**Scope**: HYP_006, HYP_007, HYP_009, HYP_011 Sealed Manifests & Reproducibility  
**Authority**: Cryptographic Lineage & Canonical Git Tree Standard

---

## 1. Executive Summary & Core Invariant

In heterogenous operating environments (e.g., Windows development workstations with `core.autocrlf = true` versus Linux homelab / CI servers with LF), newline representation divergence can break raw byte cryptographic hashes (`read_bytes()`).

### Non-Negotiable Governance Invariants
1. **Zero Retroactive Mutation**: Historical manifest digests (`manifest_sha256`, `spec_sha256`, `dataset_sha256`) sealed into decision records and Git history must **NEVER** be recalculated or retroactively altered.
2. **Canonical Line Feed (LF) Standard**: The canonical point of authority for all cryptographic hashes across ACASH is the raw binary `\n` (LF, ASCII 0x0A) byte sequence.
3. **Explicit Newline Serialization**: All runtime and tooling code writing JSON manifests, observation artifacts, or cryptographic ledgers must explicitly specify `newline="\n"` and `encoding="utf-8"`.

---

## 2. Platform Line Ending Matrix

| Environment | Git `core.autocrlf` | Checkout Format | Repository Storage | Raw `read_bytes()` Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Linux Homelab / CI** | `false` / `input` | `\n` (LF) | `\n` (LF) | Direct byte match with Git blob |
| **Windows Dev Workstation** | `true` | `\r\n` (CRLF) | `\n` (LF) | Divergent raw hash unless normalized or Git-blob derived |
| **Windows Isolated Git** | `false` | `\n` (LF) | `\n` (LF) | Direct byte match with Git blob |

---

## 3. Registered Manifest Conventions by Hypothesis

### 3.1 HYP_006 (EOD Momentum / Execution Timing)
- **Primary Manifests**:
  - `docs/phase14/manifests/manifest_r1_HYP_006.json`
  - `docs/phase14/manifests/HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001.json`
- **Spec Mirrors**:
  - `docs/phase8.5/hypotheses/HYP_006.json`
  - `docs/phase14/hypotheses/HYP_006.json`
- **Validation Invariant**:
  - `test_5_hyp_006_r1_spec_and_manifest_sealed` enforces byte-identical mirror equality between Phase 8.5 and Phase 14 specifications.
  - Windows checkout must preserve identical line endings across both files (both CRLF or both LF) to satisfy mirror equality.

### 3.2 HYP_007 (Noise Reduction / Trend Following)
- **Primary Manifests**:
  - `docs/phase14/manifests/manifest_r1_HYP_007.json`
  - `docs/phase14/manifests/manifest_r2_HYP_007.json`
  - `docs/phase14/manifests/manifest_r3_HYP_007.json`
  - `docs/phase14/manifests/manifest_r3_HYP_007_CORRECTED_001.json`
  - `docs/phase14/manifests/HYP_007_R4_M2_DATASET_MANIFEST.json`
  - `docs/phase14/manifests/HYP_007_R4_M2_RESULT_MANIFEST.json`
- **Validation Invariant**:
  - Dataset and result SHA-256 digests bind immutable historical data and simulation traces.
  - Canonical hash evaluation uses raw binary hash matching Git object trees.

### 3.3 HYP_009 (Low-Volatility Factor / Multi-Asset Allocation)
- **Primary Manifests**:
  - `docs/phase14/manifests/manifest_r1_HYP_009.json`
  - `docs/phase14/manifests/HYP_009_R2_M1_DATASET.json`
  - `docs/phase14/manifests/HYP_009_R2_M1_RESULT.json`
  - `docs/phase14/manifests/HYP_009_R2_M1_REPRODUCIBILITY_RESULT.json`
  - `docs/phase14/manifests/HYP_009_R2_M2_DATASET.json`
  - `docs/phase14/manifests/HYP_009_R2_M2_RESULT.json`
- **Validation Invariant**:
  - `test_phase14_step_r1_hyp_009.py` checks `manifest_self_hash_and_pins` and `strategy_specification_hash`.
  - Canonical tokens are validated against normalized LF content in test execution.

### 3.4 HYP_011 (Prospective Shadow SIP Recovery)
- **Primary Manifest**:
  - `docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C_B.json`
- **Sealed Digest**:
  - `eea52f69ccc97ece80c03e87780e110031d54db6ec4087b2a79480b7b45ed46f`
- **Line Ending Status**:
  - The production Stage C-B manifest on `origin/main` (`becec27f...`) is verified LF-encoded (992 bytes).
  - Its SHA-256 evaluates strictly to `eea52f...` under binary read on LF and via Git blob hash.

---

## 4. Verification and Normalization Standard

When reading JSON manifests or specifications for cryptographic verification in test or audit suites:
```python
def compute_canonical_sha256(path: Path) -> str:
    """Compute canonical SHA-256 by normalizing line endings to LF (\n)."""
    raw_bytes = path.read_bytes()
    # Normalize CRLF (\r\n) to LF (\n) to guarantee cross-platform identity
    normalized = raw_bytes.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()
```

When writing observation or state artifacts to disk (`append_observation`, `atomic_write_json`):
```python
with open(tmp_file, "w", encoding="utf-8", newline="\n") as handle:
    handle.write(json_content)
```
This guarantees that regardless of operating system, all artifacts written to disk are strictly LF-terminated.
