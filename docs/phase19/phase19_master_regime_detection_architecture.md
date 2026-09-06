# ACASH Phase 19 — Empirical Regime Detection Engine
## Master Research Architecture, Governance Specification & Adversarial Self-Audit

> **Document ID:** `ACASH-SPEC-PHASE19-REGIME-v1.0`  
> **Status:** PROPOSED ARCHITECTURE & GOVERNANCE SPECIFICATION — HUMAN APPROVAL PENDING (Phase 19 Rev 1.0)  
> **Parent Governance:** `docs/ROADMAP.md` (v3.4.0), `AGENTS.md`, ADR-022, ADR-023  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Evidence > Belief, Single Canonical Authority)  
> **Date:** 2026-09-06  
> **Version:** 1.0.0  

---

> [!IMPORTANT]
> **STRICT GOVERNANCE BOUNDARY & CAPITAL RESTRICTIONS:**
> - **THIS SPECIFICATION IS A DESIGN, ARCHITECTURAL, AND GOVERNANCE DOCUMENT ONLY.**
> - **THIS SPECIFICATION DOES NOT AUTHORIZE CODE IMPLEMENTATION.**
> - **PHASE 19 IMPLEMENTATION IS STRICTLY LOCKED / NOT AUTHORIZED.**
> - **THIS SPECIFICATION DOES NOT GRANT LIVE TRADING OR BROKER PERMISSIONS.**
> - **LIVE CAPITAL AUTHORITY REMAINS HARD-LOCKED AT $0.00.**
> - **LIVE ORDER EMISSION AUTHORITY REMAINS STRICTLY 0.**
> - **LIVE BROKER CONNECTION REMAINS STRICTLY DISCONNECTED.**
> - **ZERO RUNTIME MUTATION TO `src/` OR `tests/`.**
> - **PHASE 13 STEP 5 UNATTENDED SOAK TEST (PID 41844) REMAINS ACTIVE AND UNTOUCHED.**

---

## 1. Executive Summary & Epistemic Foundations

Phase 19 establishes the **Empirical Regime Detection Engine** for ACASH. Its sovereign purpose is to detect, classify, track, and preserve empirical evidence regarding market regimes from time-indexed financial data.

Market prices exhibit non-stationary return distributions, clustering volatility, shifting correlation structures, and intermittent liquidity states. Phase 19 provides the rigorous mathematical and measurement substrate to identify these states without committing the epistemic error of confusing descriptive classification with predictive certainty.

### 1.1 Critical Epistemic Distinctions
Phase 19 is governed by non-negotiable epistemic boundaries:

$$\boxed{\begin{aligned}
\text{Detected Regime} &\not\equiv \text{Validated Regime} \\
\text{Detected Regime} &\not\equiv \text{Economic Explanation} \\
\text{Detected Regime} &\not\equiv \text{Strategy Recommendation} \\
\text{Detected Regime} &\not\equiv \text{Capital Allocation} \\
\text{Regime Confidence} &\not\equiv \text{Statistical Significance} \\
\text{Model Stability} &\not\equiv \text{Trading Profitability} \\
\text{Historical Regime Label} &\not\equiv \text{Future Regime Certainty} \\
\text{Regime Transition} &\not\equiv \text{Guaranteed Structural Break} \\
\text{AI Interpretation} &\not\equiv \text{Empirical Evidence} \\
\text{Phase 19 Research Evidence} &\not\equiv \text{Phase 6 ValidationReport}
\end{aligned}}$$

### 1.2 The Measurement vs Decision Dichotomy
Phase 19 is strictly a **measurement and evidence layer**, *not* a decision layer:
- **Phase 19 Measures:** What empirical state characterizes the market at time $T$? (Trend slope, realized volatility, spread depth, order book imbalance, transition probability).
- **Phase 20 Decides:** Given the empirical state measured by Phase 19, which admitted strategies from Phase 17 are eligible for execution?
- **Phase 21 Allocates:** What risk budget and capital weights are assigned across eligible strategies?

Phase 19 possesses **zero** authority to select strategies, modify weights, or allocate capital.

---

## 2. Canonical Authority Architecture & Phase Boundary Matrix

Phase 19 operates within the immutable ACASH authority hierarchy:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PHASE 14: AI RESEARCH LAYER                            │
│                 (Unvalidated Hypothesis Proposals)                          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 18: STRATEGY RESEARCH & TOURNAMENT                     │
│                  (Exploratory Tournament Benchmarking)                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 19: EMPIRICAL REGIME DETECTION ENGINE                 │
│  ├── RegimeDataContract (Dual-Temporal PIT)                                 │
│  ├── RegimeFeatureBuilder (Causal Multi-Dimensional State Descriptors)       │
│  ├── RegimeDetectionEngine (Bounded Methodological Family)                  │
│  ├── RegimeStateModel (State Vector + Uncertainty + UNKNOWN State)          │
│  ├── RegimeValidationEvidence (Stability vs Significance Boundaries)        │
│  ├── RegimeHistoryLedger (Append-Only Cryptographic State Transitions)       │
│  ├── RegimeReproducibilityManifest (Declared-Environment Determinism)       │
│  └── Downstream Interface to Phase 20 (Read-Only Regime Observation)        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Read-Only Regime Observations
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 20: REGIME × STRATEGY SELECTION ENGINE                │
│                 (Dynamic Strategy Eligibility & Matching)                   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Eligible Strategy Set
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHASE 21: RISK-BASED CAPITAL ALLOCATION                     │
│              (Production Optimization Solvers: ERC, VolTarget)              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Complete Cross-Phase Authority Matrix

