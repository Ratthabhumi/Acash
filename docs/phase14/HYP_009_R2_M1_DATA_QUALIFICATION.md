# HYP_009 R2 M1 Data Qualification (SEALED)

```text
[AUTHORIZATION: AUTHORIZE_CORE_001_HYP_009_R2_M1_DATA_QUALIFICATION_AND_EXECUTION]
[DATASET: DS_SPY_CORE001_HYP009_M1_ALPACA_1DAY_SIP]
[STATE: SEALED_M1_DATASET]
[PERFORMANCE: NOT_YET_OBSERVED_AT_SEAL]
```

- **Manifest:** `docs/phase14/manifests/HYP_009_R2_M1_DATASET.json`
- **Local dataset (gitignored):** `data/hyp_009/m1_dataset.json`
- **Dataset SHA-256:** `1dc231d9eb36c8f0a2ebd0b8b4f5d20b8bca343eed406b3b11a5744fc7cc8ba7`

## 1. Acquisition

- Provider `ALPACA_HISTORICAL_STOCK_BARS`, SPY 1Day SIP, `2016-01-01..2020-12-31`.
- Two logical requests (split + raw); HTTP attempts: **2**.
- Expected NYSE sessions (canonical calendar, early closes included): **1259**.
- Split bars **1259**, raw bars **1259**; missing **0**, duplicates **0**,
  unauthorized **0**; split/raw session sets identical.
- Actual coverage min **2016-01-04** (first eligible session), max **2020-12-31**.

## 2. Corporate Actions

- Dividend authority SSGA manifest (`0f99ab26…`); **20** in-scope events
  (2016-03-18 → 2020-12-18), each with ex-date, amount, payable date.
  Note: final Dec-2020 payable date (2021-01-29) is authority metadata, not
  market data; the receivable counts in terminal equity per contract.
- Split determination: `NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW` (raw/split ratio
  constant across all 1259 sessions).

## 3. Fee Treatment Note

- Sells: SEC Section 31 (ROUND_CEILING) + FINRA TAF from canonical ACASH
  schedule authority (2016–2020 inside 2007–2024 coverage); buys: zero.
- CAT recorded **zero**: no canonical ACASH CAT fee authority exists for the
  M1 window; the frozen R1 contract includes CAT only "if effective/applicable".

## 4. Forbidden Access

- M2/M3/quarantine/prospective/HYP_007-empirical reads: **0** throughout.
- No performance metric was computed before this seal.
