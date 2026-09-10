# ACASH — Session Handoff

> **Document:** `docs/SESSION_HANDOFF.md`
> **Status:** ROUND 4 BLOCKED — CA-1 SOURCE-BINDING FIELD AWAITING HUMAN INPUT
> **Date:** 2026-09-10
> **Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`)
> **Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Implementation Correctness ≠ Mathematical Validity, Single Canonical Authority)

---

## 1. REPOSITORY CHECKPOINT (AUTHORITATIVE)

- **Branch:** `main`
- **HEAD commit at this session end:** see `git log --oneline -1` after pull

| Commit | Contains |
|---|---|
| latest | `docs/phase14/cand_free_macro_001_human_binding_worksheet.md` — Section O updated: CA-1 source-binding block now lists all 4 required components explicitly + Human Input Block added |
| latest | `docs/phase14/cand_free_macro_001_round4_specification.md` — Section 4.2 and Section 6 updated: CA-1 source-binding 4-component block + Human Input Block added |
| `b26bed2` | previous HEAD — TR-1 and CA-1 decision ratification, Round 4 specification |
| `954af2c` | `docs/phase14/cand_free_macro_001_human_specification_decision_surface.md` |
| `3e3d918` | `docs/phase14/cand_free_macro_001_validation_readiness.md` |

**Resume command:**
```powershell
git clone https://github.com/Ratthabhumi/Acash.git   # OR: git pull
git log --oneline -3                                  # verify HEAD
Get-Content docs/SESSION_HANDOFF.md                   # this file
```

---

## 2. CURRENT GOVERNANCE STATE

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                           ACASH GOVERNANCE LEDGER                             │
├───────────────────────────────────┬───────────────────────────────────────────┤
│ TR-1                              │ HUMAN-RATIFIED / BOUND                    │
│   secondary key                   │ (scheduled-calendar date ASC,             │
│                                   │  family order ASC)                        │
│   family order                    │ CPI < NFP < FOMC                          │
│ CA-1                              │ HUMAN-RATIFIED / BOUND (decision level)   │
│   session semantics               │ BOUND (5-point checklist ratified)        │
│   source-binding field            │ UNRESOLVED PROVENANCE ← HUMAN ACTION REQ  │
│ Round 4                           │ BLOCKED (exact blocker: CA-1 source field) │
│ Round 5                           │ NOT ENTERED                               │
│ D17 / SPX close-series pin        │ DEFERRED / OPEN (separate Group C item)   │
│ HYP_001 (M5 Intraday)            │ TERMINALLY_FALSIFIED / CLOSED / IMMUTABLE │
│ HYP_002 (H4 Session)             │ TERMINALLY_FALSIFIED / CLOSED             │
│ HYP_003                           │ NOT CREATED                               │
│ CAND-FREE-MACRO-001               │ CONDITIONALLY READY                       │
│ PRE-REGISTRATION                  │ NOT FULLY FROZEN                          │
│ EMPIRICAL VALIDATION              │ NOT AUTHORIZED                            │
│ BACKTEST                          │ NOT AUTHORIZED                            │
│ HYP_002 Validation (3751..4996)  │ QUARANTINED / PRISTINE (NOT REUSABLE)    │
│ HYP_002 Blind OOS (5009..6230)   │ QUARANTINED / PRISTINE (NOT REUSABLE)    │
│ 2026 M5 Holdout (6060..9999)     │ QUARANTINED / PRISTINE                    │
│ Live Capital Authority            │ $0.00 (Hard-Locked)                       │
│ Live Trading Authority            │ LOCKED                                    │
│ Broker Connection                 │ DISCONNECTED / NONE                       │
│ System                            │ RESEARCH STANDING BY                      │
└───────────────────────────────────┴───────────────────────────────────────────┘
```

---

## 3. SINGLE PENDING HUMAN ACTION (DO THIS FIRST)

The **only thing blocking Round 4 closure** is the CA-1 source-binding field.
Supply all four values below, then proceed to the next session prompt.

