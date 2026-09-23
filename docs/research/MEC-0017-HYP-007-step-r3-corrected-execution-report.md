# MEC-0017 HYP_007 Step R3 CORRECTED Execution & Terminal Gate Acceptance Report

[GOVERNANCE ARTIFACT: STEP R3 STRATEGY EXECUTION & G1-G7 ACCEPTANCE — IMPLEMENTATION CORRECTION 001]
[HYPOTHESIS_ID: HYP_007]
[MECHANISM_ID: MEC-0017]
[AUTHORIZATION: AUTHORIZE_HYP_007_R3_ANCHOR_LINEAGE_CORRECTION_AND_REEXECUTION_001]
[CORRECTION_ID: IMPLEMENTATION_CORRECTION_001]
[STARTING_CANONICAL_HEAD: 099fb460396b957cb51dd486cfb4be4f11901c0a]
[DEFECTIVE_R3_COMMIT: 89345e05f15fdd4d031800d01790fcd3209c08a3]
[DEFECTIVE_R3_RESULT_PACKAGE_SHA256: 2ef78147b22e5b1e836269b215d26417bb4c284d4b767bd70eb11cd843b13113]
[R3_EXECUTION_STATUS: CORRECTED_COMPLETE_SEALED]
[TERMINAL_VERDICT: ACCEPTED_SUPPORTED_ON_REGISTERED_M1]
[EFFECTIVE_TERMINAL_DECISION: EFFECTIVE_AFTER_CORRECTION_001]

## 1. Correction Summary

### 1.1 Defect Identification
The prior R3 execution (commit `89345e05f15fdd4d031800d01790fcd3209c08a3`, result package
`2ef78147b22e5b1e836269b215d26417bb4c284d4b767bd70eb11cd843b13113`) contained a material implementation defect:

**Defect Class:** `PREVIOUS_REGULAR_CLOSE_ANCHOR_LINEAGE_IMPLEMENTATION_DEFECT`

**Root Cause:** Line `prev_close_raw = bars_by_sess[prior_14_sessions[-1]][-1]["close"]`
incorrectly derived `previous_regular_close` from the Noise-Area eligibility list
(`prior_14_sessions[-1]`) instead of from the continuous daily-close lineage
(`continuous_daily_closes`).

**Session Affected:** `2023-06-06` only.

| Anchor Source | Session | Close Used |
| :--- | :--- | :--- |
| **Defective** (`prior_14_sessions[-1]`) | `2023-06-02` | `$427.91` |
| **Correct** (`continuous_daily_closes`) | `2023-06-05` | `$427.10` |
| **Delta** | — | **-$0.81** |

### 1.2 Contract Authority
Section 5.2 of `docs/research/MEC-0017-HYP-007-strategy-preregistration.md`:
> `prev_close_adjusted = previous_regular_close - current_day_cash_dividend`

`previous_regular_close` = immediately preceding entry in `continuous_daily_closes`
(the frozen R2 daily-close lineage), NOT `prior_14_sessions[-1]`.

### 1.3 Lineage Invariant
Three SEPARATE lineages:
- **A — Noise-Area Eligibility** (`prior_14_sessions`): excludes `2023-06-05`. ✓ Unchanged.
- **B — Daily Volatility Close** (`continuous_daily_closes`): includes `2023-06-05` at `$427.10`. ✓ Unchanged.
- **C — Previous-Regular-Close Anchor** (`get_previous_regular_close()`): reads B. **CORRECTED.**

### 1.4 Additive Supersession Record
The defective historical artifacts remain immutable at their original paths:
- `docs/phase14/manifests/manifest_r3_HYP_007.json`
- `docs/phase14/manifests/terminal_decision_HYP_007.json`
- `docs/research/MEC-0017-HYP-007-step-r3-execution-report.md`
- `docs/phase14/hyp_007_terminal_m1_decision_dossier.md`

