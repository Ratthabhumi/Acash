"""Reproducible Empirical Data-Generating Process (DGP) Benchmark Suite for ACASH Phase 6.

Formal empirical characterization across 4 experimental domains:
1. Experiment A: Zero-Alpha Null DGP (False Positive Rate with Wilson 95% Confidence Interval)
2. Experiment B: Correlated-Search Collinear DGP (Hurdle Dynamics & PBO Protection)
3. Experiment C: Serial-Correlation & Overlapping-Label DGP (Asymptotic Normal vs Newey-West HAC)
4. Experiment D: Statistical Power Curve (Detection Rate across True Annualized Sharpe Ratios)
"""

from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from acash.backtest.schema import BacktestExecutionSummary, BacktestManifest, RealityGapSummary
from acash.research.schema import ExpectedDirection, HypothesisSpecification, InvalidationCriteria
from acash.validation.deflated_sharpe import DeflatedSharpeEngine, compute_hac_newey_west_variance, compute_hac_p_value
from acash.validation.gate import StatisticalValidationGate
from acash.validation.multiple_testing import MultipleTestingEngine
from acash.validation.overfitting import OverfittingEngine
from acash.validation.schema import (
    ParameterPerturbationGrid,
    ParameterPerturbationPoint,
    SearchTrialLedger,
    SearchTrialRecord,
    SharpeSpace,
    ValidationConfig,
    ValidationGateVerdict,
)


def compute_wilson_confidence_interval(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float, float]:
    """Compute Wilson score interval for binomial proportion p = k / n.

    Returns:
        Tuple[point_estimate, ci_lower, ci_upper]
    """
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    z = 1.959963984540054  # 95% normal quantile
    denominator = 1.0 + (z**2) / n
    centre_adjusted_probability = p + (z**2) / (2.0 * n)
    adjusted_standard_deviation = math.sqrt((p * (1.0 - p) / n) + ((z**2) / (4.0 * (n**2))))
    lower_bound = max(0.0, (centre_adjusted_probability - z * adjusted_standard_deviation) / denominator)
    upper_bound = min(1.0, (centre_adjusted_probability + z * adjusted_standard_deviation) / denominator)
    if k == 0 or lower_bound < 1e-12:
        lower_bound = 0.0
    if k == n or upper_bound > 1.0 - 1e-12:
        upper_bound = 1.0
    return p, lower_bound, upper_bound





def _create_mock_manifest(
    manifest_id: str,
    hypothesis_id: str = "HYP_BENCHMARK",
    strategy_config_hash: Optional[str] = None,
    sharpe: Decimal = Decimal("1.5"),
) -> BacktestManifest:
    hyp_hash = "1" * 64
    eng_hash = "2" * 64
    strat_hash = strategy_config_hash or ("3" * 64)
    pyp_hash = "4" * 64
    git_hash = "5" * 40
    data_hash = "6" * 64

    exec_summary = BacktestExecutionSummary(
        total_orders=10,
        total_fills=10,
        total_volume_traded=Decimal("10000.0"),
        total_fees_paid=Decimal("10.0"),
        realized_pnl=Decimal("1000.0"),
        unrealized_pnl=Decimal("0.0"),
        ending_equity=Decimal("101000.0"),
        net_return_pct=Decimal("1.0"),
        sharpe_ratio=sharpe,
        max_drawdown_pct=Decimal("0.5"),
        win_rate_pct=Decimal("60.0"),
    )
    reality_gap = RealityGapSummary(
        phase4_analytical_edge_bps=Decimal("10.0"),
        phase5_simulated_realized_bps=Decimal("8.0"),
        reality_gap_bps=Decimal("2.0"),
    )
    return BacktestManifest(
        manifest_id=manifest_id,
        hypothesis_id=hypothesis_id,
        hypothesis_spec_sha256=hyp_hash,
        canonical_data_hashes=[data_hash],
        engine_config_hash=eng_hash,
        strategy_config_hash=strat_hash,
        prng_seed=42,
        pyproject_toml_sha256=pyp_hash,
        git_commit_hash=git_hash,
        execution_summary=exec_summary,
        reality_gap=reality_gap,
        computed_at_utc="2026-08-28T10:00:00Z",
        wall_clock_duration_ms=1000,
    )


