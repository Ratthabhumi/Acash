"""Canonical Schemas, Pydantic Models, and Invariants for Alpha Research & Hypothesis Engine (Phase 4).

Strictly enforces:
- Pre-registered formal hypothesis specification with explicit falsification criteria.
- Discrete bar-indexed forward return schema.
- Configurable HAC inference and bandwidth robustness tracking.
- Search degrees of freedom accounting (ResearchSearchRecord).
- Blind OOS exposure state machine (UNEXPOSED -> EVALUATED_LOCKED -> EXHAUSTED).
- 3-Tier transaction cost configurations with explicit basis point conversion.
- Complete ResearchManifest temporal and methodological lineage.
- Zero production trading logic.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import json
from typing import Any, Dict, Final, List, Optional, Tuple, Union
import pyarrow as pa
from pydantic import BaseModel, ConfigDict, Field, field_validator

from acash.data.schema import DataContractError

# ---------------------------------------------------------------------------
# Enums and Value Objects
# ---------------------------------------------------------------------------


class ExpectedDirection(str, Enum):
    """Expected predictive correlation direction."""
    LONG = "LONG"          # Feature positively correlated with forward return (+1)
    SHORT = "SHORT"        # Feature negatively correlated with forward return (-1)
    DISPERSION = "DISPERSION" # Feature predicts volatility / magnitude rather than direction


class HacBandwidthMethod(str, Enum):
    """HAC Kernel Bandwidth Selection Policy."""
    FIXED_HORIZON_MINUS_ONE = "FIXED_HORIZON_MINUS_ONE"  # Baseline heuristic: L = H - 1
    FIXED_LAG = "FIXED_LAG"                              # User-specified fixed integer lag L
    NEWEY_WEST_PLUGIN = "NEWEY_WEST_PLUGIN"              # L = floor(4 * (T / 100)^(2/9))
    ANDREWS_AR1_PLUGIN = "ANDREWS_AR1_PLUGIN"            # Automatic AR(1) plug-in bandwidth


class SignalTransformMethod(str, Enum):
    """Canonical mapping from raw feature values to standardized bounded trading signals."""
    TANH_ZSCORE = "TANH_ZSCORE"        # S(X) = tanh(z_score(X)) in [-1, 1]
    SIGN = "SIGN"                      # S(X) = sign(X) in {-1, 0, 1}
    IDENTITY_CLIPPED = "IDENTITY_CLIPPED" # S(X) = clip(X, -1, 1)


class SignalTransformConfig(BaseModel):
    """Versioned configuration for transforming raw features into bounded trading signals."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    method: SignalTransformMethod = Field(default=SignalTransformMethod.TANH_ZSCORE)
    clip_limit: Decimal = Field(default=Decimal("3.0"), gt=Decimal("0.0"))


class OosExposureState(str, Enum):
    """Strict Blind Out-of-Sample Lifecycle State Machine."""
    UNEXPOSED = "UNEXPOSED"             # OOS data never accessed for this hypothesis
    EVALUATED_LOCKED = "EVALUATED_LOCKED" # OOS evaluated once; permanently locked
    EXHAUSTED = "EXHAUSTED"             # OOS compromised/spent via unauthorized re-tuning



# ---------------------------------------------------------------------------
# Configuration Models
# ---------------------------------------------------------------------------


