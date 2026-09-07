# ACASH Phase 14: Master Research Architecture & Human Approval Readiness Review

> **Document ID:** `docs/phase14/phase14_human_approval_readiness_review.md`  
> **Status:** ARCHITECTURAL READINESS AUDIT — PREPARED FOR HUMAN GOVERNANCE REVIEW  
> **Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Single Canonical Authority, Literature Alignment), Phase 14 Master Architecture (`docs/phase14/phase14_master_research_architecture_plan.md` Rev 1.2), Phase 14 Governance Spec (`docs/phase14/phase14_architecture_and_governance_plan.md` v1.0)  
> **Date:** 2026-09-07  
> **Operating State:** System = `RESEARCH STANDING BY` | Live Capital = `$0.00` (Hard-Locked) | Trading = `LOCKED` | `HYP_003` = `NOT CREATED`  

---

> [!IMPORTANT]
> ### PURPOSE OF THIS REVIEW
> This document audits the two existing Phase 14 architectural specifications to prepare them for formal **Human Governance Approval**.  
> In accordance with `AGENTS.md` Rule 15 & Rule 18:
> - **AN AI AGENT CANNOT SELF-APPROVE ITS OWN ARCHITECTURE OR AUTHORIZE ITS OWN IMPLEMENTATION.**
> - **PLAN APPROVAL $\neq$ IMPLEMENTATION APPROVAL $\mid$ DESIGN SPECIFICATION $\neq$ CODE MUTATION.**
> - **ZERO RUNTIME CODE IS IMPLEMENTED OR MODIFIED UNDER THIS AUDIT.**
> - **ZERO CAPITAL ALLOCATION AUTHORITY (STRICTLY HARD-LOCKED AT $0.00).**
> - **ZERO ACCESS TO BROKER WIRES OR LIVE EXECUTION INFRASTRUCTURE.**

---

## 1. What Exact Problem Phase 14 Solves

In traditional or undisciplined quantitative research, researchers and AI assistants suffer from three catastrophic failure modes:
1. **The LLM Strategy Hallucination Trap:** LLMs generate plausible-sounding "trading strategies" that are either mathematically malformed, contain temporal lookahead bias ($t_{\text{feature}} > T_{\text{decision}}$), or rely on arbitrary parameter curve-fitting.
2. **The Multiple-Testing Concealment Problem:** Researchers test dozens or hundreds of prompt variations, indicators, and timeframes, reporting only the single lucky backtest without recording the trial count $K$, causing massive selection bias and false alpha discovery.
3. **The Governance Seam:** External backtest tools (VectorBT, TradingView, MT5) produce unverified screenshots or CSV files that are mistaken for canonical quantitative evidence.

**Phase 14 solves this by establishing a mathematically and epistemically bounded AI Quantitative Research Layer (`acash.research.ai`).**  
It transforms AI from an undisciplined "code generator" into an evidence-bound research assistant whose outputs are strictly typed, causally verified, cryptographically audited, and fail-closed.

---

## 2. What Phase 14 Is Allowed to Do (Authorized Scope)

Phase 14 is authorized strictly for **pre-hypothesis exploratory research intelligence and post-validation reporting**:

1. **Ingest External Literature & Unverified Claims:**
   - Ingest academic papers, exchange whitepapers, transcripts, and external candidate claims.
   - Attach immutable, tri-axial epistemic metadata (`source_type`, `verification_status`, `evidence_role`).
2. **Formulate Structured Research Proposals:**
   - Produce strictly-typed `AIHypothesisProposal` objects (target symbol, features, economic rationale, target horizon, invalidation conditions).
   - Ensure every proposal is explicitly stamped with `proposal_status: Final[str] = "UNVALIDATED_PROPOSAL"`.
3. **Explore Symbolic Feature Transformations:**
   - Suggest mathematical transformations of microstructure variables (e.g. order-flow imbalances, volatility ratios).
   - Inspect expressions with an Abstract Syntax Tree (`CausalAstValidator`) to enforce point-in-time causality ($t \le T$).
4. **Generate Institutional Research Reports (Section 33 Compliance):**
   - Synthesize formal audit dossiers from sealed, immutable artifacts (`HypothesisSpecification`, `SearchTrialLedger`, `ValidationReport`, `AlphaQualificationDossier`).
   - Cross-check every numerical assertion with an `EvidenceGroundingVerifier` that rejects the report fail-closed if any number deviates from sealed evidence.