```
CA-1 SOURCE-BINDING FIELD — HUMAN INPUT BLOCK
=============================================

URL:
    [Human supplies: exact authoritative NYSE official trading/market-holiday calendar URL]

Version / Effective Version:
    [Human supplies: specific version or effective-date range identifier]

Archive Identifier / Reproducible Snapshot:
    [Human supplies: Wayback Machine URL, versioned release tag, or archived file hash]

Retrieval Rule:
    [Human supplies: reproducible procedure for exact future retrieval of this version]

Decision date: ______________
```

> **CRITICAL GOVERNANCE RULE (AGENTS.md + CA-1 CRITICAL SOURCE RULE):**
> The agent MUST NOT invent, guess, recommend, or silently substitute the NYSE calendar
> URL/provider/version/archive. These four fields MUST be Human-supplied.

---

## 4. NEXT SESSION PROMPT (USE AFTER FILLING ALL 4 FIELDS)

Once you fill in all four CA-1 source-binding values, send the agent this prompt:

```
Continue ACASH V5 — MACRO-001 from the current verified state.

CURRENT STATE
=============
- HEAD: [run: git log --oneline -1]
- TR-1: HUMAN-RATIFIED / BOUND
    secondary key = (scheduled-calendar date ASC, family order ASC)
    family order = CPI < NFP < FOMC
- CA-1: HUMAN-RATIFIED at decision level
    session semantics BOUND (5-point checklist)
- CA-1 source-binding: NOW RESOLVED — Human supplied:
    URL: [paste your value]
    Version / Effective Version: [paste your value]
    Archive Identifier / Reproducible Snapshot: [paste your value]
    Retrieval Rule: [paste your value]
- Round 4: BLOCKED (releasing now with CA binding)
- Round 5: NOT ENTERED
- D17/SPX close-series pin: separate dependency, do not resolve here
- No empirical/data/backtest work authorized
- HYP_003 NOT CREATED
- R1 NOT AUTHORIZED
- Trading LOCKED
- Capital = $0.00

TASK
====
1. Record the CA-1 source-binding field verbatim in:
   docs/phase14/cand_free_macro_001_human_binding_worksheet.md  (Section O.5 / CA-1 SOURCE-BINDING HUMAN INPUT block)
   docs/phase14/cand_free_macro_001_round4_specification.md     (Section 6 Human Input Block)

2. Run Round 4 closure audit:
   - Verify all Round-4 items (D14/D15/D16/EX/CO/TR/CA) are fully bound
   - Confirm CA-1 source-binding is now complete
   - Mark Round 4 = COMPLETE

3. Enter Round 5:
   - Create D19/D20 Decision Surface (Kill conditions + PASS/FAIL/INVALID thresholds)
   - STOP before selecting alpha / threshold values (Human decision required)

4. Do NOT:
   - enter empirical validation
   - run backtest
   - create HYP_003
   - authorize R1
   - authorize trading
   - calculate returns / p-values / Sharpe

STOP after D19/D20 Decision Surface is prepared and before Human selects alpha.
```

---

## 5. DECISION BINDING PROGRESS MAP

```
ROUND 0   ✅ COMPLETE — Group A batch defaults A1–A5 confirmed
ROUND 1   ✅ COMPLETE — D3 (W-B window), D4 (R_EC return formula)
ROUND 2   ✅ COMPLETE — D7 (B-A baseline), D8 (O-2 overlap drop rule)
ROUND 3A  ✅ COMPLETE — G-3a purge (event-day + next trading day)
ROUND 3B  ✅ COMPLETE — K=3 grid, S-2/S-5/S-7/S-8/S-9 statistical protocol
ROUND 4   🔴 BLOCKED  — all decisions bound EXCEPT CA-1 source-binding field
  ├─ D14 IS window       ✅ BOUND: 2013-12-01 → 2021-12-31
  ├─ D15 OOS window      ✅ BOUND: 2022-01-01 → 2024-12-31
  ├─ D16 Blind window    ✅ BOUND: 2025-01-01 → 2026-09-10
  ├─ EX  exclusion rule  ✅ BOUND: official-calendar admission
  ├─ CO  SPY cost model  ✅ BOUND: DEFERRED (robustness layer)
  ├─ TR-1 tie-break      ✅ BOUND: (date ASC, CPI < NFP < FOMC)
  └─ CA-1 source-binding ❌ UNRESOLVED PROVENANCE ← supply 4 fields above
ROUND 5   ⬜ NOT ENTERED — D19 Kill conditions, D20 PASS/FAIL/INVALID thresholds
  └─ Alpha / thresholds  ⬜ HUMAN DECISION REQUIRED (not selected)
Draft Freeze              ⬜ NOT PREPARED
Anti-HARKing review       ⬜ NOT PERFORMED
Pre-registration Freeze   ⬜ NOT DECLARED
Data Archive / Manifest   ⬜ NOT ASSEMBLED
Human Authorization       ⬜ NOT GRANTED
Empirical Validation      ⬜ NOT AUTHORIZED
```

