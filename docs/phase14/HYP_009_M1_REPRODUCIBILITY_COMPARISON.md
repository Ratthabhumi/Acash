# HYP_009 M1 Reproducibility Comparison (EXACT)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_M1_POST_RESULT_INTEGRITY_CORRECTION_AND_REPRODUCIBILITY]
[ORIGINAL: docs/phase14/manifests/HYP_009_R2_M1_RESULT.json @ a3170aa]
[REPRODUCTION: docs/phase14/manifests/HYP_009_R2_M1_REPRODUCIBILITY_RESULT.json]
[COMPARISON: EXACT_MATCH_ALL_FROZEN_TARGETS]
```

## 1. Metric Comparison (Exact Decimal/String Equality, No Rounding)

| Metric | Original | Reproduction | Match |
|---|---|---|---|
| baseline ending_aum | 145227.3118497 | 145227.3118497 | EXACT |
| baseline net_total_return | 0.452273118497 | 0.452273118497 | EXACT |
| baseline annualized_sharpe | 0.7873848313776889894031366474 | same | EXACT |
| baseline max_drawdown | 0.2243751746642665240571654904 | same | EXACT |
| baseline terminal_shares | 383 | 383 | EXACT |
| stress ending_aum | 144262.5069729 | 144262.5069729 | EXACT |
| stress net_total_return | 0.442625069729 | 0.442625069729 | EXACT |
| stress annualized_sharpe | 0.7757119247420111210807917343 | same | EXACT |
| stress max_drawdown | 0.2281301602333229542420748959 | same | EXACT |
| benchmark ending_aum | 186210.7615481 | 186210.7615481 | EXACT |
| benchmark net_total_return | 0.862107615481 | 0.862107615481 | EXACT |
| benchmark max_drawdown | 0.3214097537014617766443093897 | same | EXACT |

## 2. Signal/Trade Structure Comparison

- Signal rows identical (51 rows byte-comparable modulo reporting fields).
- Pending terminal identical (2020-12-31 only).
- LONG months 44 / CASH months 7; 9 state-change executions (5 BUY / 4 SELL).
- Trade scientific content identical (execution_date, decision_date, side,
  quantity, fill, cash/shares before-after, notionals, SEC31/TAF).
- Reporting-only deltas (authorized): `total_friction` → `regulatory_fees_paid`
  + `execution_slippage_cost`; baseline regulatory fees 8.31, stress 16.58
  (identical economics to the original run).

## 3. Gates

G1–G6 all PASS (G6 derived from 10/10 contract-qualification flags, not
injected). Conjunction PASS.

## 4. Classification

- Reproducibility: `M1_TECHNICAL_REPRODUCIBILITY_CONFIRMED`
- Scientific verdict: `M1_SUPPORTED_FOR_LOCKED_OOS_CONTINUATION`
- State: `M1_CORRECTED_SEAL_SUPPORTED_M2_NOT_AUTHORIZED`
- M2: NOT executed, NOT authorized under this task.
