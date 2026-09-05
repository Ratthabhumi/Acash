# ACASH Strategy Admission Standard v1.1
## Sovereign Governance, Empirical Verification & Multi-Gate Strategy Admission Specification

> **Document ID:** `ACASH-SPEC-STRAT-ADMISSION-v1.1`  
> **Status:** PROPOSED ARCHITECTURE & GOVERNANCE SPECIFICATION — HUMAN APPROVAL PENDING (Phase 17 Rev 5.0)  
> **Parent Governance:** ADR-022 (Market-Adaptive Trading Governance), ADR-023 (Strategy Admission & Bounded Allocation)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Evidence > Belief, Single Canonical Authority)  
> **Date:** 2026-09-05  
> **Version:** 1.1.0 (Phase 17 Master Architecture Audit & Governance Alignment)  

---

> [!IMPORTANT]
> **STRICT GOVERNANCE BOUNDARY & CAPITAL RESTRICTIONS:**
> - **THIS SPECIFICATION IS A DESIGN & GOVERNANCE DOCUMENT ONLY.**
> - **THIS SPECIFICATION DOES NOT AUTHORIZE CODE IMPLEMENTATION.**
> - **THIS SPECIFICATION DOES NOT GRANT LIVE TRADING AUTHORITY.**
> - **THIS SPECIFICATION DOES NOT ALLOCATE LIVE CAPITAL.**
> - **CAPITAL ALLOCATION AUTHORITY REMAINS HARD-LOCKED AT $0.00.**
> - **LIVE BROKER CONNECTION REMAINS STRICTLY DISCONNECTED.**
> - **ZERO RUNTIME MUTATION TO `src/acash/` OR `tests/`.**
> - **PHASE 13 STEP 5 UNATTENDED SOAK (PID 41844) REMAINS ACTIVE AND UNTOUCHED.**

---

## 1. Executive Summary & Epistemic Foundations

This specification establishes the institutional-grade **Strategy Admission Standard** for ACASH. It functions as the non-negotiable sovereign governance gateway that every trading strategy candidate—whether internal quantitative model, external commercial EA, machine learning system, or discretionary rule set—must satisfy before being admitted to the Sovereign Strategy Catalog or evaluated for capital allocation.

### 1.1 The Core Epistemic Identity: Profit $\neq$ Skill $\neq$ Edge $\neq$ Luck-Free
A foundational quantitative tenet of ACASH is that observed profitability is **never** self-authenticating proof of edge:

$$\boxed{\text{Observed Profit} \neq \text{Proven Skill} \neq \text{Structural Edge} \neq \text{Luck-Free Performance}}$$

Observed trading performance is conceptually decomposed into distinct structural and stochastic components:

$$\begin{aligned}
\text{Observed Performance} = &\quad \text{Potential Unexplained Excess Return} \\
&+ \text{Market / Factor Exposure (Beta, Momentum, Carry, Value)} \\
&+ \text{Regime Tailwind (Favorable Market Environment)} \\
&+ \text{Liquidity Economics (Spread Capture, Immediacy Provision)} \\
&+ \text{Risk Premia (Variance, Tail-Risk, Liquidity Risk)} \\
&+ \text{Leverage / Sizing Multipliers} \\
&+ \text{Execution Advantage (Latency, Infrastructure, Fill Quality)} \\
&+ \text{Structural / Microstructure Advantage} \\
&+ \text{Realized Randomness / Luck} \\
&- \text{Transaction Costs, Slippage, Financing Drag, and Implementation Friction}
\end{aligned}$$

> [!NOTE]
> **Epistemic Status of Performance Attribution:**  
> This decomposition represents an **epistemic governance framework**, *not* an exact closed-form accounting identity unless underlying empirical factor and cost estimators are statistically identified and validated. The framework strictly forbids treating unexplained residual return as proven alpha. When an alternative explanation remains plausible, the burden of proof rests entirely on the strategy candidate to reject the alternative explanation empirically.

### 1.2 Five Categorical Sources of Observed Performance
Every candidate's historical returns are categorized across five non-mutually-exclusive sources:
1. **Genuine / Persistent Skill:** Edge that survives repeated independent validation, out-of-sample testing, and cannot be attributed to known factor/regime risks.
2. **Structural Edge:** Repeatable microstructure advantage (liquidity provision economics, queue priority, spread capture, order flow asymmetry, financing differential).
3. **Exposure-Driven Performance:** Returns explained by market beta, momentum, carry, value, volatility premia, or structural leverage.
4. **Regime Tailwind:** Performance generated primarily because the testing window coincided with an exceptionally favorable market environment.
5. **Luck / Sample Anomaly:** Random trade sequencing, clustered wins, multiple-testing selection bias, or small-sample outliers.

---

## 2. Canonical Authority Architecture & Harmonization Mapping

ACASH enforces strict sovereign separation of concerns across its lifecycle layers. Phase 17 operates exclusively as an **admission and governance gateway**; it does not duplicate or usurp the mathematical or operational authorities established in prior or future phases.

### 2.1 Canonical Authority Separation Matrix

| Phase | Canonical Authority Area | Sovereign Responsibilities & Artifacts | Phase 17 Interaction Boundary |
| :--- | :--- | :--- | :--- |
| **Phase 4** | Research Hypothesis Contract | Pre-registered `HypothesisSpecification`, discrete forward returns, Newey-West HAC inference. | **CONSUMES** pre-registered hypothesis contracts; verifies falsification criteria exist. |
| **Phase 5** | Simulation & Execution Reality | Native event-driven simulation, double-entry ledger, `BacktestManifest`, friction waterfall. | **CONSUMES** simulation manifests and drag breakdowns; does not run backtests. |
| **Phase 6** | Statistical Validation Authority | CPCV, Deflated Sharpe Ratio (DSR), MinTRL, PBO, Holm-Bonferroni (FWER), Benjamini-Hochberg (FDR), `SearchTrialLedger`. | **STRICT CONSUMER ONLY.** Consumes canonical `ValidationReport`. Phase 17 **NEVER** recomputes DSR/PBO or redefines $K$. |
| **Phase 8.5** | Alpha Economic Qualification | Canonical `AlphaQualificationDossier`, `AlphaEconomicDecomposition` certifying Net Alpha $> 0$. | **STRICT CONSUMER ONLY.** Consumes sealed Phase 8.5 dossiers. Phase 17 cannot manufacture qualification dossiers. |
| **Phase 11** | Forward Monitoring & Reality Gap | `ForwardTelemetryIngestor`, `ForwardHealthStateMachine`, `StrategyForwardDriftEvidence`, `ExecutionCostEvidence`. | **STRICT CONSUMER ONLY.** Consumes `ForwardHealthState`. Phase 17 **NEVER** replaces or forks Phase 11 monitoring state. |
| **Phase 12** | Venue Execution Adapters | Thin broker IPC, volume quantization, tick-grid alignment, authoritative 6-D reconciliation. | **ISOLATED.** Phase 17 verifies symbol specs (`BrokerSymbolSpec`) but possesses zero broker execution authority. |
| **Phase 13** | Paper Validation & Operational Gates | Forward paper harness, 24-hour unattended soak, 90-day forward paper execution program, Gate A/B. | **CONSUMES** operational execution evidence. Phase 17 admission does not grant Phase 13 Gate B live capital authority. |
| **Phase 14** | AI Quantitative Research Layer | LLM hypothesis assistant, Section 33 research reporting, exploratory feature discovery, causal AST. | **FIREWALL PROTECTED.** AI outputs are strictly `UNVALIDATED_PROPOSAL`. Zero self-admission; zero capital authority. |
| **Phase 17** | Strategy Admission & Lifecycle | Multi-gate admission verification, `StrategyAdmissionStatus`, `StrategyLifecycleState`, bounded allocation limits. | **SOVEREIGN GATEWAY.** Evaluates candidate dossiers against Gates 0–10; manages catalog state transitions. |
| **Phases 18–22** | Tournament, Regime & Allocation | Strategy tournaments (18), regime detection (19), strategy selection (20), allocation solvers (21), portfolio orchestration (22). | **UPSTREAM FOUNDATION.** Phase 17 provides admitted strategy inventory; does not implement solvers or tournaments. |

