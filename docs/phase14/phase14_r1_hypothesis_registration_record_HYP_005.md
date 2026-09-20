# Phase 14 Step R1: Canonical Hypothesis Pre-Registration Record (HYP_005)

```text
[STEP R1: PRE-REGISTRATION SEALED]
[RESEARCH RE-INCEPTION GATE: PASS & AUTHORIZED]
[TOKEN: AUTH_INCEPTION_HYP_005_8b61aa2dcf7cc4f0]
[M2 STRESS & M3 PROSPECTIVE: STRICTLY SEALED / LOCKED]
[STEP R2: DATASET CONSTRUCTION LOCKED]
[ZERO EMPIRICAL BACKTEST / RETURN / P&L COMPUTED]
[PAPER/LIVE: STRICTLY LOCKED]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/phase14/phase14_r1_hypothesis_registration_record_HYP_005.md`
- **Timestamp:** `2026-09-21T05:00:00+00:00`
- **Authority:** `AGENTS.md` (Zero Unverified Claims, Single Canonical Authority, Strict Fail-Closed)
- **Canonical Hypothesis Ordinal:** `5` (`HYP_005`)
- **Canonical Hypothesis ID:** `HYP_005`
- **Mechanism Lineage:** `MEC-0015` (SPY Noise-Area Intraday Momentum Net-Profitability Replication)
- **Parent Hypothesis:** `None` (De novo research; not an unprincipled rescue modification of HYP_003 or HYP_004)
- **Governing Gate:** `ResearchReInceptionGate` (Gate Decision: `INCEPTION_AUTHORIZED`)
- **Inception Token ID:** `AUTH_INCEPTION_HYP_005_8b61aa2dcf7cc4f0`
- **Proposal SHA-256:** `8b61aa2dcf7cc4f034a6bd4d3ac85f3e9eaf64943b3fa37bffb00f4ab5006634`
- **Sealed Hypothesis SHA-256:** `ec4679751fa1c4d82e2a3a871ca6dc2f7d6bfbc1e1691518ab6261059e14603f`
- **R1 Manifest SHA-256:** `f0322a049b6990ed2131f28cb33f0f2fd768a982be2e75815d9f999091422e61`
- **Preregistration Spec SHA-256:** `5036c765cea2f36b95352f5bc0311580c375e8552ec1590c228690b2543cff9e`
- **Canonical Starting Git SHA:** `4ec8e0fcaee73ea8cfbaf71f5d338ef813e1e33d`
- **Human Authorization:** `AUTHORIZE_HYP_005_INCEPTION_AND_R1_REGISTRATION`
- **Step R1 Verdict:** `HYP_005 = CREATED_AND_SEALED_R1`
- **Next Step:** `STEP_R2_MEC0015_DATASET_CONSTRUCTION_LOCKED_PENDING_SEPARATE_HUMAN_AUTHORIZATION`

---

## 1. Executive Summary & Governance Authority

Under the explicit human authorization `AUTHORIZE_HYP_005_INCEPTION_AND_R1_REGISTRATION`, `ResearchReInceptionGate` was formally invoked to evaluate the strategy replication proposal for `HYP_005` (MEC-0015).

Prior to gate invocation:
1. **Pre-Inception Blocker Verification:** All 11 upstream MEC-0015 contracts and manifests were audited, completed, and verified to have zero open blockers.
2. **Upstream Authority Hashes Pinned:** Cryptographic digests of all 11 upstream files were computed and immutably bound into the proposal, parameter configuration, preregistration document, and R1 manifest.
3. **Cardinal Equality ($K = 1$):** Parameter search grid contains exactly 1 cell (`{"primary_specification": ["MEC_0015_NOISE_AREA_INTRADAY_MOMENTUM_BASELINE"]}`), strictly matching `planned_trial_count = 1`.
4. **Terminal Protection:** Programmatic anti-resurrection rules in `ResearchReInceptionGate` protect terminal hypotheses `HYP_003` and `HYP_004`.

