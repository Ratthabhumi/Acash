# Phase 14 Step R1: Canonical Hypothesis Pre-Registration Record (HYP_011 / CORE-001)

```text
[STEP R1: PRE-REGISTRATION SEALED]
[RESEARCH RE-INCEPTION GATE: PASS & AUTHORIZED]
[TOKEN: AUTH_INCEPTION_HYP_011_d975fd46ad1a1b2f]
[K = 1 SINGLE SPECIFICATION — NO SEARCH]
[HISTORICAL / STRESS / QUARANTINE / PROSPECTIVE: ALL ZERO ACCESS]
[ZERO EMPIRICAL BACKTEST / RETURN / P&L COMPUTED]
[PAPER/LIVE: STRICTLY LOCKED]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/phase14/phase14_r1_hypothesis_registration_record_HYP_011.md`
- **Timestamp:** `2026-09-24T21:00:00Z`
- **Authority:** `AUTHORIZE_CORE_001_PARK_HYP_010_AND_PREREGISTER_HYP_011_R1` (+ `AGENTS.md`)
- **CORE_ID:** `CORE-001` | **HYPOTHESIS_ID:** `HYP_011` | **Mechanism:** `null`
- **Working title:** Global 80/20 Strategic Allocation Core
- **Parent:** None (de novo candidate #3; HYP_009 terminal, HYP_010 parked, neither amended)
- **Governing Gate:** `ResearchReInceptionGate` (`INCEPTION_AUTHORIZED`)
- **Inception Token ID:** `AUTH_INCEPTION_HYP_011_d975fd46ad1a1b2f`
- **Proposal SHA-256:** `d975fd46ad1a1b2ffdc1aeb51a0e88a471bc3b1509251a660d143a405ca4b83e`
- **Sealed Hypothesis SHA-256:** `7cfc74f16ef85ac222f6605c3eae0b1cf499848bb71c797efbd7fef79a570e78`
- **R1 Manifest SHA-256:** `fc81757fc333f9a62c3bf25264cf51091f4895825353313e1d8c086570b0fbab`
- **Preregistration Spec SHA-256:** `04dab8edb5b3c442094c284485eeddfc83c0b3c91e9c6db59e0f7694144fbe2e`
- **Strategy Specification Hash:** `3b2159c02d4013711523538f9ea5ea8668aa0761cc05b12c2d163a9721c35c68`
- **Provider-Contract Hash:** `fc2f1e7525d9cb69e74ac4d1464acab4b4855ee2e0e4ed72208f2591af749edc`
- **Sample-Partition Hash:** `0bf1c4fe4762037f542caf7562a10ab97a0fb23d1f0fc20b967f0830762f3a13`
- **Gate-Contract Hash:** `052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b`
  (identical to HYP_009/HYP_010 — same frozen G1–G6 operators, verified not forced)
- **Canonical Starting Git SHA:** `c70db723415da58f5769167567029454af4325b7`
- **Step R1 Verdict:** `HYP_011 = PREREGISTERED_SEALED_R1`
- **Next Step:** `REVIEW_CORE_001_HYP_011_R1_AND_AUTHORIZE_PROVIDER_AND_SPONSOR_QUALIFICATION`

---

## 1. Gate Invocation & Invariants (All PASS)

Real gate via `scripts/register_phase14_step_r1_hyp_011.py` (zero market-data
imports): identity valid/non-terminal/no-collision; K=1 cardinality; dataset
`DS_CORE001_HYP011_ACWI_AGG_SPY_ALPACA_1DAY_SIP_2016_2024` with window
2016-01-01..2024-12-31 (`ACWI_1DAY` hits no quarantine key); rationale ≥ 20
chars with horizons present (non-binding stubs); token locks $0.00/unqualified/
no-paper/no-live; zero market-data queries/signals/P&L.

## 2. Artifact Paths

Preregistration `docs/research/CORE-001-HYP-011-strategy-preregistration.md`;
sealed hypothesis `docs/phase14/hypotheses/HYP_011.json` (sole canonical home —
custom CORE format, no phase8.5 mirror, same documented deviation as HYP_009/010);
R1 manifest `docs/phase14/manifests/manifest_r1_HYP_011.json`; this record;
conformance record + manifest; registration script; HYP_010 park decision (separate).

## 3. Sealed State

- **HYP_011:** `R1_PREREGISTERED_SEALED`. HYP_010 parked non-falsified, untouched.
- R2 (provider + sponsor qualification): LOCKED pending
  `REVIEW_CORE_001_HYP_011_R1_AND_AUTHORIZE_PROVIDER_AND_SPONSOR_QUALIFICATION`.
- No HYP_011 empirical execution exists.
