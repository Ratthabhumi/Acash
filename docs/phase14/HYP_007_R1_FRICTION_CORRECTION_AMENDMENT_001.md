# HYP_007 R1 Additive Friction Correction Amendment 001
## FINRA TAF Rounding Authority Reconciliation & R2 Warm-Up Binding

```text
[AMENDMENT IDENTIFIER: HYP_007_R1_FRICTION_CORRECTION_AMENDMENT_001]
[AMENDMENT TYPE: ADDITIVE_R1_METADATA_RECONCILIATION]
[UPSTREAM_CANONICAL_HEAD: f965453bf95d0b1919f9b51e1fb4fdc2003e3b0d]
[TARGET_HYPOTHESIS_ID: HYP_007]
[TARGET_MECHANISM_ID: MEC-0017]
[HUMAN_AUTHORIZATION: AUTHORIZE_ADDITIVE_HYP_007_R1_FRICTION_CORRECTION_AMENDMENT_001]
[R1_ORIGINAL_ARTIFACTS_STATUS: PRESERVED_BYTE_FOR_BYTE_IMMUTABLE]
[R2_READINESS: READY_FOR_SEPARATE_HUMAN_AUTHORIZATION]
[R2_DATASET_STATUS: NOT_STARTED]
[CAPITAL_AUTHORITY: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/phase14/HYP_007_R1_FRICTION_CORRECTION_AMENDMENT_001.md`
- **Governing Standard:** ACASH `AGENTS.md` (Strict Fail-Closed Contract, Single Canonical Authority, Literature Alignment, Zero Unverified Claims).

---

## 1. Executive Summary & Defect Statement

During post-R1 canonical audit of the sealed `HYP_007` specification, one contract wording inconsistency was identified:
- In `docs/phase8.5/hypotheses/HYP_007.json` and `docs/phase14/hypotheses/HYP_007.json`, the `parameter_config_json.friction_model.finra_taf` string contained the phrase:
  `"Covered sales only; historical 7-tier schedule; round nearest cent"`
- Upstream sovereign friction authority `docs/research/manifests/MEC-0015-finra-taf-fee-schedule.json` specifies `"rounding_rule": "ROUND_CEILING_TO_CENT"` across all historical tiers pursuant to FINRA By-Laws Schedule A, Section 1(b)(1).
- SEC Section 31 in the same specification correctly specified `"round ceiling to cent"`.

In accordance with strict fail-closed governance, this discrepancy is resolved **ADDITIVELY**. The original sealed R1 artifacts remain byte-for-byte immutable. This amendment establishes the authoritative binding for all downstream execution, dataset qualification, and economic evaluation.

---

## 2. Implementation Audit & Defect Classification

An audit of the runtime execution engine (`src/acash/execution/regulatory_fees.py`) and its unit test suite (`tests/unit/execution/test_regulatory_fees.py`) was conducted:

1. **Implementation Code (`compute_finra_taf`):**
   ```python
   # src/acash/execution/regulatory_fees.py:371, 398
   # FINRA By-Laws Schedule A Section 1(b)(1) mandates rounding UP to nearest cent (ROUND_CEILING).
   fee = capped_fee.quantize(Decimal("0.01"), rounding=ROUND_CEILING)
   ```
2. **Deterministic Verification:**
   - Trade with sub-cent fee: 1 share @ $0.000166/share = $0.000166 $\to$ quantizes to **`$0.01`** (`ROUND_CEILING`).
   - Fractional cent fee: 100 shares @ $0.000119/share = $0.0119 $\to$ quantizes to **`$0.02`** (`ROUND_CEILING`).
   - Fee cap: 50,000 shares @ $0.000166/share = $8.30 (exact cap) $\to$ **`$8.30`**.
   - Buy transactions: exactly **`$0.00`** (sell-side only).
3. **Classification:**
   $$\mathbf{IMPLEMENTATION\_CORRECT\_R1\_METADATA\_INCORRECT}$$
   The Python execution engine already strictly implements `ROUND_CEILING_TO_CENT`. The defect was restricted to the descriptive metadata text string serialized into the R1 hypothesis JSON config.

---

## 3. Additive Friction Reconciliation Contract

1. **Effective Rounding Rule:**
   For all economic evaluations, dataset construction, backtesting, and transaction cost modeling under HYP_007:
   $$\text{FINRA\_TAF\_ROUNDING} = \mathbf{ROUND\_CEILING\_TO\_CENT}$$
2. **Separation from SEC Section 31:**
   - **SEC Section 31:** Applicable to covered sales only, 20-segment historical rate schedule, rounded ceiling to nearest cent (`ROUND_CEILING_TO_CENT`).
   - **FINRA TAF:** Applicable to covered sales only, 7-tier historical rate schedule, rounded ceiling to nearest cent (`ROUND_CEILING_TO_CENT`).
   - Calculations and fee caps are strictly independent.
