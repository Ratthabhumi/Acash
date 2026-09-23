# HYP_008 Pre-R1 Retirement (Additive Record)

[DOCUMENT ID: docs/phase14/HYP_008_PRE_R1_RETIREMENT.md]

[AUTHORIZATION: AUTHORIZE_RETIRE_HYP_008_AND_OPEN_CORE_001_HYP_009_IMPLEMENTATION]

[CANONICAL HEAD AT RETIREMENT: 47e95def3ad98503f41ce4549986d53f65102cb5]

[RETIREMENT TYPE: ADMINISTRATIVE_PRE_R1_RESEARCH_PRIORITY_RETIREMENT]

[STATUS: RETIRED_BEFORE_PREREGISTRATION]

## 1. Purpose

This document records the additive, pre-R1 retirement of `HYP_008` / `MEC-0018`
(Volatility & Liquidity Regime-Conditioned Time-Series Trend vs. Unconditioned
Trend Baseline). The retirement is administrative: human research priority
changed to the CORE-first architecture before HYP_008 R1 preregistration.

This document does NOT modify, delete, or reinterpret the historical HYP_008
proposal artifacts. Those artifacts remain in the audit trail exactly as sealed:

- `docs/research/MEC-0018-HYP-008-proposal.md`
- `docs/phase14/HYP_008_RESEARCH_INCEPTION_REVIEW.md`

## 2. State Transition

| Field | Value |
|---|---|
| HYPOTHESIS_ID | `HYP_008` |
| MECHANISM_ID | `MEC-0018` |
| PRIOR_STATE | `PROPOSED_NOT_PREREGISTERED` |
| NEW_STATE | `RETIRED_BEFORE_PREREGISTRATION` |
| RETIREMENT_REASON | `HUMAN_RESEARCH_PRIORITY_CHANGED_TO_CORE_FIRST_ARCHITECTURE` |
| R1_OPENED | `false` |
| BACKTEST_EXECUTED | `false` |
| HISTORICAL_SIGNAL_EVALUATION | `false` |
| M3_ACCESSED | `false` |
| PAPER_AUTHORIZED | `false` |
| LIVE_AUTHORIZED | `false` |
| CAPITAL_AUTHORITY_USD | `0.00` |
| NO_REAL_ORDERS | `true` |

## 3. Explicit Non-Claims

This retirement is:

- NOT a falsification result.
- NOT an empirical rejection.
- NOT a backtest failure.
- NOT a statement about the validity of the MEC-0018 mechanism.

No R1 gate was opened for HYP_008. No historical signal evaluation, backtest,
paper session, or live order was ever executed under HYP_008. No HYP_007 M3 or
quarantine-gap data was accessed for HYP_008.

## 4. Preserved Lineage

The following remain immutable and untouched by this retirement:

- HYP_007 closure artifacts (`HYP_007_POST_R4_OPERATIONAL_CLOSURE.md` + manifest).
- HYP_007 sealed M1/M2 evidence and R4 manifests.
- HYP_007 failure-decomposition doc and manifest
  (`HYP_007_POST_R4_FAILURE_DECOMPOSITION.md` + manifest).
- HYP_008 historical proposal artifacts listed in §1.
- HYP_007 M3 (`PROSPECTIVE_ONLY`, `LOCKED_ZERO_ACCESS`).
- Quarantine boundary `[2026-08-15, 2026-09-23)` zero-access.

Canonical capital remains `$0.00` with `NO_REAL_ORDERS=true`. Paper remains
`NOT_AUTHORIZED`; live remains `LOCKED`.

## 5. Successor Lineage

The active research lineage after this retirement is `CORE-001` / `HYP_009`
(`PROPOSED_NOT_PREREGISTERED`), recorded separately. HYP_008 is not renamed,
not reused, and not promoted under any other identifier.

## 6. Next Human Action

`REVIEW_CORE_001_HYP_009_PROPOSAL_AND_AUTHORIZE_R1_PREREGISTRATION`
