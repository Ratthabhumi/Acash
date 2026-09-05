# ACASH Phase 18 — Strategy Research & Tournament Pipeline
## Master Research Architecture, Governance Specification & Adversarial Audit

> **Document ID:** `ACASH-SPEC-PHASE18-TOURNAMENT-v1.1`  
> **Status:** PROPOSED ARCHITECTURE & GOVERNANCE SPECIFICATION — HUMAN APPROVAL PENDING (Phase 18 Rev 1.1)  
> **Parent Governance:** `docs/ROADMAP.md` (v3.4.0), `AGENTS.md`, ADR-023 (`docs/architecture/strategy_admission_standard.md`)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Evidence > Belief, Single Canonical Authority)  
> **Date:** 2026-09-06  
> **Version:** 1.1.0 (Auditor Remediation & Epistemic Hardening)  

---

> [!IMPORTANT]
> **STRICT GOVERNANCE BOUNDARY & CAPITAL RESTRICTIONS:**
> - **THIS SPECIFICATION IS A DESIGN, ARCHITECTURAL, AND GOVERNANCE DOCUMENT ONLY.**
> - **THIS SPECIFICATION DOES NOT AUTHORIZE CODE IMPLEMENTATION.**
> - **PHASE 18 IMPLEMENTATION IS STRICTLY LOCKED / NOT AUTHORIZED.**
> - **THIS SPECIFICATION DOES NOT GRANT LIVE TRADING OR BROKER PERMISSIONS.**
> - **LIVE CAPITAL AUTHORITY REMAINS HARD-LOCKED AT $0.00.**
> - **LIVE ORDER EMISSION AUTHORITY REMAINS STRICTLY 0.**
> - **LIVE BROKER CONNECTION REMAINS STRICTLY DISCONNECTED.**
> - **ZERO MUTATION TO `src/` OR `tests/`.**
> - **PHASE 13 STEP 5 UNATTENDED SOAK TEST (PID 41844) REMAINS ACTIVE AND UNTOUCHED.**

---

## 1. Executive Summary & Epistemic Foundations

Phase 18 establishes the **Strategy Research & Tournament Pipeline** for ACASH. It functions as the governed scientific laboratory where strategy candidates—originating either from human quantitative researchers or from Phase 14 AI hypothesis proposals—are registered, executed, benchmarked, ranked, and systematically stressed under controlled, reproducible experiment conditions.

### 1.1 The Core Research Objective
The fundamental goal of Phase 18 is to solve the **Discovery-to-Validation Bottleneck** without compromising statistical or economic integrity:
1. Provide a high-throughput, reproducible tournament harness that can evaluate dozens of strategy variants and parameter spaces concurrently.
2. Fairly benchmark every candidate against non-trivial transparent baselines (Equal Weight, Inverse Volatility, Cash/NOWHERE, and declared cohort-appropriate baselines).
3. Systematically capture **Negative Knowledge** (failed, overfit, or fragile models) rather than discarding them.
4. Bound and record **Search Intensity Contributions ($\Delta K$)** so that multiple testing can be canonically corrected in Phase 6.

### 1.2 The Sovereign Authority Invariant
A strategy winning a Phase 18 tournament confers **zero** statistical certification, **zero** economic qualification, **zero** admission status, and **zero** capital authority:

$$\boxed{\text{Tournament Winner} \not\equiv \text{Statistical Validity (Phase 6)} \not\equiv \text{Economic Qual (Phase 8.5)} \not\equiv \text{Admission (Phase 17)} \not\equiv \text{Capital Allocation}}$$

- **Phase 18 is an Exploratory Tournament Harness:** Relative ranking identifies candidates worthy of formal validation; it does *not* prove that the winner possesses genuine predictive edge.
- **Winner's Curse Awareness:** In any tournament of noisy strategies, the top-ranked candidate is statistically guaranteed to have received positive sample noise (luck). Phase 18 explicitly treats tournament rank as a biased selection metric that must be deflated and purged upstream.

---

## 2. Canonical Authority Hierarchy & Upstream/Downstream Flow

