# PHASE 14 — D6 MINIMUM SCHEMA DECISION REQUEST (STOP ARTIFACT)

**Document ID:** `docs/phase14/phase14_d6_schema_decision_request.md`
**Type:** STOP / decision-surface artifact (NOT a governance freeze record — see
`./phase14_d5_d6_ratification_record.md`).
**Status:** `D6 FAILED-TRIAL REPRESENTABILITY = UNSATISFIABLE UNDER CURRENT SCHEMA · AWAITING HUMAN SCHEMA DECISION`
**Date:** 2026-09-09

---

## 1. Why D6 stops here

The ratified D6 failed/crashed trial rule requires that every pre-registered trial REMAINS in the
census with an explicit status preserving:

`REGISTERED + EXECUTED SUCCESSFULLY` / `REGISTERED + FAILED` / `REGISTERED + INVALID`

and forbids: removal, return = `0` fabrication, fabricated performance, replacement, K shrinkage,
retry-as-different-identity, and any new financial-return convention for failed trials.

The ratified rule then states verbatim:

> **If the existing `SearchTrialRecord`/`SearchTrialLedger` schema cannot represent this status
> without schema change, STOP and report the minimum required schema decision rather than
> inventing semantics.**

Stage 2 audit verified against `src/acash/validation/schema.py` that this representation is
IMPOSSIBLE without a schema change. This document reports that STOP with the minimum decision.

## 2. Verified evidence (source, not walkthrough)

`SearchTrialRecord` (`validation/schema.py:70-106`) declares all evidence fields as NON-optional
Pydantic fields with no `None` escape hatch and no status field:

```text
strategy_id, hypothesis_id, trial_id             (identifiers)
feature_names, parameters                        (trial design)
in_sample_sharpe: Decimal
p_value: Decimal
p_value_input_hash: str
in_sample_return_series_sha256: str
execution_manifest_id: str                       (mandatory evidence)
created_at_utc: str
```

- `SearchTrialRecord.create()` (`schema.py:253-338`) derives `p_value` / `p_value_input_hash` /
  `in_sample_return_series_sha256` from a real in-sample return series. A crashed/invalid trial has
  no truthful return evidence, so it cannot be materialized without fabricating values (forbidden)
  or inventing semantics (forbidden).
- `compute_ledger_digest()` (`schema.py:388-468`) hashes `in_sample_sharpe` and `p_value` directly
  for every record; `SearchTrialLedger.trials` is an order-locked rich sequence.
- The Phase 6 gate couples K to the census: `K = DSR trials = Holm trials = |trials|` with the
  matrix↔ledger order binding (`validation/gate.py:343-412`). Any sibling side-census would break
  the `K_ledger == K_DSR == K_Holm` single-authority contract.
- Downstream K accounting consumes `len(ledger.trials)`; pre-registered-but-failed trials must be
  counted, so the census itself (not a side table) must hold them.

**Conclusion (verified): REGISTERED+FAILED and REGISTERED+INVALID cannot be represented under the
current schema without a schema change.**

## 3. Minimum required schema decision (enumerated options; NO invention)

The minimal, single-authority-preserving design adds a trial `status` field and makes only the
evidence fields that are meaningless without a successful execution optional for non-executed
trials. All enumerated options keep: `SearchTrialLedger` as the SOLE census authority, the open
trial ordering, the ledger digest, and the gate's K semantics (failed trials counted in K).

**Option A — Trial execution status field (INVALID → FAILED → EXECUTED_SUCCESSFULLY).**
Add `trial_status` to `SearchTrialRecord`:

```text
class SearchTrialStatus(str, Enum):
    REGISTERED = "REGISTERED"                        # pre-registered, not yet queued
    EXECUTED_SUCCESSFULLY = "EXECUTED_SUCCESSFULLY"  # run, evidence emitted
    FAILED = "AWAITING"...                           # run crashed/failed; stays in census
    INVALID = "INVALID"                              # invalid design; stays in census
```

The three ratified states are `REGISTERED+EXECUTED_SUCCESSFULLY`, `REGISTERED+FAILED`,
`REGISTERED+INVALID` (status transitions REGISTERED → EXECUTED_SUCCESSFULLY|FAILED|INVALID; frozen
forward). Evidence fields (`in_sample_sharpe`, `p_value`, `p_value_input_hash`,
`in_sample_return_series_sha256`, `execution_manifest_id`) become `Optional` under FAILED/INVALID
and remain mandatory under EXECUTED_SUCCESSFULLY. Digest keeps the executed-trials only evidence but
hashes the status+identity of ALL census members so the frozen census remains sealed as a whole.

**Option B — Minimal schema: nullable evidence + closed status set.**
Identical to Option A but with a closed string set instead of an enum (lower ceremony, weaker type
safety). Not preferred: the repo's existing schema conventions use Pydantic enums.

**Option C — Separate attestation table (NOT RECOMMENDED): record failed trials in a sibling
table and leave `SearchTrialledger` unchanged.**
Rejected as it breaks the `K_ledger == K_DSR == K_Holm` single-authority contract and the gate's
order-lock — the census itself must hold every pre-registered trial.

**Non-options (forbidden by the ratified rule, listed to prevent accidental drift):**
fabricated `in_sample_sharpe=0`/`p_value=1.0`; removing failed trials; shrinking K; replacing a
failed trial under a new identity; silent retry as a different trial identity; adding a new
"failed-trial financial return" convention.

## 4. Decision asked of the human(s)

Please select **Option A**, **Option B**, or another schema decision, and confirm:
1. Trial status enum/string must be part of `SearchTrialRecord` (census single authority).
2. `created_at_utc`/execution evidence remains excluded/included in the digest exactly as
   specified in Option A.
3. Gate K accounting counts failed/invalid census members (K stays frozen at pre-registration size).

Until this decision lands, the D6 failed-trial representation is NOT implemented — no
`SearchTrialRecord`/`SearchTrialLedger` change, no invented semantics, no schema modification.
D5 is complete and independently verified (see `./phase14_d5_d6_ratification_record.md`).

## 5. Evidence cross-reference

- `src/acash/validation/schema.py:70-106` (SearchTrialRecord), `:253-338` (`create()`),
  `:343-468` (SearchTrialLedger, `seal()`, `compute_ledger_digest()`).
- `src/acash/validation/gate.py:343-412` (sealed-ledger requirement, matrix↔ledger order binding,
  K = `|trials|`), `:238-243` (OOS minimum).
- `src/acash/research/evidence_bridge.py` (D8-B: bridge constructs records, NEVER seals).
- `src/acash/research/reinception.py:150-173` (`ResearchInceptionProposal.planned_trial_count` —
  the D6 pre-registration K anchor that already exists).

### Verification Ledger
- Implementation Status: BLOCKED on the D6 trial-status representation pending the §4 schema
  decision (reporting, not implementing, per the ratified rule).
- Contract Enforcement: STRICT FAIL-CLOSED (no placeholder, no fabrication, no schema mutation).
- Mathematical Authority: CANONICAL SPEC (census = `SearchTrialLedger` single authority; K frozen).
- Local Test Suite: NOT CHANGED BY THIS ARTIFACT (D5 suite: 32 passed).
- Type Checker (MyPy): NOT CHANGED BY THIS ARTIFACT (369 files clean).
- Remote CI Status: PENDING / NOT AVAILABLE.
- Methodological Caveats: The minimum decision requests ONE schema decision; this document STOPs
  and does not implement Option A/B autonomously.