def _create_perturbation_grid(
    strat_id: str,
    manifest_store: Dict[str, Any],
    base_sharpe: Decimal = Decimal("1.5"),
) -> ParameterPerturbationGrid:
    base_val = Decimal("10.0")
    points = []
    for label, factor, mult in [("left", Decimal("0.75"), Decimal("0.95")), ("base", Decimal("1.00"), Decimal("1.00")), ("right", Decimal("1.25"), Decimal("0.93"))]:
        p_val = base_val * factor
        man_id = f"MANIFEST_{strat_id}_{label.upper()}"
        sr = base_sharpe * mult
        man = _create_mock_manifest(manifest_id=man_id, sharpe=sr)
        manifest_store[man_id] = man
        hyp_hash = "1" * 64
        strat_hash = "3" * 64
        expected_in = hashlib.sha256(f"{hyp_hash}:{strat_hash}".encode("utf-8")).hexdigest()
        pt = ParameterPerturbationPoint(
            parameter_value=p_val,
            run_id=f"run_{strat_id}_{label}",
            manifest_id=man_id,
            input_artifact_hash=expected_in,
            output_artifact_hash=man.compute_sha256(),
            actual_sharpe=sr,
        )
        points.append(pt)

    points_tuple: Tuple[ParameterPerturbationPoint, ParameterPerturbationPoint, ParameterPerturbationPoint] = (
        points[0],
        points[1],
        points[2],
    )
    return ParameterPerturbationGrid(
        base_parameter_name="lookback",
        base_parameter_value=base_val,
        points=points_tuple,
    )


def _create_trial_ledger(
    trial_return_matrix: np.ndarray,
    strategy_id: str = "STRAT_01",
    hypothesis_id: str = "HYP_BENCHMARK",
    ledger_id: str = "LEDGER_01",
    manifest_store: Optional[Dict[str, Any]] = None,
    p_value_method: str = "ASYMPTOTIC_TWO_SIDED_ZERO_SHARPE_NORMAL_TEST_V1",
) -> SearchTrialLedger:
    t_len, k_trials = trial_return_matrix.shape
    trials: List[SearchTrialRecord] = []
    for m in range(k_trials):
        col_m = trial_return_matrix[:, m]
        mean_m = float(np.mean(col_m))
        std_m = float(np.std(col_m, ddof=1)) if len(col_m) > 1 else 1.0
        sr_m = (mean_m / std_m) * math.sqrt(252.0) if std_m > 1e-12 else 0.0
        sr_dec = Decimal(f"{sr_m:.6f}")
        features = ["mom"]
        params = {"period": 10 + m}
        cfg_hash = SearchTrialRecord.compute_config_sha256(features, params)
        man_id = f"MANIFEST_TRIAL_{strategy_id}_{m}"
        trial = SearchTrialRecord.create(
            trial_id=f"trial_{m}",
            strategy_id=strategy_id,
            hypothesis_id=hypothesis_id,
            feature_names=features,
            parameters=params,
            in_sample_sharpe=sr_dec,
            p_value_method=p_value_method,
            execution_manifest_id=man_id,
            in_sample_returns=list(col_m),
        )
        trials.append(trial)
        if manifest_store is not None:
            manifest_store[man_id] = _create_mock_manifest(
                manifest_id=man_id,
                hypothesis_id=hypothesis_id,
                strategy_config_hash=cfg_hash,
                sharpe=trial.in_sample_sharpe,
            )
    ledger = SearchTrialLedger(
        ledger_id=ledger_id,
        strategy_id=strategy_id,
        hypothesis_id=hypothesis_id,
        sharpe_space=SharpeSpace.ANNUAL,
        trials=tuple(trials),
    )
    return ledger.seal(sealed_at_utc="2026-08-28T00:00:00Z")


