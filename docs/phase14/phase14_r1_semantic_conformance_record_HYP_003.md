# Phase 14 Step R1 Semantic Conformance Clarification Record: HYP_003

```text
[HUMAN-RATIFIED CLARIFICATION]
[NON-DESTRUCTIVE]
[HYP_003 HASH PRESERVED]
[R1 LINEAGE PRESERVED]
[NO DATA AUTHORITY]
[STEP R2 STILL LOCKED]
[OOS SEALED]
```

- **Document ID:** `docs/phase14/phase14_r1_semantic_conformance_record_HYP_003.md`
- **Subject:** Governance clarification and schema adapter binding for sealed hypothesis `HYP_003` (Opening Range Breakout on `SPY` under MEC-0013 price-only mechanics).
- **Governance Basis:** Human Decision Record `docs/phase14/mec_0013_ca1_orb_human_decision_surface.md`, Human Decision `D-PREREG-1`, Human Decision `D-EMP-1`, and explicit Human Authorization for YELLOW Remediation (2026-09-18).
- **Target Sealed Hypothesis:** `HYP_003` (stored at `docs/phase14/hypotheses/HYP_003.json` and `docs/phase8.5/hypotheses/HYP_003.json`).
- **Target R1 Manifest:** `docs/phase14/manifests/manifest_r1_HYP_003.json`.
- **Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`).
- **Authority:** Strict Fail-Closed (`AGENTS.md`). Zero empirical claims, zero market data loaded, zero backtests executed, OOS strictly sealed.

---

## 1. Context & Purpose

On 2026-09-18, Step R1 successfully registered and sealed `HYP_003` under the authority of `D-PREREG-1` and `D-EMP-1`. A comprehensive read-only semantic conformance audit was conducted prior to Step R2 data acquisition to verify whether all fields in the sealed `HYP_003` artifact strictly match the Human-ratified frozen pre-registration specification (`docs/phase14/mec_0013_price_only_preregistration.md`).

The audit classified the conformance state as **YELLOW**:
1. The 14 research-design parameters, the $K=4$ primary cell definitions, and the In-Sample/Out-of-Sample partition dates embedded within `parameter_config_json` are 100% identical byte-for-byte to the frozen pre-registration.
2. However, the outer `HypothesisSpecification` model fields (`expected_direction`, `target_horizons`, `primary_horizon`, `invalidation_criteria`) and the inception proposal's `SplitPolicy(60/20/20)` were structurally mandated by the legacy Phase 4 predictive continuous-regression schema and the `ResearchReInceptionGate` validation checks.
3. If consumed by downstream continuous OLS evaluation pipelines, these outer fields would introduce severe behavioral contradictions (e.g. falsifying short trades, enforcing fixed-horizon forward returns, and imposing unratified Rank IC hurdles).

This record establishes the **binding, non-destructive semantic resolution** of these schema adapters. It preserves all cryptographic seals, modifies zero code or sealed artifacts, and defines the unambiguous interpretation rules for downstream execution harnesses.

---

## 2. Binding Clarifications

### 2.1 Audit A — Directional Lane (`expected_direction`)
- **Top-Level Artifact Value:** `expected_direction = "LONG"`.
- **Classification:** **NON-BINDING SCHEMA COMPATIBILITY STUB**.
- **Reason:** The Pydantic model `HypothesisSpecification` and Enum `ExpectedDirection` in `src/acash/research/schema.py` natively support only `LONG`, `SHORT`, and `DISPERSION`. They lack a `SYMMETRIC` variant. `expected_direction = "LONG"` was required solely to satisfy Pydantic instantiation during gate submission.
- **Binding Directional Authority:**
  $$\text{Directional Authority} \equiv \text{parameter\_config\_json}["3\_directional\_lane"] = \text{"SYMMETRIC LONG + SHORT"}$$
  and the four primary research cells:
  1. `ORB_5M_LONG` ($\text{direction} = \text{LONG}$)
  2. `ORB_5M_SHORT` ($\text{direction} = \text{SHORT}$)
  3. `ORB_15M_LONG` ($\text{direction} = \text{LONG}$)
  4. `ORB_15M_SHORT` ($\text{direction} = \text{SHORT}$)
- **Downstream Execution Invariant:** Any downstream ORB execution harness **MUST** derive trading direction exclusively from each primary cell definition. The legacy Phase 4 continuous-regression evaluator (`src/acash/research/evaluation.py`) **MUST NOT** be used for `HYP_003`.

---

### 2.2 Audit B — Holding Horizon (`target_horizons` & `primary_horizon`)
- **Top-Level Artifact Value:** `target_horizons = [1, 390]`, `primary_horizon = 390`.
- **Classification:** **NON-BINDING SCHEMA COMPATIBILITY STUB**.
- **Reason:** `ResearchReInceptionGate` asserts that `target_horizons` is non-empty and `primary_horizon in target_horizons`. The value `390` was entered as a structural surrogate representing the length of a complete regular trading session (390 minutes).
- **Binding Holding & Exit Semantics:**
  - Entry is strictly at `Next-Bar Open` ($t+1$).
  - Protective stop is fixed at the `Opposite Opening-Range Boundary`.
  - In the absence of a stop trigger, the position is held until `15:59 ET Regular-Session Close` (EOD flatten).
  - Realized holding period is **event-driven and variable**; it is **NOT** a fixed-horizon forward-return label.
- **Downstream Execution Invariant:** Downstream evaluation must never apply fixed $H$-bar forward-return labeling ($R_{t,H}$) to simulate or evaluate `HYP_003` strategy behavior.

---

### 2.3 Audit C — Statistical Invalidation Criteria (`invalidation_criteria`)
- **Top-Level Artifact Value:**
  - `min_in_sample_rank_ic = 0.010`
  - `min_hac_t_stat = 1.50`
  - `max_feature_autocorrelation = 0.98`
  - `min_cost_adjusted_spread_ratio = 1.50`
- **Classification:** **NON-BINDING SCHEMA STUBS**.
- **Reason:** `ResearchReInceptionGate` Invariant 4 strictly enforces `min_in_sample_rank_ic > 0.0` and `min_hac_t_stat >= 1.50`. These criteria were designed for continuous OLS predictive factor regressions and were never ratified by Human Operator for discrete event-driven ORB.
- **Binding Falsification & Empirical Authority:**
  - Section 6 of `docs/phase14/mec_0013_price_only_preregistration.md` governs empirical validity exclusively: technical contract pass criteria (deterministic reproducibility, zero lookahead, 100% 390-bar completeness, zero parameter tuning, temporal partition holdout).
  - The Human-ratified pre-registration explicitly affirms that empirical outcomes may be **positive, negative, or null**, and that a null or negative result is a valid scientific finding without post-hoc redesign.
- **Downstream Execution Invariant:** Any attempt to use Rank IC, HAC $t$-statistic, feature autocorrelation, or cost-spread ratio as empirical success/failure gates for `HYP_003` is **STRICTLY UNAUTHORIZED** unless explicitly authorized by a future Human Decision amendment.

---

### 2.4 Audit D — Split Policy Terminology (`proposed_split_policy`)
- **Proposal-Time Value:** `SplitPolicy(train_pct=0.60, val_pct=0.20, oos_pct=0.20, embargo_bars=0)`.
- **Classification:** **TRANSIENT PROPOSAL METADATA ONLY**.
- **Reason:** `ResearchInceptionProposal` structurally mandates a `SplitPolicy`. Note that `SplitPolicy` does **NOT** exist in `HypothesisSpecification` or `HYP_003.json`.
- **Binding Partition Authority:**
  $$\text{In-Sample (IS)} = [2017-01-01, 2022-12-31]$$
  $$\text{Out-of-Sample (OOS)} = [2023-01-01, 2026-12-31]\quad (\text{SEALED})$$
- **Terminology Invariant:** Only the interval `2023-01-01` through `2026-12-31` may be designated as **canonical OOS**. Any internal subdivision of the `2017–2022` data window must be explicitly documented as an **IS-internal subdivision** and must never be labeled or treated as canonical OOS.

---

### 2.5 Downstream Engine Binding
- **Authorized Execution Family:** Event-driven discrete simulation engine (`EventBacktestRunner` / native ACASH event backtest engine) executing the frozen mechanics of `docs/phase14/mec_0013_price_only_preregistration.md`.
- **Prohibited Execution Family:** The legacy continuous predictive `AlphaResearchPipeline` and OLS evaluator (`src/acash/research/evaluation.py`) are **STRICTLY NOT AUTHORIZED** for `HYP_003`.
- **Data Contract:** The execution harness must consume `parameter_config_json`, `primary_cells`, and the 14 frozen parameters as its sole binding strategy definition.

---

## 3. Authority Precedence Hierarchy

To prevent future ambiguity or conflicting interpretations across automated systems or human contributors, the following order of precedence is hereby established:

```text
[Highest Priority]
1. Human-Ratified Frozen Pre-Registration Specification
   (docs/phase14/mec_0013_price_only_preregistration.md)
       │
       ▼
