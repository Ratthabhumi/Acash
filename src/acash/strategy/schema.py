"""Phase 17 Strategy Admission Standard & Regime-Aware Governance Schemas.

Canonical domain contracts, enums, evidence vectors, and forensic schemas for:
- Quantitative Market State & Feature Engineering (PriceStructure, MarketDynamics, Microstructure)
- Regime Classification & Uncertainty (ClassificationStatus, ConfidenceAssessment)
- Performance Attribution, Skill-vs-Luck, and Alternative Explanations
- Effective Evidence Sample & Dependency Modeling
- 11-Gate Strategy Admission Lifecycle & Allocation Safety Bounds
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import math
from typing import Any, Mapping, Optional, Protocol, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from acash.core.domain.exceptions import DataContractError


def _ensure_utc(dt: datetime, field_name: str) -> datetime:
    """Validate that datetime is strictly timezone-aware and in UTC."""
    if dt.tzinfo is None or dt.tzinfo != timezone.utc:
        raise DataContractError(f"{field_name} must be timezone-aware UTC datetime, got {dt}.")
    return dt


def _verify_finite_decimal(val: Any, field_name: str) -> Decimal:
    """Validate that value is a finite Decimal and not NaN or Infinity."""
    try:
        dec_val: Decimal = val if isinstance(val, Decimal) else Decimal(str(val))
    except Exception as exc:
        raise DataContractError(f"Field '{field_name}' must be Decimal-convertible: {exc}") from exc
    if dec_val.is_nan() or dec_val.is_infinite():
        raise DataContractError(f"Field '{field_name}' must be finite Decimal, got {dec_val}.")
    return dec_val


# ============================================================================
# 1. ENUMS & CLASSIFICATION TYPES
# ============================================================================

class VolumeType(str, Enum):
    """Authoritative volume provenance classification."""
    TICK_VOLUME = "TICK_VOLUME"
    REAL_VOLUME = "REAL_VOLUME"
    EXCHANGE_VOLUME = "EXCHANGE_VOLUME"
    UNKNOWN = "UNKNOWN"


class ParameterProvenance(str, Enum):
    """Provenance and epistemological authority for quantitative parameters and thresholds."""
    GOVERNANCE_DEFINED = "GOVERNANCE_DEFINED"
    PROVISIONAL = "PROVISIONAL"
    RESEARCH_DERIVED = "RESEARCH_DERIVED"
    HISTORICAL_EMPIRICAL = "HISTORICAL_EMPIRICAL"
    BROKER_OBSERVED = "BROKER_OBSERVED"
    VALIDATED = "VALIDATED"


class ClassificationStatus(str, Enum):
    """Classification status for regime inference."""
    CLASSIFIED = "CLASSIFIED"
    UNCLASSIFIED = "UNCLASSIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ConfidenceAssessment(str, Enum):
    """Derived assessment of classification confidence."""
    ACCEPTABLE = "ACCEPTABLE"
    LOW = "LOW"


class SkillEvidenceStatus(str, Enum):
    """Evidence status regarding persistent excess return."""
    NO_EVIDENCE = "NO_EVIDENCE"
    PRELIMINARY = "PRELIMINARY"
    SUPPORTIVE = "SUPPORTIVE"
    STRONG = "STRONG"
    INSUFFICIENT_TO_DETERMINE = "INSUFFICIENT_TO_DETERMINE"


class LuckSensitivity(str, Enum):
    """Sensitivity of observed performance to random sequencing and sample construction."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class ObservedOutcomeUncertainty(str, Enum):
    """Uncertainty regarding the observed outcome's dispersion."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class PersistenceAssessment(str, Enum):
    """Evidence of edge persistence across separate sample blocks."""
    NOT_TESTED = "NOT_TESTED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    SUPPORTED = "SUPPORTED"
    STRONGLY_SUPPORTED = "STRONGLY_SUPPORTED"


class EvidenceSupportLevel(str, Enum):
    """Granular evidence support level for individual validation dimensions."""
    SUPPORTED = "SUPPORTED"
    WEAK = "WEAK"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_TESTED = "NOT_TESTED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FactorModelType(str, Enum):
    """Applicable asset-class factor decomposition model."""
    NONE = "NONE"
    MARKET_SPECIFIC = "MARKET_SPECIFIC"
    RESEARCH_DEFINED = "RESEARCH_DEFINED"
    VALIDATED = "VALIDATED"


class ExplanationStatus(str, Enum):
    """Evaluation status of an alternative counter-explanation."""
    PLAUSIBLE = "PLAUSIBLE"
    TESTED_REJECTED = "TESTED_REJECTED"
    SUPPORTED = "SUPPORTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNTESTED = "UNTESTED"


class StrategyMechanism(str, Enum):
    """Core market interaction and economic mechanism of a strategy."""
    FORECASTING = "FORECASTING"
    LIQUIDITY_PROVISION = "LIQUIDITY_PROVISION"
    ARBITRAGE = "ARBITRAGE"
    CARRY = "CARRY"
    VOLATILITY = "VOLATILITY"
    EXECUTION = "EXECUTION"
    OTHER_RESEARCH_DEFINED = "OTHER_RESEARCH_DEFINED"


class StrategyStyle(str, Enum):
    """Behavioral and structural execution style of a strategy."""
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    BREAKOUT = "BREAKOUT"
    MARKET_NEUTRAL = "MARKET_NEUTRAL"
    TREND_FOLLOWING = "TREND_FOLLOWING"
    GRID_PROGRESSION = "GRID_PROGRESSION"
    OTHER = "OTHER"


class StrategyAdmissionStatus(str, Enum):
    """Sovereign governance admission status of a strategy."""
    ADMITTED = "ADMITTED"
    CONDITIONALLY_ADMITTED = "CONDITIONALLY_ADMITTED"
    OBSERVE_ONLY = "OBSERVE_ONLY"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


class StrategyLifecycleState(str, Enum):
    """Catalog progression lifecycle state of a strategy."""
    CANDIDATE = "CANDIDATE"
    IN_EVALUATION = "IN_EVALUATION"
    GOVERNANCE_REVIEW = "GOVERNANCE_REVIEW"
    CATALOG_ACTIVE = "CATALOG_ACTIVE"
    CATALOG_SUSPENDED = "CATALOG_SUSPENDED"
    ARCHIVED = "ARCHIVED"


class StrategyEvidenceLevel(str, Enum):
    """Evidence provenance and environmental realism level (NOT a universal quality score)."""
    LEVEL_0_HYPOTHESIS = "LEVEL_0_HYPOTHESIS"
    LEVEL_1_BACKTEST = "LEVEL_1_BACKTEST"
    LEVEL_2_OUT_OF_SAMPLE = "LEVEL_2_OUT_OF_SAMPLE"
    LEVEL_3_STRESS_MONTE_CARLO = "LEVEL_3_STRESS_MONTE_CARLO"
    LEVEL_4_FORWARD_DEMO = "LEVEL_4_FORWARD_DEMO"
    LEVEL_5_EXECUTION_REALITY = "LEVEL_5_EXECUTION_REALITY"
    LEVEL_6_LIVE_EXECUTION = "LEVEL_6_LIVE_EXECUTION"


# ============================================================================
# 2. FORENSIC LINEAGE & EFFECTIVE SAMPLE
# ============================================================================

class DataProvenance(BaseModel):
    """Immutable provenance record of market and feature data."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    data_source: str
    symbol: str
    timeframe: str
    timestamp_utc: datetime
    data_version: str = "1.0.0"
    feature_version: str = "1.0.0"
    lookback_bars: int
    calculation_version: str = "1.0.0"
    missing_data_policy: str = "FAIL_CLOSED"
    volume_type: VolumeType = VolumeType.UNKNOWN

    @model_validator(mode="before")
    @classmethod
    def _validate_provenance(cls, data: Any) -> Any:
        if isinstance(data, dict):
            ts = data.get("timestamp_utc")
            if isinstance(ts, datetime):
                _ensure_utc(ts, "timestamp_utc")
            lb = data.get("lookback_bars")
            if lb is not None and int(lb) <= 0:
                raise DataContractError(f"lookback_bars must be strictly positive, got {lb}.")
        return data


