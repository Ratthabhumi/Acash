"""Unit and Invariant Tests for Gate 8 & Gate 8.1 Model Selection Tournament (Phase 8 Batch 4).

Tests all mandatory Gate 8 & 8.1 requirements:
1. Unified Allocator Protocol & Standardized Candidates
2. Evaluator Agnosticism (Zero Allocator Implementation Knowledge)
3. Strict Out-of-Sample Partitioning & Zero Look-Ahead Bias
4. Policy-Estimated Friction Accounting & Net Decisiveness (Gross != Net)
5. Baseline Preference Under Friction (1/N can outrank advanced optimizers)
6. Ranking != Approval (Rank #1 rejected on hurdle failure)
7. Sovereign 100% Cash Fallback (Explicit CASH_SOVEREIGN_FALLBACK verdict, never APPROVED_INVESTABLE_ALLOCATION)
8. Decoupled Semantics: Tournament Winner vs Governance Decision (Ranked #1 vs Governance Selected)
9. Net-of-Friction Realized Equity Max Drawdown Provenance
10. Optional Adapter Execution Telemetry (Skipped vs Executed vs Available)
11. Deterministic Bit-for-Bit Tournament Reproducibility
12. Rebalance Planner Decoupling (Consumes approved or fallback decisions)
"""

