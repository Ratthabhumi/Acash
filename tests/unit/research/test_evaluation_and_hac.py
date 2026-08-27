"""Unit tests for HAC Bandwidth Policies, Robustness Checks, and Hypothesis Evaluation (Phase 4)."""

from decimal import Decimal
import pytest

from acash.research.evaluation import (
    determine_hac_bandwidth,
    evaluate_hypothesis_relationship,
)
from acash.research.schema import (
    ExpectedDirection,
    HacBandwidthMethod,
    HacInferencePolicy,
    HypothesisSpecification,
    InvalidationCriteria,
)


def _make_sample_hypothesis() -> HypothesisSpecification:
    return HypothesisSpecification(
        hypothesis_id="HYP-TEST-EVAL",
        hypothesis_version="1.2.0",
        economic_rationale="Testing rationale.",
        target_symbol="ES.FUT",
        feature_dependencies=["feat1"],
        parameter_config_json="{}",
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[1, 5],
        primary_horizon=5,
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.01"),
            min_hac_t_stat=Decimal("1.50"),
        ),
        registered_at_utc="2026-08-28T00:00:00Z",
        author="Research",
    )


def test_hac_bandwidth_determination_methods() -> None:
    """Verify bandwidth determination across baseline, fixed, and plug-in policies."""
    # 1. FIXED_HORIZON_MINUS_ONE: H=5 -> lag=4
    b1 = determine_hac_bandwidth(HacBandwidthMethod.FIXED_HORIZON_MINUS_ONE, sample_size=500, horizon=5)
    assert b1 == 4

    # 2. FIXED_LAG: lag=10
    b2 = determine_hac_bandwidth(HacBandwidthMethod.FIXED_LAG, sample_size=500, horizon=5, fixed_lag=10)
    assert b2 == 10

    # 3. NEWEY_WEST_PLUGIN: T=100 -> floor(4 * 1^(2/9)) = 4
    b3 = determine_hac_bandwidth(HacBandwidthMethod.NEWEY_WEST_PLUGIN, sample_size=100, horizon=5)
    assert b3 == 4


def test_hypothesis_evaluation_and_robustness_matrix() -> None:
    """Verify evaluation generates primary HAC inference and robustness check matrix."""
    hyp = _make_sample_hypothesis()
    policy = HacInferencePolicy(
        bandwidth_method=HacBandwidthMethod.FIXED_HORIZON_MINUS_ONE,
        run_bandwidth_robustness_check=True,
        robustness_lags=[1, 2, 4],
    )

    # 20 samples with positive trend
    features = [Decimal(f"{i * 0.1:.4f}") for i in range(20)]
    fwd_returns = [Decimal(f"{i * 0.0005:.6f}") for i in range(20)]

    res = evaluate_hypothesis_relationship(
        features=features,
        forward_returns=fwd_returns,
        horizon=5,
        hypothesis=hyp,
        hac_policy=policy,
    )

    assert res.horizon == 5
    assert res.selected_hac_lag == 4
    assert res.beta > Decimal("0")
    assert res.spearman_rank_ic is not None
    assert len(res.robustness_matrix) == 3
    assert res.robustness_matrix[0].lag == 1
    assert res.robustness_matrix[1].lag == 2
    assert res.robustness_matrix[2].lag == 4