class EffectiveEvidenceSample(BaseModel):
    """Methodology-dependent effective sample size estimation accounting for dependence."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_observation_count: int
    effective_sample_size: Decimal
    estimator_method: str
    dependency_model: str
    assumptions: Tuple[str, ...]
    effective_sample_confidence: Decimal = Field(default=Decimal("1.0"))
    observed_regimes_count: int = 1
    provenance: ParameterProvenance = ParameterProvenance.RESEARCH_DERIVED

    @model_validator(mode="before")
    @classmethod
    def _validate_effective_sample(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw = data.get("raw_observation_count")
            if raw is not None and int(raw) < 0:
                raise DataContractError(f"raw_observation_count cannot be negative, got {raw}.")
            eff = data.get("effective_sample_size")
            if eff is not None:
                eff_dec = _verify_finite_decimal(eff, "effective_sample_size")
                if eff_dec < Decimal("0.0"):
                    raise DataContractError(f"effective_sample_size cannot be negative, got {eff_dec}.")
                if raw is not None and eff_dec > Decimal(str(raw)) * Decimal("1.01"):
                    raise DataContractError(
                        f"effective_sample_size ({eff_dec}) cannot materially exceed raw_observation_count ({raw})."
                    )
        return data


# ============================================================================
# 3. QUANTITATIVE MEASUREMENT FEATURE FAMILIES
# ============================================================================

class PriceStructureMeasurements(BaseModel):
    """Continuous quantitative measurements derived from OHLC price geometry."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    normalized_returns: Tuple[Decimal, ...]
    range_atr_ratio: Decimal
    body_range_ratio: Decimal
    wick_asymmetry: Decimal
    close_location: Decimal
    gap_ratio: Decimal
    is_range_expansion: bool

    @model_validator(mode="before")
    @classmethod
    def _validate_geometry(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Validate body_range_ratio in [0.0, 1.0]
            brr = data.get("body_range_ratio")
            if brr is not None:
                brr_dec = _verify_finite_decimal(brr, "body_range_ratio")
                if not (Decimal("0.0") <= brr_dec <= Decimal("1.0")):
                    raise DataContractError(f"body_range_ratio must be in [0.0, 1.0], got {brr_dec}.")

            # Validate wick_asymmetry in [-1.0, 1.0]
            wa = data.get("wick_asymmetry")
            if wa is not None:
                wa_dec = _verify_finite_decimal(wa, "wick_asymmetry")
                if not (Decimal("-1.0") <= wa_dec <= Decimal("1.0")):
                    raise DataContractError(f"wick_asymmetry must be in [-1.0, 1.0], got {wa_dec}.")

            # Validate close_location in [0.0, 1.0]
            cl = data.get("close_location")
            if cl is not None:
                cl_dec = _verify_finite_decimal(cl, "close_location")
                if not (Decimal("0.0") <= cl_dec <= Decimal("1.0")):
                    raise DataContractError(f"close_location must be in [0.0, 1.0], got {cl_dec}.")

            # Validate returns are finite
            rets = data.get("normalized_returns")
            if rets is not None:
                for idx, r in enumerate(rets):
                    _verify_finite_decimal(r, f"normalized_returns[{idx}]")
        return data


class MarketDynamicsMeasurements(BaseModel):
    """Continuous quantitative measurements of volatility, momentum, trend, and volume."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    trend_intensity: Decimal
    momentum_velocity: Decimal
    realized_volatility: Decimal
    volume_zscore: Decimal
    benchmark_correlation: Decimal

    @model_validator(mode="before")
    @classmethod
    def _validate_dynamics(cls, data: Any) -> Any:
        if isinstance(data, dict):
            vol = data.get("realized_volatility")
            if vol is not None:
                vol_dec = _verify_finite_decimal(vol, "realized_volatility")
                if vol_dec < Decimal("0.0"):
                    raise DataContractError(f"realized_volatility cannot be negative, got {vol_dec}.")
            corr = data.get("benchmark_correlation")
            if corr is not None:
                corr_dec = _verify_finite_decimal(corr, "benchmark_correlation")
                if not (Decimal("-1.0") <= corr_dec <= Decimal("1.0")):
                    raise DataContractError(f"benchmark_correlation must be in [-1.0, 1.0], got {corr_dec}.")
        return data


class MicrostructureMeasurements(BaseModel):
    """Continuous quantitative measurements of execution spread, depth, and latency."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    spread_bps: Decimal
    effective_spread_bps: Optional[Decimal] = None
    order_book_imbalance: Optional[Decimal] = None
    execution_latency_ms: Optional[Decimal] = None

    @model_validator(mode="before")
    @classmethod
    def _validate_microstructure(cls, data: Any) -> Any:
        if isinstance(data, dict):
            spr = data.get("spread_bps")
            if spr is not None:
                spr_dec = _verify_finite_decimal(spr, "spread_bps")
                if spr_dec < Decimal("0.0"):
                    raise DataContractError(f"spread_bps cannot be negative, got {spr_dec}.")
            lat = data.get("execution_latency_ms")
            if lat is not None:
                lat_dec = _verify_finite_decimal(lat, "execution_latency_ms")
                if lat_dec < Decimal("0.0"):
                    raise DataContractError(f"execution_latency_ms cannot be negative, got {lat_dec}.")
        return data


class MarketStateVector(BaseModel):
    """Continuous empirical market measurements vector. Strictly measurement-only, zero discrete regime tags."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    provenance: DataProvenance
    price_structure: PriceStructureMeasurements
    market_dynamics: MarketDynamicsMeasurements
    microstructure: MicrostructureMeasurements


# ============================================================================
# 4. REGIME & INTERPRETATION CONTRACTS
# ============================================================================

class RegimeClassificationEstimate(BaseModel):
    """Discrete regime interpretation derived from MarketStateVector."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: ClassificationStatus
    confidence_score: Decimal
    confidence_assessment: ConfidenceAssessment
    provisional_label: str = ""
    probabilities: Mapping[str, Decimal] = Field(default_factory=dict)
    classification_model_id: str = "UNASSIGNED"
    provenance_digest: str = ""
    threshold_provenance: ParameterProvenance = ParameterProvenance.PROVISIONAL

    @model_validator(mode="before")
    @classmethod
    def _validate_estimate(cls, data: Any) -> Any:
        if isinstance(data, dict):
            conf = data.get("confidence_score")
            if conf is not None:
                conf_dec = _verify_finite_decimal(conf, "confidence_score")
                if not (Decimal("0.0") <= conf_dec <= Decimal("1.0")):
                    raise DataContractError(f"confidence_score must be in [0.0, 1.0], got {conf_dec}.")
            status = data.get("status")
            if status in (ClassificationStatus.UNCLASSIFIED, ClassificationStatus.INSUFFICIENT_EVIDENCE):
                # When unclassified or insufficient, provisional label must be empty or explicitly unclassified
                if data.get("provisional_label") and data.get("provisional_label") not in ("", "UNCLASSIFIED"):
                    raise DataContractError(
                        f"Unclassified/insufficient regime status cannot carry active label: {data.get('provisional_label')}"
                    )
        return data


# ============================================================================
# 5. ATTRIBUTION, SKILL EVIDENCE & ALTERNATIVE EXPLANATIONS
# ============================================================================

class PerformanceAttributionAssessment(BaseModel):
    """Forensic decomposition of observed performance into structural, systematic, and residual components."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    gross_return: Decimal
    net_return: Decimal
    benchmark_return: Decimal = Decimal("0.0")

    factor_model_type: FactorModelType = FactorModelType.NONE
    factor_model_id: str = "NONE"
    applicability_scope: str = "NONE"

    market_beta_exposure: Decimal = Decimal("0.0")
    factor_exposure_summary: Mapping[str, Decimal] = Field(default_factory=dict)
    regime_exposure_summary: Mapping[str, Decimal] = Field(default_factory=dict)
    volatility_exposure: Decimal = Decimal("0.0")
    liquidity_exposure: Decimal = Decimal("0.0")
    leverage_exposure: Decimal = Decimal("1.0")

    execution_contribution: Decimal = Decimal("0.0")
    estimated_excess_return_component: Decimal = Decimal("0.0")
    residual_component: Decimal = Decimal("0.0")

    luck_sensitivity: LuckSensitivity = LuckSensitivity.UNKNOWN
    outcome_uncertainty: ObservedOutcomeUncertainty = ObservedOutcomeUncertainty.UNKNOWN
    persistence_assessment: PersistenceAssessment = PersistenceAssessment.NOT_TESTED
    concentration_risk: str = "UNKNOWN"
    attribution_confidence: Decimal = Field(default=Decimal("0.0"))
    methodology_version: str = "1.0.0"
    provenance: ParameterProvenance = ParameterProvenance.RESEARCH_DERIVED

    @model_validator(mode="before")
    @classmethod
    def _validate_attribution(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field_name in ("gross_return", "net_return", "benchmark_return", "attribution_confidence"):
                if field_name in data:
                    _verify_finite_decimal(data[field_name], field_name)
        return data


class SkillEvidence(BaseModel):
    """Multi-dimensional skill evidence vector strictly forbidding scalar composite scores."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    out_of_sample_support: EvidenceSupportLevel = EvidenceSupportLevel.NOT_TESTED
    walk_forward_support: EvidenceSupportLevel = EvidenceSupportLevel.NOT_TESTED
    regime_coverage_support: EvidenceSupportLevel = EvidenceSupportLevel.NOT_TESTED
    execution_realism_support: EvidenceSupportLevel = EvidenceSupportLevel.NOT_TESTED
    robustness_support: EvidenceSupportLevel = EvidenceSupportLevel.NOT_TESTED
    attribution_support: EvidenceSupportLevel = EvidenceSupportLevel.NOT_TESTED
    persistence_support: EvidenceSupportLevel = EvidenceSupportLevel.NOT_TESTED
    sample_quality_support: EvidenceSupportLevel = EvidenceSupportLevel.NOT_TESTED
    unresolved_alternatives_count: int = 0
    statistical_confidence: Decimal = Decimal("0.0")

    @model_validator(mode="before")
    @classmethod
    def _validate_skill_vector(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Prohibit composite score injection
            if "skill_score" in data or "composite_score" in data:
                raise DataContractError(
                    "Scalar composite skill scores (e.g. skill_score) are strictly prohibited in ACASH governance."
                )
            if "unresolved_alternatives_count" in data and int(data["unresolved_alternatives_count"]) < 0:
                raise DataContractError("unresolved_alternatives_count cannot be negative.")
        return data


class AlternativeExplanation(BaseModel):
    """Evaluation record of a counter-hypothesis explaining observed strategy profitability."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    explanation_id: str
    hypothesis: str
    status: ExplanationStatus
    supporting_evidence_summary: str
    unresolved_risk: str
    provenance: ParameterProvenance = ParameterProvenance.RESEARCH_DERIVED


class AlternativeExplanationRegister(BaseModel):
    """Structured register of all evaluated alternative explanations for a strategy candidate."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_id: str
    eval_timestamp_utc: datetime
    explanations: Tuple[AlternativeExplanation, ...]
    has_unresolved_critical_explanations: bool = False

    @model_validator(mode="before")
    @classmethod
    def _validate_register(cls, data: Any) -> Any:
        if isinstance(data, dict):
            ts = data.get("eval_timestamp_utc")
            if isinstance(ts, datetime):
                _ensure_utc(ts, "eval_timestamp_utc")
        return data


class WinnerSelectionRisk(BaseModel):
    """Quantification of tournament winner's curse and multiple-testing selection bias."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    tournament_size: int = 1
    parameter_search_count: int = 1
    variant_count: int = 1
    data_snooping_risk_level: str = "MODERATE"
    haircut_discount_pct: Decimal = Decimal("0.20")

    @model_validator(mode="before")
    @classmethod
    def _validate_winner_risk(cls, data: Any) -> Any:
        if isinstance(data, dict):
            hc = data.get("haircut_discount_pct")
            if hc is not None:
                hc_dec = _verify_finite_decimal(hc, "haircut_discount_pct")
                if not (Decimal("0.0") <= hc_dec <= Decimal("1.0")):
                    raise DataContractError(f"haircut_discount_pct must be in [0.0, 1.0], got {hc_dec}.")
        return data


# ============================================================================
# 6. STRATEGY DEFINITION & ADMISSION CONTRACTS
# ============================================================================

class StrategyDefinition(BaseModel):
    """Gate 0 complete structural specification of an executable strategy candidate."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_id: str
    strategy_name: str
    strategy_version: str
    mechanism: StrategyMechanism
    style: StrategyStyle
    instrument_universe: Tuple[str, ...]
    timeframe: str
    entry_logic_summary: str
    exit_logic_summary: str
    sizing_method: str
    max_positions: int
    max_gross_exposure_ratio: Decimal
    dependencies: Tuple[str, ...] = Field(default_factory=tuple)
    known_limitations: Tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="before")
    @classmethod
    def _validate_strategy_def(cls, data: Any) -> Any:
        if isinstance(data, dict):
            mp = data.get("max_positions")
            if mp is not None and int(mp) <= 0:
                raise DataContractError(f"max_positions must be strictly positive, got {mp}.")
            mge = data.get("max_gross_exposure_ratio")
            if mge is not None:
                mge_dec = _verify_finite_decimal(mge, "max_gross_exposure_ratio")
                if mge_dec <= Decimal("0.0"):
                    raise DataContractError(f"max_gross_exposure_ratio must be strictly positive, got {mge_dec}.")
        return data


class EconomicHypothesis(BaseModel):
    """Gate 1 underlying market rationale and explicit falsification criteria."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    hypothesis_id: str
    mechanism_rationale: str
    expected_edge_source: str
    falsification_criteria: Tuple[str, ...]
    known_failure_regimes: Tuple[str, ...]


class StressScenarioSpec(BaseModel):
    """Gate 4 canonical stress testing scenario specification with explicit provenance."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str
    scenario_class: str
    perturbation_description: str
    parameter_provenance: ParameterProvenance
    calibration_method: str
    required_observations: Tuple[str, ...]
    pass_fail_semantics: str
    applicability_basis: str
    is_mandatory: bool = True


class StrategyRegimeObservation(BaseModel):
    """Empirical conditional performance metrics for a specific Strategy under an observed Market State."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_id: str
    regime_label: str
    effective_sample: EffectiveEvidenceSample
    expectancy_bps: Decimal
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown_pct: Decimal
    tail_cvar_pct: Optional[Decimal] = None
    peak_margin_utilization_pct: Decimal = Decimal("0.0")
    evidence_status: SkillEvidenceStatus = SkillEvidenceStatus.INSUFFICIENT_TO_DETERMINE


# ============================================================================
# 7. CAPITAL ALLOCATION ELIGIBILITY CONTRACTS (Governance Only)
# ============================================================================

class AllocationSafetyBounds(BaseModel):
    """Deterministic hard safety bounds governing capital and exposure ceilings."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_notional_usd: Decimal
    max_risk_budget_pct: Decimal
    max_gross_exposure_ratio: Decimal
    drawdown_stepdown_pct: Decimal = Decimal("0.50")

    @model_validator(mode="before")
    @classmethod
    def _validate_safety_bounds(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field_name in ("max_notional_usd", "max_risk_budget_pct", "max_gross_exposure_ratio"):
                if field_name in data:
                    val = _verify_finite_decimal(data[field_name], field_name)
                    if val < Decimal("0.0"):
                        raise DataContractError(f"Field '{field_name}' cannot be negative, got {val}.")
        return data


class StrategyAllocationProposal(BaseModel):
    """Target capital allocation proposal emitted by an allocation policy. Zero allocation is always valid."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_id: str
    proposed_weight: Decimal
    proposed_notional_usd: Decimal
    rationale: str
    is_eligible: bool
    allocation_zero_enforced: bool = False

    @model_validator(mode="before")
    @classmethod
    def _validate_allocation(cls, data: Any) -> Any:
        if isinstance(data, dict):
            wt = data.get("proposed_weight")
            if wt is not None:
                wt_dec = _verify_finite_decimal(wt, "proposed_weight")
                if not (Decimal("0.0") <= wt_dec <= Decimal("1.0")):
                    raise DataContractError(f"proposed_weight must be in [0.0, 1.0], got {wt_dec}.")
            notional = data.get("proposed_notional_usd")
            if notional is not None:
                notional_dec = _verify_finite_decimal(notional, "proposed_notional_usd")
                if notional_dec < Decimal("0.0"):
                    raise DataContractError(f"proposed_notional_usd cannot be negative, got {notional_dec}.")
            # When ineligible or zero-enforced, allocation must be strictly zero
            if data.get("is_eligible") is False or data.get("allocation_zero_enforced") is True:
                if wt is not None and Decimal(str(wt)) != Decimal("0.0"):
                    raise DataContractError("Ineligible strategy or zero-enforced allocation must have proposed_weight == 0.0.")
                if notional is not None and Decimal(str(notional)) != Decimal("0.0"):
                    raise DataContractError("Ineligible strategy or zero-enforced allocation must have proposed_notional_usd == 0.0.")
        return data


class IAllocationPolicy(Protocol):
    """Protocol interface defining solver contracts for future Phase 21 capital allocation."""

    def propose_allocation(
        self,
        strategy: StrategyDefinition,
        candidate_evaluations: Sequence[StrategyRegimeObservation],
        safety_bounds: AllocationSafetyBounds,
        attribution: PerformanceAttributionAssessment,
    ) -> StrategyAllocationProposal:
        """Propose capital weighting under strict safety bounds and attribution constraints."""
        ...
