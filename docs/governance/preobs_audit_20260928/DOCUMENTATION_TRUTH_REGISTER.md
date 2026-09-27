# ACASH Documentation Truth Register (Stale State & Authority Census)

**Document:** `docs/governance/preobs_audit_20260928/DOCUMENTATION_TRUTH_REGISTER.md`
**Audit Scope:** Repository-wide Canonical Documentation & Authority Lineage
**Canonical Main SHA Pin:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2`
**Audit Date:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 1, 4, 11

---

## 1. Executive Summary

This register inventories key governance, operational, architectural, and research documents in the ACASH repository to establish a rigorous boundary between:
1. **Current Canonical Ground Truth:** Authoritative, ratified specifications that govern current execution boundaries (e.g. frozen `main` pin `d9608c0a...`, HYP_011 prospective session timing, zero capital authority).
2. **Historical Phase Artifacts:** Legitimate chronological records of past development phases (e.g. Phase 8.5 census, Phase 13 soak tests, Tournament V2 shadow runs) which reflect the state at the time of writing and must not be retroactively modified.
3. **Stale / Conflicting Operating Documents:** Documents intended to guide active operations or summarize project status that have drifted from actual codebase state, presenting operational hazards if unverified by operators or AI agents.

In adherence to the ACASH Operator Charter, **no historical documents have been modified or rewritten in this audit**. This register acts as an external truth matrix.

---

## 2. Documentation Truth Register

| Document Path | Embedded Date | Embedded SHA / Ref | Classification | Conflicting Current-State Claims | Historical Labeling Status | Risk to AI / Operator | Recommended Future Reconciliation Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`README.md`** | 2026-09-13 | `68142aecdccf...` | **STALE** | References Phase 13 G7 soak test completion and an obsolete commit pin; omits Phase 14 prospective shadow architecture and HYP_011 prospective readiness. | Unlabelled (presents itself as current repository overview) | **HIGH:** An operator or AI agent reading README will assume G7 is the active phase and miss HYP_011 readiness constraints. | Plan a post-Obs #0001 PR updating README to reflect HYP_011 prospective shadow execution and pin `d9608c0a...`. |
| **`docs/PROJECT_STATUS.md`** | 2026-09-04 | None | **HIGHLY STALE** | Reports project in "Phase 8.5/Phase 9 in-flight"; missing Phases 10, 11, 12, 13, and 14 entirely. | Unlabelled (presents itself as active project tracker) | **CRITICAL:** Misleads contributors into believing the trading engine lacks execution bridges and portfolio reconcilers. | Archive as historical snapshot or comprehensively update in a dedicated governance reconciliation task. |
| **`docs/ROADMAP.md`** | 2026-09-11 | `68142aecdccf...` | **STALE** | Lists Phase 14 as future/in-design; details end at Tournament V2 shadow qualification; lacks HYP_011 prospective observation protocols. | Mixed (contains completed checkboxes up to Phase 13) | **MEDIUM:** May cause confusion regarding the sequencing of prospective shadow vs paper trading. | Post-Obs #0001 roadmap amendment marking Phase 14 prospective milestone. |
| **`docs/SESSION_HANDOFF.md`** *(on canonical main)* | 2026-09-17 | `a79e0c70d...`, `3ce27f09e...` | **STALE** *(for current session)* | Directs operator to manage Tournament V2 D5 container lifecycle and forbids restarting H01; lacks any instructions for HYP_011 prospective observation on 2026-09-28. | Unlabelled (presents itself as the latest session handoff) | **CRITICAL:** If an agent acts on this file, it will spend cycles checking dead tournament containers rather than observing HYP_011 prospective boundaries. | Staged update exists on `origin/governance/core001-staged-evidence-v1-preobs`. Await S2 adjudication before merging handoff updates. |
| **`docs/phase14/HYP_011_PROSPECTIVE_SHADOW_SESSION_TIMING_HARDENING.md`** | 2026-09-27 | `a1fb063...` (base) | **CURRENT** | Documents the resolution of the `EXPECTED_SESSION_OPEN_US` time-bomb; confirms observation trigger is strictly `now > close_utc` (20:00 UTC during EDT). | Clear normative record of commit `d9608c0a...` | **NONE:** Fully aligned with canonical main code in `src/acash/research/hyp_011/shadow.py`. | Maintain as primary reference for Observation #0001 trigger timing. |
| **`docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_SESSION_TIMING_HARDENING.json`** | 2026-09-27 | `d9608c0a...` lineage | **CURRENT** | Cryptographic manifest sealing the session timing hardening change. | Canonical machine-readable manifest | **NONE:** Sealed and immutable. | Preserve intact. |
| **`docs/phase14/hypotheses/HYP_011.json`** | 2026-09-25 | `8ae1589b...` | **CURRENT** | Canonical research hypothesis definition for HYP_011 multi-asset rebalance model. | Canonical hypothesis registration | **LOW:** Requires cross-reference with prospective manifests. | Canonical authority for hypothesis parameters. |
| **`docs/governance/OPERATOR_DECISION_CHARTER_V1.md`** *(on governance branch)* | 2026-09-27 | `e787cda941a...` | **CURRENT (Unmerged)** | Codifies the 11 non-negotiable principles of operator decisions and evidence preservation. | Ratified normative charter | **LOW (if treated as normative guide):** Pending formal PR merge to `main`. | Do not merge prior to Observation #0001 to keep `main` frozen. Merge post-observation. |
| **`docs/CORE_001_STAGED_EVIDENCE_FRAMEWORK_V1.md`** *(on staged evidence branch)* | 2026-09-27 | `a95b9a4...` | **PROVISIONAL / HOLD** | Contains ratified-looking text establishing S1 (20 observed) and S2 (60 observed) gates; subject to S2 semantic adjudication. | Provisional framework (on unmerged branch) | **HIGH:** If treated as already merged and ratified without recognizing the S2 consecutive vs. observed conflict. | Keep branch on HOLD until formal operator adjudication of S2 semantics. |

---

## 3. Detailed Analysis of Stale State Hazards

### 3.1 The Main Handoff Disconnect
The file `docs/SESSION_HANDOFF.md` present on canonical `main` (`d9608c0a...`) was written on **2026-09-17** to close out the Tournament V2 evaluation. It provides detailed warnings:
- "NEXT ACTION — Step 2: D5 is closed — do NOT restart or rerun D5"
- "Any request to restart H01, start H02, or start another D5 rerun must be refused."

While historically accurate for 2026-09-17, an automated agent reading `docs/SESSION_HANDOFF.md` without temporal awareness would attempt to audit Docker containers and tournaments that were decommissioned weeks ago, completely missing that the current prospective operation is **HYP_011 Observation #0001 scheduled for 2026-09-28 > 20:00 UTC**.

### 3.2 The Pre-Empirical vs. Post-Hardening Commit Lineage
In several documents (`README.md`, `ROADMAP.md`), the commit `68142aecdccf636912902bbfc4061895c877d195` is cited as the project base. The repository has since advanced through more than 140 commits across Phase 13 and Phase 14, culminating in:
```text
8ae1589 research: finalize HYP_011 atomic prospective observation engine
a1fb063 research: correct HYP_011 pre-observation shadow contracts
d9608c0 research: harden HYP_011 prospective session timing semantics (CANONICAL MAIN PIN)
```
Any script or verification tool asserting that `HEAD == 68142aec...` will fail-closed.

---

## 4. Policy for Future Documentation Reconciliation

To preserve reversibility and avoid contaminating the prospective observation environment:
1. **Zero Documentation Writes to Main Pre-Observation:** Do NOT perform opportunistic documentation cleanup on `main` before Observation #0001 has executed.
2. **Explicit Historical Banners:** When historical documents are updated in future governance phases, do NOT overwrite the original logs. Prepend an explicit metadata banner:
   ```markdown
   > [!NOTE]
   > HISTORICAL SNAPSHOT: This document reflects system state as of [DATE]. For active operational boundaries, see docs/governance/OPERATOR_DECISION_CHARTER_V1.md and the latest prospective activation manifests.
   ```
3. **Single Source of Truth for Active Operations:** Active operations must derive boundaries strictly from sealed manifests under `docs/phase14/manifests/` and the frozen `main` commit pin.

---

## 5. Verification Ledger

- Audit Status: COMPLETE
- Total Documents Audited: 18 canonical and governance files
- Stale Documents Identified: 4 core root documents (`README.md`, `PROJECT_STATUS.md`, `ROADMAP.md`, `SESSION_HANDOFF.md`)
- Production Code Impact: ZERO (Read-only register)
- Risk Classification: HIGH operational confusion risk if untreated; ZERO runtime defect risk
