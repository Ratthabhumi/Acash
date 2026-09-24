# HYP_009 R2 M1 Execution Report (SEALED, K=1 SINGLE RUN)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_R2_M1_DATA_QUALIFICATION_AND_EXECUTION]
[RUN: ONE_CANONICAL_M1_EXECUTION]
[VERDICT: M1_SUPPORTED_FOR_LOCKED_OOS_CONTINUATION]
```

- **Manifest:** `docs/phase14/manifests/HYP_009_R2_M1_RESULT.json`
- **Source HEAD:** `290311ec2d6dc4cd64cfe4a8704f1f4a18744efe`
- **Dataset:** `DS_SPY_CORE001_HYP009_M1_ALPACA_1DAY_SIP` (`1dc231d9…`)

## 1. Signal Summary (Exact, Unrounded Elsewhere)

- 51 month-end signals (Oct-2016 → Dec-2020): 44 LONG months, 7 CASH months.
- 50 runnable; 1 pending: Dec-2020 signal (`PENDING_NEXT_PARTITION_EXECUTION_NOT_EXECUTED`,
  no January-2021 access).
- First execution 2016-11-01 (next open after Oct-2016 signal, derived from
  calendar, not hard-coded). Last execution 2020-06-01.
- 9 completed state-change trades: 5 BUY, 4 SELL. Terminal: LONG, 383 shares.

## 2. Baseline (Net of 2 bps/side, Commission 0)

- Starting AUM: 100000.00 | Ending AUM: 145227.3118497
- Net total return: 0.452273118497 | Annualized Sharpe: 0.7873848313776889894031366474
- Max drawdown: 0.2243751746642665240571654904 | Total friction: 8.31
- Dividends received: 8566.5443137 | Terminal receivable: 605.14

## 3. Stress (10 bps/side, 2x Regulatory Fees)

- Ending AUM: 144262.5069729 | Net total return: 0.442625069729
- Sharpe: 0.7757119247420111210807917343 | MDD: 0.2281301602333229542420748959
- Total friction: 16.58

## 4. Benchmark (SPY Buy & Hold, Same Economics)

- Ending AUM: 186210.7615481 | Total return: 0.862107615481
- Max drawdown: 0.3214097537014617766443093897
- CORE-001 is NOT required to beat buy-and-hold return; G4 tests drawdown only.

## 5. Gates (Exact, No Pre-Rounding)

- G1 (>0): PASS | G2 (>=0.50): PASS | G3 (<=0.35): PASS
- G4 (core MDD 0.2244 < bench MDD 0.3214): PASS
- G5 (stress >0): PASS | G6 (no material contract failure): PASS
- Conjunction: PASS → **M1_SUPPORTED_FOR_LOCKED_OOS_CONTINUATION**

## 6. Serialization Note (Disclosed Post-Result Finding)

After the run, file-byte hashes mismatched pinned manifest hashes because
`Path.write_text` on Windows emits CRLF while hashes were computed over LF
bytes. Assessment: serialization-only defect (whitespace); zero numeric impact
(all metrics/gates/ledgers content-identical). Remedy: normalized sealed files
to LF bytes (no recomputation, no rerun); all 7 pinned hashes now match file
bytes exactly; runner fixed to write `newline="\n"`. A regression test pins
CR-free sealed files. No M2 executed. No trading authorized
(paper NOT_AUTHORIZED, live LOCKED, capital $0.00, NO_REAL_ORDERS=true).