Phase 18 sits strictly downstream of research hypothesis formulation and strictly upstream of statistical validation:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PHASE 14: AI RESEARCH LAYER                            │
│                 (Unvalidated Hypothesis Proposals)                          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Pre-Registered Hypotheses
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PHASE 4: ALPHA ENGINE CONTRACT                         │
│            (HypothesisSpecification, Falsification Criteria)                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Formal Specifications
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 18: STRATEGY RESEARCH & TOURNAMENT                     │
│  ├── Research Candidate Registry                                            │
│  ├── Experiment Manifest Engine (Declared-Environment Deterministic Sealing) │
│  ├── Point-in-Time Universe & Feature Matrix (Dual-Temporal PIT)            │
│  ├── Two-Tier Execution (Tier-1 Vectorized Screening ──► Tier-2 Event-Driven)│
│  ├── Cohort-Declared Baseline Benchmarking (Cash, EW, InvVol, Cohort-Spec)  │
│  ├── Tournament Brackets, Cohorts & Relative Scoring                        │
│  ├── Negative Knowledge Ledger (Preserved Failures & Overfit Runs)          │
│  └── Trial Candidate Contribution (Emits ΔK Events to Phase 6)              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Candidate Falsification Records & ΔK
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 6: STATISTICAL VALIDATION ENGINE                      │
│      (Canonical Authority: SearchTrialLedger K, CPCV, DSR, PBO, FWER)       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ ValidationReport & evidence_digest
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 8.5: ALPHA ECONOMIC QUALIFICATION                     │
│         (Canonical Authority: AlphaQualificationDossier, Net Alpha)         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Sealed Economic Dossier
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 11: FORWARD MONITORING & REALITY GAP                  │
│       (Canonical Authority: ForwardHealthStateMachine, Drag Attribution)     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ ForwardHealthState & Telemetry
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 17: STRATEGY ADMISSION STANDARD                       │
│             (Canonical Authority: Gates 0–10 Sovereign Review)              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Cross-Phase Authority Demarcation Matrix

| Canonical Domain | Owning Authority | Phase 18 Interaction Boundary | Strict Prohibition in Phase 18 |
| :--- | :--- | :--- | :--- |
| **Hypothesis Formulation** | Phase 4 / Phase 14 | Ingests pre-registered `HypothesisSpecification`. | Phase 18 cannot alter hypothesis falsification criteria post-run. |
| **Simulation Mechanics** | Phase 5 Substrate | Ingests event-driven backtesting execution engine. | Phase 18 cannot bypass the double-entry accounting ledger. |
| **Statistical Validation** | **Phase 6 (Sole Authority)** | Emits candidate trial events ($\Delta K$). Consumes validation receipts. | **Phase 18 CANNOT compute DSR, MinTRL, PBO, or claim statistical pass.** |
| **Search Intensity / K** | **Phase 6 (Sole Authority)** | Emits raw trial candidate counts to `SearchTrialLedger`. | **Phase 18 CANNOT interpret or compute effective K.** |
| **Economic Qualification**| **Phase 8.5 (Sole Authority)**| Submits candidate for Net Alpha qualification. | **Phase 18 CANNOT certify economic edge.** |
| **Runtime Monitoring** | **Phase 11 (Sole Authority)**| Provides baseline expectations for drift detection. | **Phase 18 CANNOT emit or modify `ForwardHealthState`.** |
| **Strategy Admission** | **Phase 17 (Sole Authority)**| Submits tournament winners as candidates for Gate 0. | **Phase 18 CANNOT admit strategies to catalog.** |
| **Capital Allocation** | **Phase 21 / Phase 13 Gate B**| Out of scope. Hard-locked at `$0.00`. | **Phase 18 contains zero capital allocation methods.** |

---

## 3. Phase 18 Architectural Subsystems

Phase 18 is composed of seven decoupled sovereign subsystems:

