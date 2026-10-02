# Evidence Kernel V1 — Platform Acceptance Checklist (Frozen)

**Date Context**: 2026-10-01
**Status**: `LOCALLY_ACCEPTED_PENDING_GREEN_REMOTE_CI` (corrected
2026-10-02: `MERGE_READY` was premature — no remote CI exists and the
reported T1 had 71 failures). `MERGE_READY` returns only when fresh-clone
T1 = 0 failed AND GitHub Actions T1 + MyPy both succeed. This checklist
freezes what "Evidence Kernel V1" means for canonical-merge readiness. Broader package extraction is
explicitly deferred: `EXTRACTION_PLAN = READY_AFTER_CANONICAL_MERGE`
(see `docs/audit/EVIDENCE_KERNEL_EXTRACTION_PLAN.md` for the deferred plan —
no extraction is performed by this checklist).

---

## 1. Acceptance Items (All Required)

| # | Item | Implementation | Proof |
|---|---|---|---|
| 1 | Immutable state/observation verification | `verify_chain()` hash-linked walk + F01 terminal-economics reconciliation | `test_hyp011_audit_reproductions.py` (11), Obs #1-shaped fixture passes |
| 2 | Registered intent | `register_observation_intent()` O_EXCL + `validate_observation_intent()` pre-open lock | `test_f17_*` (7) |
| 3 | Dispatch authority | `validate_dispatch_authority()` (intent/runtime/CA/expiry/locks binding) | `test_f15_*` + continuity ceremony |
| 4 | Attempt ledger | `consume_dispatch_attempt()` O_EXCL single-use, read-only replay gate | F18 tests (consume-once, no-burn pre-validation, crash-burn, preflight) |
| 5 | Evidence digest | SHA-256 recompute over preserved bytes; invented digests rejected | `test_f19_*` digest tests |
| 6 | Semantic source identity | `derive_evidence_identity_markers()` from evidence body (ticker/product/CUSIP/sponsor); manifest-only trust rejected | `test_f19_iwb_bytes_behind_acwi_manifest_blocked`, genuine-marker + real-file tests |
| 7 | CA evidence bundle | Per-symbol manifest + evidence + schedule digests; determination binding | `test_f19_valid_bundle_and_binding_pass` + full-ceremony seal |
| 8 | Zero-network local preflight | `--local-preflight` validates everything without ledger burn or network | `test_f18_local_preflight_pass_without_consume_or_network` |
| 9 | No Paper/Live/real capital | Locks enforced in Stage C-B loader, authority manifests, state docs, and runner gates | F09 tests + `test_locks_intact` + surface `order_controls is None` |
| 10 | Retrieval honesty | `retrieval_representation` required (`NORMALIZED_RETRIEVAL_REPRESENTATION` vs `RAW_HTTP_BODY`); no false byte-identity claims | `test_f19_missing/unknown_representation_blocked` |

## 2. Explicitly Out of Scope for V1

- Generalized Evidence Kernel package extraction (deferred per extraction plan).
- HYP_011 V2 activation, Obs #2 dispatch, timers, homelab deployment.
- RI-01 feasibility execution; PPDS beyond the read-only skeleton.
- CI rulesets/branch protection (to be enabled after a green run exists).
- External timestamp receipts (e.g. RFC 3161) — noted as a future
  trust-reduction direction, not implemented.

## 3. Merge-Readiness Verdict (To Be Filled by Validation)

```text
EVIDENCE_KERNEL_V1 = REMOTE_CI_VERIFIED_MERGE_READY
CANONICAL_MERGE = NOT_YET_AUTHORIZED
```

Remote CI proof (repair branch, commit `8dd710e`):
- GitHub Actions run **37029140943**: T1 hermetic pytest SUCCESS
  (3079 passed, 28 skipped, 56 deselected, 0 failed) + MyPy strict
  SUCCESS (564 files clean).
- Canonical `origin/main` remains
  `becec27f5eacf283dcb191cf72d0858682d8e055`. No merge performed here;
  merge requires a separate explicit human authorization.

Validation record (repair branch, commits through `cc57c36`):
- HYP_011 family + PPDS in a FRESH worktree (`uv sync --locked`, no hidden
  files): **153 passed**.
- NON_MT5_DIAGNOSTIC_SUITE in the fresh worktree: 71 failed / 3070 passed /
  18 skipped / 4 deselected — SUPERSEDED by
  `docs/audit/T1_FAILURE_CLASSIFICATION_20261002.md` (per-test census:
  52 sealed-data, 12 repaired via `.gitattributes`, remainder analyzed;
  "pre-existing" is a regression-comparison note, never a green gate).
- `mypy src/ tests/`: **Success, 564 files** (including the MetaTrader5
  optional-dep override fix that un-breaks fresh-checkout typing).
- `git diff --check`: clean.
- No homelab access, no Alpaca calls, no broker, no capital, no production
  artifact mutation in this validation.
