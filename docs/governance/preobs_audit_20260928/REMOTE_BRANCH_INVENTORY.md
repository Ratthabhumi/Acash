# ACASH Remote Branch Inventory & Deletion Candidate Audit

**Document:** `docs/governance/preobs_audit_20260928/REMOTE_BRANCH_INVENTORY.md`
**Audit Scope:** All Remote Tracking References on `origin` (Freshly Queried via `git ls-remote --heads origin`)
**Canonical Main SHA Pin:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2`
**Audit Date:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 5, 8

---

## 1. Executive Summary

This inventory audits all remote branch heads on `origin` (GitHub: `Ratthabhumi/Acash`) queried directly against the remote repository via `git ls-remote --heads origin` and cross-referenced with local tracking refs.

### Key Census Findings (19 Remote Branches):
1. **Canonical Default Branch (1 branch):** `main` is pinned at `d9608c0a...` and remains strictly frozen.
2. **Fully Merged / Contained Branches (11 branches):** 11 branches have `ahead = 0` relative to `main` (verified by `git merge-base --is-ancestor <tip> origin/main == 0`). These represent completed historical work from Phases 12–14 and are safe candidates for post-observation deletion.
3. **Active Preserved Governance & Research Branches (7 branches):** 7 branches have `ahead > 0` and represent essential, active, isolated governance, research, presentation, or observability work. In accordance with the Operator Charter, **all 7 branches are strictly preserved**.
4. **Safety Invariant:** In strict adherence to pre-observation safety boundaries, **zero remote branches were deleted during this audit**.

---

## 2. Remote Branch Status Matrix

Divergence metrics and ancestry are computed against canonical `origin/main` (`d9608c0a2353bd5ed41943e5fb893ef9648089d2`):

| Remote Branch Ref | Remote Tip SHA | Ahead | Behind | Ancestor of Main? | Classification | Action | Preservation Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`refs/heads/main`** | `d9608c0a23...` | 0 | 0 | **YES** (Self) | **Canonical Main Pin** | **FROZEN** | Production execution pin for Observation #0001. Must not move. |
| **`refs/heads/governance/operator-decision-charter-v1`** | `e787cda941...` | 1 | 0 | NO | **Active Governance Branch** | **PRESERVE** | Normative Operator Decision Charter V1. Awaiting post-Obs merge. |
| **`refs/heads/governance/operator-charter-audit-v1-20260928`** | `477a8dd214...` | 2 | 0 | NO | **Active Governance Branch** | **PRESERVE** | Operator Charter Audit tool and 31 adversarial tests. Hardened. |
| **`refs/heads/governance/preobs-readonly-audit-pack-20260928`** | `c6ed64631b...` | 1 | 0 | NO | **Active Audit Pack Branch** | **PRESERVE** | Read-only pre-observation evidence and truth registers. |
| **`refs/heads/docs/readme-math-render-fix-preobs-20260928`** | `c9aaab7184...` | 1 | 0 | NO | **Isolated Presentation Fix**| **PRESERVE** | Fixes README GitHub MathJax rendering defects; held for post-Obs merge. |
| **`refs/heads/research/r0-intake-v1-20260927`** | `4fd4f3e68a...` | 3 | 0 | NO | **Research Intake Branch** | **PRESERVE** | 15 external video mechanism intake records. Parked for pre-empirical review. |
| **`refs/heads/governance/core001-staged-evidence-v1-preobs`** | `1375ccf4be...` | 2 | 0 | NO | **Active Evidence Branch** | **PRESERVE (HOLD)** | Staged evidence framework. On HOLD pending human S2 semantic adjudication. |
| **`refs/heads/feature/core001-observability-dashboard-v1`** | `3269c43893...` | 4 | 0 | NO | **Active Observability Branch**| **PRESERVE (HOLD)** | CORE-001 read-only dashboard. On HOLD pending S2 semantic decision. |
| **`refs/heads/docs/h01-shadow-session-handoff-20260914`** | `9a58ced501...` | 0 | 128 | **YES** | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Historical handoff from Phase 13. |
| **`refs/heads/docs/post-g7-state-sync`** | `4cd31044ea...` | 0 | 140 | **YES** | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Post-G7 synchronization record. |
| **`refs/heads/feat/dashboard-warm-neutral-standard`** | `ec86a8596a...` | 0 | 129 | **YES** | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Dashboard UI palette standardization. |
| **`refs/heads/feat/tournament-v2-risk-remediation-10slot`** | `243412d365...` | 0 | 106 | **YES** | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Tournament risk remediation implementation. |
| **`refs/heads/feature/phase14-readiness-def`** | `441ab6873b...` | 0 | 142 | **YES** | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Phase 14 prospective definitions. |
| **`refs/heads/feature/shadow-alpha-tournament`** | `3b2cdc2a04...` | 0 | 133 | **YES** | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Initial alpha tournament runner. |
| **`refs/heads/fix/binance-finalized-candle-contract`** | `638388e38f...` | 0 | 138 | **YES** | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Binance websocket finalized candle contract. |
| **`refs/heads/fix/dashboard-deferred-dns`** | `e659e75014...` | 0 | 132 | **YES** | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Dashboard DNS deferred resolution patch. |
| **`refs/heads/fix/dashboard-shadow-null-metrics`** | `78bb2e42c8...` | 0 | 130 | **YES** | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Fix for null metric display in shadow mode. |
| **`refs/heads/fix/tournament-max-data-age-ms`** | `bb6d49c41f...` | 0 | 131 | **YES** | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Configuration of maximum bar latency. |
| **`refs/heads/review/research-foundation-pre-empirical`** | `8650b91196...` | 0 | 145 | **YES** | **Fully Merged / Contained** | Deletion Candidate | All commits contained in main. Pre-empirical math foundation review. |

---

## 3. Preserved Active Branches Detail

### 3.1 Operator Decision Charter
- **Ref:** `refs/heads/governance/operator-decision-charter-v1`
- **Current Remote Tip:** `e787cda941a1f6fc008ba06282dfee7321c60f3f`
- **Scope:** Normative document `docs/governance/OPERATOR_DECISION_CHARTER_V1.md`.
- **Status:** Unmerged, ratified as the supreme operational operating standard. To be merged via PR post-Observation #0001.

### 3.2 Operator Charter Audit
- **Ref:** `refs/heads/governance/operator-charter-audit-v1-20260928`
- **Current Remote Tip:** `477a8dd21457268b47a70b2141b3857a7c3c9dd2`
- **Scope:** Audit CLI `tools/audit/operator_charter_audit.py`, 31 adversarial unit tests, and implementation records.
- **Status:** Complete, hardened against missing additions. To be merged post-Observation #0001.

### 3.3 README Presentation Patch
- **Ref:** `refs/heads/docs/readme-math-render-fix-preobs-20260928`
- **Current Remote Tip:** `c9aaab71843ba9343b3901804276855b60d4acc5`
- **Scope:** Fixes GitHub Markdown/MathJax alternate inline delimiter syntax (`$ `...` $`) on `README.md`.
- **Status:** Isolated on separate branch to avoid mutating canonical `main` before Observation #0001.

### 3.4 Research Intake R0
- **Ref:** `refs/heads/research/r0-intake-v1-20260927`
- **Current Remote Tip:** `4fd4f3e68a1bbf1e3d27caf060756ffcbb77c7d5`
- **Scope:** 41 new files documenting 15 external video trading mechanisms.
- **Status:** Parked on isolated branch to avoid contaminating prospective execution or backtest registers.

### 3.5 CORE-001 Staged Evidence & Observability Dashboard
- **Refs:** `refs/heads/governance/core001-staged-evidence-v1-preobs` (`1375ccf4...`) and `refs/heads/feature/core001-observability-dashboard-v1` (`3269c438...`)
- **Status:** Held on isolated branches pending the human governance decision regarding Stage S2 window semantics (60 observed vs 60 contiguous calendar sessions).

---

## 4. Deletion Candidate Verification Protocol

Every one of the 11 candidate branches is mathematically verified to be an ancestor of `main`:
```bash
# Proves every deletion candidate is reachable from origin/main
for ref in \
  9a58ced5011e15c7bcf3975f0e83acf339fa53ce \
  4cd31044ea99157e9b681c555ec0ac740eee1b75 \
  ec86a8596a8aa3d8a85c6e875d2e72adfc9c3ca2 \
  243412d36592fc57a8801dade8579b6e2ff713a5 \
  441ab6873b654b1be88cbd640f96bd165df804fd \
  3b2cdc2a04fa3f2094998730e890891eb318eb3c \
  638388e38f721b49cab2621532b04757d6d85586 \
  e659e75014895909e6310fabc006e4c3615493fb \
  78bb2e42c8221ab83e88d29dd0f0256528b59b72 \
  bb6d49c41fefef42c288ebdfce597572433423f9 \
  8650b91196f352900039483a5bbfb7fee8cacb4d; do
    git merge-base --is-ancestor $ref origin/main && echo "SAFE_TO_DELETE"
done
```

**Execution Window:** Safe for deletion during the post-Observation #0001 repository maintenance window under operator authorization.

---

## 5. Verification Ledger

- Inventory Complete: YES (19 of 19 remote heads accounted for)
- Fully Merged Branches: 11
- Preserved Active Branches: 7
- Canonical Main Ref: 1
- Deletions Performed: 0 (Strict read-only safety invariant enforced)
- Remote Verification Command: `git ls-remote --heads origin`
