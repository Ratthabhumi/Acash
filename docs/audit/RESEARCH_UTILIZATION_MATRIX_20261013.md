# ACASH Research Utilization Matrix (2026-10-13)

**Status:** INVENTORY SNAPSHOT — descriptive, not an authorization record.
**Companion:** `docs/audit/RESEARCH_UTILIZATION_CHECKPOINT_20261012.md` (prior checkpoint).

| # | Asset / Workstream | State | Utilized For M1.7? | Notes |
| :-- | :--- | :--- | :--- | :--- |
| 1 | PPDS (paired permutation deflated Sharpe) engine | Implemented + tested (PR #25) | Offline, indirectly | Benchmark correctness landed; no live consumption |
| 2 | Benchmark correctness suite (G7 S11 aligned) | MERGED to main (`3b4aba9`) | Yes — regression baseline | 52/52 targeted tests on PR HEAD |
| 3 | TRI panel / allocator evaluation | Held | No | Blocked behind data admission gates |
| 4 | Evaluation / DSR-PBO stack | Implemented | No active candidates to evaluate | Empty pipeline; engine idle by design |
| 5 | IBKR execution path | Implemented (Phase 7/12 stack) | No | `NO_REAL_ORDERS=true`; canonical capital $0.00 |
| 6 | FRED macro ingestion | Available | Not in M1.7 scope | Candidate future Lane input; not requested |
| 7 | RI-01 auction-measurement | Canary 2 lineage UNRESOLVED | No (frozen) | See `docs/audit/RI01_CHRONOLOGY_DISCREPANCY_REPORT_20261013.md` |
| 8 | Active strategy slate | EMPTY | — | No strategy admitted; HYP_003 never created |
| 9 | Lane A data-acquisition packet | DRAFTED, UNISSUED | Offline only (authority module + dry run) | `docs/research/LANE_A_UNISSUED_AUTHORITY_PACKET_20261013.md`; network execution NOT authorized |

**Summary:** All quantitative engines are implemented and idle; the binding constraint is data authority (Lane A issuance), not code. Nothing in this matrix grants acquisition, paper, or live authority.
