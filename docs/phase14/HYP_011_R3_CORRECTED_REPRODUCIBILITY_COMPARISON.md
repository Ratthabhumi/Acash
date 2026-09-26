# HYP_011 R3 Corrected Reproducibility Comparison (EXACT)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_011_R3_MDD_DEFECT_ADJUDICATION_AND_CORRECTED_REPRODUCIBILITY]
[ORIGINAL: docs/phase14/manifests/HYP_011_R3_HISTORICAL_RESULT.json @ 64c927b]
[CORRECTED: docs/phase14/manifests/HYP_011_R3_CORRECTED_REPRODUCIBILITY_RESULT.json]
[NETWORK_REQUESTS: 0]
```

## 1. Ledger Equality (Unchanged Accounting)

All 7 recomputed ledger SHAs match original sealed pins exactly: signal
schedule, baseline/stress execution, baseline/stress/SPY/ACWI equity. No
economic drift.

## 2. MDD Comparison (The Corrected Defect)

| Path | Original (peak from EOD_1) | Corrected ([100000, EOD…]) | Delta |
|---|---|---|---|
| baseline | 0.2706804464703170979420276404 | same | 0 |
| stress | 0.2707610914922089320548722783 | same | 0 |
| SPY bench | 0.3185096087705842203186407916 | same | 0 |
| ACWI bench | 0.3123026836287247134564365735 | same | 0 |

Each corrected value cross-checked equal to max ledger running drawdown.
Assessment: the defect was real in code, but numerically immaterial for this
run — every maximum drawdown trough already postdates the portfolio's first
exceedance of 100000, so the initial peak never binds. G3/G4 outcomes stand
as computed, now on the contract-correct basis.

## 3. Economics Unchanged

Ending AUMs, returns, Sharpes (all four paths): identical. Trades, holdings,
cash flows, dividends, fees: identical (ledger SHAs prove it).

## 4. Gates / Verdict

G1–G6 all PASS (G6 derived 13/13). Conjunction PASS.
- Reproducibility: `M1_TECHNICAL_REPRODUCIBILITY_CONFIRMED` analogue —
  `CORRECTED_REPRODUCIBILITY_CONFIRMED` (recorded in manifest).
- Scientific verdict: `HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW`.

## 5. Locks

Zero network. No dataset rebuild. M2/M3/quarantine/prospective/HYP_007 reads:
0. Paper NOT_AUTHORIZED, live LOCKED, capital $0.00, NO_REAL_ORDERS=true.
No third replay under this authorization.
