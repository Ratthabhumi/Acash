# HYP_007 Pre-R3 Economic Metric Binding Additive Correction 002
## Acceptance Gate Transcription Reconciliation & Pre-R3 Fail-Closed Verification

```text
[CORRECTION IDENTIFIER: HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING_CORRECTION_002]
[CORRECTION TYPE: ADDITIVE_PRE_R3_GATE_RECONCILIATION]
[UPSTREAM_CANONICAL_HEAD: 6ae052746edf3bbfebb86e997b42aa838e253174]
[TARGET_HYPOTHESIS_ID: HYP_007]
[TARGET_MECHANISM_ID: MEC-0017]
[HUMAN_AUTHORIZATION: AUTHORIZE_HYP_007_PRE_R3_GATE_RECONCILIATION_002]
[SUPERSEDED_METADATA_ARTIFACT: docs/phase14/HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING_001.md]
[SUPERSEDED_METADATA_SHA256: c6fd5488bcdc4021833a4d63ef060d23a7f099be4fa5a82a6cd269b7c359af68]
[R1_SOVEREIGN_AUTHORITY: docs/research/MEC-0017-HYP-007-strategy-preregistration.md]
[R1_SOVEREIGN_SHA256: 41a0a27f9237371538366546a1761884d636d6c6d2e01ad14a90aa1cc47e16c4]
[R2_DATASET_SHA256: 4dcf8546b8583bc214684228e29b329226ece904404768bc921f55991f1777aa]
[PRE_R3_CORRECTION_STATUS: SEALED_PASS]
[R3_READINESS: READY_FOR_SEPARATE_HUMAN_AUTHORIZATION]
[CAPITAL_AUTHORITY: $0.00 / NO_REAL_ORDERS=true]
[STRATEGY_RESULTS_STATUS: UNOBSERVED / SIGNALS=0 / TRADES=0 / PNL=0]
```

- **Document ID:** `docs/phase14/HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING_CORRECTION_002.md`
- **Governing Standard:** ACASH `AGENTS.md` (Strict Fail-Closed Contract, Single Canonical Authority, Literature Alignment, Zero Unverified Claims).

---

## 1. Executive Summary & Defect Statement

During the final pre-R3 human audit of the committed codebase (`6ae0527`), a material acceptance-gate transcription defect was discovered in `docs/phase14/HYP_007_PRE_R3_ECONOMIC_METRIC_BINDING_001.md`:
- **Defect 1 (G3):** In Section 5, Gate G3 was erroneously transcribed as $\text{Max Drawdown} \le 20.0\%$.
- **Defect 2 (G7):** In Section 4, Gate G7 was erroneously transcribed as $2\times\text{ Friction Stress Net Sharpe} \ge 0.50$.
- **Defect 3 (Gate Enumeration):** Narrative sections inadvertently referenced an obsolete gate template rather than the sovereign preregistered 7 gates of HYP_007.

This post-R1 gate drift is a material defect: relaxing Gate G7 from $\ge 0.75$ to $\ge 0.50$ or restricting Gate G3 from $\le 30.0\%$ to $\le 20.0\%$ alters the sovereign hypothesis acceptance boundary without authorization.

In accordance with strict fail-closed governance, this discrepancy is resolved **ADDITIVELY** before observing any strategy signal, trade, fill, P&L, Sharpe, or gate result. Original sealed R1 and R2 artifacts remain byte-for-byte immutable.

---

## 2. Defect Classification & Scope

- **Classification:** `PRE_R3_METADATA_GATE_DRIFT`
- **Scientific Hypothesis:** `UNCHANGED`
- **R1 Specification:** `UNCHANGED` (`docs/phase14/hypotheses/HYP_007.json`)
- **M1 Replication Sample:** `UNCHANGED` (`2021-07-01` through `2024-04-30`)
- **Trial Count $K$:** `UNCHANGED` ($K = 1$)
- **Strategy Mechanism:** `UNCHANGED` (MEC-0017)
- **Qualified Dataset:** `UNCHANGED` (`4dcf8546b8583bc214684228e29b329226ece904404768bc921f55991f1777aa`)
- **Executable Code Status:** Audit confirmed zero executable HYP_007 code had embedded the erroneous thresholds ($20\%$ or $0.50$). The single canonical gate authority has been formalized in `src/acash/research/step_r3_hyp_007_metrics.py`.

---

## 3. Sovereign Acceptance Gate Authority

Primary sovereign authority is established by `docs/research/MEC-0017-HYP-007-strategy-preregistration.md` Section 10 and ratified in `docs/phase14/hypotheses/HYP_007.json` (`parameter_config_json.acceptance_criteria`).

The authoritative, non-negotiable acceptance criteria for HYP_007 M1 evaluation are:

| Gate | Metric Name | Canonical Formulation | Sovereign Threshold | Direction |
| :---: | :--- | :--- | :---: | :---: |
| **G1** | `NET_TOTAL_RETURN` | $\text{FinalAUM} / \text{InitialAUM} - 1$ | $> 0.0$ | Strictly Positive |
| **G2** | `NET_ANNUALIZED_SHARPE` | Daily Net Returns, 252 PPY, ddof=1, rf=0 | $\ge 1.00$ | Hurdle Met |
| **G3** | `MAX_DRAWDOWN` | Net EOD Equity Curve Peak-to-Trough | $\le 30.0\%$ (0.30) | Within Ceiling |
| **G4** | `COMPLETED_TRADES` | Discrete Episodes: FLAT $\to$ POS $\to$ FLAT | $\ge 100$ | Sample Statistical Power |
| **G5** | `NO_MATERIAL_CONTRACT_FAILURE` | Strict Data & Execution Integrity | $== \text{True}$ | Zero Unhandled Errors |
| **G6** | `2X_FRICTION_STRESS_NET_RETURN` | Compounded Net Return Under 2× Friction | $> 0.0$ | Strictly Positive |
| **G7** | `2X_FRICTION_STRESS_NET_SHARPE` | Annualized Sharpe Under 2× Friction | $\ge 0.75$ | Friction Robustness |

### Evaluation Rules:
1. **Simultaneous Conjunction:** All seven gates must pass simultaneously:
   $$\text{HYP\_007\_M1\_PASS} \iff \bigwedge_{j=1}^7 G_j$$
2. **Zero Partial Pass / Scoring:** No averaging, weighting, or score-based trade-offs are permitted. If any single gate fails, HYP_007 M1 evaluation fails terminal closed.

---

## 4. Single Effective Code Authority

To prevent duplicate magic numbers and ensure single-authority enforcement in Step R3, the thresholds and evaluator are sealed in `src/acash/research/step_r3_hyp_007_metrics.py`:

```python
G1_NET_TOTAL_RETURN_MIN_EXCLUSIVE: Decimal = Decimal("0.0")
G2_NET_SHARPE_MIN: Decimal = Decimal("1.00")
G3_MAX_DRAWDOWN_MAX: Decimal = Decimal("0.30")
G4_COMPLETED_TRADES_MIN: int = 100
G5_REQUIRE_NO_MATERIAL_CONTRACT_FAILURE: bool = True
G6_STRESS_NET_RETURN_MIN_EXCLUSIVE: Decimal = Decimal("0.0")
G7_STRESS_NET_SHARPE_MIN: Decimal = Decimal("0.75")
```

The evaluator `evaluate_hyp_007_m1_acceptance_gates(...)` produces a structured `Hyp007M1AcceptanceReport` strictly enforcing this conjunction.

---

## 5. Preservation of Binding 001 Economic Semantics

All valid economic and accounting semantics established in Binding 001 remain fully operative:
1. **Starting AUM:** $\text{SIMULATED\_STARTING\_AUM\_USD} = \$100,000.00$ (Outcome C, non-capital accounting normalization).
2. **Daily Net Return:** $r_t = \text{EndingAUM}_t / \text{EndingAUM}_{t-1} - 1$.
3. **Net Total Return:** $\text{FinalAUM} / \text{InitialAUM} - 1$.
4. **Daily Sharpe Authority:** `calculate_annualized_sharpe` in `deflated_sharpe.py`, `periods_per_year=252`, `ddof=1`, `rf=0`, failing closed on zero variance.
5. **Drawdown:** Peak-to-trough from net end-of-day equity curve anchored at $\text{AUM}_0$.
6. **Completed Trade Semantics:** Round-trip FLAT $\to$ NONZERO $\to$ FLAT; directional flip closes 1 completed trade and initiates new opposite position.
7. **Fixed Intraday Shares:** Derived once daily from morning Open, prior-day AUM, and 15-day vol; repeated same-direction signals do not churn.
8. **Independent Compounding Paths:** Baseline and 2× stress maintain independent compounding equity paths.
9. **Excluded Session 2023-06-05:** Zero signals, zero trades, zero execution, zero P&L; unadjusted 15:59 close retained in continuous daily close lineage under Outcome V1.
10. **Benchmark:** Secondary contextual evidence only, not blocking G1–G7.

---

## 6. No Result-Dependent Rescue Invariant

Once Step R3 empirical strategy execution commences:
- It is **STRICTLY PROHIBITED** to modify G1–G7 thresholds, sample dates, AUM, provider contracts, quote condition policies, friction models, signal formulas, position sizing rules, or execution boundaries.
- Any future modification constitutes a new hypothesis and requires a separate hypothesis lineage.

---

## 7. Status & Next Action

- `PRE_R3_GATE_RECONCILIATION = SEALED_PASS`
- `R3_READINESS = READY_FOR_SEPARATE_HUMAN_AUTHORIZATION`
- `NEXT_REQUIRED_ACTION = AUTHORIZE_HYP_007_R3_M1_EXECUTION`
