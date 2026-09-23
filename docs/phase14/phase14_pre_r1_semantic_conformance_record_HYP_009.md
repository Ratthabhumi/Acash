# Phase 14 Pre-R1 Semantic Conformance Record: HYP_009

```text
[EXTERNAL-RESEARCH-AUTHORITY AUDIT — IMPLEMENTATION-ONLY RECORD]
[NON-DESTRUCTIVE]
[HYP_009 INCEPTION ARTIFACTS PRESERVED]
[R1 NOT OPENED]
[NO DATA AUTHORITY]
[NO BACKTEST]
```

- **Document ID:** `docs/phase14/phase14_pre_r1_semantic_conformance_record_HYP_009.md`
- **Subject:** Binding semantic classification of legacy-schema outer fields in the
  proposed hypothesis `HYP_009` (SPY Monthly 10-Month SMA Long/Cash Core, `CORE-001`).
- **Authorization:** `AUTHORIZE_CORE_001_HYP_009_SCHEMA_SEMANTIC_CONFORMANCE_PATCH`
- **Canonical HEAD at record:** `92679267cd6943103799df133748f4873e57ef07`
- **Target Hypothesis Record:** `docs/phase14/hypotheses/HYP_009.json` (UNCHANGED by this record)
- **Conformance Status:** `PASS_WITH_NON_BINDING_LEGACY_SCHEMA_ADAPTERS`

---

## 1. Context & Purpose

`HYP_009` / `CORE-001` is `PROPOSED_NOT_PREREGISTERED`. Its binding scientific
contract is frozen at proposal level in:

1. `docs/phase14/CORE_001_HYP_009_RESEARCH_INCEPTION.md`
2. `docs/phase14/manifests/CORE_001_HYP_009_RESEARCH_INCEPTION.json`
3. `parameter_config_json` inside `docs/phase14/hypotheses/HYP_009.json`

The outer `HypothesisSpecification` fields `expected_direction`,
`target_horizons`, and `primary_horizon` exist because the legacy schema
requires them. They were NOT scientifically authorized as a 21-day forecast
horizon, holding period, exit rule, or return target. This record removes that
ambiguity BEFORE formal HYP_009 R1, additively, without modifying any sealed
or inception artifact.

This is NOT a strategy correction. NOT a parameter change. NOT a scientific
amendment. It is a semantic compatibility clarification.

---

## 2. Binding Classification

| Field | Stub value (UNCHANGED) | Classification |
|---|---|---|
| `target_horizons` | `[21]` | `NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY` |
| `primary_horizon` | `21` | `NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY` |
| `expected_direction` | `LONG` | `NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY` |

### 2.1 Horizon stubs

`21` MUST NOT be interpreted as:

- required 21-session holding period;
- required 21-session forward-return prediction horizon;
- automatic exit after 21 sessions;
- rebalance every 21 sessions;
- signal lookback;
- validation target;
- acceptance threshold;
- P&L measurement interval.

The actual strategy lifecycle remains: **monthly signal evaluation** +
**persistent LONG/CASH state** + **trade only when state changes**. A LONG
state can persist across multiple months. A CASH state can persist across
multiple months. There is NO fixed holding period.

### 2.2 Direction stub

`expected_direction = LONG` MUST NOT imply:

- every observation predicts positive forward return;
- every month must be LONG;
- CASH is invalid;
- a LONG-only always-invested strategy;
- prohibition of CASH state.

Binding direction states remain `LONG` and `CASH` per the CORE-001 inception
authority.

---

## 3. Authority Precedence Hierarchy

```text
[Highest Priority]
1. CORE-001 binding inception contract
   (CORE_001_HYP_009_RESEARCH_INCEPTION.md)
       │
       ▼
2. CORE-001 inception manifest
   (manifests/CORE_001_HYP_009_RESEARCH_INCEPTION.json)
       │
       ▼
3. Embedded strategy configuration
   (HYP_009.json["parameter_config_json"])
       │
       ▼
4. This semantic-conformance clarification record
   (phase14_pre_r1_semantic_conformance_record_HYP_009.md)
       │
       ▼
5. Schema-required top-level compatibility stubs
   (HYP_009.json["expected_direction"], ["target_horizons"], ["primary_horizon"])
[Lowest Priority]
```

**Conflict Resolution Rule:** A higher tier strictly governs on any
contradiction. Lower tiers are never retroactively modified to "harmonize".

---

## 4. Reaffirmed Binding Contract (Unchanged)

- Signal cadence: `MONTHLY` (`LAST_REGULAR_TRADING_SESSION_OF_EACH_CALENDAR_MONTH`).
- Signal: `LONG` iff `signal_level > sma_10m`; equality → `CASH`.
- States: `LONG` / `CASH` only. Exposure 100% / 0%. `MAX_GROSS_LEVERAGE = 1.0`.
- No short. No volatility targeting. No stop-loss. `CASH_RETURN = 0.0`.
- Signal observable only after month-end close t; earliest execution = next
  eligible regular-session open t+1.
- `FIXED_HOLDING_PERIOD: false`. `FIXED_21_DAY_EXIT: false`.
  `FIXED_21_DAY_PREDICTION_TARGET: false`.
- `MONTHLY_SIGNAL_CADENCE: true`. `STATE_PERSISTS_UNTIL_NEXT_STATE_CHANGE: true`.

---

## 5. Governance State Boundary

This record grants NO empirical, data, or trading authority.

- **HYP_009 Status:** `PROPOSED_NOT_PREREGISTERED`
- **Semantic Conformance:** `PASS_WITH_NON_BINDING_LEGACY_SCHEMA_ADAPTERS`
- **R1 Status:** `NOT OPENED`
- **Market Data Loaded:** `ZERO`
- **Historical Signals Computed:** `ZERO`
- **Backtesting / Simulation:** `LOCKED` (not authorized, not executed)
- **HYP_007 M3:** `NOT ACCESSED`
- **Trading Authority:** Paper `NOT_AUTHORIZED`, Live `LOCKED`, Capital `$0.00`, `NO_REAL_ORDERS=true`

---

## 6. Preserved Artifacts (All UNCHANGED)

- `docs/phase14/hypotheses/HYP_009.json` (stub values `[21]` / `21` / `LONG` retained)
- `docs/phase14/CORE_001_HYP_009_RESEARCH_INCEPTION.md` + manifest
- HYP_007 sealed artifacts, failure decomposition, M3 governance
- HYP_008 historical proposal + retirement record

## 7. Next Human Action

`REVIEW_CORE_001_HYP_009_PROPOSAL_AND_AUTHORIZE_R1_PREREGISTRATION`
