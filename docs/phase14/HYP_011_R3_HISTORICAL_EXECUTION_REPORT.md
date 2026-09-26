# HYP_011 R3 Historical Execution Report (SEALED, K=1 SINGLE RUN)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_011_R3_HISTORICAL_DATASET_BUILD_AND_SINGLE_EXECUTION]
[RUN: ONE_CANONICAL_HISTORICAL_EXECUTION]
[VERDICT: HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW]
```

- **Manifest:** `docs/phase14/manifests/HYP_011_R3_HISTORICAL_RESULT.json`
- **Source HEAD:** `b2c78009dbef1bd55bb0a8d9bc89cd1d8d23a66d`
- **Dataset:** `DS_CORE001_HYP011_ACWI_AGG_SPY_ALPACA_1DAY_SIP_2016_2024_001` (`4cf20b51…`)

## 1. Rebalance / Trade Summary

- 9/9 scheduled allocation events executed (2016-01-04 + Januarys 2017–2024).
- 18 completed trades: 11 BUY (all REBALANCE_BUY) / 7 SELL (all REBALANCE_SELL).
- Terminal: ACWI 1507 sh + AGG 385 sh, cash 4473.86 (baseline).

## 2. Baseline (Net of 2 bps/side, Commission 0)

- 100000.00 → **218852.857740** | ret **1.1885285774** |
  Sharpe **0.7082199886205631037448519049** | MDD **0.2706804464703170979420276404**
- Dividends 28501.574104, reg fees 0.25, slippage 28.746364, terminal receivable 0.

## 3. Stress (10 bps/side, 2x Regulatory Fees)

- **218619.359444** | ret 1.18619359444 | Sharpe 0.7072509593375763856321580724 |
  MDD 0.2707610914922089320548722783 | reg fees 0.50 | slippage 143.30995.

## 4. Benchmarks

- SPY B&H: **317645.2207582** | ret 2.176452207582 | Sharpe 0.8672932560936021361331579227 |
  MDD **0.3185096087705842203186407916** (1 trade, divs 25641.37).
- ACWI B&H (informational, non-binding): **240741.694289** | ret 1.40741694289 |
  Sharpe 0.6966831110016731839996157771 | MDD 0.3123026836287247134564365735.

## 5. Gates (Exact)

- G1 (>0): PASS | G2 (≥0.50): PASS | G3 (≤0.35): PASS
- G4 (core MDD 0.2707 < bench MDD 0.3185): PASS
- G5 (stress >0): PASS | G6 (derived 13/13): PASS
- Conjunction: PASS → **HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW**

## 6. Notes

- Pre-result corrections disclosed: dividend filter-then-validate (pre-seal),
  fee probe narrowed to actual sell dates (pre-seal), first-day return anchored
  at 100000 (caught by test pre-seal). No post-result repair/rerun.
- No recent-stress/quarantine/prospective access. No M3. Paper NOT_AUTHORIZED,
  live LOCKED, capital $0.00, NO_REAL_ORDERS=true.
- Next (separate authorization only): prospective shadow. Recent stress is
  non-decisive and was not run.
