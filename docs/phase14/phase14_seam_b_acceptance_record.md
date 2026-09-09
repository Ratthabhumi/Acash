# PHASE 14 — SEAM B HUMAN ACCEPTANCE RECORD

**Document ID:** `docs/phase14/phase14_seam_b_acceptance_record.md`
**Type:** Canonical governance acceptance record — [HUMAN-RATIFIED] decision recorded verbatim; NOT agent-authored governance.
**Status:** `[HUMAN-RATIFIED]` — SEAM_B_OPTION_A = ACCEPTED
**Date:** 2026-09-08
**Authority:** `./AGENTS.md`, `./phase14_gate14_acceptance_record.md` (Gate 14 = ACCEPTED),
`./phase14_s5_test_only_acceptance_record.md` (S5 = ACCEPTED),
`./phase14_master_research_architecture_plan.md`, `./phase14_architecture_and_governance_plan.md`
**Decision origin:** Seam B Option A implementation (trusted causal feature materialization) delivered and
audited; formal human acceptance supplied explicitly in the human acceptance prompt of 2026-09-08.

> [!CAUTION]
> ### GOVERNANCE BOUNDARIES OF THIS RECORD
> - **This record records Seam B Option A acceptance ONLY** — the bounded "trusted causal feature
>   materialization capability."
> - **It is NOT production integration authorization, NOT strategy qualification, NOT hypothesis
>   registration, and NOT trading authorization.** The Phase 14 research pipeline is NOT production-ready,
>   NOT runtime-enabled, NOT strategy-qualified, and NOT authorized for trading by this acceptance.
> - **SEAM B ACCEPTANCE ≠ END-TO-END PHASE 4→5→6→8.5 LINEAGE AUTHORIZATION ≠ STRATEGY
>   QUALIFICATION ≠ TRADING AUTHORITY.**
> - A materialized feature proposal is a **bounded research data-plumbing artifact only**. It is NOT
>   automatically a hypothesis, a registered hypothesis, a validated strategy, a qualified alpha, a
>   paper-trading strategy, or a live-trading strategy.
> - `ResearchManifest.features_manifest_hash` remains **UNRESOLVED** and is explicitly NOT resolved by
>   this record (see §4).
> - This record is a documentation-only change. It does not modify any source file, test file, runtime
>   wiring, schema, F-1, Retrieval, E9, the Hypothesis registry, R1 artifacts, gate state, or any
>   authority-bearing subsystem.
> - The deferred Phase 5 study-identity/lineage seam (Seam A, `HYP-PHASE5-POC`) remains **DEFERRED** and
>   is NOT resolved by this acceptance.

---

## 1. Human decision (recorded verbatim)

> **DECISION: `SEAM B OPTION A = ACCEPTED`**
>
> This acceptance applies ONLY to the trusted causal feature materialization capability implemented in
> the previously authorized Seam B slice:
>
> ```
> AIFeatureProposal
>   → trusted causal materialization
>   → deterministic PyArrow feature output
>   → causal/lookahead enforcement
>   → provenance and digest verification
>   → Phase 4-compatible feature-table output
> ```

Scope of acceptance: **"trusted causal feature materialization capability"** — a bounded research
data-plumbing capability. It does **NOT** mean that a feature proposal is a hypothesis, a registered
hypothesis, a validated strategy, a qualified alpha, a paper-trading strategy, or a live-trading
strategy. No end-to-end lineage authorization is implied.

## 2. Accepted implementation surface

| File | Change |
|---|---|
| `src/acash/research/ai/features/materializer.py` | NEW — trusted causal materializer + provenance contract |
| `src/acash/research/ai/features/__init__.py` | MODIFIED — materializer exports only |
| `tests/unit/research/ai/test_feature_materializer.py` | NEW — 67 Seam B tests (Groups A–H) |

## 3. Accepted verification evidence

The reported verification evidence is accepted:

| Evidence item | Result |
|---|---|
| Seam B targeted suite | **67 passed** |
| AI unit suite (`tests/unit/research/ai`) | **307 passed** |
| Full repository regression | **1880 passed, 1 skipped** |
| Pre-existing warnings | **3 pre-existing, unchanged** |
| Full-tree mypy strict (`uv run mypy src/ tests/`) | **360 files clean** |
| Security boundary scan | **PASS** (whitelist-only evaluator; no eval/exec/dynamic import; no forbidden subsystem import) |
| Determinism / provenance audit | **PASS** (same input → identical output/digest; source/formula mutation detected; canonical hasher match) |
| Forbidden authority subsystem touched | **NONE** |
| Commit / push performed | **NONE** |

