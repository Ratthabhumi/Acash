"""Portfolio Governance Gate for Phase 8 Portfolio Engine.

Authorizes final investable capital allocations from ranked AllocationCandidate evaluations
under sovereign risk, hurdle clearance, constraint feasibility, and evidence integrity contracts.
Enforces the fundamental architectural invariant: Ranking != Approval.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Mapping, Optional, Sequence
from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.portfolio.schema import (
    AllocationCandidate,
    AllocationDecision,
    AllocationEvaluation,
    PortfolioConstraints,
    RiskSnapshot,
)


class GovernanceConfig(BaseModel):
    """Configuration for sovereign portfolio governance authorization gates."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    governance_policy_version: str = "v1.0.0"
    require_evidence_threshold_met: bool = False
    require_dsr_significance: bool = False
    min_dsr_probability: Decimal = Decimal("0.95")


class PortfolioGovernanceGate:
    """Authoritative sovereign gate authorizing investable target portfolio allocations."""

    def __init__(self, config: Optional[GovernanceConfig] = None) -> None:
        self.config = config or GovernanceConfig()

    def evaluate_and_decide(
        self,
        candidates: Sequence[AllocationCandidate],
        ranked_evaluations: Sequence[AllocationEvaluation],
        risk_snapshot: RiskSnapshot,
        constraints: PortfolioConstraints,
        as_of: Optional[datetime] = None,
    ) -> AllocationDecision:
        """Evaluate ranked candidate proposals against sovereign risk gates and emit AllocationDecision."""
        auth_ts = as_of or datetime.now(timezone.utc)
        cand_map = {c.candidate_id: c for c in candidates}

        # 1. PRE-ALLOCATION SOVEREIGN RISK GATE
        pre_risk_verdict, pre_risk_reason = self._check_pre_risk_gate(risk_snapshot, constraints)
        if pre_risk_verdict is not None:
            return self._build_cash_decision(
                decision_id=f"DEC_CASH_{int(auth_ts.timestamp())}",
                gate_verdict=pre_risk_verdict,
                rationale=pre_risk_reason,
                auth_ts=auth_ts,
                risk_snapshot=risk_snapshot,
                constraints=constraints,
            )

        # 2. EVALUATE RANKED CANDIDATES IN DESCENDING ORDER
        rejection_reasons: list[str] = []
        for eval_rec in ranked_evaluations:
            candidate = cand_map.get(eval_rec.candidate_id)
            if candidate is None:
                raise DataContractError(
                    f"Evaluation refers to unknown candidate_id '{eval_rec.candidate_id}'."
                )

            verdict, reason = self._verify_candidate_eligibility(
                candidate=candidate,
                evaluation=eval_rec,
                constraints=constraints,
            )

            if verdict == "APPROVED":
                # Candidate approved by sovereign governance!
                is_cash = (candidate.allocator_name == "CASH")
                gate_verdict = "CASH_SOVEREIGN_FALLBACK" if is_cash else "APPROVED_INVESTABLE_ALLOCATION"
                rationale_text = (
                    f"Candidate '{candidate.candidate_id}' satisfied all sovereign risk, hurdle, and constraint gates."
                    if not is_cash
                    else f"Cash fallback baseline authorized: {candidate.candidate_id}."
                )
                return AllocationDecision(
                    decision_id=f"DEC_{candidate.candidate_id}_{int(auth_ts.timestamp())}",
                    selected_candidate_id=candidate.candidate_id,
                    allocator_name=candidate.allocator_name,
                    authorized_weights=eval_rec.normalized_weights,
                    cash_weight=eval_rec.normalized_cash_weight,
                    authorization_timestamp=auth_ts,
                    is_fallback_baseline=is_cash,
                    gate_verdict=gate_verdict,
                    rationale=rationale_text,
                    candidate_digest=candidate.candidate_digest,
                    evaluation_digest=eval_rec.evaluation_digest,
                    risk_snapshot_digest=risk_snapshot.snapshot_digest,
                    constraints_digest=constraints.constraints_digest,
                    governance_policy_version=self.config.governance_policy_version,
                )
            else:
                rejection_reasons.append(f"[{candidate.candidate_id}: {reason}]")

        # 3. CASH SOVEREIGNTY FALLBACK IF NO CANDIDATE ELIGIBLE
        combined_rationale = "; ".join(rejection_reasons) if rejection_reasons else "No candidates evaluated."
        return self._build_cash_decision(
            decision_id=f"DEC_CASH_FALLBACK_{int(auth_ts.timestamp())}",
            gate_verdict="REJECT_NO_ELIGIBLE_CANDIDATE",
            rationale=f"All evaluated candidates rejected by sovereign governance: {combined_rationale}",
            auth_ts=auth_ts,
            risk_snapshot=risk_snapshot,
            constraints=constraints,
        )

    def _check_pre_risk_gate(
        self,
        risk_snapshot: RiskSnapshot,
        constraints: PortfolioConstraints,
    ) -> tuple[Optional[str], str]:
        """Check top-level portfolio risk boundaries and constraint feasibility."""
        if risk_snapshot.is_kill_switch_active:
            return "PRE_RISK_GATE_KILL_SWITCH_ACTIVE", "PRE_RISK_GATE_KILL_SWITCH_ACTIVE: Sovereign risk kill switch is active."

        if risk_snapshot.current_drawdown_pct >= risk_snapshot.max_drawdown_limit_pct:
            return (
                "PRE_RISK_GATE_DRAWDOWN_LIMIT_BREACHED",
                f"PRE_RISK_GATE_DRAWDOWN_LIMIT_BREACHED: Portfolio drawdown ({risk_snapshot.current_drawdown_pct}) exceeds limit ({risk_snapshot.max_drawdown_limit_pct}).",
            )

        if risk_snapshot.margin_headroom < risk_snapshot.margin_buffer_threshold:
            return (
                "PRE_RISK_GATE_MARGIN_BUFFER_BREACHED",
                f"PRE_RISK_GATE_MARGIN_BUFFER_BREACHED: Margin headroom ({risk_snapshot.margin_headroom}) below buffer threshold ({risk_snapshot.margin_buffer_threshold}).",
            )

        if constraints.min_weight > constraints.max_weight:
            return "CONSTRAINT_INFEASIBLE", f"CONSTRAINT_INFEASIBLE: min_weight ({constraints.min_weight}) > max_weight ({constraints.max_weight})."

        if constraints.min_cash_buffer > Decimal("1.0"):
            return "CONSTRAINT_INFEASIBLE", f"CONSTRAINT_INFEASIBLE: min_cash_buffer ({constraints.min_cash_buffer}) > 1.0."

        return None, ""

    def _verify_candidate_eligibility(
        self,
        candidate: AllocationCandidate,
        evaluation: AllocationEvaluation,
        constraints: PortfolioConstraints,
    ) -> tuple[str, str]:
        """Validate an individual candidate evaluation against all governance gates."""
        from acash.portfolio.schema import recompute_digest

        # 1. Candidate and Evaluation identity & cryptographic digest verification
        if evaluation.candidate_id != candidate.candidate_id:
            return (
                "EVALUATION_INVALID",
                f"EVALUATION_INVALID: Candidate ID mismatch (evaluation: '{evaluation.candidate_id}', candidate: '{candidate.candidate_id}').",
            )

        if not evaluation.evaluation_digest or recompute_digest(evaluation) != evaluation.evaluation_digest:
            return (
                "EVALUATION_INVALID",
                "EVALUATION_INVALID: Cryptographic recomputation of evaluation_digest failed or digest missing.",
            )

        if not candidate.candidate_digest or recompute_digest(candidate) != candidate.candidate_digest:
            return (
                "EVALUATION_INVALID",
                "EVALUATION_INVALID: Cryptographic recomputation of candidate_digest failed or digest missing.",
            )

        if evaluation.candidate_digest and evaluation.candidate_digest != candidate.candidate_digest:
            return (
                "EVALUATION_INVALID",
                f"EVALUATION_INVALID: Evaluation candidate_digest '{evaluation.candidate_digest}' != candidate.candidate_digest '{candidate.candidate_digest}'.",
            )

        # 2. DSR Provenance Consistency verification
        dsr_k_meta = evaluation.evaluation_metadata.get("dsr_trials_k")
        if dsr_k_meta is not None and dsr_k_meta != str(candidate.search_trials_k):
            return (
                "DSR_PROVENANCE_MISMATCH",
                f"DSR_PROVENANCE_MISMATCH: evaluation dsr_trials_k ({dsr_k_meta}) != candidate search_trials_k ({candidate.search_trials_k}).",
            )

        dsr_var_meta = evaluation.evaluation_metadata.get("dsr_variance_of_trials")
        if dsr_var_meta is not None and dsr_var_meta != str(candidate.trial_variance):
            return (
                "DSR_PROVENANCE_MISMATCH",
                f"DSR_PROVENANCE_MISMATCH: evaluation dsr_variance_of_trials ({dsr_var_meta}) != candidate trial_variance ({candidate.trial_variance}).",
            )

        dsr_mode_meta = evaluation.evaluation_metadata.get("dsr_selection_mode")
        if dsr_mode_meta is not None:
            expected_mode = "SINGLE_TRIAL" if candidate.search_trials_k == 1 else "MULTIPLE_TRIAL"
            if dsr_mode_meta != expected_mode:
                return (
                    "DSR_PROVENANCE_MISMATCH",
                    f"DSR_PROVENANCE_MISMATCH: evaluation dsr_selection_mode ({dsr_mode_meta}) contradicts candidate K={candidate.search_trials_k} (expected {expected_mode}).",
                )

        # 3. Independent Governance-Owned Invariant & Constraint Verification
        w_sum = Decimal("0.0")
        for sym, w in evaluation.normalized_weights.items():
            if not w.is_finite() or w < Decimal("0.0"):
                return "CONSTRAINT_VIOLATION", f"CONSTRAINT_VIOLATION: Asset '{sym}' weight {w} is non-finite or negative (long-only breached)."
            if w < constraints.min_weight or w > constraints.max_weight:
                return "CONSTRAINT_VIOLATION", f"CONSTRAINT_VIOLATION: Asset '{sym}' weight {w} outside [{constraints.min_weight}, {constraints.max_weight}]."
            w_sum += w

        cash_w = evaluation.normalized_cash_weight
        if not cash_w.is_finite() or cash_w < Decimal("0.0"):
            return "CONSTRAINT_VIOLATION", f"CONSTRAINT_VIOLATION: Cash weight {cash_w} is non-finite or negative."

        total_sum = w_sum + cash_w
        if abs(total_sum - Decimal("1.0")) > Decimal("1e-6"):
            return "CONSTRAINT_VIOLATION", f"CONSTRAINT_VIOLATION: Normalized weights + cash sum ({total_sum}) != 1.0."

        if w_sum > constraints.max_gross_leverage + Decimal("1e-6"):
            return "CONSTRAINT_VIOLATION", f"CONSTRAINT_VIOLATION: Gross leverage ({w_sum}) exceeds max_gross_leverage ({constraints.max_gross_leverage})."

        if candidate.allocator_name != "CASH" and cash_w < constraints.min_cash_buffer - Decimal("1e-6"):
            return "CONSTRAINT_VIOLATION", f"CONSTRAINT_VIOLATION: Cash weight {cash_w} below min_cash_buffer {constraints.min_cash_buffer}."

        if not evaluation.constraints_satisfied:
            return "CONSTRAINT_VIOLATION", "CONSTRAINT_VIOLATION: Candidate evaluation flagged constraints_satisfied = False."

        # 4. Evidence threshold policy verification (if enabled)
        if self.config.require_evidence_threshold_met and candidate.allocator_name != "CASH":
            status = evaluation.evaluation_metadata.get("sample_sufficiency_status")
            if status != "EVIDENCE_THRESHOLD_MET":
                return "EVIDENCE_THRESHOLD_NOT_MET", f"EVIDENCE_THRESHOLD_NOT_MET: Sample evidence threshold not met (status: {status})."

        # 5. DSR significance verification (if enabled)
        if self.config.require_dsr_significance and candidate.allocator_name != "CASH":
            dsr_prob_str = evaluation.evaluation_metadata.get("dsr_probability", "0.0")
            try:
                dsr_prob = Decimal(dsr_prob_str)
                if dsr_prob < self.config.min_dsr_probability:
                    return "DSR_PROBABILITY_BELOW_THRESHOLD", f"DSR_PROBABILITY_BELOW_THRESHOLD: DSR probability {dsr_prob} < required threshold {self.config.min_dsr_probability}."
            except Exception:
                return "DSR_PROBABILITY_INVALID", "DSR_PROBABILITY_INVALID: Failed to parse DSR probability from evaluation metadata."

        # 6. Hurdle verification (Cash candidates exempt)
        if candidate.allocator_name != "CASH" and not evaluation.hurdle_rate_cleared:
            return "HURDLE_REJECTION", f"HURDLE_REJECTION: Net expected excess return ({evaluation.net_expected_excess_return}) failed hurdle margin."

        return "APPROVED", "All gates satisfied."

    def _build_cash_decision(
        self,
        decision_id: str,
        gate_verdict: str,
        rationale: str,
        auth_ts: datetime,
        risk_snapshot: RiskSnapshot,
        constraints: PortfolioConstraints,
    ) -> AllocationDecision:
        """Construct sovereign 100% Cash AllocationDecision upon rejection."""
        return AllocationDecision(
            decision_id=decision_id,
            selected_candidate_id="CASH_SOVEREIGN_FALLBACK",
            allocator_name="CASH",
            authorized_weights={},
            cash_weight=Decimal("1.0"),
            authorization_timestamp=auth_ts,
            is_fallback_baseline=True,
            gate_verdict=gate_verdict,
            rationale=rationale,
            candidate_digest="",
            evaluation_digest="",
            risk_snapshot_digest=risk_snapshot.snapshot_digest,
            constraints_digest=constraints.constraints_digest,
            governance_policy_version=self.config.governance_policy_version,
        )
