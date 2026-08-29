"""Unit tests for Phase 4 Research Schemas, Pydantic Models, and Cost Conversions."""

from decimal import Decimal
import json
import pyarrow as pa
import pytest

from acash.research.schema import (
    CANONICAL_FORWARD_OUTCOMES_SCHEMA,
    CANONICAL_HYPOTHESIS_EVALUATION_SCHEMA,
    CostModelConfig,
    ExpectedDirection,
    HacBandwidthMethod,
    HacInferencePolicy,
    HypothesisSpecification,
    InvalidationCriteria,
    OosExposureState,
    ResearchSearchRecord,
    SplitPolicy,
)


def test_hypothesis_specification_model_and_serialization() -> None:
    """Verify HypothesisSpecification enforces typed fields and serializes canonically."""
    crit = InvalidationCriteria(
        min_in_sample_rank_ic=Decimal("0.03"),
        min_hac_t_stat=Decimal("2.2"),
        max_feature_autocorrelation=Decimal("0.95"),
        min_cost_adjusted_spread_ratio=Decimal("1.8"),
    )

    hyp = HypothesisSpecification(
        hypothesis_id="HYP-001-OBI-MOMENTUM",
        hypothesis_version="1.2.0",
        economic_rationale="Order book imbalance exerts short-term inventory adjustment pressure on next-bar prices.",
        target_symbol="ES.FUT",
        feature_dependencies=["obi_top5"],
        parameter_config_json='{"obi_depth": 5}',
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[1, 5, 15],
        primary_horizon=5,
        invalidation_criteria=crit,
        registered_at_utc="2026-08-28T00:00:00Z",
        author="Quantitative Research",
    )

    json_str = hyp.to_canonical_json()
    assert '"hypothesis_id":"HYP-001-OBI-MOMENTUM"' in json_str
    assert '"primary_horizon":{"__type__":"int","value":5}' in json_str



def test_cost_model_config_basis_point_conversion() -> None:
    """Verify CostModelConfig converts basis points to exact decimal return units."""
    # 1.5 bps spread + 0.5 bps fee + 1.0 bps slippage = 3.0 bps = 0.000300
    cost_cfg = CostModelConfig(
        quoted_spread_bps=Decimal("1.5"),
        roundtrip_broker_fee_bps=Decimal("0.5"),
        fixed_slippage_bps=Decimal("1.0"),
        latency_delay_ms=25,
    )
    assert cost_cfg.total_roundtrip_cost_decimal == Decimal("0.0003")


def test_canonical_arrow_schemas() -> None:
    """Verify PyArrow schemas for outcomes and evaluations."""
    fwd_names = CANONICAL_FORWARD_OUTCOMES_SCHEMA.names
    assert "symbol" in fwd_names
    assert "horizon_bars" in fwd_names
    assert "forward_return" in fwd_names
    assert "is_purged_boundary" in fwd_names

    eval_names = CANONICAL_HYPOTHESIS_EVALUATION_SCHEMA.names
    assert "hypothesis_id" in eval_names
    assert "beta" in eval_names
    assert "hac_t_stat" in eval_names
    assert "tier3_economic_edge_bps" in eval_names
