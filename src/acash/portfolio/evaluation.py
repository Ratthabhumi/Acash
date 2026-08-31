"""Allocation Evaluation Engine for Phase 8 Portfolio Engine.

Computes objective out-of-sample performance, friction, and comparative RankScore for
AllocationCandidate proposals with strict dimensional consistency, CPCV integration, and DSR.
"""

from decimal import Decimal
import functools
import math
from typing import List, Mapping, Optional, Sequence, Tuple
import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.portfolio.schema import (
    EPSILON_RANK_TIE,
    EPSILON_WEIGHT_SUM,
    AllocationCandidate,
    AllocationEvaluation,
    AssetReturnPanel,
    PortfolioConstraints,
)
from acash.validation.cpcv import CombinatorialPurgedCrossValidation
from acash.validation.deflated_sharpe import DeflatedSharpeEngine
from acash.validation.schema import SelectionCorrectionMode, ValidationConfig


class FrictionParameters(BaseModel):
    """Transaction cost parameters for rebalance friction estimation."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    fee_rate: Decimal = Decimal("0.0005")      # 5 bps per unit notional traded
    half_spread: Decimal = Decimal("0.0005")   # 5 bps per unit notional traded
    slippage: Decimal = Decimal("0.0002")      # 2 bps per unit notional traded

    @property
    def total_cost_rate(self) -> Decimal:
        """Total one-time transaction friction rate per unit notional turnover."""
        return self.fee_rate + self.half_spread + self.slippage


class EvaluationConfig(BaseModel):
    """Configuration for out-of-sample portfolio evaluation with strict dimensional horizon scaling."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    risk_free_rate: Decimal = Decimal("0.04")                # Annualized risk-free rate (e.g. 4.0% p.a.)
    hurdle_margin: Decimal = Decimal("0.02")                 # Annualized hurdle margin (e.g. 2.0% p.a.)
    friction_params: FrictionParameters = Field(default_factory=FrictionParameters)
    rebalance_frequency_per_year: Decimal = Decimal("12")    # Expected rebalance events per year (e.g. 12 for monthly, 52 for weekly)
    lambda_turnover: Decimal = Decimal("0.5")                # Turnover penalty coefficient in RankScore
    lambda_tail: Decimal = Decimal("0.5")                    # Tail risk (CVaR) penalty coefficient in RankScore
    annualization_factor: Decimal = Decimal("252")           # Bar scaling factor to annualized space
    cpcv_min_sample_size: int = 20                           # Minimum sample size T to enable CPCV fold evaluation
    cpcv_num_groups_n: int = 5                               # CPCV groups (N=5, k=2 -> 10 folds)
    cpcv_num_test_groups_k: int = 2                          # CPCV test groups per combination
    configured_evidence_threshold: int = 40                  # Configured policy threshold separating initial execution from evidence threshold


# Allocator tie-breaking precedence: simpler baselines preferred
_ALLOCATOR_PREFERENCE: dict[str, int] = {
    "CASH": 5,
    "EQUAL_WEIGHT": 4,
    "INVERSE_VOL": 3,
    "HRP": 2,
    "ERC": 1,
}


def _get_allocator_preference(candidate_id: str) -> int:
    for k, v in _ALLOCATOR_PREFERENCE.items():
        if k in candidate_id:
            return v
    return 0


def _compare_evaluations(a: AllocationEvaluation, b: AllocationEvaluation) -> int:
    """Deterministic comparator for evaluations: descending rank_score with tie-breaking."""
    diff = a.rank_score - b.rank_score
    if abs(diff) > EPSILON_RANK_TIE:
        return -1 if diff > Decimal("0") else 1

    # Within EPSILON_RANK_TIE: apply baseline preference tie-breaker (CASH > EW > INV_VOL)
    pref_a = _get_allocator_preference(a.candidate_id)
    pref_b = _get_allocator_preference(b.candidate_id)
    if pref_a != pref_b:
        return -1 if pref_a > pref_b else 1

    # Deterministic lexicographical fallback by candidate_id
    if a.candidate_id != b.candidate_id:
        return -1 if a.candidate_id < b.candidate_id else 1
    return 0


