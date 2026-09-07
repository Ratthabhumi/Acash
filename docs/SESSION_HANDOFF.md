# ACASH — Session Handoff

> **Document:** `docs/SESSION_HANDOFF.md`
> **Status:** HYP_002 CLOSED — RESEARCH STANDING BY — PHASE 14 CONTINUATION PENDING HUMAN AUTHORIZATION
> **Date:** 2026-09-07
> **Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`)
> **Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Implementation Correctness ≠ Mathematical Validity, Single Canonical Authority)

---

## 1. SESSION STATUS

**System is RESEARCH STANDING BY.**

This session completed the canonical closure of **HYP_TSMOM_EURUSD_HTF_002 (Ordinal HYP_002)** at the governance level, sealed it, and prepared a clean resume point for the next session. No Phase 14 implementation, no HYP_003, and no empirical/trading activity occurred.

**The single next recommended action is: Review / authorize Phase 14 implementation.**

---

## 2. CURRENT CANONICAL STATE

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           ACASH GOVERNANCE LEDGER                         │
├───────────────────────────────────┬───────────────────────────────────────┤
│ HYP_001 (M5 Intraday)            │ TERMINALLY_FALSIFIED / CLOSED / IMMUT  │
│ HYP_002 (H4 Session)             │ TERMINALLY_FALSIFIED / CLOSED          │
│ HYP_003                          │ NOT CREATED                            │
│ HYP_002 Validation (3751..4996)  │ QUARANTINED / PRISTINE (NOT REUSABLE)  │
│ HYP_002 Blind OOS (5009..6230)   │ QUARANTINED / PRISTINE (NOT REUSABLE)  │
│ 2026 M5 Holdout (6060..9999)     │ QUARANTINED / PRISTINE                 │
│ Live Capital Authority           │ $0.00 (Hard-Locked)                    │
│ Live Trading Authority           │ LOCKED                                 │
│ Broker Connection                │ DISCONNECTED / NONE                    │
│ Phase 14 (Research Intelligence) │ DESIGN READY / APPROVAL PENDING        │
│ Phase 14 Runtime (srch/research) │ NOT IMPLEMENTED                        │
│ System                           │ RESEARCH STANDING BY                   │
└───────────────────────────────────┴───────────────────────────────────────┘
```

---

## 3. HYPOTHESIS LINEAGE

| Hypothesis | Market / TF | Lifecycle | Final State |
|---|---|---|---|
| `HYP_TSMOM_EURUSD_001` | EURUSD M5 | R1→R2→R3 (0/9 qualified) → R4–R7 early-terminated | **TERMINALLY_FALSIFIED / CLOSED / IMMUTABLE** |
| `HYP_TSMOM_EURUSD_HTF_002` | EURUSD H4 | R1→R2→R3 (0/12 qualified) → R4 early-terminated | **TERMINALLY_FALSIFIED / CLOSED** |
| `HYP_003` | — | — | **NOT CREATED** |

---

## 4. HYP_001 FINAL STATE

- **Identity:** `HYP_TSMOM_EURUSD_001`
- **State:** `TERMINALLY_FALSIFIED / CLOSED / IMMUTABLE`
- **In-sample:** 0/9 trials qualified (M5 intraday momentum).
- **R4–R7:** early-terminated by the failure rule.
- **Sealed hypothesis digest:** `5afb92d7175721872d51ab82b2ebaaaa353c2d21bcbbd596e8bf1a3c52de0ef4`
- **R3 ledger digest:** `b1185c4f26d4934e930d526b66d7f3e8786bdbb6c24c263957f9288aa4072b43`
- **2026 M5 Holdout (6060..9999):** `QUARANTINED / PRISTINE`
- **Status:** `VERIFIED` (closure artifacts audited in prior session)

---

## 5. HYP_002 FINAL STATE

- **Identity:** `HYP_TSMOM_EURUSD_HTF_002` (Ordinal `HYP_002`)
- **State:** `TERMINALLY_FALSIFIED / CLOSED`
- **In-sample census:** exactly `K=12` pre-registered trials executed; **0/12 qualified**.
- **Per-gate result:** 0/12 passed Rank IC, 0/12 passed HAC t-stat, 12/12 passed stationarity (ρ₁), 0/12 passed Net PnL, 0/12 passed Sharpe.
- **Sharpe range:** −2.234 … −3.677 (undeflated annualized IS Sharpe, annualization √1512, friction 1.2 bps roundtrip).
- **R4:** skipped by the early-termination rule (failure condition reached in-sample).
- **Status:** `VERIFIED` (R3 forensic closure audit + governance hardening completed this session, 2026-09-07)