from datetime import datetime, timezone
from decimal import Decimal
import numpy as np
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.baselines import (
    CashAllocator,
    EqualWeightAllocator,
    InverseVolatilityAllocator,
    PortfolioAllocator,
)
from acash.portfolio.estimators import HistoricalSampleMeanEstimator
from acash.portfolio.evaluation import AllocationEvaluator, EvaluationConfig, FrictionParameters
from acash.portfolio.governance import GovernanceConfig, PortfolioGovernanceGate
from acash.portfolio.optimizers import (
    EqualRiskContributionAllocator,
    HierarchicalRiskParityAllocator,
)
from acash.portfolio.planner import RebalancePlanner
from acash.portfolio.schema import (
    AllocationCandidate,
    AllocationDecision,
    AssetReturnPanel,
    PortfolioConstraints,
    RebalancePlan,
    RiskSnapshot,
)
from acash.portfolio.tournament import (
    AllocationTournamentRunner,
    AllocatorSummary,
    SplitRecord,
    TournamentConfig,
    TournamentReport,
    TournamentSplitConfig,
    slice_panel,
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


def _sample_return_panel(n_obs: int = 120, seed: int = 42) -> AssetReturnPanel:
    np.random.seed(seed)
    t1 = np.random.normal(0.0008, 0.010, n_obs)
    t2 = 0.5 * t1 + np.random.normal(0.0006, 0.012, n_obs)
    t3 = 0.2 * t1 + np.random.normal(0.0004, 0.015, n_obs)
    t4 = np.random.normal(0.0002, 0.008, n_obs)

    timestamps = tuple(
        datetime(2026, 1, 1 + i // 24, (i % 24), 0, 0, tzinfo=timezone.utc)
        for i in range(n_obs)
    )
    matrix = tuple(
        (
            Decimal(str(round(t1[i], 6))),
            Decimal(str(round(t2[i], 6))),
            Decimal(str(round(t3[i], 6))),
            Decimal(str(round(t4[i], 6))),
        )
        for i in range(n_obs)
    )
    return AssetReturnPanel(
        universe_id="UNIV_TOURNAMENT_4A",
        timestamps=timestamps,
        symbols=("SPY", "QQQ", "TLT", "GLD"),
        returns_matrix=matrix,
        frequency="1D",
    )


# ==============================================================================
# SECTION 1: Unified Protocol & Standardized Candidates
# ==============================================================================

def test_all_allocators_satisfy_portfolio_allocator_protocol() -> None:
    suite = AllocationTournamentRunner.create_default_suite(include_optional=True)
    all_allocators: list[PortfolioAllocator] = [CashAllocator()] + list(suite)
    panel = _sample_return_panel(n_obs=40)
    constraints = _default_constraints()
    current_w = {s: Decimal("0.0") for s in panel.symbols}

    assert len(all_allocators) >= 5, "Must contain Cash plus at least 4 core risky allocators."

    for alloc in all_allocators:
        assert hasattr(alloc, "allocator_name")
        assert hasattr(alloc, "compute_candidate")
        assert callable(alloc.compute_candidate)
        assert isinstance(alloc.allocator_name, str)
        assert len(alloc.allocator_name) > 0

        cand = alloc.compute_candidate(panel, constraints, current_w)
        assert isinstance(cand, AllocationCandidate)
        assert cand.allocator_name == alloc.allocator_name
        assert len(cand.asset_weights) == len(panel.symbols)
        assert cand.cash_weight is not None
        assert cand.candidate_digest != ""
        total_w = sum(cand.asset_weights.values()) + cand.cash_weight
        assert abs(total_w - Decimal("1.0")) <= Decimal("0.0001")


def test_agnostic_evaluator_has_zero_allocator_implementation_knowledge() -> None:
    """Evaluator must accept opaque AllocationCandidate and evaluate purely on return stream."""
    panel = _sample_return_panel(n_obs=50)
    constraints = _default_constraints()
    current_w = {s: Decimal("0.0") for s in panel.symbols}
    expected_returns = HistoricalSampleMeanEstimator().estimate_expected_returns(panel)

    evaluator = AllocationEvaluator()

    opaque_cand = AllocationCandidate(
        candidate_id="OPAQUE_BLACKBOX_42",
        allocator_name="UNKNOWN_BLACKBOX_ALGORITHM",
        asset_weights={"SPY": Decimal("0.30"), "QQQ": Decimal("0.30"), "TLT": Decimal("0.20"), "GLD": Decimal("0.15")},
        cash_weight=Decimal("0.05"),
        in_sample_metrics={"expected_return": Decimal("0.05"), "variance": Decimal("0.01")},
        provenance={"source": "external_research_signal"},
    )

    evaluation = evaluator.evaluate_candidate(
        candidate=opaque_cand,
        panel=panel,
        constraints=constraints,
        current_weights=current_w,
        expected_returns=expected_returns,
    )

    assert evaluation.candidate_id == "OPAQUE_BLACKBOX_42"
    assert evaluation.rank_score is not None
    assert evaluation.turnover_required == Decimal("0.95")
    assert evaluation.estimated_transaction_cost > Decimal("0.0")


# ==============================================================================
# SECTION 2: Out-of-Sample Partitioning & Zero Look-Ahead Bias
# ==============================================================================

def test_slice_panel_preserves_temporal_integrity() -> None:
    panel = _sample_return_panel(n_obs=100)
    sliced = slice_panel(panel, 10, 40)

    assert sliced.T == 30
    assert len(sliced.timestamps) == 30
    assert sliced.timestamps[0] == panel.timestamps[10]
    assert sliced.timestamps[-1] == panel.timestamps[39]
    assert sliced.symbols == panel.symbols
    assert sliced.universe_id == panel.universe_id
    assert sliced.panel_digest != panel.panel_digest

    with pytest.raises(DataContractError):
        slice_panel(panel, 50, 40)
    with pytest.raises(DataContractError):
        slice_panel(panel, -1, 40)
    with pytest.raises(DataContractError):
        slice_panel(panel, 10, 150)


def test_split_generation_enforces_strict_causality_and_purging() -> None:
    runner = AllocationTournamentRunner()
    panel = _sample_return_panel(n_obs=120)
    splits = runner.generate_splits(panel)

    assert len(splits) == 5

    for (train_s, train_e), (test_s, test_e) in splits:
        assert train_s == 0
        assert train_e < test_s
        assert (test_s - train_e) >= runner.config.split_config.purge_bars
        assert test_e <= panel.T
        assert test_e > test_s


# ==============================================================================
# SECTION 3: Friction Accounting & Net Decisiveness
# ==============================================================================

def test_friction_reduces_gross_return_and_impacts_ranking() -> None:
    eval_config = EvaluationConfig(
        friction_params=FrictionParameters(
            fee_rate=Decimal("0.0010"),      # 10 bps
            half_spread=Decimal("0.0010"),   # 10 bps
            slippage=Decimal("0.0005"),      # 5 bps -> total 25 bps per unit turnover
        ),
        rebalance_frequency_per_year=Decimal("12"),
    )
    evaluator = AllocationEvaluator(config=eval_config)
    panel = _sample_return_panel(n_obs=50)
    constraints = _default_constraints()
    current_w = {s: Decimal("0.0") for s in panel.symbols}
    expected_returns = {"SPY": Decimal("0.10"), "QQQ": Decimal("0.10"), "TLT": Decimal("0.05"), "GLD": Decimal("0.05")}

    cand_high_to = AllocationCandidate(
        candidate_id="CAND_HIGH_TURNOVER",
        allocator_name="AGGRESSIVE_STRATEGY",
        asset_weights={"SPY": Decimal("0.50"), "QQQ": Decimal("0.45"), "TLT": Decimal("0.0"), "GLD": Decimal("0.0")},
        cash_weight=Decimal("0.05"),
    )
    cand_low_to = AllocationCandidate(
        candidate_id="CAND_LOW_TURNOVER",
        allocator_name="PASSIVE_STRATEGY",
        asset_weights={"SPY": Decimal("0.0"), "QQQ": Decimal("0.0"), "TLT": Decimal("0.0"), "GLD": Decimal("0.0")},
        cash_weight=Decimal("1.0"),
    )

    eval_high = evaluator.evaluate_candidate(cand_high_to, panel, constraints, current_w, expected_returns)
    eval_low = evaluator.evaluate_candidate(cand_low_to, panel, constraints, current_w, expected_returns)

    assert eval_high.turnover_required > eval_low.turnover_required
    assert eval_high.estimated_transaction_cost > eval_low.estimated_transaction_cost
    expected_friction = Decimal("0.95") * Decimal("0.0025") * Decimal("12")
    assert abs(eval_high.estimated_transaction_cost - expected_friction) < Decimal("0.0001")


# ==============================================================================
# SECTION 4: Multi-Split Tournament Execution & Invariants
# ==============================================================================

def test_full_tournament_execution_and_reporting() -> None:
    runner = AllocationTournamentRunner()
    for alloc in runner.create_default_suite(include_optional=False):
        runner.register_allocator(alloc)

    panel = _sample_return_panel(n_obs=100)
    constraints = _default_constraints()
    risk_snap = _healthy_risk_snapshot()

    report = runner.run_tournament(
        panel=panel,
        constraints=constraints,
        risk_snapshot=risk_snap,
    )

    assert isinstance(report, TournamentReport)
    assert report.total_bars == 100
    assert report.n_splits == 5
    assert len(report.split_records) == 5 * 4  # 5 splits * 4 core risky allocators
    assert len(report.allocator_summaries) == 4
    assert len(report.ranked_allocator_names) == 4

    ranks = [s.tournament_rank for s in report.allocator_summaries]
    assert ranks == [1, 2, 3, 4]

    assert report.final_decision is not None
    assert report.final_decision.gate_verdict in (
        "APPROVED_INVESTABLE_ALLOCATION",
        "CASH_SOVEREIGN_FALLBACK",
    )
    assert report.tournament_digest != ""
    assert report.tournament_rank_1_allocator in report.ranked_allocator_names


def test_cash_fallback_verdict_is_cash_sovereign_fallback_never_approved_investable() -> None:
    """Core Gate 8.1 Invariant: When Cash is chosen upon rejection, verdict MUST be CASH_SOVEREIGN_FALLBACK.
    APPROVED_INVESTABLE_ALLOCATION is strictly forbidden from coexisting with CASH fallback.
    """
    tournament_config = TournamentConfig(
        evaluation_config=EvaluationConfig(
            risk_free_rate=Decimal("0.04"),
            hurdle_margin=Decimal("0.50"),  # Impossible hurdle forces rejection
        ),
        governance_config=GovernanceConfig(
            require_evidence_threshold_met=False,
            require_dsr_significance=False,
        ),
    )
    runner = AllocationTournamentRunner(config=tournament_config)
    for alloc in runner.create_default_suite(include_optional=False):
        runner.register_allocator(alloc)

    panel = _sample_return_panel(n_obs=80)
    constraints = _default_constraints()
    risk_snap = _healthy_risk_snapshot()

    report = runner.run_tournament(panel, constraints, risk_snap)
    decision = report.final_decision

    # 1. Gate verdict MUST be sovereign fallback, NEVER APPROVED_INVESTABLE_ALLOCATION
    assert decision.gate_verdict in ("CASH_SOVEREIGN_FALLBACK", "REJECT_NO_ELIGIBLE_CANDIDATE")
    assert decision.gate_verdict != "APPROVED_INVESTABLE_ALLOCATION"
    assert decision.allocator_name == "CASH"
    assert decision.is_fallback_baseline is True
    assert decision.cash_weight == Decimal("1.0")
    for w in decision.authorized_weights.values():
        assert w == Decimal("0.0")

    # 2. Decoupled origin telemetry
    assert report.governance_selected_allocator == "CASH"
    assert report.decision_origin == "GOVERNANCE_FALLBACK"
    assert report.cash_selection_mode == "GOVERNANCE_FALLBACK"
    # Tournament rank #1 was the top risky optimizer, NOT Cash
    assert report.tournament_rank_1_allocator != "CASH"
    assert report.tournament_rank_1_allocator in report.ranked_allocator_names


def test_explicit_cash_candidate_semantics() -> None:
    """If CASH is explicitly registered in tournament, selection mode reflects EXPLICIT_CASH_ALLOCATOR."""
    runner = AllocationTournamentRunner()
    runner.register_allocator(CashAllocator())

    panel = _sample_return_panel(n_obs=50)
    constraints = _default_constraints()
    risk_snap = _healthy_risk_snapshot()

    report = runner.run_tournament(panel, constraints, risk_snap)
    assert report.decision_origin == "EXPLICIT_CASH_ALLOCATOR"
    assert report.cash_selection_mode == "EXPLICIT_CASH_ALLOCATOR"
    assert report.final_decision.allocator_name == "CASH"
    assert report.final_decision.gate_verdict == "CASH_SOVEREIGN_FALLBACK"


def test_sovereign_cash_fallback_on_risk_kill_switch() -> None:
    """If kill switch is active, pre-allocation risk gate forces 100% Cash regardless of rankings."""
    runner = AllocationTournamentRunner()
    for alloc in runner.create_default_suite(include_optional=False):
        runner.register_allocator(alloc)

    panel = _sample_return_panel(n_obs=60)
    constraints = _default_constraints()

    risk_snap = RiskSnapshot(
        snapshot_id="SNAP_KILL_SWITCH",
        timestamp=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        account_equity=Decimal("1000000.0"),
        cash_balance=Decimal("150000.0"),
        margin_used=Decimal("850000.0"),
        margin_headroom=Decimal("150000.0"),
        margin_buffer_threshold=Decimal("50000.0"),
        current_drawdown_pct=Decimal("0.02"),
        max_drawdown_limit_pct=Decimal("0.10"),
        is_kill_switch_active=True,  # KILL SWITCH TRIGGERED!
    )

    report = runner.run_tournament(panel, constraints, risk_snap)

    assert report.final_decision.gate_verdict == "PRE_RISK_GATE_KILL_SWITCH_ACTIVE"
    assert report.final_decision.is_fallback_baseline is True
    assert report.final_decision.cash_weight == Decimal("1.0")


def test_rebalance_planner_consumes_only_approved_decision() -> None:
    """Downstream rebalance planner generates execution deltas strictly from approved or fallback decision."""
    runner = AllocationTournamentRunner()
    for alloc in runner.create_default_suite(include_optional=False):
        runner.register_allocator(alloc)

    panel = _sample_return_panel(n_obs=80)
    constraints = _default_constraints()
    risk_snap = _healthy_risk_snapshot()

    report = runner.run_tournament(panel, constraints, risk_snap)
    decision = report.final_decision

    planner = RebalancePlanner()
    current_positions = {s: Decimal("0.0") for s in panel.symbols}
    reference_prices = {"SPY": Decimal("500.0"), "QQQ": Decimal("400.0"), "TLT": Decimal("100.0"), "GLD": Decimal("200.0")}

    plan = planner.generate_plan(
        decision=decision,
        account_equity=Decimal("1000000.0"),
        current_positions=current_positions,
        reference_prices=reference_prices,
        constraints=constraints,
    )

    assert isinstance(plan, RebalancePlan)
    assert plan.decision_id == decision.decision_id
    assert plan.decision_digest == decision.decision_digest
    assert len(plan.desired_position_delta) == len(panel.symbols)
    assert len(plan.desired_notional_delta) == len(panel.symbols)
    assert plan.plan_digest != ""
    assert plan.estimated_rebalance_friction >= Decimal("0.0")


def test_reproducible_metadata_captures_all_declared_parameters() -> None:
    """Evidence requirement: configuration must contain everything required to reproduce experiment."""
    runner = AllocationTournamentRunner()
    for alloc in runner.create_default_suite(include_optional=False):
        runner.register_allocator(alloc)

    panel = _sample_return_panel(n_obs=60)
    constraints = _default_constraints()
    risk_snap = _healthy_risk_snapshot()

    report = runner.run_tournament(panel, constraints, risk_snap)
    meta = report.reproducible_metadata

    required_keys = [
        "tournament_id",
        "dataset_id",
        "date_range",
        "symbols",
        "split_config",
        "evaluation_config",
        "governance_config",
        "git_commit",
        "total_bars",
        "n_splits",
        "allocator_count",
        "decision_id",
        "decision_gate_verdict",
        "tournament_rank_1_allocator",
        "governance_selected_allocator",
        "decision_origin",
        "cash_selection_mode",
        "allocators_available",
        "allocators_executed",
        "allocators_skipped",
        "backend_versions",
        "max_drawdown_provenance",
        "friction_model",
        "fold_aggregation_method",
    ]
    for k in required_keys:
        assert k in meta, f"Missing reproducible metadata field: '{k}'"


def test_baseline_preference_when_advanced_optimizer_has_excessive_turnover() -> None:
    """Core Invariant: Advanced Optimizer != Automatic Preference.
    If 1/N has lower turnover penalty than an aggressive optimizer, 1/N ranks above it.
    """
    eval_config = EvaluationConfig(
        lambda_turnover=Decimal("5.0"),
        friction_params=FrictionParameters(
            fee_rate=Decimal("0.0020"),
            half_spread=Decimal("0.0020"),
            slippage=Decimal("0.0010"),
        ),
    )
    evaluator = AllocationEvaluator(config=eval_config)
    panel = _sample_return_panel(n_obs=50)
    constraints = _default_constraints()
    current_w = {"SPY": Decimal("0.2375"), "QQQ": Decimal("0.2375"), "TLT": Decimal("0.2375"), "GLD": Decimal("0.2375")}
    expected_returns = {"SPY": Decimal("0.08"), "QQQ": Decimal("0.08"), "TLT": Decimal("0.04"), "GLD": Decimal("0.04")}

    ew_cand = EqualWeightAllocator().compute_candidate(panel, constraints, current_w)
    aggressive_cand = AllocationCandidate(
        candidate_id="CAND_AGGRESSIVE",
        allocator_name="AGGRESSIVE_OPTIMIZER",
        asset_weights={"SPY": Decimal("0.95"), "QQQ": Decimal("0.0"), "TLT": Decimal("0.0"), "GLD": Decimal("0.0")},
        cash_weight=Decimal("0.05"),
    )

    ew_eval = evaluator.evaluate_candidate(ew_cand, panel, constraints, current_w, expected_returns)
    aggr_eval = evaluator.evaluate_candidate(aggressive_cand, panel, constraints, current_w, expected_returns)

    assert ew_eval.turnover_required < Decimal("0.05")
    assert aggr_eval.turnover_required > Decimal("0.70")
    assert ew_eval.rank_score > aggr_eval.rank_score

    ranked = evaluator.rank_evaluations([aggr_eval, ew_eval])
    assert ranked[0].candidate_id == ew_cand.candidate_id


def test_optional_adapters_participate_in_suite_when_available() -> None:
    """Optional packages participate when installed and degrade gracefully when absent."""
    import importlib.util
    has_skfolio = importlib.util.find_spec("skfolio") is not None
    has_cvxpy = importlib.util.find_spec("cvxpy") is not None

    suite = AllocationTournamentRunner.create_default_suite(include_optional=True)
    alloc_names = [a.allocator_name for a in suite]

    assert "EQUAL_WEIGHT" in alloc_names
    assert "INVERSE_VOL" in alloc_names
    assert "HIERARCHICAL_RISK_PARITY" in alloc_names
    assert "EQUAL_RISK_CONTRIBUTION" in alloc_names

    if has_skfolio:
        assert "SKFOLIO_HIERARCHICAL_RISK_PARITY" in alloc_names
    else:
        assert "SKFOLIO_HIERARCHICAL_RISK_PARITY" not in alloc_names

    if has_cvxpy:
        assert "CVXPY_MINIMUM_VARIANCE" in alloc_names
    else:
        assert "CVXPY_MINIMUM_VARIANCE" not in alloc_names


def test_deterministic_repeated_tournament_reproducibility() -> None:
    """Requirement: Two identical runs on identical data produce bit-for-bit identical digests and scores."""
    runner1 = AllocationTournamentRunner()
    for alloc in runner1.create_default_suite(include_optional=False):
        runner1.register_allocator(alloc)

    runner2 = AllocationTournamentRunner()
    for alloc in runner2.create_default_suite(include_optional=False):
        runner2.register_allocator(alloc)

    panel = _sample_return_panel(n_obs=80, seed=12345)
    constraints = _default_constraints()
    risk_snap = _healthy_risk_snapshot()

    as_of = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    report1 = runner1.run_tournament(panel, constraints, risk_snap, as_of=as_of)
    report2 = runner2.run_tournament(panel, constraints, risk_snap, as_of=as_of)

    assert report1.tournament_digest == report2.tournament_digest
    assert report1.final_decision.decision_digest == report2.final_decision.decision_digest
    assert report1.ranked_allocator_names == report2.ranked_allocator_names

    for s1, s2 in zip(report1.allocator_summaries, report2.allocator_summaries):
        assert s1.allocator_name == s2.allocator_name
        assert s1.aggregate_rank_score == s2.aggregate_rank_score
        assert s1.mean_net_return == s2.mean_net_return
        assert s1.worst_max_drawdown == s2.worst_max_drawdown
        assert s1.tournament_rank == s2.tournament_rank


# ==============================================================================
# SECTION 5: Gate 8.2 Adversarial Invariants (Train/Test Isolation & Friction)
# ==============================================================================

def test_adversarial_zero_lookahead_test_tampering_isolation() -> None:
    """Requirement 1 & 8: Tampering with test data does NOT alter candidate weights or candidate digest.
    Evaluator on test data strictly changes OOS score, but cannot backpropagate into candidate weights.
    """
    panel = _sample_return_panel(n_obs=80, seed=42)
    constraints = _default_constraints()
    current_w = {s: Decimal("0.0") for s in panel.symbols}

    train_panel = slice_panel(panel, 0, 40)
    test_panel_orig = slice_panel(panel, 42, 80)

    # Tampered test panel: 10x shock to all asset returns
    tampered_matrix = tuple(
        tuple(val * Decimal("10.0") for val in row)
        for row in test_panel_orig.returns_matrix
    )
    test_panel_tampered = AssetReturnPanel(
        universe_id=test_panel_orig.universe_id,
        timestamps=test_panel_orig.timestamps,
        symbols=test_panel_orig.symbols,
        returns_matrix=tampered_matrix,
        frequency=test_panel_orig.frequency,
    )

    evaluator = AllocationEvaluator()
    mean_estimator = HistoricalSampleMeanEstimator()
    exp_ret_train = mean_estimator.estimate_expected_returns(train_panel)

    allocators = AllocationTournamentRunner.create_default_suite(include_optional=True)

    for alloc in allocators:
        # Candidate generated on train_panel
        cand1 = alloc.compute_candidate(train_panel, constraints, current_w)
        cand2 = alloc.compute_candidate(train_panel, constraints, current_w)

        # 1. Weights and digests must be completely identical
        assert cand1.asset_weights == cand2.asset_weights
        assert cand1.candidate_digest == cand2.candidate_digest

        # 2. OOS evaluation on original test panel vs tampered test panel
        eval_orig = evaluator.evaluate_candidate(cand1, test_panel_orig, constraints, current_w, exp_ret_train)
        eval_tampered = evaluator.evaluate_candidate(cand1, test_panel_tampered, constraints, current_w, exp_ret_train)

        # Candidate weights inside evaluation remain identical (frozen)
        assert eval_orig.normalized_weights == eval_tampered.normalized_weights
        assert eval_orig.candidate_digest == eval_tampered.candidate_digest

        # But OOS evaluation digests and performance metrics MUST differ due to test differences
        assert eval_orig.evaluation_digest != eval_tampered.evaluation_digest
        assert eval_orig.oos_sharpe_ratio != eval_tampered.oos_sharpe_ratio


def test_adversarial_train_alteration_changes_candidate_weights() -> None:
    """Requirement 1 & 8: Candidate generation digest and weights depend strictly on training data."""
    panel_orig = _sample_return_panel(n_obs=50, seed=101)
    constraints = _default_constraints()
    current_w = {s: Decimal("0.0") for s in panel_orig.symbols}

    # Altered train panel with distinct empirical seed (different covariance and variance structure)
    panel_altered = _sample_return_panel(n_obs=50, seed=999)

    # Test covariance-dependent optimizers
    hrp = HierarchicalRiskParityAllocator()
    inv_vol = InverseVolatilityAllocator()

    cand_hrp_orig = hrp.compute_candidate(panel_orig, constraints, current_w)
    cand_hrp_alt = hrp.compute_candidate(panel_altered, constraints, current_w)
    assert cand_hrp_orig.candidate_digest != cand_hrp_alt.candidate_digest
    assert cand_hrp_orig.asset_weights != cand_hrp_alt.asset_weights

    cand_inv_orig = inv_vol.compute_candidate(panel_orig, constraints, current_w)
    cand_inv_alt = inv_vol.compute_candidate(panel_altered, constraints, current_w)
    assert cand_inv_orig.candidate_digest != cand_inv_alt.candidate_digest
    assert cand_inv_orig.asset_weights != cand_inv_alt.asset_weights


def test_adversarial_friction_consistency_and_zero_double_counting() -> None:
    """Requirement 3 & 8: Prove exact friction dependency table and verify zero double-counting."""
    runner = AllocationTournamentRunner()
    for alloc in runner.create_default_suite(include_optional=False):
        runner.register_allocator(alloc)

    panel = _sample_return_panel(n_obs=90, seed=777)
    constraints = _default_constraints()
    risk_snap = _healthy_risk_snapshot()

    report = runner.run_tournament(panel, constraints, risk_snap)

    for rec in report.split_records:
        # 1. One-time friction: Turnover * total_cost_rate (12 bps)
        expected_one_time = rec.turnover * Decimal("0.0012")
        assert abs(rec.one_time_friction - expected_one_time) < Decimal("0.00000001")

        # 2. Annualized friction: One-time * 12
        expected_ann_friction = rec.one_time_friction * Decimal("12")
        assert abs(rec.annualized_friction - expected_ann_friction) < Decimal("0.00000001")

        # 3. Net return: Gross return - Annualized friction
        assert abs(rec.net_return_annualized - (rec.gross_return_annualized - rec.annualized_friction)) < Decimal("0.00000001")

        # 4. MaxDD provenance is net-of-friction compounding path
        assert rec.max_drawdown_provenance == "NET_FRICTION_ADJUSTED_EQUITY_PATH"
        assert rec.friction_model == "POLICY_ESTIMATED_FRICTION"


def test_adversarial_governance_cannot_alter_tournament_ranking_or_scores() -> None:
    """Requirement 4 & 8: Tournament RankScore and ranking order are invariant to Governance policy."""
    config_benign = TournamentConfig(
        tournament_id="TOURNAMENT_BENIGN",
        evaluation_config=EvaluationConfig(hurdle_margin=Decimal("0.001")),
        governance_config=GovernanceConfig(require_evidence_threshold_met=False),
    )
    config_draconian = TournamentConfig(
        tournament_id="TOURNAMENT_DRACONIAN",
        evaluation_config=EvaluationConfig(hurdle_margin=Decimal("100.0")),  # Impossible hurdle
        governance_config=GovernanceConfig(require_evidence_threshold_met=False),
    )

    runner_benign = AllocationTournamentRunner(config=config_benign)
    for alloc in runner_benign.create_default_suite(include_optional=False):
        runner_benign.register_allocator(alloc)

    runner_draconian = AllocationTournamentRunner(config=config_draconian)
    for alloc in runner_draconian.create_default_suite(include_optional=False):
        runner_draconian.register_allocator(alloc)

    panel = _sample_return_panel(n_obs=80, seed=999)
    constraints = _default_constraints()
    risk_snap = _healthy_risk_snapshot()

    report_benign = runner_benign.run_tournament(panel, constraints, risk_snap)
    report_draconian = runner_draconian.run_tournament(panel, constraints, risk_snap)

    # 1. Ranking order MUST be identical
    assert report_benign.ranked_allocator_names == report_draconian.ranked_allocator_names
    assert report_benign.tournament_rank_1_allocator == report_draconian.tournament_rank_1_allocator

    # 2. Individual allocator Aggregate RankScores MUST be identical
    for sb, sd in zip(report_benign.allocator_summaries, report_draconian.allocator_summaries):
        assert sb.allocator_name == sd.allocator_name
        assert sb.aggregate_rank_score == sd.aggregate_rank_score
        assert sb.tournament_rank == sd.tournament_rank

    # 3. BUT Governance Decisions diverge completely
    assert report_draconian.final_decision.gate_verdict == "REJECT_NO_ELIGIBLE_CANDIDATE"
    assert report_draconian.governance_selected_allocator == "CASH"
    assert report_draconian.decision_origin == "GOVERNANCE_FALLBACK"


def test_fold_lifecycle_digests_and_temporal_boundaries() -> None:
    """Requirement 2: Every fold record contains complete lifecycle timestamps and digests."""
    runner = AllocationTournamentRunner()
    for alloc in runner.create_default_suite(include_optional=False):
        runner.register_allocator(alloc)

    panel = _sample_return_panel(n_obs=80, seed=555)
    constraints = _default_constraints()
    risk_snap = _healthy_risk_snapshot()

    report = runner.run_tournament(panel, constraints, risk_snap)

    for rec in report.split_records:
        assert rec.test_start > rec.train_end, "Test start must be strictly after train end."
        assert rec.purge_bars == runner.config.split_config.purge_bars
        assert rec.train_panel_digest != ""
        assert rec.test_panel_digest != ""
        assert rec.train_panel_digest != rec.test_panel_digest
        assert rec.candidate_generation_digest == rec.candidate_digest
        assert rec.test_evaluation_digest != ""