class InvalidationCriteria(BaseModel):
    """Pre-registered statistical falsification criteria."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    min_in_sample_rank_ic: Decimal = Field(default=Decimal("0.025"), ge=Decimal("0.0"))
    min_hac_t_stat: Decimal = Field(default=Decimal("2.00"), ge=Decimal("1.5"))
    max_feature_autocorrelation: Decimal = Field(default=Decimal("0.98"), le=Decimal("1.0"))
    min_cost_adjusted_spread_ratio: Decimal = Field(default=Decimal("1.50"), ge=Decimal("1.0"))


class HypothesisSpecification(BaseModel):
    """Formal, immutable pre-registered scientific hypothesis specification."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    hypothesis_id: str
    hypothesis_version: str
    parent_hypothesis_id: Optional[str] = None

    # Structural Economic Theory
    economic_rationale: str

    # Feature Dependencies & Target Instruments
    target_symbol: str
    feature_dependencies: List[str]
    parameter_config_json: str

    # Statistical Expectations
    expected_direction: ExpectedDirection
    target_horizons: List[int]
    primary_horizon: int

    # Falsification Bounds
    invalidation_criteria: InvalidationCriteria

    registered_at_utc: str
    author: str

    def to_canonical_json(self) -> str:
        """Serialize hypothesis specification to canonical JSON using the universal CanonicalConfigSerializer."""
        from acash.core.serialization import CanonicalConfigSerializer
        d = self.model_dump(mode="python")
        return CanonicalConfigSerializer.to_canonical_json(d)



class HacInferencePolicy(BaseModel):
    """Configurable HAC inference policy with robustness check matrix."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    bandwidth_method: HacBandwidthMethod = Field(default=HacBandwidthMethod.FIXED_HORIZON_MINUS_ONE)
    fixed_lag_value: Optional[int] = None
    kernel_type: str = Field(default="bartlett")
    run_bandwidth_robustness_check: bool = Field(default=True)
    robustness_lags: List[int] = Field(default_factory=lambda: [1, 5, 10, 20])


class CostModelConfig(BaseModel):
    """Versioned friction and execution cost configuration."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    quoted_spread_bps: Decimal = Field(default=Decimal("1.0"), ge=Decimal("0.0"))
    roundtrip_broker_fee_bps: Decimal = Field(default=Decimal("0.5"), ge=Decimal("0.0"))
    fixed_slippage_bps: Decimal = Field(default=Decimal("0.5"), ge=Decimal("0.0"))
    latency_delay_ms: int = Field(default=50, ge=0)

    @property
    def total_roundtrip_cost_decimal(self) -> Decimal:
        """Convert total roundtrip friction from basis points to decimal return units."""
        bps_sum = self.quoted_spread_bps + self.roundtrip_broker_fee_bps + self.fixed_slippage_bps
        return bps_sum / Decimal("10000")


class SplitPolicy(BaseModel):
    """Chronological dataset partitioning policy with embargo buffers."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    train_pct: Decimal = Field(default=Decimal("0.60"), gt=Decimal("0.0"), lt=Decimal("1.0"))
    val_pct: Decimal = Field(default=Decimal("0.20"), gt=Decimal("0.0"), lt=Decimal("1.0"))
    oos_pct: Decimal = Field(default=Decimal("0.20"), gt=Decimal("0.0"), lt=Decimal("1.0"))
    embargo_bars: int = Field(default=60, ge=0)


class ResearchSearchRecord(BaseModel):
    """Comprehensive accounting of research search space and multiple-testing exposure."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    experiment_id: str
    hypothesis_id: str

    # Degrees of Freedom Tracking
    parameter_variants_count: int
    feature_variants_tried: List[str]
    label_variants_tried: List[str]
    model_variants_tried: List[str]
    dataset_window_variants_tried: List[str]

    # Selection Governance
    selection_procedure: str
    selected_candidate_id: str
    total_effective_trials: int
    oos_exposure_state: OosExposureState

    def to_canonical_json(self) -> str:
        d = self.model_dump(mode="json")
        return json.dumps(d, sort_keys=True)


class RobustnessCheckRecord(BaseModel):
    """HAC Bandwidth robustness check result at a specific lag."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    lag: int
    beta: Decimal
    hac_se: Decimal
    hac_t_stat: Decimal
    asymptotic_p_value: Decimal


class EvaluationResult(BaseModel):
    """Comprehensive evaluation metrics for a feature-forward return relationship."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    horizon: int
    valid_observations_count: int
    purged_observations_count: int

    # Primary OLS Slope HAC Inference
    beta: Decimal
    hac_se: Decimal
    hac_t_stat: Decimal
    asymptotic_p_value: Decimal
    selected_hac_lag: int

    # Descriptive Association Metrics
    pearson_ic: Optional[Decimal]
    spearman_rank_ic: Optional[Decimal]
    feature_autocorrelation_lag1: Optional[Decimal]

    # 3-Tier Friction Waterfall
    tier1_raw_edge_bps: Decimal
    tier2_net_edge_bps: Decimal
    tier3_economic_edge_bps: Decimal

    # Robustness Checks across Lags
    robustness_matrix: List[RobustnessCheckRecord] = Field(default_factory=list)

    is_statistically_significant: bool
    is_falsified: bool