This corrected report and associated `_CORRECTED_001` manifests are the effective
scientific authority after this correction.

---

## 2. Corrected Execution — Cryptographic Lineage & Result Hashes

| Artifact / Evidence Ledger | Authoritative SHA-256 Digest | Status |
| :--- | :--- | :--- |
| **R2 Dataset Content Digest** | `4dcf8546b8583bc214684228e29b329226ece904404768bc921f55991f1777aa` | VERIFIED_MATCH |
| **Signal Ledger SHA-256** | `394a9f5d87a3849886d827f6a7898e8be5f1990dcf53a2d081f800099d0eeea2` | SEALED |
| **Baseline Execution Ledger SHA-256** | `662f7ea3c77f1865031245de804e1dc1814da5e35052e021d9ca72de5166f94f` | SEALED |
| **Stress Execution Ledger SHA-256** | `578432e61234d268d544514bcf4b45596721f644d0c51569186bbff704f6b43b` | SEALED |
| **Trade Ledger SHA-256** | `f31337a29324e04314a9a6efb5fa66012e87b72f12c737aab9530e87b1ff45f2` | SEALED |
| **Baseline Daily Equity SHA-256** | `13d150866b30c6502eb55c6daa33ff4a80ffae818ca21473fe35ceb332a13d0f` | SEALED |
| **Stress Daily Equity SHA-256** | `3d0daf6a410512a548c38ba0074ce242b089f552898ef36991278ffc6c0badda` | SEALED |
| **Gate Evaluation SHA-256** | `38d887f0e0fd497e749c4fcad3eeea413cde41a9be54117118911e16867f0a9b` | SEALED |
| **Complete R3 Result Package SHA-256 (CORRECTED)** | **`d4bf18bb80ec650e4c4c0600a8cb5aebb762a7169b8b89111e604adf91293a25`** | **SEALED_CORRECTED_EFFECTIVE** |

---

## 3. Corrected Empirical Economics Summary

| Metric | Baseline Institutional Model | 2× Friction Stress Model |
| :--- | :--- | :--- |
| **Initial AUM** | `$100,000.00` | `$100,000.00` |
| **Final Ending AUM** | `$181398.6190` | `$166436.0150` |
| **Net Total Return** | `81.3986%` | `66.4360%` |
| **Annualized Sharpe (252d)** | `1.686202192600117000` | `1.450544137964326000` |
| **Max Drawdown** | `11.7561%` | `12.5290%` |
| **Completed Trades** | `659` | `659` |

---

## 4. Corrected Acceptance Gate Details (G1–G7)

1. **G1: Net Total Return > 0.0**
   - Observed: `0.81398619` → **PASS**
2. **G2: Net Annualized Sharpe >= 1.00**
   - Observed: `1.686202192600117000` → **PASS**
3. **G3: Max Drawdown <= 0.30**
   - Observed: `0.1175609627310022972937046720` → **PASS**
4. **G4: Completed Trades >= 100**
   - Observed: `659` → **PASS**
5. **G5: No Material Contract Failure == True**
   - Observed: `True` → **PASS**
6. **G6: 2× Friction Stress Net Return > 0.0**
   - Observed: `0.664360149877033475783475785` → **PASS**
7. **G7: 2× Friction Stress Net Sharpe >= 0.75**
   - Observed: `1.450544137964326000` → **PASS**

**Conjunction Outcome:** All 7 gates: `True`

---

## 5. Methodological & Governance Boundaries

1. **Same R2 dataset:** Identical sealed parquet (SHA `4dcf8546...`) — no new data acquired.
2. **Trial count K=1:** Corrected re-execution of the same registered trial, NOT a new K.
3. **M2 Zero Access Invariant:** M2 (`>= 2024-05-01`) strictly locked.
4. **Sovereign Capital:** `$0.00`. `NO_REAL_ORDERS = true`.
5. **Next Step:** Human governance decision required before any M2 access or paper/live execution.
