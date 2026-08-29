"""Validation Engine Pydantic Schemas and Data Contracts (Phase 6).

Strictly enforces:
- Immutable, frozen Pydantic models with extra="forbid".
- Exact Decimal and int types for canonical parameters.
- Identity and lineage integrity: SearchTrialLedger unique trial_id, matching strategy_id/hypothesis_id.
- ParameterPerturbationPoint requiring run_id, input_artifact_hash, output_artifact_hash, and actual_sharpe.
- Formal DSR/SR0 provenance: SelectionCorrectionMode (SINGLE_TRIAL vs MULTIPLE_TRIAL) and explicit estimator specification.
- Analytical friction stress demarcation (analytical_friction_monotonicity_passed).
- Cryptographic DAG: evidence_digest (pure evidence) -> decision_digest (evidence + governance) -> validation_id.
"""

from decimal import Decimal
from enum import Enum
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from acash.core.domain.exceptions import DataContractError
from acash.data.features.engine import to_decimal18


class ValidationGateVerdict(str, Enum):
    """Formal decision emitted by the Statistical Validation Gate."""

    PASS_TRADEABLE_ALPHA = "PASS_TRADEABLE_ALPHA"
    REJECT_MISSING_TRIAL_LEDGER = "REJECT_MISSING_TRIAL_LEDGER"
    REJECT_OVERFIT_DSR = "REJECT_OVERFIT_DSR"
    REJECT_HIGH_PBO = "REJECT_HIGH_PBO"
    REJECT_PARAMETER_FRAGILE = "REJECT_PARAMETER_FRAGILE"
    REJECT_INSUFFICIENT_TRL = "REJECT_INSUFFICIENT_TRL"
    REJECT_OOS_DEGRADATION = "REJECT_OOS_DEGRADATION"
    REJECT_MISSING_OOS_DATA = "REJECT_MISSING_OOS_DATA"
    REJECT_FRICTION_COLLAPSE = "REJECT_FRICTION_COLLAPSE"


class SelectionCorrectionMode(str, Enum):
    """Operational mode for Sharpe ratio hypothesis testing and selection bias correction."""

    SINGLE_TRIAL = "SINGLE_TRIAL"  # K = 1: Asymptotic Mertens/Opdyke test against hurdle without selection deflation (SR0 = 0)
    MULTIPLE_TRIAL = "MULTIPLE_TRIAL"  # K >= 2: Bailey-López de Prado Gumbel EVT selection deflation using empirical trial variance