### Complete HYP_002 lifecycle
| Step | Status |
|---|---|
| R1 Pre-registration | ✅ PASS & SEALED |
| R2 Data Preparation | ✅ PASS & SEALED |
| R3 In-Sample Search Census | ✅ PASS AS PROCESS (12/12 executed, 0/12 qualified) |
| R4 Validation | ⏭️ SKIPPED / EARLY-TERMINATED |

---

## 6. CRYPTOGRAPHIC DIGESTS (HYP_002)

> These digests are **historical and immutable**. They MUST NOT be altered.

| Artifact | Digest |
|---|---|
| Sealed hypothesis spec (`HYP_TSMOM_EURUSD_HTF_002.json`) | `47c077a65f3057ae5ec83c8e7cf9179ababea9e5b18bc999bdc480a44f544afe` |
| R3 Search Trial Ledger (`ledger_digest`) | `d6d627334a1560193c495947e4f9ab3a62e983ac46cba1ef4cf51a1707dd6565` |
| R3 Manifest (`r3_manifest_HYP_TSMOM_EURUSD_HTF_002.json`) | `809ac530c69745924550723b19b79a7a82bd4182659f6eb2a5cfc4b019c24ccd` |

Digest lineage cross-check (`VERIFIED` this session):
- R3 manifest's `hypothesis_sha256` == sealed hypothesis digest.
- R3 manifest's `ledger_digest` == ledger JSON `ledger_digest` field. (Ledger digest is the canonical sealed-model digest, not a raw file hash.)

---

## 7. DATA QUARANTINE STATE

Cross-Hypothesis Data Quarantine is a **HARD INVARIANT**. Every protected partition is `PRISTINE` / `UNEXPOSED`.

| Protected Span | Bars | Status |
|---|---|---|
| HYP_002 H4 Validation | 3751..4996 | `QUARANTINED / PRISTINE` — NOT REUSABLE FOR HYP_003 BY DEFAULT |
| HYP_002 H4 Blind OOS | 5009..6230 | `QUARANTINED / PRISTINE` — NOT REUSABLE FOR HYP_003 BY DEFAULT |
| 2026 M5 Holdout (HYP_001) | 6060..9999 | `QUARANTINED / PRISTINE` |

Enforced in code:
- `src/acash/research/quarantine.py` — `PERMANENTLY_QUARANTINED_HOLDOUTS`:
  - `"HYP_TSMOM_EURUSD_001": (6060, 9999)`
  - `"HYP_TSMOM_EURUSD_HTF_002": (3751, 6230)`
- `src/acash/research/reinception.py` — `PERMANENTLY_QUARANTINED_WINDOWS`:
  - `"EURUSD_M5_HOLDOUT"`: `2026-08-18T04:40:00+00:00` → `2026-09-04T21:00:00+00:00`
  - `"EURUSD_H4_VALIDATION_OOS"`: `2023-05-29T16:00:00+00:00` → `2024-12-31T20:00:00+00:00`

Status: `VERIFIED` (quarantine fail-closed behavior covered by unit tests).

---

## 8. CAPITAL / TRADING AUTHORITY

| Authority | State |
|---|---|
| Live Capital Authority | `$0.00` (Hard-Locked) |
| Live Order Emission | `0` |
| Trading Authority | `LOCKED` |
| Broker Connection | `DISCONNECTED / NONE` |

Status: `VERIFIED`. No capital or trading authorization was modified.

---

## 9. GOVERNANCE FIXES COMPLETED (this session)

Committed hardening fixes for HYP_002 governance closure:

1. **HAC bandwidth methodology annotated (`VERIFIED`).** R3 executed `HacBandwidthMethod.NEWEY_WEST_PLUGIN` (Newey-West 1994 rule-of-thumb, bandwidth `8` for all trials), not the previously documented Andrews (1991) AR(1) plug-in. Recorded as a governance-maintenance annotation in the design doc, R3 audit report (§5.1), and dossier (§4b.1). Historical result NOT rewritten; no re-run.
2. **Haircut Sharpe terminology clarified (`VERIFIED`).** R3's `haircut_sharpe_annualized` / ledger `in_sample_sharpe` is the **undeflated annualized in-sample Sharpe** (`mean/std(ddof=1) × √1512`). The canonical Phase-6 Haircut Sharpe is **multiple-testing–adjusted** (`MultipleTestingEngine.calculate_bonferroni_haircut_sharpe`). **Never conflate the two.** Mapping documented (audit §5.2, dossier §4b.2, design doc).
3. **HYP_002 added to the terminal hypothesis registry (`VERIFIED`)** — `TERMINAL_HYPOTHESIS_REGISTRY` in `src/acash/research/reinception.py`.
4. **HYP_002 protected H4 Validation/OOS region added to quarantine enforcement (`VERIFIED`)** — both `quarantine.py` and `reinception.py`.
5. **H4 `UNLOCKED_FOR_R3_CENSUS` dataset exposure state supported (`VERIFIED`)** — added to `DatasetExposureState` enum so the H4 R2/R3 train partition is recognized (fixes a latent `UNKNOWN` fail for the legitimate drawn-in-sample behavior).
6. **Dossier ledger digest typo corrected (`VERIFIED`)** — mermaid digest updated `18c1df66…` → `d6d62733…`; actual ledger untouched.

---

## 10. TEST AND TYPE-CHECK RESULTS

| Check | Result | Status |
|---|---|---|
| Full local test suite | **1534 passed, 1 skipped, 0 failures, 3 warnings** | VERIFIED (this session) |
| MyPy (`src/ tests/`) | **0 issues over 310 source files** | VERIFIED (this session) |
| Post-fix static governance audit | **17/17 assertions PASS** | VERIFIED (this session) |
| Remote CI / GitHub | `NOT INDEPENDENTLY VERIFIED` (not re-pushed this session) | REPORTED (unverified) |

The 3 warnings were inspected: (2) `Pandas4Warning: Timestamp.utcnow deprecated` in `tests/unit/backtest/test_nautilus_bridge.py`; (1) expected pydantic serializer warning in `test_mt5_reconciliation.py` (`INVALID_MODE` enum). All classified as expected behavior / dependency debt, not actionable defects.

> Gate: test success is an **output**, not proof of scientific validity. See Section 12.

---

## 11. KNOWN METHODOLOGICAL CAVEATS

- **Scope of HYP_002 falsification (`VERIFIED`):** the result falsifies only *"univariate unconditional price momentum on EURUSD H4 under HYP_002."* It does **NOT** prove:
  - universal mean reversion;
  - failure of all momentum strategies;
  - failure of other assets or timeframes;
  - profitability of carry / macro / orderflow;
  - profitability in 2026.
- **Epistemic boundary:** a failed momentum hypothesis must never be turned into a positive mean-reversion claim without a new, independently registered hypothesis.
- **Haircut Sharpe seam (`VERIFIED`):** R3's undeflated annualized IS Sharpe is **NOT** the canonical multiple-testing–adjusted Haircut Sharpe. No Bonferroni/DSR deflation was applied in R3. The two metrics must never be conflated.
- **HAC method deviation (`VERIFIED`):** executed method was Newey-West plug-in, not Andrews (1991). All 12 HAC t-stats were negative (−0.31 … −1.58), far below the +2.00 hurdle, so the verdict is unaffected by the method.
- **Statistical dependence (`RETENTION`):** candidate models sharing underlying data remain statistically dependent; marginal vs. conditional admission probabilities are distinct. No claim of orthogonality is made.

---

## 12. PHASE 14 CURRENT STATUS

- **Design documents exist:**
  - `docs/phase14/phase14_master_research_architecture_plan.md` (Rev 1.2, `PROPOSED MASTER RESEARCH ARCHITECTURE - HUMAN APPROVAL PENDING`)
  - `docs/phase14/phase14_architecture_and_governance_plan.md` (v1.0)
- **Status:** `DESIGN READY` → `HUMAN APPROVAL PENDING` → `IMPLEMENTATION PENDING`.
- **Runtime module:** **NOT IMPLEMENTED** — no package exists under `src/acash/research/ai`.
- **Purpose:** Research Intelligence only. AI output is an **`UNVALIDATED PROPOSAL`**.
- **Phase 14 has ZERO authority** to: register hypotheses, qualify alpha, certify backtests, authorize trading, access capital, bypass R1 / R2 / R3, bypass quarantine, or override human governance.
- **Future flow:**
  ```
  Phase 14 Research Intelligence
    → candidate research proposal
    → ResearchReInceptionGate
    → NEW R1 → R2 → R3 → later validation/governance
  ```
- **Do NOT create HYP_003 yet.**

---

## 13. WHAT MUST NOT BE DONE

