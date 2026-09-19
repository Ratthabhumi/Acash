# Phase 14 Step R1: Canonical Hypothesis Pre-Registration Record (HYP_004)

```text
[STEP R1: PRE-REGISTRATION SEALED]
[RESEARCH RE-INCEPTION GATE: PASS & AUTHORIZED]
[TOKEN: AUTH_INCEPTION_HYP_004_148ac7aa2e59f25d]
[OOS 2023-2026: STRICTLY SEALED / UNREAD]
[STEP R2: DATASET CONSTRUCTION LOCKED]
[ZERO EMPIRICAL BACKTEST / RETURN COMPUTED]
[PAPER/LIVE: STRICTLY LOCKED]
```

- **Document ID:** `docs/phase14/phase14_r1_hypothesis_registration_record_HYP_004.md`
- **Timestamp:** `2026-09-19T05:00:00+00:00`
- **Authority:** `AGENTS.md` (Zero Unverified Claims, Single Canonical Authority, Strict Fail-Closed)
- **Canonical Hypothesis Ordinal:** `4` (`HYP_004`)
- **Canonical Hypothesis ID:** `HYP_004`
- **Mechanism Lineage:** `MEC-0014A` (Market Intraday Momentum: Gao Baseline Predictive-Relation Econometric Replication on SPY)
- **Parent Hypothesis:** `None` (De novo research; not a rescue modification of HYP_003)
- **Governing Gate:** `ResearchReInceptionGate` (Gate Decision: `INCEPTION_AUTHORIZED`)
- **Inception Token ID:** `AUTH_INCEPTION_HYP_004_148ac7aa2e59f25d`
- **Proposal SHA-256:** `148ac7aa2e59f25dadd1173250254bef42037525646fe1b7f39284d256ad13d7`
- **Sealed Hypothesis SHA-256:** `fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d`
- **R1 Manifest SHA-256:** `eacd98963f51b759b43ba8565aecbc43432f93acd9386b3c20bec8184712bd5b`
- **Preregistration Spec SHA-256:** `1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce`
- **Canonical Parent Git SHA:** `ccd42a50be935cacb22b7681d5b806c449495057`
- **Step R1 Verdict:** `PASS & SEALED`
- **Next Step:** `STEP R2 (DATASET CONSTRUCTION) — STRICTLY LOCKED PENDING SEPARATE HUMAN AUTHORIZATION`

---

## 1. Executive Summary & Governance Authority

Under the explicit human authorization for Phase 14 Step R1, `ResearchReInceptionGate` was invoked to evaluate the formal statistical replication proposal for `HYP_004` (MEC-0014A).

Prior to gate invocation:
1. **Governance Hardening:** `HYP_003` was added to `TERMINAL_HYPOTHESIS_REGISTRY` in `src/acash/research/reinception.py`, ensuring programmatic anti-resurrection protection independent of file existence.
2. **Preregistration Integrity:** `docs/research/MEC-0014A-statistical-preregistration-draft.md` was validated (SHA-256: `1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce`) confirming zero remaining open blockers.
3. **Cardinal Equality ($K=1$):** Parameter search grid contains exactly 1 cell (`{"primary_specification": ["GAO_R1_TO_R13_BASELINE"]}`), matching `planned_trial_count = 1`.

### Invariant Verification Results:
- **Invariant 1 (Identity & Immutability):** `HYP_004` matches pattern `^HYP_[A-Z0-9_]+$`. Not in `TERMINAL_HYPOTHESIS_REGISTRY`. No collision with existing sealed files. **VERIFIED PASS**.
- **Invariant 2 (Anti-HARKing Cardinal Equality):** Search grid cardinality = 1. Declared `planned_trial_count = 1`. Equality strictly satisfied ($K = 1$). **VERIFIED PASS**.
- **Invariant 3 (Declarative Data Contract & Quarantine):** Instrument is `SPY`. Proposed data window is `2017-01-01T00:00:00+00:00` to `2022-12-31T23:59:59+00:00` (In-Sample replication window only). Out-of-Sample window (`2023–2026`) is strictly sealed. **VERIFIED PASS**.
- **Invariant 4 (Pre-Registration Completeness):** Structural economic rationale is 242 characters ($\ge 20$). Explicit semantic feature dependencies declared. Minimal deterministic schema compatibility stubs defined. **VERIFIED PASS**.
- **Invariant 5 (Decoupled Readiness):** Inception Authorization Token hard-locks `capital_authority_usd == $0.00`, `is_strategy_qualified == False`, `is_paper_authorized == False`, `is_live_authorized == False`. **VERIFIED PASS**.
- **Invariant 6 (Zero Data / Execution Access):** Step R1 performed zero market data queries, zero CSV/Parquet reads, zero network calls, and zero return/regression calculations. **VERIFIED PASS**.

---

## 2. Artifact Paths & Exact Hashes

### 2.1 Canonical Git-Tracked Research Artifacts

These artifacts are committed to canonical Git and provide the sovereign versioned authority:

| Artifact Description | Canonical Git-Tracked Path | SHA-256 Digest |
| :--- | :--- | :--- |
| **Preregistration Document** | `docs/research/MEC-0014A-statistical-preregistration-draft.md` | `1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce` |
| **Sealed Hypothesis (Phase 8.5 Mirror)** | `docs/phase8.5/hypotheses/HYP_004.json` | `fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d` |
| **Sealed Hypothesis (Phase 14 Mirror)** | `docs/phase14/hypotheses/HYP_004.json` | `fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d` |
| **R1 Manifest (Phase 14 Mirror)** | `docs/phase14/manifests/manifest_r1_HYP_004.json` | `eacd98963f51b759b43ba8565aecbc43432f93acd9386b3c20bec8184712bd5b` |
| **Semantic Conformance Record** | `docs/phase14/phase14_r1_semantic_conformance_record_HYP_004.md` | Tracked markdown |

*Note: The two canonical Git-tracked hypothesis mirrors (`docs/phase8.5/` and `docs/phase14/`) are 100% byte-identical.*

### 2.2 Local Runtime / Gitignored Mirrors

The following files are generated locally by the R1 registration script for local execution harness compatibility. Because `/data/` is excluded by `.gitignore`, these paths are **not** tracked in Git and do not constitute independent Git repository authorities; their contents are strictly reproducible from the tracked R1 registration process:

| Local Runtime Description | Local Filesystem Path (Gitignored) | SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- |
| **Local Hypothesis Mirror** | `data/manifests/research/hypotheses/HYP_004.json` | `fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d` | Byte-identical to tracked mirrors |
| **Local R1 Manifest Mirror** | `data/manifests/research/manifest_r1_HYP_004.json` | `eacd98963f51b759b43ba8565aecbc43432f93acd9386b3c20bec8184712bd5b` | Byte-identical to tracked manifest |

---

## 3. Scope & Operational Locks

- **Empirical Execution:** STRICTLY NOT AUTHORIZED under Step R1.
- **Dataset Construction:** LOCKED pending explicit human authorization for Step R2.
- **Market Data Reads:** ZERO operations performed.
- **Out-of-Sample Window ($\ge 2023-01-01$):** STRICTLY SEALED.
- **Trading Authorization:** Paper trading = `LOCKED`, Live trading = `LOCKED`, Canonical capital = `$0.00`, `NO_REAL_ORDERS = true`.
- **HYP_003 Integrity:** Sealed HYP_003 artifacts unmodified; HYP_003 permanently falsified and enrolled in `TERMINAL_HYPOTHESIS_REGISTRY`.
