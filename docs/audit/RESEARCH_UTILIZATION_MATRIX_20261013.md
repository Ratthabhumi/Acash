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

## Addendum 2026-10-14 — M1.8 / M1.8.1 / canary readiness (append-only; rows 1–9 above unmodified)

Stages: IMPLEMENTED / SYNTHETIC_TESTED / REAL_DATA_QUALIFIED / ECONOMICALLY_EVALUATED / AUTHORIZED.

| Asset / Workstream | Path | Implemented? | Synthetic-tested? | Real-data qualified? | Economically evaluated? | Authorized? | Next use / outstanding authority |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| M1.8 offline rehearsal | `src/acash/data/qualification/lane_a_rehearsal.py` | Yes (PR #29) | Yes (33) | No | No | Merge pending | Human merge review |
| M1.8.1 storage/evidence | `src/acash/data/qualification/lane_a_transport.py` | Yes (PR #30) | Yes (25) | No | No | Merge pending | Human merge review; crash durability NOT verified |
| Canary readiness (draft) | `src/acash/data/qualification/lane_a_canary.py` | Yes (PR #32, stacked draft) | Yes (16, fake transports) | No | No | No (preparation only) | Approval verifier + Lane A issuance |
| ETF admission handoff | `docs/research/ETF_DATA_ADMISSION_HANDOFF_20261014.md` | Yes (PR #31) | N/A (docs) | No | No | No | Operator decision packet |
| Lane B corporate actions | Lane B spec/contracts | Spec only | Partial | No (issuer evidence absent) | No | No | Sponsor-verified dividends/splits |
| HYP_010 | phase14 records | Terminally falsified (preserved) | — | No | No | No | No reuse as Alpha |
| Allocators (Cash/EW/InverseVol) | portfolio modules | Yes | Synthetic | No | No | No | Parked until qualified data |
| DSR / PBO / CPCV | validation stack | Yes (tools) | Synthetic | No candidates | No | No | No new strategies pre-data |
| VIX / VIX1D | research note on main | Note only | No | No | No | No | Empirical validation on qualified data |
| IBKR modeled friction | fee scenarios | Modeled (NOT account-verified) | Synthetic | No | Partial (scenarios) | No | Real fee/FX/tax evidence |
| FRED / BOT | source research | Research only | No | No | No | No | PIT-safe macro inputs when scoped |

**Addendum summary:** Offline software preparation is complete through the stacked canary draft; every downstream gate (merge approvals, Lane A issuance, provider entitlement, historical qualification, portfolio economics) remains unauthorised. Terminal falsifications (HYP_003, HYP_010) and frozen lineages (RI-01) are preserved unchanged.