- Do NOT create `HYP_003` yet.
- Do NOT reuse `HYP_002` Validation/OOS partitions (quarantined).
- Do NOT reuse the 2026 M5 Holdout (quarantined).
- Do NOT run more `HYP_002` trials.
- Do NOT run Validation / OOS / backtests on quarantined data.
- Do NOT access, modify, or delete the 2026 M5 Holdout.
- Do NOT acquire new market data without authorization.
- Do NOT connect to a broker.
- Do NOT allocate capital > `$0.00`.
- Do NOT alter historical HYP_001 / HYP_002 results or their digests (Sections 4, 5, 6).
- Do NOT treat AI / Phase 14 output as anything other than an `UNVALIDATED PROPOSAL`.
- Do NOT run Phase 14 runtime (it does not exist yet).

---

## 14. NEXT RECOMMENDED ACTION

**Review / authorize Phase 14 implementation.**

This is the architecture-phase gate. Approval of the Phase 14 plan (design) vs. authorization to implement the Phase 14 runtime are **separate authorizations**. Only after Phase 14 human authorization may the Research Intelligence runtime be built, and only after that may it propose a candidate for `HYP_003` (which itself requires a fresh, independent R1 pre-registration).

---

## 15. EXACT RESUME CHECKLIST FOR NEXT SESSION

> Optimized for resuming from another machine/session. On opening this document, resume here directly — you do not need to re-read prior history.

### Step 1 — Verify clean synchronization
```powershell
git fetch origin
git status          # expect: working tree CLEAN
git log -3 --oneline
git rev-parse HEAD
```

### Step 2 — Verify virtual environment & type checker
```powershell
uv sync
uv run mypy src/ tests/
# Expected: Success: no issues found in 310 source files
```

### Step 3 — Verify HYP_002 closure digests (immutable anchors)
```powershell
Get-Content docs/phase8.5/manifests/r3_manifest_HYP_TSMOM_EURUSD_HTF_002.json | ConvertFrom-Json |
  Select-Object hypothesis_sha256, ledger_digest
# hypothesis_sha256 == 47c077a65f3057ae5ec83c8e7cf9179ababea9e5b18bc999bdc480a44f544afe
# ledger_digest       == d6d627334a1560193c495947e4f9ab3a62e983ac46cba1ef4cf51a1707dd6565
```

### Step 4 — Verify governance/quarantine enforcement
- Confirm `HYP_TSMOM_EURUSD_HTF_002` is in `TERMINAL_HYPOTHESIS_REGISTRY` (`reinception.py`).
- Confirm `("HYP_TSMOM_EURUSD_HTF_002", (3751, 6230))` is in `PERMANENTLY_QUARANTINED_HOLDOUTS` (`quarantine.py`) and the H4 window is in `PERMANENTLY_QUARANTINED_WINDOWS`.

### Step 5 — Run targeted governance regression
```powershell
uv run pytest tests/unit/research/test_governance_hardening.py tests/unit/research/test_research_reinception_gate.py -q
# Expected focuses: HYP_002 registry membership; H4 validation/OOS quarantine fail-closed; positive H4 train path
```

### Step 6 — Run full regression suite (optional but recommended before any code change)
```powershell
uv run pytest -q
# Expected (reference): 1534 passed, 1 skipped, 0 failures, 3 warnings
```

### Step 7 — Next session objective
1. Read `docs/phase14/phase14_master_research_architecture_plan.md` (and `phase14_architecture_and_governance_plan.md`).
2. Obtain **human authorization** for Phase 14 implementation (separate from design approval).
3. Only then implement the Research Intelligence runtime under `src/acash/research/ai`.
4. Only after that may it propose a candidate for `HYP_003` — via `ResearchReInceptionGate` → NEW R1.

**System is RESEARCH STANDING BY. HYP_003 is NOT CREATED.**

---

## Appendix A — Historical Record: Phase 13 Slice 1 (Gate A)

The prior canonical handoff (2026-09-04, Phase 13 Slice 1 Gate A Pre-Live Certification) is superseded for *current-state* purposes but its governance evidence remains valid and is preserved:

- **Gate A:** `CERTIFIED` (Human Auditor Sign-Off 2026-09-04).
- **Gate B:** `STRICTLY LOCKED` — live capital `$0.00`.
- **Phase 13 status:** Steps 1–4 PASSED; strategy blocked (`NO QUALIFIED ALPHA`).
- Phase 13 Gate A evidence artifacts (A-3/A-10/A-11) and the B-1/B-2 remediation remain under their frozen digests in `docs/phase13/`.

This Phase 13 record does not change the current Phase 8.5 / HYP_002 closed state described in Sections 1–15.