class SearchTrialRecord(BaseModel):
    """Single exploratory trial / parameter configuration tracked in the search space."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trial_id: str = Field(min_length=1, description="Unique deterministic trial identifier.")
    strategy_id: str = Field(min_length=1)
    hypothesis_id: str = Field(min_length=1)
    feature_names: List[str]
    parameters: Dict[str, Any]
    in_sample_sharpe: Decimal
    p_value: Decimal = Field(ge=Decimal("0.0"), le=Decimal("1.0"), description="Valid empirical p-value in [0.0, 1.0].")


class SearchTrialLedger(BaseModel):
    """Sovereign ledger accounting for all exploratory trials to strictly couple search intensity with DSR & FWER."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ledger_id: str = Field(min_length=1, description="Unique deterministic ledger identifier.")
    strategy_id: str = Field(min_length=1, description="Strategy identifier bound to this ledger.")
    hypothesis_id: str = Field(min_length=1, description="Hypothesis identifier bound to this ledger.")
    trials: List[SearchTrialRecord] = Field(min_length=1, description="Immutable record of all explored trials.")
    sharpe_space: str = Field(default="PERIOD", description="'PERIOD' or 'ANNUAL' frequency of recorded Sharpes.")

    @model_validator(mode="after")
    def validate_ledger_integrity(self) -> "SearchTrialLedger":
        """Enforce identity, hypothesis coupling, and uniqueness invariants."""
        if not self.trials:
            raise DataContractError("SearchTrialLedger cannot be empty: must contain at least 1 trial.")

        # 1. Enforce unique trial_ids (K_ledger == |unique trial_id|)
        trial_ids = [t.trial_id for t in self.trials]
        unique_ids = set(trial_ids)
        if len(unique_ids) != len(trial_ids):
            raise DataContractError(
                f"SearchTrialLedger contains duplicate trial_ids: {len(trial_ids)} records but only {len(unique_ids)} unique IDs."
            )

        # 2. Enforce strategy_id and hypothesis_id consistency across all trials
        for t in self.trials:
            if t.strategy_id != self.strategy_id:
                raise DataContractError(
                    f"Trial {t.trial_id} strategy_id '{t.strategy_id}' does not match ledger strategy_id '{self.strategy_id}'."
                )
            if t.hypothesis_id != self.hypothesis_id:
                raise DataContractError(
                    f"Trial {t.trial_id} hypothesis_id '{t.hypothesis_id}' does not match ledger hypothesis_id '{self.hypothesis_id}'."
                )

        return self

    @property
    def total_trials(self) -> int:
        """Total number of exploratory trials K."""
        return len(self.trials)

    def get_empirical_sharpe_variance(self) -> float:
        """Empirical sample variance of Sharpe ratios across recorded trials.

        Raises DataContractError if fewer than 2 trials exist and variance is requested.
        """
        if len(self.trials) < 2:
            raise DataContractError(
                f"Cannot compute empirical trial variance with fewer than 2 recorded trials (got {len(self.trials)}). "
                f"Single-trial DSR must operate under SelectionCorrectionMode.SINGLE_TRIAL."
            )
        sharpes = [float(t.in_sample_sharpe) for t in self.trials]
        var = float(np.var(sharpes, ddof=1))
        return max(1e-12, var)

    @property
    def p_values(self) -> List[Decimal]:
        """All empirical p-values recorded in the ledger."""
        return [t.p_value for t in self.trials]


class ParameterPerturbationPoint(BaseModel):
    """Single execution point in a parameter sensitivity grid carrying cryptographic lineage proof."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    parameter_value: Decimal = Field(gt=Decimal("0.0"), description="Perturbed parameter value.")
    run_id: str = Field(min_length=3, description="Unique backtest/experiment run ID.")
    input_artifact_hash: str = Field(min_length=16, description="SHA-256 digest of input configuration & data.")
    output_artifact_hash: str = Field(min_length=16, description="SHA-256 digest of backtest execution artifacts.")
    actual_sharpe: Decimal = Field(description="Measured Sharpe ratio from this independent execution run.")
    manifest_id: Optional[str] = Field(default=None, description="Optional BacktestManifest identifier linkage.")


class ParameterPerturbationGrid(BaseModel):
    """Strict parameter perturbation grid enforcing +/- 25% boundary invariants and execution lineage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    base_parameter_name: str
    base_parameter_value: Decimal = Field(gt=Decimal("0.0"), description="Base parameter theta_0 > 0.")
    points: List[ParameterPerturbationPoint] = Field(
        min_length=3, max_length=3,
        description="Strict 3-point execution list [0.75 * theta_0, 1.0 * theta_0, 1.25 * theta_0]."
    )

    @property
    def grid_values(self) -> List[Decimal]:
        """Extracted parameter values at each point."""
        return [p.parameter_value for p in self.points]

    @property
    def sharpe_profile(self) -> List[Decimal]:
        """Extracted measured Sharpe ratios across execution points."""
        return [p.actual_sharpe for p in self.points]

    @model_validator(mode="after")
    def validate_grid_geometry_and_lineage(self) -> "ParameterPerturbationGrid":
        """Enforce strict [0.75, 1.0, 1.25] geometric perturbation invariants and distinct execution lineage."""
        if len(self.points) != 3:
            raise DataContractError("Parameter perturbation grid must have exactly 3 points [0.75*theta, 1.0*theta, 1.25*theta].")

        # 1. Check distinct execution runs
        run_ids = {p.run_id for p in self.points}
        if len(run_ids) != 3:
            raise DataContractError(
                f"Parameter perturbation requires 3 distinct execution run_ids, got {len(run_ids)}: {run_ids}"
            )

        # 2. Check geometry
        theta = self.base_parameter_value
        expected_left = theta * Decimal("0.75")
        expected_mid = theta
        expected_right = theta * Decimal("1.25")

        tol = Decimal("1e-6")
        if abs(self.points[0].parameter_value - expected_left) > tol:
            raise DataContractError(f"Grid left point {self.points[0].parameter_value} does not equal 0.75 * {theta} = {expected_left}")
        if abs(self.points[1].parameter_value - expected_mid) > tol:
            raise DataContractError(f"Grid mid point {self.points[1].parameter_value} does not equal 1.0 * {theta} = {expected_mid}")
        if abs(self.points[2].parameter_value - expected_right) > tol:
            raise DataContractError(f"Grid right point {self.points[2].parameter_value} does not equal 1.25 * {theta} = {expected_right}")

        return self


