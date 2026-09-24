# Phase 14 Pre-R1 Semantic Conformance Record: HYP_011

```text
[EXTERNAL-RESEARCH-AUTHORITY AUDIT — IMPLEMENTATION-ONLY RECORD]
[NON-DESTRUCTIVE]
[HYP_011 INCEPTION ARTIFACTS PRESERVED]
[R1 NOT OPENED]
[NO DATA AUTHORITY]
[NO BACKTEST]
```

- **Document ID:** `docs/phase14/phase14_pre_r1_semantic_conformance_record_HYP_011.md`
- **Authorization:** `AUTHORIZE_CORE_001_PARK_HYP_010_AND_PREREGISTER_HYP_011_R1`
- **Target Hypothesis Record:** `docs/phase14/hypotheses/HYP_011.json` (UNCHANGED by this record)
- **Conformance Status:** `PASS_WITH_NON_BINDING_LEGACY_SCHEMA_ADAPTERS`

## Binding Classification

| Field | Stub value (UNCHANGED) | Classification |
|---|---|---|
| `target_horizons` | `[21]` | `NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY` |
| `primary_horizon` | `21` | `NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY` |
| `expected_direction` | `LONG` | `NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY` |

`21` MUST NOT be interpreted as a holding period, prediction horizon, exit
rule, rebalance cadence, or P&L interval. HYP_011 has no signal horizon at
all: static 80/20 allocation with annual calendar rebalancing. `LONG` MUST NOT
imply always-invested equity or prohibit the 20% bond allocation.

## Authority Precedence

1. CORE-001 HYP_011 binding inception contract (inception md)
2. Inception manifest
3. `HYP_011.json["parameter_config_json"]`
4. This conformance record
5. Schema-required top-level compatibility stubs (lowest; never govern on conflict)

## Binding Contract Reaffirmed (Unchanged)

Static 80/20 ACWI/AGG, annual first-open-of-year rebalance with deterministic
whole-share solver, leverage ≤ 1.0, no short/vol-targeting, cash 0.0.

## Governance Boundary

HYP_011 `PROPOSED_NOT_PREREGISTERED`. R1 NOT opened. Market data ZERO.
Backtesting LOCKED. Paper NOT_AUTHORIZED, live LOCKED, capital $0.00,
`NO_REAL_ORDERS=true`.
