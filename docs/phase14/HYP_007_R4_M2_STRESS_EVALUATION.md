# HYP_007 Step R4: M2 Post-Publication Stress Evaluation Dossier
## Rigorous Recent-Regime Stress Evaluation on Sample M2 (2024-05-01 through 2026-08-14)

```text
[EVALUATION IDENTIFIER: HYP_007_R4_M2_STRESS_EVALUATION]
[HYPOTHESIS_ID: HYP_007]
[MECHANISM_ID: MEC-0017]
[AUTHORIZATION: AUTHORIZE_HYP_007_POST_M1_FREEZE_AND_CONDITIONAL_R4_M2_EXECUTION]
[SAMPLE: M2_POST_PUBLICATION_STRESS_SAMPLE]
[ROLE: PUBLICLY_EXPOSED_POST_PUBLICATION_STRESS_SAMPLE]
[CLASSIFICATION: NOT_PRISTINE_OOS]
[M2_WINDOW: 2024-05-01 THROUGH 2026-08-14]
[M2_SIMULATED_STARTING_AUM: $100,000.00]
[R4_VERDICT: FAIL_CURRENT_EDGE_NOT_SUPPORTED]
[R4_PACKAGE_SHA256: 9fbf1413e8ad517d6ee5b7c1a77d0c7324a359396c9e0591beaba0344d3c52b0]
[M2_DATASET_CONTENT_SHA256: 4b2e997ed825359cb6830b03759fdeebe9ba666426e434ddbb91c771e1ba1284]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
[PAPER_AUTHORITY: LOCKED]
[LIVE_AUTHORITY: LOCKED]
[M3_STATE: LOCKED_ZERO_ACCESS]
```

- **Document ID:** `docs/phase14/HYP_007_R4_M2_STRESS_EVALUATION.md`
- **Governing Standard:** ACASH `AGENTS.md` (Strict Fail-Closed Contract, Literature Alignment, Zero Unverified Claims).

---

## 1. Executive Summary & Verdict

Step R4 executes the preregistered HYP_007 strategy across the publicly exposed recent stress window **M2** (`2024-05-01` through `2026-08-14`).
- **Terminal R4 Verdict:** `FAIL_CURRENT_EDGE_NOT_SUPPORTED`
- **Combined Interpretation:** `HISTORICAL_REPLICATION_SUPPORTED_BUT_CURRENT_EDGE_NOT_SUPPORTED`

### Performance Summary:
- **Baseline Initial AUM:** $100000.00
- **Baseline Final AUM:** $103504.05
- **Baseline Net Total Return:** 3.50%
- **Baseline Annualized Sharpe:** 0.1762
- **Baseline Max Drawdown:** 21.70%
- **Baseline Completed Trades:** 503
- **2x Friction Stress Final AUM:** $96042.29
- **2x Friction Stress Total Return:** -3.96%
- **2x Friction Stress Sharpe:** -0.0506
- **2x Friction Stress Max Drawdown:** 24.16%

---

## 2. Gate Evaluation Ledger

| Gate | Metric Name | Observed Value | Frozen Hurdle | Gate Verdict |
| :---: | :--- | :---: | :---: | :---: |
| **R4-G1** | `NET_TOTAL_RETURN` | 3.50% | $> 0.0$ | PASS |
| **R4-G2** | `NET_ANNUALIZED_SHARPE` | 0.1762 | $\ge 0.50$ | FAIL |
| **R4-G3** | `MAX_DRAWDOWN` | 21.70% | $\le 35.0\%$ | PASS |
| **R4-G4** | `2X_FRICTION_STRESS_TOTAL_RETURN` | -3.96% | $\ge 0.0$ | FAIL |

**Conjunction Rule:** All four gates must pass simultaneously without discretionary override.