| Phase | Sovereign Ownership | Consumes from Upstream | Produces for Downstream | Forbidden Authority in Phase |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 6** | Canonical Statistical Validation, DSR, MinTRL, PBO, multiple testing. | Candidate trial logs, return matrices. | `ValidationReport`, `evidence_digest`. | Cannot be bypassed; sole authority for statistical validity. |
| **Phase 8.5** | Alpha Economic Qualification, Friction Waterfall, Net Alpha Dossier. | Backtest manifests, simulation logs. | `AlphaQualificationDossier`. | Cannot be bypassed; sole authority for economic edge. |
| **Phase 11** | Forward Monitoring, Telemetry Ingestion, Reality Gap Attribution. | Live broker telemetry, forward fills. | `ForwardHealthState`, `ExecutionCostEvidence`. | Cannot be mutated; sole authority for runtime health. |
| **Phase 13** | Paper Validation, 24h Soak, Pre-Live Operations, Gate A/B. | Phase 12 adapters, Phase 10 supervisor. | Operational Soak Receipts, Gate B readiness. | Cannot be claimed complete without empirical evidence. |
| **Phase 14** | AI Quantitative Research Proposals, Hypothesis Assistance. | Epistemic corpus, research literature. | `UNVALIDATED_PROPOSAL`. | Cannot grant alpha qualification or trading authority. |
| **Phase 17** | Strategy Admission Standard, Lifecycle State, Catalog Gates 0–10. | Phase 6 receipts, Phase 8.5 dossiers. | `StrategyAdmissionStatus`, Catalog Entry. | Cannot execute live orders or allocate capital. |
| **Phase 18** | Tournament Pipeline, Candidate Registry, Cohort Benchmarking. | Phase 14 proposals, Phase 4 specs. | `TournamentCandidateEvaluationRecord`, $\Delta K$. | Cannot grant statistical validity or admission. |
| **Phase 19** | **Empirical Regime Detection, State Measurement, Transition Tracking.** | **Point-in-Time Market Data, Phase 11 telemetry.** | **`RegimeObservationEnvelope`, Regime Ledger.** | **FORBIDDEN: Strategy selection, capital allocation, statistical validation, order execution.** |
| **Phase 20** | Regime × Strategy Selection, Compatibility Gating, Decision Memory. | Phase 17 catalog, Phase 19 regime state. | Active Strategy Slate. | Cannot modify regime models or risk budgets. |
| **Phase 21** | Risk-Based Capital Allocation Solvers (ERC, VolTargeting, Bounds). | Phase 20 strategy slate, Phase 9 limits. | Target Capital Allocation. | Cannot exceed Phase 17 bounded allocation limits. |
| **Phase 22** | Portfolio Orchestration, Multi-Strategy Netting, Memory Flywheel. | Phase 21 weights, Phase 10 supervisor. | Execution Intent Batch. | Cannot override sovereign kill switch. |

---

## 3. Phase 19 Core Architectural Subsystems

Phase 19 is organized into nine decoupled sovereign subsystems:

```
                                  PHASE 19 ARCHITECTURE
                                            │
       ┌────────────────────┬───────────────┴───────────────┬──────────────────┐
       ▼                    ▼                               ▼                  ▼
1. DATA CONTRACT       2. FEATURE BUILDER             3. DETECTION ENGINE 4. STATE MODEL
  (Dual-Temporal PIT)    (Deterministic Causal)         (Bounded Family)    (Vector + UNKNOWN)
                                                                               │
       ┌───────────────────────────────────────────────────────────────────────┘
       ▼
5. VALIDATION EVIDENCE ──► 6. HISTORY LEDGER ──► 7. MANIFEST ENGINE ──► 8. MONITORING / 9. DOWNSTREAM
  (Stability != Alpha)       (Chained Events)       (Environment Sealing)  (Phase 11 & Phase 20)
```

### 3.1 Subsystem 1: `RegimeDataContract`
- **Responsibility:** Ingests raw market data and enforces dual-temporal point-in-time validity.
- **Timestamp Semantics:**
  - `event_time_utc`: Wall-clock exchange bar timestamp.
  - `knowledge_time_utc`: Earliest timestamp when the data was available to the system without lookahead.
  - Invariant: $T_{\text{event\_utc}} \le T_{\text{decision\_utc}} \quad\land\quad T_{\text{knowledge\_utc}} \le T_{\text{as\_of\_utc}}$.
- **Market & Session Calendar:** Distinguishes continuous trading hours, rollover intervals, weekend closures, and holiday schedules.
- **Missing Data Policy (Strict Fail-Closed):**
  - Forward-filling of missing market quotes across session breaks is **strictly prohibited**.
  - If bar gaps exceed the tolerance threshold ($\tau_{\text{gap}} > 2$ missing intervals), the data stream is flagged `DATA_GAP_UNRESOLVED` and the detector emits `RegimeState.UNKNOWN`.