```
                                  PHASE 18 ARCHITECTURE
                                            │
       ┌────────────────────┬───────────────┴───────────────┬──────────────────┐
       ▼                    ▼                               ▼                  ▼
1. CANDIDATE REGISTRY  2. MANIFEST ENGINE             3. PIT SUBSTRATE    4. EXECUTION HARNESS
  (Specs & Lineage)      (Environment Sealing)          (Zero Lookahead)   (Tier-1 / Tier-2)
                                                                               │
       ┌───────────────────────────────────────────────────────────────────────┘
       ▼
5. TOURNAMENT ENGINE ──► 6. SCORING & BENCHMARKING ──► 7. NEGATIVE KNOWLEDGE LEDGER
  (Cohorts & Brackets)     (Relative Heuristic)             (Failed Trials & ΔK Events)
```

### 3.1 Subsystem 1: Research Candidate Registry (`ResearchCandidateRegistry`)
- **Responsibility:** Maintains immutable registration of all strategy models, feature specifications, and parameter variants entering the research environment.
- **Candidate Identity Formulation:**
  $$\text{candidate\_id} = \text{CAND-}\{\text{family}\}\text{-}\{\text{mechanism}\}\text{-}\{\text{version}\}\text{-}\{\text{config\_sha256}[:8]\}$$
- **Mandatory Registration Contract:**
  - Must bind to a pre-existing Phase 4 `hypothesis_id`.
  - Declared parameter space with finite discrete boundaries (continuous unrestricted grids are forbidden).
  - Explicit declaration of source: `HUMAN_RESEARCH`, `PHASE14_AI_PROPOSAL`, or `SYSTEMATIC_MUTATION`.

### 3.2 Subsystem 2: Experiment Manifest Engine (`ExperimentManifestEngine`)
- **Responsibility:** Enforces deterministic reproducibility across all tournament evaluations under declared environments.
- **Epistemic Standard: Environment-Sealed Determinism:**
  Rather than making unverified claims of universal bitwise reproducibility across disparate platforms, Phase 18 enforces **deterministic reproducibility under a declared execution environment**.
- **Declared Execution Environment Specification (`DeclaredExecutionEnvironment`):**
  1. Python runtime and micro-version (e.g. `CPython 3.12.x`)
  2. OS and platform architecture (e.g. `Windows-11-AMD64`)
  3. Dependency lockfile digest (cryptographic hash of `uv.lock`)
  4. Core numerical library versions (`numpy`, `scipy`, `pandas`, `vectorbt`)
  5. Phase 5 simulation engine version digest
  6. CPU floating-point / BLAS runtime characteristics where material
  7. Canonical pseudo-random seed
  8. Git commit SHA of the research engine
  9. Dataset and universe SHA-256 digests
- **Manifest Cryptographic Digest:**
  $$\text{experiment\_digest} = \text{SHA256}(\text{dataset\_sha256} + \text{universe\_hash} + \text{candidate\_manifests} + \text{env\_digest} + \text{seed})$$
- **Invariance Guarantee:** Re-executing an experiment manifest on an identical dataset within the declared execution environment must produce identical trade logs, drawdowns, and rank orderings.

### 3.3 Subsystem 3: Point-in-Time Universe Substrate (`PointInTimeUniverseSubstrate`)
- **Responsibility:** Enforces strict temporal data partitioning preventing information leakage across competing tournament candidates.
- **Dual-Temporal Filtering:**
  $$T_{\text{event\_utc}} \le T_{\text{decision\_utc}} \quad\land\quad T_{\text{knowledge\_utc}} \le T_{\text{as\_of\_utc}}$$
- **Shared-Universe Leakage Guard:** Competing strategies in a tournament bracket are evaluated sequentially or in isolated sandboxes. A candidate strategy cannot observe or condition on the decisions, fills, or positions of rival strategies in the tournament.

### 3.4 Subsystem 4: Two-Tier Execution Harness (`TwoTierExecutionHarness`)
To balance computational throughput with microstructural realism, Phase 18 implements a strict two-tier execution policy:

```
[Candidate Batch] ──► TIER 1: Vectorized Screening ──► Falsified? ──► YES ──► [Negative Knowledge Ledger]
                                  │
                                  ▼ NO (Survives Screening)
                      TIER 2: Event-Driven Simulation ──► Falsified? ──► YES ──► [Negative Knowledge Ledger]
                                  │
                                  ▼ NO (Survives Simulation)
                      [Tournament Bracket & Benchmarking]
```