### Invariant Verification Results:
- **Invariant 1 (Identity & Immutability):** `HYP_005` matches pattern `^HYP_[A-Z0-9_]+$`. Not in `TERMINAL_HYPOTHESIS_REGISTRY`. No collision with existing sealed files on disk. **VERIFIED PASS**.
- **Invariant 2 (Anti-HARKing Cardinal Equality):** Search grid cardinality = 1. Declared `planned_trial_count = 1`. Equality strictly satisfied ($K = 1$). **VERIFIED PASS**.
- **Invariant 3 (Declarative Data Contract & Quarantine):** Instrument is `SPY`. Proposed data window is `2007-05-01T00:00:00+00:00` to `2024-04-30T23:59:59+00:00` (M1 publication-exposed replication sample). M2 post-publication stress sample is locked for R4 only. M3 prospective sample is strictly sealed. **VERIFIED PASS**.
- **Invariant 4 (Pre-Registration Completeness):** Structural economic rationale is 221 characters ($\ge 20$). Explicit semantic feature dependencies declared. Minimal deterministic schema compatibility stubs defined. **VERIFIED PASS**.
- **Invariant 5 (Decoupled Readiness):** Inception Authorization Token hard-locks `capital_authority_usd == $0.00`, `is_strategy_qualified == False`, `is_paper_authorized == False`, `is_live_authorized == False`. **VERIFIED PASS**.
- **Invariant 6 (Zero Data / Execution Access):** Step R1 performed zero market data queries, zero CSV/Parquet reads, zero network calls, zero signal generation, and zero return/P&L calculations. **VERIFIED PASS**.

---

## 2. Artifact Paths & Exact Hashes

### 2.1 Canonical Git-Tracked Research Artifacts

| Artifact Description | Canonical Git-Tracked Path | SHA-256 Digest |
| :--- | :--- | :--- |
| **Preregistration Document** | `docs/research/MEC-0015-HYP-005-strategy-preregistration.md` | `5036c765cea2f36b95352f5bc0311580c375e8552ec1590c228690b2543cff9e` |
| **Sealed Hypothesis (Phase 8.5 Mirror)** | `docs/phase8.5/hypotheses/HYP_005.json` | `ec4679751fa1c4d82e2a3a871ca6dc2f7d6bfbc1e1691518ab6261059e14603f` |
| **Sealed Hypothesis (Phase 14 Mirror)** | `docs/phase14/hypotheses/HYP_005.json` | `ec4679751fa1c4d82e2a3a871ca6dc2f7d6bfbc1e1691518ab6261059e14603f` |
| **R1 Manifest (Phase 14 Mirror)** | `docs/phase14/manifests/manifest_r1_HYP_005.json` | `f0322a049b6990ed2131f28cb33f0f2fd768a982be2e75815d9f999091422e61` |
| **Registration Record** | `docs/phase14/phase14_r1_hypothesis_registration_record_HYP_005.md` | Tracked markdown |
| **Semantic Conformance Record** | `docs/phase14/phase14_r1_semantic_conformance_record_HYP_005.md` | Tracked markdown |

*Note: The canonical Git-tracked hypothesis mirrors (`docs/phase8.5/` and `docs/phase14/`) are 100% byte-identical.*

### 2.2 Local Runtime / Gitignored Mirrors

| Local Runtime Description | Local Filesystem Path (Gitignored) | SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- |
| **Local Hypothesis Mirror** | `data/manifests/research/hypotheses/HYP_005.json` | `ec4679751fa1c4d82e2a3a871ca6dc2f7d6bfbc1e1691518ab6261059e14603f` | Byte-identical to tracked mirrors |
| **Local R1 Manifest Mirror** | `data/manifests/research/manifest_r1_HYP_005.json` | `f0322a049b6990ed2131f28cb33f0f2fd768a982be2e75815d9f999091422e61` | Byte-identical to tracked manifest |

---

## 3. Scope & Operational Locks

- **HYP_005 State:** `CREATED_AND_SEALED_R1`.
- **Empirical Execution:** STRICTLY NOT AUTHORIZED under Step R1.
- **Dataset Construction (R2):** LOCKED pending explicit separate human authorization.
- **Historical Replication (R3):** LOCKED pending R2 dataset build.
- **Stress Evaluation (R4):** LOCKED.
- **Market Data Reads During R1:** ZERO operations performed.
- **Capital Allocation:** `$0.00` strictly enforced by `InceptionAuthorizationToken`.
- **Trading Authorization:** `NO_REAL_ORDERS = true`. Paper trading = `NOT AUTHORIZED`. Live trading = `LOCKED`.
- **Terminal Hypothesis Protection:** `HYP_003` and `HYP_004` remain permanently closed and enrolled in `TERMINAL_HYPOTHESIS_REGISTRY`.
