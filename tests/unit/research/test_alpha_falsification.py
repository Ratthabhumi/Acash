"""Unit & Adversarial Tests for Phase 8.5 Computable Falsification & Trigger Engine (Slice 3).

Covers:
- LESS_THAN, GREATER_THAN, LESS_EQUAL, GREATER_EQUAL comparison operators.
- Exact equality boundary condition semantics.
- Non-finite (NaN, Inf) fail-closed rejection.
- Trigger battery evaluation across multi-metric observation payloads.
- Missing metric error handling in battery evaluation.
- build_falsification_triggers_from_invalidation_criteria canonical adapter.
- Invariant: Trigger evaluation detects condition only (does not mutate state or grant capital).
- Immutability & extra="forbid" preservation.
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from acash.core.domain.exceptions import DataContractError
from acash.research.alpha_schema import (
    AlphaFalsificationTrigger,
    FalsificationComparisonOperator,
)
from acash.research.qualification import (
    build_falsification_triggers_from_invalidation_criteria,
    check_has_any_falsification_triggered,
    evaluate_falsification_battery,
    evaluate_falsification_trigger,
)
from acash.research.schema import InvalidationCriteria


# ---------------------------------------------------------------------------
# 1. Single Trigger Evaluation & Operator Tests
# ---------------------------------------------------------------------------


def test_falsification_trigger_less_than_operator() -> None:
    """Verify LESS_THAN trigger trips strictly when observed < threshold."""
    trigger = AlphaFalsificationTrigger(
        trigger_name="OOS_RANK_IC_DEGRADATION",
        metric_name="rank_ic",
        threshold_value=Decimal("0.025"),
        comparison_operator=FalsificationComparisonOperator.LESS_THAN,
    )

    # 1. Observed >= threshold -> NOT triggered
    eval_pass = evaluate_falsification_trigger(trigger, Decimal("0.030"))
    assert eval_pass.is_triggered is False
    assert eval_pass.observed_value == Decimal("0.030")
    assert eval_pass.trigger_reason is None

    # 2. Boundary: Observed == threshold -> NOT triggered
    eval_boundary = evaluate_falsification_trigger(trigger, Decimal("0.025"))
    assert eval_boundary.is_triggered is False
    assert eval_boundary.trigger_reason is None

    # 3. Observed < threshold -> TRIGGERED
    eval_fail = evaluate_falsification_trigger(trigger, Decimal("0.015"))
    assert eval_fail.is_triggered is True
    assert eval_fail.observed_value == Decimal("0.015")
    assert eval_fail.trigger_reason is not None
    assert "tripped" in eval_fail.trigger_reason
    assert "0.015 < threshold 0.025" in eval_fail.trigger_reason


def test_falsification_trigger_greater_than_operator() -> None:
    """Verify GREATER_THAN trigger trips strictly when observed > threshold."""
    trigger = AlphaFalsificationTrigger(
        trigger_name="FEATURE_AUTOCORRELATION_SATURATION",
        metric_name="autocorrelation_lag1",
        threshold_value=Decimal("0.98"),
        comparison_operator=FalsificationComparisonOperator.GREATER_THAN,
    )

    # 1. Observed <= threshold -> NOT triggered
    eval_pass = evaluate_falsification_trigger(trigger, Decimal("0.95"))
    assert eval_pass.is_triggered is False
    assert eval_pass.trigger_reason is None

    # 2. Boundary: Observed == threshold -> NOT triggered
    eval_boundary = evaluate_falsification_trigger(trigger, Decimal("0.98"))
    assert eval_boundary.is_triggered is False

    # 3. Observed > threshold -> TRIGGERED
    eval_fail = evaluate_falsification_trigger(trigger, Decimal("0.99"))
    assert eval_fail.is_triggered is True
    assert eval_fail.observed_value == Decimal("0.99")
    assert eval_fail.trigger_reason is not None
    assert "0.99 > threshold 0.98" in eval_fail.trigger_reason


def test_falsification_trigger_inclusive_operators() -> None:
    """Verify LESS_EQUAL and GREATER_EQUAL inclusive boundary operators."""
    trigger_le = AlphaFalsificationTrigger(
        trigger_name="DRAWDOWN_CRITICAL_FLOOR",
        metric_name="drawdown_pct",
        threshold_value=Decimal("15.0"),
        comparison_operator=FalsificationComparisonOperator.LESS_EQUAL,
    )
    # Exact boundary trips LESS_EQUAL
    assert evaluate_falsification_trigger(trigger_le, Decimal("15.0")).is_triggered is True
    assert evaluate_falsification_trigger(trigger_le, Decimal("15.01")).is_triggered is False

    trigger_ge = AlphaFalsificationTrigger(
        trigger_name="VOLATILITY_BURST",
        metric_name="volatility_ann",
        threshold_value=Decimal("0.40"),
        comparison_operator=FalsificationComparisonOperator.GREATER_EQUAL,
    )
    # Exact boundary trips GREATER_EQUAL
    assert evaluate_falsification_trigger(trigger_ge, Decimal("0.40")).is_triggered is True
    assert evaluate_falsification_trigger(trigger_ge, Decimal("0.399")).is_triggered is False


# ---------------------------------------------------------------------------
# 2. Non-Finite & Fail-Closed Robustness Tests
# ---------------------------------------------------------------------------


def test_falsification_trigger_rejects_non_finite_inputs() -> None:
    """Verify non-finite (NaN, Inf) or malformed observed values raise DataContractError."""
    trigger = AlphaFalsificationTrigger(
        trigger_name="TEST_TRIGGER",
        metric_name="metric",
        threshold_value=Decimal("1.0"),
        comparison_operator=FalsificationComparisonOperator.LESS_THAN,
    )

    with pytest.raises(DataContractError, match="Non-finite"):
        evaluate_falsification_trigger(trigger, Decimal("NaN"))

    with pytest.raises(DataContractError, match="Non-finite"):
        evaluate_falsification_trigger(trigger, Decimal("Infinity"))

    with pytest.raises(DataContractError, match="Unsupported type"):
        evaluate_falsification_trigger(trigger, None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 3. Battery Evaluation Tests
# ---------------------------------------------------------------------------


def test_falsification_battery_evaluation_clean_pass() -> None:
    """Verify that when all metrics satisfy criteria, no triggers in battery trip."""
    criteria = InvalidationCriteria(
        min_in_sample_rank_ic=Decimal("0.025"),
        min_hac_t_stat=Decimal("2.00"),
        max_feature_autocorrelation=Decimal("0.98"),
        min_cost_adjusted_spread_ratio=Decimal("1.50"),
    )
    triggers = build_falsification_triggers_from_invalidation_criteria(criteria)
    assert len(triggers) == 4

    observed_metrics = {
        "rank_ic": Decimal("0.045"),          # > 0.025 (PASS)
        "hac_t_stat": Decimal("2.85"),         # > 2.00 (PASS)
        "autocorrelation_lag1": Decimal("0.72"), # < 0.98 (PASS)
        "spread_ratio": Decimal("2.10"),       # > 1.50 (PASS)
    }

    evaluated_battery = evaluate_falsification_battery(triggers, observed_metrics)
    assert len(evaluated_battery) == 4
    assert check_has_any_falsification_triggered(evaluated_battery) is False
    assert all(t.is_triggered is False for t in evaluated_battery)


def test_falsification_battery_evaluation_detects_single_tripped_trigger() -> None:
    """Verify that a single invalidation in the battery is detected deterministically."""
    criteria = InvalidationCriteria()
    triggers = build_falsification_triggers_from_invalidation_criteria(criteria)

    observed_metrics = {
        "rank_ic": Decimal("0.045"),
        "hac_t_stat": Decimal("1.20"),  # FAILS (< 2.00 threshold)
        "autocorrelation_lag1": Decimal("0.50"),
        "spread_ratio": Decimal("3.00"),
    }

    evaluated_battery = evaluate_falsification_battery(triggers, observed_metrics)
    assert check_has_any_falsification_triggered(evaluated_battery) is True

    # Identify exact tripped trigger
    tripped = [t for t in evaluated_battery if t.is_triggered]
    assert len(tripped) == 1
    assert tripped[0].trigger_name == "HAC_T_STAT_INSIGNIFICANCE"
    assert "hac_t_stat=1.20 < threshold 2.00" in (tripped[0].trigger_reason or "")


def test_falsification_battery_missing_metric_raises_data_contract_error() -> None:
    """Verify that missing a required metric in the battery raises DataContractError."""
    criteria = InvalidationCriteria()
    triggers = build_falsification_triggers_from_invalidation_criteria(criteria)

    # Incomplete metric payload (missing spread_ratio)
    incomplete_metrics = {
        "rank_ic": Decimal("0.045"),
        "hac_t_stat": Decimal("2.50"),
        "autocorrelation_lag1": Decimal("0.50"),
    }

    with pytest.raises(DataContractError, match="Missing required metric 'spread_ratio'"):
        evaluate_falsification_battery(triggers, incomplete_metrics, require_all_metrics=True)

    # With require_all_metrics=False, unobserved trigger remains untouched
    battery_lenient = evaluate_falsification_battery(triggers, incomplete_metrics, require_all_metrics=False)
    assert len(battery_lenient) == 4
    unobserved = [t for t in battery_lenient if t.metric_name == "spread_ratio"][0]
    assert unobserved.observed_value is None
    assert unobserved.is_triggered is False


# ---------------------------------------------------------------------------
# 4. Immutability & Separation of Concerns Tests
# ---------------------------------------------------------------------------


def test_falsification_trigger_immutability_preserved() -> None:
    """Verify that trigger evaluation produces new frozen models and leaves inputs untouched."""
    original = AlphaFalsificationTrigger(
        trigger_name="OOS_RANK_IC_DEGRADATION",
        metric_name="rank_ic",
        threshold_value=Decimal("0.025"),
        comparison_operator=FalsificationComparisonOperator.LESS_THAN,
    )
    assert original.is_triggered is False
    assert original.observed_value is None

    evaluated = evaluate_falsification_trigger(original, Decimal("0.010"))
    assert evaluated.is_triggered is True
    assert evaluated.observed_value == Decimal("0.010")

    # Original model is completely unmutated
    assert original.is_triggered is False
    assert original.observed_value is None

    # Mutation attempt on evaluated model raises ValidationError
    with pytest.raises(ValidationError, match="Instance is frozen"):
        evaluated.is_triggered = False