class FrictionStressParameters(BaseModel):
    """Component-wise friction parameters connecting directly with Phase 4/5 Reality Gap decomposition."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    spread_bps: Decimal = Field(default=Decimal("2.0"), ge=Decimal("0.0"))
    fee_bps: Decimal = Field(default=Decimal("1.0"), ge=Decimal("0.0"))
    slippage_bps: Decimal = Field(default=Decimal("0.5"), ge=Decimal("0.0"))
    latency_drift_bps: Decimal = Field(default=Decimal("0.3"), ge=Decimal("0.0"))
    maker_adverse_selection_bps: Decimal = Field(default=Decimal("0.2"), ge=Decimal("0.0"))


class CPCVPartition(BaseModel):
    """Single combinatorial cross-validation split containing train, test, purged, and embargoed index sets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    combination_id: int = Field(description="Deterministic 0-indexed combination identifier.")
    test_group_indices: List[int] = Field(description="Group indices assigned to testing.")
    train_indices: List[int] = Field(description="Sample indices assigned to model training.")
    test_indices: List[int] = Field(description="Sample indices assigned to out-of-sample testing.")
    purged_indices: List[int] = Field(description="Sample indices purged due to label window overlap.")
    embargoed_indices: List[int] = Field(description="Sample indices embargoed to prevent boundary leakage.")


class DSRResult(BaseModel):
    """Statistical output from the Deflated Sharpe Ratio (Bailey & López de Prado 2014) inference engine."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    estimated_sharpe: Decimal = Field(description="Sample annualized Sharpe ratio.")
    benchmark_sharpe: Decimal = Field(description="Target hurdle benchmark Sharpe (default 0.0).")
    expected_max_sharpe_sr0: Decimal = Field(description="Expected maximum Sharpe ratio under the null hypothesis given K trials.")
    sample_skewness: Decimal = Field(description="Fisher-Pearson sample skewness g_1 of returns.")
    sample_kurtosis: Decimal = Field(ge=Decimal("1.0"), description="Pearson sample fourth moment kurtosis g_2 of returns (normal = 3.0).")
    effective_trials_k: int = Field(ge=1, description="Total number of exploratory trials K.")
    selection_correction_mode: SelectionCorrectionMode = Field(description="Mode of selection bias adjustment (SINGLE_TRIAL or MULTIPLE_TRIAL).")
    sr0_estimator: str = Field(default="EMPIRICAL_TRIAL_VARIANCE_GUMBEL_V1", description="Formal specification of the SR0 expectation model.")
    variance_estimator: str = Field(default="EMPIRICAL_SAMPLE_VARIANCE_DDOF1", description="Variance estimation method for trial Sharpes.")
    sharpe_space: str = Field(default="PERIOD", description="Frequency space evaluated ('PERIOD' or 'ANNUAL').")
    trial_variance_used: Decimal = Field(description="Empirical variance of trials V used in SR0 calculation.")
    sample_size_t: int = Field(description="Number of observations / return periods.")
    dsr_statistic: Decimal = Field(description="Standardized asymptotic DSR test statistic z.")
    dsr_p_value: Decimal = Field(description="P-value of null hypothesis rejection (DSR probability).")
    min_track_record_length_bars: int = Field(description="Minimum observation bars required for statistical significance at target alpha.")
    is_statistically_significant: bool = Field(description="True if DSR p-value >= 0.95 (alpha <= 0.05).")
    has_sufficient_track_record: bool = Field(description="True if sample_size_t >= min_track_record_length_bars.")


class MultipleTestingResult(BaseModel):
    """Results of Family-Wise Error Rate (FWER) and False Discovery Rate (FDR) corrections across K trials."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_p_values: List[Decimal]
    holm_bonferroni_p_values: List[Decimal] = Field(description="Step-down FWER adjusted p-values.")
    benjamini_hochberg_q_values: List[Decimal] = Field(description="FDR adjusted q-values.")
    haircut_sharpe_ratio: Decimal = Field(description="Haircut Sharpe ratio adjusting for K orthogonal trials (Harvey, Liu, Zhu 2016).")
    is_fwer_significant: bool = Field(description="True if top strategy passes Holm-Bonferroni at alpha <= 0.05.")