5. **Record Negative Research Knowledge:**
   - Classify and preserve failed hypotheses in a semantic graph (`FAILED_UNDER_COSTS`, `FAILED_UNDER_OOS`, `INVALIDATED_BY_DSR`) to prevent circular re-invention.

---

## 3. What Phase 14 Is Absolutely Forbidden to Do (Strict Non-Ownership Boundaries)

Phase 14 has **ZERO AUTHORITY** to perform any of the following actions:

$$\begin{array}{rll}
\mathbf{F-1:} & \text{\bfseries NO Self-Registration of Hypotheses} & \text{Cannot register a } \texttt{HypothesisSpecification}\text{ directly. Human/sovereign approval required.} \\
\mathbf{F-2:} & \text{\bfseries NO Backtest Execution Authority} & \text{Cannot simulate returns or compute PnL. Only Phase 5 }\texttt{BacktestEngine}\text{ executes backtests.} \\
\mathbf{F-3:} & \text{\bfseries NO Statistical Gate Authority} & \text{Cannot compute canonical DSR, PBO, or FWER. Only Phase 6 }\texttt{ValidationGate}\text{ has authority.} \\
\mathbf{F-4:} & \text{\bfseries NO Alpha Qualification Authority} & \text{Cannot emit an }\texttt{AlphaQualificationDossier}\text{. Only Phase 8.5 emits dossiers.} \\
\mathbf{F-5:} & \text{\bfseries NO Broker or Wire Connectivity} & \text{Strictly zero imports of }\texttt{acash.execution}\text{, MetaTrader 5, sockets, or HTTP execution wires.} \\
\mathbf{F-6:} & \text{\bfseries NO Capital Allocation Authority} & \text{Capital authority is hard-locked at \$0.00. Cannot allocate or risk funds.} \\
\mathbf{F-7:} & \text{\bfseries NO Quarantine Partition Access} & \text{Cannot read, inspect, or partition quarantined datasets (e.g. 2026 M5 holdout).} \\
\mathbf{F-8:} & \text{\bfseries NO Evidence Mutation} & \text{Cannot modify, rewrite, or delete historical ledgers, manifests, or test outputs.}
\end{array}$$

---

## 4. How Phase 14 Integrates with `ResearchReInceptionGate`

The integration between Phase 14 and the canonical research pipeline is sequential, directional, and fail-closed:

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. EXTERNAL INTAKE & LITERATURE                             │
│    - External Claim / Academic Paper / Microstructure Idea  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. PHASE 14 RESEARCH INTELLIGENCE                           │
│    - Candidate Intake Note & Mechanism Review               │
│    - Epistemic Classification (UNVERIFIED / REPORTED)       │
│    - Status: UNVALIDATED_PROPOSAL                           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼ [HUMAN GOVERNANCE REVIEW]
┌─────────────────────────────────────────────────────────────┐
│ 3. HUMAN QUANT DECISION                                     │
│    - Human auditor explicitly approves candidate concept    │
│    - Closes specification gaps from first principles        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. RESEARCH RE-INCEPTION GATE (src/acash/research/reincept) │
│    - Asserts candidate is NOT in TERMINAL_HYPOTHESIS_REGIST │
│    - Enforces Cross-Hypothesis Data Quarantine (Disjoint)   │
│    - Enforces fail-closed validation of proposed window     │
└──────────────────────────────┬──────────────────────────────┘
                               │ [Passes Gate]
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. STEP R1 FORMAL PRE-REGISTRATION                          │
│    - Creates sealed HypothesisSpecification (e.g. HYP_003)  │
│    - Cryptographic hash sealed into execution manifest      │
└─────────────────────────────────────────────────────────────┘
```

**Key Invariant:** Phase 14 proposals **CANNOT bypass** the `ResearchReInceptionGate`. Any attempt to register a proposal on quarantined data or with duplicate lineage is blocked fail-closed.

---

## 5. How AI Outputs Remain `UNVALIDATED PROPOSALS`

To prevent AI-generated ideas from being mistaken for validated alpha, Phase 14 enforces strict type-level and semantic boundaries:
1. **Immutable Model Status:** The DTO `AIHypothesisProposal` contains a frozen field:
   ```python
   proposal_status: Final[str] = "UNVALIDATED_PROPOSAL"
   ```
2. **Type Incompatibility:** An `AIHypothesisProposal` cannot be consumed by Phase 5 `BacktestEngine` or Phase 6 `ValidationGate`. To become an empirical experiment, it must be explicitly translated into a `HypothesisSpecification` via human or sovereign gate conversion.
3. **Zero Authority Marker:** Every AI proposal includes an immutable disclaimer stating that the hypothesis has zero empirical standing and zero trading authority.

---

## 6. Provenance & Epistemic Evidence Classification

Phase 14 implements a **Tri-Axial Separation** of source metadata to prevent marketing claims from masquerading as verified facts:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   TRI-AXIAL EPISTEMIC TAXONOMY                         │
├───────────────────┬────────────────────────────┬───────────────────────┤
│ Axis              │ Allowable Values           │ Purpose               │
├───────────────────┼────────────────────────────┼───────────────────────┤
│ source_type       │ ACADEMIC, BLOG, GITHUB,    │ Classifies the media  │
│                   │ VENDOR, COURSE, SOCIAL,    │ and origin channel.   │
│                   │ DATASET                    │                       │
├───────────────────┼────────────────────────────┼───────────────────────┤
│ verification_state│ UNVERIFIED,                │ Tracks independent    │
│                   │ PARTIALLY_VERIFIED,        │ empirical validation. │
│                   │ REPRODUCED,                │                       │
│                   │ INDEPENDENTLY_VALIDATED    │                       │
├───────────────────┼────────────────────────────┼───────────────────────┤
│ evidence_role     │ BACKGROUND,                │ Defines the epistemic │
│                   │ HYPOTHESIS_SOURCE,         │ function in research. │
│                   │ METHOD_REFERENCE,          │                       │
│                   │ EMPIRICAL_EVIDENCE         │                       │
└───────────────────┴────────────────────────────┴───────────────────────┘
```