class AllocationEvaluator:
    """Evaluates candidate weight proposals against empirical return panels and constraints."""

    def __init__(self, config: Optional[EvaluationConfig] = None) -> None:
        self.config = config or EvaluationConfig()

    def evaluate_candidate(
        self,
        candidate: AllocationCandidate,
        panel: AssetReturnPanel,
        constraints: PortfolioConstraints,
        current_weights: Mapping[str, Decimal],
        expected_returns: Mapping[str, Decimal],
    ) -> AllocationEvaluation:
        """Evaluate candidate out-of-sample performance, friction, and comparative RankScore.

        Enforces strict dimensional consistency:
        - All return components (Expected Return, r_f, Annualized Friction, Hurdle) in 1/year annualized space.
        - One-way Turnover in [0, 1] portfolio fraction space.
        - CVaR in positive loss magnitude space.
        """
        if panel.T < 2:
            raise DataContractError(f"Return panel must have at least T >= 2 observations (computational minimum), got T={panel.T}.")

        # 1. Validate expected returns completeness
        for sym in panel.symbols:
            if sym not in expected_returns:
                raise DataContractError(f"Missing expected return for asset: {sym}")

        # 2. Normalize and check constraints
        raw_risky_sum = sum(candidate.asset_weights.values(), Decimal("0.0"))
        declared_cash = candidate.cash_weight if candidate.cash_weight is not None else Decimal("0.0")

        # Determine cash provenance
        if candidate.allocator_name == "CASH" or declared_cash == Decimal("1.0"):
            cash_provenance = "EXPLICIT_ALLOCATOR"
        elif declared_cash > Decimal("0.0") and raw_risky_sum < (Decimal("1.0") - constraints.min_cash_buffer):
            cash_provenance = "RESIDUAL_CONSTRAINT"
        elif declared_cash > Decimal("0.0"):
            cash_provenance = "EXPLICIT_ALLOCATOR"
        else:
            cash_provenance = "ZERO_CASH"

        # Normalized weights
        normalized_weights = {s: candidate.asset_weights.get(s, Decimal("0.0")) for s in panel.symbols}
        normalized_cash = max(Decimal("0.0"), Decimal("1.0") - sum(normalized_weights.values(), Decimal("0.0")))

        # Check constraint satisfaction
        constraints_satisfied = True
        for sym, w in normalized_weights.items():
            if w < constraints.min_weight or w > constraints.max_weight:
                constraints_satisfied = False
                break
        if normalized_cash < constraints.min_cash_buffer and candidate.allocator_name != "CASH":
            constraints_satisfied = False

        # 3. Calculate turnover & one-time transaction friction
        current_cash = max(Decimal("0.0"), Decimal("1.0") - sum(current_weights.values(), Decimal("0.0")))
        asset_delta_sum = sum(
            abs(normalized_weights.get(s, Decimal("0.0")) - current_weights.get(s, Decimal("0.0")))
            for s in panel.symbols
        )
        cash_delta = abs(normalized_cash - current_cash)
        turnover_required = Decimal("0.5") * (asset_delta_sum + cash_delta)
        one_time_transaction_cost = turnover_required * self.config.friction_params.total_cost_rate

        # Dimensional scaling: convert one-time rebalance cost to annualized friction rate
        annualized_friction_cost = one_time_transaction_cost * self.config.rebalance_frequency_per_year

        # 4. Calculate OOS portfolio performance metrics
        eval_meta: dict[str, str] = {
            "evaluation_horizon": panel.frequency,
            "return_frequency": panel.frequency,
            "annualization_factor": str(self.config.annualization_factor),
            "risk_free_rate_basis": "ANNUALIZED_PER_ANNUM",
            "friction_basis": "EXPECTED_ANNUALIZED_POLICY_APPROXIMATION",
            "rebalance_frequency_per_year": str(self.config.rebalance_frequency_per_year),
            "cvar_convention": "POSITIVE_LOSS_MAGNITUDE",
            "cash_provenance": cash_provenance,
            "evidence_threshold_policy": "CONFIGURED_POLICY_THRESHOLD",
            "sample_sufficiency_status": (
                "EVIDENCE_THRESHOLD_MET" if panel.T >= self.config.configured_evidence_threshold else "INSUFFICIENT_EVIDENCE"
            ),
        }

        if candidate.allocator_name == "CASH" or sum(normalized_weights.values(), Decimal("0.0")) == Decimal("0.0"):
            oos_sharpe_ratio: Optional[Decimal] = Decimal("0.0")
            oos_cvar_95: Optional[Decimal] = Decimal("0.0")
            gross_expected_return = Decimal("0.0")
            eval_meta["cpcv_aggregation_method"] = "EXPLICIT_CASH_BENCHMARK"
            eval_meta["cpcv_fold_count"] = "0"
            eval_meta["dsr_probability"] = "0.0"
            eval_meta["dsr_trials_k"] = "1"
            eval_meta["dsr_selection_mode"] = "SINGLE_TRIAL"
            eval_meta["negative_return_count"] = "0"
            eval_meta["tail_observation_count"] = "0"
            eval_meta["tail_fraction"] = "0.0"
            eval_meta["cvar_validity_status"] = "ZERO_DOWNSIDE_IN_SAMPLE"
        else:
            weights_f64 = np.array([float(normalized_weights[s]) for s in panel.symbols], dtype=np.float64)
            returns_f64 = np.array([[float(v) for v in row] for row in panel.returns_matrix], dtype=np.float64)
            portfolio_returns = returns_f64 @ weights_f64

            # Evaluate tail risk diagnostics
            neg_count = int(np.sum(portfolio_returns < 0.0))
            eval_meta["negative_return_count"] = str(neg_count)

            # Evaluate DSR probability with explicit selection-history provenance
            try:
                dsr_engine = DeflatedSharpeEngine()
                ann_scale_f = float(self.config.annualization_factor)
                var_trials_period = float(candidate.trial_variance) / ann_scale_f if ann_scale_f > 0 else 0.0
                dsr_res = dsr_engine.evaluate_dsr(
                    returns=[float(x) for x in portfolio_returns],
                    dsr_trials_k=candidate.search_trials_k,
                    variance_of_trials=var_trials_period,
                    periods_per_year=ann_scale_f,
                )
                eval_meta["dsr_probability"] = str(round(float(dsr_res.dsr_probability), 6))
                eval_meta["dsr_trials_k"] = str(candidate.search_trials_k)
                eval_meta["dsr_variance_of_trials"] = str(candidate.trial_variance)
                eval_meta["dsr_expected_max_sharpe_sr0"] = str(round(float(dsr_res.expected_max_sharpe_sr0), 6))
                eval_meta["dsr_sample_sharpe"] = str(round(float(dsr_res.estimated_sharpe), 6))
                eval_meta["dsr_skewness"] = str(round(float(dsr_res.sample_skewness), 6))
                eval_meta["dsr_kurtosis"] = str(round(float(dsr_res.sample_kurtosis), 6))
                eval_meta["dsr_sample_size_t"] = str(len(portfolio_returns))
                eval_meta["dsr_null_policy"] = "ACASH_ZERO_LOCATION_NULL_POLICY"
                eval_meta["dsr_selection_mode"] = (
                    "MULTIPLE_TRIAL" if candidate.search_trials_k > 1 else "SINGLE_TRIAL"
                )
            except Exception:
                eval_meta["dsr_probability"] = "0.0"
                eval_meta["dsr_trials_k"] = str(candidate.search_trials_k)
                eval_meta["dsr_variance_of_trials"] = str(candidate.trial_variance)
                eval_meta["dsr_expected_max_sharpe_sr0"] = "0.0"
                eval_meta["dsr_selection_mode"] = (
                    "MULTIPLE_TRIAL" if candidate.search_trials_k > 1 else "SINGLE_TRIAL"
                )
                eval_meta["dsr_null_policy"] = "ACASH_ZERO_LOCATION_NULL_POLICY"

            # Check if CPCV should be used for OOS evaluation
            if panel.T >= self.config.cpcv_min_sample_size:
                oos_sharpe_ratio, oos_cvar_95, fold_cnt, tail_cnt = self._evaluate_cpcv_metrics(
                    returns_f64=returns_f64,
                    weights_f64=weights_f64,
                )
                eval_meta["cpcv_fold_count"] = str(fold_cnt)
                eval_meta["cpcv_aggregation_method"] = "CPCV_ARITHMETIC_MEAN_OF_FOLDS"
                eval_meta["tail_observation_count"] = str(tail_cnt)
                eval_meta["tail_fraction"] = str(round(tail_cnt / max(1, panel.T), 4))
            else:
                oos_sharpe_ratio, oos_cvar_95, tail_cnt = self._evaluate_direct_metrics(
                    returns_f64=returns_f64,
                    weights_f64=weights_f64,
                )
                eval_meta["cpcv_fold_count"] = "1"
                eval_meta["cpcv_aggregation_method"] = "DIRECT_FULL_SAMPLE_PATH"
                eval_meta["tail_observation_count"] = str(tail_cnt)
                eval_meta["tail_fraction"] = str(round(tail_cnt / max(1, panel.T), 4))

            # CVaR validity categorization
            if neg_count == 0:
                eval_meta["cvar_validity_status"] = "ZERO_DOWNSIDE_IN_SAMPLE"
            elif tail_cnt < 2:
                eval_meta["cvar_validity_status"] = "INSUFFICIENT_TAIL_OBSERVATIONS"
            else:
                eval_meta["cvar_validity_status"] = "VALID_TAIL_ESTIMATE"

            # Annualized gross expected return: w^T mu
            gross_expected_return = sum(
                (normalized_weights[s] * expected_returns[s] for s in panel.symbols),
                Decimal("0.0"),
            )

        # 5. Net expected excess return & Hurdle check (in identical annualized space 1/year)
        net_expected_excess_return = gross_expected_return - annualized_friction_cost - self.config.risk_free_rate
        hurdle_rate_cleared = (net_expected_excess_return >= self.config.hurdle_margin) if candidate.allocator_name != "CASH" else False

        # 6. Calculate RankScore
        sharpe_part = oos_sharpe_ratio if oos_sharpe_ratio is not None else Decimal("0.0")
        cvar_part = oos_cvar_95 if oos_cvar_95 is not None else Decimal("0.0")
        rank_score = sharpe_part - (self.config.lambda_turnover * turnover_required) - (self.config.lambda_tail * cvar_part)

        return AllocationEvaluation(
            candidate_id=candidate.candidate_id,
            candidate_digest=candidate.candidate_digest,
            normalized_weights=normalized_weights,
            normalized_cash_weight=normalized_cash,
            oos_sharpe_ratio=oos_sharpe_ratio,
            oos_cvar_95=oos_cvar_95,
            turnover_required=turnover_required,
            estimated_transaction_cost=annualized_friction_cost,
            net_expected_excess_return=net_expected_excess_return,
            hurdle_rate_cleared=hurdle_rate_cleared,
            constraints_satisfied=constraints_satisfied,
            rank_score=rank_score,
            evaluation_metadata=eval_meta,
        )

    def _evaluate_direct_metrics(
        self,
        returns_f64: np.ndarray,
        weights_f64: np.ndarray,
    ) -> Tuple[Decimal, Decimal, int]:
        """Compute Sharpe and CVaR directly on empirical observed portfolio return path."""
        portfolio_returns = returns_f64 @ weights_f64
        mean_p = float(np.mean(portfolio_returns))
        std_p = float(np.std(portfolio_returns, ddof=1)) if len(portfolio_returns) > 1 else 0.0

        ann_scale = float(self.config.annualization_factor)
        rf_per_period = float(self.config.risk_free_rate) / ann_scale

        if std_p > 1e-12:
            sharpe_val = ((mean_p - rf_per_period) / std_p) * np.sqrt(ann_scale)
            oos_sharpe = Decimal(str(round(sharpe_val, 6)))
        else:
            oos_sharpe = Decimal("0.0")

        # CVaR 95% (Loss-space positive magnitude)
        var_95 = float(np.percentile(portfolio_returns, 5))
        tail_returns = portfolio_returns[portfolio_returns <= var_95]
        cvar_val = -float(np.mean(tail_returns)) if len(tail_returns) > 0 else -var_95
        oos_cvar = Decimal(str(max(0.0, round(cvar_val, 6))))

        return oos_sharpe, oos_cvar, len(tail_returns)

    def _evaluate_cpcv_metrics(
        self,
        returns_f64: np.ndarray,
        weights_f64: np.ndarray,
    ) -> Tuple[Decimal, Decimal, int, int]:
        """Compute fold-aggregated Sharpe and CVaR across Combinatorial Purged Cross-Validation test partitions."""
        val_config = ValidationConfig(
            cpcv_num_groups_n=self.config.cpcv_num_groups_n,
            cpcv_num_test_groups_k=self.config.cpcv_num_test_groups_k,
            embargo_bars=1,
        )
        cpcv = CombinatorialPurgedCrossValidation(config=val_config)
        partitions = cpcv.generate_partitions(
            sample_size=len(returns_f64),
            label_horizon=1,
            embargo_bars=1,
        )

        fold_sharpes: list[float] = []
        fold_cvars: list[float] = []
        fold_tail_counts: list[int] = []
        ann_scale = float(self.config.annualization_factor)
        rf_per_period = float(self.config.risk_free_rate) / ann_scale

        for part in partitions:
            test_indices = list(part.test_indices)
            if len(test_indices) < 2:
                continue
            test_returns_mat = returns_f64[test_indices]
            port_test_returns = test_returns_mat @ weights_f64

            mean_f = float(np.mean(port_test_returns))
            std_f = float(np.std(port_test_returns, ddof=1)) if len(port_test_returns) > 1 else 0.0

            if std_f > 1e-12:
                sh_f = ((mean_f - rf_per_period) / std_f) * np.sqrt(ann_scale)
            else:
                sh_f = 0.0
            fold_sharpes.append(sh_f)

            var_95 = float(np.percentile(port_test_returns, 5))
            tail_f = port_test_returns[port_test_returns <= var_95]
            cv_f = -float(np.mean(tail_f)) if len(tail_f) > 0 else -var_95
            fold_cvars.append(max(0.0, cv_f))
            fold_tail_counts.append(len(tail_f))

        if not fold_sharpes:
            direct_s, direct_c, direct_tail = self._evaluate_direct_metrics(returns_f64, weights_f64)
            return direct_s, direct_c, 1, direct_tail

        # Aggregate fold distributions via arithmetic mean of out-of-sample folds
        mean_oos_sharpe = float(np.mean(fold_sharpes))
        mean_oos_cvar = float(np.mean(fold_cvars))
        mean_tail_count = int(round(float(np.mean(fold_tail_counts))))

        return Decimal(str(round(mean_oos_sharpe, 6))), Decimal(str(round(mean_oos_cvar, 6))), len(fold_sharpes), mean_tail_count

    def rank_evaluations(self, evaluations: Sequence[AllocationEvaluation]) -> list[AllocationEvaluation]:
        """Sort evaluations strictly by rank_score descending with deterministic EPSILON_RANK_TIE tie-breaking."""
        return sorted(evaluations, key=functools.cmp_to_key(_compare_evaluations))
