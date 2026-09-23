# HYP_007 CORRECTED Terminal M1 Strategy Acceptance Dossier

[DECISION RECORD: PHASE 14 STEP R3 TERMINAL M1 EVALUATION — IMPLEMENTATION CORRECTION 001]
[HYPOTHESIS_ID: HYP_007]
[MECHANISM_ID: MEC-0017]
[DECISION_ID: DEC_TERMINAL_M1_HYP_007_CORRECTED_001]
[LIFECYCLE_STATE: M1_ACCEPTED_SUPPORTED_CORRECTED_001]
[TERMINAL_VERDICT: ACCEPTED_SUPPORTED_ON_REGISTERED_M1]
[EFFECTIVE_TERMINAL_DECISION: EFFECTIVE_AFTER_CORRECTION_001]

## 1. Decision Authority & Context

Under `AUTHORIZE_HYP_007_R3_ANCHOR_LINEAGE_CORRECTION_AND_REEXECUTION_001`, the
registered single trial ($K=1$) of `HYP_007` was re-executed with the corrected
`previous_regular_close` anchor lineage, superseding the defective result
at commit `89345e05f15fdd4d031800d01790fcd3209c08a3` (package `2ef78147b22e5b1e836269b215d26417bb4c284d4b767bd70eb11cd843b13113`).

## 2. Gate Verification Ledger

| Gate | Name | Threshold | Observed | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **G1** | Net Total Return | `> 0.0` | `0.81398619` | **PASS** |
| **G2** | Net Annualized Sharpe | `>= 1.00` | `1.686202192600117000` | **PASS** |
| **G3** | Max Drawdown | `<= 0.30` | `0.1175609627310022972937046720` | **PASS** |
| **G4** | Completed Trades | `>= 100` | `659` | **PASS** |
| **G5** | No Material Contract Failure | `== True` | `True` | **PASS** |
| **G6** | 2× Friction Stress Net Return | `> 0.0` | `0.664360149877033475783475785` | **PASS** |
| **G7** | 2× Friction Stress Net Sharpe | `>= 0.75` | `1.450544137964326000` | **PASS** |

**Conjunction Outcome:** All 7 acceptance gates `True`.

## 3. Cryptographic Verification (CORRECTED)

- **Corrected R3 Result Package SHA-256:** `d4bf18bb80ec650e4c4c0600a8cb5aebb762a7169b8b89111e604adf91293a25`
- **R2 Dataset Content SHA-256:** `4dcf8546b8583bc214684228e29b329226ece904404768bc921f55991f1777aa`
- **Signal Ledger SHA-256:** `394a9f5d87a3849886d827f6a7898e8be5f1990dcf53a2d081f800099d0eeea2`
- **Baseline Execution Ledger SHA-256:** `662f7ea3c77f1865031245de804e1dc1814da5e35052e021d9ca72de5166f94f`
- **Stress Execution Ledger SHA-256:** `578432e61234d268d544514bcf4b45596721f644d0c51569186bbff704f6b43b`
- **Trade Ledger SHA-256:** `f31337a29324e04314a9a6efb5fa66012e87b72f12c737aab9530e87b1ff45f2`

## 4. Governance Invariants & Required Next Action

- **M1 Characterization:** Validated replication on publication-exposed direct-SIP sample.
- **M2 Sample:** Locked under zero access.
- **Capital Authority:** `$0.00`.
- **Order Policy:** `NO_REAL_ORDERS = true`.
- **Paper & Live Execution:** Locked.
- **Human Authority Required:** A human governance decision is required before any subsequent phase, M2 access, or runtime authorization can occur.