Furthermore, every AI invocation emits a `ResearchManifest` binding:
- LLM Provider, Model ID, Model Version
- SHA-256 of the prompt template
- Generation temperature, random seed, and completion hash
- Git commit hash of the active codebase

---

## 7. How Candidate Research Is Prevented from Auto-Registering

To eliminate accidental or programmatic hypothesis generation without governance approval:
1. **No Write Access to Hypothesis Registry:** Phase 14 modules have no write access to `docs/phase8.5/hypotheses/` or `data/manifests/research/hypotheses/`.
2. **Explicit Human Gatekeeper:** The conversion from an `AIHypothesisProposal` to a `HypothesisSpecification` requires an explicit, authenticated human interaction or governance CLI action.
3. **Ordinals are Centrally Governed:** Ordinal hypothesis identifiers (`HYP_001`, `HYP_002`, `HYP_003`) are minted only through formal pre-registration scripts (e.g. `scripts/register_phase8_5_step_r1_htf_002.py`), never by LLM runtime components.

---

## 8. How Cross-Hypothesis Data Quarantine Is Enforced

Cross-Hypothesis Data Quarantine is a **hard mathematical invariant** in ACASH:
1. **Permanent Blacklist in Code:**
   - In `src/acash/research/reinception.py`:
     - `PERMANENTLY_QUARANTINED_WINDOWS` protects EURUSD M5 Holdout (`2026-08-18` to `2026-09-04`) and EURUSD H4 Validation/OOS (`2023-05-29` to `2024-12-31`).
   - In `src/acash/research/quarantine.py`:
     - `PERMANENTLY_QUARANTINED_HOLDOUTS` protects bar ranges `6060..9999` (HYP_001) and `3751..6230` (HYP_002).
2. **Disjoint Partition Assertion:**  
   Before any new hypothesis can be registered, `ResearchReInceptionGate.evaluate_new_hypothesis_inception()` executes an intersection check between the proposed dataset window and all permanently quarantined windows. If any overlap $> 0$ bars is detected, it raises `QuarantineViolationError` immediately.

---

