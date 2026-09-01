"""Phase 8 Allocation Tournament Engine (Gate 8.1 Semantic Hardened).

Provides an objective, out-of-sample empirical model-selection tournament across all
candidate asset allocators (Baselines, Native Optimizers, and Optional Adapters).

Strictly enforces:
1. Invariant: Candidate != Evaluation != Decision
2. Invariant: Ranking != Approval
3. Invariant: Advanced Optimizer != Automatic Preference
4. Invariant: CASH is Sovereign Capital Preservation Benchmark & Fallback (not a competing covariance optimizer).
5. Invariant: APPROVED_INVESTABLE_ALLOCATION != CASH_SOVEREIGN_FALLBACK.
6. Zero Look-Ahead Bias: In-sample train strictly isolated from out-of-sample test.
7. Zero Floating-Point Leakage: Decision weights and money quantities remain Decimal.
8. Zero Privilege: All candidates evaluated through identical opaque metrics.
9. Policy-Estimated Friction: Linear 12 bps model annualized by rebalance frequency; not realized broker cost.
10. Net Max Drawdown Provenance: Evaluated on net-of-friction compounding equity path.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import sys
from typing import Any, List, Mapping, Optional, Sequence, Tuple
import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.exceptions import DataContractError
from acash.portfolio.baselines import (
    CashAllocator,
    EqualWeightAllocator,
    InverseVolatilityAllocator,
    PortfolioAllocator,
)
from acash.portfolio.estimators import HistoricalSampleMeanEstimator
from acash.portfolio.evaluation import AllocationEvaluator, EvaluationConfig
from acash.portfolio.governance import GovernanceConfig, PortfolioGovernanceGate
from acash.portfolio.optimizers import (
    EqualRiskContributionAllocator,
    HierarchicalRiskParityAllocator,
)
from acash.portfolio.schema import (
    AllocationCandidate,
    AllocationDecision,
    AllocationEvaluation,
    AssetReturnPanel,
    PortfolioConstraints,
    RiskSnapshot,
)
from acash.validation.deflated_sharpe import DeflatedSharpeEngine


def _sha256_hexdigest(obj: Any) -> str:
    serialized = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def slice_panel(panel: AssetReturnPanel, start_idx: int, end_idx: int) -> AssetReturnPanel:
    """Slice an AssetReturnPanel along the time dimension without mutating symbols or universe."""
    if start_idx < 0 or end_idx > panel.T or start_idx >= end_idx:
        raise DataContractError(
            f"Invalid slice bounds [{start_idx}:{end_idx}] for panel of length {panel.T}."
        )
    sub_timestamps = panel.timestamps[start_idx:end_idx]
    sub_matrix = panel.returns_matrix[start_idx:end_idx]
    return AssetReturnPanel(
        universe_id=panel.universe_id,
        timestamps=sub_timestamps,
        symbols=panel.symbols,
        returns_matrix=sub_matrix,
        frequency=panel.frequency,
    )


class TournamentSplitConfig(BaseModel):
    """Configuration for out-of-sample partitioning across the empirical timeline."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    split_mode: str = "WALK_FORWARD"  # WALK_FORWARD or K_FOLD
    n_splits: int = 5
    train_ratio: Decimal = Decimal("0.70")
    purge_bars: int = 2
    random_seed: Optional[int] = 42