#### Strict Separation of Tier Roles:
1. **Tier 1 (Vectorized Screening):**
   - **Role:** Fast exploratory parameter filtering using vectorized array operations (`NumPy`, `pandas`, `vectorbt`).
   - **Epistemic Classification:** *Exploratory screening evidence only.*
   - **Multiple Testing Contribution:** Tier-1 trials count as candidate search attempts and **MAY contribute to the search ledger** to preserve multiple-testing accounting.
   - **Absolute Restriction:** **Tier-1 results MUST NOT become a ValidationReport or enter Phase 6 statistical validation directly.**
2. **Tier 2 (Event-Driven Simulation):**
   - **Role:** Full microstructural execution via canonical Phase 5 `BacktestSubstrate` (order lifecycle, queue priority, bid-ask spread crossing, transaction friction waterfalls).
   - **Epistemic Classification:** *High-fidelity simulation evidence.*
   - **Requirement:** Only candidates surviving Tier-2 simulation are eligible for tournament cohort benchmarking and subsequent Phase 6 submission.

### 3.5 Subsystem 5: Tournament Cohort & Bracket Manager (`TournamentCohortManager`)
- **Responsibility:** Groups candidates into fair, apples-to-apples evaluation brackets based on asset class, timeframe, and market mechanism.
- **Cohort Categorization:**
  - FX Intraday Forecasting Cohort
  - Crypto High-Frequency Microstructure Cohort
  - Equity Factor / Reversion Cohort
  - Liquidity Provision / Spread Capture Cohort
- **Rule:** Strategies with fundamentally different holding horizons or risk models (e.g. 5-minute scalping vs 30-day carry) must never be evaluated in the same relative ranking bracket.

### 3.6 Subsystem 6: Scoring & Relative Benchmarking Engine (`TournamentScoringEngine`)
- **Responsibility:** Measures candidate performance relative to transparent passive baselines.
- **Cohort-Dependent Baseline Specification:**
  Every tournament bracket must evaluate the candidate against declared, relevant baseline actors:
  1. `BASELINE-0 (CASH)`: Zero return, zero risk ($0.00 PnL$). Mandatory for all cohorts.
  2. `BASELINE-1 (EQUAL_WEIGHT)`: Passive buy-and-hold across the cohort asset universe. Mandatory for asset-selection cohorts.
  3. `BASELINE-2 (INVERSE_VOLATILITY)`: Risk-parity passive allocation. Mandatory for multi-asset cohorts.
  4. `BASELINE-3 (COHORT_SPECIFIC_BENCHMARK)`: Declared in `ExperimentManifest`. For continuous intraday markets with centralized or reliable volume, Session VWAP Reversion is standard; for 24/7 OTC or multi-week swing cohorts, an appropriate transparent baseline (e.g. Rolling Moving Average or Naive Carry) must be declared and justified.
- **Epistemic Status of Tournament Scores:**
  Tournament scores are strictly internal research ranking heuristics. They do not constitute empirical proof of alpha or replace Phase 6 validation.

### 3.7 Subsystem 7: Negative Knowledge Ledger & Search Intensity Emission (`NegativeKnowledgeLedger`)
- **Responsibility:** Immutably records every candidate evaluation, parameter trial, and failed experiment.
- **Anti-Survivorship Principle:** Failed strategies are never deleted. They are permanently recorded with their failure classification:
  - `FAILED_TIER1_SCREENING`: Negative gross edge in vectorized pass.
  - `FAILED_COST_WATERFALL`: Positive gross edge, but destroyed by spread/slippage.
  - `FAILED_STRESS_PERTURBATION`: Margin failure under canonical stress.
  - `FAILED_PARAMETER_CLIFF`: Edge collapses under $\pm 10\%$ neighborhood perturbation.
  - `FAILED_BENCHMARK_ALPHA`: Underperformed simple Equal-Weight baseline.
