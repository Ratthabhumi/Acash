# ACASH Branch Integration Matrix

**Cutoff Timestamp**: 2026-09-30T07:00:00Z  
**Baseline Anchor**: Canonical `origin/main` at `becec27f5eacf283dcb191cf72d0858682d8e055`  
**Remote Branch Inventory Count**: Exactly 21 branches on GitHub (all surveyed below)  
**Operational Status**: Attempt #2 execution frozen; research, dashboard, and integration lanes on HOLD.

---

## 1. Complete Remote Branch Survey (21 Branches)

| # | Branch Name | Remote Tip SHA | Divergence vs `main` (Behind / Ahead) | Classification | Scope / Governance Rationale |
| :---: | :--- | :--- | :---: | :--- | :--- |
| 1 | **`main`** | `becec27f5eacf283dcb191cf72d0858682d8e055` | 0 / 0 | **CANONICAL** | Sovereign production authority. Contains merged Stage C recovery (`08530b1`) + sealed Stage C-B manifest (`becec27`). |
| 2 | **`fix/hyp011-prospective-sip-window-recovery-20260929`** | `6787db0dbd9732f5a5812ef1575f484104a3b9dc` | 2 / 0 | **MERGED** | Dedicated recovery implementation branch. Canonically integrated into main via merge commit `08530b1`. Retained as immutable lineage evidence. |
| 3 | **`research/ppds-r0-capital-broker-architecture-20260928`** | `1b5aed1bafe70ecd41ec57a6da0b8af92be65801` | 9 / 6 | **HOLD** | PPDS Phase 15 R0 architectural intake. Merging forbidden during Stage C prospective shadow run to preserve frozen execution stack. |
| 4 | **`feature/core001-observability-dashboard-v1`** | `3269c4389305af4f380bd72db786bc400c74c331` | 9 / 4 | **HOLD** | Observability dashboard implementation. Non-critical to operational execution; held to avoid scope expansion and dependency churn. |
| 5 | **`research/r0-intake-v1-20260927`** | `4fd4f3e68a1bbf1e3d27caf060756ffcbb77c7d5` | 9 / 3 | **HOLD** | Research R0 initial intake notes and exploratory qualification. |
| 6 | **`governance/core001-staged-evidence-v1-preobs`** | `1375ccf4be87a3c0390fc94ddb82b1ac942a419e` | 9 / 2 | **HISTORICAL** | Staged governance evidence pack prior to Attempt #1. |
| 7 | **`governance/operator-charter-audit-v1-20260928`** | `477a8dd21457268b47a70b2141b3857a7c3c9dd2` | 9 / 2 | **HOLD** | Operator charter audit report. Held pending post-run reconciliation. |
| 8 | **`governance/operator-decision-charter-v1`** | `e787cda941a1f6fc008ba06282dfee7321c60f3f` | 9 / 1 | **HOLD** | Human operator decision charter draft. Held pending empirical completion of Stage C Observation #1 Attempt #2. |
| 9 | **`governance/preobs-readonly-audit-pack-20260928`** | `a7654383b5a0c2d5b6384ca4abb6fa074d7cda8e` | 9 / 2 | **HISTORICAL** | Read-only pre-observation audit snapshot before Attempt #1 dispatch. |
| 10 | **`docs/readme-math-render-fix-preobs-20260928`** | `c9aaab71843ba9343b3901804276855b60d4acc5` | 9 / 1 | **HISTORICAL** | Documentation math rendering fix. |
| 11 | **`feat/tournament-v2-risk-remediation-10slot`** | `243412d36592fc57a8801dade8579b6e2ff713a5` | 115 / 0 | **PAUSED** | Tournament risk slot expansion. Frozen outside active Phase 14 prospective scope. |
| 12 | **`docs/h01-shadow-session-handoff-20260914`** | `9a58ced5011e15c7bcf3975f0e83acf339fa53ce` | 137 / 0 | **HISTORICAL** | H01 shadow session handoff notes from 2026-09-14. |
| 13 | **`feat/dashboard-warm-neutral-standard`** | `ec86a8596a8aa3d8a85c6e875d2e72adfc9c3ca2` | 138 / 0 | **PAUSED** | Dashboard warm-neutral UI theme standard. Non-operational. |
| 14 | **`fix/dashboard-shadow-null-metrics`** | `78bb2e42c8221ab83e88d29dd0f0256528b59b72` | 139 / 0 | **PAUSED** | Dashboard null handling for shadow metrics. |
| 15 | **`fix/tournament-max-data-age-ms`** | `bb6d49c41fefef42c288ebdfce597572433423f9` | 140 / 0 | **PAUSED** | Tournament harness maximum data age timeout adjustment. |
| 16 | **`fix/dashboard-deferred-dns`** | `e659e75014895909e6310fabc006e4c3615493fb` | 141 / 0 | **PAUSED** | Dashboard DNS resolution deferral patch. |
| 17 | **`feature/shadow-alpha-tournament`** | `3b2cdc2a04fa3f2094998730e890891eb318eb3c` | 142 / 0 | **PAUSED** | Shadow alpha tournament runtime substrate candidate. |
| 18 | **`fix/binance-finalized-candle-contract`** | `638388e38f721b49cab2621532b04757d6d85586` | 147 / 0 | **HOLD** | Crypto data contract fix. Not applicable to equity HYP_011 prospective run. |
| 19 | **`docs/post-g7-state-sync`** | `4cd31044ea99157e9b681c555ec0ac740eee1b75` | 149 / 0 | **HISTORICAL** | G7 soak sync documentation and operational notes. |
| 20 | **`feature/phase14-readiness-def`** | `441ab6873b654b1be88cbd640f96bd165df804fd` | 151 / 0 | **HISTORICAL** | Phase 14 initial readiness definition. Superseded by canonical Phase 14 integration. |
| 21 | **`review/research-foundation-pre-empirical`** | `8650b91196f352900039483a5bbfb7fee8cacb4d` | 154 / 0 | **HISTORICAL** | Pre-empirical research foundation review checkpoint. |

---

## 2. Audit Branch Status & Post-Push Inventory

### Pre-Push vs Post-Push Inventory Accounting
- **Pre-Push Remote Inventory Cutoff (`2026-09-30T07:00:00Z`)**: Exactly 21 remote branches on GitHub (surveyed above).
- **Post-Push Remote Inventory (`2026-09-30T07:03:37Z`)**: 22 remote branches on GitHub, reflecting the authorized publication of the isolated audit branch.

| Branch Name | Local Tip SHA | Remote Tracking | Divergence vs `main` | Status | Purpose |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **`audit/repo-closure-20260930`** | `04907ac5...` (initial audit push) | `origin/audit/repo-closure-20260930` (`04907ac5...`) | Ahead 1 / Behind 0 | **AUDIT BRANCH PUBLISHED** | Isolated audit documentation (`docs/audit/`), hermetic test isolation, and defect reproduction pack pushed for independent review. |

---

## 3. Governance Integration Policy

1. **Zero Merge Policy During Active Prospective Run**: No branch may be merged into `main` before Observation #1 Attempt #2 completes and its evidence ledger is formally reconciled.
2. **Preservation of Divergence Evidence**: Historical topic and governance branches are preserved as lineage points; they must not be force-pushed, rebased, or deleted.
3. **Re-basing Requirements Post-Observation #1**: Any branch considered for future integration must be rebased or cleanly merged onto canonical `main` with dedicated integration commits only after formal human authorization.