### 3.2 Subsystem 2: `RegimeFeatureBuilder`
- **Responsibility:** Constructs causal, mathematically bounded features representing market state dynamics.
- **Feature Space Dimensions:**
  1. **Volatility & Dispersion:** Normalized Realized Volatility ($\sigma_{\text{realized}}$), Parkinson High-Low Volatility, Garman-Klass Volatility, Average True Range Ratio ($ATR / P_{\text{close}}$).
  2. **Trend & Directional Structure:** Discrete forward slope $\hat{\beta}_{\text{trend}}$, Directional Movement Index (DMI/ADX), Multi-scale Moving Average Divergence.
  3. **Liquidity & Microstructure (Where Available):** Bid-Ask Spread Delta, Depth Imbalance Ratio (OBI), Amihud Illiquidity Metric, Effective Spread / Realized Spread.
  4. **Cross-Sectional & Correlation Context:** Pairwise asset correlation drift, cross-sectional dispersion.
- **Causal Invariance Guarantee:** Every feature must be strictly backward-looking over interval $[t - W, t]$. Future window transformations (e.g. centered moving averages, lookahead smoothing filters) fail closed immediately at schema validation.

### 3.3 Subsystem 3: `RegimeDetectionEngine`
Phase 19 explicitly rejects the assumption that a single detection algorithm is universally optimal. It supports a **bounded family of four methodology classes**:

```
                              DETECTION METHODOLOGY FAMILY
                                            │
       ┌────────────────────┬───────────────┴───────────────┬──────────────────┐
       ▼                    ▼                               ▼                  ▼
CLASS A: RULE-BASED    CLASS B: CLUSTERING            CLASS C: MARKOV SWITCH CLASS D: CHANGE-POINT
(Quantile Thresholds)  (GMM / K-Means Covariance)     (HMM Latent State)     (CUSUM / BOCPD)
```

1. **Class A: Deterministic Rule-Based Classification:**
   - Transparent, non-parametric state mapping across orthogonal quantiles (e.g. Trend $\in \{\text{BEAR}, \text{NEUTRAL}, \text{BULL}\} \times \text{Vol} \in \{\text{LOW}, \text{NORMAL}, \text{HIGH}\}$).
   - Zero parameter overfitting; robust baseline.
2. **Class B: Unsupervised Statistical Clustering:**
   - Gaussian Mixture Models (GMM) or K-Means over normalized feature vectors.
   - Deterministic initial seeds; cluster labels mapped via standardized centroid sorting.
3. **Class C: Hidden Markov Models (HMM / State Switching):**
   - Latent state estimation assuming first-order Markov transitions with declared transition matrix priors.
   - Outputs posterior state probabilities $[P(S_1), \dots, P(S_K)]$.
4. **Class D: Non-Parametric Change-Point Detection:**
   - Bayesian Online Changepoint Detection (BOCPD) or Page-Hinkley CUSUM to identify acute structural distribution shifts.

### 3.4 Subsystem 4: `RegimeStateModel`
- **Responsibility:** Formal representation of the detected regime state.
- **Schema Specification (`RegimeState`):**
  ```python
  class RegimeState(BaseModel):
      timestamp_utc: datetime
      symbol_or_universe: str
      detector_id: str
      detector_family: DetectorFamily
      primary_regime: RegimeIdentifier
      regime_probabilities: dict[RegimeIdentifier, Decimal]
      uncertainty_score: Decimal
      persistence_duration_bars: int
      is_ambiguous: bool
      detector_version: str
      feature_digest: str
  ```
- **The Mandatory `UNKNOWN` State:**
  When classifier confidence falls below the ambiguity threshold ($P_{\max} < 0.50$), when detectors in an ensemble contradict, or when data gaps exist, Phase 19 must emit:
  $$\boxed{\text{primary\_regime} = \mathbf{RegimeIdentifier.UNKNOWN}}$$
  Phase 19 strictly forbids forcing a weak classification into an arbitrary discrete regime.

### 3.5 Subsystem 5: `RegimeValidationEvidence`
- **Responsibility:** Evaluates regime detector stability, persistence, and information content without encroaching on Phase 6 statistical validation.
- **Evaluation Criteria:**
  - **Transition Stability:** Frequency of regime flipping (anti-churn metric).
  - **Within-Regime Distributional Homogeneity:** Kolmogorov-Smirnov / Wasserstein distance of return distributions across identical regime tags.
  - **Cross-Regime Separation:** Distance between regime centroids in feature space.
- **Epistemic Constraint:** Phase 19 validation proves only that the detector measures a persistent statistical distribution; it does **not** prove that trading strategies conditioned on this regime will be profitable.

### 3.6 Subsystem 6: `RegimeHistoryLedger`
- **Responsibility:** Cryptographically chained, append-only disk ledger recording all historical regime observations and transitions.
- **Chained Event Structure:**
  $$\text{event\_hash}_t = \text{SHA256}(\text{event\_hash}_{t-1} + \text{timestamp} + \text{detector\_id} + \text{regime\_state} + \text{feature\_digest})$$
- **Audit Requirement:** Historical regime labels can never be overwritten retroactively. If a detector model is updated, historical periods are re-evaluated under a new detector version ID, preserving the original historical observation intact.