---

## 6. COMPLETED STAGES (DO NOT RE-RUN)

- SSRN literature discovery
- Free-data feasibility review
- Bootstrap mechanism governance review
- MACRO-001 readiness review (Validation Readiness package, `3e3d918`)
- Human Specification Decision Surface (`954af2c`)
- Decision Compression (Human Binding Worksheet)
- Round 4 Source-Binding Discovery (this session) — CA-1 Human Input Block prepared

---

## 7. SESSION BOUNDARY (HARD, VERBATIM)

- `CAND-FREE-MACRO-001` remains **CONDITIONALLY READY**.
- `PRE-REGISTRATION` remains **NOT FULLY FROZEN**.
- `EMPIRICAL VALIDATION` remains **NOT AUTHORIZED**.
- `BACKTEST` remains **NOT AUTHORIZED**.
- `HYP_003` = **NOT AUTHORIZED** · `R1` = **NOT AUTHORIZED** · `ResearchReInceptionGate` = **NOT INVOKED**.
- `TRADING` = **LOCKED** · `CAPITAL` = **$0.00** · `BROKER` = **DISCONNECTED / NONE**.

**DO NOT BACKTEST YET.**

No empirical work is authorized until the full binding sequence completes with explicit Human authorization: no event study, returns, IC, Sharpe, p-values, backtest, parameter optimization, hypothesis creation, gate invocation, broker connection, or order generation.

---

## 8. WHAT MUST NOT BE DONE

- Do NOT invent the NYSE calendar URL, version, archive identifier, or retrieval rule.
- Do NOT create `HYP_003`.
- Do NOT reuse quarantined HYP_002 Validation/OOS or 2026 M5 Holdout partitions.
- Do NOT run Validation / OOS / backtests on quarantined data.
- Do NOT acquire new market data without authorization.
- Do NOT connect to a broker; do NOT allocate capital > `$0.00`.
- Do NOT alter historical HYP_001 / HYP_002 results or their digests (Sections 9, 10).
- Do NOT silently resolve a MACRO-001 decision gap — write `HUMAN DECISION REQUIRED`.
- Do NOT author any empirical/statistical claim for CAND-FREE-MACRO-001 before the pre-registration is frozen.
- Do NOT invent K, floors (`max(1e-12, val)`), neutral outcomes, or magic constants. Raise `DataContractError` instead.

---

## 9. HYPOTHESIS LINEAGE (HISTORICAL — IMMUTABLE)

| Hypothesis | Market / TF | Lifecycle | Final State |
|---|---|---|---|
| `HYP_TSMOM_EURUSD_001` | EURUSD M5 | R1→R2→R3 (0/9 qualified) → R4–R7 early-terminated | **TERMINALLY_FALSIFIED / CLOSED / IMMUTABLE** |
| `HYP_TSMOM_EURUSD_HTF_002` | EURUSD H4 | R1→R2→R3 (0/12 qualified) → R4 early-terminated | **TERMINALLY_FALSIFIED / CLOSED** |
| `HYP_003` | — | — | **NOT CREATED** |

