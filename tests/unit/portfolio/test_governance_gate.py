"""Unit and Invariant Tests for Portfolio Governance Gate (Phase 8 Batch 2B.1).

Tests all 18 mandatory governance invariants:
- Ranking != Approval
- Pre-allocation risk gate (kill switch, drawdown, margin buffer)
- Constraint feasibility & independent bounds enforcement
- Cryptographic evaluation and candidate digest recomputation
- Candidate-to-evaluation lineage and candidate_digest matching
- DSR metadata and search history consistency
- Hurdle clearance gate
- Multi-candidate eligibility & failover to lower-ranked approved candidates
- 100% Cash fallback sovereignty
- Cryptographic decision digest lineage & sensitivity
- Idempotency and determinism
- Distinction between residual constraint cash vs governance-forced cash
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.governance import GovernanceConfig, PortfolioGovernanceGate
from acash.portfolio.schema import (
    AllocationCandidate,
    AllocationDecision,
    AllocationEvaluation,
    PortfolioConstraints,
    RiskSnapshot,
)


def _default_constraints() -> PortfolioConstraints:
    return PortfolioConstraints(
        min_weight=Decimal("0.0"),
        max_weight=Decimal("1.0"),
        max_gross_leverage=Decimal("1.0"),
        min_cash_buffer=Decimal("0.05"),
    )


def _healthy_risk_snapshot() -> RiskSnapshot:
    return RiskSnapshot(
        snapshot_id="SNAP_HEALTHY",
        timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        account_equity=Decimal("1000000.0"),
        cash_balance=Decimal("150000.0"),
        margin_used=Decimal("850000.0"),
        margin_headroom=Decimal("150000.0"),
        margin_buffer_threshold=Decimal("50000.0"),
        current_drawdown_pct=Decimal("0.02"),
        max_drawdown_limit_pct=Decimal("0.10"),
        is_kill_switch_active=False,
    )


def _sample_candidates_and_evaluations() -> tuple[list[AllocationCandidate], list[AllocationEvaluation]]:
    cand_ew = AllocationCandidate(
        candidate_id="CAND_EW",
        allocator_name="EQUAL_WEIGHT",
        asset_weights={"AAPL": Decimal("0.45"), "SPY": Decimal("0.45")},
        cash_weight=Decimal("0.10"),
        search_trials_k=1,
        trial_variance=0.0,
    )
    cand_inv = AllocationCandidate(
        candidate_id="CAND_INV",
        allocator_name="INVERSE_VOL",
        asset_weights={"AAPL": Decimal("0.30"), "SPY": Decimal("0.60")},
        cash_weight=Decimal("0.10"),
        search_trials_k=1,
        trial_variance=0.0,
    )
    cand_cash = AllocationCandidate(
        candidate_id="CAND_CASH",
        allocator_name="CASH",
        asset_weights={"AAPL": Decimal("0.0"), "SPY": Decimal("0.0")},
        cash_weight=Decimal("1.0"),
        search_trials_k=1,
        trial_variance=0.0,
    )

    eval_ew = AllocationEvaluation(
        candidate_id="CAND_EW",
        candidate_digest=cand_ew.candidate_digest,
        normalized_weights={"AAPL": Decimal("0.45"), "SPY": Decimal("0.45")},
        normalized_cash_weight=Decimal("0.10"),
        oos_sharpe_ratio=Decimal("1.50"),
        oos_cvar_95=Decimal("0.02"),
        turnover_required=Decimal("0.10"),
        estimated_transaction_cost=Decimal("0.01"),
        net_expected_excess_return=Decimal("0.08"),
        hurdle_rate_cleared=True,
        constraints_satisfied=True,
        rank_score=Decimal("1.44"),
        evaluation_metadata={
            "sample_sufficiency_status": "EVIDENCE_THRESHOLD_MET",
            "dsr_probability": "0.98",
            "dsr_trials_k": "1",
            "dsr_variance_of_trials": "0.0",
            "dsr_selection_mode": "SINGLE_TRIAL",
        },
    )

    eval_inv = AllocationEvaluation(
        candidate_id="CAND_INV",
        candidate_digest=cand_inv.candidate_digest,
        normalized_weights={"AAPL": Decimal("0.30"), "SPY": Decimal("0.60")},
        normalized_cash_weight=Decimal("0.10"),
        oos_sharpe_ratio=Decimal("1.20"),
        oos_cvar_95=Decimal("0.015"),
        turnover_required=Decimal("0.05"),
        estimated_transaction_cost=Decimal("0.005"),
        net_expected_excess_return=Decimal("0.06"),
        hurdle_rate_cleared=True,
        constraints_satisfied=True,
        rank_score=Decimal("1.16"),
        evaluation_metadata={
            "sample_sufficiency_status": "EVIDENCE_THRESHOLD_MET",
            "dsr_probability": "0.96",
            "dsr_trials_k": "1",
            "dsr_variance_of_trials": "0.0",
            "dsr_selection_mode": "SINGLE_TRIAL",
        },
    )

    eval_cash = AllocationEvaluation(
        candidate_id="CAND_CASH",
        candidate_digest=cand_cash.candidate_digest,
        normalized_weights={"AAPL": Decimal("0.0"), "SPY": Decimal("0.0")},
        normalized_cash_weight=Decimal("1.0"),
        oos_sharpe_ratio=Decimal("0.0"),
        oos_cvar_95=Decimal("0.0"),
        turnover_required=Decimal("0.0"),
        estimated_transaction_cost=Decimal("0.0"),
        net_expected_excess_return=Decimal("-0.04"),
        hurdle_rate_cleared=False,
        constraints_satisfied=True,
        rank_score=Decimal("0.0"),
        evaluation_metadata={
            "sample_sufficiency_status": "EVIDENCE_THRESHOLD_MET",
            "dsr_probability": "0.0",
            "dsr_trials_k": "1",
            "dsr_variance_of_trials": "0.0",
            "dsr_selection_mode": "SINGLE_TRIAL",
        },
    )

    return [cand_ew, cand_inv, cand_cash], [eval_ew, eval_inv, eval_cash]


# A. Kill switch -> Cash
def test_governance_kill_switch_forces_cash() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()
    risk = _healthy_risk_snapshot().model_copy(update={"is_kill_switch_active": True})
    decision = gate.evaluate_and_decide(candidates, evaluations, risk, _default_constraints())
    assert decision.is_fallback_baseline
    assert decision.cash_weight == Decimal("1.0")
    assert decision.gate_verdict == "PRE_RISK_GATE_KILL_SWITCH_ACTIVE"
    assert decision.selected_candidate_id == "CASH_SOVEREIGN_FALLBACK"


# B. Drawdown breach -> Cash
def test_governance_drawdown_breach_forces_cash() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()
    risk = _healthy_risk_snapshot().model_copy(
        update={"current_drawdown_pct": Decimal("0.15"), "max_drawdown_limit_pct": Decimal("0.10")}
    )
    decision = gate.evaluate_and_decide(candidates, evaluations, risk, _default_constraints())
    assert decision.is_fallback_baseline
    assert decision.cash_weight == Decimal("1.0")
    assert decision.gate_verdict == "PRE_RISK_GATE_DRAWDOWN_LIMIT_BREACHED"


# C. Margin buffer breach -> Cash
def test_governance_margin_buffer_breach_forces_cash() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()
    risk = _healthy_risk_snapshot().model_copy(
        update={"margin_headroom": Decimal("10000.0"), "margin_buffer_threshold": Decimal("50000.0")}
    )
    decision = gate.evaluate_and_decide(candidates, evaluations, risk, _default_constraints())
    assert decision.is_fallback_baseline
    assert decision.cash_weight == Decimal("1.0")
    assert decision.gate_verdict == "PRE_RISK_GATE_MARGIN_BUFFER_BREACHED"


# D. Infeasible Constraints -> Cash
def test_governance_infeasible_constraints_forces_cash() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()
    infeasible_constraints = PortfolioConstraints.model_construct(
        min_weight=Decimal("0.60"),
        max_weight=Decimal("0.40"),  # min > max
        max_gross_leverage=Decimal("1.0"),
        min_cash_buffer=Decimal("0.05"),
    )
    decision = gate.evaluate_and_decide(candidates, evaluations, _healthy_risk_snapshot(), infeasible_constraints)
    assert decision.is_fallback_baseline
    assert decision.cash_weight == Decimal("1.0")
    assert decision.gate_verdict == "CONSTRAINT_INFEASIBLE"


# E. Insufficient evidence -> rejection / Cash (when policy enabled)
def test_governance_insufficient_evidence_policy_rejection() -> None:
    gate = PortfolioGovernanceGate(config=GovernanceConfig(require_evidence_threshold_met=True))
    candidates, evaluations = _sample_candidates_and_evaluations()

    eval_ew_insufficient = AllocationEvaluation(
        candidate_id=candidates[0].candidate_id,
        candidate_digest=candidates[0].candidate_digest,
        normalized_weights=evaluations[0].normalized_weights,
        normalized_cash_weight=evaluations[0].normalized_cash_weight,
        oos_sharpe_ratio=evaluations[0].oos_sharpe_ratio,
        oos_cvar_95=evaluations[0].oos_cvar_95,
        turnover_required=evaluations[0].turnover_required,
        estimated_transaction_cost=evaluations[0].estimated_transaction_cost,
        net_expected_excess_return=evaluations[0].net_expected_excess_return,
        hurdle_rate_cleared=evaluations[0].hurdle_rate_cleared,
        constraints_satisfied=evaluations[0].constraints_satisfied,
        rank_score=evaluations[0].rank_score,
        evaluation_metadata={**evaluations[0].evaluation_metadata, "sample_sufficiency_status": "INSUFFICIENT_EVIDENCE"},
    )

    decision = gate.evaluate_and_decide(
        candidates=candidates,
        ranked_evaluations=[eval_ew_insufficient],
        risk_snapshot=_healthy_risk_snapshot(),
        constraints=_default_constraints(),
    )
    assert decision.cash_weight == Decimal("1.0")
    assert decision.gate_verdict == "REJECT_NO_ELIGIBLE_CANDIDATE"
    assert "EVIDENCE_THRESHOLD_NOT_MET" in decision.rationale


# F. DSR significance below threshold -> rejection (when policy enabled)
def test_governance_dsr_significance_rejection() -> None:
    gate = PortfolioGovernanceGate(
        config=GovernanceConfig(require_dsr_significance=True, min_dsr_probability=Decimal("0.95"))
    )
    candidates, evaluations = _sample_candidates_and_evaluations()

    eval_low_dsr = AllocationEvaluation(
        candidate_id=candidates[0].candidate_id,
        candidate_digest=candidates[0].candidate_digest,
        normalized_weights=evaluations[0].normalized_weights,
        normalized_cash_weight=evaluations[0].normalized_cash_weight,
        oos_sharpe_ratio=evaluations[0].oos_sharpe_ratio,
        oos_cvar_95=evaluations[0].oos_cvar_95,
        turnover_required=evaluations[0].turnover_required,
        estimated_transaction_cost=evaluations[0].estimated_transaction_cost,
        net_expected_excess_return=evaluations[0].net_expected_excess_return,
        hurdle_rate_cleared=evaluations[0].hurdle_rate_cleared,
        constraints_satisfied=evaluations[0].constraints_satisfied,
        rank_score=evaluations[0].rank_score,
        evaluation_metadata={**evaluations[0].evaluation_metadata, "dsr_probability": "0.80"},
    )

    decision = gate.evaluate_and_decide(
        candidates=candidates,
        ranked_evaluations=[eval_low_dsr],
        risk_snapshot=_healthy_risk_snapshot(),
        constraints=_default_constraints(),
    )
    assert decision.cash_weight == Decimal("1.0")
    assert decision.gate_verdict == "REJECT_NO_ELIGIBLE_CANDIDATE"
    assert "DSR_PROBABILITY_BELOW_THRESHOLD" in decision.rationale


# G. Hurdle failure -> Cash
def test_governance_hurdle_failure_rejection() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()

    eval_hurdle_fail = AllocationEvaluation(
        candidate_id=candidates[0].candidate_id,
        candidate_digest=candidates[0].candidate_digest,
        normalized_weights=evaluations[0].normalized_weights,
        normalized_cash_weight=evaluations[0].normalized_cash_weight,
        oos_sharpe_ratio=evaluations[0].oos_sharpe_ratio,
        oos_cvar_95=evaluations[0].oos_cvar_95,
        turnover_required=evaluations[0].turnover_required,
        estimated_transaction_cost=evaluations[0].estimated_transaction_cost,
        net_expected_excess_return=evaluations[0].net_expected_excess_return,
        hurdle_rate_cleared=False,  # Failed hurdle!
        constraints_satisfied=evaluations[0].constraints_satisfied,
        rank_score=evaluations[0].rank_score,
        evaluation_metadata=evaluations[0].evaluation_metadata,
    )

    decision = gate.evaluate_and_decide(
        candidates=candidates,
        ranked_evaluations=[eval_hurdle_fail],
        risk_snapshot=_healthy_risk_snapshot(),
        constraints=_default_constraints(),
    )
    assert decision.cash_weight == Decimal("1.0")
    assert decision.gate_verdict == "REJECT_NO_ELIGIBLE_CANDIDATE"
    assert "HURDLE_REJECTION" in decision.rationale


# H. Ranking != Approval: Rank #1 fails hurdle, Rank #2 passes -> Rank #2 selected
def test_governance_rank1_fails_hurdle_rank2_selected() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()

    eval_ew_fail_hurdle = AllocationEvaluation(
        candidate_id=candidates[0].candidate_id,
        candidate_digest=candidates[0].candidate_digest,
        normalized_weights=evaluations[0].normalized_weights,
        normalized_cash_weight=evaluations[0].normalized_cash_weight,
        oos_sharpe_ratio=evaluations[0].oos_sharpe_ratio,
        oos_cvar_95=evaluations[0].oos_cvar_95,
        turnover_required=evaluations[0].turnover_required,
        estimated_transaction_cost=evaluations[0].estimated_transaction_cost,
        net_expected_excess_return=evaluations[0].net_expected_excess_return,
        hurdle_rate_cleared=False,  # Failed hurdle
        constraints_satisfied=True,
        rank_score=evaluations[0].rank_score,
        evaluation_metadata=evaluations[0].evaluation_metadata,
    )
    eval_inv_pass = evaluations[1]

    decision = gate.evaluate_and_decide(
        candidates=candidates,
        ranked_evaluations=[eval_ew_fail_hurdle, eval_inv_pass],
        risk_snapshot=_healthy_risk_snapshot(),
        constraints=_default_constraints(),
    )

    assert decision.selected_candidate_id == "CAND_INV"
    assert decision.allocator_name == "INVERSE_VOL"
    assert decision.gate_verdict == "APPROVED_INVESTABLE_ALLOCATION"
    assert decision.authorized_weights["AAPL"] == Decimal("0.30")
    assert decision.authorized_weights["SPY"] == Decimal("0.60")
    assert decision.cash_weight == Decimal("0.10")


# I. All candidates fail -> Cash
def test_governance_all_candidates_fail_forces_cash() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()

    eval_ew_fail = AllocationEvaluation(
        candidate_id=candidates[0].candidate_id,
        candidate_digest=candidates[0].candidate_digest,
        normalized_weights=evaluations[0].normalized_weights,
        normalized_cash_weight=evaluations[0].normalized_cash_weight,
        oos_sharpe_ratio=evaluations[0].oos_sharpe_ratio,
        oos_cvar_95=evaluations[0].oos_cvar_95,
        turnover_required=evaluations[0].turnover_required,
        estimated_transaction_cost=evaluations[0].estimated_transaction_cost,
        net_expected_excess_return=evaluations[0].net_expected_excess_return,
        hurdle_rate_cleared=False,
        constraints_satisfied=True,
        rank_score=evaluations[0].rank_score,
        evaluation_metadata=evaluations[0].evaluation_metadata,
    )
    eval_inv_fail = AllocationEvaluation(
        candidate_id=candidates[1].candidate_id,
        candidate_digest=candidates[1].candidate_digest,
        normalized_weights=evaluations[1].normalized_weights,
        normalized_cash_weight=evaluations[1].normalized_cash_weight,
        oos_sharpe_ratio=evaluations[1].oos_sharpe_ratio,
        oos_cvar_95=evaluations[1].oos_cvar_95,
        turnover_required=evaluations[1].turnover_required,
        estimated_transaction_cost=evaluations[1].estimated_transaction_cost,
        net_expected_excess_return=evaluations[1].net_expected_excess_return,
        hurdle_rate_cleared=True,
        constraints_satisfied=False,  # Constraints failed
        rank_score=evaluations[1].rank_score,
        evaluation_metadata=evaluations[1].evaluation_metadata,
    )

    decision = gate.evaluate_and_decide(
        candidates=candidates,
        ranked_evaluations=[eval_ew_fail, eval_inv_fail],
        risk_snapshot=_healthy_risk_snapshot(),
        constraints=_default_constraints(),
    )
    assert decision.is_fallback_baseline
    assert decision.cash_weight == Decimal("1.0")
    assert decision.gate_verdict == "REJECT_NO_ELIGIBLE_CANDIDATE"


# J. Unknown Candidate ID -> Fail Closed
def test_governance_unknown_candidate_fail_closed() -> None:
    gate = PortfolioGovernanceGate()
    _, evaluations = _sample_candidates_and_evaluations()

    with pytest.raises(DataContractError, match="Evaluation refers to unknown candidate_id"):
        gate.evaluate_and_decide(
            candidates=[],  # Empty candidates list!
            ranked_evaluations=evaluations,
            risk_snapshot=_healthy_risk_snapshot(),
            constraints=_default_constraints(),
        )


# K. Decision digest changes when RiskSnapshot changes
def test_decision_digest_sensitivity_to_risk_snapshot() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()
    ts = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    risk1 = _healthy_risk_snapshot()
    risk2 = RiskSnapshot.model_validate({**risk1.model_dump(), "account_equity": Decimal("900000.0")})

    dec1 = gate.evaluate_and_decide(candidates, evaluations, risk1, _default_constraints(), as_of=ts)
    dec2 = gate.evaluate_and_decide(candidates, evaluations, risk2, _default_constraints(), as_of=ts)

    assert dec1.decision_digest != dec2.decision_digest
    assert dec1.risk_snapshot_digest != dec2.risk_snapshot_digest


# L. Decision digest changes when PortfolioConstraints change
def test_decision_digest_sensitivity_to_constraints() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()
    ts = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    const1 = _default_constraints()
    const2 = PortfolioConstraints.model_validate({**const1.model_dump(), "min_cash_buffer": Decimal("0.08")})

    dec1 = gate.evaluate_and_decide(candidates, evaluations, _healthy_risk_snapshot(), const1, as_of=ts)
    dec2 = gate.evaluate_and_decide(candidates, evaluations, _healthy_risk_snapshot(), const2, as_of=ts)

    assert dec1.decision_digest != dec2.decision_digest
    assert dec1.constraints_digest != dec2.constraints_digest


# M. Decision digest changes when governance policy version changes
def test_decision_digest_sensitivity_to_governance_version() -> None:
    candidates, evaluations = _sample_candidates_and_evaluations()
    ts = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    gate_v1 = PortfolioGovernanceGate(config=GovernanceConfig(governance_policy_version="v1.0.0"))
    gate_v2 = PortfolioGovernanceGate(config=GovernanceConfig(governance_policy_version="v2.0.0"))

    dec1 = gate_v1.evaluate_and_decide(candidates, evaluations, _healthy_risk_snapshot(), _default_constraints(), as_of=ts)
    dec2 = gate_v2.evaluate_and_decide(candidates, evaluations, _healthy_risk_snapshot(), _default_constraints(), as_of=ts)

    assert dec1.decision_digest != dec2.decision_digest
    assert dec1.governance_policy_version == "v1.0.0"
    assert dec2.governance_policy_version == "v2.0.0"


# N. Deterministic same-input decision
def test_governance_decision_determinism() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()
    ts = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    dec1 = gate.evaluate_and_decide(candidates, evaluations, _healthy_risk_snapshot(), _default_constraints(), as_of=ts)
    dec2 = gate.evaluate_and_decide(candidates, evaluations, _healthy_risk_snapshot(), _default_constraints(), as_of=ts)

    assert dec1.decision_digest == dec2.decision_digest
    assert dec1.authorized_weights == dec2.authorized_weights
    assert dec1.cash_weight == dec2.cash_weight


# O. Tampered Evaluation Digest -> Rejection
def test_governance_tampered_evaluation_digest_rejection() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()

    eval_tampered = AllocationEvaluation.model_construct(
        **{**evaluations[0].model_dump(), "evaluation_digest": "a" * 64}  # Forged fake digest!
    )

    decision = gate.evaluate_and_decide(
        candidates=candidates,
        ranked_evaluations=[eval_tampered],
        risk_snapshot=_healthy_risk_snapshot(),
        constraints=_default_constraints(),
    )
    assert decision.cash_weight == Decimal("1.0")
    assert decision.gate_verdict == "REJECT_NO_ELIGIBLE_CANDIDATE"
    assert "EVALUATION_INVALID" in decision.rationale


# P. Candidate Digest Mismatch -> Rejection
def test_governance_candidate_digest_mismatch_rejection() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()

    # Evaluation pointing to forged candidate digest
    eval_mismatched = AllocationEvaluation.model_construct(
        **{**evaluations[0].model_dump(), "candidate_digest": "f" * 64}
    )

    decision = gate.evaluate_and_decide(
        candidates=candidates,
        ranked_evaluations=[eval_mismatched],
        risk_snapshot=_healthy_risk_snapshot(),
        constraints=_default_constraints(),
    )
    assert decision.cash_weight == Decimal("1.0")
    assert decision.gate_verdict == "REJECT_NO_ELIGIBLE_CANDIDATE"
    assert "EVALUATION_INVALID" in decision.rationale


# Q. DSR Metadata Mismatch -> Rejection
def test_governance_dsr_metadata_mismatch_rejection() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()

    # Candidate has K=1, but evaluation metadata forged K=25
    eval_forged_dsr = AllocationEvaluation(
        candidate_id=candidates[0].candidate_id,
        candidate_digest=candidates[0].candidate_digest,
        normalized_weights=evaluations[0].normalized_weights,
        normalized_cash_weight=evaluations[0].normalized_cash_weight,
        oos_sharpe_ratio=evaluations[0].oos_sharpe_ratio,
        oos_cvar_95=evaluations[0].oos_cvar_95,
        turnover_required=evaluations[0].turnover_required,
        estimated_transaction_cost=evaluations[0].estimated_transaction_cost,
        net_expected_excess_return=evaluations[0].net_expected_excess_return,
        hurdle_rate_cleared=evaluations[0].hurdle_rate_cleared,
        constraints_satisfied=evaluations[0].constraints_satisfied,
        rank_score=evaluations[0].rank_score,
        evaluation_metadata={**evaluations[0].evaluation_metadata, "dsr_trials_k": "25"},
    )

    decision = gate.evaluate_and_decide(
        candidates=candidates,
        ranked_evaluations=[eval_forged_dsr],
        risk_snapshot=_healthy_risk_snapshot(),
        constraints=_default_constraints(),
    )
    assert decision.cash_weight == Decimal("1.0")
    assert decision.gate_verdict == "REJECT_NO_ELIGIBLE_CANDIDATE"
    assert "DSR_PROVENANCE_MISMATCH" in decision.rationale


# R. Independent Governance Constraint Verification
def test_governance_independent_constraint_violation() -> None:
    gate = PortfolioGovernanceGate()
    candidates, evaluations = _sample_candidates_and_evaluations()

    # Evaluation falsely marked constraints_satisfied=True, but weight violates min_cash_buffer
    eval_breached_cash = AllocationEvaluation(
        candidate_id=candidates[0].candidate_id,
        candidate_digest=candidates[0].candidate_digest,
        normalized_weights={"AAPL": Decimal("0.50"), "SPY": Decimal("0.48")},
        normalized_cash_weight=Decimal("0.02"),  # Below min_cash_buffer 0.05!
        oos_sharpe_ratio=evaluations[0].oos_sharpe_ratio,
        oos_cvar_95=evaluations[0].oos_cvar_95,
        turnover_required=evaluations[0].turnover_required,
        estimated_transaction_cost=evaluations[0].estimated_transaction_cost,
        net_expected_excess_return=evaluations[0].net_expected_excess_return,
        hurdle_rate_cleared=True,
        constraints_satisfied=True,  # Falsely claimed satisfied!
        rank_score=evaluations[0].rank_score,
        evaluation_metadata=evaluations[0].evaluation_metadata,
    )

    decision = gate.evaluate_and_decide(
        candidates=candidates,
        ranked_evaluations=[eval_breached_cash],
        risk_snapshot=_healthy_risk_snapshot(),
        constraints=_default_constraints(),
    )
    assert decision.cash_weight == Decimal("1.0")
    assert decision.gate_verdict == "REJECT_NO_ELIGIBLE_CANDIDATE"
    assert "CONSTRAINT_VIOLATION" in decision.rationale
