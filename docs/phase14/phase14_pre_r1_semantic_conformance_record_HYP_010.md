# Phase 14 Pre-R1 Semantic Conformance Record: HYP_010

```text
[EXTERNAL-RESEARCH-AUTHORITY AUDIT — IMPLEMENTATION-ONLY RECORD]
[NON-DESTRUCTIVE]
[HYP_010 INCEPTION ARTIFACTS PRESERVED]
[R1 NOT OPENED]
[NO DATA AUTHORITY]
[NO BACKTEST]
```

- **Document ID:** `docs/phase14/phase14_pre_r1_semantic_conformance_record_HYP_010.md`
- **Authorization:** `AUTHORIZE_CORE_001_HYP_010_R1_PREREGISTRATION`
- **Target Hypothesis Record:** `docs/phase14/hypotheses/HYP_010.json` (UNCHANGED by this record)
- **Conformance Status:** `PASS_WITH_NON_BINDING_LEGACY_SCHEMA_ADAPTERS`

## Binding Classification

| Field | Stub value (UNCHANGED) | Classification |
|---|---|---|
| `target_horizons` | `[21]` | `NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY` |
| `primary_horizon` | `21` | `NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY` |
| `expected_direction` | `LONG` | `NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY` |

`21` MUST NOT be interpreted as a holding period, prediction horizon, exit
rule, rebalance cadence, signal lookback, validation target, or P&L interval.
The strategy lifecycle is: monthly signal evaluation + persistent target-asset
holding + trade only on target change. `expected_direction = LONG` MUST NOT
imply always-invested equity or prohibit the AGG defensive state.

## Authority Precedence

1. CORE-001 HYP_010 binding inception contract (inception md)
2. Inception manifest
3. `HYP_010.json["parameter_config_json"]`
4. This conformance record
5. Schema-required top-level compatibility stubs (lowest; never govern on conflict)

## Binding Contract Reaffirmed (Unchanged)

Monthly dual momentum (M12, absolute SPY-vs-BIL gate with AGG on equality,
relative SPY-vs-VEU with SPY on equality), 13 month-end warmup, next-open
execution, 100%/whole-share holdings, leverage ≤ 1.0, no short/vol-targeting,
`FIXED_HOLDING_PERIOD: false`, cash 0.0.

## Governance Boundary

HYP_010 `PROPOSED_NOT_PREREGISTERED`. R1 NOT opened. Market data ZERO.
Backtesting LOCKED. Paper NOT_AUTHORIZED, live LOCKED, capital $0.00,
`NO_REAL_ORDERS=true`.
