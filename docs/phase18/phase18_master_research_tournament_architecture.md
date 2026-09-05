# ACASH Phase 18 — Strategy Research & Tournament Pipeline
## Master Research Architecture, Governance Specification & Adversarial Audit

> **Document ID:** `ACASH-SPEC-PHASE18-TOURNAMENT-v1.0`  
> **Status:** PROPOSED ARCHITECTURE & GOVERNANCE SPECIFICATION — HUMAN APPROVAL PENDING (Phase 18 Rev 1.0)  
> **Parent Governance:** `docs/ROADMAP.md` (v3.4.0), `AGENTS.md`, ADR-023 (`docs/architecture/strategy_admission_standard.md`)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Evidence > Belief, Single Canonical Authority)  
> **Date:** 2026-09-06  
> **Version:** 1.0.0  

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
2. Fairly benchmark every candidate against non-trivial transparent baselines (Equal Weight, Inverse Volatility, Cash/NOWHERE, and Microstructure baselines).
3. Systematically capture **Negative Knowledge** (failed, overfit, or fragile models) rather than discarding them.
4. Bound and record **Search Intensity ($K$)** so that multiple testing can be canonically corrected in Phase 6.

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
│  ├── Experiment Manifest Engine (SHA-256 Bitwise Sealing)                   │
│  ├── Point-in-Time Universe & Feature Matrix (Dual-Temporal PIT)            │
│  ├── Two-Tier Execution (Tier-1 Vectorized Screening ──► Tier-2 Event-Driven)│
│  ├── Transparent Baseline Benchmarking (Cash, EW, InvVol, VWAP)             │
│  ├── Tournament Brackets, Cohorts & Relative Scoring                        │
│  ├── Negative Knowledge Ledger (Preserved Failures & Overfit Runs)          │
│  └── Search Intensity Emission (Trial Count Delta ΔK)                       │
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
| **Statistical Validation** | **Phase 6 (Sole Authority)** | Emits candidate trials ($\Delta K$) and evaluation paths. Consumes validation receipts. | **Phase 18 CANNOT compute DSR, MinTRL, PBO, or claim statistical pass.** |
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
  (Specs & Lineage)      (Cryptographic Identity)       (Zero Lookahead)   (Tier-1 / Tier-2)
                                                                               │
       ┌───────────────────────────────────────────────────────────────────────┘
       ▼
5. TOURNAMENT ENGINE ──► 6. SCORING & BENCHMARKING ──► 7. NEGATIVE KNOWLEDGE LEDGER
  (Cohorts & Brackets)     (Relative Heuristic)             (Failed Trials & ΔK Emission)
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
- **Responsibility:** Enforces bitwise reproducibility across all tournament evaluations.
- **Manifest Cryptographic Digest:**
  $$\text{experiment\_digest} = \text{SHA256}(\text{dataset\_sha256} + \text{universe\_hash} + \text{candidate\_manifests} + \text{code\_git\_sha} + \text{config\_digest})$$
- **Invariance Guarantee:** Re-executing an experiment manifest on an identical dataset must produce mathematically identical trade logs, drawdowns, and rank orderings ($|\text{Discrepancy}| = 0$).

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
                                  ▼ NO (Passed Prescreen)
                      TIER 2: Event-Driven Simulation ──► Falsified? ──► YES ──► [Negative Knowledge Ledger]
                                  │
                                  ▼ NO (Passed Reality Check)
                      [Tournament Bracket & Benchmarking]
