# ACASH — Session Handoff

> **Document:** `docs/SESSION_HANDOFF.md`
> **Status:** RESEARCH STANDING BY — CAND-FREE-MACRO-001 CONDITIONALLY READY — HUMAN DECISION BINDING PENDING
> **Date:** 2026-09-10
> **Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`)
> **Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Implementation Correctness ≠ Mathematical Validity, Single Canonical Authority)

---

## 1. REPOSITORY CHECKPOINT (AUTHORITATIVE)

- **Branch:** `main`
- **HEAD == origin/main == `7faf012`**
- Sync command used at checkpoint: `git clone` (fresh) or `git pull` (existing repo), then open this file.

| Commit | Contains |
|---|---|
| `7faf012` | `docs/phase14/cand_free_macro_001_human_binding_worksheet.md` (Human Binding Worksheet — Decision Compression) |
| `954af2c` | `docs/phase14/cand_free_macro_001_human_specification_decision_surface.md` (Decision Surface, decisions D1–D22) |
| `3e3d918` | `docs/phase14/cand_free_macro_001_validation_readiness.md` (Validation Readiness package) |

**Known pre-existing untracked file (local only):** `docs/phase14/bootstrap_mechanism_governance_review.md` is **LEFT UNCOMMITTED** — not part of the intended current work. Do not blindly stage it; commit only if a future governance review decides it belongs in the canonical chain.

---

## 2. CURRENT GOVERNANCE STATE

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           ACASH GOVERNANCE LEDGER                         │
├───────────────────────────────────┬───────────────────────────────────────┤
│ HYP_001 (M5 Intraday)            │ TERMINALLY_FALSIFIED / CLOSED / IMMUT  │
│ HYP_002 (H4 Session)             │ TERMINALLY_FALSIFIED / CLOSED          │
│ HYP_003                          │ NOT CREATED                            │
│ CAND-FREE-MACRO-001              │ CONDITIONALLY READY                    │
│ PRE-REGISTRATION                 │ NOT FULLY FROZEN                       │
│ EMPIRICAL VALIDATION             │ NOT AUTHORIZED                         │
│ BACKTEST                         │ NOT AUTHORIZED                         │
│ HYP_002 Validation (3751..4996)  │ QUARANTINED / PRISTINE (NOT REUSABLE)  │
│ HYP_002 Blind OOS (5009..6230)   │ QUARANTINED / PRISTINE (NOT REUSABLE)  │
│ 2026 M5 Holdout (6060..9999)     │ QUARANTINED / PRISTINE                 │
│ Live Capital Authority           │ $0.00 (Hard-Locked)                    │
│ Live Trading Authority           │ LOCKED                                 │
│ Broker Connection                │ DISCONNECTED / NONE                    │
│ System                           │ RESEARCH STANDING BY                   │
└───────────────────────────────────┴───────────────────────────────────────┘
```

---

## 3. NEXT STEP — HUMAN SPECIFICATION BINDING

Start from the **Human Binding Worksheet**: `docs/phase14/cand_free_macro_001_human_binding_worksheet.md`.

Decision compression achieved: 22 dimensions (D1–D22) → **5 batch-confirmable** (Group A) + **12 Human choice** (Group B, folded into 5 rounds) + **3 derivable** (Group C, incl. K) + governance items.

Decision sequence (exact order, do not skip):

```
ROUND 0   Batch-confirm proposed defaults (A1–A5)
ROUND 1   Event Window + Return          (D3, D4)
ROUND 2   Baseline + Overlap             (D7, D8)
ROUND 3   Grid → K → Statistical Protocol (D10, D11, D12)
          [K = |Cartesian product(Grid)|, derived, never hand-picked]
ROUND 4   IS/OOS + Blind + Cost          (D14, D15, D16, D9)
ROUND 5   Kill + PASS/FAIL/INVALID       (D19, D20)
     ↓
Draft Freeze Candidate
     ↓
Anti-HARKing review ("any parameter chosen because we saw the outcome?")
     ↓
Pre-registration Freeze
     ↓
Data Archive / Manifest
     ↓
Explicit Human Authorization
     ↓
ONLY THEN   empirical validation / backtest
```

Do NOT state that any of these future steps are already completed.

---

## 4. DO NOT RE-RUN COMPLETED STAGES

The following stages are **COMPLETE** and must **NOT** be repeated:

- SSRN literature discovery
- free-data feasibility review
- bootstrap mechanism governance review
- MACRO-001 readiness review (Validation Readiness package, `3e3d918`)
- Human Specification Decision Surface (`954af2c`)
- Decision Compression (Human Binding Worksheet, `7faf012`)

Next work begins at: **Human Decision Binding (ROUND 0)** of the worksheet.

---

## 5. SESSION BOUNDARY (HARD, VERBATIM)

- `CAND-FREE-MACRO-001` remains **CONDITIONALLY READY**.
- `PRE-REGISTRATION` remains **NOT FULLY FROZEN**.
- `EMPIRICAL VALIDATION` remains **NOT AUTHORIZED**.
- `BACKTEST` remains **NOT AUTHORIZED**.
- `HYP_003` = **NOT AUTHORIZED** · `R1` = **NOT AUTHORIZED** · `ResearchReInceptionGate` = **NOT INVOKED**.
- `TRADING` = **LOCKED** · `CAPITAL` = **$0.00** · `BROKER` = **DISCONNECTED / NONE**.

**DO NOT BACKTEST YET.**

No empirical work is authorized until the full binding sequence of Section 3 completes with explicit Human authorization: no event study, returns, IC, Sharpe, p-values, backtest, parameter optimization, hypothesis creation, gate invocation, broker connection, or order generation.

