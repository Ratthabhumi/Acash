# HYP_011 R3 Post-Result MDD Defect Adjudication

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_011_R3_MDD_DEFECT_ADJUDICATION_AND_CORRECTED_REPRODUCIBILITY]
[ORIGINAL_RESULT: HISTORICAL_RESULT_INVALIDATED_BY_IMPLEMENTATION_DEFECT]
[SCIENTIFIC_HYPOTHESIS_FALSIFIED: false]
[DATASET_INVALIDATED: false]
```

- **Manifest:** `docs/phase14/manifests/HYP_011_R3_POST_RESULT_MDD_DEFECT_ADJUDICATION.json`
- **Original commit:** `64c927b39c6e4efcdf642facd178742e6ddf4ca1` (preserved, immutable)
- **Original verdict:** `HISTORICAL_REPLICATION_SUPPORTED_FOR_PROSPECTIVE_SHADOW`
  (no longer canonical scientific authority)

## 1. Defect

Frozen contract requires MDD from `[100000.00, EOD_1, …, EOD_N]`. The committed
runner recomputed `max_drawdown([r.total_equity …])`; the reused function seeds
peak at `equities[0]`, so the frozen pre-trade 100000.00 initial peak was
omitted from the final metric. Discovered AFTER performance observed.

## 2. Impact Scope

- Affected metrics: baseline/stress/SPY-benchmark/ACWI-benchmark MDD.
- Potentially affected gates: G3, G4.
- Unaffected: dataset, prices, dividends, splits, fees, trades, cash flows,
  holdings, returns, Sharpe values, G1/G2/G5/G6 evidence.
- Ledger running drawdowns (seeded at 100000 correctly) are the cross-check
  authority for the corrected computation.

## 3. Corrective Path

Exactly ONE corrected reproducibility replay from the SAME sealed dataset
(`4cf20b51…`, verified before replay), no new market-data acquisition, no
science change. If the corrected run mismatches economics or reveals another
material defect: STOP with no third replay.