3. **Canonical 7-Tier Schedule Verified:**

| Segment | Effective Period | Rate per Share | Fee Cap per Trade | Rounding Rule | Official Source |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | 2004-11-01 to 2011-06-30 | $0.000075 | $3.75 | `ROUND_CEILING_TO_CENT` | Notice to Members 04-70 |
| **2** | 2011-07-01 to 2012-02-29 | $0.000090 | $4.50 | `ROUND_CEILING_TO_CENT` | Regulatory Notice 11-27 |
| **3** | 2012-03-01 to 2012-06-30 | $0.000095 | $4.75 | `ROUND_CEILING_TO_CENT` | Regulatory Notice 12-06 |
| **4** | 2012-07-01 to 2021-12-31 | $0.000119 | $5.95 | `ROUND_CEILING_TO_CENT` | Regulatory Notice 12-31 |
| **5** | 2022-01-01 to 2022-12-31 | $0.000130 | $6.49 | `ROUND_CEILING_TO_CENT` | SR-FINRA-2020-032 (Phase 1) |
| **6** | 2023-01-01 to 2023-12-31 | $0.000145 | $7.27 | `ROUND_CEILING_TO_CENT` | SR-FINRA-2020-032 (Phase 2) |
| **7** | 2024-01-01 to 2024-12-31 | $0.000166 | $8.30 | `ROUND_CEILING_TO_CENT` | SR-FINRA-2020-032 (Phase 3) |

---

## 4. Pre-M1 Dataset Warm-Up Binding (Prompt §12)

HYP_007 strategy evaluation begins on M1 start date **`2021-07-01`**. To execute the first M1 session (`2021-07-01`) validly, the frozen mathematical contract requires historical inputs:

1. **Noise Area Requirement:**
   - Requires exactly 14 prior completed eligible regular trading sessions with complete 390 1-minute bars.
   - Evaluated using sovereign `NyseCa1Calendar`:
     The 14th prior regular trading session is **`2021-06-11` (Friday)**.
2. **Volatility Sizing Requirement:**
   - Requires 15 daily simple close-to-close returns of unadjusted closes (`DAILY_VOL_WINDOW_RETURNS_COUNT = 15, DDOF = 1, SHIFT = 1`).
   - Calculating 15 daily returns requires exactly 16 prior unadjusted daily closes ($t-1$ through $t-16$).
   - Evaluated using sovereign `NyseCa1Calendar`:
     The 16th prior regular trading session is **`2021-06-09` (Wednesday)**.
3. **Earliest Required Warm-Up Date:**
   $$\mathbf{Earliest\ Required\ Warm\text{-}Up\ Session = 2021\text{-}06\text{-}09\ (Wednesday)}$$
4. **Warm-Up Governance Boundaries:**
   - Pre-M1 warm-up data (`2021-06-09` through `2021-06-30`, exactly 16 sessions) exists solely to initialize frozen state arrays.
   - Warm-up sessions are **STRICTLY PROHIBITED** from generating strategy signals.
   - Warm-up sessions are **STRICTLY PROHIBITED** from executing trades or contributing to P&L.
   - Warm-up sessions require 1-minute OHLCV bars and daily closes only; execution quotes are **NOT** required for warm-up sessions.

---

## 5. R2 Execution Quote Boundary (Prompt §13 & §14)

1. Execution quotes may be retrieved only for M1 trading sessions (`2021-07-01` through `2024-04-30`) at designated execution decision boundaries:
   - `10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30, 15:00, 15:30 ET`
   - Forced EOD flatten: `[15:59:00, 16:00:00) ET`
2. Model: `FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY`.
3. No arbitrary timeout is permitted (no 2-second, 30-second, or 1-minute timeouts).
4. Only condition code `R` is executable; condition `?` and unmapped codes fail closed.

---

## 6. Scientific & Governance Invariants Summary

- **Scientific Hypothesis:** `UNCHANGED`
- **M1 Replication Sample:** `2021-07-01` through `2024-04-30` (`UNCHANGED`)
- **M2 Stress Sample:** `2024-05-01` onward (`LOCKED_ZERO_ACCESS`, `UNCHANGED`)
- **Trial Count $K$:** Exactly `1` (`UNCHANGED`)
- **Strategy Equations:** `UNCHANGED` (Noise Area, Bands, VWAP HLC3, 15d Vol Sizing nearest integer)
- **Economic Acceptance Gates:** `UNCHANGED` (G1–G7 strictly preserved)
- **HYP_007 Status:** `R1_SEALED_READY_FOR_R2`
- **R2 Readiness:** `READY_FOR_SEPARATE_HUMAN_AUTHORIZATION`
- **R2 Dataset Build:** `NOT_STARTED`
- **Capital Authority:** `$0.00` (`NO_REAL_ORDERS = true`)
