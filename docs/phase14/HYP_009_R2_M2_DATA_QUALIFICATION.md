# HYP_009 R2 M2 Data Qualification (SEALED)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_PRE_M2_RECONCILIATION_AND_LOCKED_M2_EXECUTION]
[DATASET: DS_SPY_CORE001_HYP009_M2_ALPACA_1DAY_SIP]
[STATE: M2_DATASET_QUALIFIED_AND_SEALED_PERFORMANCE_REPLAYED_ONCE]
```

- **Manifest:** `docs/phase14/manifests/HYP_009_R2_M2_DATASET.json`
- **Local dataset (gitignored):** `data/hyp_009/m2_dataset.json`
- **Dataset SHA-256:** `7961f19b6fa4cc752c1dae328001ea396f7b492b53f42d3898ae6b743f37c4d1`

## 1. Acquisition

- Provider `ALPACA_HISTORICAL_STOCK_BARS`, SPY 1Day SIP, `2021-01-01..2024-12-31`.
- Actual HTTP transport attempts: **2** (1 page per adjustment).
- Expected NYSE sessions: **1005**. Split bars **1005**, raw bars **1005**;
  missing/extra/duplicates **0**; split/raw session sets identical.
- Actual coverage min **2021-01-04**, max **2024-12-31**.
- Page SHAs: split == raw (`a56d7e78…`) — expected under no-split events.

## 2. Corporate Actions

- Dividend authority SSGA manifest (`0f99ab26…`); **13** in-scope events
  (2021-03 → 2024-03 quarterly). Authority coverage ends 2024-04-30, so
  Q2–Q4 2024 have no authoritative records and enter the frozen formula as
  D = 0 (no inference performed).
- Split determination: `NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW` (ratio constant
  across M1/M2 boundary and full M2).

## 3. Signal Continuity

- TR index rebuilt over sealed M1 closes + M2 closes; all 51 sealed M1
  month-end levels reproduced exactly before M2 evaluation.
- Dec-2020 frozen state LONG injected; first M2 execution 2021-01-04.

## 4. Forbidden Access

- M2: 2 authorized transport attempts. M3/quarantine/prospective/HYP_007: **0**.
