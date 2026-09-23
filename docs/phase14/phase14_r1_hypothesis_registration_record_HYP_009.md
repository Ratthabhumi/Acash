# Phase 14 Step R1: Canonical Hypothesis Pre-Registration Record (HYP_009 / CORE-001)

```text
[STEP R1: PRE-REGISTRATION SEALED]
[RESEARCH RE-INCEPTION GATE: PASS & AUTHORIZED]
[TOKEN: AUTH_INCEPTION_HYP_009_e2ee71d26cf5891c]
[K = 1 SINGLE SPECIFICATION — NO SEARCH]
[M2 LOCKED / M3 LOCKED / PROSPECTIVE LOCKED]
[STEP R2: M1 DATA QUALIFICATION LOCKED]
[ZERO EMPIRICAL BACKTEST / RETURN / P&L COMPUTED]
[PAPER/LIVE: STRICTLY LOCKED]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/phase14/phase14_r1_hypothesis_registration_record_HYP_009.md`
- **Timestamp:** `2026-09-23T22:41:00Z`
- **Authority:** `AUTHORIZE_CORE_001_HYP_009_R1_PREREGISTRATION` (+ `AGENTS.md` fail-closed)
- **CORE_ID:** `CORE-001`
- **Canonical Hypothesis ID:** `HYP_009`
- **Mechanism Lineage:** None (de novo core lineage; HYP_008 / MEC-0018 retired, not reused)
- **Parent Hypothesis:** `None`
- **Governing Gate:** `ResearchReInceptionGate` (Gate Decision: `INCEPTION_AUTHORIZED`)
- **Inception Token ID:** `AUTH_INCEPTION_HYP_009_e2ee71d26cf5891c`
- **Proposal SHA-256:** `e2ee71d26cf5891c47f8b7e9716c8778469775d2beb4f0683b811f3588741e92`
- **Sealed Hypothesis SHA-256:** `f927ccd7b2a3adec18d8097fb09eea90a7bbeebe9872c9f563811bdb6b4842fa`
- **R1 Manifest SHA-256:** `ded1528d78f92003ab538a1ade7b9e047ed7306feaac4faa3270c67df27fce7c`
- **Preregistration Spec SHA-256:** `6813f3a5870c9027801f510f61a7a17cae01ebc7706b5b94fcb3334236202177`
- **Strategy Specification Hash:** `c3892a6af4dfaf729218dbf6182f95b9a4c5862032055965c1b9129fbff359e0`
- **Provider-Contract Hash:** `1ed9892b4871a9c430b0770f6f691244661dec5257059dda9af5effb94ae55d6`
- **Sample-Partition Hash:** `063ceeb13f30dbbb1ff6610d24baf6aa5a084282a12e698b9403fa42c85a004f`
- **Gate-Contract Hash:** `052758ae6ff6ef022b11103f1f307cdcb5afd2ef506f4babaf89ca2ed9a7ea4b`
- **Canonical Starting Git SHA:** `dd8b6e2beecc13950aca9c1777f843749529af00`
- **Step R1 Verdict:** `HYP_009 = PREREGISTERED_SEALED_R1`
- **Next Step:** `AUTHORIZE_CORE_001_HYP_009_R2_M1_DATA_QUALIFICATION_AND_EXECUTION`

---

## 1. Gate Invocation & Invariant Results

Under `AUTHORIZE_CORE_001_HYP_009_R1_PREREGISTRATION`, the real
`ResearchReInceptionGate.evaluate_reinception_proposal` was invoked via
`scripts/register_phase14_step_r1_hyp_009.py` (zero market-data imports;
zero network/parquet calls).

- **Invariant 1 (Identity):** `HYP_009` matches `^HYP_[A-Z0-9_]+$`; not terminal;
  no `docs/phase8.5/hypotheses/HYP_009.json` collision. **PASS**.
- **Invariant 2 (Anti-HARKing):** grid `{"core_specification": [...]}` cardinality
  = 1; `planned_trial_count = 1` ($K = 1$). **PASS**.
- **Invariant 3 (Data contract):** dataset `DS_SPY_CORE001_ALPACA_1DAY_SIP_2016_2026`,
  window `2016-01-01..2026-08-15` declared; `SPY_1DAY` hits no permanent
  quarantine key. **PASS**.
- **Invariant 4 (Completeness):** rationale ≥ 20 chars; features declared;
  horizons `[21]`/`21` present (non-binding stubs per conformance record). **PASS**.
- **Invariant 5 (Decoupled readiness):** token hard-locks `$0.00` / unqualified /
  no-paper / no-live. **PASS**.
- **Invariant 6 (Zero access):** R1 performed zero market-data queries, zero
  signal/P&L/Sharpe/MDD computation. **PASS**.

## 2. Artifact Paths

| Artifact | Canonical Path |
|---|---|
| Preregistration Document | `docs/research/CORE-001-HYP-009-strategy-preregistration.md` |
| Sealed Hypothesis (Phase 14, sole canonical home) | `docs/phase14/hypotheses/HYP_009.json` |
| R1 Manifest | `docs/phase14/manifests/manifest_r1_HYP_009.json` |
| Registration Record | `docs/phase14/phase14_r1_hypothesis_registration_record_HYP_009.md` |
| Semantic Conformance Record | `docs/phase14/phase14_pre_r1_semantic_conformance_record_HYP_009.md` |
| Registration Script | `scripts/register_phase14_step_r1_hyp_009.py` |

Documented deviations from the HYP_005 script pattern: no phase8.5 mirror
(HYP_009 uses the custom CORE format, not a bare `HypothesisSpecification`);
tracked-files-only writes (no `data/` gitignored mirrors); `hypothesis_sha256`
is SHA-256 over sealed file bytes for the same reason.

## 3. Sealed State

- **HYP_009 State:** `R1_PREREGISTERED_SEALED` (transitioned from
  `PROPOSED_NOT_PREREGISTERED` under gate authority; scientific fields untouched).
- **All five OPEN_BEFORE_R1 items:** RESOLVED (signal construction, cost model,
  sample partitions, locked OOS boundary, prospective boundary rule).
- **M2:** `LOCKED_HISTORICAL_OOS_NOT_PRISTINE_RESEARCHER_BLIND` — no reads until
  R1 sealed + M1 dataset complete + M1 result sealed + explicit human auth.
- **M3:** `NOT_PRISTINE_OOS` — must not rescue a failed M2.
- **Quarantine / prospective:** zero-access locked at R1.
- **R2 (M1 data qualification & execution):** LOCKED pending
  `AUTHORIZE_CORE_001_HYP_009_R2_M1_DATA_QUALIFICATION_AND_EXECUTION`.