# =========================================================================
# EXPERIMENT A: Zero-Alpha Null DGP
# =========================================================================
def run_null_dgp_experiment(
    num_simulations: int = 100,
    T: int = 500,
    M: int = 10,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Experiment A: Evaluate false positive approval rate under pure zero-alpha Gaussian noise."""
    gate = StatisticalValidationGate()
    spec = HypothesisSpecification(
        hypothesis_id="HYP_BENCHMARK",
        hypothesis_version="v1.0",
        economic_rationale="Null Alpha DGP Benchmark",
        target_symbol="BTCUSDT",
        feature_dependencies=["mom"],
        parameter_config_json="{}",
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[1],
        primary_horizon=1,
        invalidation_criteria=InvalidationCriteria(),
        registered_at_utc="2026-08-28T00:00:00Z",
        author="Auditor",
    )

    verdict_counts: Dict[str, int] = {}
    pass_count = 0

    for seed_idx in range(num_simulations):
        np.random.seed(random_seed + seed_idx)
        trial_matrix = np.random.normal(0.0, 0.01, (T, M))
        is_returns = list(trial_matrix[:, 0])
        oos_returns = list(np.random.normal(0.0, 0.01, T // 2))

        manifest_store: Dict[str, Any] = {}
        strat_id = f"STRAT_NULL_{seed_idx}"
        ledger = _create_trial_ledger(trial_return_matrix=trial_matrix, strategy_id=strat_id, manifest_store=manifest_store)
        grid = _create_perturbation_grid(strat_id=strat_id, manifest_store=manifest_store, base_sharpe=ledger.trials[0].in_sample_sharpe)

        report = gate.evaluate_strategy(
            strategy_id=strat_id,
            hypothesis_id="HYP_BENCHMARK",
            hypothesis_spec=spec,
            in_sample_returns=is_returns,
            out_of_sample_returns=oos_returns,
            trial_ledger=ledger,
            trial_return_matrix=trial_matrix,
            trial_matrix_column_trial_ids=[f"trial_{i}" for i in range(M)],
            perturbation_grid=grid,
            raw_predictive_edge_bps=5.0,
            manifest_store=manifest_store,
        )

        v_name = report.verdict.value
        verdict_counts[v_name] = verdict_counts.get(v_name, 0) + 1
        if report.is_tradeable_alpha:
            pass_count += 1

    p_point, ci_lower, ci_upper = compute_wilson_confidence_interval(pass_count, num_simulations)
    return {
        "experiment_name": "Experiment A: Zero-Alpha Null DGP",
        "num_simulations": num_simulations,
        "sample_size_T": T,
        "exploratory_models_M": M,
        "random_seed": random_seed,
        "pass_count": pass_count,
        "observed_false_positive_rate": p_point,
        "wilson_95_ci": [ci_lower, ci_upper],
        "verdict_distribution": verdict_counts,
    }


# =========================================================================
# EXPERIMENT B: Correlated-Search DGP
# =========================================================================
def run_correlated_search_experiment(
    T: int = 500,
    K: int = 50,
    correlations: Sequence[float] = (0.0, 0.50, 0.85, 0.95, 0.99),
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Experiment B: Characterize DSR and PBO dynamics under varying candidate return collinearity."""
    np.random.seed(random_seed)
    common_signal = np.random.normal(0.0010, 0.010, T)
    results = []

    for rho in correlations:
        trial_matrix = np.zeros((T, K))
        for k in range(K):
            if k == 0:
                trial_matrix[:, k] = common_signal
            else:
                noise = np.random.normal(0.0, 0.010, T)
                trial_matrix[:, k] = rho * common_signal + math.sqrt(max(0.0, 1.0 - rho**2)) * noise

        sharpes = []
        for k in range(K):
            mean_k = np.mean(trial_matrix[:, k])
            std_k = np.std(trial_matrix[:, k], ddof=1)
            sr = (mean_k / std_k) * math.sqrt(252.0)
            sharpes.append(sr)

        var_sharpes = float(np.var(sharpes, ddof=1))
        sr0_period = DeflatedSharpeEngine.compute_expected_max_sharpe_sr0(
            dsr_trials_k=K,
            variance_of_trials=var_sharpes / 252.0,
            mean_of_trials=0.0,
        )
        sr0_annual = sr0_period * math.sqrt(252.0)

        dsr_res = DeflatedSharpeEngine.evaluate_dsr(
            returns=trial_matrix[:, 0],
            dsr_trials_k=K,
            variance_of_trials=var_sharpes / 252.0,
            mean_of_trials=0.0,
            periods_per_year=252.0,
        )

        cpcv = StatisticalValidationGate().cpcv_engine
        is_mat, oos_mat = cpcv.evaluate_balanced_cscv_sharpe_matrices(trial_matrix)
        pbo, mean_logit, std_logit = OverfittingEngine.calculate_pbo(is_mat, oos_mat)

        results.append({
            "correlation_rho": rho,
            "sharpe_mean": float(np.mean(sharpes)),
            "empirical_sharpe_variance_V": var_sharpes,
            "expected_max_sharpe_sr0_annual": sr0_annual,
            "primary_sharpe": sharpes[0],
            "dsr_probability": float(dsr_res.dsr_probability),
            "pbo_estimate": pbo,
            "pbo_rejects": pbo >= 0.25,
        })

    return {
        "experiment_name": "Experiment B: Correlated Search DGP",
        "sample_size_T": T,
        "declared_trials_K": K,
        "random_seed": random_seed,
        "results": results,
    }


# =========================================================================
# EXPERIMENT C: Serial Dependence & HAC Robust Inference
# =========================================================================
def run_serial_dependence_experiment(
    T: int = 1000,
    num_sims: int = 300,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Experiment C: Quantify Type I error inflation under serial autocorrelation and overlapping forward labels."""
    np.random.seed(random_seed)
    scenarios = [
        ("IID_Noise", 0.0, 1),
        ("AR1_phi_0.20", 0.20, 1),
        ("AR1_phi_0.40", 0.40, 1),
        ("Overlapping_H5", 0.0, 5),
        ("Overlapping_H10", 0.0, 10),
    ]

    results = []
    for name, phi, H in scenarios:
        sig_count_asymp = 0
        sig_count_hac = 0

        for s in range(num_sims):
            white_noise = np.random.normal(0.0, 0.01, T + H)
            if phi > 0:
                raw_r = np.zeros(T + H)
                for t in range(1, T + H):
                    raw_r[t] = phi * raw_r[t - 1] + white_noise[t]
            else:
                raw_r = white_noise

            if H > 1:
                returns = np.array([np.sum(raw_r[t:t+H]) for t in range(T)])
            else:
                returns = raw_r[:T]

            mean_r = float(np.mean(returns))
            std_r = float(np.std(returns, ddof=1))
            t_asymp = (mean_r / std_r) * math.sqrt(T) if std_r > 1e-12 else 0.0
            p_asymp = math.erfc(abs(t_asymp) / math.sqrt(2.0))
            if p_asymp <= 0.05:
                sig_count_asymp += 1

            p_hac = float(compute_hac_p_value(returns, max_lags=(H if H > 1 else None)))
            if p_hac <= 0.05:
                sig_count_hac += 1

        p_asymp_est, asymp_ci_l, asymp_ci_u = compute_wilson_confidence_interval(sig_count_asymp, num_sims)
        p_hac_est, hac_ci_l, hac_ci_u = compute_wilson_confidence_interval(sig_count_hac, num_sims)

        results.append({
            "scenario": name,
            "asymptotic_normal_fpr_5pct": p_asymp_est,
            "asymptotic_normal_wilson_95_ci": [asymp_ci_l, asymp_ci_u],
            "asymptotic_inflation_ratio": p_asymp_est / 0.05,
            "hac_newey_west_fpr_5pct": p_hac_est,
            "hac_newey_west_wilson_95_ci": [hac_ci_l, hac_ci_u],
        })

    return {
        "experiment_name": "Experiment C: Serial Dependence & HAC Robust Inference",
        "sample_size_T": T,
        "num_simulations": num_sims,
        "random_seed": random_seed,
        "results": results,
    }


# =========================================================================
# EXPERIMENT D: Statistical Power Analysis (Alternative DGPs)
# =========================================================================
def run_statistical_power_experiment(
    true_sharpe_ratios: Sequence[float] = (0.0, 0.50, 1.00, 1.50, 2.00, 2.50, 3.00),
    num_simulations: int = 50,
    T: int = 500,
    M: int = 10,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Experiment D: Characterize detection power P(PASS) across true non-zero alpha Sharpe levels."""
    gate = StatisticalValidationGate()
    spec = HypothesisSpecification(
        hypothesis_id="HYP_BENCHMARK",
        hypothesis_version="v1.0",
        economic_rationale="Statistical Power Benchmark",
        target_symbol="BTCUSDT",
        feature_dependencies=["mom"],
        parameter_config_json="{}",
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[1],
        primary_horizon=1,
        invalidation_criteria=InvalidationCriteria(),
        registered_at_utc="2026-08-28T00:00:00Z",
        author="Auditor",
    )

    power_curve_diverse = []
    power_curve_collinear = []
    ann_factor = math.sqrt(252.0)
    sigma_daily = 0.010

    for true_sr in true_sharpe_ratios:
        mu_daily = (true_sr / ann_factor) * sigma_daily
        pass_diverse = 0
        pass_collinear = 0

        for seed_idx in range(num_simulations):
            np.random.seed(random_seed + int(true_sr * 1000) + seed_idx)
            primary_is = np.random.normal(mu_daily, sigma_daily, T)
            primary_oos = np.random.normal(mu_daily, sigma_daily, T // 2)

            # Topology 1: Diverse Search Universe (1 true alpha model + (M-1) noise exploration models)
            trial_matrix_div = np.zeros((T, M))
            trial_matrix_div[:, 0] = primary_is
            for m in range(1, M):
                trial_matrix_div[:, m] = np.random.normal(0.0, sigma_daily, T)

            store_div: Dict[str, Any] = {}
            strat_id_div = f"STRAT_PWR_DIV_SR{int(true_sr*100)}_{seed_idx}"
            ledger_div = _create_trial_ledger(trial_return_matrix=trial_matrix_div, strategy_id=strat_id_div, manifest_store=store_div)
            grid_div = _create_perturbation_grid(strat_id=strat_id_div, manifest_store=store_div, base_sharpe=ledger_div.trials[0].in_sample_sharpe)

            rep_div = gate.evaluate_strategy(
                strategy_id=strat_id_div,
                hypothesis_id="HYP_BENCHMARK",
                hypothesis_spec=spec,
                in_sample_returns=list(primary_is),
                out_of_sample_returns=list(primary_oos),
                trial_ledger=ledger_div,
                trial_return_matrix=trial_matrix_div,
                trial_matrix_column_trial_ids=[f"trial_{i}" for i in range(M)],
                perturbation_grid=grid_div,
                raw_predictive_edge_bps=25.0,
                manifest_store=store_div,
            )
            if rep_div.is_tradeable_alpha:
                pass_diverse += 1

            # Topology 2: Collinear Search Universe (1 primary + (M-1) correlated signal perturbations)
            trial_matrix_col = np.zeros((T, M))
            trial_matrix_col[:, 0] = primary_is
            for m in range(1, M):
                noise = np.random.normal(0.0, sigma_daily, T)
                trial_matrix_col[:, m] = 0.85 * primary_is + math.sqrt(1.0 - 0.85**2) * noise

            store_col: Dict[str, Any] = {}
            strat_id_col = f"STRAT_PWR_COL_SR{int(true_sr*100)}_{seed_idx}"
            ledger_col = _create_trial_ledger(trial_return_matrix=trial_matrix_col, strategy_id=strat_id_col, manifest_store=store_col)
            grid_col = _create_perturbation_grid(strat_id=strat_id_col, manifest_store=store_col, base_sharpe=ledger_col.trials[0].in_sample_sharpe)

            rep_col = gate.evaluate_strategy(
                strategy_id=strat_id_col,
                hypothesis_id="HYP_BENCHMARK",
                hypothesis_spec=spec,
                in_sample_returns=list(primary_is),
                out_of_sample_returns=list(primary_oos),
                trial_ledger=ledger_col,
                trial_return_matrix=trial_matrix_col,
                trial_matrix_column_trial_ids=[f"trial_{i}" for i in range(M)],
                perturbation_grid=grid_col,
                raw_predictive_edge_bps=25.0,
                manifest_store=store_col,
            )
            if rep_col.is_tradeable_alpha:
                pass_collinear += 1

        p_div, div_l, div_u = compute_wilson_confidence_interval(pass_diverse, num_simulations)
        p_col, col_l, col_u = compute_wilson_confidence_interval(pass_collinear, num_simulations)

        power_curve_diverse.append({
            "true_annualized_sharpe": true_sr,
            "simulations": num_simulations,
            "pass_count": pass_diverse,
            "power_p_pass": p_div,
            "wilson_95_ci": [div_l, div_u],
        })
        power_curve_collinear.append({
            "true_annualized_sharpe": true_sr,
            "simulations": num_simulations,
            "pass_count": pass_collinear,
            "power_p_pass": p_col,
            "wilson_95_ci": [col_l, col_u],
        })

    return {
        "experiment_name": "Experiment D: Statistical Power Analysis",
        "sample_size_T": T,
        "exploratory_models_M": M,
        "random_seed": random_seed,
        "power_curve_diverse_noise_universe": power_curve_diverse,
        "power_curve_collinear_sweep_universe": power_curve_collinear,
    }



def run_full_dgp_benchmark_suite(
    output_json_path: Optional[Path] = None,
    output_md_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute complete reproducible Phase 6 DGP benchmark suite and persist machine-readable artifacts."""
    print("Executing ACASH Phase 6 DGP Empirical Benchmark Suite...")
    exp_a = run_null_dgp_experiment(num_simulations=100, T=500, M=10, random_seed=42)
    exp_b = run_correlated_search_experiment(T=500, K=50, random_seed=42)
    exp_c = run_serial_dependence_experiment(T=1000, num_sims=300, random_seed=42)
    exp_d = run_statistical_power_experiment(num_simulations=50, T=500, M=10, random_seed=42)

    benchmark_bundle = {
        "suite_name": "ACASH_PHASE6_DGP_BENCHMARK_SUITE",
        "executed_at_utc": "2026-08-30T10:00:00Z",
        "experiment_a_null_dgp": exp_a,
        "experiment_b_correlated_search": exp_b,
        "experiment_c_serial_dependence": exp_c,
        "experiment_d_statistical_power": exp_d,
    }

    if output_json_path is not None:
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_bundle, f, indent=2)

    if output_md_path is not None:
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        md_content = generate_markdown_benchmark_report(benchmark_bundle)
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    return benchmark_bundle


def generate_markdown_benchmark_report(data: Dict[str, Any]) -> str:
    """Generate professional Markdown documentation report from benchmark output."""
    exp_a = data["experiment_a_null_dgp"]
    exp_b = data["experiment_b_correlated_search"]
    exp_c = data["experiment_c_serial_dependence"]
    exp_d = data["experiment_d_statistical_power"]

    lines = [
        "# ACASH Phase 6 Empirical DGP Benchmark Report",
        "",
        "## 1. Experiment A: Zero-Alpha Null DGP (False Positive Rate)",
        f"- **Simulations**: {exp_a['num_simulations']} runs (T={exp_a['sample_size_T']}, M={exp_a['exploratory_models_M']}, Seed={exp_a['random_seed']})",
        f"- **Observed Approval Rate**: `{exp_a['observed_false_positive_rate'] * 100:.2f}%` ({exp_a['pass_count']}/{exp_a['num_simulations']})",
        f"- **Wilson 95% Confidence Interval**: `[{exp_a['wilson_95_ci'][0] * 100:.2f}%, {exp_a['wilson_95_ci'][1] * 100:.2f}%]`",
        f"- **Verdict Distribution**: `{json.dumps(exp_a['verdict_distribution'])}`",
        "",
        "## 2. Experiment B: Correlated Search DGP (Hurdle Dynamics & PBO)",
        "| Correlation $\\rho$ | Empirical $\\operatorname{Var}(\\widehat{SR})$ | $SR_0$ Hurdle (Ann) | DSR Probability | PBO Estimate | PBO Rejection |",
        "| :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for row in exp_b["results"]:
        lines.append(
            f"| {row['correlation_rho']:.2f} | {row['empirical_sharpe_variance_V']:.6f} | "
            f"{row['expected_max_sharpe_sr0_annual']:.4f} | {row['dsr_probability'] * 100:.2f}% | "
            f"{row['pbo_estimate']:.4f} | {'REJECT' if row['pbo_rejects'] else 'PASS'} |"
        )

    lines.extend([
        "",
        "## 3. Experiment C: Serial Dependence & HAC Robust Inference",
        "| Scenario | Asymptotic Normal FPR | Wilson 95% CI | Inflation | HAC Newey-West FPR | HAC Wilson 95% CI |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ])
    for row in exp_c["results"]:
        lines.append(
            f"| {row['scenario']} | {row['asymptotic_normal_fpr_5pct'] * 100:.2f}% | "
            f"[{row['asymptotic_normal_wilson_95_ci'][0]*100:.2f}%, {row['asymptotic_normal_wilson_95_ci'][1]*100:.2f}%] | "
            f"{row['asymptotic_inflation_ratio']:.2f}x | {row['hac_newey_west_fpr_5pct'] * 100:.2f}% | "
            f"[{row['hac_newey_west_wilson_95_ci'][0]*100:.2f}%, {row['hac_newey_west_wilson_95_ci'][1]*100:.2f}%] |"
        )

    lines.extend([
        "",
        "## 4. Experiment D: Statistical Power Analysis (Detection Rate across True $SR$)",
        "",
        "### Topology 1: Diverse Search Universe (1 True Alpha + 9 Exploratory Noise Models)",
        "| True Annualized Sharpe | Simulations | Pass Count | Statistical Power $P(\\text{PASS})$ | Wilson 95% CI |",
        "| :---: | :---: | :---: | :---: | :---: |",
    ])

    for row in exp_d["power_curve_diverse_noise_universe"]:
        lines.append(
            f"| {row['true_annualized_sharpe']:.2f} | {row['simulations']} | "
            f"{row['pass_count']} | {row['power_p_pass'] * 100:.2f}% | "
            f"[{row['wilson_95_ci'][0]*100:.2f}%, {row['wilson_95_ci'][1]*100:.2f}%] |"
        )

    lines.extend([
        "",
        "### Topology 2: Collinear Sweep Universe (1 Primary + 9 Correlated Perturbations $\\rho=0.85$)",
        "| True Annualized Sharpe | Simulations | Pass Count | Statistical Power $P(\\text{PASS})$ | Wilson 95% CI |",
        "| :---: | :---: | :---: | :---: | :---: |",
    ])
    for row in exp_d["power_curve_collinear_sweep_universe"]:
        lines.append(
            f"| {row['true_annualized_sharpe']:.2f} | {row['simulations']} | "
            f"{row['pass_count']} | {row['power_p_pass'] * 100:.2f}% | "
            f"[{row['wilson_95_ci'][0]*100:.2f}%, {row['wilson_95_ci'][1]*100:.2f}%] |"
        )

    return "\n".join(lines)



if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    docs_dir = base_dir / "docs" / "validation"
    json_path = docs_dir / "phase6_methodology_dgp_report.json"
    md_path = docs_dir / "phase6_methodology_dgp_report.md"
    run_full_dgp_benchmark_suite(output_json_path=json_path, output_md_path=md_path)
    print(f"\nBenchmark artifacts written to:\n- {json_path}\n- {md_path}")