### 3.7 Subsystem 7: `RegimeReproducibilityManifest`
- **Responsibility:** Enforces deterministic reproducibility within declared execution environments.
- **Declared Execution Environment (`DeclaredExecutionEnvironment`):**
  1. Python runtime & micro-version (`CPython 3.12.x`)
  2. OS & hardware architecture (`Windows-11-AMD64`)
  3. Dependency lockfile hash (`uv.lock`)
  4. Core numerical package versions (`numpy`, `scipy`, `scikit-learn`, `hmmlearn`)
  5. Canonical random seed
  6. Git commit SHA
  7. Input market data partition SHA-256 digests
- **Invariance Guarantee:** Re-running a detector on identical historical data partitions under the declared environment manifest must reproduce identical regime labels and transition timestamps.

### 3.8 Subsystem 8: `RegimeMonitoringInterface`
- **Responsibility:** Read-only ingestion of runtime forward telemetry from Phase 11.
- **Strict Boundary Rule:** Phase 19 **MUST NOT** replace, fork, or compete with Phase 11 `ForwardHealthStateMachine`.
- **Operational Interface:** Phase 19 ingests Phase 11 `ExecutionCostEvidence` and `StrategyForwardDriftEvidence` solely as observational context to determine whether live market dynamics match historical regime training distributions.

### 3.9 Subsystem 9: Downstream Interface to Phase 20 (`DownstreamContract`)
- **Responsibility:** Pure read-only emission of regime observations to Phase 20.
- **Output Artifact (`RegimeObservationEnvelope`):**
  - Current regime identifier and probability vector.
  - Regime stability duration ($N$ bars in current state).
  - Transition alert flag (`TRANSITION_CONFIRMED`, `TRANSITION_CANDIDATE`, `STABLE`).
  - Uncertainty metadata.
- **Decoupling Guarantee:** Phase 19 provides the state observation. It possesses zero visibility into strategy code, portfolio weights, or risk budgets.

---

## 4. Regime Detection Methodology Governance & Negative Knowledge

### 4.1 Methodology Governance Rules
1. **Anti-Whipsaw Hysteresis:** State transitions require confirmation across $H \ge 2$ consecutive bars or a transition probability exceeding threshold $\theta_{\text{trans}} \ge 0.65$ to prevent false switching and trading churn.
2. **Minimum Regime Duration:** Any regime state with a median empirical duration of $< 5$ bars is classified as `NOISE_STATE` and merged into the background neutral state.
3. **Parameter Perturbation Robustness:** A detector must survive $\pm 15\%$ perturbation to its lookback window $W$ without altering $> 10\%$ of historical state labels. Detectors collapsing under small window changes fail closed.

### 4.2 Negative Knowledge & Detection Failure Preservation
Failed, unstable, or non-generalizing regime models are treated as first-class scientific artifacts:
- **`NegativeRegimeLedger`:** Permanently catalogs detectors that suffered:
  - Excessive transition churn ($> 30\%$ bars exhibiting state flips).
  - Low-sample collapse ($< 2\%$ of historical data in an isolated state).
  - Parameter cliff sensitivity.
  - Out-of-sample distributional breakdown.
- **Anti-Snooping Rule:** Negative knowledge prevents redundant hyperparameter search loops from repeatedly evaluating known non-stationary feature combinations.

---

## 5. Mandatory Adversarial Self-Audit (26 Dimensions)