### 2.2 Phase 15 & 16 Harmonization Statement
In accordance with ADR-023 and the canonical repository roadmap:
- **Phase 15 (Strategy Lifecycle Management):** Formally harmonized into **Phase 17**. Phase 17 is the canonical institutional home for `StrategyLifecycleState`, lifecycle state machines, lifecycle gates, and transition authority.
- **Phase 16 (Performance Degradation & Data Flywheel):** Formally redistributed across **Phase 17** (Gate 9 drift gating), **Phase 11** (runtime telemetry ingestion), **Phase 20** (decision outcome tracking), and **Phase 22** (organizational memory ledger).
- **Rule:** There are **zero** separate implementation milestones for Phase 15 or Phase 16. Their complete requirements remain preserved and traceable within this standard.

### 2.3 Phase 14 AI Proposal Firewall
Phase 14 AI quantitative research proposals entering the Phase 17 pipeline must comply with strict epistemic firewalls:

$$\boxed{\text{AI Output} \equiv \text{UNVALIDATED\_PROPOSAL} \quad\not\equiv\quad \text{Admission Evidence} \quad\not\equiv\quad \text{Trading Authority}}$$

1. **Zero Direct Admission:** No AI component may autonomously transition a candidate into `ADMITTED`, `CONDITIONALLY_ADMITTED`, or `OBSERVE_ONLY`.
2. **Mandatory Full Pipeline Traversal:** An AI-generated hypothesis must traverse the entire canonical pipeline:
   $$\text{Phase 14 Proposal} \longrightarrow \text{Phase 4 Pre-Reg} \longrightarrow \text{Phase 5 Simulation} \longrightarrow \text{Phase 6 Validation} \longrightarrow \text{Phase 8.5 Dossier} \longrightarrow \text{Phase 17 Gate 0}$$
3. **Zero Weight to Subjective AI Confidence:** Model perplexity, LLM self-confidence, synthetic explanations, or multi-agent consensus **never** constitute empirical evidence under any Phase 17 gate.

---

## 3. Orthogonal Three-Plane State Architecture

To eliminate semantic coupling and prevent authority collision, ACASH strictly decouples strategy state into **three independent orthogonal planes**:

$$\boxed{\mathbf{Strategy\ Admission\ Status} \quad\perp\quad \mathbf{Strategy\ Lifecycle\ State} \quad\perp\quad \mathbf{Forward\ Health\ State}}$$

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PLANE 1: STRATEGY ADMISSION STATUS                       │
│                     (Phase 17 Sovereign Governance Plane)                    │
│   [REJECTED] ◄── [OBSERVE_ONLY] ──► [CONDITIONALLY_ADMITTED] ──► [ADMITTED] │
│                          ▲                        │                         │
│                          │                        ▼                         │
│                     [RETIRED] ◄──────────── [SUSPENDED]                     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Cross-Plane Dependency
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PLANE 2: STRATEGY LIFECYCLE STATE                       │
│                      (Phase 17 Lifecycle Engine Plane)                      │
│   [CANDIDATE] ──► [IN_EVALUATION] ──► [GOVERNANCE_REVIEW] ──► [CATALOG_ACTIVE│
│                                                                    │        │
│                         [ARCHIVED] ◄── [CATALOG_SUSPENDED] ◄───────┘        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Cross-Plane Ingestion
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PLANE 3: FORWARD HEALTH STATE                          │
│                   (Phase 11 Forward Monitoring Plane)                       │
│     [INSUFFICIENT_EVIDENCE] ──► [HEALTHY] ──► [DEGRADED] ──► [STRUCTURAL_   │
│                                                   │            BREAK]       │
│                                                   ▼                         │
│                                         [MONITORING_BLOCKED]                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 State Plane Definitions & Single Authority Ownership

#### Plane 1: `StrategyAdmissionStatus` (Sovereign Governance Authority)
- **Single Authority Owner:** Phase 17 Sovereign Admission Committee (Human-Governed).
- **Purpose:** Represents the formal governance verdict on whether a strategy is permitted in the catalog and under what operational envelope.
- **States:**
  - `REJECTED`: Fails one or more mandatory admission gates. Terminal for current spec; cannot receive capital or live execution.
  - `OBSERVE_ONLY`: Permitted for paper tracking and observational monitoring only. Strictly zero capital allocation ($0.00).
  - `CONDITIONALLY_ADMITTED`: Meets core statistical gates; subject to probationary operational constraints (e.g. strict volume cap, single venue).
  - `ADMITTED`: Fully satisfies Gates 0–10. Eligible for portfolio tournament evaluation and bounded capital allocation.
  - `SUSPENDED`: Temporarily halted due to forward health degradation, unexpected drift, or risk event. Reversible upon audit.
  - `RETIRED`: Permanently decommissioned due to structural alpha exhaustion or strategy replacement. Irreversible.

#### Plane 2: `StrategyLifecycleState` (Lifecycle Engine Authority — Harmonized Phase 15)
- **Single Authority Owner:** Phase 17 Strategy Lifecycle State Machine.
- **Purpose:** Tracks mechanical progression through the evaluation, cataloging, and archival pipeline.
- **States:**
  - `CANDIDATE`: Strategy registered with formal specification; evaluation not yet begun.
  - `IN_EVALUATION`: Currently executing Gates 0–9 verification workflows.
  - `GOVERNANCE_REVIEW`: Gates 0–9 passed; awaiting Gate 10 sovereign dossier review and human committee determination.
  - `CATALOG_ACTIVE`: Admitted to catalog; operational in active monitoring or portfolio tournament.
  - `CATALOG_SUSPENDED`: Catalog operations halted pending investigation.
  - `ARCHIVED`: Final immutable state sealed in operational ledger.

#### Plane 3: `ForwardHealthState` (Runtime Monitoring Authority — Canonical Phase 11)
- **Single Authority Owner:** Phase 11 `ForwardHealthStateMachine`.
- **Purpose:** Real-time observational tracking of strategy statistical persistence and execution reality.
- **States:** `INSUFFICIENT_EVIDENCE`, `HEALTHY`, `DEGRADED`, `STRUCTURAL_BREAK`, `MONITORING_BLOCKED`.
- **Rule:** Phase 17 **NEVER** computes, overrides, or mutates `ForwardHealthState`. It ingests this state as an external evidence signal.

### 3.2 Cross-Plane Dependency Matrix & Invariants
1. **Separation Invariant:** A strategy may be `ADMITTED` in Plane 1, `CATALOG_ACTIVE` in Plane 2, while simultaneously transitioning to `DEGRADED` in Plane 3.
2. **Fail-Closed Feedback Loop:**
   - If Plane 3 emits `STRUCTURAL_BREAK` $\implies$ Plane 1 immediately transitions to `SUSPENDED` (deterministic fail-closed rule).
   - If Plane 3 emits `MONITORING_BLOCKED` $\implies$ Plane 1 transitions to `SUSPENDED` (fail-closed on telemetry loss).
3. **Reactivation Invariant:** Reversing `SUSPENDED` back to `ADMITTED` requires Plane 3 returning to `HEALTHY` **plus** formal human committee re-certification.

---

## 4. The 11 Strategy Admission Gates (Gate 0 through Gate 10)

The admission pipeline enforces sequential gate progression. A candidate must satisfy each gate completely before proceeding to the next.

```
Candidate Spec ──► Gate 0 ──► Gate 1 ──► Gate 2 ──► Gate 3 ──► Gate 4
                                                                │
Catalog Admitted ◄── Gate 10 ◄── Gate 9 ◄── Gate 8 ◄── Gate 7 ◄── Gate 6 ◄── Gate 5
```

### Detailed Gate-by-Gate Specification

#### Gate 0 — Strategy Mechanism & Operational Definition
- **Purpose:** Establish unambiguous machine-readable identity, operational mechanics, and structural boundaries.
- **Input Artifacts:** Candidate Strategy Specification (`StrategySpecificationDTO`).
- **Authoritative Source:** Research Author / Strategy Registration Harness.
- **Verification Contract:**
  - Valid `strategy_id` conforming to `STRAT-{TYPE}-{ASSET}-{NAME}-V{SEMVER}`.
  - Declared `StrategyMechanism`: `FORECASTING`, `LIQUIDITY_PROVISION`, `ARBITRAGE`, `CARRY`, `VOLATILITY`, `EXECUTION`, `OTHER_RESEARCH_DEFINED`.
  - Declared `StrategyStyle`: `MOMENTUM`, `MEAN_REVERSION`, `BREAKOUT`, `MARKET_NEUTRAL`, `TREND_FOLLOWING`, `GRID_PROGRESSION`, `OTHER`.
  - Defined instrument universe, timeframe, entry/exit rules, sizing method, `max_positions`, `max_gross_exposure_ratio`.
- **Output Artifact:** Validated `RegisteredStrategyContract`.
- **Pass/Fail Authority:** Phase 17 Gate 0 Contract Validator (Automated).
- **Discipline:** Deterministic fail-closed. Missing parameters or unbounded leverage trigger immediate rejection.

#### Gate 1 — Pre-Registered Economic Mechanism & Falsification Specification
- **Purpose:** Answer *"Why should this strategy have an edge?"* before analyzing return data.
- **Input Artifacts:** Phase 4 Pre-Registration Contract (`HypothesisSpecification`).
- **Authoritative Source:** Phase 4 Alpha Engine.
- **Verification Contract:**
  - Verifiable economic rationale (e.g. behavioral overreaction, liquidity provision premium, institutional execution constraints).
  - Explicit, non-retrospective falsification criteria (e.g. "Net expectancy $< 1.0$ pip over 200 trades falsifies hypothesis").
  - Declared unfavorable market regimes where the strategy is expected to underperform or halt.
- **Output Artifact:** `HypothesisFalsificationRecord`.
- **Pass/Fail Authority:** Phase 17 Governance Review (Automated + Auditor Check).
- **Discipline:** A backtest without a pre-registered falsification hypothesis is strictly rejected.

#### Gate 2 — In-Sample Backtest & Simulation under Realistic Friction
- **Purpose:** Quantify historical return distribution net of realistic market frictions on discovery data.
- **Input Artifacts:** Phase 5 `BacktestManifest`, `SimulationResult`, and shadow ledger audit.
- **Authoritative Source:** Phase 5 Backtest Simulation Substrate.
- **Verification Contract:**
  - Net return accounting for historical spreads, commissions, swaps, and slippage.
  - Newey-West HAC-adjusted Sharpe Ratio estimate and confidence interval.
  - Max Drawdown, Sortino, Calmar, Profit Factor, Expectancy, and CVaR (95%/99%).
  - Zero double-counting verification ($|\text{AccountingResidual}| \le 10^{-10}$).
- **Output Artifact:** `VerifiedBacktestMetricsRecord`.
- **Pass/Fail Authority:** Phase 17 Gate 2 Validator (Automated).
- **Discipline:** Net Profit Factor $\le 1.0$, negative expectancy, or undefined drawdown boundaries fail immediately.

#### Gate 3 — Canonical Statistical Validation & Multiple-Testing Controls
- **Purpose:** Rigorously test out-of-sample persistence and multiple-testing overfitting risk.
- **Input Artifacts:** Phase 6 Canonical `ValidationReport` and `evidence_digest`.
- **Authoritative Source:** **Phase 6 Statistical Validation Engine (Sole Authority).**
- **Verification Contract:**
  - **ZERO RECALCULATION RULE:** Phase 17 reads pre-computed values from Phase 6 `ValidationReport`.
  - Combinatorial Purged Cross-Validation (CPCV) stability and pseudo-OOS path distribution.
  - Deflated Sharpe Ratio (DSR) $\ge 0.95$ under verified trial count $K_{\text{ledger}}$ from sealed `SearchTrialLedger`.
  - Probability of Backtest Overfitting (PBO) $< 0.25$.
  - Minimum Track Record Length (MinTRL) verified against sample size.
  - Multiple testing adjustments (Holm-Bonferroni FWER, Benjamini-Hochberg FDR, Haircut Sharpe).
- **Output Artifact:** `StatisticalValidationAdmissionReceipt`.
- **Pass/Fail Authority:** Phase 17 Gate 3 Automated Verification against Phase 6 Authority.
- **Discipline:** Any candidate failing Phase 6 validation is strictly rejected. Phase 17 cannot grant statistical waivers.

#### Gate 4 — Canonical Stress Testing Matrix
- **Purpose:** Verify strategy survival under acute liquidity, volatility, spread, and structural shocks.
- **Input Artifacts:** Stress Test Run Results across the 12 Canonical Scenarios (Section 5).
- **Authoritative Source:** Phase 5 Stress Engine / Simulation Substrate.
- **Verification Contract:** Evaluation of all 12 scenarios; zero margin exhaustion; adherence to risk boundaries.
- **Output Artifact:** `StressMatrixEvaluationReport`.
- **Pass/Fail Authority:** Phase 17 Stress Matrix Evaluator (Automated).
- **Discipline:** Failure of any mandatory stress scenario triggers rejection or conditional restriction.

#### Gate 5 — Monte Carlo Path & Dependency-Aware Sequence Risk
- **Purpose:** Evaluate drawdown and ruin distributions under trade order randomization.
- **Input Artifacts:** Monte Carlo Resampling Output (Block Bootstrap for autocorrelated series).
- **Authoritative Source:** Phase 6 Robustness Substrate.
- **Verification Contract:**
  - Mandatory dependency check: Plain IID shuffling is forbidden if serial correlation or volatility clustering exists.
  - 95th and 99th percentile maximum drawdown estimation.
  - Mathematical probability of ruin must equal 0.00% under allocation envelope.
- **Output Artifact:** `SequenceRiskEvaluationRecord`.
- **Pass/Fail Authority:** Phase 17 Gate 5 Validator.
- **Discipline:** Probability of ruin $> 0.00\%$ fails closed immediately.

#### Gate 6 — Parameter Robustness, Cliff & Cost Sensitivity Analysis
- **Purpose:** Guard against fragile parameters and evaluate cost-decay boundaries.
- **Input Artifacts:** Multi-dimensional parameter grid evaluations and friction stress decay curves.
- **Authoritative Source:** Phase 6 Parameter Fragility & Curvature Engine.
- **Verification Contract:**
  - Parameter neighborhood sweep ($\pm 10\%, \pm 20\%$).
  - Absence of parameter cliffs (isolated narrow spikes).
  - Cost decay sensitivity: Edge must survive at least $+50\%$ increase in prevailing spread.
- **Output Artifact:** `ParameterRobustnessRecord`.
- **Pass/Fail Authority:** Phase 17 Gate 6 Validator.
- **Discipline:** Parameter fragility or cost collapse triggers rejection.

#### Gate 7 — Alpha Economic Qualification Dossier
- **Purpose:** Verify that net performance represents authentic economic extraction, not uncompensated friction or data artifacts.
- **Input Artifacts:** Canonical `AlphaQualificationDossier` and `AlphaEconomicDecomposition`.
- **Authoritative Source:** **Phase 8.5 Alpha Research & Economic Evidence Engine (Sole Authority).**
- **Verification Contract:**
  - Sealed Phase 8.5 Dossier with cryptographic `dossier_hash`.
  - Economic edge verification: $\text{Net Alpha} = \text{Gross Alpha} - \text{Friction Waterfall} > 0$.
  - Lineage verification to underlying data hashes and hypothesis specification.
- **Output Artifact:** `EconomicQualificationAdmissionReceipt`.
- **Pass/Fail Authority:** Phase 17 Gate 7 Validator.
- **Discipline:** Absence of valid Phase 8.5 dossier blocks admission unconditionally.

#### Gate 8 — Forward Telemetry & Execution Evidence (The Anti-Calendar Rule)
- **Purpose:** Validate operational execution under live/paper market feeds.
- **Input Artifacts:** Phase 13 Forward Execution Records & Phase 11 `ExecutionCostEvidence`.
- **Authoritative Source:** Phase 13 Forward Program & Phase 11 Observational Plane.
- **Verification Contract:**
  - **Strict Anti-Calendar Rule:** Calendar days alone **never** constitute evidence ($\text{90 Calendar Days} \neq \text{Sufficient Evidence}$).
  - Effective Evidence Sample: $N_{\text{eff}} \ge 200$ independent execution observations after adjusting for autocorrelation.
  - Regime diversity: Observed across at least two distinct classified market regimes.
  - Realized broker spread and slippage fidelity verified against simulation assumptions.
- **Output Artifact:** `ForwardExecutionEvidenceRecord`.
- **Pass/Fail Authority:** Phase 17 Gate 8 Validator.
- **Discipline:** Insufficient $N_{\text{eff}}$ or single-regime bias holds candidate in `OBSERVE_ONLY`.

#### Gate 9 — Expected vs Actual Mechanism Drift
- **Purpose:** Confirm that forward execution aligns with research-stage behavior.
- **Input Artifacts:** Phase 11 `StrategyForwardDriftEvidence` and `ForwardHealthState`.
- **Authoritative Source:** **Phase 11 Forward Monitoring & Execution Reality Plane (Sole Authority).**
- **Verification Contract:**
  - Ingestion of current Phase 11 `ForwardHealthState`.
  - Tracking error of forward return distribution vs backtest distribution within statistical bounds.
  - Phase 11 health state must be `HEALTHY`.
- **Output Artifact:** `MechanismDriftAdmissionRecord`.
- **Pass/Fail Authority:** Phase 17 Gate 9 Validator.
- **Discipline:** `ForwardHealthState.DEGRADED` or `STRUCTURAL_BREAK` blocks admission or triggers `SUSPENDED`.

#### Gate 10 — Sovereign Admission Dossier & The 20 Mandatory Questions
- **Purpose:** Comprehensive sovereign review, alternative explanation evaluation, and formal admission determination.
- **Input Artifacts:** Complete Gates 0–9 evidence bundle, Alternative Explanation Register, 20 Written Answers.
- **Authoritative Source:** Phase 17 Sovereign Admission Committee (Human Governance).
- **Verification Contract:**
  - Evaluation of the Alternative Explanation Register (Section 7).
  - Forensic answers to all 20 Mandatory Admission Questions (Section 8).
  - Generation of multi-dimensional `SkillEvidence` vector DTO.
  - Formal committee vote and cryptographic decision signing.
- **Output Artifact:** Sealed `SovereignAdmissionDossier` signed by committee.
- **Pass/Fail Authority:** **Human Sovereign Committee (Mandatory Human Sign-Off).**
- **Discipline:** Zero autonomous self-admission. Admission to `ADMITTED` requires explicit human approval.

---

## 5. Authoritative Stress Testing Matrix (Gate 4)

The 12 canonical stress scenarios represent governance-defined perturbation tests executed via the simulation engine:

| Scenario ID | Scenario Class | Perturbation Applied | Provenance | Calibration Basis | Required Observations | Pass/Fail Semantics | Applicability | Governance Status |
|---|---|---|---|---|---|---|---|---|
| `SCN-VOL-01` | Volatility Spike | Instantaneous 3x ATR expansion over 5 bars | `RESEARCH_DERIVED` | Historical 99th percentile ATR jump in G10 FX | Floating DD, margin consumption, liquidation distance | Ruin prob = 0; Free margin > 30% | All strategies | **MANDATORY** |
| `SCN-VOL-02` | Volatility Compression | ATR drops to < 10th percentile for 30 days | `RESEARCH_DERIVED` | Historical summer holiday range compression | Opportunity cost, stale carrying costs | No runaway grid expansion; zero invalid exits | Breakout / Trend | **MANDATORY** |
| `SCN-SPR-01` | Spread Widening | 5x normal spread expansion at entry/exit | `BROKER_OBSERVED` | MetaQuotes MT5 roll-over hour (21:00–22:00 UTC) logs | Realized net P/L, slippage drag | Expectancy $\ge 0$ under 2x spread | All strategies | **MANDATORY** |
| `SCN-GAP-01` | Weekend / Session Gap | 200 bps price gap through Stop Loss | `HISTORICAL_EMPIRICAL` | Historical weekend election/geopolitical gaps | Gap slippage loss, negative balance risk | Max loss strictly $\le$ Risk Budget ceiling | All strategies | **MANDATORY** |
| `SCN-LIQ-01` | Liquidity Vacuum | Order book depth drops 80%; partial fills | `BROKER_OBSERVED` | Thin holiday session book depth telemetry | Unfilled leg risk, basket desynchronization | No orphan legs; execution fails closed | Multi-leg / Arbitrage | **MANDATORY** |
| `SCN-LAT-01` | Execution Delay Spike | 500 ms roundtrip broker latency injected | `BROKER_OBSERVED` | Cross-region network congestion tail | Adverse fill slippage, stale signal execution | Fails closed on quote expiration | Scalping / Microstructure | **MANDATORY** |
| `SCN-TRN-01` | Persistent Adverse Trend | 5-sigma monotonic trend without pullbacks | `RESEARCH_DERIVED` | Historical SNB 2015 / Brexit multi-sigma moves | Max basket exposure, margin exhaustion | Basket resolves within exposure ceiling or halts | Grid / Mean-Reversion | **MANDATORY** |
| `SCN-COR-01` | Correlation Breakdown | Pair correlation flips from +0.8 to -0.8 | `HISTORICAL_EMPIRICAL` | Regime-switch correlation breakdown in crisis | Net portfolio directional exposure | Portfolio gross exposure strictly bounded | Multi-asset / Pair Arb | **MANDATORY** |
| `SCN-EVT-01` | High-Impact News Shock | 100 bps dislocation in < 1 second | `HISTORICAL_EMPIRICAL` | High-impact economic release tick feed logs | Slippage, stop execution price, spread spike | Adheres to Event Policy (Hold, Halt, Flatten)| All strategies | **MANDATORY** |
| `SCN-BRK-01` | Structural Regime Break | Return shifts negative; volatility doubles | `RESEARCH_DERIVED` | Out-of-sample monetary policy shifts | Expected-vs-actual drift, downgrade trigger | Strategy trips Gate 9 drift within $N$ bars | All strategies | **MANDATORY** |
| `SCN-SWP-01` | Financing Drag (Swap) | Triple swap / adverse interest rate diff | `GOVERNANCE_DEFINED` | Conservative financing rate stress model | Long-term holding cost erosion | Net expectancy positive after 60-day hold | Swing / Long-duration | RESEARCH_ONLY |
| `SCN-REC-01` | Recovery Trap Excursion | Sustained underwater float near liquidation | `RESEARCH_DERIVED` | Historical near-death recovery trajectories | Drawdown duration, near-death exposure | No unhedged infinite recovery assumption | Grid / Averaging | **MANDATORY** |

---

## 6. Forward Telemetry, Paper Evidence & The Anti-Calendar Rule (Gate 8)

Gate 8 establishes the bridge between theoretical backtesting and empirical forward execution:

### 6.1 The Anti-Calendar Axiom
$$\boxed{\text{Calendar Elapsed Time (e.g. 90 Days)} \not\equiv \text{Statistical Forward Evidence}}$$

- 90 calendar days containing 5 trades during an uncharacteristically quiet regime provides **zero** statistical certainty of edge.
- 30 calendar days containing 400 execution observations across trending, high-volatility, and news-event regimes provides substantive operational evidence.

### 6.2 The Effective Evidence Sample Metric ($N_{\text{eff}}$)
To prevent clustered or autocorrelated signals from exaggerating sample significance, sample size is adjusted:

$$N_{\text{eff}} = \frac{N_{\text{raw}}}{1 + 2 \sum_{k=1}^{K} \rho_k}$$

where $\rho_k$ is the empirical autocorrelation of trade returns at lag $k$, truncated when $\rho_k$ drops below statistical noise.

### 6.3 Regime Coverage Requirement
A strategy candidate must be evaluated across a minimum of **two distinct classified market regimes** (e.g. Low Volatility Mean-Reverting AND High Volatility Trend) before Gate 8 certification is possible.

---

## 7. The Alternative Explanation Register (Gate 10)

Every strategy candidate must maintain an explicit counter-hypothesis register. Unconditional admission is prohibited if any critical alternative explanation remains unresolved:

| Explanation ID | Counter-Hypothesis | Evaluation Scope | Permitted Status Values |
|---|---|---|---|
| `ALT-01` | **Market Beta Drift** | Returns explained by broad market index drift rather than strategy selection logic. | `PLAUSIBLE`, `TESTED_REJECTED`, `SUPPORTED`, `INSUFFICIENT_DATA`, `UNTESTED` |
| `ALT-02` | **Short Volatility Premia** | Returns are merely compensation for unhedged catastrophe / tail-risk exposure. | `PLAUSIBLE`, `TESTED_REJECTED`, `SUPPORTED`, `INSUFFICIENT_DATA`, `UNTESTED` |
| `ALT-03` | **Regime Tailwind** | Performance was generated exclusively by an abnormal, non-repeating favorable market state. | `PLAUSIBLE`, `TESTED_REJECTED`, `SUPPORTED`, `INSUFFICIENT_DATA`, `UNTESTED` |
| `ALT-04` | **Selection / Data Mining Bias** | Strategy was selected as the lucky winner among hundreds of evaluated unrecorded variants. | `PLAUSIBLE`, `TESTED_REJECTED`, `SUPPORTED`, `INSUFFICIENT_DATA`, `UNTESTED` |
| `ALT-05` | **Execution Fantasy** | Profitability depends strictly on zero slippage or unrealistic order-queue fill priority. | `PLAUSIBLE`, `TESTED_REJECTED`, `SUPPORTED`, `INSUFFICIENT_DATA`, `UNTESTED` |
| `ALT-06` | **Asymmetric Recovery / Averaging** | Strategy hides risk via unclosed floating drawdown, grid martingale, or infinite recovery. | `PLAUSIBLE`, `TESTED_REJECTED`, `SUPPORTED`, `INSUFFICIENT_DATA`, `UNTESTED` |

> [!CAUTION]
> If any alternative explanation (`ALT-01` through `ALT-06`) is classified as `SUPPORTED`, or remains `PLAUSIBLE` without compensatory risk constraints, `StrategyAdmissionStatus.ADMITTED` is **strictly prohibited**.

---

## 8. The 20 Mandatory Admission Questions (Gate 10)

The final Gate 10 sovereign dossier must include formal, forensic written answers to all 20 questions:

1. What is the economic, statistical, or microstructure mechanism generating the return?
2. Under which specific market states and regimes is the strategy expected to generate positive excess return?
3. Under which specific market states and regimes is the strategy expected to suffer losses or decay?
4. What systematic market, factor, or alternative risk premia exposures does the strategy carry?
5. Does the strategy demonstrate positive net expectancy after accounting for realistic spreads, commissions, slippage, and financing costs?
6. Does the empirical edge persist in out-of-sample testing outside the discovery dataset?
7. Does the edge persist across multiple walk-forward or temporal validation windows?
8. Does historical profitability depend predominantly on a single regime or isolated historical episode?
9. Could the observed performance plausibly be explained by randomness, trade sequencing, or luck?
10. What is the effective sample size ($N_{\text{eff}}$) after accounting for autocorrelation and position clustering?
11. How many strategy variants, indicators, and parameter permutations were evaluated before discovering this candidate ($K$)?
12. Is the candidate vulnerable to multiple testing bias, selection bias, or data snooping?
13. How much of the net performance is attributable to execution quality, speed, or broker microstructure?
14. What are the quantified risk consequences under the 12 canonical stress testing scenarios?
15. What is the maximum drawdown and ruin probability under adverse trade sequencing via Monte Carlo simulation?
16. What plausible alternative explanations in the Alternative Explanation Register remain unresolved?
17. What observable empirical evidence would conclusively falsify the strategy's core hypothesis?
18. What observable monitoring conditions would trigger immediate strategy suspension or de-allocation?
19. What critical data, regime observations, or execution telemetry are currently missing or unverified?
20. **[MANDATORY GOVERNANCE QUESTION] Why should this strategy NOT receive additional capital or operational risk at this time?**

---

## 9. Sovereign Admission Dossier & Decision Framework

### 9.1 Multi-Dimensional Evidence Vector (Strict Rejection of Scalar Scores)
ACASH strictly forbids composite scalar scores (e.g. `score = 82/100`). Candidate quality is expressed via the multi-dimensional **`SkillEvidence`** vector DTO using `EvidenceSupportLevel` (`SUPPORTED`, `WEAK`, `INCONCLUSIVE`, `NOT_TESTED`, `FAILED`, `NOT_APPLICABLE`):

```python
class SkillEvidence(BaseModel):
    out_of_sample_support: EvidenceSupportLevel
    walk_forward_support: EvidenceSupportLevel
    regime_coverage_support: EvidenceSupportLevel
    execution_realism_support: EvidenceSupportLevel
    robustness_support: EvidenceSupportLevel
    attribution_support: EvidenceSupportLevel
    persistence_support: EvidenceSupportLevel
    sample_quality_support: EvidenceSupportLevel
    unresolved_alternatives_count: int
    statistical_confidence: Decimal
```

### 9.2 State Transition Authority Matrix
All state transitions across Plane 1 (`StrategyAdmissionStatus`) and Plane 2 (`StrategyLifecycleState`) are bound to explicit governance authorities:

| Target Transition | Required Preconditions | Authorized Actor | Verification Standard |
| :--- | :--- | :--- | :--- |
| `CANDIDATE` $\to$ `IN_EVALUATION` | Gate 0 passed; machine-readable spec registered. | Automated Pipeline | Deterministic contract check |
| `IN_EVALUATION` $\to$ `GOVERNANCE_REVIEW` | Gates 0–9 fully certified; evidence artifacts sealed. | Automated Pipeline | Cryptographic digest verification |
| `GOVERNANCE_REVIEW` $\to$ `ADMITTED` | Gate 10 dossier complete; all 20 questions answered; zero critical alternatives unresolved. | **Human Sovereign Committee** | **Mandatory Human Sign-Off** |
| `GOVERNANCE_REVIEW` $\to$ `CONDITIONALLY_ADMITTED` | Gates 0–9 passed; minor operational restriction required (e.g. volume cap). | **Human Sovereign Committee** | **Mandatory Human Sign-Off** |
| `GOVERNANCE_REVIEW` $\to$ `OBSERVE_ONLY` | Insufficient $N_{\text{eff}}$ or single-regime coverage; forward tracking required. | **Human Sovereign Committee** | Human Auditor Review |
| Any $\to$ `REJECTED` | Failure of any mandatory gate (Gates 0–9) or committee rejection at Gate 10. | Automated Validator / Committee | Fail-Closed / Committee Vote |
| `ADMITTED` $\to$ `SUSPENDED` | Phase 11 `STRUCTURAL_BREAK` or `MONITORING_BLOCKED`; risk ceiling breach; unexpected drift. | **Deterministic Fail-Closed Engine** OR Human Auditor | **Automatic / Immediate** |
| `SUSPENDED` $\to$ `ADMITTED` | Root cause resolved; Phase 11 returns to `HEALTHY`; full audit completed. | **Human Sovereign Committee** | **Mandatory Human Sign-Off** |
| Any $\to$ `RETIRED` | Permanent alpha exhaustion; strategy replacement; persistent structural decay. | **Human Sovereign Committee** | **Mandatory Human Sign-Off** |
| Any $\to$ `ARCHIVED` | Final administrative closeout and sealing into operational ledger. | Automated Ledger Pipeline | Chained SHA-256 Ledger Event |

### 9.3 Revocation, Suspension & Retirement Semantics

ACASH strictly distinguishes the operational semantics of non-active states:

- **`SUSPENDED` (Reversible Operational Halt):**
  - Triggered automatically when Phase 11 emits `ForwardHealthState.STRUCTURAL_BREAK`, when telemetry fails, or when a risk envelope is violated.
  - Operational impact: Strategy execution is halted immediately; open positions are managed according to risk policy; allocation budget is set to `$0.00`.
  - Reversibility: Reversible only after formal root-cause analysis, Phase 11 returning to `HEALTHY`, and human committee sign-off.
- **`REJECTED` (Evaluation Disqualification):**
  - Occurs when a candidate fails any mandatory gate (Gates 0–9) or is rejected by committee at Gate 10.
  - Operational impact: Candidate is barred from catalog entry. Current specification is sealed as failed.
  - Reversibility: Irreversible for the specific candidate specification. Resubmission requires registering a new hypothesis specification.
- **`RETIRED` (Permanent Alpha Decommissioning):**
  - Occurs when an admitted strategy suffers irreversible alpha decay, regime obsolescence, or is formally replaced.
  - Operational impact: Strategy is permanently removed from tournament eligibility and allocation catalogs.
  - Reversibility: **Strictly irreversible.**
- **`ARCHIVED` (Historical Provenance Sealing):**
  - Terminal state where the entire strategy lifecycle record, decisions, and telemetry are immutably sealed in the operational ledger.

---

## 10. Capital Allocation Boundary & Bounded Exposure Rules

The boundary between strategy admission and capital allocation is absolute and non-negotiable:

$$\boxed{\text{Strategy Admission (Phase 17)} \quad\not\equiv\quad \text{Capital Authorization (Phase 13 Gate B / Phase 21)}}$$

1. **The Zero-Capital Invariant:**  
   $$\boxed{\mathbf{Allocation = \$0.00} \quad \text{is always valid, sovereign, and the system default.}}$$
   - Admission to the Sovereign Strategy Catalog confers **zero** inherent rights to live capital.
   - A strategy may reside in `ADMITTED` status indefinitely with an active allocation of exactly `$0.00`.
2. **Decoupling from Broker Execution:**  
   - Phase 17 does not possess interfaces to submit orders, modify broker positions, or toggle live execution flags.
   - Live capital deployment is governed exclusively by **Phase 13 Gate B (Mandatory Human Sign-Off)**.
3. **Bounded Allocation Contracts:**  
   - Any future allocation policy (Phase 21) operating on admitted strategies must enforce hard bounding envelopes: `max_capital_allocation_usd`, `max_leverage_ratio`, `max_drawdown_budget_usd`, and `max_daily_loss_usd`.

---

## 11. Threshold Provenance & Classification Taxonomy

To uphold `AGENTS.md` epistemic integrity, every numerical threshold in this specification is explicitly classified:

| Threshold Expression | Location | Classification | Owning Authority / Provenance Basis | Epistemic Status |
| :--- | :--- | :--- | :--- | :--- |
| $\text{DSR} \ge 0.95$ | Gate 3 | **Class A: Canonical ACASH Threshold** | Phase 6 Statistical Contract (`deflated_sharpe.py`) | Canonical Literature Standard (Bailey & López de Prado 2014) |
| $\text{PBO} < 0.25$ | Gate 3 | **Class A: Canonical ACASH Threshold** | Phase 6 Overfitting Contract (`overfitting.py`) | Canonical Literature Standard (Bailey et al. 2016) |
| $\text{Ruin Probability} = 0.00\%$ | Gate 5 | **Class A: Canonical ACASH Threshold** | Phase 1/9 Risk Axiom (`AGENTS.md`) | Mathematical Invariant under bounded sizing |
| $\text{Accounting Residual} \le 10^{-10}$ | Gate 2 | **Class A: Canonical ACASH Threshold** | Phase 5 Double-Entry Shadow Ledger Contract | Exact Numerical Accounting Invariant |
| $\text{Allocation} = \$0.00$ | General | **Class A: Canonical ACASH Threshold** | ADR-023 / Project-Wide Capital Governance | Sovereign Fail-Closed Default |
| $\text{WFE} \ge 0.50$ | Gate 3 | **Class B: Governance-Defined Threshold** | Phase 17 Governance Standard (ADR-023) | Institutional Policy Threshold |
| $\text{OOS Degradation} \le 50\%$ | Gate 3 | **Class B: Governance-Defined Threshold** | Phase 17 Governance Standard (ADR-023) | Institutional Policy Threshold |
| $N_{\text{eff}} \ge 200$ | Gate 8 | **Class B: Governance-Defined Threshold** | Phase 17 Effective Evidence Standard (ADR-023) | Sample Size Governance Ceiling |
| $\text{Spread Sensitivity} \ge +50\%$ | Gate 6 | **Class B: Governance-Defined Threshold** | Phase 17 Robustness Policy (ADR-023) | Cost Margin Safety Policy |
| $\text{Regime Diversity} \ge 2$ | Gate 8 | **Class B: Governance-Defined Threshold** | Phase 17 Regime Coverage Policy (ADR-023) | Environmental Robustness Policy |
| $\text{Parameter Sweep} \pm 10\%, \pm 20\%$| Gate 6 | **Class C: Research Heuristic** | Quantitative Research Best Practice | Sensitivity Screening Heuristic |
| 12 Stress Matrix Perturbations | Gate 4 | **Class C: Research Heuristic** | Historical FX / Market Microstructure Events | Empirical Stress Calibration |
| 60-Day Swap Holding Window | Gate 4 | **Class D: Illustrative Threshold** | Long-Duration Carry Stress Example | Illustrative Governance Scenario |

- **Class A:** Enforced by sealed upstream codebase contracts. Non-modifiable by Phase 17.
- **Class B:** Established by formal ACASH institutional governance (ADR-022/ADR-023). Modifiable only via formal ADR amendment.
- **Class C:** Empirical research heuristics calibrated to historical market microstructure.
- **Class D:** Illustrative examples for scenario modeling; not universal mathematical absolutes.

---

## 12. Mandatory Scientific Language & Epistemic Rules

All documentation, evaluation reports, and generated research dossiers must adhere strictly to institutional epistemic language:

| Prohibited Unverified Claims | Mandatory Epistemic Formulations |
| :--- | :--- |
| ❌ *"Strategy proved skill"* | ✅ *"Evidence is supportive of persistent excess return under tested conditions"* |
| ❌ *"Strategy proved alpha"* | ✅ *"Observed performance is consistent with the stated economic mechanism"* |
| ❌ *"Luck was completely eliminated"* | ✅ *"Performance remains statistically distinguishable from null under tested trade reshuffling"* |
| ❌ *"Regime X caused the returns"* | ✅ *"Conditional performance is significantly stronger under Regime X"* |
| ❌ *"Backtest guarantees execution"* | ✅ *"Simulated research performance under stated transaction cost assumptions"* |
| ❌ *"Strategy is certified safe"* | ✅ *"Strategy satisfied Gate 0–10 evidence criteria under bounded risk envelopes"* |

---

## 13. Future Phase Boundaries (Phases 18–23)

To ensure modular monolith decoupling, Phase 17 explicitly defines its boundaries with subsequent phases:

- **Phase 18 (Strategy Research & Tournament Pipeline):** Phase 18 manages automated hypothesis evaluation and relative ranking tournaments across multiple strategies. Phase 17 provides the admission standard that every tournament entrant must satisfy; Phase 17 does not execute tournaments.
- **Phase 19 (Empirical Regime Detection Engine):** Phase 19 provides empirical, online classification of market regimes (trend, volatility, liquidity). Phase 17 consumes regime tags for Gates 4 and 8; Phase 17 does not build regime estimation models.
- **Phase 20 (Regime × Strategy Selection & Decision Engine):** Phase 20 matches admitted strategies to detected regimes in real time. Phase 17 determines strategy eligibility; Phase 20 executes dynamic runtime selection.
- **Phase 21 (Risk-Based Capital Allocation Solvers):** Phase 21 implements production mathematical optimization solvers (Equal Risk Contribution, Volatility Targeting). Phase 17 establishes bounded allocation limits; Phase 21 solves capital weights.
- **Phase 22 (Portfolio / Multi-Strategy Orchestration & Memory Flywheel):** Phase 22 handles multi-strategy execution netting and organizational memory ledgers.
- **Phase 23 (Adaptive Multi-Horizon Strategy Architecture):** Architectural record establishing strategy-agnostic multi-horizon principles (ADR-024/ADR-025).

---

## 14. Implementation Constraints & Acceptance Criteria (For Future Implementation Phase)

When implementation of Phase 17 is formally authorized by the Human Auditor, the engineering team must satisfy the following constraints:

### 14.1 Engineering & Architecture Constraints
1. **Directory Isolation:** Core domain logic must reside in `src/acash/admission/` (or `src/acash/governance/admission/`). Zero modification to existing sealed modules (`src/acash/validation/`, `src/acash/execution/`, `src/acash/monitoring/`).
2. **Immutable Domain DTOs:** All state entities, evidence vectors, and admission records must be frozen, immutable Pydantic v2 models or dataclasses.
3. **Deterministic Verification:** Automated gate evaluations (Gates 0–9) must be 100% deterministic and reproducible given identical input artifacts.
4. **Cryptographic Lineage:** Every `SovereignAdmissionDossier` must seal the `sha256` digests of:
   - Candidate `HypothesisSpecification`
   - Phase 5 `BacktestManifest`
   - Phase 6 `ValidationReport` (`evidence_digest`)
   - Phase 8.5 `AlphaQualificationDossier` (`dossier_hash`)
   - Committee Decision Record
5. **Strict Typing:** 100% clean under `mypy --strict`.

### 14.2 Acceptance Criteria for Implementation Authorization
- [ ] Complete unit test suite verifying all state transitions across Plane 1, Plane 2, and Plane 3.
- [ ] Adversarial test vectors verifying immediate fail-closed behavior upon `STRUCTURAL_BREAK` or invalid Phase 6 digests.
- [ ] Cryptographic lineage tests verifying that tampering with any upstream artifact breaks admission verification.
- [ ] Full integration test traversing candidate registration through Gate 10 sovereign dossier generation with `$0.00` capital ceiling.

---

## 15. Authoritative Academic & Empirical Grounding

1. **Barber, Lee, Liu, & Odean (2014):** *The Cross-Section of Speculator Skill: Evidence from Day Trading.* Proves that while the vast majority of active traders lose net of costs, a small persistent upper tail exists; crucially, luck explains a substantial fraction of top performers' short-term returns.
2. **Berk & van Binsbergen (2015):** *Measuring Skill in the Mutual Fund Industry.* Proves managerial skill exists when measured as gross value extraction, but investor net returns depend entirely on cost and fee drag.
3. **Bailey, Borwein, López de Prado, & Zhu (2016):** *The Probability of Backtest Overfitting.* Establishes the mathematical formulation of PBO via Combinatorial Symmetric Cross-Validation (CSCV).
4. **Bailey & López de Prado (2014):** *The Deflated Sharpe Ratio.* Corrects for multiple testing, non-normality, and sample length in performance evaluation.
5. **Market Microstructure Literature (Glosten-Milgrom 1985, Kyle 1985, Amihud 2002):** Establishes that liquidity-providing and market-making strategies derive edge from spread capture and adverse-selection management—fundamentally distinct from directional forecasting.
6. **MetaTrader 5 MqlRates Technical Architecture:** Proves that MetaQuotes explicitly decouples `tick_volume` (quote ticks) from `real_volume` (exchange traded lots) and instantaneous `spread`, validating ACASH's strict volume provenance contracts.

---

## 16. Governance Sign-Off & Provenance Block

```text
================================================================================
ACASH STRATEGY ADMISSION STANDARD (PHASE 17) — SPECIFICATION PROVENANCE
================================================================================
Specification Document: docs/architecture/strategy_admission_standard.md
Document Revision     : Phase 17 Rev 5.0 (v1.1.0)
Current Status        : PROPOSED / HUMAN APPROVAL PENDING
Parent ADRs           : ADR-022, ADR-023
Authoritative Standard: AGENTS.md

Authority Invariants:
  [x] Phase 6 Statistical Authority Preserved (Strict Consumer Only)
  [x] Phase 8.5 Economic Qualification Authority Preserved (Strict Consumer Only)
  [x] Phase 11 Forward Monitoring Authority Preserved (Strict Consumer Only)
  [x] Phase 13 Paper / Forward Execution Authority Preserved (Zero Capital Override)
  [x] Phase 14 AI Proposal Firewall Preserved (AI != Evidence, AI != Authority)
  [x] Live Capital Authority Hard-Locked at $0.00
  [x] Live Orders Emitted: 0 | Broker Wire: DISCONNECTED

Harmonization Record:
  [x] Phase 15 (Strategy Lifecycle Management) Harmonized into Phase 17
  [x] Phase 16 (Performance Degradation) Harmonized into Phase 17–22 Sequence

Implementation Status:
  [x] Implementation is STRICTLY LOCKED / NOT AUTHORIZED
  [x] Zero Runtime Code Committed
================================================================================
```
