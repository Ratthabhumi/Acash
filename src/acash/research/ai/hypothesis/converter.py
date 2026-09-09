"""Phase 14 S2 strict proposal-to-specification converter.

Converts an ``AIHypothesisProposal`` into a canonical Phase 4
``HypothesisSpecification`` artifact. The conversion is HUMAN-GATED: the
``HypothesisSpecification`` is returned as an artifact and NEVER registered,
NEVER authorized for backtesting/research execution, and NEVER promoted to
HYP_003. The converter holds zero registration or execution authority.
"""

import json
from typing import Tuple

from acash.core.domain.exceptions import DataContractError
from acash.research.ai.enums import CandidateStatus
from acash.research.ai.schema import AIHypothesisProposal
from acash.research.schema import HypothesisSpecification


class HypothesisProposalConverter:
    """Strict converter. Invalid input raises ``DataContractError`` (fail-closed)."""

    def to_hypothesis_specification(
        self,
        proposal: AIHypothesisProposal,
        *,
        hypothesis_id: str,
        hypothesis_version: str,
        author: str,
        registered_at_utc: str,
        primary_horizon: int,
        parameter_config_json: str,
    ) -> HypothesisSpecification:
        if proposal.proposal_status != CandidateStatus.UNVALIDATED_PROPOSAL:
            raise DataContractError(
                f"Refusing to convert a proposal in status {proposal.proposal_status.value}."
            )
        if not proposal.feature_dependencies:
            raise DataContractError("Proposal carries no feature dependencies.")
        horizons: Tuple[int, ...] = proposal.target_horizons
        if not horizons:
            raise DataContractError("Proposal carries no target horizons.")
        if primary_horizon not in horizons:
            raise DataContractError(
                f"primary_horizon {primary_horizon} not present in target_horizons {horizons}."
            )
        try:
            parsed = json.loads(parameter_config_json)
        except json.JSONDecodeError as exc:
            raise DataContractError("parameter_config_json is not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise DataContractError("parameter_config_json must deserialize to an object.")
        specification = HypothesisSpecification(
            hypothesis_id=hypothesis_id,
            hypothesis_version=hypothesis_version,
            parent_hypothesis_id=None,
            economic_rationale=proposal.economic_rationale,
            target_symbol=proposal.target_symbol,
            feature_dependencies=list(proposal.feature_dependencies),
            parameter_config_json=parameter_config_json,
            expected_direction=proposal.expected_direction,
            target_horizons=list(horizons),
            primary_horizon=primary_horizon,
            invalidation_criteria=proposal.proposed_invalidation_criteria,
            registered_at_utc=registered_at_utc,
            author=author,
        )
        return specification