- **Single Authority for Search Intensity ($K$):**
  $$\boxed{\text{Phase 18 emits raw trial candidate events; Phase 6 exclusively determines SearchTrialLedger state and } K \text{ semantics.}}$$
  - Phase 18 tracks the raw count of evaluated parameter sets and strategy variants ($\Delta K_{\text{trials}}$).
  - It emits these counts as structured event contributions to Phase 6.
  - Phase 18 does **NOT** calculate effective $K$, does **NOT** compute multiple-testing penalty thresholds, and does **NOT** maintain a competing trial ledger.

---

## 4. Adversarial Self-Audit (12 Audit Dimensions — Remediated)

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      PHASE 18 ADVERSARIAL AUDIT MATRIX (REV 1.1)                 │
├──────────────────────────────────────┬───────────────────────────────────────────┤
│ Audit Dimension                      │ Enforced Fail-Closed Remediation          │
├──────────────────────────────────────┼───────────────────────────────────────────┤
│ 1. Authority Boundaries              │ PASS — Phase 18 emits raw trial events;   │
│                                      │ Phase 6 maintains sole statistical state. │
│ 2. Selection / Tournament Bias       │ PASS — Winner's curse discount is tagged  │
│                                      │ strictly as research ranking heuristic.   │
│ 3. Multiple Testing & Search K       │ PASS — Full trial contributions emitted;  │
│                                      │ Phase 6 exclusively governs K semantics.  │
│ 4. Lookahead & Data Leakage          │ PASS — Isolated candidate execution; zero │
│                                      │ cross-candidate feature interaction.      │
│ 5. Survivorship Bias Mitigation      │ PASS — Append-only registry; zero pruning │
│                                      │ of failed runs; cohorts report failure %. │
│ 6. Reproducibility & Determinism     │ PASS — Manifest-sealed determinism under  │
│                                      │ declared environment (DeclaredExecutionEnv)│
│ 7. Candidate Lineage Tracking        │ PASS — Cryptographic chain from Phase 4   │
│                                      │ hypothesis to experiment run record.      │
│ 8. Negative Knowledge & Leakage      │ PASS — Negative data stored for audit; no │
│                                      │ unrecorded algorithmic cross-leakage.     │
│ 9. Ranking Semantics Discipline      │ PASS — Relative rank is ordinal research  │
│                                      │ heuristic; overlapping CIs = tie flag.    │
│ 10. Host Compute & Resource Gov      │ PASS — Concurrency <= Cores-2; low process│
│                                      │ priority; 2.0 GB RSS fail-closed watchdog.│
│ 11. Phase 14 AI Epistemic Firewall   │ PASS — AI outputs strictly unvalidated    │
│                                      │ proposals; zero autonomous self-admission.│
│ 12. Phase 17 Admission Boundary      │ PASS — Tournament winner still has zero   │
│                                      │ admission status; must pass Gates 0–10.   │
└──────────────────────────────────────┴───────────────────────────────────────────┘
```

### Audit Dimension 1: Authority Boundary & Separation of Concerns
- **Adversarial Vector:** *Does Phase 18 act as a secondary statistical or qualification authority?*
- **Remediation in Rev 1.1:**
  1. Phase 18 is strictly prohibited from calculating DSR, MinTRL, PBO, or emitting `ValidationReport`.
  2. Phase 18 emits raw trial candidate events; Phase 6 exclusively determines `SearchTrialLedger` state and multiple-testing penalization.
  3. Phase 18 outputs are labeled exclusively as `TournamentCandidateEvaluationRecord`.

### Audit Dimension 2: Selection Bias & Winner's Curse
- **Adversarial Vector:** *Does the WinnerCurseDiscountFactor masquerade as a canonical statistical correction?*
- **Remediation in Rev 1.1:**
  1. `WinnerCurseDiscountFactor` is explicitly classified as an **internal research ranking heuristic**.
  2. It possesses **zero statistical authority** and is strictly prohibited from flowing into or substituting for Phase 6 DSR / PBO.
  3. The raw, undiscounted data along with trial count contributions are transmitted to Phase 6 so that canonical statistical adjustments can occur under Phase 6 authority.

### Audit Dimension 3: Multiple Testing & Search Intensity Accounting ($K$)
- **Adversarial Vector:** *Can Phase 18 conceal failed Tier-1 trials or redefine how K is counted?*
- **Remediation in Rev 1.1:**
  1. Every Tier-1 parameter permutation and Tier-2 simulation run is recorded as an evaluated candidate trial.
  2. Phase 18 transmits these trial events to Phase 6 without attempting to compress, deflate, or alter their multiple-testing interpretation.
  3. Phase 6 retains sole sovereign authority over $K$ semantics and ledger validation.

### Audit Dimension 4: Data Leakage & Lookahead Prevention
- **Adversarial Vector:** *Can cross-sectional normalization across tournament candidates leak information from future bars or rival strategies?*
- **Remediation:**
  1. Candidate simulation runs execute in isolated sandboxes with frozen read-only access to historical feature Parquet partitions.
  2. Ranking is computed exclusively post-hoc on sealed performance arrays.
  3. Dual-temporal point-in-time boundaries ($T_{\text{event}} \le T_{\text{decision}} \land T_{\text{knowledge}} \le T_{\text{as\_of}}$) are strictly enforced.

### Audit Dimension 5: Survivorship Bias Mitigation
- **Adversarial Vector:** *Are failed tournament candidates discarded, distorting historical performance records?*
- **Remediation:**
  1. Append-only `ResearchCandidateRegistry`: zero deletion policy.
  2. Negative runs are cataloged permanently with specific failure signatures.
  3. Cohort evaluation summaries report overall failure rates alongside finalist metrics.

### Audit Dimension 6: Reproducibility & Environment Sealing
- **Adversarial Vector:** *Does Phase 18 claim unverified bitwise reproducibility across disparate hardware and software builds?*
- **Remediation in Rev 1.1:**
  1. Replaced "Bitwise-reproducible experiment sealing" with **manifest-sealed deterministic reproducibility under a declared execution environment**.
  2. Defined `DeclaredExecutionEnvironment` schema capturing Python version, OS architecture, dependency lockfile digest (`uv.lock`), numerical library builds, simulation engine version, and random seeds.
  3. Acknowledged that execution across differing CPU microarchitectures or BLAS implementations may introduce floating-point discrepancies; determinism is guaranteed within the declared environment digest.

### Audit Dimension 7: Candidate Provenance & Lineage Tracking
- **Adversarial Vector:** *Can an unanchored candidate strategy enter the tournament without hypothesis lineage?*
- **Remediation:**
  1. Mandatory lineage chain: $\text{Phase 4 Hypothesis} \to \text{Phase 18 ExperimentManifest} \to \text{Phase 18 RunRecord}$.
  2. Missing lineage fails closed immediately; unanchored strategies cannot be registered.

### Audit Dimension 8: Negative Knowledge & Path-Dependency Leakage
- **Adversarial Vector:** *Does negative knowledge from Experiment A automatically prune search spaces in Experiment B, creating hidden selection leakage?*
- **Remediation in Rev 1.1:**
  1. Negative knowledge serves strictly for **institutional memory, post-hoc audit, and search intensity accounting**.
  2. Automatic algorithmic pruning across independent hypotheses is strictly forbidden.
  3. If a researcher chooses to constrain a parameter space based on prior negative knowledge, this constraint must be explicitly declared in the pre-registered Phase 4 `HypothesisSpecification` and accounted for in Phase 6 search history.

### Audit Dimension 9: Ranking Semantics Discipline
- **Adversarial Vector:** *Is tournament rank #1 treated as empirical proof of superiority over rank #2?*
- **Remediation:**
  1. Ranking is strictly an ordinal research convenience, not proof of alpha.
  2. Pairwise HAC confidence intervals are calculated; overlapping intervals are explicitly flagged as statistical ties.

### Audit Dimension 10: Compute & Resource Governance
- **Adversarial Vector:** *Can high-throughput tournaments starve background processes (e.g. Phase 13 soak) or exhaust host RAM?*
- **Remediation:**
  1. Concurrency limit: $\le \text{LogicalCores} - 2$.
  2. Process priority: `BELOW_NORMAL_PRIORITY_CLASS` (preventing CPU starvation of PID 41844).
  3. Memory ceiling: 2.0 GB RSS per worker with fail-closed watchdogs.

### Audit Dimension 11: Phase 14 AI Epistemic Firewall
- **Adversarial Vector:** *Can generative AI self-promote candidates through Phase 18 directly to the catalog?*
- **Remediation:**
  1. AI outputs remain strictly classified as `UNVALIDATED_PROPOSAL`.
  2. AI agents cannot modify tournament scoring weights or baseline definitions.
  3. Advancing a candidate from Phase 18 to Phase 6 requires human quantitative authorization.

### Audit Dimension 12: Phase 17 Admission Boundary
- **Adversarial Vector:** *Can winning a tournament bypass Phase 17 admission gates?*
- **Remediation:**
  1. Tournament survival merely qualifies a candidate for Phase 6 submission.
  2. The candidate must subsequently pass Phase 8.5 (Economic Qualification), Phase 11 (Forward Monitoring), and Phase 17 (Gates 0–10).

---

## 5. Threshold Provenance & Classification Taxonomy

All numerical thresholds and evaluation parameters in Phase 18 are classified in accordance with `AGENTS.md` standards:

| Parameter / Threshold | Subsystem | Classification | Owning Authority / Provenance | Epistemic Description |
| :--- | :--- | :--- | :--- | :--- |
| $\text{Seed} = \text{uint32}(\text{SHA256}[:4])$ | Manifest Engine | **Class A: Canonical ACASH Invariant** | Phase 1/5 Deterministic Seed Standard | Exact environment-sealed reproducibility |
| $K_{\text{Phase6}} \equiv K_{\text{prior}} + \Delta K$ | Negative Ledger | **Class A: Canonical ACASH Invariant** | Phase 6 Multiple Testing Contract | Strict fail-closed search intensity accounting |
| $\text{Capital Allocation} = \$0.00$ | System-Wide | **Class A: Canonical ACASH Invariant** | ADR-023 / Project-Wide Governance | Hard-locked system invariant |
| $\text{Tier-1 Parameter Sweep} \pm 20\%$ | Two-Tier Harness | **Class B: Governance-Defined Threshold** | Phase 18 Research Governance | Standard exploratory screening boundary |
| $\text{Worker Concurrency} \le \text{Cores} - 2$ | Resource Substrate | **Class B: Governance-Defined Threshold** | Phase 18 Host Protection Policy | CPU starvation prevention policy |
| $\text{Max Worker Memory} \le 2.0\text{ GB}$ | Resource Substrate | **Class B: Governance-Defined Threshold** | Phase 18 Host Protection Policy | Memory thrashing prevention policy |
| $\text{Minimum Cohort Size} \ge 5$ | Cohort Manager | **Class C: Research Heuristic** | Quantitative Tournament Best Practice | Minimum cross-sectional diversity heuristic |
| $\text{Tie-Breaking Alpha Band } p > 0.05$ | Scoring Engine | **Class C: Research Heuristic** | Econometric Hypothesis Testing Standard | Pairwise statistical tie detection heuristic |
| Winner's Curse Heuristic $\sqrt{\frac{2 \ln M}{T}}$| Scoring Engine | **Class C: Research Heuristic** | Extreme Value Theory (López de Prado 2018) | Heuristic ranking selection discount |
| 4 Declared Baseline Hurdles | Benchmarking Engine | **Class B: Governance-Defined Threshold** | Phase 18 Benchmarking Standard | Mandatory relative hurdle baseline suite |

---

## 6. Implementation Constraints & Acceptance Criteria (For Future Implementation Phase)

When Phase 18 implementation is formally authorized by the Human Auditor following the completion of Phase 13, the implementation must adhere to the following strict constraints:

### 6.1 Architecture & Code Structure
1. **Module Location:** All Phase 18 code must reside exclusively in `src/acash/research/tournament/`.
2. **Zero Modification to Prior Sealed Modules:** No changes to `src/acash/core/`, `src/acash/data/`, `src/acash/validation/`, `src/acash/execution/`, `src/acash/monitoring/`, or `src/acash/runtime/`.
3. **Data Transfer Objects:** All candidate definitions, experiment manifests, tournament receipts, and ledger events must be immutable Pydantic v2 models (`frozen=True`) with strict Decimal arithmetic for financial metrics.
4. **Typing & Linting:** 100% clean under `mypy --strict`.

### 6.2 Acceptance Criteria for Implementation Authorization
- [ ] Unit test suite verifying exact deterministic reproducibility of tournament manifests within a declared execution environment.
- [ ] Unit test verifying that every parameter trial correctly logs candidate trial events for Phase 6 search ledger ingestion.
- [ ] Integration test verifying that a tournament winner cannot bypass Phase 6 or Phase 8.5 to gain catalog admission.
- [ ] Adversarial test demonstrating that injecting lookahead bias into one candidate does not leak to rival candidates.
- [ ] Host safety test verifying worker concurrency respects `LogicalCores - 2` ceiling and does not impact concurrent background tasks.

---

## 7. Authoritative Academic & Quantitative Grounding

1. **López de Prado, M. (2018):** *Advances in Financial Machine Learning.* John Wiley & Sons. (Formulates the mathematics of selection bias, combinatorial cross-validation, and the false discovery rate in strategy tournaments).
2. **Harvey, C. R., & Liu, Y. (2015):** *Backtesting.* The Journal of Portfolio Management. (Establishes haircut Sharpe ratios and adjustments for multiple testing in quantitative research).
3. **Bailey, D. H., & López de Prado, M. (2014):** *The Deflated Sharpe Ratio: Correcting for Selection Bias, Non-Normality and Sample Length.* Journal of Portfolio Management. (Establishes the canonical derivation of expected maximum Sharpe under search intensity $K$).
4. **Carhart, M. M. (1997):** *On Persistence in Mutual Fund Performance.* The Journal of Finance. (Demonstrates that top-performing funds in tournament rankings frequently suffer from mean reversion and cost decay).
5. **White, H. (2000):** *A Reality Check for Data Snooping.* Econometrica. (Proves that the distribution of the maximum performance statistic over a universe of evaluated models must be adjusted using bootstrap methods).

---

## 8. Governance Sign-Off & Specification Provenance

```text
================================================================================
ACASH STRATEGY RESEARCH & TOURNAMENT PIPELINE (PHASE 18) — SPECIFICATION PROVENANCE
================================================================================
Specification Document: docs/phase18/phase18_master_research_tournament_architecture.md
Document Revision     : Phase 18 Rev 1.1 (v1.1.0)
Current Status        : PROPOSED / HUMAN APPROVAL PENDING
Parent Governance     : docs/ROADMAP.md (v3.4.0), AGENTS.md, ADR-023
Adversarial Audit     : COMPLETE (12 / 12 Dimensions PASS — Remediated)

