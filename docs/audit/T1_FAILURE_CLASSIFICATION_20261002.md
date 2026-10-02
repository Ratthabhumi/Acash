# T1 Failure Classification — 2026-10-02 (fresh-clone census)

**Method**: fresh detached worktree at `e8fd46c`, `uv sync --locked`,
T1 command exactly:

```text
uv run pytest -q --tb=line \
  -m "not non_hermetic and not native_mt5 and not sealed_data and not dashboard" \
  --ignore=tests/unit/execution/mt5
```

**Before**: 70 failed / 3071 passed / 18 skipped / 4 deselected.
Every failure below was reproduced from source/test behavior, never
classified merely because it fails. No blanket file-level markers: all
tiers are per-test, except none (every affected file mixes tiers).

## Class B — sealed_data (52 tests): untracked data absent from fresh clones

Proof pattern (identical for all 52): the test requires a file under
`data/parquet/research/`, `data/hyp_009/`, `data/hyp_007/`, or
`data/manifests/research/`. `git ls-files` proves **zero tracked files**
under all four directories — no fresh clone can satisfy them. They pass
in checkouts carrying the operator's local untracked data mirror.

| Test | Missing path (proof) |
|---|---|
| `test_hyp_004_log_return_robustness.py` ×13 (`test_01`, `test_02`, `test_03`, `test_04`, `test_05`, `test_06`, `test_09`, `test_10`, `test_12`, `test_13`, `test_18`, `test_19`, `test_21`) | `data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet` / `…_R3_primary_returns.parquet` (`FileNotFoundError` / `R2/R3 … does not exist`) |
| `test_phase14_hyp_009_m1_g6_reconciliation.py::test_m1_g6_evidence_reconciled_pass` | `data/hyp_009/m1_dataset_reproducibility_001.json` (`missing sealed artifact`) |
| `test_phase14_hyp_009_m2_readiness.py::test_dec2020_frozen_state_binding` | `data/hyp_009/signal_ledger_reproducibility_001.json` (`FileNotFoundError`) |
| `test_phase14_hyp_009_r2_m1_reproducibility.py` ×2 | `data/hyp_009/m1_dataset_reproducibility_001.json`, `…/signal_ledger_reproducibility_001.json` |
| `test_phase14_hyp_009_r2_m1_seal.py::test_sealed_files_cr_free_and_hashes_match` | `data/hyp_009/signal_ledger.json` (`FileNotFoundError`) |
| `test_phase14_hyp_009_r2_m2_corrected_seal.py` ×3 | `data/hyp_009/m2_dataset_dividend_corrected_001.json`, `data/hyp_009/m2_signal_ledger_dividend_corrected_001.json` |
| `test_phase14_hyp_009_r2_m2_seal.py` ×3 | `data/hyp_009/m2_dataset.json`, `data/hyp_009/m2_signal_ledger.json` |
| `test_phase14_step_r1_hyp_004.py::test_12/test_13` | `data/manifests/research/hypotheses/HYP_004.json`, `…/manifest_r1_HYP_004.json` |
| `test_phase14_step_r1_hyp_005.py::test_4/test_5` | `data/manifests/research/hypotheses/HYP_005.json`, `…/manifest_r1_HYP_005.json` |
| `test_phase14_step_r1_hyp_006_amendment_001.py::test_2` | `data/manifests/research/HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001.json` (`exists()` False) |
| `test_phase14_step_r1_hyp_007_amendment_001.py::test_2` | `data/manifests/research/HYP_007_R1_FRICTION_CORRECTION_AMENDMENT_001.json` (`exists()` False) |
| `test_phase14_step_r3_hyp_003.py::test_gate1_r2_dataset_hash_verification` | `data/parquet/research/HYP_003_SPY_1Min_IS_canonical.parquet` (`Canonical dataset not found`) |
| `test_phase14_step_r3_hyp_004.py::test_12/test_1/test_2` | `data/parquet/research/HYP_004_MEC0014A_R2_session_endpoints.parquet` |
| `test_phase14_step_r3_hyp_007_execution.py::test_deterministic_r3_reproducibility` | `data/hyp_007/` qualified Parquet evidence (`not found in data/hyp_007/`) |
| `test_phase14_step_r4_hyp_004.py` ×15 | `data/parquet/research/HYP_004_MEC0014A_R2/R3_*.parquet` (same two files) |
| `test_phase14_step_r4_hyp_007_execution.py::test_r4_preconditions_stage_a_verified` | `data/hyp_007/m1_bars_qualified.parquet` |
| `test_phase14_step_r4_hyp_007_failure_decomposition.py::test_sealed_repo_load_and_full_decomposition_runs` | `./data/hyp_007/m1_trade_ledger.parquet` |