## 4. CRITICAL CONTRACT BOUNDARY — `features_manifest_hash` remains UNRESOLVED

Explicitly recorded — **do not treat this field as resolved by Seam B acceptance.**

Facts (from repository source):
- `ResearchManifest.features_manifest_hash` is an existing source field: `Optional[str] = None`
  (`src/acash/research/ai/schema.py`).
- It participates in `ResearchManifest` canonical digest computation and integrity verification.
- **No canonical producer/consumer binding currently exists** — nothing populates or consumes it.
- Documentation describes it as a required string field (doc-vs-source divergence).
- Therefore the binding contract for this field is **not yet canonical**.

**Boundary:**
- DO NOT resolve this field in this acceptance record.
- DO NOT modify `schema.py`.
- DO NOT create a producer for this field.
- DO NOT redefine what this field hashes.

This field remains a **separate future human decision surface**. Seam B acceptance does not require it
for the bounded materialization capability: causality, determinism, provenance self-seal, Phase 4 output
compatibility, and inbound security are fully satisfied independently of it.

## 5. Explicit non-authorization (preserved exactly)

This Seam B acceptance does **NOT** authorize:

- Phase 4→5→6→8.5 end-to-end orchestration
- Phase 5 changes
- Phase 6 changes
- Phase 8.5 changes
- HYP_003
- R1
- hypothesis registration
- strategy qualification
- Strategy Admission
- broker access
- order execution
- portfolio/risk changes
- capital authority
- trading
- runtime research activation
- resolution or producer creation for `features_manifest_hash`

## 6. Invariant matrix (verified post-write)

| Invariant | State |
|---|---|
| HYP_003 | ABSENT |
| R1 | NOT STARTED |
| Trading | LOCKED |
| Capital | $0.00 |
| Broker | DISCONNECTED / NO AUTHORITY |
| Seam A (Phase 5 identity / HYP-PHASE5-POC) | DEFERRED |
| S5 | ACCEPTED |
| Gate 14 | ACCEPTED |
| F-1 | UNCHANGED |
| Retrieval | EXCLUDED / UNRESOLVED |
| E9 | DEFERRED |
| `features_manifest_hash` | UNRESOLVED |
| Production runtime wiring | NOT AUTHORIZED |

## 7. End-to-end boundary

Seam B acceptance means the feature materialization capability is accepted as a **bounded research
data-plumbing capability**. It does **NOT** mean that a feature proposal is:

- a hypothesis
- a registered hypothesis
- a validated strategy
- a qualified alpha
- a paper-trading strategy
- a live-trading strategy

**No end-to-end Phase 4→5→6→8.5 lineage authorization is implied.**

## 8. Final state

```text
SEAM B (OPTION A) = ACCEPTED  — trusted causal feature materialization capability
features_manifest_hash        = UNRESOLVED (future human decision surface)
SEAM A                        = DEFERRED
S5                            = ACCEPTED
Gate 14                       = ACCEPTED
HYP_003                       = ABSENT
R1                            = NOT STARTED
Trading                       = LOCKED
Capital                       = $0.00
NO NEW AUTHORITY
```

**HYP_003 is not created. R1 is not started. No canonical gate is invoked. No source, test, schema,
runtime wiring, or governance-field contract is modified. No commit or push is made.** The remaining
Seam A (Phase 5 study identity / `HYP-PHASE5-POC` lineage) and the `features_manifest_hash` decision
surface are the subject of separate, future human decisions — prepared only after the human reviews
this acceptance record.

### Verification Ledger
- Implementation Status: COMPLETE (Seam B Option A — trusted causal feature materialization)
- Contract Enforcement: STRICT FAIL-CLOSED (materializer security boundary + provenance + causality)
- Mathematical Authority: CANONICAL SPEC (reuses canonical operators, validator, table hash, serializer; no invented digest)
- Local Test Suite: VERIFIED (Seam B 67 passed; AI 307 passed; full regression 1880 passed, 1 skipped, 3 pre-existing warnings)
- Type Checker (MyPy): VERIFIED (360 files clean, strict)
- Remote CI Status: PENDING / NOT AVAILABLE
- Methodological Caveats: Acceptance covers ONLY the bounded Seam B materialization capability and its enumerated evidence. `features_manifest_hash` remains UNRESOLVED (no canonical producer/consumer contract exists; not required for the accepted capability). Seam A remains DEFERRED. No end-to-end lineage, production integration, strategy qualification, or trading authorization is implied. This record is documentation-only; no source/test/schema/runtime-wiring/authority change was made. No commit/push performed.
