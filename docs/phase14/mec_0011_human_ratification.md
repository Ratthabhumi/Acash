# MEC-0011: HUMAN RATIFICATION RECORD (D1 / D2 / D3)

**Document ID:** `docs/phase14/mec_0011_human_ratification.md`
**Object:** Formal record of the three binding Human decisions for the MEC-0011 research track, post $0 data-feasibility audit and post decision-surface review.
**Status:** `[HUMAN RATIFIED]` `[DOCUMENTATION-ONLY]` `[NOT EMPIRICAL VALIDATION]` `[NOT HYP_003]` `[NOT R1]` `[NOT A CANDIDATE]`
**Decision date:** 2026-09-10
**Authority:** Human operator (sole ratifying authority for MEC-0011 governance decisions)
**ASCII-only:** YES (no non-ASCII bytes)

## 1. MEC-0011 IDENTITY

- Mechanism candidate: **MEC-0011 - Cross-Asset Gold / DXY Relative-Movement & Volume Divergence**.
- Working research object: the actual **ICE U.S. Dollar Index (DXY)** identity referenced by the source claim, and gold (spot/relative-movement) as its cross-asset counterpart.
- Source documents:
  - `docs/phase14/mec_0011_gold_dxy_relative_movement_intake.md` (intake record)
  - `docs/phase14/mec_0011_gold_dxy_data_feasibility_audit.md` (feasibility audit)
  - `docs/phase14/mec_0011_human_decision_surface.md` (decision surface this record ratifies)

## 2. CURRENT STATUS

- MEC-0011 remains: **RESEARCH INTAKE ONLY / NOT AUTHORIZED FOR EMPIRICAL VALIDATION**.
- No empirical result exists. No data was processed. No backtest was run. No parameter was optimized.
- Registries/candidates: NO promotion. No CAND-FREE or HYP identifier is created. `free_data_source_registry.md` is not modified; no Gold/DXY source is ACCEPTED.

## 3. DECISION INTRODUCTION

This record ratifies, without reinterpretation, the three selections made by the Human on the
MEC-0011 decision surface:

- **D1 = A** (Gold leg: accept Stooq XAUUSD under documented non-commercial/private research frame)
- **D2 = C** (DXY leg: ICE DXY as research identity, grey source)
- **D3 = B** (Volume branch: terminate literal-volume sub-mechanism; retain price/relative-movement track)

Each decision is recorded below with its DECISION ID, QUESTION, HUMAN SELECTION, RATIONALE,
BOUNDARY, DOWNSTREAM EFFECT, and REMAINING BLOCKERS.

---

## 4. D1 - GOLD LEG (License / Usage Frame)

### DECISION RECORD D1

**DECISION ID:** D1
**QUESTION:** Under what licensing/usage frame is the gold price leg allowed (if pursued)?
**HUMAN SELECTION:** A = Accept Stooq XAUUSD under a documented non-commercial/private research usage frame.
**RATIONALE:** (as stated by Human) The audited Stooq XAUUSD is the only deep daily $0 gold price candidate; its personal/non-commercial terms are compatible with private research use, non-redistribution, and archive-at-retrieval discipline.
**BOUNDARY:** `[HUMAN-ACCEPTED]` `[CONDITIONAL]`
- Private research use only. Non-commercial only. Archived data only. No redistribution.
- D1 does NOT mean Stooq is globally or commercially accepted.
- The licensing/usage frame must be documented (as a standing condition, not an inferred right).
- Archive-at-retrieval remains mandatory.
- No automatic upgrade of the source registry; Stooq is not represented as canonical institutional data.
**DOWNSTREAM EFFECT:** A gold price leg (Stooq XAUUSD, daily OHLC, ~1968+) may be bound into the research frame subject to the documented non-commercial/private conditions and archive discipline. All design work that touches the gold leg must carry the documented frame; any commercial or redistributed use is out of scope.
**REMAINING BLOCKERS:** B1 (license/usage documentation binding), B6 (PIT/archive methodology - Stooq `[PIT UNPROVEN]`, archive-at-retrieval proof), B9 (archive + manifest), plus B4 (timestamp/calendar binding) shared with the DXY leg.

---

## 5. D2 - DXY LEG (Identity)

### DECISION RECORD D2

