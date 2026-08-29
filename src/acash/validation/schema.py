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
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer, deep_freeze_value
from acash.data.features.engine import to_decimal18


class ValidationGateVerdict(str, Enum):
    """Formal decision emitted by the Statistical Validation Gate."""

    PASS_TRADEABLE_ALPHA = "PASS_TRADEABLE_ALPHA"
    REJECT_MISSING_TRIAL_LEDGER = "REJECT_MISSING_TRIAL_LEDGER"
    REJECT_OVERFIT_DSR = "REJECT_OVERFIT_DSR"
    REJECT_HIGH_PBO = "REJECT_HIGH_PBO"
    REJECT_PARAMETER_FRAGILE = "REJECT_PARAMETER_FRAGILE"
    REJECT_MISSING_PERTURBATION_GRID = "REJECT_MISSING_PERTURBATION_GRID"
    REJECT_MISSING_CPCV_EVIDENCE = "REJECT_MISSING_CPCV_EVIDENCE"
    REJECT_MULTIPLE_TESTING_FWER = "REJECT_MULTIPLE_TESTING_FWER"
    REJECT_HAIRCUT_SHARPE = "REJECT_HAIRCUT_SHARPE"
    REJECT_INSUFFICIENT_TRL = "REJECT_INSUFFICIENT_TRL"
    REJECT_OOS_DEGRADATION = "REJECT_OOS_DEGRADATION"
    REJECT_MISSING_OOS_DATA = "REJECT_MISSING_OOS_DATA"
    REJECT_FRICTION_COLLAPSE = "REJECT_FRICTION_COLLAPSE"


class SelectionCorrectionMode(str, Enum):
    """Operational mode for Sharpe ratio hypothesis testing and selection bias correction."""

    SINGLE_TRIAL = "SINGLE_TRIAL"  # K = 1: Asymptotic Mertens/Opdyke test against hurdle without selection deflation (SR0 = 0)
    MULTIPLE_TRIAL = "MULTIPLE_TRIAL"  # K >= 2: Bailey-López de Prado Gumbel EVT selection deflation using empirical trial variance



class SharpeSpace(str, Enum):
    """Explicit frequency space for Sharpe ratios in trial ledgers and statistical validation reports."""

    PERIOD = "PERIOD"
    ANNUAL = "ANNUAL"


