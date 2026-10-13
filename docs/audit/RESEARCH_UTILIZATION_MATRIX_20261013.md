# ACASH Research Utilization Matrix (2026-10-13)

**Status:** INVENTORY SNAPSHOT — descriptive, not an authorization record.
**Companion:** `docs/audit/RESEARCH_UTILIZATION_CHECKPOINT_20261012.md` (prior checkpoint).

| # | Asset / Workstream | State | Utilized For M1.7? | Notes |
| :-- | :--- | :--- | :--- | :--- |
| 1 | PPDS (Portfolio Decision Support) read-only runtime (`src/acash/ppds/`) | Implemented + tested (merged to canonical `main` in PR #9) | Offline, indirectly | Synthetic read-only consumer; M1.6 benchmark correctness landed separately (PR #25 = `3b4aba9`); no live consumption |
| 2 | Benchmark correctness suite (G7 S11 aligned) | MERGED to main (`3b4aba9`) | Yes — regression baseline | 52/52 targeted tests on PR HEAD |
| 3 | TRI panel / allocator evaluation | Held | No | Blocked behind data admission gates |
| 4 | Evaluation / DSR-PBO stack | Implemented | No active candidates to evaluate | Empty pipeline; engine idle by design |
| 5 | Execution stack (Alpaca adapter + MT5 adapter + mock/paper drivers) | Implemented (paper/real drivers present) | No | `NO_REAL_ORDERS=true`; canonical capital $0.00. IBKR is NOT an execution path in `src/` — it appears only as the `IBKR_INSPIRED_SYNTHETIC_FRICTION` fee model in `src/acash/data/contracts/etf_fx_benchmark.py`, which is explicitly NOT account-verified |
| 6 | FRED macro ingestion | Available | Not in M1.7 scope | Candidate future Lane input; not requested |
| 7 | RI-01 auction-measurement | Canary 2 lineage UNRESOLVED | No (frozen) | See `docs/audit/RI01_CHRONOLOGY_DISCREPANCY_REPORT_20261013.md` |
| 8 | Active strategy slate | EMPTY | — | No strategy admitted; HYP_003 exists and was closed as terminally falsified (`docs/phase14/hyp_003_terminal_falsification_dossier.md`, commit `9b6a45a`) |
| 9 | Lane A data-acquisition packet | DRAFTED, UNISSUED | Offline only (authority module + dry run) | `docs/research/LANE_A_UNISSUED_AUTHORITY_PACKET_20261013.md`; network execution NOT authorized |

**Summary:** Per-row states above are evidenced only by each row's Notes references; this snapshot makes no blanket claim of qualification, admission, or readiness beyond those rows. The binding constraint recorded here is data authority (Lane A issuance). Nothing in this matrix grants acquisition, paper, or live authority.
