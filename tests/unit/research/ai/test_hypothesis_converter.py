"""Hypothesis converter tests.

The converter is strict and human-gated: it returns a canonical
``HypothesisSpecification`` artifact only, with zero registration,
backtesting, execution, or trading authority.
"""

import pytest
from decimal import Decimal

from acash.core.domain.exceptions import DataContractError
from acash.research.ai.hypothesis.converter import HypothesisProposalConverter
from acash.research.ai.schema import AIHypothesisProposal
from acash.research.schema import (
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
)


def _valid_proposal() -> AIHypothesisProposal:
    return AIHypothesisProposal(
        proposal_id="AI-HYP-0011223344556677",
        economic_rationale="Opening volume surge drives directional trend continuation across morning session.",
        market_microstructure_mechanism="Opening cross auction order unbundling creates inventory imbalance.",
        invalidation_conditions=("Rank IC < 0.02",),
        target_symbol="NQ",
        target_timeframe="M5",
        feature_dependencies=("close", "ema_fast"),
        expected_direction=ExpectedDirection.LONG,
        target_horizons=(1, 6),
        proposed_invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.025"),
            min_hac_t_stat=Decimal("2.00"),
            max_feature_autocorrelation=Decimal("0.98"),
            min_cost_adjusted_spread_ratio=Decimal("1.50"),
        ),
        source_metadata_id="SRC-0011223344556677",
        llm_provider="mock",
        llm_model_id="mock-model-v1",
        prompt_template_sha256="0" * 64,
        temperature=Decimal("0.0"),
        seed=1,
        generated_at_utc="2026-09-08T13:00:00+00:00",
        raw_response_sha256="1" * 64,
    )


def test_strict_conversion_maps_all_fields() -> None:
    converter = HypothesisProposalConverter()
    proposal = _valid_proposal()
    spec = converter.to_hypothesis_specification(
        proposal,
        hypothesis_id="HYP-CONV-0001",
        hypothesis_version="1.0.0",
        author="human-researcher",
        registered_at_utc="2026-09-08T14:00:00+00:00",
        primary_horizon=1,
        parameter_config_json='{"max_lookback_ema": 200}',
    )
    assert isinstance(spec, HypothesisSpecification)
    assert spec.hypothesis_id == "HYP-CONV-0001"
    assert spec.economic_rationale == proposal.economic_rationale
    assert spec.target_symbol == "NQ"
    assert spec.feature_dependencies == list(proposal.feature_dependencies)
    assert spec.expected_direction == ExpectedDirection.LONG
    assert spec.primary_horizon == 1
    assert spec.target_horizons == [1, 6]
    assert spec.invalidation_criteria.min_in_sample_rank_ic == Decimal("0.025")


def test_conversion_rejects_primary_horizon_outside_targets() -> None:
    converter = HypothesisProposalConverter()
    with pytest.raises(DataContractError):
        converter.to_hypothesis_specification(
            _valid_proposal(),
            hypothesis_id="HYP-CONV-0002",
            hypothesis_version="1.0.0",
            author="human-researcher",
            registered_at_utc="2026-09-08T14:00:00+00:00",
            primary_horizon=120,
            parameter_config_json="{}",
        )


def test_conversion_rejects_invalid_parameter_config_json() -> None:
    converter = HypothesisProposalConverter()
    with pytest.raises(DataContractError):
        converter.to_hypothesis_specification(
            _valid_proposal(),
            hypothesis_id="HYP-CONV-0003",
            hypothesis_version="1.0.0",
            author="human-researcher",
            registered_at_utc="2026-09-08T14:00:00+00:00",
            primary_horizon=1,
            parameter_config_json="not-json",
        )


def test_conversion_rejects_non_object_parameter_config() -> None:
    converter = HypothesisProposalConverter()
    with pytest.raises(DataContractError):
        converter.to_hypothesis_specification(
            _valid_proposal(),
            hypothesis_id="HYP-CONV-0004",
            hypothesis_version="1.0.0",
            author="human-researcher",
            registered_at_utc="2026-09-08T14:00:00+00:00",
            primary_horizon=6,
            parameter_config_json='["array", "not", "object"]',
        )


def test_conversion_is_pure_without_side_effects() -> None:
    converter = HypothesisProposalConverter()
    spec = converter.to_hypothesis_specification(
        _valid_proposal(),
        hypothesis_id="HYP-CONV-0005",
        hypothesis_version="1.0.0",
        author="human-researcher",
        registered_at_utc="2026-09-08T14:00:00+00:00",
        primary_horizon=1,
        parameter_config_json="{}",
    )
    assert spec.parent_hypothesis_id is None
    assert spec.hypothesis_id == "HYP-CONV-0005"