class OverfittingReport(BaseModel):
    """Diagnostics on Probability of Backtest Overfitting (PBO) and parameter sensitivity curvature."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pbo_estimate: Decimal = Field(description="Empirical probability of backtest overfitting with mid-rank tie handling.")
    logits_distribution_mean: Decimal = Field(description="Mean of relative rank log-odds distribution.")
    logits_distribution_std: Decimal = Field(description="Standard deviation of relative rank log-odds distribution.")
    parameter_fragility_max_curvature: Decimal = Field(description="Second-order discrete curvature across +/- 25% perturbation.")
    is_pbo_acceptable: bool = Field(description="True if PBO < 0.25.")
    is_parameter_stable: bool = Field(description="True if degradation across +/- 25% perturbation <= 30%.")
    analytical_friction_monotonicity_passed: bool = Field(description="True if returns decay monotonically under component-wise analytical friction stress curve.")


class ValidationConfig(BaseModel):
    """Master configuration for the Statistical Validation Gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    num_groups_n: int = Field(default=10, ge=3, description="Number of contiguous groups for CPCV.")
    num_test_groups_k: int = Field(default=2, ge=1, description="Number of test groups per combinatorial split.")
    embargo_bars: int = Field(default=5, ge=0, description="Number of bars embargoed after each test window.")
    confidence_level_alpha: Decimal = Field(default=Decimal("0.05"), gt=Decimal("0.0"), lt=Decimal("1.0"))
    min_dsr_probability: Decimal = Field(default=Decimal("0.95"), ge=Decimal("0.50"), le=Decimal("1.0"))
    max_acceptable_pbo: Decimal = Field(default=Decimal("0.25"), gt=Decimal("0.0"), lt=Decimal("1.0"))
    min_oos_sharpe_retention_pct: Decimal = Field(default=Decimal("50.0"), ge=Decimal("0.0"), description="Minimum OOS Sharpe retention vs In-Sample (%).")


