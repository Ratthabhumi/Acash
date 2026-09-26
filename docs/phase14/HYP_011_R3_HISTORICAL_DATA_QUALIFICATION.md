# HYP_011 R3 Historical Data Qualification (SEALED)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_011_R3_HISTORICAL_DATASET_BUILD_AND_SINGLE_EXECUTION]
[DATASET: DS_CORE001_HYP011_ACWI_AGG_SPY_ALPACA_1DAY_SIP_2016_2024_001]
[STATE: HISTORICAL_DATASET_QUALIFIED_AND_SEALED_PERFORMANCE_REPLAYED_ONCE]
```

- **Manifest:** `docs/phase14/manifests/HYP_011_R3_HISTORICAL_DATASET.json`
- **Local dataset (gitignored):** `data/hyp_011/historical_dataset_001.json`
- **Dataset SHA-256:** `4cf20b51c2e2be2bb629ba10be7c25b34e8259bd5549575156afe433fb16c3d5`

## 1. Acquisition

- Provider `ALPACA_HISTORICAL_STOCK_BARS`, ACWI/AGG/SPY 1Day SIP,
  `2016-01-01..2024-12-31` (split + raw = 6 logical requests).
- Actual HTTP transport attempts: **6** (1 page per series, 2264 bars each).
- Expected NYSE sessions (calendar-derived): **2264**. All six series match
  exactly: missing/extra/duplicates **0**; split/raw alignment PASS per symbol.
- Actual coverage min **2016-01-04**, max **2024-12-31**.

## 2. Corporate Actions

- Dividends: SPY 36 / AGG 108 / ACWI 20 from sealed authorities (no refetch);
  counts verified; all ex-dates are evaluated sessions (164/164).
- Splits: `NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW` per symbol (full-window
  raw/split ratio constancy).
- Fee authority: SEC31 + TAF resolvable for all 9 rebalance sessions.

## 3. Forbidden Access

- Recent-stress/quarantine/prospective/HYP_007-empirical reads: **0**.
- No performance metric was computed before this seal.
