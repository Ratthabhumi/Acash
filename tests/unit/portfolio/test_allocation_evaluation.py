"""Unit and invariant tests for Phase 8 Allocation Evaluation Engine."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Mapping
import pytest

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.portfolio.baselines import (
    CashAllocator,
    EqualWeightAllocator,
    InverseVolatilityAllocator,
)
from acash.portfolio.evaluation import (
    AllocationEvaluator,
    EvaluationConfig,
    FrictionParameters,
)
from acash.portfolio.schema import (
    AllocationCandidate,
    AllocationEvaluation,
    AssetReturnPanel,
    PortfolioConstraints,
)


def _sample_panel() -> AssetReturnPanel:
    t1 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    t4 = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)

    # AAPL has positive returns, SPY moderate
    returns = (
        (Decimal("0.02"), Decimal("0.01")),
        (Decimal("0.01"), Decimal("0.005")),
        (Decimal("0.03"), Decimal("-0.005")),
        (Decimal("0.02"), Decimal("0.015")),
    )

    return AssetReturnPanel(
        universe_id="UNIV_TEST",
        timestamps=(t1, t2, t3, t4),
        symbols=("AAPL", "SPY"),
        returns_matrix=returns,
        frequency="1D",
    )


def _default_constraints() -> PortfolioConstraints:
    return PortfolioConstraints(
        min_weight=Decimal("0.0"),
        max_weight=Decimal("1.0"),
        max_gross_leverage=Decimal("1.0"),
        min_cash_buffer=Decimal("0.05"),
    )


def test_turnover_and_friction_calculation() -> None:
    """Verify evaluator calculates one-way turnover and transaction friction with explicit horizon scaling."""
    panel = _sample_panel()
    constraints = _default_constraints()
    evaluator = AllocationEvaluator(
        config=EvaluationConfig(
            rebalance_frequency_per_year=Decimal("12"),
            friction_params=FrictionParameters(
                fee_rate=Decimal("0.0005"),      # 5 bps fee
                half_spread=Decimal("0.0005"),   # 5 bps half spread
                slippage=Decimal("0.0002"),      # 2 bps slippage
            )
        )
    )

    # Candidate: 45% AAPL, 45% SPY, 10% Cash
    candidate = AllocationCandidate(
        candidate_id="CAND_01",
        allocator_name="EQUAL_WEIGHT",
        asset_weights={"AAPL": Decimal("0.45"), "SPY": Decimal("0.45")},
        cash_weight=Decimal("0.10"),
    )

    # Current Portfolio: 100% Cash (0% AAPL, 0% SPY)
    current_weights = {"AAPL": Decimal("0.0"), "SPY": Decimal("0.0")}

    evaluation = evaluator.evaluate_candidate(
        candidate=candidate,
        panel=panel,
        constraints=constraints,
        current_weights=current_weights,
        expected_returns={"AAPL": Decimal("0.20"), "SPY": Decimal("0.10")},
    )

    # Turnover = 0.5 * (|0.45 - 0| + |0.45 - 0| + |0.10 - 1.0|) = 0.5 * (0.45 + 0.45 + 0.90) = 0.90
    assert abs(evaluation.turnover_required - Decimal("0.90")) < Decimal("1e-6")

    # One-time Friction = 0.90 * (0.0005 + 0.0005 + 0.0002) = 0.90 * 0.0012 = 0.00108
    # Annualized Friction (12 events/year) = 0.00108 * 12 = 0.01296
    assert abs(evaluation.estimated_transaction_cost - Decimal("0.01296")) < Decimal("1e-6")


def test_cpcv_fold_aggregation_evaluation() -> None:
    """Verify evaluator executes CPCV combinatorial fold generation and aggregates fold metrics when T >= 20."""
    timestamps = tuple(datetime(2026, 8, 1 + i, 12, 0, 0, tzinfo=timezone.utc) for i in range(25))
    # Return panel of length T=25
    returns = tuple(
        (Decimal(str(round(0.01 * (1 if i % 2 == 0 else -0.5), 4))),
         Decimal(str(round(0.015 * (1 if i % 3 == 0 else -0.2), 4))))
        for i in range(25)
    )
    panel = AssetReturnPanel(
        universe_id="UNIV_CPCV",
        timestamps=timestamps,
        symbols=("AAPL", "SPY"),
        returns_matrix=returns,
        frequency="1D",
    )
    evaluator = AllocationEvaluator(config=EvaluationConfig(cpcv_min_sample_size=20))
    candidate = AllocationCandidate(
        candidate_id="CAND_CPCV",
        allocator_name="EQUAL_WEIGHT",
        asset_weights={"AAPL": Decimal("0.45"), "SPY": Decimal("0.45")},
        cash_weight=Decimal("0.10"),
    )
    evaluation = evaluator.evaluate_candidate(
        candidate=candidate,
        panel=panel,
        constraints=_default_constraints(),
        current_weights={},
        expected_returns={"AAPL": Decimal("0.15"), "SPY": Decimal("0.10")},
    )

    assert evaluation.oos_sharpe_ratio is not None
    assert evaluation.oos_cvar_95 is not None
    assert evaluation.oos_cvar_95 >= Decimal("0.0")


def test_cash_candidate_evaluation() -> None:
    """Verify evaluating a 100% Cash candidate produces zero risky return/cvar and correct net return."""
    panel = _sample_panel()
    constraints = _default_constraints()
    evaluator = AllocationEvaluator()

    cash_cand = CashAllocator().compute_candidate(
        panel=panel,
        constraints=constraints,
        current_weights={"AAPL": Decimal("0.0"), "SPY": Decimal("0.0")},
    )

    evaluation = evaluator.evaluate_candidate(
        candidate=cash_cand,
        panel=panel,
        constraints=constraints,
        current_weights={"AAPL": Decimal("0.0"), "SPY": Decimal("0.0")},
        expected_returns={"AAPL": Decimal("0.20"), "SPY": Decimal("0.10")},
    )

    assert evaluation.normalized_cash_weight == Decimal("1.0")
    assert evaluation.turnover_required == Decimal("0.0")
    # For cash, net excess return is -r_f (since portfolio return is 0, net return = 0 - r_f)
    assert evaluation.net_expected_excess_return == -evaluator.config.risk_free_rate
    assert not evaluation.hurdle_rate_cleared


def test_rank_score_and_deterministic_tie_breaking() -> None:
    """Verify rank_candidates sorts by rank_score descending and applies tie-breaking preference."""
    panel = _sample_panel()
    constraints = _default_constraints()
    evaluator = AllocationEvaluator()

    cand_cash = CashAllocator().compute_candidate(panel, constraints, {})
    cand_ew = EqualWeightAllocator().compute_candidate(panel, constraints, {})
    cand_inv = InverseVolatilityAllocator().compute_candidate(panel, constraints, {})

    expected_returns = {"AAPL": Decimal("0.15"), "SPY": Decimal("0.10")}

    eval_cash = evaluator.evaluate_candidate(cand_cash, panel, constraints, {}, expected_returns)
    eval_ew = evaluator.evaluate_candidate(cand_ew, panel, constraints, {}, expected_returns)
    eval_inv = evaluator.evaluate_candidate(cand_inv, panel, constraints, {}, expected_returns)

    ranked = evaluator.rank_evaluations([eval_cash, eval_ew, eval_inv])
    assert len(ranked) == 3
    # Scores must be in strictly descending order (or equal with tie-breaking)
    assert ranked[0].rank_score >= ranked[1].rank_score >= ranked[2].rank_score


def test_epsilon_rank_tie_precision() -> None:
    """Verify that non-tied higher score strictly beats baseline preference, but tied scores respect preference."""
    evaluator = AllocationEvaluator()

    # Case 1: EW score is strictly higher than Cash -> EW must be #1
    e_cash = AllocationEvaluation(
        candidate_id="CAND_CASH_1",
        normalized_weights={"AAPL": Decimal("0.0"), "SPY": Decimal("0.0")},
        normalized_cash_weight=Decimal("1.0"),
        oos_sharpe_ratio=Decimal("0.0"),
        oos_cvar_95=Decimal("0.0"),
        turnover_required=Decimal("0.0"),
        estimated_transaction_cost=Decimal("0.0"),
        net_expected_excess_return=Decimal("-0.04"),
        hurdle_rate_cleared=False,
        constraints_satisfied=True,
        rank_score=Decimal("1.00"),
    )
    e_ew = AllocationEvaluation(
        candidate_id="CAND_EW_1",
        normalized_weights={"AAPL": Decimal("0.45"), "SPY": Decimal("0.45")},
        normalized_cash_weight=Decimal("0.10"),
        oos_sharpe_ratio=Decimal("1.50"),
        oos_cvar_95=Decimal("0.02"),
        turnover_required=Decimal("0.10"),
        estimated_transaction_cost=Decimal("0.001"),
        net_expected_excess_return=Decimal("0.08"),
        hurdle_rate_cleared=True,
        constraints_satisfied=True,
        rank_score=Decimal("1.44"),
    )
    ranked_1 = evaluator.rank_evaluations([e_cash, e_ew])
    assert ranked_1[0].candidate_id == "CAND_EW_1"

    # Case 2: Tied score within EPSILON_RANK_TIE (1e-8) -> Cash preference must win
    e_cash_tied = AllocationEvaluation(
        candidate_id="CAND_CASH_2",
        normalized_weights={"AAPL": Decimal("0.0"), "SPY": Decimal("0.0")},
        normalized_cash_weight=Decimal("1.0"),
        oos_sharpe_ratio=Decimal("0.0"),
        oos_cvar_95=Decimal("0.0"),
        turnover_required=Decimal("0.0"),
        estimated_transaction_cost=Decimal("0.0"),
        net_expected_excess_return=Decimal("-0.04"),
        hurdle_rate_cleared=False,
        constraints_satisfied=True,
        rank_score=Decimal("1.500000001"),
    )
    e_ew_tied = AllocationEvaluation(
        candidate_id="CAND_EW_2",
        normalized_weights={"AAPL": Decimal("0.45"), "SPY": Decimal("0.45")},
        normalized_cash_weight=Decimal("0.10"),
        oos_sharpe_ratio=Decimal("1.50"),
        oos_cvar_95=Decimal("0.02"),
        turnover_required=Decimal("0.10"),
        estimated_transaction_cost=Decimal("0.001"),
        net_expected_excess_return=Decimal("0.08"),
        hurdle_rate_cleared=True,
        constraints_satisfied=True,
        rank_score=Decimal("1.500000000"),
    )
    ranked_2 = evaluator.rank_evaluations([e_ew_tied, e_cash_tied])
    assert ranked_2[0].candidate_id == "CAND_CASH_2"


def test_cvar_loss_magnitude_positivity() -> None:
    """Verify CVaR is non-negative loss magnitude and penalizes RankScore."""
    panel = _sample_panel()
    constraints = _default_constraints()
    evaluator = AllocationEvaluator()

    cand_ew = EqualWeightAllocator().compute_candidate(panel, constraints, {})
    evaluation = evaluator.evaluate_candidate(
        candidate=cand_ew,
        panel=panel,
        constraints=constraints,
        current_weights={},
        expected_returns={"AAPL": Decimal("0.15"), "SPY": Decimal("0.10")},
    )

    assert evaluation.oos_cvar_95 is not None
    assert evaluation.oos_cvar_95 >= Decimal("0.0")
    # RankScore must be Sharpe - lambda_TO * TO - lambda_Tail * CVaR
    expected_rank = (
        (evaluation.oos_sharpe_ratio or Decimal("0.0"))
        - (evaluator.config.lambda_turnover * evaluation.turnover_required)
        - (evaluator.config.lambda_tail * evaluation.oos_cvar_95)
    )
    assert abs(evaluation.rank_score - expected_rank) < Decimal("1e-6")


def test_evaluation_reproducible_metadata() -> None:
    """Verify AllocationEvaluation artifact contains all reproducible metadata fields."""
    panel = _sample_panel()
    constraints = _default_constraints()
    evaluator = AllocationEvaluator()

    cand_ew = EqualWeightAllocator().compute_candidate(panel, constraints, {})
    evaluation = evaluator.evaluate_candidate(
        candidate=cand_ew,
        panel=panel,
        constraints=constraints,
        current_weights={},
        expected_returns={"AAPL": Decimal("0.15"), "SPY": Decimal("0.10")},
    )

    meta = evaluation.evaluation_metadata
    assert "evaluation_horizon" in meta
    assert "rebalance_frequency_per_year" in meta
    assert "friction_basis" in meta
    assert meta["friction_basis"] == "EXPECTED_ANNUALIZED_POLICY_APPROXIMATION"
    assert "cvar_convention" in meta
    assert meta["cvar_convention"] == "POSITIVE_LOSS_MAGNITUDE"
    assert "sample_sufficiency_status" in meta
    assert "dsr_probability" in meta


def test_evidentiary_sample_sufficiency_flag() -> None:
    """Verify evaluator distinguishes computable sample from configured policy evidence threshold."""
    # Small panel T=4 (below policy threshold 40)
    panel_small = _sample_panel()
    evaluator = AllocationEvaluator(config=EvaluationConfig(configured_evidence_threshold=40))
    cand_ew = EqualWeightAllocator().compute_candidate(panel_small, _default_constraints(), {})
    eval_small = evaluator.evaluate_candidate(
        candidate=cand_ew,
        panel=panel_small,
        constraints=_default_constraints(),
        current_weights={},
        expected_returns={"AAPL": Decimal("0.15"), "SPY": Decimal("0.10")},
    )
    assert eval_small.evaluation_metadata["sample_sufficiency_status"] == "INSUFFICIENT_EVIDENCE"
    assert eval_small.evaluation_metadata["evidence_threshold_policy"] == "CONFIGURED_POLICY_THRESHOLD"

    from datetime import timedelta
    timestamps_large = tuple(datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(days=i) for i in range(45))
    returns_large = tuple((Decimal("0.01"), Decimal("0.015")) for _ in range(45))
    panel_large = AssetReturnPanel(
        universe_id="UNIV_LARGE",
        timestamps=timestamps_large,
        symbols=("AAPL", "SPY"),
        returns_matrix=returns_large,
        frequency="1D",
    )
    cand_large = EqualWeightAllocator().compute_candidate(panel_large, _default_constraints(), {})
    eval_large = evaluator.evaluate_candidate(
        candidate=cand_large,
        panel=panel_large,
        constraints=_default_constraints(),
        current_weights={},
        expected_returns={"AAPL": Decimal("0.15"), "SPY": Decimal("0.10")},
    )
    assert eval_large.evaluation_metadata["sample_sufficiency_status"] == "EVIDENCE_THRESHOLD_MET"


def test_dsr_selection_history_provenance() -> None:
    """Verify DSR probability accounts for multiple search trials and trial variance."""
    from datetime import timedelta
    timestamps = tuple(datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(days=i) for i in range(30))
    returns = tuple(
        (Decimal(str(round(0.02 * (1 if i % 2 == 0 else -0.3), 4))),
         Decimal(str(round(0.01 * (1 if i % 3 == 0 else -0.1), 4))))
        for i in range(30)
    )
    panel = AssetReturnPanel(
        universe_id="UNIV_DSR",
        timestamps=timestamps,
        symbols=("AAPL", "SPY"),
        returns_matrix=returns,
        frequency="1D",
    )
    evaluator = AllocationEvaluator()

    # Candidate 1: Single trial K=1
    cand_k1 = AllocationCandidate(
        candidate_id="CAND_K1",
        allocator_name="EQUAL_WEIGHT",
        asset_weights={"AAPL": Decimal("0.5"), "SPY": Decimal("0.5")},
        search_trials_k=1,
        trial_variance=0.0,
    )
    eval_k1 = evaluator.evaluate_candidate(
        candidate=cand_k1,
        panel=panel,
        constraints=_default_constraints(),
        current_weights={},
        expected_returns={"AAPL": Decimal("0.15"), "SPY": Decimal("0.10")},
    )
    assert eval_k1.evaluation_metadata["dsr_trials_k"] == "1"
    assert eval_k1.evaluation_metadata["dsr_selection_mode"] == "SINGLE_TRIAL"
    assert eval_k1.evaluation_metadata["dsr_expected_max_sharpe_sr0"] == "0.0"

    # Candidate 2: Multiple trials K=25 with trial_variance=0.5
    cand_k25 = AllocationCandidate(
        candidate_id="CAND_K25",
        allocator_name="EQUAL_WEIGHT",
        asset_weights={"AAPL": Decimal("0.5"), "SPY": Decimal("0.5")},
        search_trials_k=25,
        trial_variance=0.5,
    )
    eval_k25 = evaluator.evaluate_candidate(
        candidate=cand_k25,
        panel=panel,
        constraints=_default_constraints(),
        current_weights={},
        expected_returns={"AAPL": Decimal("0.15"), "SPY": Decimal("0.10")},
    )
    assert eval_k25.evaluation_metadata["dsr_trials_k"] == "25"
    assert eval_k25.evaluation_metadata["dsr_selection_mode"] == "MULTIPLE_TRIAL"
    assert float(eval_k25.evaluation_metadata["dsr_expected_max_sharpe_sr0"]) > 0.0
    # DSR probability with K=25 selection deflation must be strictly lower than or equal to single trial K=1
    assert float(eval_k25.evaluation_metadata["dsr_probability"]) <= float(eval_k1.evaluation_metadata["dsr_probability"])


def test_cvar_zero_downside_and_tail_diagnostics() -> None:
    """Verify CVaR validity categorization distinguishes zero downside from valid tail."""
    timestamps = tuple(datetime(2026, 8, 1 + i, 12, 0, 0, tzinfo=timezone.utc) for i in range(4))
    # All returns positive -> zero downside in sample
    returns_pos = tuple((Decimal("0.01"), Decimal("0.02")) for _ in range(4))
    panel_pos = AssetReturnPanel(
        universe_id="UNIV_POS",
        timestamps=timestamps,
        symbols=("AAPL", "SPY"),
        returns_matrix=returns_pos,
        frequency="1D",
    )
    evaluator = AllocationEvaluator()
    cand = AllocationCandidate(
        candidate_id="CAND_POS",
        allocator_name="EQUAL_WEIGHT",
        asset_weights={"AAPL": Decimal("0.5"), "SPY": Decimal("0.5")},
    )
    eval_pos = evaluator.evaluate_candidate(
        candidate=cand,
        panel=panel_pos,
        constraints=_default_constraints(),
        current_weights={},
        expected_returns={"AAPL": Decimal("0.15"), "SPY": Decimal("0.10")},
    )
    assert eval_pos.evaluation_metadata["negative_return_count"] == "0"
    assert eval_pos.evaluation_metadata["cvar_validity_status"] == "ZERO_DOWNSIDE_IN_SAMPLE"
    assert eval_pos.oos_cvar_95 == Decimal("0.0")


def test_evaluator_missing_expected_return_fail_closed() -> None:
    """Verify evaluator fails closed when expected returns mapping is missing an asset."""
    panel = _sample_panel()
    constraints = _default_constraints()
    evaluator = AllocationEvaluator()

    cand_ew = EqualWeightAllocator().compute_candidate(panel, constraints, {})
    # Missing SPY in expected_returns
    with pytest.raises(DataContractError, match="Missing expected return for asset"):
        evaluator.evaluate_candidate(
            candidate=cand_ew,
            panel=panel,
            constraints=constraints,
            current_weights={},
            expected_returns={"AAPL": Decimal("0.15")},
        )