Every risk vector is audited with explicit control definitions, fail-closed behaviors, and implementation-readiness statuses:

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      PHASE 19 ADVERSARIAL AUDIT MATRIX                           │
├────┬────────────────────────────────────┬───────────────────────────────────────┤
│ #  │ Audit Dimension                    │ Audit Verification Status             │
├────┼────────────────────────────────────┼───────────────────────────────────────┤
│ 1  │ Lookahead Bias / Future Leakage    │ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 2  │ Point-in-Time Integrity            │ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 3  │ Regime Label Hindsight Bias        │ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 4  │ Arbitrary Threshold / Hyperparams  │ CONTROL SPECIFIED — RESEARCH HEURISTIC│
│ 5  │ Regime Proliferation / Over-Frag   │ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 6  │ False Regime Switching / Churn     │ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 7  │ Low-Sample Regimes                 │ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 8  │ Regime Boundary Sensitivity        │ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 9  │ Detector Instability Across Windows│ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 10 │ Data Snooping / Multiple Testing   │ CONTROL SPECIFIED — SUBORDINATE PH6   │
│ 11 │ Cross-Asset Contamination          │ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 12 │ Survivorship Bias                  │ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 13 │ Missing Data / Stale Data          │ CONTROL SPECIFIED — STRICT FAIL-CLOSED│
│ 14 │ Feature Revision / Restatement     │ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 15 │ Model Drift                        │ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 16 │ Detector Drift                     │ CONTROL SPECIFIED — NOT RUNTIME VERIF │
│ 17 │ UNKNOWN / Ambiguous State Handling │ CONTROL SPECIFIED — STRICT FAIL-CLOSED│
│ 18 │ Economic Interpretation Overreach  │ CONTROL SPECIFIED — EPISTEMIC RULE    │
│ 19 │ Phase 6 Authority Boundary         │ CONTROL SPECIFIED — SOLE AUTH PH6     │
│ 20 │ Phase 11 Authority Boundary        │ CONTROL SPECIFIED — SOLE AUTH PH11    │
│ 21 │ Phase 17 Authority Boundary        │ CONTROL SPECIFIED — SOLE AUTH PH17    │
│ 22 │ Phase 20 Boundary                  │ CONTROL SPECIFIED — READ-ONLY EMISSION│
│ 23 │ Capital Allocation Boundary        │ CONTROL SPECIFIED — $0.00 HARD-LOCKED │
│ 24 │ Reproducibility / Lineage          │ CONTROL SPECIFIED — MANIFEST SEALED   │
│ 25 │ Compute / Resource Governance      │ CONTROL SPECIFIED — RESOURCE BOUNDED  │
│ 26 │ AI Epistemic Firewall              │ CONTROL SPECIFIED — UNVALIDATED PROP  │
└────┴────────────────────────────────────┴───────────────────────────────────────┘
```

### Detailed Dimensional Analysis

#### 1. Lookahead Bias / Future Leakage
- **Risk:** Calculating regime features using full-sample statistics (e.g. full-dataset standard deviation) or future bars leaks tomorrow's state into today's label.
- **Control:** Strict backward-only window $[t-W, t]$. Centered filters and full-sample scalers are prohibited.
- **Fail-Closed Behavior:** Any feature attempting index access $> t$ raises `LookaheadContaminationError`.
- **Status:** `CONTROL SPECIFIED — NOT YET VERIFIED IN RUNTIME`.

#### 2. Point-in-Time Integrity
- **Risk:** Time series revisions or restatements altering historical regime labels retroactively.
- **Control:** Dual-temporal timestamping ($T_{\text{event}} \le T_{\text{decision}} \land T_{\text{knowledge}} \le T_{\text{as\_of}}$).
- **Fail-Closed Behavior:** Knowledge timestamps $> T_{\text{decision}}$ fail closed.
- **Status:** `CONTROL SPECIFIED — NOT YET VERIFIED IN RUNTIME`.

#### 3. Regime Label Hindsight Bias
- **Risk:** Using smoothed posterior HMM probabilities $P(S_t \mid y_1, \dots, y_T)$ where $T > t$ (smoothing filter instead of filtering filter).
- **Control:** Online detection must strictly use the causal filtering distribution $P(S_t \mid y_1, \dots, y_t)$. Smoothing is permitted only in post-hoc research analysis and explicitly tagged as `HINDSIGHT_SMOOTHED`.
- **Fail-Closed Behavior:** `HINDSIGHT_SMOOTHED` tags are rejected by Phase 20 live selection.
- **Status:** `CONTROL SPECIFIED — NOT YET VERIFIED IN RUNTIME`.

#### 4. Arbitrary Threshold & Hyperparameter Tuning
- **Risk:** Cherry-picking volatility cutoffs (e.g. $\sigma > 0.015$) to optimize a subsequent backtest.
- **Control:** Cutoffs must be pre-registered using expanding-window empirical quantiles (e.g. 80th percentile over prior 252 bars).
- **Fail-Closed Behavior:** Static hand-tuned magic numbers without empirical derivation are rejected.
- **Status:** `CONTROL SPECIFIED — RESEARCH HEURISTIC ONLY`.

#### 5. Regime Proliferation / Over-Fragmentation
- **Risk:** Overfitting data by creating 20 granular micro-regimes with minimal data support.
- **Control:** Maximum number of active discrete states per detector family is bounded: $K \le 5$.
- **Fail-Closed Behavior:** Any clustering model initialized with $K > 5$ raises `RegimeProliferationError`.
- **Status:** `CONTROL SPECIFIED — GOVERNANCE POLICY BOUND`.

#### 6. False Regime Switching / Churn
- **Risk:** High-frequency state oscillation generating transaction whipsaw downstream.
- **Control:** Anti-churn hysteresis: requires confirmation across $H \ge 2$ bars or persistence filter.
- **Fail-Closed Behavior:** State transitions oscillating $< 3$ bars revert to `RegimeIdentifier.UNKNOWN`.
- **Status:** `CONTROL SPECIFIED — NOT YET VERIFIED IN RUNTIME`.

#### 7. Low-Sample Regimes
- **Risk:** Detecting an "acute crisis" regime containing only 6 total bars, making statistical inference impossible.
- **Control:** Minimum sample threshold: Any state accounting for $< 3\%$ of historical data cannot be admitted as an independent operational regime.
- **Fail-Closed Behavior:** Sub-threshold states are merged into `RegimeIdentifier.UNKNOWN`.
- **Status:** `CONTROL SPECIFIED — NOT YET VERIFIED IN RUNTIME`.

#### 8. Regime Boundary Sensitivity
- **Risk:** Small perturbations in prices flip the regime classification completely.
- **Control:** Boundary sensitivity audit: state must remain stable under $\pm 0.5 \times \text{Spread}$ noise injection.
- **Fail-Closed Behavior:** Detectors failing boundary sensitivity are relegated to `NegativeRegimeLedger`.
- **Status:** `CONTROL SPECIFIED — NOT YET VERIFIED IN RUNTIME`.

#### 9. Detector Instability Across Windows
- **Risk:** Expanding or rolling lookback windows fundamentally change cluster centroid definitions.
- **Control:** Centroid tracking: cluster re-estimation must maintain centroid cosine similarity $\ge 0.85$ with prior window.
- **Fail-Closed Behavior:** Centroid inversion triggers `RegimeCentroidInversionError` and halts detector.
- **Status:** `CONTROL SPECIFIED — NOT YET VERIFIED IN RUNTIME`.

#### 10. Data Snooping & Multiple Testing
- **Risk:** Evaluating 500 regime indicator permutations without adjusting statistical significance.
- **Control:** Subordinate to Phase 6: All evaluated regime detector configurations emit trial candidate events to the canonical `SearchTrialLedger`.
- **Fail-Closed Behavior:** Phase 19 cannot declare statistical significance independently.
- **Status:** `CONTROL SPECIFIED — SUBORDINATED TO PHASE 6 AUTHORITY`.

#### 11. Cross-Asset Contamination
- **Risk:** Using US Equity volatility to classify FX market regimes without checking market hours or transmission lags.
- **Control:** Strict universe scoping: multi-asset features must have explicit alignment contracts and timezone normalization.
- **Fail-Closed Behavior:** Unaligned cross-asset streams fail closed immediately.
- **Status:** `CONTROL SPECIFIED — NOT YET VERIFIED IN RUNTIME`.

#### 12. Survivorship Bias
- **Risk:** Discarding failed regime detectors, giving a false impression of high detector stability.
- **Control:** Append-only `NegativeRegimeLedger`: every failed configuration is immutably sealed.
- **Fail-Closed Behavior:** Zero deletion policy.
- **Status:** `CONTROL SPECIFIED — NOT YET VERIFIED IN RUNTIME`.

#### 13. Missing Data & Stale Feeds
- **Risk:** Market feed halts; detector continues forward-filling stale volatility, giving false calm.
- **Control:** Max gap policy: $\tau_{\text{gap}} > 2$ missing bars triggers immediate transition to `RegimeIdentifier.UNKNOWN`.
- **Fail-Closed Behavior:** Instantaneous emit of `UNKNOWN` state.
- **Status:** `CONTROL SPECIFIED — STRICT FAIL-CLOSED`.

#### 14. Feature Revision & Data Vendor Restatement
- **Risk:** Vendor restates historical volume, changing historical regime tags retroactively.
- **Control:** Immutable historical record: ledger records historical tag as of knowledge time. Re-evaluations are recorded under new revision hashes.
- **Fail-Closed Behavior:** Overwriting historical ledger events is cryptographically impossible.
- **Status:** `CONTROL SPECIFIED — CRYPTOGRAPHICALLY ENFORCED`.

#### 15. Model Drift
- **Risk:** Market structural dynamics shift (e.g. zero-rate regime to high-rate regime); old model becomes obsolete.
- **Control:** Distributional tracking: Kolmogorov-Smirnov test between training feature distribution and rolling 90-day feature distribution.
- **Fail-Closed Behavior:** Significant drift ($p < 0.01$) flags detector as `DETECTOR_DRIFT_DEGRADED`.
- **Status:** `CONTROL SPECIFIED — NOT YET VERIFIED IN RUNTIME`.

#### 16. Detector Drift
- **Risk:** Gradual parameter migration in adaptive online filters causing unmonitored state drift.
- **Control:** Strict parameter bounds: online adaptation rates are clamped with maximum step size $\Delta \le 0.01$.
- **Fail-Closed Behavior:** Exceeding adaptation ceiling halts online updates.
- **Status:** `CONTROL SPECIFIED — NOT YET VERIFIED IN RUNTIME`.

#### 17. UNKNOWN & Ambiguous State Handling
- **Risk:** Model forces ambiguous data into a binary Bull/Bear state.
- **Control:** First-class `RegimeIdentifier.UNKNOWN`. If max probability $P < 0.50$, output is strictly `UNKNOWN`.
- **Fail-Closed Behavior:** Downstream Phase 20 treats `UNKNOWN` as a derisking state.
- **Status:** `CONTROL SPECIFIED — STRICT FAIL-CLOSED`.

#### 18. Economic Interpretation Overreach
- **Risk:** Naming a statistical cluster "Institutional Accumulation" without microstructural proof.
- **Control:** Epistemic naming convention: Clusters are named by mathematical characteristics (e.g. `HIGH_VOL_NEGATIVE_TREND`, `LOW_VOL_CONSOLIDATION`). Subjective narrative labels are strictly prohibited.
- **Fail-Closed Behavior:** Non-conforming labels are rejected at schema validation.
- **Status:** `CONTROL SPECIFIED — EPISTEMIC RULE`.

#### 19. Phase 6 Authority Boundary
- **Risk:** Phase 19 computing its own DSR or claiming that a regime detector is statistically validated.
- **Control:** Complete decoupling: Phase 19 outputs measurements. Phase 6 is the sole statistical validation authority.
- **Fail-Closed Behavior:** Zero statistical validation methods exist in Phase 19.
- **Status:** `CONTROL SPECIFIED — SOLE AUTHORITY PHASE 6`.

#### 20. Phase 11 Authority Boundary
- **Risk:** Phase 19 attempting to monitor runtime operational health or strategy drift.
- **Control:** Phase 11 owns `ForwardHealthStateMachine`. Phase 19 only ingests Phase 11 telemetry as read-only context.
- **Fail-Closed Behavior:** Phase 19 possesses zero methods to emit health states.
- **Status:** `CONTROL SPECIFIED — SOLE AUTHORITY PHASE 11`.

#### 21. Phase 17 Authority Boundary
- **Risk:** Phase 19 attempting to admit or disqualify strategies based on regime performance.
- **Control:** Phase 17 owns Gates 0–10. Phase 19 has zero strategy catalog authority.
- **Fail-Closed Behavior:** Phase 19 contains zero strategy admission interfaces.
- **Status:** `CONTROL SPECIFIED — SOLE AUTHORITY PHASE 17`.

#### 22. Phase 20 Boundary
- **Risk:** Phase 19 deciding which strategy should run in the detected regime.
- **Control:** Pure read-only emission of `RegimeObservationEnvelope`. Phase 20 contains the matching logic.
- **Fail-Closed Behavior:** Phase 19 is strategy-blind.
- **Status:** `CONTROL SPECIFIED — READ-ONLY EMISSION`.

#### 23. Capital Allocation Boundary
- **Risk:** Phase 19 increasing position sizing or leverage during "Low Volatility" regimes.
- **Control:** Live capital remains hard-locked at `$0.00`. Phase 19 has zero sizing or broker connection.
- **Fail-Closed Behavior:** Allocation is invariant at `$0.00`.
- **Status:** `CONTROL SPECIFIED — $0.00 HARD-LOCKED`.

#### 24. Reproducibility & Lineage
- **Risk:** Inability to reproduce a historical regime classification run.
- **Control:** Manifest sealing: `DeclaredExecutionEnvironment` captures all dependencies, git SHA, dataset hashes, and seeds.
- **Fail-Closed Behavior:** Missing manifest blocks experiment publication.
- **Status:** `CONTROL SPECIFIED — MANIFEST SEALED`.

#### 25. Compute & Resource Governance
- **Risk:** Complex HMM or change-point models consuming excessive CPU/RAM and starving background soak tests (PID 41844).
- **Control:** Execution bounds: Concurrency $\le \text{Cores} - 2$, memory ceiling 2.0 GB RSS, low process priority.
- **Fail-Closed Behavior:** Watchdog terminates runaway detector processes.
- **Status:** `CONTROL SPECIFIED — RESOURCE BOUNDED`.

#### 26. AI Epistemic Firewall
- **Risk:** LLM interpreting raw market data and hallucinating macro regime labels.
- **Control:** Phase 14 AI outputs are strictly `UNVALIDATED_PROPOSAL`. AI cannot assign regime labels directly.
- **Fail-Closed Behavior:** Zero LLM inference in the primary detection loop.
- **Status:** `CONTROL SPECIFIED — UNVALIDATED PROPOSALS ONLY`.

---

## 6. Threshold Provenance & Classification Taxonomy

All numerical thresholds in Phase 19 are classified in accordance with `AGENTS.md`:

| Threshold Expression | Subsystem | Classification | Owning Authority / Provenance | Epistemic Description |
| :--- | :--- | :--- | :--- | :--- |
| $\text{Capital Allocation} = \$0.00$ | System-Wide | **Class A: Canonical ACASH Invariant** | ADR-023 / Project-Wide Governance | Hard-locked system default invariant |
| $T_{\text{event}} \le T_{\text{decision}} \land T_{\text{knowledge}} \le T_{\text{as\_of}}$ | Data Contract | **Class A: Canonical ACASH Invariant** | Phase 2/3 Dual-Temporal Invariant | Causal point-in-time boundary |
| $\text{Max States } K \le 5$ | State Model | **Class B: Governance-Defined Threshold** | Phase 19 Architecture Policy | Anti-proliferation state ceiling |
| $\text{Ambiguity Cutoff } P_{\max} < 0.50$ | State Model | **Class B: Governance-Defined Threshold** | Phase 19 Fail-Closed Policy | Transition to UNKNOWN threshold |
| $\text{Max Missing Bars } \tau_{\text{gap}} \le 2$ | Data Contract | **Class B: Governance-Defined Threshold** | Phase 19 Data Quality Policy | Missing data fail-closed tolerance |
| $\text{Worker Concurrency } \le \text{Cores} - 2$| Host Governance | **Class B: Governance-Defined Threshold** | Phase 19 Host Protection Policy | CPU starvation prevention ceiling |
| $\text{Worker Memory } \le 2.0\text{ GB}$ | Host Governance | **Class B: Governance-Defined Threshold** | Phase 19 Host Protection Policy | Host memory thrashing ceiling |
| $\text{Hysteresis Confirmation } H \ge 2\text{ bars}$ | Detection Engine | **Class C: Research Heuristic** | Microstructure Regime Best Practice | Anti-churn state persistence heuristic |
| $\text{Transition Prob } \theta_{\text{trans}} \ge 0.65$ | Detection Engine | **Class C: Research Heuristic** | Quantitative Markov Switching Practice| State transition confirmation threshold |
| $\text{Minimum State Support } \ge 3\%$ | Validation | **Class C: Research Heuristic** | Statistical Clustering Practice | Low-sample state pruning heuristic |
| $\text{Window Perturbation } \pm 15\%$ | Validation | **Class C: Research Heuristic** | Robustness Analysis Practice | Boundary sensitivity sweep heuristic |
| 90-Day Drift Evaluation Window | Monitoring | **Class D: Illustrative Threshold** | Macro Environment Drift Example | Illustrative drift monitoring window |

---

## 7. Implementation Constraints & Acceptance Criteria (For Future Phase 19 Implementation)

When implementation of Phase 19 is formally authorized by the Human Auditor following Phase 13 completion, the engineering team must satisfy the following constraints:

### 7.1 Architecture & Engineering Constraints
1. **Module Isolation:** All Phase 19 code must reside exclusively in `src/acash/research/regime/`.
2. **Zero Modification to Sealed Modules:** Zero edits to `src/acash/core/`, `src/acash/data/`, `src/acash/validation/`, `src/acash/execution/`, `src/acash/monitoring/`, or `src/acash/runtime/`.
3. **Immutable Domain Entities:** All data models, regime states, and transition receipts must be frozen Pydantic v2 models (`frozen=True`) with Decimal arithmetic for probabilities.
4. **Typing:** 100% clean under `mypy --strict`.

### 7.2 Acceptance Criteria for Implementation Authorization
- [ ] Unit test suite verifying that historical lookback calculations strictly access $t \le T_{\text{decision}}$.
- [ ] Unit test verifying that data gaps $> 2$ bars immediately emit `RegimeIdentifier.UNKNOWN`.
- [ ] Adversarial test verifying that HMM state estimation online uses causal filtering only (rejection of smoothed hindsight filters).
- [ ] Integration test verifying that Phase 19 outputs only read-only `RegimeObservationEnvelope` to Phase 20 without strategy selection logic.
- [ ] Concurrency and resource test verifying that worker threads execute with `BELOW_NORMAL_PRIORITY_CLASS` and respect memory watchdogs.

---

## 8. Authoritative Academic & Empirical Grounding

1. **Hamilton, J. D. (1989):** *A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle.* Econometrica. (Establishes the canonical Markov-switching regime autoregression model).
2. **Ang, A., & Bekaert, G. (2002):** *International Asset Allocation with Regime Shifts.* The Review of Financial Studies. (Demonstrates that correlation and volatility regimes change dynamically, altering portfolio efficiency).
3. **Adams, R. P., & MacKay, D. J. (2007):** *Bayesian Online Changepoint Detection.* University of Cambridge. (Formulates online, causal changepoint estimation without future knowledge).
4. **Kritzman, M., Page, S., & Turkington, D. (2012):** *Regime Shifts: Implications for Dynamic Asset Allocation.* Financial Analysts Journal. (Shows that regime classification improves drawdown mitigation when applied with strict transition rules).
5. **López de Prado, M. (2018):** *Advances in Financial Machine Learning.* John Wiley & Sons. (Formulates the perils of structural breaks, pseudo-stationarity, and regime-dependent backtesting).

---

## 9. Governance Sign-Off & Specification Provenance

```text
================================================================================
ACASH EMPIRICAL REGIME DETECTION ENGINE (PHASE 19) — SPECIFICATION PROVENANCE
================================================================================
Specification Document: docs/phase19/phase19_master_regime_detection_architecture.md
Document Revision     : Phase 19 Rev 1.0 (v1.0.0)
Current Status        : PROPOSED / HUMAN APPROVAL PENDING
Parent Governance     : docs/ROADMAP.md (v3.4.0), AGENTS.md, ADR-022, ADR-023
Adversarial Audit     : COMPLETE (26 / 26 Dimensions Evaluated)

