"""Phase 11 Monitoring & Execution Reality Attribution Domain Schemas.

Canonical sovereign data contracts, enums, governance policies, and immutable evidence DTOs
for online strategy drift detection and execution reality attribution.
All identity digests strictly adhere to Tier 1 CanonicalConfigSerializer authority.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from enum import Enum
import hashlib
import re
from typing import Any, Mapping, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer

USD_SCALE = Decimal("0.01")
SHA256_HEX_REGEX = re.compile(r"^[0-9a-f]{64}$")


def _ensure_utc(dt: datetime, field_name: str) -> datetime:
    """Validate that datetime is strictly timezone-aware and in UTC."""
    if dt.tzinfo is None or dt.tzinfo != timezone.utc:
        raise DataContractError(f"{field_name} must be timezone-aware UTC datetime, got {dt}.")
    return dt


def _validate_sha256_digest(digest: str, field_name: str) -> str:
    """Validate that digest is a canonical 64-character lowercase SHA-256 string."""
    if not isinstance(digest, str) or not SHA256_HEX_REGEX.match(digest):
        raise DataContractError(
            f"Invalid SHA-256 digest format for '{field_name}': expected 64-hex lowercase, got '{digest}'."
        )
    return digest


# ============================================================================
# 1. ENUMS
# ============================================================================

class ExecutionSide(str, Enum):
    """Authoritative order side for execution attribution."""

    BUY = "BUY"
    SELL = "SELL"

    @property
    def side_sign(self) -> Decimal:
        """Return directional multiplier for execution drag calculation (+1 for BUY, -1 for SELL)."""
        return Decimal("1.0") if self == ExecutionSide.BUY else Decimal("-1.0")


class ForwardHealthState(str, Enum):
    """Deterministic forward health state classification for active strategies."""

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STRUCTURAL_BREAK = "STRUCTURAL_BREAK"
    MONITORING_BLOCKED = "MONITORING_BLOCKED"


class ForwardGovernanceRecommendation(str, Enum):
    """Advisory recommendation emitted to consuming governance (Phase 10 Stage 2 Census)."""

    CONTINUE_UNRESTRICTED = "CONTINUE_UNRESTRICTED"
    DEGRADED_PROBATION = "DEGRADED_PROBATION"
    RECOMMEND_EXCLUSION = "RECOMMEND_EXCLUSION"
    RECOMMEND_RETIREMENT = "RECOMMEND_RETIREMENT"
    MONITORING_BLOCKED_FLAG = "MONITORING_BLOCKED_FLAG"


# ============================================================================
# 2. TRACK A: FORWARD OBSERVATION & POLICIES
# ============================================================================

class ForwardObservation(BaseModel):
    """Immutable single-period forward performance observation for an active strategy.

    Lineage Invariant:
    - dossier_digest is an immutable reference to historical Phase 8.5 AlphaQualificationDossier.
    - observation_sequence is strictly monotonic per strategy.
    - observation_digest is computed via Tier 1 CanonicalConfigSerializer over all fields excluding itself.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    observation_id: str
    strategy_id: str
    dossier_digest: str
    as_of_utc: datetime
    wall_clock_utc: datetime

    realized_return: Decimal
    expected_return: Optional[Decimal] = None
    benchmark_return: Decimal = Decimal("0.0")
    gross_pnl_usd: Decimal
    net_pnl_usd: Decimal
    turnover_ratio: Decimal

    observation_sequence: int
    is_telemetry_valid: bool = True
    observation_digest: str = ""

    @model_validator(mode="before")
    @classmethod
    def _validate_and_compute_digest(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Validate timestamps
        as_of = data.get("as_of_utc")
        if isinstance(as_of, datetime):
            _ensure_utc(as_of, "as_of_utc")
        wall_clock = data.get("wall_clock_utc")
        if isinstance(wall_clock, datetime):
            _ensure_utc(wall_clock, "wall_clock_utc")

        # Validate sequence
        seq = data.get("observation_sequence")
        if seq is not None and int(seq) < 0:
            raise DataContractError(f"observation_sequence must be non-negative, got {seq}.")

        # Validate turnover
        turnover = data.get("turnover_ratio")
        if turnover is not None:
            t_dec = Decimal(str(turnover))
            if t_dec < Decimal("0.0") or t_dec > Decimal("2.0"):
                raise DataContractError(f"turnover_ratio must be in [0.0, 2.0], got {t_dec}.")

        # Validate realized_return domain invariant: simple discrete period return must be strictly > -1.0
        r_ret = data.get("realized_return")
        if r_ret is not None:
            r_dec = Decimal(str(r_ret))
            if r_dec <= Decimal("-1.0"):
                raise DataContractError(
                    f"Domain invariant violated: simple discrete realized_return ({r_dec}) must be strictly > -1.0. "
                    "Return <= -1.0 collapses equity to zero or negative values."
                )

        # Validate historical dossier digest reference format
        dossier_d = data.get("dossier_digest")
        if dossier_d is not None:
            _validate_sha256_digest(str(dossier_d), "dossier_digest")

        # Non-self-referential canonical digest construction
        supplied_digest = data.get("observation_digest")
        computed_digest = cls._compute_observation_digest_from_dict(data)

        if supplied_digest:
            _validate_sha256_digest(supplied_digest, "observation_digest")
            if supplied_digest != computed_digest:
                raise DataContractError(
                    f"Observation digest tampering detected: supplied {supplied_digest} != computed {computed_digest}."
                )
        else:
            data["observation_digest"] = computed_digest

        return data

    @classmethod
    def _compute_observation_digest_from_dict(cls, data: Mapping[str, Any]) -> str:
        """Compute authoritative Tier 1 digest of payload excluding observation_digest."""
        payload = {
            "observation_id": str(data.get("observation_id", "")),
            "strategy_id": str(data.get("strategy_id", "")),
            "dossier_digest": str(data.get("dossier_digest", "")),
            "as_of_utc": (
                data["as_of_utc"].isoformat()
                if isinstance(data.get("as_of_utc"), datetime)
                else str(data.get("as_of_utc", ""))
            ),
            "wall_clock_utc": (
                data["wall_clock_utc"].isoformat()
                if isinstance(data.get("wall_clock_utc"), datetime)
                else str(data.get("wall_clock_utc", ""))
            ),
            "realized_return": str(data.get("realized_return", "0.0")),
            "expected_return": (
                str(data.get("expected_return")) if data.get("expected_return") is not None else None
            ),
            "benchmark_return": str(data.get("benchmark_return", "0.0")),
            "gross_pnl_usd": str(data.get("gross_pnl_usd", "0.0")),
            "net_pnl_usd": str(data.get("net_pnl_usd", "0.0")),
            "turnover_ratio": str(data.get("turnover_ratio", "0.0")),
            "observation_sequence": int(data.get("observation_sequence", 0)),
            "is_telemetry_valid": bool(data.get("is_telemetry_valid", True)),
        }
        return CanonicalConfigSerializer.compute_sha256(payload)


class ForwardHealthPolicy(BaseModel):
    """Configurable forward governance policy enforcing asymmetric anti-whipsaw hysteresis."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    min_observations: int = 30
    rolling_window_size: int = 60
    degradation_persistence_n: int = 3
    recovery_persistence_m: int = 10
    recovery_cooldown_periods: int = 5
    min_acceptable_sharpe: Decimal = Decimal("0.50")
    max_sharpe_decay_pct: Decimal = Decimal("0.50")
    critical_drawdown_limit: Decimal = Decimal("0.20")
    critical_cumulative_loss_bps: Decimal = Decimal("2500")
    policy_digest: str = ""

    @model_validator(mode="before")
    @classmethod
    def _validate_and_compute_policy_digest(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        min_obs = int(data.get("min_observations", 30))
        win_size = int(data.get("rolling_window_size", 60))
        if min_obs <= 0 or win_size < min_obs:
            raise DataContractError(
                f"Invalid observation window: min_observations ({min_obs}) must be > 0 and <= rolling_window_size ({win_size})."
            )

        n_deg = int(data.get("degradation_persistence_n", 3))
        m_rec = int(data.get("recovery_persistence_m", 10))
        if n_deg <= 0 or m_rec <= n_deg:
            raise DataContractError(
                f"Asymmetric hysteresis invariant violated: recovery_persistence_m ({m_rec}) must strictly exceed degradation_persistence_n ({n_deg})."
            )

        cooldown = int(data.get("recovery_cooldown_periods", 5))
        if cooldown < 0:
            raise DataContractError(f"recovery_cooldown_periods must be non-negative, got {cooldown}.")

        dd_limit = Decimal(str(data.get("critical_drawdown_limit", "0.20")))
        if dd_limit <= Decimal("0.0") or dd_limit > Decimal("1.0"):
            raise DataContractError(f"critical_drawdown_limit must be in (0.0, 1.0], got {dd_limit}.")

        # Compute Tier 1 policy digest excluding policy_digest field
        payload = {
            "min_observations": min_obs,
            "rolling_window_size": win_size,
            "degradation_persistence_n": n_deg,
            "recovery_persistence_m": m_rec,
            "recovery_cooldown_periods": cooldown,
            "min_acceptable_sharpe": str(data.get("min_acceptable_sharpe", "0.50")),
            "max_sharpe_decay_pct": str(data.get("max_sharpe_decay_pct", "0.50")),
            "critical_drawdown_limit": str(dd_limit),
            "critical_cumulative_loss_bps": str(data.get("critical_cumulative_loss_bps", "2500")),
        }
        computed_digest = CanonicalConfigSerializer.compute_sha256(payload)

        supplied_digest = data.get("policy_digest")
        if supplied_digest:
            _validate_sha256_digest(supplied_digest, "policy_digest")
            if supplied_digest != computed_digest:
                raise DataContractError(
                    f"Policy digest mismatch: supplied {supplied_digest} != computed {computed_digest}."
                )
        else:
            data["policy_digest"] = computed_digest

        return data


class ForwardWindowMetrics(BaseModel):
    """Deterministically calculated rolling window econometric metrics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    window_size: int
    observation_count: int

    mean_realized_return_annualized: Decimal
    realized_volatility_annualized: Decimal
    realized_sharpe_ratio: Decimal
    max_drawdown: Decimal
    inception_max_drawdown: Decimal
    hit_rate: Decimal

    # Statistical Decay Estimators
    tracking_error_annualized: Optional[Decimal] = None
    t_stat_decay: Decimal
    expected_vs_realized_divergence_bps: Optional[Decimal] = None
    information_coefficient: Optional[Decimal] = None
    ic_decay_slope: Optional[Decimal] = None


class StrategyForwardDriftEvidence(BaseModel):
    """Forensic evidence document containing forward health status and governance recommendations.

    Strict Invariants:
    - Contains advisory recommendation for consuming governance (Phase 10 Stage 2 Census).
    - STRICTLY ZERO is_tournament_eligible attribute.
    - Tier 1 evidence_digest over non-self-referential payload.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str
    strategy_id: str
    dossier_digest: str
    as_of_utc: datetime
    wall_clock_utc: datetime

    health_state: ForwardHealthState
    recommendation: ForwardGovernanceRecommendation
    metrics: ForwardWindowMetrics
    policy_digest: str

    consecutive_degraded_periods: int
    consecutive_recovery_periods: int
    drift_flags: Tuple[str, ...]

    evidence_digest: str = ""

    @model_validator(mode="before")
    @classmethod
    def _validate_and_compute_evidence_digest(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Validate timestamps
        as_of = data.get("as_of_utc")
        if isinstance(as_of, datetime):
            _ensure_utc(as_of, "as_of_utc")
        wall_clock = data.get("wall_clock_utc")
        if isinstance(wall_clock, datetime):
            _ensure_utc(wall_clock, "wall_clock_utc")

        # Validate digests
        _validate_sha256_digest(str(data.get("dossier_digest", "")), "dossier_digest")
        _validate_sha256_digest(str(data.get("policy_digest", "")), "policy_digest")

        # Invariant enforcement: forbid authority creep
        if "is_tournament_eligible" in data:
            raise DataContractError(
                "AUTHORITY_CREEP_DETECTED: StrategyForwardDriftEvidence is strictly forbidden "
                "from defining 'is_tournament_eligible'. Tournament eligibility belongs to Phase 10 Census."
            )

        computed_digest = cls._compute_evidence_digest_from_dict(data)
        supplied_digest = data.get("evidence_digest")
        if supplied_digest:
            _validate_sha256_digest(supplied_digest, "evidence_digest")
            if supplied_digest != computed_digest:
                raise DataContractError(
                    f"Evidence digest tampering detected: supplied {supplied_digest} != computed {computed_digest}."
                )
        else:
            data["evidence_digest"] = computed_digest

        return data

    @classmethod
    def _compute_evidence_digest_from_dict(cls, data: Mapping[str, Any]) -> str:
        """Compute authoritative Tier 1 digest of payload excluding evidence_digest."""
        metrics_obj = data.get("metrics")
        metrics_dict: dict[str, Any] = {}
        if isinstance(metrics_obj, ForwardWindowMetrics):
            metrics_dict = {
                "window_size": metrics_obj.window_size,
                "observation_count": metrics_obj.observation_count,
                "mean_realized_return_annualized": str(metrics_obj.mean_realized_return_annualized),
                "realized_volatility_annualized": str(metrics_obj.realized_volatility_annualized),
                "realized_sharpe_ratio": str(metrics_obj.realized_sharpe_ratio),
                "max_drawdown": str(metrics_obj.max_drawdown),
                "inception_max_drawdown": str(metrics_obj.inception_max_drawdown),
                "hit_rate": str(metrics_obj.hit_rate),
                "tracking_error_annualized": (
                    str(metrics_obj.tracking_error_annualized)
                    if metrics_obj.tracking_error_annualized is not None
                    else None
                ),
                "t_stat_decay": str(metrics_obj.t_stat_decay),
                "expected_vs_realized_divergence_bps": (
                    str(metrics_obj.expected_vs_realized_divergence_bps)
                    if metrics_obj.expected_vs_realized_divergence_bps is not None
                    else None
                ),
                "information_coefficient": (
                    str(metrics_obj.information_coefficient)
                    if metrics_obj.information_coefficient is not None
                    else None
                ),
                "ic_decay_slope": (
                    str(metrics_obj.ic_decay_slope) if metrics_obj.ic_decay_slope is not None else None
                ),
            }
        elif isinstance(metrics_obj, dict):
            metrics_dict = {
                k: str(v) if isinstance(v, Decimal) else v
                for k, v in metrics_obj.items()
            }

        payload = {
            "evidence_id": str(data.get("evidence_id", "")),
            "strategy_id": str(data.get("strategy_id", "")),
            "dossier_digest": str(data.get("dossier_digest", "")),
            "as_of_utc": (
                data["as_of_utc"].isoformat()
                if isinstance(data.get("as_of_utc"), datetime)
                else str(data.get("as_of_utc", ""))
            ),
            "wall_clock_utc": (
                data["wall_clock_utc"].isoformat()
                if isinstance(data.get("wall_clock_utc"), datetime)
                else str(data.get("wall_clock_utc", ""))
            ),
            "health_state": (
                data["health_state"].value
                if isinstance(data.get("health_state"), ForwardHealthState)
                else str(data.get("health_state", ""))
            ),
            "recommendation": (
                data["recommendation"].value
                if isinstance(data.get("recommendation"), ForwardGovernanceRecommendation)
                else str(data.get("recommendation", ""))
            ),
            "metrics": metrics_dict,
            "policy_digest": str(data.get("policy_digest", "")),
            "consecutive_degraded_periods": int(data.get("consecutive_degraded_periods", 0)),
            "consecutive_recovery_periods": int(data.get("consecutive_recovery_periods", 0)),
            "drift_flags": list(data.get("drift_flags", ())),
        }
        return CanonicalConfigSerializer.compute_sha256(payload)


# ============================================================================
# 3. TRACK B: EXECUTION REALITY ATTRIBUTION & POLICIES
# ============================================================================

class ExecutionObservation(BaseModel):
    """Normalized atomic fill observation with discrete price milestones ingested from Phase 7.

    Strict Invariants:
    - All price milestones > Decimal('0.0').
    - arrival_bid_price <= arrival_ask_price.
    - Option A Canonical Midpoint: arrival_mid_price == (arrival_bid_price + arrival_ask_price) / 2.
    - decision_timestamp_utc <= arrival_timestamp_utc <= fill_timestamp_utc.
    - Notional value conservation: quantize(filled_quantity * executed_fill_price, 0.01) == quantize(filled_notional_usd, 0.01).
    - execution_digest is non-self-referential Tier 1 SHA-256 digest.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    observation_id: str
    execution_id: str
    intent_id: str
    strategy_id: str
    venue: str
    symbol: str
    side: ExecutionSide

    # Quantities & Notional Value
    requested_quantity: Decimal
    filled_quantity: Decimal
    filled_notional_usd: Decimal

    # Price Milestones & Option A Canonical Midpoint
    decision_mid_price: Decimal
    arrival_bid_price: Decimal
    arrival_ask_price: Decimal
    arrival_mid_price: Decimal
    executed_fill_price: Decimal

    # Monetary Frictions
    commission_fee_usd: Decimal
    rebate_usd: Decimal

    # Discrete Timestamps
    decision_timestamp_utc: datetime
    arrival_timestamp_utc: datetime
    fill_timestamp_utc: datetime

    network_latency_ms: Optional[float] = None
    is_partial_fill: bool = False
    execution_digest: str = ""

    @model_validator(mode="before")
    @classmethod
    def _validate_and_compute_digest(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Validate side
        side_val = data.get("side")
        if isinstance(side_val, str):
            try:
                data["side"] = ExecutionSide(side_val)
            except ValueError:
                raise DataContractError(f"Invalid ExecutionSide '{side_val}': must be 'BUY' or 'SELL'.")

        # Validate timestamps and temporal ordering
        d_ts = _ensure_utc(data["decision_timestamp_utc"], "decision_timestamp_utc")
        a_ts = _ensure_utc(data["arrival_timestamp_utc"], "arrival_timestamp_utc")
        f_ts = _ensure_utc(data["fill_timestamp_utc"], "fill_timestamp_utc")
        if not (d_ts <= a_ts <= f_ts):
            raise DataContractError(
                f"Temporal ordering violation: decision ({d_ts.isoformat()}) <= arrival ({a_ts.isoformat()}) <= fill ({f_ts.isoformat()}) failed."
            )

        # Validate positive quantities and notional
        req_q = Decimal(str(data["requested_quantity"]))
        fill_q = Decimal(str(data["filled_quantity"]))
        fill_notional = Decimal(str(data["filled_notional_usd"]))
        if req_q <= Decimal("0.0"):
            raise DataContractError(f"requested_quantity must be positive, got {req_q}.")
        if fill_q <= Decimal("0.0") or fill_q > req_q:
            raise DataContractError(f"filled_quantity must be positive and <= requested_quantity ({req_q}), got {fill_q}.")
        if fill_notional <= Decimal("0.0"):
            raise DataContractError(f"filled_notional_usd must be positive, got {fill_notional}.")

        # Validate positive prices
        dec_mid = Decimal(str(data["decision_mid_price"]))
        arr_bid = Decimal(str(data["arrival_bid_price"]))
        arr_ask = Decimal(str(data["arrival_ask_price"]))
        arr_mid = Decimal(str(data["arrival_mid_price"]))
        fill_px = Decimal(str(data["executed_fill_price"]))

        for px_name, px_val in [
            ("decision_mid_price", dec_mid),
            ("arrival_bid_price", arr_bid),
            ("arrival_ask_price", arr_ask),
            ("arrival_mid_price", arr_mid),
            ("executed_fill_price", fill_px),
        ]:
            if px_val <= Decimal("0.0"):
                raise DataContractError(f"{px_name} must be strictly positive, got {px_val}.")

        # Validate spread non-inversion
        if arr_bid > arr_ask:
            raise DataContractError(f"Inverted spread: arrival_bid_price ({arr_bid}) > arrival_ask_price ({arr_ask}).")

        # Validate Option A: Canonical Midpoint Invariance
        expected_mid = (arr_bid + arr_ask) / Decimal("2.0")
        if arr_mid != expected_mid:
            raise DataContractError(
                f"Option A Canonical Midpoint violated: arrival_mid_price ({arr_mid}) != (bid + ask)/2 ({expected_mid})."
            )

        # Validate fees and rebates
        comm = Decimal(str(data["commission_fee_usd"]))
        reb = Decimal(str(data["rebate_usd"]))
        if comm < Decimal("0.0"):
            raise DataContractError(f"commission_fee_usd must be non-negative, got {comm}.")
        if reb < Decimal("0.0"):
            raise DataContractError(f"rebate_usd must be non-negative, got {reb}.")

        # Validate Notional Conservation with Canonical Decimal Quantization
        expected_notional = (fill_q * fill_px).quantize(USD_SCALE, rounding=ROUND_HALF_EVEN)
        actual_notional = fill_notional.quantize(USD_SCALE, rounding=ROUND_HALF_EVEN)
        if expected_notional != actual_notional:
            raise DataContractError(
                f"Notional conservation violated: quantize(qty * fill_px)={expected_notional} != quantize(filled_notional_usd)={actual_notional}."
            )

        # Canonical Tier 1 non-self-referential execution digest
        computed_digest = cls._compute_execution_digest_from_dict(data)
        supplied_digest = data.get("execution_digest")
        if supplied_digest:
            _validate_sha256_digest(supplied_digest, "execution_digest")
            if supplied_digest != computed_digest:
                raise DataContractError(
                    f"Execution digest tampering detected: supplied {supplied_digest} != computed {computed_digest}."
                )
        else:
            data["execution_digest"] = computed_digest

        return data

    @classmethod
    def _compute_execution_digest_from_dict(cls, data: Mapping[str, Any]) -> str:
        """Compute authoritative Tier 1 digest of payload excluding execution_digest."""
        side_val = data.get("side")
        side_str = side_val.value if isinstance(side_val, ExecutionSide) else str(side_val)

        payload = {
            "observation_id": str(data.get("observation_id", "")),
            "execution_id": str(data.get("execution_id", "")),
            "intent_id": str(data.get("intent_id", "")),
            "strategy_id": str(data.get("strategy_id", "")),
            "venue": str(data.get("venue", "")),
            "symbol": str(data.get("symbol", "")),
            "side": side_str,
            "requested_quantity": str(data.get("requested_quantity", "0.0")),
            "filled_quantity": str(data.get("filled_quantity", "0.0")),
            "filled_notional_usd": str(data.get("filled_notional_usd", "0.0")),
            "decision_mid_price": str(data.get("decision_mid_price", "0.0")),
            "arrival_bid_price": str(data.get("arrival_bid_price", "0.0")),
            "arrival_ask_price": str(data.get("arrival_ask_price", "0.0")),
            "arrival_mid_price": str(data.get("arrival_mid_price", "0.0")),
            "executed_fill_price": str(data.get("executed_fill_price", "0.0")),
            "commission_fee_usd": str(data.get("commission_fee_usd", "0.0")),
            "rebate_usd": str(data.get("rebate_usd", "0.0")),
            "decision_timestamp_utc": (
                data["decision_timestamp_utc"].isoformat()
                if isinstance(data.get("decision_timestamp_utc"), datetime)
                else str(data.get("decision_timestamp_utc", ""))
            ),
            "arrival_timestamp_utc": (
                data["arrival_timestamp_utc"].isoformat()
                if isinstance(data.get("arrival_timestamp_utc"), datetime)
                else str(data.get("arrival_timestamp_utc", ""))
            ),
            "fill_timestamp_utc": (
                data["fill_timestamp_utc"].isoformat()
                if isinstance(data.get("fill_timestamp_utc"), datetime)
                else str(data.get("fill_timestamp_utc", ""))
            ),
            "network_latency_ms": data.get("network_latency_ms"),
            "is_partial_fill": bool(data.get("is_partial_fill", False)),
        }
        return CanonicalConfigSerializer.compute_sha256(payload)


class RealizedExecutionDrag(BaseModel):
    """Decomposed basis point drag attributed to discrete execution friction components.

    Policy Statement:
    - The components are attribution categories under the declared benchmark convention.
    - They are not required to algebraically reconcile to a single decision-to-fill implementation
      shortfall because categories use distinct benchmark denominators.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    observation_id: str
    symbol: str

    spread_drag_bps: Decimal
    timing_drag_bps: Decimal
    slippage_drag_bps: Decimal
    commission_fee_bps: Decimal
    rebate_benefit_bps: Decimal

    gross_execution_drag_bps: Decimal
    net_realized_execution_cost_bps: Decimal
    expected_vs_realized_drag_bps: Decimal


class ExecutionAttributionPolicy(BaseModel):
    """Configurable governance policy defining sample reliability thresholds for execution friction."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sample_window_days: int = 30
    min_reliable_sample_count: int = 100
    min_reliable_coverage_ratio: Decimal = Decimal("0.95")
    critical_fail_closed_coverage_ratio: Decimal = Decimal("0.80")
    tail_percentile: Decimal = Decimal("0.95")
    policy_digest: str = ""

    @model_validator(mode="before")
    @classmethod
    def _validate_and_compute_policy_digest(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        window_days = int(data.get("sample_window_days", 30))
        min_samples = int(data.get("min_reliable_sample_count", 100))
        if window_days <= 0 or min_samples <= 0:
            raise DataContractError("sample_window_days and min_reliable_sample_count must be positive.")

        rel_cov = Decimal(str(data.get("min_reliable_coverage_ratio", "0.95")))
        crit_cov = Decimal(str(data.get("critical_fail_closed_coverage_ratio", "0.80")))
        if crit_cov >= rel_cov or crit_cov <= Decimal("0.0") or rel_cov > Decimal("1.0"):
            raise DataContractError(
                f"Coverage ratio policy invalid: 0 < critical ({crit_cov}) < reliable ({rel_cov}) <= 1.0 required."
            )

        payload = {
            "sample_window_days": window_days,
            "min_reliable_sample_count": min_samples,
            "min_reliable_coverage_ratio": str(rel_cov),
            "critical_fail_closed_coverage_ratio": str(crit_cov),
            "tail_percentile": str(data.get("tail_percentile", "0.95")),
        }
        computed_digest = CanonicalConfigSerializer.compute_sha256(payload)

        supplied_digest = data.get("policy_digest")
        if supplied_digest:
            _validate_sha256_digest(supplied_digest, "policy_digest")
            if supplied_digest != computed_digest:
                raise DataContractError(
                    f"Execution policy digest mismatch: supplied {supplied_digest} != computed {computed_digest}."
                )
        else:
            data["policy_digest"] = computed_digest

        return data


class ExecutionCostEvidence(BaseModel):
    """Aggregated empirical execution cost evidence with statistical uncertainty metadata.

    Strict Invariants:
    - Provides empirical basis points to Phase 8 portfolio optimizers via configuration loaders.
    - Zero write authority into Phase 8 code.
    - Single authoritative Tier 1 lineage digest.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str
    venue: str
    symbol: str
    as_of_utc: datetime
    coverage_start_utc: datetime
    coverage_end_utc: datetime

    fill_count: int
    effective_sample_count: int
    coverage_ratio: Decimal

    mean_gross_drag_bps: Decimal
    mean_net_cost_bps: Decimal
    median_net_cost_bps: Decimal
    p95_gross_drag_bps: Decimal
    standard_error_bps: Decimal
    confidence_interval_95_half_width_bps: Decimal
    is_statistically_reliable: bool

    policy_digest: str
    lineage_digest: str = ""

    @model_validator(mode="before")
    @classmethod
    def _validate_and_compute_lineage_digest(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        as_of = _ensure_utc(data["as_of_utc"], "as_of_utc")
        cov_start = _ensure_utc(data["coverage_start_utc"], "coverage_start_utc")
        cov_end = _ensure_utc(data["coverage_end_utc"], "coverage_end_utc")
        if cov_start > cov_end:
            raise DataContractError(f"coverage_start_utc ({cov_start}) cannot exceed coverage_end_utc ({cov_end}).")

        fill_count = int(data.get("fill_count", 0))
        if fill_count < 0:
            raise DataContractError(f"fill_count must be non-negative, got {fill_count}.")

        _validate_sha256_digest(str(data.get("policy_digest", "")), "policy_digest")

        computed_digest = cls._compute_lineage_digest_from_dict(data)
        supplied_digest = data.get("lineage_digest")
        if supplied_digest:
            _validate_sha256_digest(supplied_digest, "lineage_digest")
            if supplied_digest != computed_digest:
                raise DataContractError(
                    f"Lineage digest mismatch: supplied {supplied_digest} != computed {computed_digest}."
                )
        else:
            data["lineage_digest"] = computed_digest

        return data

    @classmethod
    def _compute_lineage_digest_from_dict(cls, data: Mapping[str, Any]) -> str:
        """Compute authoritative Tier 1 digest of payload excluding lineage_digest."""
        payload = {
            "evidence_id": str(data.get("evidence_id", "")),
            "venue": str(data.get("venue", "")),
            "symbol": str(data.get("symbol", "")),
            "as_of_utc": (
                data["as_of_utc"].isoformat()
                if isinstance(data.get("as_of_utc"), datetime)
                else str(data.get("as_of_utc", ""))
            ),
            "coverage_start_utc": (
                data["coverage_start_utc"].isoformat()
                if isinstance(data.get("coverage_start_utc"), datetime)
                else str(data.get("coverage_start_utc", ""))
            ),
            "coverage_end_utc": (
                data["coverage_end_utc"].isoformat()
                if isinstance(data.get("coverage_end_utc"), datetime)
                else str(data.get("coverage_end_utc", ""))
            ),
            "fill_count": int(data.get("fill_count", 0)),
            "effective_sample_count": int(data.get("effective_sample_count", 0)),
            "coverage_ratio": str(data.get("coverage_ratio", "0.0")),
            "mean_gross_drag_bps": str(data.get("mean_gross_drag_bps", "0.0")),
            "mean_net_cost_bps": str(data.get("mean_net_cost_bps", "0.0")),
            "median_net_cost_bps": str(data.get("median_net_cost_bps", "0.0")),
            "p95_gross_drag_bps": str(data.get("p95_gross_drag_bps", "0.0")),
            "standard_error_bps": str(data.get("standard_error_bps", "0.0")),
            "confidence_interval_95_half_width_bps": str(data.get("confidence_interval_95_half_width_bps", "0.0")),
            "is_statistically_reliable": bool(data.get("is_statistically_reliable", False)),
            "policy_digest": str(data.get("policy_digest", "")),
        }
        return CanonicalConfigSerializer.compute_sha256(payload)
