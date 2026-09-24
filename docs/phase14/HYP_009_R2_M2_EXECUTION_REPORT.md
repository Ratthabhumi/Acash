# HYP_009 R2 M2 Execution Report (SEALED, K=1 SINGLE RUN)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_PRE_M2_RECONCILIATION_AND_LOCKED_M2_EXECUTION]
[RUN: ONE_CANONICAL_M2_EXECUTION]
[VERDICT: FAIL_CORE_EDGE_NOT_SUPPORTED]
```

- **Manifest:** `docs/phase14/manifests/HYP_009_R2_M2_RESULT.json`
- **Source HEAD:** `53f031028e186d4081ce5a47df722a08be48de95`
- **Dataset:** `DS_SPY_CORE001_HYP009_M2_ALPACA_1DAY_SIP` (`7961f19b…`)

## 1. Signal Summary

- 48 M2 month-end signals (Jan-2021 → Dec-2024): 38 LONG, 10 CASH.
- 9 state-change executions (5 BUY / 4 SELL), first 2021-01-04 (Dec-2020 LONG).
- Dec-2024 signal LONG with no transition → no pending execution, no 2025 access.
- Terminal: LONG, 231 shares (baseline).

## 2. Baseline (Net of 2 bps/side, Commission 0)

- Starting AUM 100000.00 (fresh; M1 AUM not carried) → ending **136245.1680884**
- Net total return **0.362451680884** | Sharpe **0.7310806434865794464782941709**
- Max drawdown **0.2557624443312489943856781208**
- Regulatory fees 4.44, slippage cost 190.9548676, dividends 3965.420956

## 3. Stress (10 bps/side, 2x Regulatory Fees)

- Ending **135215.777549** | Return **0.35215777549** | Sharpe 0.7170002785477880420023898889
- MDD 0.2596240811274515820595574966 | Reg fees 8.82 | Slippage 952.245247

## 4. Benchmark (M2 SPY Buy & Hold, Independent 100k Start)

- Ending **161436.045482** | Return 0.61436045482
- Max drawdown **0.2409397072449208847315742869**

## 5. Gates (Exact)

- G1 (>0): PASS | G2 (>=0.50): PASS | G3 (<=0.35): PASS
- G4 (core MDD 0.2558 < bench MDD 0.2409): **FAIL** — the M2 trend filter did
  not improve on buy-and-hold drawdown in 2021–2024.
- G5 (stress >0): PASS | G6 (derived 10/10): PASS
- Conjunction: FAIL → **FAIL_CORE_EDGE_NOT_SUPPORTED**

## 6. Post-Run Notes

- Verdict-label correction (pre-commit, zero empirical impact): the runner
  initially emitted M1's failure label; corrected to the frozen M2 label
  `FAIL_CORE_EDGE_NOT_SUPPORTED` with `classify_m2_verdict` + tests. No rerun.
- No M3 access. No rescue. Paper NOT_AUTHORIZED, live LOCKED, capital $0.00,
  NO_REAL_ORDERS=true. HYP_009 progression stops per frozen contract.