Audit Classification:
  -> Architecture Specified         : COMPLETE (9 Subsystems Designed)
  -> Logical Consistency            : VERIFIED (Zero authority collisions)
  -> Implementation Readiness       : NOT AUTHORIZED / LOCKED
  -> Runtime Verification           : NOT YET VERIFIED (Requires implementation)

Authority Invariants:
  [x] Phase 6 Statistical Authority Preserved (Strict Consumer; zero DSR/PBO in Phase 19)
  [x] Phase 8.5 Economic Qualification Authority Preserved (Zero qualification in Phase 19)
  [x] Phase 11 Forward Monitoring Authority Preserved (Read-only reference; zero health mutation)
  [x] Phase 17 Strategy Admission Authority Preserved (Zero catalog authority in Phase 19)
  [x] Phase 20 Strategy Selection Boundary Preserved (Pure read-only regime observation emission)
  [x] Phase 14 AI Proposal Firewall Preserved (AI != Evidence, AI != Authority)
  [x] Live Capital Authority Hard-Locked at $0.00
  [x] Live Orders Emitted: 0 | Broker Wire: DISCONNECTED

Implementation Status:
  [x] Implementation is STRICTLY LOCKED / NOT AUTHORIZED
  [x] Zero Runtime Code Committed
  [x] Active Soak Test (PID 41844) Untouched & Continuous (~13.8h elapsed)
================================================================================
```
