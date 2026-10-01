# Evidence Kernel Extraction Plan (design — no package move yet)

**Direction**: `Research experiments -> Evidence Kernel`.
**Rule**: the Evidence Kernel MUST NOT import HYP_011 (or any experiment).
HYP_011 becomes the first consumer/adaptor, not the architecture.

## 1. Candidate generic interfaces (already implemented under hyp_011/)

| Generic interface | Current location | Generic? |
|---|---|---|
| `EvidenceDigest` (canonical SHA-256 over canonical JSON) | `acash.core.serialization.CanonicalConfigSerializer` + local `_canonical_sha256` helpers | YES — already generic |
| `SourceIdentity` (sponsor + product identity binding) | `shadow_ca.SPONSOR_BY_SYMBOL` + `shadow_ca_bundle.PRODUCT_IDENTITY_BY_SYMBOL` | Split: sponsor map is HYP_011-specific; the *mechanism* (frozen identity table + exact-match enforcement) is generic |
| `RegisteredIntent` (create-once pre-session attestation) | `shadow_authority.register/load/verify_registered_intent_binding` | YES — parameterize `hypothesis_id`, intent payload schema |
| `DispatchAuthority` (single-use binding: intent + runtime + evidence + window + locks) | `shadow_authority.validate_dispatch_authority` | PARTIAL — validity window + locks are generic; runtime-SHA + CA-manifest bindings are experiment-supplied payload |
| `AttemptLedger` (O_EXCL single-use consumption) | `shadow_authority.consume_dispatch_attempt` | YES — already key-agnostic |
| `EvidenceBundle` (manifest + raw bytes + recomputed digests) | `shadow_ca_bundle.verify_evidence_bundle` | YES — parameterize identity table + scope rules |
| `ExperimentRegistry` (chain head + observed-session ledger) | `shadow_ops.verify_chain/append_observation` | PARTIAL — hash-chain mechanics generic; economic reconciliation is HYP_011-specific |

## 2. Proposed target package (future)

`src/acash/evidence_kernel/` — pure, dependency-free (stdlib +
`acash.core.domain.exceptions` + serialization only):

- `digest.py` — canonical JSON SHA-256.
- `registry.py` — generic create-once artifact registry (O_EXCL,
  server-side timestamp, pre-event cutoff as injected predicate).
- `ledger.py` — generic single-use consumption ledger.
- `bundle.py` — generic evidence bundle (manifest + raw bytes +
  recomputed digests + caller-supplied identity predicate).
- `authority.py` — generic binding validator skeleton (validity window,
  locks) with experiment-supplied binding checks.

## 3. Compatibility migration strategy

1. Extract byte-identical logic first (move, no behavior change), proven by
   the existing HYP_011 adversarial suites running unmodified.
2. Parameterize experiment specifics behind small adaptor modules
   (`hyp_011_evidence_adaptor.py`: sponsor map, product identities,
   economic reconciliation, calendar predicates).
3. HYP_011 test suite must pass unchanged against the adaptor (except
   import paths) before any second consumer (RI-01, PPDS) is admitted.
4. No broad move is performed in the current pack: this plan is design
   only. A move commit must separately prove behavior preservation
   (identical test outcomes + pristine-baseline comparison).

## 4. Acceptance boundary for the move

- All HYP_011 adversarial suites green on the new import paths.
- `Evidence Kernel MUST NOT import HYP_011` enforced by a static
  import-direction test.
- No network, no broker, no capital code enters the kernel package.