class ValidationReport(BaseModel):
    """Immutable, sovereign validation certificate emitted by the Statistical Validation Gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    validation_id: str = Field(description="Unique cryptographic validation report identifier (decision_digest prefix).")
    evidence_digest: str = Field(description="Deterministic SHA-256 digest of underlying statistical evidence.")
    decision_digest: str = Field(description="Deterministic SHA-256 digest of evidence + governance verdict.")
    strategy_id: str
    hypothesis_id: str
    verdict: ValidationGateVerdict
    is_tradeable_alpha: bool
    dsr_result: DSRResult
    multiple_testing_result: MultipleTestingResult
    overfitting_report: OverfittingReport
    in_sample_sharpe: Decimal
    out_of_sample_sharpe: Optional[Decimal] = None
    oos_retention_pct: Optional[Decimal] = None
    created_timestamp_utc: str = Field(description="Auxiliary non-canonical timestamp.")

    def to_canonical_evidence_json(self) -> str:
        """Emit deterministic, sorted JSON representation of the underlying mathematical evidence.

        Strictly excludes governance verdicts, decision digests, validation_id, and runtime timestamps.
        """
        data = {
            "dsr_result": {
                "benchmark_sharpe": str(self.dsr_result.benchmark_sharpe),
                "dsr_p_value": str(self.dsr_result.dsr_p_value),
                "dsr_statistic": str(self.dsr_result.dsr_statistic),
                "effective_trials_k": self.dsr_result.effective_trials_k,
                "estimated_sharpe": str(self.dsr_result.estimated_sharpe),
                "expected_max_sharpe_sr0": str(self.dsr_result.expected_max_sharpe_sr0),
                "has_sufficient_track_record": self.dsr_result.has_sufficient_track_record,
                "is_statistically_significant": self.dsr_result.is_statistically_significant,
                "min_track_record_length_bars": self.dsr_result.min_track_record_length_bars,
                "sample_kurtosis": str(self.dsr_result.sample_kurtosis),
                "sample_size_t": self.dsr_result.sample_size_t,
                "sample_skewness": str(self.dsr_result.sample_skewness),
                "selection_correction_mode": self.dsr_result.selection_correction_mode.value,
                "sharpe_space": self.dsr_result.sharpe_space,
                "sr0_estimator": self.dsr_result.sr0_estimator,
                "trial_variance_used": str(self.dsr_result.trial_variance_used),
                "variance_estimator": self.dsr_result.variance_estimator,
            },
            "evidence_digest": self.evidence_digest,
            "hypothesis_id": self.hypothesis_id,
            "in_sample_sharpe": str(self.in_sample_sharpe),
            "multiple_testing_result": {
                "haircut_sharpe_ratio": str(self.multiple_testing_result.haircut_sharpe_ratio),
                "is_fwer_significant": self.multiple_testing_result.is_fwer_significant,
                "raw_p_values": [str(p) for p in self.multiple_testing_result.raw_p_values],
            },
            "oos_retention_pct": str(self.oos_retention_pct) if self.oos_retention_pct is not None else None,
            "out_of_sample_sharpe": str(self.out_of_sample_sharpe) if self.out_of_sample_sharpe is not None else None,
            "overfitting_report": {
                "analytical_friction_monotonicity_passed": self.overfitting_report.analytical_friction_monotonicity_passed,
                "is_parameter_stable": self.overfitting_report.is_parameter_stable,
                "is_pbo_acceptable": self.overfitting_report.is_pbo_acceptable,
                "logits_distribution_mean": str(self.overfitting_report.logits_distribution_mean),
                "logits_distribution_std": str(self.overfitting_report.logits_distribution_std),
                "parameter_fragility_max_curvature": str(self.overfitting_report.parameter_fragility_max_curvature),
                "pbo_estimate": str(self.overfitting_report.pbo_estimate),
            },
            "strategy_id": self.strategy_id,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def to_canonical_report_json(self) -> str:
        """Emit deterministic, sorted JSON representation of the sealed governance report.

        Includes evidence digest, decision digest, verdict, and validation_id.
        Excludes only non-canonical runtime created_timestamp_utc.
        """
        data = {
            "decision_digest": self.decision_digest,
            "evidence_digest": self.evidence_digest,
            "hypothesis_id": self.hypothesis_id,
            "in_sample_sharpe": str(self.in_sample_sharpe),
            "is_tradeable_alpha": self.is_tradeable_alpha,
            "oos_retention_pct": str(self.oos_retention_pct) if self.oos_retention_pct is not None else None,
            "out_of_sample_sharpe": str(self.out_of_sample_sharpe) if self.out_of_sample_sharpe is not None else None,
            "strategy_id": self.strategy_id,
            "validation_id": self.validation_id,
            "verdict": self.verdict.value,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def to_canonical_json(self) -> str:
        """Backward-compatible alias for canonical report serialization."""
        return self.to_canonical_report_json()