class TournamentConfig(BaseModel):
    """Authoritative reproducibility configuration for an allocation tournament."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    tournament_id: str = "TOURNAMENT_PHASE8_GATE8"
    dataset_id: str = "EMPIRICAL_PANEL"
    split_config: TournamentSplitConfig = Field(default_factory=TournamentSplitConfig)
    evaluation_config: EvaluationConfig = Field(default_factory=EvaluationConfig)
    governance_config: GovernanceConfig = Field(default_factory=GovernanceConfig)
    annualization_factor: Decimal = Decimal("252")
    git_commit: str = "8ccbdb2"


class SplitRecord(BaseModel):
    """Performance and telemetry record for a single allocator on a single OOS split."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    split_index: int
    train_bars: int
    test_bars: int
    purge_bars: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    train_panel_digest: str
    test_panel_digest: str
    allocator_name: str
    candidate_id: str
    candidate_digest: str
    candidate_generation_digest: str
    test_evaluation_digest: str
    weights: Mapping[str, Decimal]
    cash_weight: Decimal
    turnover: Decimal
    one_time_friction: Decimal
    annualized_friction: Decimal
    gross_return_annualized: Decimal
    net_return_annualized: Decimal
    volatility_annualized: Decimal
    gross_sharpe: Decimal
    net_sharpe: Decimal
    max_drawdown: Decimal
    cvar_95: Decimal
    hurdle_rate_cleared: bool
    rank_score: Decimal
    max_drawdown_provenance: str = "NET_FRICTION_ADJUSTED_EQUITY_PATH"
    friction_model: str = "POLICY_ESTIMATED_FRICTION"
    fold_aggregation_method: str = "ARITHMETIC_MEAN_ACROSS_SPLITS"


class AllocatorSummary(BaseModel):
    """Aggregated out-of-sample performance and governance scorecard for an allocator."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    allocator_name: str
    backend_package: str
    n_splits_evaluated: int
    mean_turnover: Decimal
    total_friction_cost: Decimal
    mean_gross_return: Decimal
    mean_net_return: Decimal
    mean_net_sharpe: Decimal
    mean_volatility: Decimal
    worst_max_drawdown: Decimal
    mean_cvar_95: Decimal
    hurdle_clearance_rate: Decimal
    deflated_sharpe_probability: Decimal
    aggregate_rank_score: Decimal
    tournament_rank: int
    is_governance_approved: bool
    governance_verdict: str
    rejection_reason: Optional[str] = None


class TournamentReport(BaseModel):
    """Complete, immutable empirical tournament report and decision audit record."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    tournament_id: str
    dataset_id: str
    universe_id: str
    symbols: Tuple[str, ...]
    date_range: Tuple[datetime, datetime]
    total_bars: int
    n_splits: int
    split_records: Tuple[SplitRecord, ...]
    allocator_summaries: Tuple[AllocatorSummary, ...]
    ranked_allocator_names: Tuple[str, ...]
    tournament_rank_1_allocator: str
    governance_selected_allocator: str
    decision_origin: str  # RANKED_WINNER, GOVERNANCE_FALLBACK, or EXPLICIT_CASH_ALLOCATOR
    cash_selection_mode: str  # NONE, GOVERNANCE_FALLBACK, or EXPLICIT_CASH_ALLOCATOR
    allocators_available: Tuple[str, ...]
    allocators_executed: Tuple[str, ...]
    allocators_skipped: Mapping[str, str]
    backend_versions: Mapping[str, str]
    final_decision: AllocationDecision
    reproducible_metadata: Mapping[str, Any]
    tournament_digest: str


