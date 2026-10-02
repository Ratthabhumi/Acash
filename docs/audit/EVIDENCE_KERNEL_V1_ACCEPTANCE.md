# Evidence Kernel V1 — Platform Acceptance Checklist (Frozen)

**Date Context**: 2026-10-01
**Status**: `FROZEN_FOR_MERGE_REVIEW`. This checklist freezes what "Evidence
Kernel V1" means for canonical-merge readiness. Broader package extraction is
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
EVIDENCE_KERNEL_V1 = MERGE_READY / BLOCKED   <- §8 validation decides
```
