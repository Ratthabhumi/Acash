# Phase 14 Step R1: Canonical Hypothesis Pre-Registration Record (HYP_010 / CORE-001)

```text
[STEP R1: PRE-REGISTRATION SEALED]
[RESEARCH RE-INCEPTION GATE: PASS & AUTHORIZED]
[TOKEN: AUTH_INCEPTION_HYP_010_baf1924f0934d395]
[K = 1 SINGLE SPECIFICATION — NO SEARCH]
[HISTORICAL / STRESS / QUARANTINE / PROSPECTIVE: ALL ZERO ACCESS]
[ZERO EMPIRICAL BACKTEST / RETURN / P&L COMPUTED]
[PAPER/LIVE: STRICTLY LOCKED]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/phase14/phase14_r1_hypothesis_registration_record_HYP_010.md`
- **Timestamp:** `2026-09-24T00:00:00Z`
- **Authority:** `AUTHORIZE_CORE_001_HYP_010_R1_PREREGISTRATION` (+ `AGENTS.md` fail-closed)
- **CORE_ID:** `CORE-001` | **HYPOTHESIS_ID:** `HYP_010` | **Mechanism:** `null`
- **Working title:** ETF-Native Global Equity Dual Momentum Core
- **Parent:** None (de novo candidate #2; HYP_009 terminal predecessor, not amended)
- **Governing Gate:** `ResearchReInceptionGate` (`INCEPTION_AUTHORIZED`)
- **Inception Token ID:** `AUTH_INCEPTION_HYP_010_baf1924f0934d395`
- **Proposal SHA-256:** `baf1924f0934d39571a249e771eff6c92cfe84f7293aa06d064a4545ecd205f3`
- **Sealed Hypothesis SHA-256:** `a32698926a8968820b81239d910a4e5db42f6b101cd09fb73c859b0675464d0b`
- **R1 Manifest SHA-256:** `fba365716f7494275537f6118ccaa70efc25629f1f1f47bfd1b4046ebee17ff0`
- **Preregistration Spec SHA-256:** `e4d873d78131974a8f7e29c5146e526615d78257abb3f51ae338b86403fda456`
- **Strategy Specification Hash:** `63ff2373c08dde547495f96bc62564ac2851933da33ca7fb074fd5575ae984e3`
- **Provider-Contract Hash:** `a91ce9ec239dfc239f8e772d5ea89d4ff474507a1c51b319849dca35b313e3a9`
- **Sample-Partition Hash:** `a9cf14955fffcf16719f8cdd36a7bf1ab81f6ff4bdbdf1c083e13c1663c66d13`
- **Gate-Contract Hash:** `052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b`
  (identical to HYP_009's — same frozen G1–G6 operators, by design)
- **Canonical Starting Git SHA:** `cd3a3f65b0cff038eeb9e90733b0fb853bcc48bf`
- **Step R1 Verdict:** `HYP_010 = PREREGISTERED_SEALED_R1`
- **Next Step:** `REVIEW_CORE_001_HYP_010_R1_AND_AUTHORIZE_PROVIDER_DATA_QUALIFICATION`

---

## 1. Gate Invocation & Invariants (All PASS)

Real `ResearchReInceptionGate.evaluate_reinception_proposal` via
`scripts/register_phase14_step_r1_hyp_010.py` (zero market-data imports):

- **Identity:** `HYP_010` matches pattern, not terminal, no prior file. PASS.
- **Anti-HARKing:** grid cardinality 1 = `planned_trial_count` 1 (K=1). PASS.
- **Data contract:** dataset `DS_ETF_CORE001_HYP010_ALPACA_1DAY_SIP_2016_2026`,
  window 2016-01-01..2026-08-15; `SPY_1DAY` hits no quarantine key. PASS.
- **Completeness:** rationale ≥ 20 chars, features declared, horizons present
  (non-binding stubs per conformance record). PASS.
- **Decoupled readiness:** token locks $0.00/unqualified/no-paper/no-live. PASS.
- **Zero access:** no market-data queries, signals, or P&L in R1. PASS.

## 2. Artifact Paths

Preregistration `docs/research/CORE-001-HYP-010-strategy-preregistration.md`;
sealed hypothesis `docs/phase14/hypotheses/HYP_010.json` (sole canonical home —
custom CORE format, no phase8.5 mirror, same documented deviation as HYP_009);
R1 manifest `docs/phase14/manifests/manifest_r1_HYP_010.json`; this record;
conformance record + manifest; registration script.

## 3. Sealed State

- **HYP_010:** `R1_PREREGISTERED_SEALED`. R2 (provider qualification):
  LOCKED pending `REVIEW_CORE_001_HYP_010_R1_AND_AUTHORIZE_PROVIDER_DATA_QUALIFICATION`.
- HYP_009 terminal evidence untouched. No HYP_010 empirical execution exists.