**DECISION ID:** D2
**QUESTION:** Which dollar-index series becomes the research identity for MEC-0011's dollar leg?
**HUMAN SELECTION:** C = ICE DXY as the identity of the research object.
**RATIONALE:** (as stated by Human) The source claim refers to the actual ICE U.S. Dollar Index; MEC-0011 studies the ICE DXY identity, not a stand-in index.
**BOUNDARY:** `[HUMAN-ACCEPTED AS RESEARCH IDENTITY]` `[NOT DATA-VALIDATION-READY]` `[GREY SOURCE]`
- MEC-0011 studies the actual ICE DXY identity referenced by the source claim.
- Do NOT silently substitute FRED Fed dollar indexes. Do NOT silently substitute ECB reconstructed DXY.
- Critical identity distinction (cannot be conflated): Fed dollar index != ICE DXY; ECB reconstruction != ICE DXY.
- D2 authorizes identity selection only. It does NOT authorize empirical validation.
- D2 does NOT upgrade ICE DXY to `[ACCEPT]`.
- D2 does NOT establish that a free compliant ICE DXY historical archive exists.
- Any grey-source acceptance conditions (provenance/licensing acceptance; private-archive-only constraint) are NOT resolved by this identity selection; they remain to be formally bound in the SOURCE / PROVENANCE BINDING stage.
**DOWNSTREAM EFFECT:** The research object is fixed as the ICE DXY identity. No Fed or ECB dollar series may be silently substituted to overcome data availability. The point: a later "convenience" swap to TWEXBGS or a eurofxref proxy is prohibited without a new explicit Human decision.
**REMAINING BLOCKERS:** B2 (ICE DXY provenance/licensing), B3 (ICE DXY historical archive/access - free compliant access unestablished), B4 (timestamp/calendar binding), B6 (PIT/archive methodology), B7 (deterministic research specification), B8 (pre-registration), B9 (archive + manifest), B10 (explicit Human empirical-validation authorization).

---

## 6. D3 - VOLUME BRANCH (Disposition)

### DECISION RECORD D3

**DECISION ID:** D3
**QUESTION:** What happens to the literal volume-divergence branch of MEC-0011?
**HUMAN SELECTION:** B = Terminate the literal-volume branch while retaining the price/relative-movement track.
**RATIONALE:** (as stated by Human) The audit established that DXY has no native volume and that daily exchange-grade gold volume is not free; the literal volume-divergence sub-mechanism is therefore not operationalizable at $0.
**BOUNDARY:** `[HUMAN-ACCEPTED]` `[TERMINATED SUB-MECHANISM]`
- The literal "DXY volume mismatch vs Gold volume" mechanism is TERMINATED as an operational $0 sub-mechanism.
- MEC-0011 itself remains ALIVE via the price/relative-movement track.
- Do NOT create the GLD-vs-UUP variant.
- Do NOT substitute ETF volume for DXY volume.
- Do NOT create a new candidate or new intake.
- Do NOT infer predictive power from the original volume claim.
**DOWNSTREAM EFFECT:** No operational volume sub-mechanism remains within MEC-0011. Any future volume-related work requires a separate, explicitly commissioned intake/variant and a fresh Human decision. The price/relative-movement track is the only active MEC-0011 line; it remains subject to D1/D2 conditions and the blockers below.
**REMAINING BLOCKERS:** None for the volume branch (terminated). For the retained track: B1, B2, B3, B4, B5, B6, B7, B8, B9, B10 all remain open (see Task 2 blocker table).

---

## 7. DECISION RECORDING SUMMARY

| DECISION ID | QUESTION | HUMAN SELECTION | DATE | AUTHORITY | STATUS LABELS |
|---|---|---|---|---|---|
| D1 | Gold-leg license/usage frame | A (Stooq XAUUSD, non-commercial/private research frame) | 2026-09-10 | Human | `[HUMAN-ACCEPTED]` `[CONDITIONAL]` |
| D2 | DXY-leg identity | C (ICE DXY as research identity; grey source) | 2026-09-10 | Human | `[HUMAN-ACCEPTED AS RESEARCH IDENTITY]` `[NOT DATA-VALIDATION-READY]` `[GREY SOURCE]` |
| D3 | Volume-branch disposition | B (terminate literal-volume branch; retain price track) | 2026-09-10 | Human | `[HUMAN-ACCEPTED]` `[TERMINATED SUB-MECHANISM]` |

## 8. EXPLICIT NON-AUTHORIZATIONS (RATIFICATION ROUND)

The Human decisions D1-D3 are NOT authorization for:
- backtesting, empirical validation, signal testing, parameter search
- hypothesis registration, HYP_003 creation, R1 invocation
- trading, live or paper execution
- candidate authorization or registry promotion
- any modification of F-1, MACRO-001, HYP-001, HYP-002, HYP registries, Phase-6, gate logic, trading authorization, capital state, or R1

## 9. CROSS-REFERENCE

- Ratifies selections recorded in `docs/phase14/mec_0011_human_decision_surface.md` (D1/D2/D3 blocks).
- Carries audit classifications from `docs/phase14/mec_0011_gold_dxy_data_feasibility_audit.md` without upgrade.
- Next governance stage (not commenced here): **SOURCE / PROVENANCE BINDING** (see `mec_0011_post_decision_feasibility.md`).

### Verification Ledger
- Implementation Status: N/A (documentation-only ratification record; no code, no data, no computation)
- Contract Enforcement: STRICT FAIL-CLOSED - no evidence upgraded; no registry modified; no authorization extended
- Mathematical Authority: N/A (no formulation claimed)
- Local Test Suite: NOT RUN (no code touched)
- Type Checker (MyPy): NOT RUN (no code touched)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: decision date 2026-09-10; D1 mandate recorded as conditional private/non-commercial research use; D2 identity ratified while provenance/licensing/access remain unresolved (grey); D3 terminates the literal-volume sub-mechanism without retroactive claims; no empirical result exists.