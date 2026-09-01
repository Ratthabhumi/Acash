"""Phase 9: Canonical Risk Domain Contracts & Configuration (Contract v1.1 Locked).

Strictly enforces:
1. Four-Way Separation of Concerns: Research (8.5) != Allocation (8) != Risk (9) != Execution (7).
2. Sovereign Risk Veto: Risk Rejection => Execution Blocked (Fail-Closed, 0 Orders Transmitted).
3. Zero Direct Broker Transmission: Phase 9 has NO direct broker wire access.
4. Emergency Intent != Positions Flattened: Intent generation specifies target 0; Phase 7 reconciles fills.
5. Finite Decimal precision: All numeric values validated as finite Decimals; reject NaN/Inf/silent-casts.
6. Replay & Staleness defense: RiskEvaluationReport bound to 60s TTL and cryptographic digests.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
import re
from typing import Any, Mapping, Optional, Sequence, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.types import freeze_mapping
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.schema import AuthorizationApproval

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _verify_finite_decimal(
    v: Any,
    context: str = "value",
    allow_negative: bool = False,
    min_val: Optional[Decimal] = None,
    max_val: Optional[Decimal] = None,
) -> Decimal:
    """Strict finite Decimal validation preventing NaN, Infinity, and silent conversion errors."""
    if isinstance(v, Decimal):
        if not v.is_finite():
            raise DataContractError(f"Non-finite Decimal {context} '{v}' encountered.")
        dec = v
    elif isinstance(v, (int, float, str)):
        try:
            dec = Decimal(str(v))
            if not dec.is_finite():
                raise DataContractError(f"Non-finite {context} '{v}' encountered.")
        except (InvalidOperation, OverflowError) as e:
            raise DataContractError(f"Invalid numeric representation for {context} '{v}'.") from e
    else:
        raise DataContractError(f"Unsupported type {type(v)} for Decimal {context}.")

    if not allow_negative and dec < Decimal("0"):
        raise DataContractError(f"{context} cannot be negative, got '{dec}'.")

    if min_val is not None and dec < min_val:
        raise DataContractError(f"{context} '{dec}' is below minimum required '{min_val}'.")

    if max_val is not None and dec > max_val:
        raise DataContractError(f"{context} '{dec}' exceeds maximum permitted '{max_val}'.")

    return dec


def _validate_sha256(v: str, context: str) -> str:
    """Validate strict lowercase 64-hex SHA-256 pattern."""
    if not isinstance(v, str) or not _SHA256_PATTERN.match(v):
        raise DataContractError(
            f"{context} must be a 64-character lowercase hexadecimal SHA-256 digest, got '{v}'."
        )
    return v


def _ensure_utc(dt: Any) -> datetime:
    """Ensure datetime has explicit UTC timezone, parsing ISO formatted strings if provided."""
    if isinstance(dt, str):
        clean_str = dt.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(clean_str)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except Exception as exc:
            raise DataContractError(f"Invalid ISO datetime string '{dt}': {exc}") from exc
    if isinstance(dt, datetime):
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    raise DataContractError(f"Expected datetime or ISO string, got: {type(dt)}")


# ============================================================================
# 1. ENUMERATIONS
# ============================================================================


class RiskVerdict(str, Enum):
    """Authoritative verdict emitted by the Deterministic Risk Engine."""

    APPROVED = "APPROVED"  # 100% of candidate weights clear all sovereign risk gates
    REDUCED = "REDUCED"  # Scaled down monotonically via EXACT_SCALE_DOWN policy
    REJECTED = "REJECTED"  # Failed risk gates; 100% Cash assigned (0 orders)
    KILL_SWITCH_BLOCKED = "KILL_SWITCH_BLOCKED"  # Blocked due to active/tripped kill switch


class DeriskPolicy(str, Enum):
    """Deterministic derisking policies for candidate target allocations."""

    EXACT_SCALE_DOWN = "EXACT_SCALE_DOWN"  # Proportional scale-down preserving cash buffer
    BINARY_REJECT = "BINARY_REJECT"  # Any breach immediately forces REJECTED (100% Cash)


class KillSwitchState(str, Enum):
    """Authoritative state machine states for the Sovereign Kill Switch Controller."""

    ACTIVE = "ACTIVE"  # Normal operations permitted
    TRIPPED = "TRIPPED"  # Hard breach tripped; immediate admission lockout
    PERSISTENTLY_BLOCKED = "PERSISTENTLY_BLOCKED"  # Persisted to disk ledger; survives restarts
    RESET_PENDING = "RESET_PENDING"  # Quorum signatures submitted, awaiting full verification


class EmergencyFlattenStatus(str, Enum):
    """Lifecycle status of an Emergency Flattening Intent."""

    FLATTEN_REQUESTED = "FLATTEN_REQUESTED"  # Zero-target intent emitted by Phase 9
    FLATTEN_COMPLETED = "FLATTEN_COMPLETED"  # Verified zero gross exposure via broker reconciliation
    FLATTEN_FAILED = "FLATTEN_FAILED"  # Execution or reconciliation conflict encountered


# ============================================================================
# 2. RISK POLICY CONFIGURATION CONTRACT
# ============================================================================


class RiskPolicyConfig(BaseModel):
    """Immutable configuration for Sovereign Risk Engine policies."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_version: str = Field(default="v1.0.0", description="Semantic policy version string.")
    derisk_policy: DeriskPolicy = Field(
        default=DeriskPolicy.EXACT_SCALE_DOWN,
        description="Sizing policy applied when candidate breaches leverage/concentration.",
    )
    max_gross_leverage: Decimal = Field(
        default=Decimal("1.00"),
        description="Maximum permitted gross portfolio leverage (sum of risky weights).",
    )
    max_asset_concentration: Decimal = Field(
        default=Decimal("0.25"),
        description="Maximum permitted single-asset weight allocation.",
    )
    min_cash_buffer: Decimal = Field(
        default=Decimal("0.05"),
        description="Mandatory minimum cash buffer floor (1.0 - gross leverage).",
    )
    max_drawdown_limit_pct: Decimal = Field(
        default=Decimal("15.00"),
        description="Maximum peak-to-trough equity drawdown percentage before halt.",
    )
    max_daily_loss_usd: Decimal = Field(
        default=Decimal("10000.00"),
        description="Maximum cumulative daily loss (USD) before automatic kill-switch halt.",
    )
    min_margin_buffer_usd: Decimal = Field(
        default=Decimal("5000.00"),
        description="Minimum free margin buffer (USD) required for new orders.",
    )
    max_market_data_age_ms: int = Field(
        default=1500,
        gt=0,
        description="Maximum allowed telemetry/market data age in milliseconds.",
    )
    max_clock_drift_ms: int = Field(
        default=500,
        gt=0,
        description="Maximum allowed clock drift between system and broker in milliseconds.",
    )
    evaluation_ttl_seconds: int = Field(
        default=60,
        gt=0,
        description="Time-to-live in seconds for RiskEvaluationReport validity.",
    )
    policy_digest: str = Field(
        default="",
        description="Canonical SHA-256 fingerprint of this policy specification.",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_and_compute_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Validate finite Decimals
            max_lev = _verify_finite_decimal(
                data.get("max_gross_leverage", Decimal("1.00")),
                "max_gross_leverage",
                min_val=Decimal("0.0"),
            )
            max_conc = _verify_finite_decimal(
                data.get("max_asset_concentration", Decimal("0.25")),
                "max_asset_concentration",
                min_val=Decimal("0.0"),
                max_val=Decimal("1.0"),
            )
            min_cash = _verify_finite_decimal(
                data.get("min_cash_buffer", Decimal("0.05")),
                "min_cash_buffer",
                min_val=Decimal("0.0"),
                max_val=Decimal("1.0"),
            )
            max_dd = _verify_finite_decimal(
                data.get("max_drawdown_limit_pct", Decimal("15.00")),
                "max_drawdown_limit_pct",
                min_val=Decimal("0.0"),
                max_val=Decimal("100.0"),
            )
            max_loss = _verify_finite_decimal(
                data.get("max_daily_loss_usd", Decimal("10000.00")),
                "max_daily_loss_usd",
                min_val=Decimal("0.0"),
            )
            min_margin = _verify_finite_decimal(
                data.get("min_margin_buffer_usd", Decimal("5000.00")),
                "min_margin_buffer_usd",
                min_val=Decimal("0.0"),
            )

            # Invariant: min_cash_buffer + max_gross_leverage <= 1.0 (with standard unleveraged ceiling)
            if min_cash > Decimal("1.0"):
                raise DataContractError("min_cash_buffer cannot exceed 1.0.")

            raw_policy = data.get("derisk_policy")
            if isinstance(raw_policy, DeriskPolicy):
                derisk_policy_val = raw_policy.value
            elif isinstance(raw_policy, str):
                derisk_policy_val = raw_policy
            else:
                derisk_policy_val = DeriskPolicy.EXACT_SCALE_DOWN.value

            payload = {
                "policy_version": str(data.get("policy_version", "v1.0.0")),
                "derisk_policy": derisk_policy_val,
                "max_gross_leverage": str(max_lev),
                "max_asset_concentration": str(max_conc),
                "min_cash_buffer": str(min_cash),
                "max_drawdown_limit_pct": str(max_dd),
                "max_daily_loss_usd": str(max_loss),
                "min_margin_buffer_usd": str(min_margin),
                "max_market_data_age_ms": int(data.get("max_market_data_age_ms", 1500)),
                "max_clock_drift_ms": int(data.get("max_clock_drift_ms", 500)),
                "evaluation_ttl_seconds": int(data.get("evaluation_ttl_seconds", 60)),
            }
            canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
            computed_digest = hashlib.sha256(canonical_bytes).hexdigest()

            data["max_gross_leverage"] = max_lev
            data["max_asset_concentration"] = max_conc
            data["min_cash_buffer"] = min_cash
            data["max_drawdown_limit_pct"] = max_dd
            data["max_daily_loss_usd"] = max_loss
            data["min_margin_buffer_usd"] = min_margin
            data["policy_digest"] = computed_digest
        return data


# ============================================================================
# 3. CANDIDATE RISK ALLOCATION INPUT CONTRACT
# ============================================================================


class CandidateRiskAllocation(BaseModel):
    """Input allocation DTO wrapping candidate portfolio weights for risk evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    candidate_id: str = Field(description="Unique candidate allocation identifier.")
    strategy_id: str = Field(description="Target strategy or portfolio tournament identifier.")
    weights: Mapping[str, Decimal] = Field(
        description="Proposed asset weights mapping (finite Decimals, >= 0.0)."
    )
    cash_weight: Decimal = Field(description="Proposed cash weight (finite Decimal, >= 0.0).")
    source_decision_digest: str = Field(
        description="SHA-256 digest of upstream Phase 8 AllocationDecision."
    )
    as_of_utc: datetime = Field(description="Strict UTC timestamp of proposal epoch.")
    candidate_digest: str = Field(
        default="", description="Cryptographic SHA-256 fingerprint of candidate allocation."
    )

    @field_validator("weights", mode="after")
    @classmethod
    def validate_and_freeze_weights(cls, v: Mapping[str, Decimal]) -> Mapping[str, Decimal]:
        if not isinstance(v, Mapping):
            raise DataContractError("weights must be a Mapping of symbol to Decimal weight.")
        cleaned: dict[str, Decimal] = {}
        for sym, w in v.items():
            if not isinstance(sym, str) or not sym.strip():
                raise DataContractError(f"Invalid symbol in weights: '{sym}'.")
            dec_w = _verify_finite_decimal(w, f"weights[{sym}]", allow_negative=False)
            cleaned[sym.strip().upper()] = dec_w
        return freeze_mapping(cleaned)

    @model_validator(mode="before")
    @classmethod
    def validate_and_freeze(cls, data: Any) -> Any:
        if isinstance(data, dict):
            _validate_sha256(
                data.get("source_decision_digest", ""), "source_decision_digest"
            )
            raw_weights = data.get("weights", {})
            if not isinstance(raw_weights, Mapping):
                raise DataContractError("weights must be a Mapping of symbol to Decimal weight.")

            cleaned_weights: dict[str, Decimal] = {}
            for sym, w in raw_weights.items():
                if not isinstance(sym, str) or not sym.strip():
                    raise DataContractError(f"Invalid symbol in weights: '{sym}'.")
                dec_w = _verify_finite_decimal(w, f"weights[{sym}]", allow_negative=False)
                cleaned_weights[sym.strip().upper()] = dec_w

            cash_w = _verify_finite_decimal(
                data.get("cash_weight", Decimal("0.0")), "cash_weight", allow_negative=False
            )

            as_of = _ensure_utc(data.get("as_of_utc", datetime.now(timezone.utc)))

            # Sort symbols lexicographically for deterministic digest
            sorted_weights = {k: str(cleaned_weights[k]) for k in sorted(cleaned_weights.keys())}
            payload = {
                "candidate_id": str(data.get("candidate_id", "")),
                "strategy_id": str(data.get("strategy_id", "")),
                "weights": sorted_weights,
                "cash_weight": str(cash_w),
                "source_decision_digest": str(data.get("source_decision_digest", "")),
                "as_of_utc": as_of.isoformat(),
            }
            canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
            candidate_digest = hashlib.sha256(canonical_bytes).hexdigest()

            data["weights"] = freeze_mapping(cleaned_weights)
            data["cash_weight"] = cash_w
            data["as_of_utc"] = as_of
            data["candidate_digest"] = candidate_digest
        return data


# ============================================================================
# 4. RISK EVALUATION REPORT (AUTHORITATIVE OUTPUT CONTRACT)
# ============================================================================


class RiskEvaluationReport(BaseModel):
    """Immutable cryptographic evidence report emitted by the Deterministic Risk Engine.

    Bound by strict 60-second TTL, input lineage digests, and canonical serialization.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    evaluation_id: str = Field(description="Unique deterministic evaluation identifier.")
    verdict: RiskVerdict = Field(description="Deterministic risk evaluation verdict.")
    original_allocation_digest: str = Field(
        description="SHA-256 digest of evaluated candidate allocation."
    )
    portfolio_state_digest: str = Field(
        description="SHA-256 digest of input PortfolioState snapshot."
    )
    account_state_digest: str = Field(
        description="SHA-256 digest of input AccountState snapshot."
    )
    risk_policy_digest: str = Field(
        description="SHA-256 digest of active RiskPolicyConfig."
    )
    adjusted_weights: Mapping[str, Decimal] = Field(
        description="Final approved or derisked asset weights (finite Decimals, >= 0.0)."
    )
    cash_weight: Decimal = Field(
        description="Final authorized cash weight (finite Decimal, >= 0.0)."
    )
    metrics_observed: Mapping[str, Decimal] = Field(
        default_factory=dict,
        description="Key risk metrics observed during evaluation (gross leverage, drawdown, etc.).",
    )
    rejection_reason: Optional[str] = Field(
        default=None,
        description="Structured machine-readable rejection code on failure, None on APPROVED/REDUCED.",
    )
    evaluated_at_utc: datetime = Field(
        description="Strict UTC timestamp when risk evaluation was executed."
    )
    expires_at_utc: datetime = Field(
        description="Strict UTC expiration timestamp (evaluated_at_utc + evaluation_ttl_seconds)."
    )
    report_digest: str = Field(
        default="", description="Canonical SHA-256 cryptographic digest of this report."
    )

    @field_validator("adjusted_weights", mode="after")
    @classmethod
    def validate_and_freeze_adjusted_weights(cls, v: Mapping[str, Decimal]) -> Mapping[str, Decimal]:
        if not isinstance(v, Mapping):
            raise DataContractError("adjusted_weights must be a Mapping of symbol to Decimal weight.")
        cleaned: dict[str, Decimal] = {}
        for sym, w in v.items():
            if not isinstance(sym, str) or not sym.strip():
                raise DataContractError(f"Invalid symbol in adjusted_weights: '{sym}'.")
            dec_w = _verify_finite_decimal(w, f"adjusted_weights[{sym}]", allow_negative=False)
            cleaned[sym.strip().upper()] = dec_w
        return freeze_mapping(cleaned)

    @field_validator("metrics_observed", mode="after")
    @classmethod
    def validate_and_freeze_metrics(cls, v: Mapping[str, Decimal]) -> Mapping[str, Decimal]:
        if not isinstance(v, Mapping):
            return freeze_mapping({})
        cleaned: dict[str, Decimal] = {}
        for k, val in v.items():
            cleaned[str(k)] = _verify_finite_decimal(val, f"metrics_observed[{k}]", allow_negative=True)
        return freeze_mapping(cleaned)

    @model_validator(mode="before")
    @classmethod
    def validate_and_seal_report(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Validate digests
            _validate_sha256(data.get("original_allocation_digest", ""), "original_allocation_digest")
            _validate_sha256(data.get("portfolio_state_digest", ""), "portfolio_state_digest")
            _validate_sha256(data.get("account_state_digest", ""), "account_state_digest")
            _validate_sha256(data.get("risk_policy_digest", ""), "risk_policy_digest")

            # Validate weights
            raw_weights = data.get("adjusted_weights", {})
            if not isinstance(raw_weights, Mapping):
                raise DataContractError("adjusted_weights must be a Mapping of symbol to Decimal weight.")

            cleaned_weights: dict[str, Decimal] = {}
            for sym, w in raw_weights.items():
                if not isinstance(sym, str) or not sym.strip():
                    raise DataContractError(f"Invalid symbol in adjusted_weights: '{sym}'.")
                dec_w = _verify_finite_decimal(w, f"adjusted_weights[{sym}]", allow_negative=False)
                cleaned_weights[sym.strip().upper()] = dec_w

            cash_w = _verify_finite_decimal(
                data.get("cash_weight", Decimal("0.0")), "cash_weight", allow_negative=False
            )

            # Validate timestamps
            eval_at = _ensure_utc(data.get("evaluated_at_utc", datetime.now(timezone.utc)))
            exp_at = _ensure_utc(data.get("expires_at_utc", eval_at))
            if exp_at < eval_at:
                raise DataContractError(
                    f"expires_at_utc ({exp_at.isoformat()}) cannot precede evaluated_at_utc ({eval_at.isoformat()})."
                )

            # Validate metrics
            raw_metrics = data.get("metrics_observed", {})
            cleaned_metrics: dict[str, Decimal] = {}
            if isinstance(raw_metrics, Mapping):
                for k, v in raw_metrics.items():
                    cleaned_metrics[str(k)] = _verify_finite_decimal(v, f"metrics_observed[{k}]", allow_negative=True)

            verdict_val = (
                data["verdict"].value if isinstance(data["verdict"], RiskVerdict) else str(data["verdict"])
            )

            sorted_weights = {k: str(cleaned_weights[k]) for k in sorted(cleaned_weights.keys())}
            sorted_metrics = {k: str(cleaned_metrics[k]) for k in sorted(cleaned_metrics.keys())}

            payload = {
                "evaluation_id": str(data.get("evaluation_id", "")),
                "verdict": verdict_val,
                "original_allocation_digest": str(data.get("original_allocation_digest", "")),
                "portfolio_state_digest": str(data.get("portfolio_state_digest", "")),
                "account_state_digest": str(data.get("account_state_digest", "")),
                "risk_policy_digest": str(data.get("risk_policy_digest", "")),
                "adjusted_weights": sorted_weights,
                "cash_weight": str(cash_w),
                "metrics_observed": sorted_metrics,
                "rejection_reason": data.get("rejection_reason"),
                "evaluated_at_utc": eval_at.isoformat(),
                "expires_at_utc": exp_at.isoformat(),
            }
            canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
            report_digest = hashlib.sha256(canonical_bytes).hexdigest()

            data["adjusted_weights"] = freeze_mapping(cleaned_weights)
            data["cash_weight"] = cash_w
            data["metrics_observed"] = freeze_mapping(cleaned_metrics)
            data["evaluated_at_utc"] = eval_at
            data["expires_at_utc"] = exp_at
            data["report_digest"] = report_digest
        return data

    def is_expired(self, as_of: Optional[datetime] = None) -> bool:
        """Evaluate whether this risk report has expired relative to as_of timestamp."""
        check_time = _ensure_utc(as_of or datetime.now(timezone.utc))
        return check_time >= self.expires_at_utc


# ============================================================================
# 5. KILL SWITCH RESET EVENT CONTRACT
# ============================================================================


class KillSwitchResetEvent(BaseModel):
    """Signed multi-sig reset event authorized to transition PERSISTENTLY_BLOCKED -> ACTIVE.

    Bound to Phase 7 Ed25519TrustStore multi-sig quorum contract.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(description="Unique deterministic reset event identifier.")
    kill_switch_event_id: str = Field(
        description="Target KillSwitchEvent ID being cleared/reset."
    )
    root_cause_summary: str = Field(
        min_length=1, description="Mandatory forensic root-cause analysis summary."
    )
    approvals: Tuple[AuthorizationApproval, ...] = Field(
        min_length=1, description="Signed cryptographic approvals from authorized keys."
    )
    required_approvals: int = Field(
        ge=1, description="Minimum number of verified signatures required for quorum."
    )
    created_at_utc: datetime = Field(description="Strict UTC timestamp of reset proposal.")
    reset_digest: str = Field(
        default="", description="Canonical SHA-256 digest of this reset event payload."
    )

    @model_validator(mode="before")
    @classmethod
    def validate_and_compute_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            created_at = _ensure_utc(data.get("created_at_utc", datetime.now(timezone.utc)))
            approvals = data.get("approvals", ())
            req_approvals = int(data.get("required_approvals", 1))

            if not str(data.get("root_cause_summary", "")).strip():
                raise DataContractError("root_cause_summary must be a non-empty string.")

            if len(approvals) < req_approvals:
                raise DataContractError(
                    f"Provided approvals count ({len(approvals)}) is less than required ({req_approvals})."
                )

            approval_digests = tuple(sorted(a.approval_digest for a in approvals))
            payload = {
                "event_id": str(data.get("event_id", "")),
                "kill_switch_event_id": str(data.get("kill_switch_event_id", "")),
                "root_cause_summary": str(data.get("root_cause_summary", "")).strip(),
                "required_approvals": req_approvals,
                "approval_digests": approval_digests,
                "created_at_utc": created_at.isoformat(),
            }
            canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
            reset_digest = hashlib.sha256(canonical_bytes).hexdigest()

            data["created_at_utc"] = created_at
            data["approvals"] = tuple(approvals)
            data["reset_digest"] = reset_digest
        return data


# ============================================================================
# 6. EMERGENCY FLATTENING INTENT CONTRACT
# ============================================================================


class EmergencyFlattenIntent(BaseModel):
    """Deterministic zero-target liquidation intent emitted by Phase 9.

    Strict Invariant: EmergencyFlattenIntent != Positions Flattened.
    Phase 9 specifies zero-target intent; Phase 7 admits, transmits, and reconciles.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent_id: str = Field(description="Unique deterministic emergency intent identifier.")
    kill_switch_event_id: str = Field(
        description="Associated KillSwitchEvent ID that triggered the liquidation."
    )
    target_positions: Mapping[str, Decimal] = Field(
        description="Target quantities for all active assets (strictly Decimal('0.0')).",
    )
    closing_deltas: Mapping[str, Decimal] = Field(
        description="Required delta orders to close positions (-current_quantity).",
    )
    issued_at_utc: datetime = Field(description="Strict UTC timestamp of intent issuance.")
    status: EmergencyFlattenStatus = Field(
        default=EmergencyFlattenStatus.FLATTEN_REQUESTED,
        description="Current lifecycle status of the emergency liquidation intent.",
    )
    intent_digest: str = Field(
        default="", description="Canonical SHA-256 cryptographic digest of this intent."
    )

    @model_validator(mode="before")
    @classmethod
    def validate_and_compute_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_targets = data.get("target_positions", {})
            if not isinstance(raw_targets, Mapping):
                raise DataContractError("target_positions must be a Mapping of symbol to Decimal.")

            cleaned_targets: dict[str, Decimal] = {}
            for sym, q in raw_targets.items():
                dec_q = _verify_finite_decimal(q, f"target_positions[{sym}]", allow_negative=False)
                if dec_q != Decimal("0.0"):
                    raise DataContractError(
                        f"EmergencyFlattenIntent target for '{sym}' must be exactly 0.0, got '{dec_q}'."
                    )
                cleaned_targets[sym.strip().upper()] = Decimal("0.0")

            raw_deltas = data.get("closing_deltas", {})
            if not isinstance(raw_deltas, Mapping):
                raise DataContractError("closing_deltas must be a Mapping of symbol to Decimal.")

            cleaned_deltas: dict[str, Decimal] = {}
            for sym, d in raw_deltas.items():
                dec_d = _verify_finite_decimal(d, f"closing_deltas[{sym}]", allow_negative=True)
                cleaned_deltas[sym.strip().upper()] = dec_d

            issued_at = _ensure_utc(data.get("issued_at_utc", datetime.now(timezone.utc)))

            sorted_targets = {k: str(cleaned_targets[k]) for k in sorted(cleaned_targets.keys())}
            sorted_deltas = {k: str(cleaned_deltas[k]) for k in sorted(cleaned_deltas.keys())}

            payload = {
                "intent_id": str(data.get("intent_id", "")),
                "kill_switch_event_id": str(data.get("kill_switch_event_id", "")),
                "target_positions": sorted_targets,
                "closing_deltas": sorted_deltas,
                "issued_at_utc": issued_at.isoformat(),
            }
            canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
            intent_digest = hashlib.sha256(canonical_bytes).hexdigest()

            data["target_positions"] = freeze_mapping(cleaned_targets)
            data["closing_deltas"] = freeze_mapping(cleaned_deltas)
            data["issued_at_utc"] = issued_at
            data["intent_digest"] = intent_digest
        return data
