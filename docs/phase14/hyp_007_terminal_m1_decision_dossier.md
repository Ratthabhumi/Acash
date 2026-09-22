# HYP_007 Terminal M1 Strategy Acceptance Dossier

[DECISION RECORD: PHASE 14 STEP R3 TERMINAL M1 EVALUATION]
[HYPOTHESIS_ID: HYP_007]
[MECHANISM_ID: MEC-0017]
[DECISION_ID: DEC_TERMINAL_M1_HYP_007]
[LIFECYCLE_STATE: M1_ACCEPTED_SUPPORTED]
[TERMINAL_VERDICT: ACCEPTED_SUPPORTED_ON_REGISTERED_M1]

## 1. Decision Authority & Context

Under `AUTHORIZE_HYP_007_R3_M1_EXECUTION` issued on canonical starting commit `099fb460396b957cb51dd486cfb4be4f11901c0a`, the registered single trial ($K=1$) of `HYP_007` (MEC-0017: SPY Noise-Area Intraday Momentum Direct-SIP Net-Profitability Replication) was executed on the qualified M1 sample (`2021-07-01` through `2024-04-30`).

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

**Conjunction Outcome:** All 7 acceptance gates PASS.

## 3. Cryptographic Verification

- **R3 Result Package SHA-256:** `2ef78147b22e5b1e836269b215d26417bb4c284d4b767bd70eb11cd843b13113`
- **R2 Dataset Content SHA-256:** `4dcf8546b8583bc214684228e29b329226ece904404768bc921f55991f1777aa`
- **Signal Ledger SHA-256:** `f4dbb4b98ac145320da9543c42f5060f832aada17dd3b148492d03c236a5ed46`
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
