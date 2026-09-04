# ACASH Bounded Capital Allocation & Risk Governance Framework
## Sovereign Risk Budgeting, Zero-Allocation Semantics & Performance-Chasing Protection Specification

> **Document ID:** `ACASH-SPEC-CAPITAL-ALLOC-v1.0`  
> **Status:** Approved Architecture Specification (Phase 17 Rev 4.1)  
> **Parent Governance:** ADR-003 (Deterministic Risk Engine), ADR-022 (Market-Adaptive Governance), ADR-023 (Strategy Admission & Bounded Allocation)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Evidence > Belief)  
> **Date:** 2026-09-04  
> **Version:** 1.0.0  

---

> [!IMPORTANT]
> **GOVERNANCE DEMARCATION:**
> - Phase 17 defines **eligibility contracts, hard safety bounds, zero-allocation semantics, and solver protocols**.
> - **THIS SPECIFICATION DOES NOT IMPLEMENT MATHEMATICAL OPTIMIZATION SOLVERS.** (Convex optimization, Risk Parity solvers, and Volatility Targeting engines belong to **Phase 21**).
> - Live capital authority remains strictly `$0.00`.

---

## 1. Executive Summary & Core Invariants

The ACASH Capital Allocation Framework establishes deterministic mathematical boundaries and governance guardrails governing how admitted strategies receive capital and risk budgets.

```
                  SOVEREIGN STRATEGY CATALOG
                              │
                              ▼
                  STRATEGY ADMISSION DOSSIER
                 (Gate 0–10 Passed & Verified)
                              │
                              ▼
               ATTRIBUTION & RESIDUAL CHECK
             (Is edge understood? Residual != Alpha)
                              │
                              ▼
                 REGIME COMPATIBILITY CHECK
               (Is current state favorable?)
                              │
                              ▼
                 ALLOCATION ELIGIBILITY GATE
               (Meets evidence & bounds tests?)
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
            INELIGIBLE                  ELIGIBLE
                │                           │
                ▼                           ▼
        ALLOCATION = $0.00          SAFETY BOUNDS CEILING
        (Always Valid &             (max_notional_usd,
            Default)                 max_risk_budget_pct,
                                     max_gross_exposure)
                                            │
                                            ▼
                                    PHASE 21 SOLVERS
                                    (Equal Risk Contrib,
                                     Vol Target, Haircut)
                                            │
                                            ▼
                                    FINAL PROPOSAL
                                   (Weight & Notional)
```

### 1.1 Core Invariant: Allocation = $0.00 is Always Valid and Default
A strategy being admitted to the Sovereign Strategy Catalog **does not entitle it to capital**:

$$\boxed{\text{Admission to Catalog} \quad \neq \quad \text{Entitlement to Capital Allocation}}$$

Under any ambiguity, regime mismatch, or risk breach, the allocation policy must seamlessly output:
$$\text{Proposed Weight} = 0.00, \quad \text{Proposed Notional} = \$0.00$$
Zero allocation is a completely valid, expected, and frequently optimal operational state.

---

## 2. Deterministic Zero-Allocation Triggers

A strategy candidate's `AllocationEligibility` is immediately forced to `INELIGIBLE` (`allocation = $0.00`) if any of the following conditions occur:

1. **Unresolved Attribution:** The `PerformanceAttributionAssessment` has zero confidence, unexplained residual return, or lacks an applicable factor model.
2. **Insufficient Effective Sample:** $N_{\text{eff}}$ is below the provenanced threshold or observations are clustered in an unrepeated historical regime.
3. **Low Confidence Regime:** The current market state has `ConfidenceAssessment.LOW` or `ClassificationStatus.INSUFFICIENT_EVIDENCE`.
4. **Regime Mismatch:** The current market state is classified as an unfavorable regime for the strategy's mechanism.
5. **Persistence Failure:** Out-of-sample or cross-validation persistence assessment is `FAILED` or `INCONCLUSIVE`.
6. **Severe Selection Bias:** The candidate was identified via unconstrained data-mining across hundreds of variations without holdout validation.
7. **Unresolved Critical Alternative Explanation:** The `AlternativeExplanationRegister` has critical counter-hypotheses marked `PLAUSIBLE` or `SUPPORTED`.
8. **Operational Degradation:** Runtime forward monitoring reports `ForwardHealthState.DEGRADED` or `STRUCTURAL_BREAK`.

---

## 3. Hard Allocation Safety Bounds (`AllocationSafetyBounds`)

All allocation proposals emitted by Phase 21 solvers must strictly satisfy deterministic upper bounds:

```python
class AllocationSafetyBounds(BaseModel):
    max_notional_usd: Decimal          # Absolute capital ceiling in USD
    max_risk_budget_pct: Decimal       # Maximum percentage of total portfolio risk budget
    max_gross_exposure_ratio: Decimal  # Maximum leverage / gross exposure multiplier
    drawdown_stepdown_pct: Decimal     # De-allocation rate upon strategy drawdown
```

### Invariant Checks:
- If `proposed_weight > max_risk_budget_pct` $\implies$ Raises `DataContractError`.
- If `proposed_notional_usd > max_notional_usd` $\implies$ Raises `DataContractError`.
- If `proposed_gross_exposure > max_gross_exposure_ratio` $\implies$ Raises `DataContractError`.
- If `is_eligible == False` and `proposed_weight != Decimal("0.0")` $\implies$ Raises `DataContractError`.

---

## 4. Protection Against Performance Chasing & Winner's Curse

### 4.1 The Winner's Curse Phenomenon
In competitive strategy tournaments, the strategy with the highest short-term return is rarely the strategy with the highest true edge. Random noise and favorable trade sequencing inevitably boost lucky candidates to the top rank.

ACASH mandates **`WinnerSelectionRisk`** discounting:
$$\text{Allocated Weight} = \text{Raw Solved Weight} \times (1 - \text{Haircut Discount Pct})$$

The haircut discount increases monotonically with:
- Number of tournament competitors ($M$)
- Number of parameter combinations searched
- Severity of data-snooping risk level (`LOW`, `MODERATE`, `HIGH`)

### 4.2 Multi-Period Smoothing (Anti-Recency Hysteresis)
Allocation shifts are smoothed across multiple evaluation periods to prevent whipsaw turnover. Capital cannot be aggressively rotated based on a single week or month of exceptional performance.

---

## 5. Solver Protocol Contract (`IAllocationPolicy`)

Phase 17 defines the abstract protocol interface that future Phase 21 solvers must implement:

```python
class IAllocationPolicy(Protocol):
    """Protocol interface defining solver contracts for future Phase 21 capital allocation."""

    def propose_allocation(
        self,
        strategy: StrategyDefinition,
        candidate_evaluations: Sequence[StrategyRegimeObservation],
        safety_bounds: AllocationSafetyBounds,
        attribution: PerformanceAttributionAssessment,
    ) -> StrategyAllocationProposal:
        """Propose capital weighting under strict safety bounds and attribution constraints."""
        ...
```

This establishes an impenetrable contract boundary: Phase 17 governs **what is permissible and safe**; Phase 21 implements **how mathematical weights are optimized within those bounds**.