class ResearchManifest(BaseModel):
    """Immutable provenance record documenting complete research run lineage and results."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_id: str
    experiment_id: str
    hypothesis_id: str
    hypothesis_version: str
    symbol: str

    # Protocol & Estimator Lineage
    inference_estimator: str
    forward_return_definition: str
    hac_bandwidth_method: str
    hac_bandwidth_value: int
    hac_kernel: str
    cost_model_version: str
    purging_policy_version: str
    embargo_policy_version: str

    # Cryptographic Provenance
    input_feature_hashes: List[str]
    parameter_config_hash: str
    search_record_hash: str

    # Temporal Coordinates & Embargo
    train_window: Tuple[str, str]
    validation_window: Tuple[str, str]
    oos_window: Tuple[str, str]
    embargo_bars: int
    purged_train_rows_count: int

    # Statistical Results Summary
    in_sample_beta: Decimal
    in_sample_hac_t_stat: Decimal
    in_sample_rank_ic: Decimal
    oos_beta: Optional[Decimal]
    oos_hac_t_stat: Optional[Decimal]
    oos_rank_ic: Optional[Decimal]
    tier3_economic_edge_bps: Decimal
    is_hypothesis_accepted: bool
    oos_exposure_state: OosExposureState

    software_version: str
    computed_at_utc: str


# ---------------------------------------------------------------------------
# PyArrow Canonical Schemas
# ---------------------------------------------------------------------------

CANONICAL_FORWARD_OUTCOMES_SCHEMA: Final[pa.Schema] = pa.schema([
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("trading_date", pa.date32(), nullable=False),
    pa.field("decision_bar_index", pa.int32(), nullable=False),
    pa.field("decision_bar_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("entry_bar_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("exit_bar_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
    pa.field("entry_price", pa.decimal128(38, 18), nullable=False),
    pa.field("exit_price", pa.decimal128(38, 18), nullable=False),
    pa.field("horizon_bars", pa.int32(), nullable=False),
    pa.field("forward_return", pa.decimal128(38, 18), nullable=True),
    pa.field("is_purged_boundary", pa.bool_(), nullable=False),
])


CANONICAL_HYPOTHESIS_EVALUATION_SCHEMA: Final[pa.Schema] = pa.schema([
    pa.field("hypothesis_id", pa.string(), nullable=False),
    pa.field("symbol", pa.string(), nullable=False),
    pa.field("horizon_bars", pa.int32(), nullable=False),
    pa.field("partition", pa.string(), nullable=False),  # "TRAIN", "VALIDATION", "OOS"
    pa.field("beta", pa.decimal128(38, 18), nullable=False),
    pa.field("hac_se", pa.decimal128(38, 18), nullable=False),
    pa.field("hac_t_stat", pa.decimal128(38, 18), nullable=False),
    pa.field("asymptotic_p_value", pa.decimal128(38, 18), nullable=False),
    pa.field("pearson_ic", pa.decimal128(38, 18), nullable=True),
    pa.field("spearman_rank_ic", pa.decimal128(38, 18), nullable=True),
    pa.field("tier1_raw_edge_bps", pa.decimal128(38, 18), nullable=False),
    pa.field("tier2_net_edge_bps", pa.decimal128(38, 18), nullable=False),
    pa.field("tier3_economic_edge_bps", pa.decimal128(38, 18), nullable=False),
    pa.field("is_falsified", pa.bool_(), nullable=False),
])