Action: per-test `@pytest.mark.sealed_data` with inline proof path
(52 markers, 18 files). Before: FAIL. New tier: deselected from T1.

## Class C — repaired, not tiered (12 tests): LF-pinned seals vs CRLF blobs

Proof: pinned SHA == SHA256(LF-normalized bytes) exactly (verified per
file); CRLF blob SHA appears in no pin anywhere tracked (verified by
corpus scan). Genuine F03 defect, repaired by targeted `.gitattributes`
(`text eol=lf` on exactly the 63 LF-pinned paths) — no test touched:

`test_phase14_hyp_005_block_and_hyp_006_preinception.py::test_1/test_2`,
`test_phase14_hyp_011_post_r1_reconciliation.py::test_prospective_timestamp_authority`,
`test_phase14_step_r1_hyp_004.py::test_9`, `test_phase14_step_r1_hyp_005.py::test_6`,
`test_phase14_step_r1_hyp_005_amendment_001.py::test_1/test_2`,
`test_phase14_step_r1_hyp_010.py::test_manifest_self_hash_and_pins`,
`test_phase14_step_r1_hyp_011.py::test_manifest_self_hash_and_pins`,
`test_phase14_step_r2_hyp_003.py::test_gate1_governance_preconditions_verified`,
`test_phase14_step_r2_hyp_004.py::test_1_governance_preconditions_verified`,
`test_phase14_step_r4_hyp_007_governance.py::test_manifest_and_doc_integrity`.

Before: FAIL (any checkout). After: PASS (any checkout). New tier: T1.

CRLF-pinned artifacts (`docs/phase14/hypotheses/HYP_006/007/009.json`,
8.5 copies, SSGA/fee-schedule manifests) intentionally untouched: their
pins match blob bytes and their tests are green.

## Not separately tiered (2 tests investigated, covered by above)

- `test_phase14_step_r1_hyp_005_amendment_001.py::test_4_ssga…`: pins
  CRLF-form bytes; green in CRLF checkouts (a whole-tree LF normalization
  done purely as a census experiment broke it; the tree was never modified).
  No marker needed.
- `test_hyp_004_log_return_robustness.py::test_01_all_upstream_hashes_pinned`:
  fails in fresh clones on the missing R2 dataset (Class B, marked above);
  its pin aspects are CRLF-form and need no separate tier.

## Class H — observed transient, NOT tiered (gate_b, 5 tests)

`test_gate_b_admission.py` ×4 + `test_gate_b_e2e_lifecycle.py` ×1 failed
in full-suite runs and passed in isolation (8.89s), file scope (27 passed),
directory scope (147 passed), and 6/6 stress loops — varying sets across
runs. Load-dependent behavior, unrelated to this pack (no gate_b file
touched). No marker added: hiding load-flakes with markers is forbidden;
final T1 rerun below shows the suite disposition. If they recur in remote
CI, they become a standalone defect, not a tiering exercise.

## Resulting T1 disposition

- Fresh-clone T1 after this pack: 0 failed expected (verified in Phase 4).
- Deselected: pre-existing 4 + 52 sealed_data = 56.