---

## 6. WHAT MUST NOT BE DONE

- Do NOT create `HYP_003`.
- Do NOT reuse quarantined HYP_002 Validation/OOS or 2026 M5 Holdout partitions.
- Do NOT run Validation / OOS / backtests on quarantined data.
- Do NOT acquire new market data without authorization.
- Do NOT connect to a broker; do NOT allocate capital > `$0.00`.
- Do NOT alter historical HYP_001 / HYP_002 results or their digests (Sections 7, 8).
- Do NOT silently resolve a MACRO-001 decision gap — write `HUMAN DECISION REQUIRED` / `PROPOSED DEFAULT — HUMAN CONFIRMATION REQUIRED`.
- Do NOT author any empirical/statistical claim for CAND-FREE-MACRO-001 before the pre-registration is frozen.
- Do NOT invent K, floors (`max(1e-12, val)`), neutral outcomes, or magic constants. Raise `DataContractError` instead.

---

## 7. HYPOTHESIS LINEAGE (HISTORICAL — IMMUTABLE)

| Hypothesis | Market / TF | Lifecycle | Final State |
|---|---|---|---|
| `HYP_TSMOM_EURUSD_001` | EURUSD M5 | R1→R2→R3 (0/9 qualified) → R4–R7 early-terminated | **TERMINALLY_FALSIFIED / CLOSED / IMMUTABLE** |
| `HYP_TSMOM_EURUSD_HTF_002` | EURUSD H4 | R1→R2→R3 (0/12 qualified) → R4 early-terminated | **TERMINALLY_FALSIFIED / CLOSED** |
| `HYP_003` | — | — | **NOT CREATED** |

HYP_002 closure: in-sample census exactly `K=12`; 0/12 qualified. Sharpe range −2.234 … −3.677 (undeflated annualized IS, √1512, 1.2 bps roundtrip). Status `VERIFIED` (closure audited 2026-09-07).

---

## 8. CRYPTOGRAPHIC DIGESTS (HYP_002) — IMMUTABLE, MUST NOT BE ALTERED

| Artifact | Digest |
|---|---|
| Sealed hypothesis spec (`HYP_TSMOM_EURUSD_HTF_002.json`) | `47c077a65f3057ae5ec83c8e7cf9179ababea9e5b18bc999bdc480a44f544afe` |
| R3 Search Trial Ledger (`ledger_digest`) | `d6d627334a1560193c495947e4f9ab3a62e983ac46cba1ef4cf51a1707dd6565` |
| R3 Manifest (`r3_manifest_HYP_TSMOM_EURUSD_HTF_002.json`) | `809ac530c69745924550723b19b79a7a82bd4182659f6eb2a5cfc4b019c24ccd` |

Lineage cross-check (VERIFIED): manifest `hypothesis_sha256` == sealed digest; manifest `ledger_digest` == ledger `ledger_digest` field.

---

## 9. DATA QUARANTINE STATE — HARD INVARIANT

| Protected Span | Bars | Status |
|---|---|---|
| HYP_002 H4 Validation | 3751..4996 | `QUARANTINED / PRISTINE` — NOT REUSABLE BY DEFAULT |
| HYP_002 H4 Blind OOS | 5009..6230 | `QUARANTINED / PRISTINE` — NOT REUSABLE BY DEFAULT |
| 2026 M5 Holdout (HYP_001) | 6060..9999 | `QUARANTINED / PRISTINE` |

Enforced in code: `src/acash/research/quarantine.py` (`PERMANENTLY_QUARANTINED_HOLDOUTS`) and `src/acash/research/reinception.py` (`TERMINAL_HYPOTHESIS_REGISTRY`, `PERMANENTLY_QUARANTINED_WINDOWS`). Status `VERIFIED`.

---

## 10. CAPITAL / TRADING AUTHORITY

| Authority | State |
|---|---|
| Live Capital Authority | `$0.00` (Hard-Locked) |
| Live Order Emission | `0` |
| Trading Authority | `LOCKED` |
| Broker Connection | `DISCONNECTED / NONE` |

Status `VERIFIED`. No authorization modified by the MACRO-001 documentation work.

---

## 11. PHASE 14 STATUS

- **Research-Intelligence runtime:** implemented (`feat(research-ai)` commits). AI output is an **`UNVALIDATED PROPOSAL`** with zero authority to register hypotheses, qualify alpha, certify backtests, authorize trading, access capital, bypass R1/R2/R3, bypass quarantine, or override human governance.
- **Free-data MACRO-001 lane:** governance documentation complete (readiness → decision surface → binding worksheet). **Empirical work pending frozen pre-registration + Human authorization.**

---

## 12. EXACT RESUME CHECKLIST FOR NEXT SESSION

```powershell
git clone https://github.com/Ratthabhumi/Acash.git   # OR: git pull
# expect HEAD == 7faf012 == origin/main
Get-Content docs/SESSION_HANDOFF.md                   # this file — checkpoint + boundaries
```

1. Read `docs/phase14/cand_free_macro_001_human_binding_worksheet.md`.
2. Begin **ROUND 0** — batch-confirm Group A defaults (A1–A5); if any rejected, mark `HUMAN DECISION REQUIRED`.
3. Proceed ROUND 1 → ROUND 5 per Section 3 sequence.
4. Produce Draft Freeze Candidate → anti-HARKing review → freeze → manifest → **explicit Human authorization** → only then empirical/backtest.

**System is RESEARCH STANDING BY. CAND-FREE-MACRO-001 is CONDITIONALLY READY. PRE-REGISTRATION is NOT FULLY FROZEN. EMPIRICAL VALIDATION and BACKTEST are NOT AUTHORIZED.**