Remediation Highlights (Rev 1.1):
  [x] K Semantics: Phase 18 emits raw trial events; Phase 6 exclusively determines K semantics.
  [x] Tier-1 Clarification: Exploratory screening only; contributes to trials; cannot become ValidationReport.
  [x] Reproducibility: Toned down from 'bitwise' to 'manifest-sealed under declared environment'.
  [x] Winner's Curse: Tagged strictly as internal research ranking heuristic (zero statistical authority).
  [x] Baseline-3: Caveated as cohort-dependent; declared and justified in ExperimentManifest.
  [x] Negative Knowledge: Preserved for audit/lineage; forbidden from unrecorded cross-hypothesis pruning.

Authority Invariants:
  [x] Phase 6 Statistical Authority Preserved (Strict Consumer Only; trial events emitted)
  [x] Phase 8.5 Economic Qualification Authority Preserved (Strict Consumer Only)
  [x] Phase 11 Forward Monitoring Authority Preserved (Strict Consumer Only)
  [x] Phase 17 Strategy Admission Authority Preserved (Gate 0–10 Mandatory)
  [x] Phase 14 AI Proposal Firewall Preserved (AI != Evidence, AI != Authority)
  [x] Live Capital Authority Hard-Locked at $0.00
  [x] Live Orders Emitted: 0 | Broker Wire: DISCONNECTED

Implementation Status:
  [x] Implementation is STRICTLY LOCKED / NOT AUTHORIZED
  [x] Zero Runtime Code Committed
  [x] Active Soak Test (PID 41844) Untouched & Continuous
================================================================================
```