HYP_002 closure: in-sample census exactly `K=12`; 0/12 qualified. Sharpe range −2.234 … −3.677 (undeflated annualized IS, √1512, 1.2 bps roundtrip). Status `VERIFIED` (closure audited 2026-09-07).

---

## 10. CRYPTOGRAPHIC DIGESTS (HYP_002) — IMMUTABLE, MUST NOT BE ALTERED

| Artifact | Digest |
|---|---|
| Sealed hypothesis spec (`HYP_TSMOM_EURUSD_HTF_002.json`) | `47c077a65f3057ae5ec83c8e7cf9179ababea9e5b18bc999bdc480a44f544afe` |
| R3 Search Trial Ledger (`ledger_digest`) | `d6d627334a1560193c495947e4f9ab3a62e983ac46cba1ef4cf51a1707dd6565` |
| R3 Manifest (`r3_manifest_HYP_TSMOM_EURUSD_HTF_002.json`) | `809ac530c69745924550723b19b79a7a82bd4182659f6eb2a5cfc4b019c24ccd` |

Lineage cross-check (VERIFIED): manifest `hypothesis_sha256` == sealed digest; manifest `ledger_digest` == ledger `ledger_digest` field.

---

## 11. DATA QUARANTINE STATE — HARD INVARIANT

| Protected Span | Bars | Status |
|---|---|---|
| HYP_002 H4 Validation | 3751..4996 | `QUARANTINED / PRISTINE` — NOT REUSABLE BY DEFAULT |
| HYP_002 H4 Blind OOS | 5009..6230 | `QUARANTINED / PRISTINE` — NOT REUSABLE BY DEFAULT |
| 2026 M5 Holdout (HYP_001) | 6060..9999 | `QUARANTINED / PRISTINE` |

Enforced in code: `src/acash/research/quarantine.py` (`PERMANENTLY_QUARANTINED_HOLDOUTS`) and `src/acash/research/reinception.py` (`TERMINAL_HYPOTHESIS_REGISTRY`, `PERMANENTLY_QUARANTINED_WINDOWS`). Status `VERIFIED`.

---

## 12. CAPITAL / TRADING AUTHORITY

| Authority | State |
|---|---|
| Live Capital Authority | `$0.00` (Hard-Locked) |
| Live Order Emission | `0` |
| Trading Authority | `LOCKED` |
| Broker Connection | `DISCONNECTED / NONE` |

Status `VERIFIED`. No authorization modified by the MACRO-001 documentation work.

---

## 13. PHASE 14 STATUS

- **Research-Intelligence runtime:** implemented (`feat(research-ai)` commits). AI output is an **`UNVALIDATED PROPOSAL`** with zero authority to register hypotheses, qualify alpha, certify backtests, authorize trading, access capital, bypass R1/R2/R3, bypass quarantine, or override human governance.
- **Free-data MACRO-001 lane:** governance documentation complete (readiness → decision surface → binding worksheet → Round 4 Human Input Block prepared). **Empirical work pending CA-1 source-binding + frozen pre-registration + Human authorization.**

---

## 14. EXACT RESUME CHECKLIST FOR NEXT SESSION

```powershell
git clone https://github.com/Ratthabhumi/Acash.git   # OR: git pull
git log --oneline -3                                  # verify latest HEAD
Get-Content docs/SESSION_HANDOFF.md                   # this file — checkpoint + boundaries
```

1. Fill in the **4 CA-1 source-binding fields** in Section 3 above.
2. Use the prompt template from **Section 4** to send to the agent.
3. Agent will: bind CA-1 → close Round 4 → enter Round 5 → prepare D19/D20 Decision Surface → **STOP before alpha**.
4. Human selects alpha/thresholds in a separate session.
5. Then: Draft Freeze → Anti-HARKing review → Pre-registration Freeze → Data Archive/Manifest → **explicit Human authorization** → only then empirical/backtest.

**System is RESEARCH STANDING BY. CAND-FREE-MACRO-001 is CONDITIONALLY READY. PRE-REGISTRATION is NOT FULLY FROZEN. EMPIRICAL VALIDATION and BACKTEST are NOT AUTHORIZED.**