```

1. **Tier 1: Vectorized Screening (`Tier1ScreeningEngine`):**
   - Implemented via array operations (`NumPy`, `pandas`, `vectorbt`).
   - Purpose: Rapid screening across broad parameter grids ($\pm 20\%$) to discard obviously non-viable candidates.
   - **Epistemic Firewall:** Tier-1 results are strictly exploratory heuristics. **NO candidate may advance to Phase 6 statistical validation based solely on Tier-1 screening.**
2. **Tier 2: Event-Driven Simulation (`Tier2SimulationEngine`):**
   - Implemented using the canonical Phase 5 event-driven simulation substrate (`BacktestSubstrate`).
   - Purpose: High-fidelity order lifecycle (`CREATED` $\to$ `SUBMITTED` $\to$ `ACCEPTED` $\to$ `FILLED`), tick-level queue priority, bid-ask spread crossing, and transaction friction waterfalls.
   - Requirement: Only candidates surviving Tier-2 simulation are eligible for tournament cohort inclusion and subsequent Phase 6 submission.

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
- **Mandatory Baseline Benchmark Suite:**
  Every tournament bracket must evaluate the candidate against four mandatory baseline actors:
  1. `BASELINE-0 (CASH)`: Zero return, zero risk ($0.00 PnL$).
  2. `BASELINE-1 (EQUAL_WEIGHT)`: Passive buy-and-hold across the cohort asset universe.
  3. `BASELINE-2 (INVERSE_VOLATILITY)`: Risk-parity passive allocation.
  4. `BASELINE-3 (VWAP_REVERSION)`: Transparent, parameter-free microstructure baseline.
- **Relative Edge Requirement:**
  A candidate strategy must outperform `BASELINE-1` and `BASELINE-2` net of costs to achieve a positive relative tournament score.
- **Scoring Formulation:**
  Multi-dimensional metric vector: Information Ratio vs Baseline, Calmar Ratio, Tail Gain-to-Pain Ratio, Maximum Adverse Excursion, and Friction Decay Slope.

### 3.7 Subsystem 7: Negative Knowledge Ledger & Search Intensity Emitter (`NegativeKnowledgeLedger`)
- **Responsibility:** Immutably records every candidate evaluation, parameter trial, and failed experiment.
- **Anti-Survivorship Principle:** Failed strategies are never deleted. They are permanently recorded with their failure classification:
  - `FAILED_TIER1_SCREENING`: Negative gross edge in vectorized pass.
  - `FAILED_COST_WATERFALL`: Positive gross edge, but destroyed by spread/slippage.
  - `FAILED_STRESS_PERTURBATION`: Margin failure under canonical stress.
  - `FAILED_PARAMETER_CLIFF`: Edge collapses under $\pm 10\%$ neighborhood perturbation.
  - `FAILED_BENCHMARK_ALPHA`: Underperformed simple Equal-Weight baseline.
- **Trial Count Emission ($\Delta K$):**
  Phase 18 records the exact count of all evaluated candidates and emits $\Delta K$ directly to the canonical Phase 6 `SearchTrialLedger`.

---

## 4. Adversarial Self-Audit (12 Audit Dimensions)

To uphold the strict standards of `AGENTS.md`, this specification undergoes a comprehensive 12-dimension adversarial audit before presentation for human review.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 18 ADVERSARIAL AUDIT MATRIX                        │
│ 1. Authority Boundaries        5. Survivorship Bias    9. Ranking Semantics │
│ 2. Selection / Tournament Bias 6. Reproducibility     10. Compute Governance│
│ 3. Multiple Testing & K        7. Candidate Lineage   11. AI Firewall       │
│ 4. Lookahead & Data Leakage    8. Negative Knowledge  12. Phase 17 Boundary │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Audit Dimension 1: Authority Boundary & Separation of Concerns
- **Adversarial Vector:** *Does Phase 18 inadvertently replicate Phase 6 validation, Phase 8.5 qualification, Phase 11 monitoring, or Phase 17 admission?*
- **Audit Findings:** In early draft concepts, tournaments generated "composite scores" that could be mistaken for qualification certificates.
- **Enforced Remediation:**
  1. Phase 18 is strictly prohibited from calculating DSR, MinTRL, PBO, or emitting `ValidationReport`.
  2. Phase 18 is strictly prohibited from generating `AlphaQualificationDossier` or asserting Net Alpha legitimacy.
  3. Phase 18 is strictly prohibited from granting catalog admission (`StrategyAdmissionStatus` remains exclusively owned by Phase 17).
  4. Phase 18 outputs are labeled exclusively as `TournamentCandidateEvaluationRecord`.

### Audit Dimension 2: Selection Bias & Tournament Bias (Winner's Curse)
- **Adversarial Vector:** *Does ranking 100 noisy strategies and selecting the winner produce severe selection bias and inflated expectations?*
- **Audit Findings:** Yes. In a tournament of $M$ candidates with true Sharpe $= 0$, the maximum sample Sharpe follows the Gumbel extreme-value distribution:
  $$\mathbb{E}[\max_{i=1\dots M} \widehat{SR}_i] \approx \sqrt{2 \ln M} + \frac{\gamma_E}{\sqrt{2 \ln M}} > 0$$
- **Enforced Remediation:**
  1. Phase 18 explicitly acknowledges that the tournament winner's reported Sharpe is **maximally biased upward**.
  2. The tournament winner's performance metrics are tagged with a mandatory `WinnerCurseDiscountFactor`:
     $$\text{Discounted\_SR} = \widehat{SR} - \sqrt{\frac{2 \ln M}{T}}$$
  3. The full trial count $M$ is transmitted to Phase 6 so that DSR inflates the null hypothesis threshold accordingly.

### Audit Dimension 3: Multiple Testing & Search Intensity Accounting ($K$)
- **Adversarial Vector:** *Can an algorithm test 10,000 parameter permutations in Tier 1 and only report the 5 tournament finalists to Phase 6, concealing $K = 9,995$?*
- **Audit Findings:** This would constitute catastrophic data snooping and destroy the mathematical validity of Phase 6 DSR and Holm-Bonferroni corrections.
- **Enforced Remediation:**
  1. Every single parameter trial executed in Tier 1 and Tier 2 increments the local atomic counter $\Delta K_{\text{tournament}}$.
  2. Phase 18 requires cryptographic batch reporting: an experiment cannot yield a valid candidate receipt for Phase 6 without sealing the complete ledger of all $K$ discarded trials.
  3. Single Canonical Authority invariant: $K_{\text{Phase6}} \equiv K_{\text{Phase6\_prior}} + \Delta K_{\text{tournament}}$.

### Audit Dimension 4: Data Leakage & Lookahead Prevention
- **Adversarial Vector:** *Can cross-sectional normalization across tournament candidates leak information from future bars or rival strategies?*
- **Audit Findings:** If candidates are ranked bar-by-bar using cross-sectional statistics (e.g. cross-sectional z-score of returns), an execution error or lookahead bug in Strategy A could leak into Strategy B's input features.
- **Enforced Remediation:**
  1. Candidate simulation runs are executed in strictly isolated sandboxes with frozen read-only access to historical feature Parquet partitions.
  2. Cross-candidate interactions during simulation are mathematically impossible: ranking is computed exclusively post-hoc on sealed performance arrays.
  3. Dual-temporal point-in-time boundaries ($T_{\text{event}} \le T_{\text{decision}} \land T_{\text{knowledge}} \le T_{\text{as\_of}}$) are enforced at the data catalog layer.

### Audit Dimension 5: Survivorship Bias Mitigation
- **Adversarial Vector:** *Are failed or discarded tournament candidates pruned from the database, leaving only surviving high-performing strategies visible to researchers?*
- **Audit Findings:** Deleting failed runs distorts historical records, prevents institutional memory, and induces survivorship bias in meta-research.
- **Enforced Remediation:**
  1. Zero deletion policy: `ResearchCandidateRegistry` is append-only.
  2. Failed runs are permanently stored with exact failure signatures (`FAILED_TIER1`, `COST_EXHAUSTION`, `STRESS_COLLAPSE`).
  3. Research queries by default return the entire cohort distribution, displaying failure rates alongside finalist metrics.

### Audit Dimension 6: Reproducibility & Bitwise Determinism
- **Adversarial Vector:** *Can a tournament run produce different rankings on different days due to multi-threading race conditions, non-deterministic random seeds, or dependency version updates?*
- **Audit Findings:** Multi-threaded parallel backtests often exhibit non-deterministic tie-breaking or out-of-order execution, producing shifting Sharpe ratios.
- **Enforced Remediation:**
  1. Fixed pseudo-random seed policy: Every stochastic resampling process must derive its seed canonically from $\text{seed} = \text{uint32}(\text{SHA256}(\text{manifest\_id})[:4])$.
  2. Deterministic total ordering: All event processing and tie-breaking must use canonical 5-tuples $(T_{\text{event}}, \text{source\_key}, \text{rank}, \text{stream\_id}, \text{sub\_index})$.
  3. Manifest sealing: An experiment cannot be registered without recording the exact Git commit SHA and Python environment package hash.

### Audit Dimension 7: Candidate Provenance & Lineage Tracking
- **Adversarial Vector:** *Can a candidate strategy be submitted to Phase 6 without proof of its origin, generating 'orphan' models?*
- **Audit Findings:** In quantitative shops, models often get tweaked informally without tracking which hypothesis prompted the change.
- **Enforced Remediation:**
  1. Mandatory lineage chain: Every candidate must provide cryptographic links:
     $$\text{HypothesisSpecification (Phase 4)} \longrightarrow \text{ExperimentManifest (Phase 18)} \longrightarrow \text{CandidateRunRecord (Phase 18)}$$
  2. Missing lineage fails closed immediately; Phase 6 validation gates reject any submission missing a valid upstream manifest digest.

### Audit Dimension 8: Negative Knowledge Preservation & Falsification
- **Adversarial Vector:** *Does the tournament system discard negative results, causing future researchers to repeat the same failed experiments?*
- **Audit Findings:** Repeating failed experiments wastes compute and repeatedly inflates implicit multiple testing.
- **Enforced Remediation:**
  1. `NegativeKnowledgeLedger` indexes failed hypotheses and parameter regions.
  2. Before launching a new tournament, the system runs a preflight check against the negative ledger to alert researchers if a proposed parameter grid has already been definitively falsified.

### Audit Dimension 9: Ranking Semantics & Epistemic Discipline
- **Adversarial Vector:** *Is the 'Rank #1' tournament candidate treated as superior to 'Rank #2' when the difference is within statistical noise?*
- **Audit Findings:** Minor differences in Sharpe (e.g. 1.45 vs 1.42) over 500 trades have overlapping $95\%$ confidence intervals, making strict rank order scientifically meaningless.
- **Enforced Remediation:**
  1. Ranking is explicitly documented as an ordinal screening convenience, *not* an epistemic proof of superiority.
  2. The scoring engine calculates pairwise HAC confidence intervals on return differentials: if $\text{diff} = R_A - R_B$ is not statistically distinguishable from zero, strategies $A$ and $B$ are flagged as a statistical tie.

### Audit Dimension 10: Compute & Resource Governance
- **Adversarial Vector:** *Can an unconstrained grid search spin out of control, consuming hundreds of gigabytes of RAM, starving the Phase 13 soak test, or causing workstation thrashing?*
- **Audit Findings:** Unbounded parallel research processes can easily exhaust system RAM or CPU cores, threatening the host OS and concurrent background processes.
- **Enforced Remediation:**
  1. Strict resource bounds: Tournament batches must enforce max worker concurrency ($\le \text{LogicalCores} - 2$).
  2. Process isolation: Research batch runners must execute under low OS process priority (`BELOW_NORMAL_PRIORITY_CLASS`) so they never starve PID 41844 or critical runtime services.
  3. Hard memory ceiling: Any worker exceeding 2.0 GB RSS is automatically halted via fail-closed memory watchdogs.

### Audit Dimension 11: Phase 14 AI Epistemic Firewall
- **Adversarial Vector:** *Can an LLM or generative AI agent use Phase 18 to run autonomous search loops, declare its own strategies successful, and promote them directly to the catalog?*
- **Audit Findings:** Generative agents optimize for specified metrics and will ruthlessly exploit simulator edge cases or overfit backtests if given unmonitored execution loops.
- **Enforced Remediation:**
  1. AI outputs remain strictly classified as `UNVALIDATED_PROPOSAL`.
  2. AI agents are prohibited from modifying tournament scoring weights, altering baseline benchmarks, or overriding falsification criteria.
  3. Promotion from Phase 18 to Phase 6 requires human quantitative authorization or an immutable pre-registered workflow.

### Audit Dimension 12: Phase 17 Admission Boundary
- **Adversarial Vector:** *Does passing a Phase 18 tournament allow a strategy to enter the Phase 17 catalog directly?*
- **Audit Findings:** Conflating tournament survival with admission destroys the Gate 0–10 institutional standard.
- **Enforced Remediation:**
  1. Tournament survival merely qualifies a candidate to be submitted to Phase 6 (Validation).
  2. It must subsequently satisfy Phase 8.5 (Economic Qualification Dossier) and Phase 11 (Forward Monitoring).
  3. Phase 17 Gate 10 sovereign review by the Human Sovereign Committee is mandatory before catalog entry is permitted.

---

## 5. Threshold Provenance & Classification Taxonomy

All numerical thresholds and evaluation parameters in Phase 18 are classified in accordance with `AGENTS.md` standards:

| Parameter / Threshold | Subsystem | Classification | Owning Authority / Provenance | Epistemic Description |
| :--- | :--- | :--- | :--- | :--- |
| $\text{Seed} = \text{uint32}(\text{SHA256}[:4])$ | Manifest Engine | **Class A: Canonical ACASH Invariant** | Phase 1/5 Deterministic Seed Standard | Exact bitwise reproducibility requirement |
| $K_{\text{Phase6}} \equiv K_{\text{prior}} + \Delta K$ | Negative Ledger | **Class A: Canonical ACASH Invariant** | Phase 6 Multiple Testing Contract | Strict fail-closed search intensity accounting |
| $\text{Capital Allocation} = \$0.00$ | System-Wide | **Class A: Canonical ACASH Invariant** | ADR-023 / Project-Wide Governance | Hard-locked system invariant |
| $\text{Tier-1 Parameter Sweep} \pm 20\%$ | Two-Tier Harness | **Class B: Governance-Defined Threshold** | Phase 18 Research Governance | Standard screening neighborhood boundary |
| $\text{Worker Concurrency} \le \text{Cores} - 2$ | Resource Substrate | **Class B: Governance-Defined Threshold** | Phase 18 Host Protection Policy | CPU starvation prevention policy |
| $\text{Max Worker Memory} \le 2.0\text{ GB}$ | Resource Substrate | **Class B: Governance-Defined Threshold** | Phase 18 Host Protection Policy | Memory thrashing prevention policy |
| $\text{Minimum Cohort Size} \ge 5$ | Cohort Manager | **Class C: Research Heuristic** | Quantitative Tournament Best Practice | Minimum cross-sectional diversity heuristic |
| $\text{Tie-Breaking Alpha Band } p > 0.05$ | Scoring Engine | **Class C: Research Heuristic** | Econometric Hypothesis Testing Standard | Pairwise statistical tie detection heuristic |
| Winner's Curse Formula $\sqrt{\frac{2 \ln M}{T}}$ | Scoring Engine | **Class C: Research Heuristic** | Extreme Value Theory (López de Prado 2018) | Heuristic selection bias discount |
| 4 Mandatory Baselines (Cash, EW, InvVol, VWAP) | Benchmarking Engine | **Class B: Governance-Defined Threshold** | Phase 18 Benchmarking Standard | Mandatory relative hurdle baseline |

---

## 6. Implementation Constraints & Acceptance Criteria (For Future Implementation Phase)

When Phase 18 implementation is formally authorized by the Human Auditor following the completion of Phase 13, the implementation must adhere to the following strict constraints:

### 6.1 Architecture & Code Structure
1. **Module Location:** All Phase 18 code must reside exclusively in `src/acash/research/tournament/`.
2. **Zero Modification to Prior Sealed Modules:** No changes to `src/acash/core/`, `src/acash/data/`, `src/acash/validation/`, `src/acash/execution/`, `src/acash/monitoring/`, or `src/acash/runtime/`.
3. **Data Transfer Objects:** All candidate definitions, experiment manifests, tournament receipts, and ledger events must be immutable Pydantic v2 models (`frozen=True`) with strict Decimal arithmetic for financial metrics.
4. **Typing & Linting:** 100% clean under `mypy --strict`.

### 6.2 Acceptance Criteria for Implementation Authorization
- [ ] Unit test suite verifying exact bitwise reproducibility of tournament manifests across repeated runs.
- [ ] Unit test verifying that every parameter trial correctly increments the local $\Delta K$ counter and updates the negative knowledge ledger.
- [ ] Integration test verifying that a tournament winner cannot bypass Phase 6 or Phase 8.5 to gain catalog admission.
- [ ] Adversarial test demonstrating that injecting a lookahead bias into one strategy candidate is quarantined and does not leak to rival candidates.
- [ ] Host safety test verifying that worker concurrency strictly respects the `LogicalCores - 2` ceiling and does not affect background processes.

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
Document Revision     : Phase 18 Rev 1.0 (v1.0.0)
Current Status        : PROPOSED / HUMAN APPROVAL PENDING
Parent Governance     : docs/ROADMAP.md (v3.4.0), AGENTS.md, ADR-023
Adversarial Audit     : COMPLETE (12 / 12 Dimensions PASS)

Authority Invariants:
  [x] Phase 6 Statistical Authority Preserved (Strict Consumer Only; ΔK emitted to sealed ledger)
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