## 9. Architectural Decomposition: Existing Design vs Gaps

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ARCHITECTURAL TAXONOMY OF PHASE 14                                                     │
├──────────────────────────┬─────────────────────────────────────────────────────────────┤
│ Category                 │ Component Status & Scope                                    │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ EXISTING / VERIFIED      │ - HypothesisSpecification, SearchTrialLedger, ValidationRep │
│ DESIGN                   │ - ResearchReInceptionGate & Quarantine Enforcement          │
│                          │ - ADR-021 (Multi-Asset Core), ADR-022 (Strategy Governance) │
│                          │ - ADR-023 (Strategy Admission Standard)                    │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ PROPOSED DESIGN          │ - Phase 14 Master Architecture Plan (Rev 1.2)               │
│                          │ - Tri-Axial Metadata Schema (ResearchSourceMetadata)        │
│                          │ - EvidenceGroundingVerifier (Zero-hallucination engine)     │
│                          │ - CausalAstValidator (Point-in-time feature AST validator)  │
│                          │ - ResearchManifest (Cryptographic lineage DAG)              │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ IMPLEMENTATION GAP       │ - Runtime package src/acash/research/ai/ does not exist     │
│ (To Be Built in Phase 14)│ - HTTPX client wrapper for LLM provider abstraction         │
│                          │ - Section 33 automated research report generator            │
│                          │ - Unit and invariant test suites for Phase 14               │
├──────────────────────────┼─────────────────────────────────────────────────────────────┤
│ FUTURE OPTION            │ - External exploratory backends (VectorBT, HFTBacktest)     │
│ (Non-Core / Deferred)    │ - Optional vendor SDK convenience wrappers (openai, anth)   │
│                          │ - Multi-agent research tournament orchestration             │
└──────────────────────────┴─────────────────────────────────────────────────────────────┘
```

---

## 10. Proposed Runtime APIs & Interfaces to Implement

Upon human approval, implementation will construct the following interfaces under `src/acash/research/ai/`:

### 10.1 Provider Abstraction Layer (`acash.research.ai.provider.base`):
```python
class ILLMProvider(Protocol):
    async def generate_completion(
        self, prompt: str, system_prompt: str, config: LLMGenerationConfig
    ) -> LLMCompletionResponse: ...
```

### 10.2 AI Hypothesis Assistant (`acash.research.ai.hypothesis.assistant`):
```python
class AIHypothesisAssistant:
    def formulate_proposal(
        self, request: HypothesisFormulationRequest
    ) -> AIHypothesisProposal: ...
```

### 10.3 Point-in-Time AST Validator (`acash.research.ai.features.ast_validator`):
```python
class CausalAstValidator:
    def validate_expression(
        self, expression: str, available_variables: Sequence[str]
    ) -> AstValidationResult: ...
```

### 10.4 Evidence Grounding Verifier (`acash.research.ai.reporting.citation_verifier`):
```python
class EvidenceGroundingVerifier:
    def verify_report(
        self, report_markdown: str, sealed_dossier: AlphaQualificationDossier
    ) -> GroundingVerificationResult: ...
