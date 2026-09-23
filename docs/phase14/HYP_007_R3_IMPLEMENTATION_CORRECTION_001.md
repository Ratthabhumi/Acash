# HYP_007 R3 Implementation Correction 001

[GOVERNANCE ARTIFACT: MATERIAL IMPLEMENTATION DEFECT CORRECTION]
[HYPOTHESIS_ID: HYP_007]
[MECHANISM_ID: MEC-0017]
[CORRECTION_ID: IMPLEMENTATION_CORRECTION_001]
[DEFECTIVE_COMMIT: 89345e05f15fdd4d031800d01790fcd3209c08a3]
[DEFECTIVE_RESULT_PACKAGE_SHA256: 2ef78147b22e5b1e836269b215d26417bb4c284d4b767bd70eb11cd843b13113]
[AUTHORIZATION: AUTHORIZE_HYP_007_R3_ANCHOR_LINEAGE_CORRECTION_AND_REEXECUTION_001]
[EFFECTIVE_TERMINAL_DECISION: terminal_decision_HYP_007_CORRECTED_001.json]

## 1. Defect Statement

**Defect Class:** `PREVIOUS_REGULAR_CLOSE_ANCHOR_LINEAGE_IMPLEMENTATION_DEFECT`

The prior R3 execution incorrectly derived `previous_regular_close` from `prior_14_sessions[-1]`
(the Noise-Area eligibility list) instead of `continuous_daily_closes` (the frozen R2 lineage).

### Affected Session

For session `2023-06-06`:
- `prior_14_sessions[-1]` = `2023-06-02`, close = `$427.91`
- Correct `continuous_daily_closes` prev entry = `2023-06-05`, close = `$427.10`
- Delta: **-$0.81**

### Three Lineages Must Remain Separate

| Lineage | Source | Includes 2023-06-05? |
| :--- | :--- | :--- |
| Noise-Area Eligibility | `prior_14_sessions` | NO |
| Volatility Close | `continuous_daily_closes` | YES ($427.10) |
| Previous-Regular-Close Anchor | `get_previous_regular_close()` → `continuous_daily_closes` | YES ($427.10) |

## 2. Correction

Added `get_previous_regular_close(session_date_str, continuous_daily_closes) -> Decimal` helper.
The anchor lineage now reads `continuous_daily_closes[i-1]` where `i` is the current session's
position — never `prior_14_sessions[-1]`.

## 3. Immutability of Defective Evidence

The following defective artifacts are preserved unchanged:
- `docs/phase14/manifests/manifest_r3_HYP_007.json`
- `docs/phase14/manifests/terminal_decision_HYP_007.json`
- `docs/research/MEC-0017-HYP-007-step-r3-execution-report.md`
- `docs/phase14/hyp_007_terminal_m1_decision_dossier.md`

## 4. Effective Authority After Correction

- `docs/phase14/manifests/manifest_r3_HYP_007_CORRECTED_001.json`
- `docs/phase14/manifests/terminal_decision_HYP_007_CORRECTED_001.json`
- `docs/research/MEC-0017-HYP-007-step-r3-corrected-execution-report.md`
- `docs/phase14/hyp_007_corrected_terminal_m1_decision_dossier.md`
- `docs/phase14/HYP_007_R3_IMPLEMENTATION_CORRECTION_001.md` (this document)
- `docs/phase14/manifests/HYP_007_R3_IMPLEMENTATION_CORRECTION_001.json`
