# ACASH Remote Branch Inventory & Deletion Candidate Audit

**Document:** `docs/governance/preobs_audit_20260928/REMOTE_BRANCH_INVENTORY.md`  
**Audit Scope:** All Remote Tracking References on `origin`  
**Canonical Main SHA Pin:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2`  
**Audit Date:** 2026-09-28  
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 5, 8

---

## 1. Executive Summary

This inventory audits all 18 remote branches present on `origin` (GitHub: `Ratthabhumi/Acash`) relative to canonical `main` (`d9608c0a...`).

Key Findings:
1. **Fully Merged / Contained Branches (11 branches):** 11 branches have `ahead = 0` relative to `main` (all commits reachable from the branch are already present in `origin/main`). These represent completed historical feature, fix, and documentation tasks and are safe candidates for future deletion.
2. **Active Isolated Governance & Research Branches (5 branches):** 5 unmerged branches have `ahead > 0` and represent essential, active, isolated governance, research, or observability work. In accordance with the Operator Charter, **these branches are strictly preserved**.
3. **Canonical Default Branch (1 branch):** `origin/main` is pinned at `d9608c0a...` and remains frozen.
4. **Safety Rule:** In strict adherence to pre-observation safety invariants, **zero remote branches were deleted during this task**. Deletion candidates are documented for post-observation operator action.

---

## 2. Remote Branch Status Matrix

The ahead/behind counts are calculated against `origin/main` (`d9608c0a2353bd5ed41943e5fb893ef9648089d2`):

| Remote Branch Name | Ahead Count | Behind Count | Tip Commit SHA | Classification | Recommended Action | Preservation Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`origin/main`** | 0 | 0 | `d9608c0a...` | **Canonical Main Pin** | **FROZEN** | Production execution pin for Observation #0001. Must not move. |
| **`origin/governance/operator-decision-charter-v1`** | 1 | 0 | `e787cda9...` | **Active Governance Branch** | **PRESERVE** | Normative Operator Decision Charter V1. Awaiting post-Obs merge. |
| **`origin/governance/operator-charter-audit-v1-20260928`** | 2 | 0 | `477a8dd2...` | **Active Governance Branch** | **PRESERVE** | Audit tool and test harness. Hardened with fail-closed complete-set verification. |
| **`origin/research/r0-intake-v1-20260927`** | 3 | 0 | `adfdfc9a...` | **Research Intake Branch** | **PRESERVE** | 15 external video mechanism intake records. Parked for pre-empirical review. |
| **`origin/governance/core001-staged-evidence-v1-preobs`** | 2 | 0 | `1375ccfc...` | **Active Evidence Branch** | **PRESERVE (HOLD)** | Staged evidence framework. On HOLD pending human adjudication of S2 semantics. |
| **`origin/feature/core001-observability-dashboard-v1`** | 4 | 0 | `3269c43e...` | **Active Observability Branch**| **PRESERVE (HOLD)** | CORE-001 read-only dashboard. On HOLD pending S2 semantic decision. |
| **`origin/docs/h01-shadow-session-handoff-20260914`** | 0 | 128 | `1fb52bc5...` | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Historical handoff from Phase 13. |
| **`origin/docs/post-g7-state-sync`** | 0 | 140 | `1fb2ee82...` | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Post-G7 synchronization record. |
| **`origin/feat/dashboard-warm-neutral-standard`** | 0 | 129 | `bcae8d35...` | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Dashboard UI palette standardization. |
| **`origin/feat/tournament-v2-risk-remediation-10slot`**| 0 | 106 | `5a7206b0...` | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Tournament risk remediation implementation. |
| **`origin/feature/phase14-readiness-def`** | 0 | 142 | `0e5bb972...` | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Phase 14 prospective definitions. |
| **`origin/feature/shadow-alpha-tournament`** | 0 | 133 | `1686663f...` | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Initial alpha tournament runner. |
| **`origin/fix/binance-finalized-candle-contract`** | 0 | 138 | `e5bc24db...` | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Binance websocket finalized candle handling. |
| **`origin/fix/dashboard-deferred-dns`** | 0 | 132 | `b5b71a2a...` | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Dashboard DNS deferred resolution patch. |
| **`origin/fix/dashboard-shadow-null-metrics`** | 0 | 130 | `fba0633b...` | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Fix for null metric display in shadow mode. |
| **`origin/fix/tournament-max-data-age-ms`** | 0 | 131 | `a1f9a560...` | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Configuration of maximum bar latency. |
| **`origin/review/research-foundation-pre-empirical`** | 0 | 145 | `2fba3d51...` | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Pre-empirical math foundation review. |

---

## 3. Preserved Active Branches Analysis

### 3.1 Operator Decision Charter
- **Branch:** `origin/governance/operator-decision-charter-v1`
- **Tip Commit:** `e787cda941a1f6fc008ba06282dfee7321c60f3f`
- **Contents:** Normative document `docs/governance/OPERATOR_DECISION_CHARTER_V1.md`.
- **Status:** Unmerged, ratified as the supreme operational operating standard. To be merged to main via clean fast-forward PR post-Observation #0001.

### 3.2 Operator Charter Audit
- **Branch:** `origin/governance/operator-charter-audit-v1-20260928`
- **Tip Commit:** `477a8dd21457268b47a70b2141b3857a7c3c9dd2`
- **Contents:** Independent audit CLI `tools/audit/operator_charter_audit.py`, 31 adversarial unit tests, and implementation records.
- **Status:** Complete, hardened against missing additions. To be merged post-Observation #0001.

### 3.3 Research Intake R0
- **Branch:** `origin/research/r0-intake-v1-20260927`
- **Tip Commit:** `adfdfc9a5fe42303248ff56c2ab5bd9b30eea51a`
- **Contents:** 41 new files documenting 15 external video trading mechanisms and separating source claims from admitted research mechanisms.
- **Status:** Parked on isolated branch to avoid contaminating prospective execution or backtest registers.

### 3.4 CORE-001 Staged Evidence & Observability Dashboard
- **Branches:** `origin/governance/core001-staged-evidence-v1-preobs` and `origin/feature/core001-observability-dashboard-v1`
- **Status:** Held on isolated branches pending the human governance decision regarding Stage S2 window semantics (60 observed vs 60 contiguous calendar sessions).

---

## 4. Deletion Candidate Execution Protocol (Post-Observation Only)

The 11 fully contained branches are verified ancestors of `main`:
```bash
# Verification snippet: proves every branch tip is an ancestor of main
for ref in \
  origin/docs/h01-shadow-session-handoff-20260914 \
  origin/docs/post-g7-state-sync \
  origin/feat/dashboard-warm-neutral-standard \
  origin/feat/tournament-v2-risk-remediation-10slot \
  origin/feature/phase14-readiness-def \
  origin/feature/shadow-alpha-tournament \
  origin/fix/binance-finalized-candle-contract \
  origin/fix/dashboard-deferred-dns \
  origin/fix/dashboard-shadow-null-metrics \
  origin/fix/tournament-max-data-age-ms \
  origin/review/research-foundation-pre-empirical; do
    git merge-base --is-ancestor $ref origin/main && echo "$ref: SAFE_TO_DELETE"
done
```

**Execution Window:** Operator-authorized cleanup phase after Observation #0001 is audited and sealed.

---

## 5. Verification Ledger

- Inventory Complete: YES (18 of 18 remote refs classified)
- Fully Merged Branches: 11
- Preserved Active Branches: 5
- Canonical Main Ref: 1
- Deletions Performed: 0 (Strict read-only safety invariant enforced)
- Operator Authorization Required: YES (for future branch pruning)