```

---

## 11. Comprehensive Verification & Test Strategy

Prioritizing the testing order from `AGENTS.md`:
$$\text{Happy Path} \to \text{Boundary} \to \text{Malformed} \to \text{Contradictory} \to \text{Adversarial} \to \text{Permutation} \to \text{Numerical Stability} \to \text{Golden Reference}$$

1. **Adversarial Malformed LLM Output Tests:** Corrupted JSON, markdown wraps, missing enum fields $\to$ fail closed with `DataContractError`.
2. **Point-in-Time Leakage Rejection Tests:** Feature proposals with `lead()`, unshifted lookaheads, or whole-dataset statistics $\to$ rejected by `CausalAstValidator`.
3. **Evidence Grounding / Anti-Hallucination Tests:** Report claiming Sharpe ratio $3.5$ against sealed dossier with Sharpe $1.8$ $\to$ rejected by `EvidenceGroundingVerifier`.
4. **Non-Bypass Pipeline Invariant Tests:** Attempting to submit an `AIHypothesisProposal` directly to `AlphaQualificationGate` $\to$ blocked.
5. **Secret Hygiene & Network Isolation:** Mock providers used in tests; missing API keys fail closed without leaking environment variables.

---

## 12. Audit of Candidate Review for Unsupported Extrapolations

The candidate review for `NY_OPEN_EMA_MOMENTUM_NASDAQ_M5` was audited for speculative leaps. The following boundaries are strictly enforced:

1. **`FAST_EMA_PERIOD` is Strictly `NOT PROVEN`:**  
   The video mentioned 12, but the QuantLab screenshot omitted the period. Proposing that "12 bars on M5 = 60 minutes = first hour" is an **unsupported inference** (post-hoc rationalization). It MUST remain classified as `NOT PROVEN`.
2. **`ATR_PERIOD` is Strictly `NOT PROVEN`:**  
   Assuming ATR(14) simply because it is an industry convention is rejected. It MUST remain classified as `NOT PROVEN`.
3. **Exact Stop and Trailing Semantics are Strictly `NOT PROVEN`:**  
   Intrabar tick touch vs bar close evaluation of $\text{EMA}_{120}$ is unstated and remains `NOT PROVEN`.
4. **"300,000 Parameter Combinations" is an Inferred Estimate:**  
   The figure $\approx 368,640$ is an **ILLUSTRATIVE / INFERRED ESTIMATE** demonstrating how combinatorial degrees of freedom explode; it is **NOT A PROVEN TRIAL COUNT**. Authoritative cardinality requires an explicitly pre-registered search space.
5. **Source Backtest Performance Claims are Strictly `SELF-REPORTED`:**  
   $+982\%$ net return, $1.29$ PF, $1.85$ Sharpe, and $100\%$ Monte Carlo profit probability are unverified marketing claims with zero empirical authority in ACASH.

---

## 13. Required Human Approval Decisions Before Implementation

Before a single line of runtime code is written in `src/acash/research/ai/`, the Human Quantitative Auditor must formally render decisions on the following 5 governance gates:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   REQUIRED HUMAN GOVERNANCE DECISIONS                  │
├──────┬──────────────────────────────┬──────────────────────────────────┤
│ Gate │ Decision Item                │ Description                      │
├──────┼──────────────────────────────┼──────────────────────────────────┤
│ G-1  │ Master Plan Adoption         │ Formally approve Phase 14 Master │
│      │                              │ Architecture Plan (Rev 1.2).     │
├──────┼──────────────────────────────┼──────────────────────────────────┤
│ G-2  │ Scope Authorization          │ Authorize Slices 1–4 runtime     │
│      │                              │ implementation under src/.       │
├──────┼──────────────────────────────┼──────────────────────────────────┤
│ G-3  │ Dependency Policy            │ Confirm zero vendor SDKs in core │
│      │                              │ (use httpx + mock providers).    │
├──────┼──────────────────────────────┼──────────────────────────────────┤
│ G-4  │ Research Telemetry Budget    │ Approve token usage and inference│
│      │                              │ cost observability limits.       │
├──────┼──────────────────────────────┼──────────────────────────────────┤
│ G-5  │ Candidate Status Consensus   │ Confirm candidate NY_OPEN_M5 is  │
│      │                              │ UNVALIDATED PROPOSAL (NEEDS MORE │
│      │                              │ RESEARCH), NOT HYP_003.          │
└──────┴──────────────────────────────┴──────────────────────────────────┘
```

---

## 14. Architecture Readiness Assessment & Final State

### A. Phase 14 Architecture Readiness Verdict
$$\boxed{\mathbf{PHASE\ 14\ ARCHITECTURE:\ READY\ FOR\ HUMAN\ APPROVAL}}$$
The architectural specification is mathematically sound, integrates cleanly with existing contracts, enforces strict fail-closed boundaries, and introduces zero circular dependencies.

### B. Implementation Scope
- Pure Python under `src/acash/research/ai/` (5 slices, ~17 modules).
- Comprehensive test coverage under `tests/unit/research/ai/`.
- Zero modifications to frozen core (`src/acash/execution`, `src/acash/portfolio`, `src/acash/risk`, `src/acash/runtime`).

### C. Security & Governance Risks
- **Prompt Injection:** Mitigated via independent tool execution boundaries (untrusted research text cannot trigger code execution).
- **Hallucination:** Mitigated via `EvidenceGroundingVerifier` cross-checking sealed artifacts.
- **Data Contamination:** Mitigated via immutable `PERMANENTLY_QUARANTINED_WINDOWS` in `reinception.py`.

### D. Current Candidate Readiness Status
- **Candidate:** `NY_OPEN_EMA_MOMENTUM_NASDAQ_M5`
- **Status:** **`UNVALIDATED PROPOSAL`**
- **Recommendation:** **`NEEDS MORE RESEARCH (REFINE)`**
- **HYP_003 Status:** **`NOT CREATED`**

### E. Current System Governance State
- **Capital Authority:** **`$0.00` (Hard-Locked)**
- **Trading Authority:** **`LOCKED`**
- **Broker Connection:** **`DISCONNECTED / NONE`**
- **Operational State:** **`RESEARCH STANDING BY`**