2. Human-Ratified Semantic Conformance Clarification Record
   (docs/phase14/phase14_r1_semantic_conformance_record_HYP_003.md)
       │
       ▼
3. Embedded Strategy Configuration in Sealed Hypothesis
   (HYP_003.json["parameter_config_json"])
       │
       ▼
4. Schema-Required Top-Level Compatibility Stubs
   (HYP_003.json["expected_direction"], ["target_horizons"], ["invalidation_criteria"])
[Lowest Priority]
```

**Conflict Resolution Rule:** In the event of any contradiction between an upper tier and a lower tier, the **higher-precedence authority strictly governs**. Under no circumstances may lower-level sealed artifacts be retroactively modified or amended to "harmonize" with higher tiers.

---

## 4. Cryptographic Hash & Lineage Preservation

All cryptographic digests and lineage bindings established during Step R1 remain strictly identical, immutable, and preserved:

| Artifact | Canonical Path | Preserved SHA-256 Digest | Status |
|---|---|---|---|
| **Sealed Hypothesis Specification** | `docs/phase14/hypotheses/HYP_003.json` | `f59010d14f466e9681325a314fd3e7ef30af43ffd69bc6cecbad1b5e6aab4ee0` | **UNCHANGED** |
| **Phase 8.5 Hypothesis Mirror** | `docs/phase8.5/hypotheses/HYP_003.json` | `f59010d14f466e9681325a314fd3e7ef30af43ffd69bc6cecbad1b5e6aab4ee0` | **UNCHANGED** |
| **R1 Registration Manifest** | `docs/phase14/manifests/manifest_r1_HYP_003.json` | `27952f476cf96f75dc47ca0eb68a4b74d1f8dc6bf2f0848d1a877740cc32b372` | **UNCHANGED** |
| **Frozen Pre-Registration Document** | `docs/phase14/mec_0013_price_only_preregistration.md` | `3c04f617b9877a85a07043e67b7554034ebd703fe823d3d2de777a7722a3150c` | **UNCHANGED** |
| **Inception Authorization Token** | `AUTH_INCEPTION_HYP_003_845fda6b9ec7dc77` | `845fda6b9ec7dc77520c690f7618e86e18484b787db6aa421340ce71e6e55d33` | **UNCHANGED** |
| **Parent Commit Lineage** | Git Commit SHA | `5ec7d8b52333c71ab89b32426e4f80bd1aea2784` | **UNCHANGED** |

---

## 5. Governance State Boundary After Ratification

This clarification record resolves schema adapter ambiguity only. It does **NOT** grant empirical execution or data acquisition authority.

- **Step R1 Status:** `COMPLETE` / `SEALED`
- **HYP_003 Status:** `SEALED` / `IMMUTABLE`
- **Semantic Conformance:** `HUMAN-RATIFIED & CLARIFIED`
- **Step R2 Status:** `STRICTLY LOCKED / NOT INVOKED`
- **Market Data Loaded:** `ZERO`
- **In-Sample Data Inspection:** `NOT STARTED`
- **Out-of-Sample (OOS) State:** `SEALED / UNREAD`
- **Backtesting / Simulation:** `LOCKED`
- **Trading Authority:** Paper `NOT AUTHORIZED`, Live `LOCKED`, Capital `$0.00`, `NO_REAL_ORDERS=true`