class AllocationTournamentRunner:
    """Orchestrates multi-split empirical out-of-sample tournament evaluation and governance."""

    def __init__(
        self,
        config: Optional[TournamentConfig] = None,
        evaluator: Optional[AllocationEvaluator] = None,
        governance_gate: Optional[PortfolioGovernanceGate] = None,
    ) -> None:
        self.config = config or TournamentConfig()
        self.evaluator = evaluator or AllocationEvaluator(config=self.config.evaluation_config)
        self.governance_gate = governance_gate or PortfolioGovernanceGate(config=self.config.governance_config)
        self._allocators: list[PortfolioAllocator] = []

    def register_allocator(self, allocator: PortfolioAllocator) -> None:
        """Register an allocator candidate into the tournament."""
        self._allocators.append(allocator)

    @classmethod
    def create_default_suite(cls, include_optional: bool = True) -> list[PortfolioAllocator]:
        """Create canonical suite of competing risky asset allocation models.

        Per Gate 8.1 architecture:
        CASH is the sovereign capital preservation benchmark and governance fallback;
        it does not compete against optimizers in the tournament ranking table.
        """
        suite: list[PortfolioAllocator] = [
            EqualWeightAllocator(),
            InverseVolatilityAllocator(),
            HierarchicalRiskParityAllocator(),
            EqualRiskContributionAllocator(),
        ]
        if include_optional:
            import importlib.util
            if importlib.util.find_spec("skfolio") is not None:
                from acash.portfolio.adapters.skfolio_adapter import SkfolioHRPAdapter
                suite.append(SkfolioHRPAdapter())
            if importlib.util.find_spec("cvxpy") is not None:
                from acash.portfolio.adapters.cvxpy_adapter import CvxpyMeanRiskAdapter
                suite.append(CvxpyMeanRiskAdapter())
        return suite

    @classmethod
    def get_candidate_universe_manifest(cls) -> Tuple[Tuple[str, ...], Mapping[str, str], Mapping[str, str]]:
        """Return (all_known_candidates, skipped_candidates_with_reason, backend_versions)."""
        import importlib.util

        known_candidates = (
            "EQUAL_WEIGHT",
            "INVERSE_VOL",
            "HIERARCHICAL_RISK_PARITY",
            "EQUAL_RISK_CONTRIBUTION",
            "SKFOLIO_HIERARCHICAL_RISK_PARITY",
            "CVXPY_MINIMUM_VARIANCE",
        )
        skipped: dict[str, str] = {}
        if importlib.util.find_spec("skfolio") is None:
            skipped["SKFOLIO_HIERARCHICAL_RISK_PARITY"] = "Optional package 'skfolio' not installed in current environment."
        if importlib.util.find_spec("cvxpy") is None:
            skipped["CVXPY_MINIMUM_VARIANCE"] = "Optional package 'cvxpy' not installed in current environment."

        backend_versions: dict[str, str] = {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
        }
        try:
            import importlib
            scipy_mod = importlib.import_module("scipy")
            backend_versions["scipy"] = getattr(scipy_mod, "__version__", "installed")
        except Exception:
            backend_versions["scipy"] = "missing"

        if "SKFOLIO_HIERARCHICAL_RISK_PARITY" not in skipped:
            try:
                import importlib
                skfolio_mod = importlib.import_module("skfolio")
                backend_versions["skfolio"] = getattr(skfolio_mod, "__version__", "installed")
            except Exception:
                backend_versions["skfolio"] = "installed"
        else:
            backend_versions["skfolio"] = "NOT_INSTALLED"

        if "CVXPY_MINIMUM_VARIANCE" not in skipped:
            try:
                import importlib
                cvxpy_mod = importlib.import_module("cvxpy")
                backend_versions["cvxpy"] = getattr(cvxpy_mod, "__version__", "installed")
            except Exception:
                backend_versions["cvxpy"] = "installed"
        else:
            backend_versions["cvxpy"] = "NOT_INSTALLED"

        return known_candidates, skipped, backend_versions

    def generate_splits(self, panel: AssetReturnPanel) -> list[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Generate out-of-sample train/test splits strictly preserving causality (no look-ahead)."""
        T = panel.T
        n_splits = self.config.split_config.n_splits
        purge = self.config.split_config.purge_bars

        if T < 20:
            raise DataContractError(f"Insufficient observations for tournament: T={T} < 20.")

        splits: list[Tuple[Tuple[int, int], Tuple[int, int]]] = []
        min_train = max(10, int(T * float(self.config.split_config.train_ratio) / 2))
        step = (T - min_train - purge) // n_splits
        if step < 2:
            step = 2

        for i in range(n_splits):
            train_end = min_train + i * step
            test_start = train_end + purge
            test_end = min(T, test_start + step)
            if test_start >= T or test_end <= test_start:
                break
            splits.append(((0, train_end), (test_start, test_end)))

        if len(splits) == 0:
            raise DataContractError("Failed to generate valid splits from panel dimensions.")
        return splits

    def run_tournament(
        self,
        panel: AssetReturnPanel,
        constraints: PortfolioConstraints,
        risk_snapshot: RiskSnapshot,
        current_weights: Optional[Mapping[str, Decimal]] = None,
        as_of: Optional[datetime] = None,
    ) -> TournamentReport:
        """Execute full out-of-sample tournament evaluation and emit authoritative decision."""
        if not self._allocators:
            raise DataContractError("No allocators registered for tournament.")

        current_w = current_weights or {s: Decimal("0.0") for s in panel.symbols}
        splits = self.generate_splits(panel)
        split_records: list[SplitRecord] = []
        mean_estimator = HistoricalSampleMeanEstimator(self.config.annualization_factor)

        # 1. Run each allocator across all OOS splits
        for split_idx, ((train_s, train_e), (test_s, test_e)) in enumerate(splits):
            train_panel = slice_panel(panel, train_s, train_e)
            test_panel = slice_panel(panel, test_s, test_e)

            # Strict temporal non-leakage invariant assertion:
            if test_panel.timestamps[0] <= train_panel.timestamps[-1]:
                raise DataContractError(
                    f"Look-ahead violation detected: test start {test_panel.timestamps[0]} <= train end {train_panel.timestamps[-1]}"
                )
            if test_s < train_e + self.config.split_config.purge_bars:
                raise DataContractError(
                    f"Purge boundary violation: test index {test_s} < train end {train_e} + purge {self.config.split_config.purge_bars}"
                )

            expected_returns_train = mean_estimator.estimate_expected_returns(train_panel)

            for allocator in self._allocators:
                candidate = allocator.compute_candidate(train_panel, constraints, current_w)

                evaluation = self.evaluator.evaluate_candidate(
                    candidate=candidate,
                    panel=test_panel,
                    constraints=constraints,
                    current_weights=current_w,
                    expected_returns=expected_returns_train,
                )

                # Compute realized OOS path performance
                norm_w = evaluation.normalized_weights
                weights_f64 = np.array([float(norm_w.get(s, Decimal("0.0"))) for s in test_panel.symbols], dtype=np.float64)
                returns_f64 = np.array([[float(v) for v in row] for row in test_panel.returns_matrix], dtype=np.float64)
                oos_portfolio_returns = returns_f64 @ weights_f64

                mean_p = float(np.mean(oos_portfolio_returns))
                std_p = float(np.std(oos_portfolio_returns, ddof=1)) if len(oos_portfolio_returns) > 1 else 0.0
                ann_factor_f = float(self.config.annualization_factor)
                sqrt_ann = math.sqrt(ann_factor_f)

                gross_ret_ann = Decimal(str(round(mean_p * ann_factor_f, 8)))
                vol_ann = Decimal(str(round(std_p * sqrt_ann, 8)))
                gross_sharpe = Decimal(str(round((mean_p / std_p * sqrt_ann) if std_p > 1e-12 else 0.0, 6)))

                # Net-of-friction realized equity path Max Drawdown
                one_time_f = evaluation.turnover_required * self.config.evaluation_config.friction_params.total_cost_rate
                cum_equity = (1.0 - float(one_time_f)) * np.cumprod(1.0 + oos_portfolio_returns)
                equity_path = np.insert(cum_equity, 0, 1.0)
                running_max = np.maximum.accumulate(equity_path)
                drawdowns = (equity_path - running_max) / running_max
                max_dd = Decimal(str(round(float(-np.min(drawdowns)), 8))) if len(drawdowns) > 0 else Decimal("0.0")

                net_ret_ann = gross_ret_ann - evaluation.estimated_transaction_cost
                net_sharpe = (
                    Decimal(str(round(float(net_ret_ann - self.config.evaluation_config.risk_free_rate) / (float(vol_ann) if float(vol_ann) > 1e-12 else 1.0), 6)))
                    if float(vol_ann) > 1e-12
                    else Decimal("0.0")
                )

                rec = SplitRecord(
                    split_index=split_idx + 1,
                    train_bars=train_panel.T,
                    test_bars=test_panel.T,
                    purge_bars=self.config.split_config.purge_bars,
                    train_start=train_panel.timestamps[0],
                    train_end=train_panel.timestamps[-1],
                    test_start=test_panel.timestamps[0],
                    test_end=test_panel.timestamps[-1],
                    train_panel_digest=train_panel.panel_digest,
                    test_panel_digest=test_panel.panel_digest,
                    allocator_name=allocator.allocator_name,
                    candidate_id=candidate.candidate_id,
                    candidate_digest=candidate.candidate_digest,
                    candidate_generation_digest=candidate.candidate_digest,
                    test_evaluation_digest=evaluation.evaluation_digest,
                    weights=evaluation.normalized_weights,
                    cash_weight=evaluation.normalized_cash_weight,
                    turnover=evaluation.turnover_required,
                    one_time_friction=one_time_f,
                    annualized_friction=evaluation.estimated_transaction_cost,
                    gross_return_annualized=gross_ret_ann,
                    net_return_annualized=net_ret_ann,
                    volatility_annualized=vol_ann,
                    gross_sharpe=gross_sharpe,
                    net_sharpe=net_sharpe,
                    max_drawdown=max_dd,
                    cvar_95=evaluation.oos_cvar_95 or Decimal("0.0"),
                    hurdle_rate_cleared=evaluation.hurdle_rate_cleared,
                    rank_score=evaluation.rank_score,
                    max_drawdown_provenance="NET_FRICTION_ADJUSTED_EQUITY_PATH",
                    friction_model="POLICY_ESTIMATED_FRICTION",
                    fold_aggregation_method="ARITHMETIC_MEAN_ACROSS_SPLITS",
                )
                split_records.append(rec)

        # 2. Aggregate metrics per allocator across all splits
        allocator_names = [a.allocator_name for a in self._allocators]
        summaries: list[AllocatorSummary] = []
        dsr_engine = DeflatedSharpeEngine()
        ann_factor_f = float(self.config.annualization_factor)

        for alloc_name in allocator_names:
            alloc_recs = [r for r in split_records if r.allocator_name == alloc_name]
            n_eval = len(alloc_recs)
            if n_eval == 0:
                continue

            mean_turnover = sum((r.turnover for r in alloc_recs), Decimal("0.0")) / Decimal(str(n_eval))
            total_friction = sum((r.one_time_friction for r in alloc_recs), Decimal("0.0"))
            mean_gross_ret = sum((r.gross_return_annualized for r in alloc_recs), Decimal("0.0")) / Decimal(str(n_eval))
            mean_net_ret = sum((r.net_return_annualized for r in alloc_recs), Decimal("0.0")) / Decimal(str(n_eval))
            mean_net_sharpe = sum((r.net_sharpe for r in alloc_recs), Decimal("0.0")) / Decimal(str(n_eval))
            mean_vol = sum((r.volatility_annualized for r in alloc_recs), Decimal("0.0")) / Decimal(str(n_eval))
            worst_mdd = max(r.max_drawdown for r in alloc_recs)
            mean_cvar = sum((r.cvar_95 for r in alloc_recs), Decimal("0.0")) / Decimal(str(n_eval))
            hurdle_cleared_count = sum(1 for r in alloc_recs if r.hurdle_rate_cleared)
            hurdle_rate = Decimal(str(round(hurdle_cleared_count / n_eval, 4)))
            agg_rank_score = sum((r.rank_score for r in alloc_recs), Decimal("0.0")) / Decimal(str(n_eval))

            dsr_prob = Decimal("0.0")
            try:
                dsr_res = dsr_engine.evaluate_dsr(
                    returns=[float(r.net_return_annualized / self.config.annualization_factor) for r in alloc_recs],
                    dsr_trials_k=len(allocator_names),
                    variance_of_trials=float(np.var([float(r.net_sharpe) for r in alloc_recs])) if len(alloc_recs) > 1 else 0.0,
                    periods_per_year=ann_factor_f,
                )
                dsr_prob = Decimal(str(round(float(dsr_res.dsr_probability), 4)))
            except Exception:
                dsr_prob = Decimal("0.0")

            backend_pkg = "acash_native"
            if "SKFOLIO" in alloc_name:
                backend_pkg = "skfolio"
            elif "CVXPY" in alloc_name:
                backend_pkg = "cvxpy"

            summary = AllocatorSummary(
                allocator_name=alloc_name,
                backend_package=backend_pkg,
                n_splits_evaluated=n_eval,
                mean_turnover=mean_turnover,
                total_friction_cost=total_friction,
                mean_gross_return=mean_gross_ret,
                mean_net_return=mean_net_ret,
                mean_net_sharpe=mean_net_sharpe,
                mean_volatility=mean_vol,
                worst_max_drawdown=worst_mdd,
                mean_cvar_95=mean_cvar,
                hurdle_clearance_rate=hurdle_rate,
                deflated_sharpe_probability=dsr_prob,
                aggregate_rank_score=agg_rank_score,
                tournament_rank=0,
                is_governance_approved=False,
                governance_verdict="PENDING",
            )
            summaries.append(summary)

        # 3. Sort summaries by aggregate_rank_score descending (with baseline tie-breaking)
        def _pref(name: str) -> int:
            if "EQUAL_WEIGHT" in name:
                return 4
            if "INVERSE" in name:
                return 3
            if "HRP" in name:
                return 2
            if "ERC" in name:
                return 1
            return 0

        summaries.sort(
            key=lambda s: (float(s.aggregate_rank_score), _pref(s.allocator_name)),
            reverse=True,
        )

        ranked_alloc_names: list[str] = []
        updated_summaries: list[AllocatorSummary] = []
        for rank_idx, s in enumerate(summaries, start=1):
            ranked_alloc_names.append(s.allocator_name)
            updated_summaries.append(
                s.model_copy(update={"tournament_rank": rank_idx})
            )

        # 4. Generate final candidate proposals on the full panel and evaluate for Governance
        full_expected_returns = mean_estimator.estimate_expected_returns(panel)
        full_candidates: list[AllocationCandidate] = []
        for alloc in self._allocators:
            cand = alloc.compute_candidate(panel, constraints, current_w)
            full_candidates.append(cand)

        full_evaluations: list[AllocationEvaluation] = []
        for cand in full_candidates:
            ev = self.evaluator.evaluate_candidate(
                candidate=cand,
                panel=panel,
                constraints=constraints,
                current_weights=current_w,
                expected_returns=full_expected_returns,
            )
            full_evaluations.append(ev)

        ranked_evaluations = self.evaluator.rank_evaluations(full_evaluations)

        # 5. Authorize through PortfolioGovernanceGate
        decision = self.governance_gate.evaluate_and_decide(
            candidates=full_candidates,
            ranked_evaluations=ranked_evaluations,
            risk_snapshot=risk_snapshot,
            constraints=constraints,
            as_of=as_of or datetime.now(timezone.utc),
        )

        # 6. Update governance status in allocator summaries
        cand_map = {c.allocator_name: c for c in full_candidates}
        eval_map = {e.candidate_id: e for e in full_evaluations}
        final_summaries: list[AllocatorSummary] = []
        for s in updated_summaries:
            is_appr = (decision.allocator_name == s.allocator_name and decision.gate_verdict == "APPROVED_INVESTABLE_ALLOCATION")
            candidate_obj: Optional[AllocationCandidate] = cand_map.get(s.allocator_name)
            eval_item: Optional[AllocationEvaluation] = eval_map.get(candidate_obj.candidate_id) if candidate_obj is not None else None
            if is_appr:
                v_code = "APPROVED"
                rej_reason = None
            elif candidate_obj is not None and eval_item is not None:
                v_code, rej_reason = self.governance_gate._verify_candidate_eligibility(candidate_obj, eval_item, constraints)
            else:
                v_code = "REJECTED"
                rej_reason = "Candidate or evaluation missing."
            final_summaries.append(
                s.model_copy(update={
                    "is_governance_approved": is_appr,
                    "governance_verdict": v_code,
                    "rejection_reason": rej_reason,
                })
            )

        # 7. Telemetry & provenance tracking
        known_candidates, skipped_candidates, backend_versions = self.get_candidate_universe_manifest()
        executed_candidates = tuple(allocator_names)

        tournament_rank_1 = ranked_alloc_names[0] if ranked_alloc_names else "NONE"
        governance_selected = decision.allocator_name

        if decision.allocator_name == "CASH":
            if any(a.allocator_name == "CASH" for a in self._allocators):
                decision_origin = "EXPLICIT_CASH_ALLOCATOR"
                cash_selection_mode = "EXPLICIT_CASH_ALLOCATOR"
            else:
                decision_origin = "GOVERNANCE_FALLBACK"
                cash_selection_mode = "GOVERNANCE_FALLBACK"
        else:
            decision_origin = "RANKED_WINNER"
            cash_selection_mode = "NONE"

        metadata: dict[str, Any] = {
            "tournament_id": self.config.tournament_id,
            "dataset_id": self.config.dataset_id,
            "date_range": [panel.timestamps[0].isoformat(), panel.timestamps[-1].isoformat()],
            "symbols": list(panel.symbols),
            "split_config": self.config.split_config.model_dump(),
            "evaluation_config": self.config.evaluation_config.model_dump(),
            "governance_config": self.config.governance_config.model_dump(),
            "git_commit": self.config.git_commit,
            "total_bars": panel.T,
            "n_splits": len(splits),
            "allocator_count": len(self._allocators),
            "decision_id": decision.decision_id,
            "decision_gate_verdict": decision.gate_verdict,
            "decision_is_fallback_baseline": decision.is_fallback_baseline,
            "tournament_rank_1_allocator": tournament_rank_1,
            "governance_selected_allocator": governance_selected,
            "decision_origin": decision_origin,
            "cash_selection_mode": cash_selection_mode,
            "allocators_available": list(known_candidates),
            "allocators_executed": list(executed_candidates),
            "allocators_skipped": dict(skipped_candidates),
            "backend_versions": dict(backend_versions),
            "max_drawdown_provenance": "NET_FRICTION_ADJUSTED_EQUITY_PATH",
            "friction_model": "POLICY_ESTIMATED_FRICTION",
            "fold_aggregation_method": "ARITHMETIC_MEAN_ACROSS_SPLITS",
        }
        tournament_digest = _sha256_hexdigest(metadata)

        return TournamentReport(
            tournament_id=self.config.tournament_id,
            dataset_id=self.config.dataset_id,
            universe_id=panel.universe_id,
            symbols=panel.symbols,
            date_range=(panel.timestamps[0], panel.timestamps[-1]),
            total_bars=panel.T,
            n_splits=len(splits),
            split_records=tuple(split_records),
            allocator_summaries=tuple(final_summaries),
            ranked_allocator_names=tuple(ranked_alloc_names),
            tournament_rank_1_allocator=tournament_rank_1,
            governance_selected_allocator=governance_selected,
            decision_origin=decision_origin,
            cash_selection_mode=cash_selection_mode,
            allocators_available=known_candidates,
            allocators_executed=executed_candidates,
            allocators_skipped=skipped_candidates,
            backend_versions=backend_versions,
            final_decision=decision,
            reproducible_metadata=metadata,
            tournament_digest=tournament_digest,
        )