class SearchTrialRecord(BaseModel):
    """Single exploratory trial / parameter configuration tracked in the search space."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    trial_id: str = Field(min_length=1, description="Unique deterministic trial identifier.")
    strategy_id: str = Field(min_length=1)
    hypothesis_id: str = Field(min_length=1)
    feature_names: Sequence[str] = Field(min_length=1, description="Immutable tuple of feature dependencies.")
    parameters: Mapping[str, Any] = Field(
        default_factory=dict, description="Deeply immutable mapping of search parameters."
    )

    in_sample_sharpe: Decimal
    p_value: Decimal = Field(ge=Decimal("0.0"), le=Decimal("1.0"), description="Valid empirical p-value in [0.0, 1.0].")
    p_value_method: str = Field(
        default="ASYMPTOTIC_TWO_SIDED_T_TEST_V1",
        description="Statistical hypothesis test method used to derive p_value.",
    )
    p_value_input_hash: str = Field(
        default="",
        pattern=r"^([0-9a-f]{64})?$",
        description="Canonical SHA-256 hash binding p_value to return series, config, and test method.",
    )
    in_sample_return_series_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
        description="Mandatory 64-hex SHA-256 hash of the trial in-sample return series.",
    )
    config_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
        description="Mandatory 64-hex SHA-256 hash of parameter and feature configuration.",
    )
    execution_manifest_id: str = Field(
        min_length=1, description="Mandatory bound BacktestManifest ID for candidate execution lineage."
    )

    @staticmethod
    def compute_config_sha256(feature_names: Sequence[str], parameters: Mapping[str, Any]) -> str:
        """Deterministic canonical SHA-256 digest of feature dependencies and search parameters using CanonicalConfigSerializer."""
        config_obj = {
            "features": sorted(list(feature_names)),
            "params": parameters,
        }
        return CanonicalConfigSerializer.compute_sha256(config_obj)

    @staticmethod
    def compute_canonical_p_value(in_sample_returns: Union[Sequence[Union[Decimal, float]], np.ndarray]) -> Decimal:

        """Compute canonical two-sided asymptotic t-test p-value from empirical return series."""
        arr = np.array([float(x) for x in in_sample_returns], dtype=np.float64)
        n = len(arr)
        if n < 2:
            return Decimal("1.0")
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1))
        if std <= 1e-12:
            return Decimal("1.0")
        t_stat = (mean / std) * math.sqrt(n)
        p_val = math.erfc(abs(t_stat) / math.sqrt(2.0))
        dec = to_decimal18(Decimal(f"{p_val:.12f}"))
        return dec if dec is not None else Decimal("1.0")


    @staticmethod
    def compute_p_value_input_hash(
        return_series_sha256: str,
        config_sha256: str,
        p_value: Union[Decimal, str, float],
        p_value_method: str = "ASYMPTOTIC_TWO_SIDED_T_TEST_V1",
    ) -> str:
        """Deterministic canonical SHA-256 binding p-value to return series, config, and derivation method."""
        val_str = f"{float(p_value):.12f}" if isinstance(p_value, (Decimal, float)) else str(p_value)
        payload = f"{return_series_sha256}:{config_sha256}:{val_str}:{p_value_method}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest().lower()

    @field_validator("parameters", mode="after")
    @classmethod
    def freeze_parameters_field(cls, v: Any) -> Any:
        """Ensure parameters mapping is recursively frozen into deeply immutable MappingProxyType."""
        return deep_freeze_value(v)

    @model_validator(mode="before")
    @classmethod
    def populate_mandatory_hashes_and_types(cls, data: Any) -> Any:
        """Ensure cryptographic hashes and deep immutability are strictly populated for all records."""
        if isinstance(data, dict):
            if "feature_names" in data and isinstance(data["feature_names"], (list, set, tuple)):
                data["feature_names"] = tuple(sorted(list(data["feature_names"])))
            if "parameters" in data and data["parameters"] is not None:
                data["parameters"] = deep_freeze_value(data["parameters"])
            if "config_sha256" not in data or data["config_sha256"] is None:
                features = data.get("feature_names", ())
                params = data.get("parameters", {})
                data["config_sha256"] = cls.compute_config_sha256(features, params)
            if "in_sample_return_series_sha256" not in data or data["in_sample_return_series_sha256"] is None:
                if "in_sample_returns" in data and data["in_sample_returns"] is not None:
                    from acash.validation.gate import _compute_canonical_series_sha256
                    data["in_sample_return_series_sha256"] = _compute_canonical_series_sha256(data["in_sample_returns"])
                else:
                    trial_id = data.get("trial_id", "unknown")
                    raise DataContractError(
                        f"in_sample_return_series_sha256 requires actual in_sample_returns "
                        f"or an explicitly supplied verified artifact hash for trial '{trial_id}'."
                    )
            if "p_value" not in data and "in_sample_returns" in data and data["in_sample_returns"] is not None:
                data["p_value"] = cls.compute_canonical_p_value(data["in_sample_returns"])
            if ("p_value_input_hash" not in data or not data["p_value_input_hash"]) and "p_value" in data:
                method = data.get("p_value_method", "ASYMPTOTIC_TWO_SIDED_T_TEST_V1")
                data["p_value_input_hash"] = cls.compute_p_value_input_hash(
                    return_series_sha256=data["in_sample_return_series_sha256"],
                    config_sha256=data["config_sha256"],
                    p_value=data["p_value"],
                    p_value_method=method,
                )
        return data


    @classmethod
    def create(
        cls,
        trial_id: str,
        strategy_id: str,
        hypothesis_id: str,
        feature_names: Sequence[str],
        parameters: Mapping[str, Any],
        in_sample_sharpe: Decimal,
        p_value: Decimal,
        execution_manifest_id: str,
        in_sample_returns: Optional[Sequence[Union[Decimal, float]]] = None,
        in_sample_return_series_sha256: Optional[str] = None,
        config_sha256: Optional[str] = None,
        p_value_method: str = "ASYMPTOTIC_TWO_SIDED_T_TEST_V1",
        p_value_input_hash: Optional[str] = None,
    ) -> "SearchTrialRecord":
        """Factory helper creating validated SearchTrialRecord with automatic SHA-256 digest derivation."""
        from acash.validation.gate import _compute_canonical_series_sha256

        frozen_params = deep_freeze_value(parameters)
        sorted_features = tuple(sorted(list(feature_names)))

        if in_sample_return_series_sha256 is None:
            if in_sample_returns is None:
                raise DataContractError(
                    f"Must provide either in_sample_returns or in_sample_return_series_sha256 for trial '{trial_id}'."
                )
            in_sample_return_series_sha256 = _compute_canonical_series_sha256(in_sample_returns)

        if config_sha256 is None:
            config_sha256 = cls.compute_config_sha256(sorted_features, frozen_params)

        if p_value_input_hash is None:
            p_value_input_hash = cls.compute_p_value_input_hash(
                return_series_sha256=in_sample_return_series_sha256,
                config_sha256=config_sha256,
                p_value=p_value,
                p_value_method=p_value_method,
            )

        return cls(
            trial_id=trial_id,
            strategy_id=strategy_id,
            hypothesis_id=hypothesis_id,
            feature_names=sorted_features,
            parameters=frozen_params,
            in_sample_sharpe=in_sample_sharpe,
            p_value=p_value,
            p_value_method=p_value_method,
            p_value_input_hash=p_value_input_hash,
            in_sample_return_series_sha256=in_sample_return_series_sha256,
            config_sha256=config_sha256,
            execution_manifest_id=execution_manifest_id,
        )


class SearchTrialLedger(BaseModel):
    """Sovereign ledger accounting for all exploratory trials to strictly couple search intensity with DSR & FWER.

    SEARCH SPACE CENSUS CONTRACT:
    Once sealed, SearchTrialLedger constitutes the authoritative, exhaustive census of all exploratory
    search trials conducted within the research session. The total trial count K = |trials| represents the
    upper bound on declared selection opportunities, guaranteeing that all downstream multiple-testing
    and overfitting evaluations (DSR, Holm-Bonferroni FWER, Haircut Sharpe) penalize selection bias
    conservatively and truthfully across the entire exploration history.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    ledger_id: str = Field(min_length=1, description="Unique ledger identifier.")
    strategy_id: str = Field(min_length=1, description="Bound strategy identifier.")
    hypothesis_id: str = Field(min_length=1, description="Bound hypothesis identifier.")
    trials: Tuple[SearchTrialRecord, ...] = Field(
        min_length=1, description="Non-empty immutable tuple of exploratory trials."
    )
    sharpe_space: SharpeSpace = Field(
        default=SharpeSpace.PERIOD,
        description="Explicit SharpeSpace (PERIOD or ANNUAL) frequency of recorded Sharpes.",
    )
    is_sealed: bool = Field(default=False, description="True if search universe is sealed and immutable.")
    sealed_at_utc: Optional[str] = Field(default=None, description="UTC timestamp when search universe was sealed.")
    ledger_digest: Optional[str] = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        description="Cryptographic SHA-256 fingerprint of the sealed ledger universe (64 lowercase hex).",
    )

    @model_validator(mode="before")
    @classmethod
    def coerce_trials_tuple(cls, data: Any) -> Any:
        """Coerce list of trials to immutable tuple."""
        if isinstance(data, dict):
            if "trials" in data and isinstance(data["trials"], (list, tuple)):
                data["trials"] = tuple(data["trials"])
            if "sharpe_space" in data and isinstance(data["sharpe_space"], str):
                try:
                    data["sharpe_space"] = SharpeSpace(data["sharpe_space"])
                except ValueError as e:
                    raise DataContractError(f"Invalid sharpe_space '{data['sharpe_space']}': must be 'PERIOD' or 'ANNUAL'.") from e
        return data

    def compute_ledger_digest(self) -> str:
        """Deterministic canonical SHA-256 fingerprint over all candidate trial lineage records.

        CONTRACT SPECIFICATION:
        - `ledger_digest` represents the pure mathematical CONTENT IDENTITY of the candidate search universe.
        - `sealed_at_utc` represents the OPERATIONAL LIFECYCLE METADATA recording when the sealing occurred.
        - Sealing timestamps do NOT alter the content identity of the underlying search universe.
        """
        canonical_obj = {
            "ledger_id": self.ledger_id,
            "strategy_id": self.strategy_id,
            "hypothesis_id": self.hypothesis_id,
            "sharpe_space": self.sharpe_space.value if isinstance(self.sharpe_space, SharpeSpace) else str(self.sharpe_space),
            "trials": [
                {
                    "trial_id": t.trial_id,
                    "config_sha256": t.config_sha256,
                    "in_sample_return_series_sha256": t.in_sample_return_series_sha256,
                    "execution_manifest_id": t.execution_manifest_id,
                    "in_sample_sharpe": t.in_sample_sharpe,
                    "p_value": t.p_value,
                    "p_value_method": t.p_value_method,
                    "p_value_input_hash": t.p_value_input_hash,
                }
                for t in self.trials
            ],
        }
        return CanonicalConfigSerializer.compute_sha256(canonical_obj)


    def seal(self, sealed_at_utc: Optional[str] = None) -> "SearchTrialLedger":
        """Explicitly seal the search trial universe with canonical timestamp and immutable cryptographic digest."""
        if self.is_sealed and self.ledger_digest is not None:
            return self

        from datetime import datetime, timezone
        now_utc = sealed_at_utc or datetime.now(timezone.utc).isoformat()
        digest = self.compute_ledger_digest()
        return self.model_copy(
            update={
                "is_sealed": True,
                "sealed_at_utc": now_utc,
                "ledger_digest": digest,
            }
        )

    @model_validator(mode="after")
    def validate_ledger_identity_and_uniqueness(self) -> "SearchTrialLedger":
        """Enforce strict trial uniqueness and strategy/hypothesis identity consistency."""
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

        # 3. Enforce strict ledger_digest invariant on sealed ledgers (No SEALED + NO DIGEST escape hatch)
        if self.is_sealed:
            if self.ledger_digest is None:
                raise DataContractError(
                    f"SearchTrialLedger '{self.ledger_id}' is marked is_sealed=True but ledger_digest is None. "
                    f"Sealed ledgers must possess a non-null canonical cryptographic ledger_digest."
                )
            expected = self.compute_ledger_digest()
            if self.ledger_digest != expected:
                raise DataContractError(
                    f"SearchTrialLedger '{self.ledger_id}' ledger_digest mismatch: "
                    f"stored digest '{self.ledger_digest}' does not match computed '{expected}'."
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
        return max(0.0, var)


    @property
    def p_values(self) -> List[Decimal]:
        """All empirical p-values recorded in the ledger."""
        return [t.p_value for t in self.trials]


class ParameterPerturbationPoint(BaseModel):
    """Single execution point in a parameter sensitivity grid carrying cryptographic lineage proof."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    parameter_value: Decimal = Field(gt=Decimal("0.0"), description="Perturbed parameter value.")
    run_id: str = Field(min_length=3, description="Unique backtest/experiment run ID.")
    manifest_id: str = Field(
        pattern=r"^[0-9a-zA-Z_-]{8,64}$",
        description="Mandatory BacktestManifest identifier binding.",
    )
    input_artifact_hash: str = Field(
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 digest of composite input lineage SHA256(hypothesis_spec_sha256:strategy_config_hash) (64 lowercase hex).",
    )
    output_artifact_hash: str = Field(
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 canonical digest of the executed BacktestManifest artifact (64 lowercase hex).",
    )
    actual_sharpe: Decimal = Field(description="Measured Sharpe ratio from this independent execution run.")

    def validate_manifest_binding(self, manifest: Any) -> bool:
        """Verify 4-way cryptographic and execution semantic binding against a real BacktestManifest.

        Enforces:
        1. manifest is an instance of BacktestManifest (Strict type contract, zero duck-typing)
        2. manifest_id == point.manifest_id
        3. manifest execution Sharpe == point.actual_sharpe
        4. manifest canonical output digest (compute_sha256()) == point.output_artifact_hash
        5. manifest input configuration lineage SHA256(hypothesis_spec_sha256:strategy_config_hash) == point.input_artifact_hash
        """
        from acash.backtest.schema import BacktestManifest

        if not isinstance(manifest, BacktestManifest):
            raise DataContractError(
                f"Point manifest '{self.manifest_id}' must be an instance of BacktestManifest, "
                f"got {type(manifest).__name__}."
            )

        if manifest.manifest_id != self.manifest_id:
            raise DataContractError(
                f"Manifest ID mismatch: point has '{self.manifest_id}', manifest has '{manifest.manifest_id}'."
            )

        exec_summary = manifest.execution_summary
        if exec_summary.sharpe_ratio is None:
            raise DataContractError(f"Manifest '{manifest.manifest_id}' execution_summary has no sharpe_ratio.")

        if Decimal(str(exec_summary.sharpe_ratio)) != self.actual_sharpe:
            raise DataContractError(
                f"Sharpe ratio mismatch: point has {self.actual_sharpe}, manifest has {exec_summary.sharpe_ratio}."
            )

        # Output artifact hash validation: must strictly equal manifest.compute_sha256()
        manifest_out_hash = manifest.compute_sha256()
        if self.output_artifact_hash != manifest_out_hash:
            raise DataContractError(
                f"Output artifact hash mismatch: point has '{self.output_artifact_hash}', manifest produced '{manifest_out_hash}'."
            )

        # Input artifact hash validation: must strictly equal SHA256(hypothesis_spec_sha256:strategy_config_hash)
        expected_in = hashlib.sha256(
            f"{manifest.hypothesis_spec_sha256}:{manifest.strategy_config_hash}".encode("utf-8")
        ).hexdigest()
        if self.input_artifact_hash != expected_in:
            raise DataContractError(
                f"Input artifact hash mismatch: point has '{self.input_artifact_hash}', "
                f"expected exact '{expected_in}' = SHA256(hypothesis_spec_sha256:strategy_config_hash)."
            )

        return True




class ParameterPerturbationGrid(BaseModel):
    """Strict parameter perturbation grid enforcing exact +/- 25% boundary invariants and execution lineage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    base_parameter_name: str
    base_parameter_value: Decimal = Field(gt=Decimal("0.0"), description="Base parameter theta_0 > 0.")
    points: List[ParameterPerturbationPoint] = Field(
        min_length=3, max_length=3,
        description="Strict 3-point execution list [0.75 * theta_0, 1.0 * theta_0, 1.25 * theta_0] in exact semantic order.",
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
        """Enforce exact [0.75, 1.0, 1.25] geometric perturbation invariants and distinct execution lineage."""
        if len(self.points) != 3:
            raise DataContractError("Parameter perturbation grid must have exactly 3 points [0.75*theta, 1.0*theta, 1.25*theta].")

        # 1. Check distinct execution runs, manifests, and output artifacts
        run_ids = {p.run_id for p in self.points}
        if len(run_ids) != 3:
            raise DataContractError(
                f"Parameter perturbation requires 3 distinct execution run_ids, got {len(run_ids)}: {run_ids}."
            )
        manifest_ids = {p.manifest_id for p in self.points}
        if len(manifest_ids) != 3:
            raise DataContractError(
                f"Parameter perturbation requires 3 distinct manifest_ids, got {len(manifest_ids)}: {manifest_ids}."
            )
        output_hashes = {p.output_artifact_hash for p in self.points}
        if len(output_hashes) != 3:
            raise DataContractError(
                f"Parameter perturbation requires 3 distinct output_artifact_hashes, got {len(output_hashes)}: {output_hashes}."
            )

        # 2. Check exact ordered geometry without tolerance
        theta = self.base_parameter_value
        expected_left = theta * Decimal("0.75")
        expected_mid = theta
        expected_right = theta * Decimal("1.25")

        if self.points[0].parameter_value != expected_left:
            raise DataContractError(
                f"Grid left point parameter_value '{self.points[0].parameter_value}' does not exactly equal 0.75 * {theta} = '{expected_left}'."
            )
        if self.points[1].parameter_value != expected_mid:
            raise DataContractError(
                f"Grid mid point parameter_value '{self.points[1].parameter_value}' does not exactly equal 1.0 * {theta} = '{expected_mid}'."
            )
        if self.points[2].parameter_value != expected_right:
            raise DataContractError(
                f"Grid right point parameter_value '{self.points[2].parameter_value}' does not exactly equal 1.25 * {theta} = '{expected_right}'."
            )

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
    sample_kurtosis: Decimal = Field(description="Pearson sample kurtosis g_2 of returns (normal distribution = 3.0, lower bound 1.0).")
    sample_size_t: int = Field(description="Sample length in return periods T.")
    effective_trials_k: int = Field(description="Effective trial count K derived from SearchTrialLedger.")
    declared_trials_k: int = Field(default=1, description="Authoritative declared search opportunities count recorded in ledger.")
    effective_independent_trials_k: Optional[int] = Field(
        default=None,
        description="Estimated number of statistically independent trials (K_eff <= K). Defaults to K as upper bound.",
    )
    independence_assumption: str = Field(
        default="CONSERVATIVE_SEARCH_OPPORTUNITIES_UPPER_BOUND",
        description="Explicit assumption governing the relation between declared trials and statistical independence.",
    )
    trial_variance_used: Decimal = Field(description="Trial Sharpe variance V used in Gumbel maximum calculation.")
    dsr_statistic: Decimal = Field(description="Calculated DSR standard normal test statistic.")
    dsr_p_value: Decimal = Field(description="Deflated Sharpe Ratio p-value (probability that true SR > SR_0).")
    is_statistically_significant: bool = Field(description="True if dsr_p_value >= min_dsr_probability (e.g. 0.95).")
    min_track_record_length_bars: int = Field(description="Minimum Track Record Length (MinTRL) in bars required for statistical significance.")
    has_sufficient_track_record: bool = Field(description="True if sample_size_t >= min_track_record_length_bars.")
    sharpe_space: SharpeSpace = Field(default=SharpeSpace.ANNUAL, description="Frequency space of the reported Sharpe ratios (ANNUAL).")
    inference_space: SharpeSpace = Field(default=SharpeSpace.PERIOD, description="Frequency space of the internal hypothesis test calculations (PERIOD).")

    selection_correction_mode: SelectionCorrectionMode = Field(default=SelectionCorrectionMode.MULTIPLE_TRIAL, description="Selection correction mode.")

    sr0_estimator: str = Field(default="EMPIRICAL_TRIAL_VARIANCE_GUMBEL_V1", description="Identifier of the SR_0 calculation method.")
    variance_estimator: str = Field(default="EMPIRICAL_SAMPLE_VARIANCE_DDOF1", description="Identifier of the trial variance estimation method.")

    @model_validator(mode="before")
    @classmethod
    def populate_declared_trials(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "declared_trials_k" not in data and "effective_trials_k" in data:
                data["declared_trials_k"] = data["effective_trials_k"]
        return data


class MultipleTestingResult(BaseModel):
    """Multiple-testing correction outputs over SearchTrialLedger exploratory trials."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    effective_trials_k: int = Field(description="Total evaluated trials K from ledger.")
    raw_p_values: List[Decimal] = Field(description="Ascending sorted empirical p-values from trial ledger.")
    holm_bonferroni_p_values: List[Decimal] = Field(description="Family-Wise Error Rate (FWER) adjusted p-values.")
    benjamini_hochberg_q_values: List[Decimal] = Field(description="False Discovery Rate (FDR) adjusted q-values.")
    bonferroni_haircut_sharpe_ratio: Decimal = Field(
        default=Decimal("0.0"),
        description="ACASH Bonferroni-adjusted multiple-testing Haircut Sharpe Ratio (ANNUAL space).",
    )
    haircut_sharpe_ratio: Decimal = Field(
        default=Decimal("0.0"),
        description="Backward-compatible alias for bonferroni_haircut_sharpe_ratio.",
    )
    bonferroni_haircut_sharpe_ratio_period: Decimal = Field(
        default=Decimal("0.0"),
        description="ACASH Bonferroni-adjusted Haircut Sharpe Ratio evaluated strictly in PERIOD return space.",
    )
    sharpe_space: SharpeSpace = Field(
        default=SharpeSpace.ANNUAL,
        description="Frequency space of the reported bonferroni_haircut_sharpe_ratio (ANNUAL).",
    )
    inference_space: SharpeSpace = Field(
        default=SharpeSpace.PERIOD,
        description="Frequency space where statistical hypothesis testing and p-value inversion are conducted (PERIOD).",
    )
    is_fwer_significant: bool = Field(description="True if primary hypothesis satisfies Holm-Bonferroni step-down.")

    @model_validator(mode="before")
    @classmethod
    def synchronize_haircut_ratio(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "bonferroni_haircut_sharpe_ratio" in data and "haircut_sharpe_ratio" not in data:
                data["haircut_sharpe_ratio"] = data["bonferroni_haircut_sharpe_ratio"]
            elif "haircut_sharpe_ratio" in data and "bonferroni_haircut_sharpe_ratio" not in data:
                data["bonferroni_haircut_sharpe_ratio"] = data["haircut_sharpe_ratio"]
        return data





class OverfittingReport(BaseModel):
    """Composite diagnostics on backtest overfitting, parameter surface fragility, and friction monotonicity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pbo_estimate: Decimal = Field(description="Probability of Backtest Overfitting (PBO) via mid-rank log-odds.")
    logits_distribution_mean: Decimal = Field(description="Mean of the empirical log-odds lambda distribution.")
    logits_distribution_std: Decimal = Field(description="Standard deviation of the empirical log-odds lambda distribution.")
    is_pbo_acceptable: bool = Field(description="True if PBO < max_acceptable_pbo (e.g. 0.25).")
    parameter_fragility_max_curvature: Decimal = Field(description="Maximum second-order discrete curvature across parameter perturbations.")
    is_parameter_stable: bool = Field(description="True if parameter surface is flat (curvature below tolerance and degradation <= 30%).")
    analytical_friction_monotonicity_passed: bool = Field(description="True if simulated return degrades monotonically under increasing friction stress multipliers.")


class ValidationPolicyConfig(BaseModel):
    """Governance policy thresholds for the Statistical Validation Gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    confidence_level_alpha: Decimal = Field(default=Decimal("0.05"), gt=Decimal("0.0"), lt=Decimal("1.0"))
    min_dsr_probability: Decimal = Field(default=Decimal("0.95"), ge=Decimal("0.50"), le=Decimal("1.0"))
    max_acceptable_pbo: Decimal = Field(default=Decimal("0.25"), gt=Decimal("0.0"), lt=Decimal("1.0"))
    min_oos_sharpe_retention_pct: Decimal = Field(default=Decimal("50.0"), ge=Decimal("0.0"), description="Minimum OOS Sharpe retention vs In-Sample (%).")
    enforce_fwer_significance: bool = Field(default=True, description="Whether Holm-Bonferroni FWER significance is required for Gate PASS.")
    min_haircut_sharpe: Decimal = Field(default=Decimal("0.0"), description="Minimum acceptable Haircut Sharpe Ratio (HLZ 2016).")
    sharpe_consistency_tolerance: Decimal = Field(
        default=Decimal("0.001"),
        ge=Decimal("0.0"),
        le=Decimal("0.1"),
        description="Methodological tolerance bound epsilon_sr for ledger vs empirical sample Sharpe consistency.",
    )


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
    enforce_fwer_significance: bool = Field(default=True, description="Whether Holm-Bonferroni FWER significance is required for Gate PASS.")
    min_haircut_sharpe: Decimal = Field(default=Decimal("0.0"), description="Minimum acceptable Haircut Sharpe Ratio (HLZ 2016).")
    periods_per_year: Decimal = Field(default=Decimal("252.0"), gt=Decimal("0.0"), description="Annualization frequency (e.g. 252 for daily, 252*24 for hourly).")
    sharpe_consistency_tolerance: Decimal = Field(
        default=Decimal("0.001"),
        ge=Decimal("0.0"),
        le=Decimal("0.1"),
        description="Methodological tolerance bound epsilon_sr for ledger vs empirical sample Sharpe consistency.",
    )





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
    dsr_result: Optional[DSRResult] = Field(default=None, description="DSR inference output, None if validation failed closed prior to computation.")
    multiple_testing_result: Optional[MultipleTestingResult] = Field(default=None, description="Multiple testing output, None if validation failed closed prior to computation.")
    overfitting_report: Optional[OverfittingReport] = Field(default=None, description="Overfitting output, None if validation failed closed prior to computation.")
    in_sample_sharpe: Optional[Decimal] = None
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
            } if self.dsr_result is not None else None,
            "evidence_digest": self.evidence_digest,
            "hypothesis_id": self.hypothesis_id,
            "in_sample_sharpe": str(self.in_sample_sharpe) if self.in_sample_sharpe is not None else None,
            "multiple_testing_result": {
                "haircut_sharpe_ratio": str(self.multiple_testing_result.haircut_sharpe_ratio),
                "is_fwer_significant": self.multiple_testing_result.is_fwer_significant,
                "raw_p_values": [str(p) for p in self.multiple_testing_result.raw_p_values],
            } if self.multiple_testing_result is not None else None,
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
            } if self.overfitting_report is not None else None,
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
            "in_sample_sharpe": str(self.in_sample_sharpe) if self.in_sample_sharpe is not None else None,
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