## Addendum 2026-10-02 — platform-hermeticity repairs (CI ubuntu/Python 3.12)

Remote CI (run 37018838519) exposed two further genuine hermeticity gaps,
both repaired on the branch (no tiering — real defects):

1. **94 collection errors, `NameError: RestrictionAdmissionGate`**:
   `src/acash/execution/operational_restriction.py` used an unquoted
   forward reference (`-> RestrictionAdmissionGate`, class defined later)
   without `from __future__ import annotations`. Python 3.14 defers
   annotation evaluation (PEP 649) so local runs passed; CI's Python 3.12
   evaluates eagerly at def time. Root cause proven by version switch;
   fix proven by 94→0 collection errors on 3.12. (Repo convention is
   future-annotations, e.g. `gate_b/storage.py`.)
2. **12 mypy errors (Win32-only ctypes APIs)** in `gate_b/manifest.py`,
   `gate_b/storage.py`, `test_gate_b_governance_repair.py`: `os.name`
   guards satisfy runtime but not static typing on Linux. Repaired with
   `sys.platform == "win32"` narrowing (runtime-identical) + runtime
   skips for Windows-only NTFS/Authenticode tests. Verified
   `mypy src/ tests/` clean on Windows host AND `--platform linux`.
3. **`test_no_forbidden_access_mocks` UnboundLocalError on ≤3.13**: nested
   `def _boom(request: httpx.Request)` preceded a function-local
   `import httpx`, making the annotation's name local-but-unbound at def
   time (lazy on 3.14 only). Repaired by dropping the redundant local
   import (module already imports httpx).

## Addendum 2026-10-02 — remote-CI round 2 (run 37026947850)

MyPy strict went SUCCESS. T1 failed with 12, all analyzed:

1. **3 gate_b NTFS-semantics tests** (`e2e_storage_root_is_proven_physical_ntfs`,
   `e2e_full_lifecycle_and_zero_ram_restart`,
   `directory_flush_on_read_only_directory_fails_closed`): assert physical
   NTFS behavior (volume provenance, win_error=5 on read-only flush)
   impossible on posix. Runtime `pytest.skip` on non-Windows added
   (Windows behavior unchanged); no static or logic change.
2. **9 byte-audit tests pinning CRLF worktree bytes** (HYP_009 record
   `fb85…`, SSGA manifest `0f99…`, HYP_006/007 `30d6…`/`912a…`,
   bar-provider `4b2c…`, R2-HYP-007 raw-SHA `c77b…`, etc.): committed blobs
   are LF-only (verified from the git object store); these pins match
   Windows-autocrlf checkout bytes only and can never pass on LF
   checkouts. Repaired by targeted `.gitattributes` `text eol=crlf` on
   exactly the 15 CRLF-pinned paths (LF-form digests of those files appear
   nowhere tracked — verified blast-free). No seal, test, or pin edited.

Remote-CI verification matrix (fresh worktree at final commit):
- T1 on CPython 3.14.3: 3089 passed / 0 failed / 56 deselected.
- T1 on CPython 3.12.13: 3089 passed / 0 failed / 56 deselected.
- `mypy src/ tests/`: clean (564 files), host + `--platform linux`.

## Addendum 2026-10-02 — remote-CI round 4 (final byte-audit sweep)

The round-3 corpus scan covered tests+manifests only and missed pins living in src/. A full-corpus scan (all tracked text) found 4 more CRLF-pinned paths (manifest_r1_HYP_007.json — the round-3 R1-manifest raw-SHA failure — plus search_trial_ledger_HYP_003.json, manifest-EURUSD_H4_2021_2024_canonical.json, MEC-0014-transaction-contract-manifest.json) plus 4 dual-pinned layer_b_evidence_*.json files (both forms referenced somewhere; left entirely untouched — no T1 test asserts either form against disk bytes). Appended to .gitattributes (82 entries total). No seal/test/pin edited.
