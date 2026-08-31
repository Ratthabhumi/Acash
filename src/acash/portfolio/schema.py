"""Canonical domain models, DTOs, and cryptographic lineage for Phase 8 Portfolio Engine.

Strictly enforces:
- Immutable (frozen) models.
- Decimal precision for financial numerics.
- Lexicographically sorted unique symbol ordering.
- Cryptographic SHA-256 digests on all domain entities.
- Fail-closed error boundaries (zero magic floors / fallbacks).
"""

from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any, Final, Mapping, Optional, Sequence, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import (
    DataContractError,
    DomainValidationError,
)


# Centralized Canonical Numerical Tolerances
EPSILON_PSD: Final[float] = 1e-10
EPSILON_WEIGHT_SUM: Final[Decimal] = Decimal("1e-6")
EPSILON_RANK_TIE: Final[Decimal] = Decimal("1e-8")


def _sha256_hexdigest(data: Any) -> str:
    """Deterministic SHA-256 digest calculation over canonical JSON payload."""
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class PortfolioUniverse(BaseModel):
    """Authoritative definition of candidate tradable instruments for an allocation epoch."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    universe_id: str
    assets: tuple[str, ...]
    as_of: datetime
    universe_digest: str = ""

    @model_validator(mode="before")
    @classmethod
    def validate_and_compute_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_assets = data.get("assets", ())
            if not raw_assets:
                raise DataContractError("PortfolioUniverse must contain at least one asset.")
            
            cleaned_assets = []
            seen = set()
            for s in raw_assets:
                if not isinstance(s, str) or not s.strip():
                    raise DomainValidationError(f"Invalid symbol in assets: {s}")
                sym = s.strip().upper()
                if sym in seen:
                    raise DataContractError(f"Duplicate symbol detected in universe: {sym}")
                seen.add(sym)
                cleaned_assets.append(sym)
            
            sorted_assets = tuple(sorted(cleaned_assets))
            data["assets"] = sorted_assets

            as_of_val = data.get("as_of")
            as_of_str = as_of_val.isoformat() if isinstance(as_of_val, datetime) else str(as_of_val)
            
            payload = {
                "universe_id": data.get("universe_id"),
                "assets": list(sorted_assets),
                "as_of": as_of_str,
            }
            data["universe_digest"] = _sha256_hexdigest(payload)
        return data


class AssetReturnPanel(BaseModel):
    """Immutable observation matrix of historical asset period returns (T x N)."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    universe_id: str
    timestamps: tuple[datetime, ...]
    symbols: tuple[str, ...]
    returns_matrix: tuple[tuple[Decimal, ...], ...]
    frequency: str = "1D"
    panel_digest: str = ""

    @property
    def T(self) -> int:
        return len(self.timestamps)

    @property
    def N(self) -> int:
        return len(self.symbols)

    @model_validator(mode="before")
    @classmethod
    def validate_panel_and_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            timestamps = tuple(data.get("timestamps", ()))
            symbols = tuple(data.get("symbols", ()))
            returns_matrix = data.get("returns_matrix", ())

            t_len = len(timestamps)
            n_len = len(symbols)

            if t_len < 1:
                raise DataContractError("AssetReturnPanel must contain at least 1 timestamp.")
            if n_len < 1:
                raise DataContractError("AssetReturnPanel must contain at least 1 symbol.")
            if len(returns_matrix) != t_len:
                raise DataContractError(
                    f"Return matrix row count ({len(returns_matrix)}) does not match timestamp count ({t_len})."
                )

            cleaned_matrix = []
            for r_idx, row in enumerate(returns_matrix):
                if len(row) != n_len:
                    raise DataContractError(
                        f"Return row {r_idx} column count ({len(row)}) does not match symbol count ({n_len})."
                    )
                cleaned_row = []
                for c_idx, val in enumerate(row):
                    if not isinstance(val, Decimal):
                        try:
                            val = Decimal(str(val))
                        except Exception as e:
                            raise DomainValidationError(f"Invalid decimal at [{r_idx}, {c_idx}]: {val}") from e
                    if not val.is_finite():
                        raise DomainValidationError(f"Return value at [{r_idx}, {c_idx}] must be a finite Decimal, got: {val}")
                    cleaned_row.append(val)
                cleaned_matrix.append(tuple(cleaned_row))

            data["returns_matrix"] = tuple(cleaned_matrix)
            data["timestamps"] = timestamps
            data["symbols"] = symbols

            payload = {
                "universe_id": data.get("universe_id"),
                "timestamps": [t.isoformat() if isinstance(t, datetime) else str(t) for t in timestamps],
                "symbols": list(symbols),
                "returns_matrix": [[str(v) for v in row] for row in cleaned_matrix],
                "frequency": data.get("frequency", "1D"),
            }
            data["panel_digest"] = _sha256_hexdigest(payload)
        return data


class PortfolioConstraints(BaseModel):
    """Explicit mathematical boundaries defining the feasible allocation space."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    min_weight: Decimal = Decimal("0.0")
    max_weight: Decimal = Decimal("1.0")
    max_gross_leverage: Decimal = Decimal("1.0")
    min_cash_buffer: Decimal = Decimal("0.05")
    max_turnover_per_rebalance: Optional[Decimal] = None
    constraints_digest: str = ""

    @model_validator(mode="before")
    @classmethod
    def populate_constraints_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            payload = {
                "min_weight": str(data.get("min_weight", "0.0")),
                "max_weight": str(data.get("max_weight", "1.0")),
                "max_gross_leverage": str(data.get("max_gross_leverage", "1.0")),
                "min_cash_buffer": str(data.get("min_cash_buffer", "0.05")),
                "max_turnover_per_rebalance": str(data.get("max_turnover_per_rebalance", "")) if data.get("max_turnover_per_rebalance") is not None else "",
            }
            data["constraints_digest"] = _sha256_hexdigest(payload)
        return data

    @model_validator(mode="after")
    def validate_constraint_invariants(self) -> "PortfolioConstraints":
        if self.min_weight < Decimal("0.0"):
            raise DomainValidationError(f"min_weight cannot be negative, got {self.min_weight}")
        if self.max_weight > Decimal("1.0"):
            raise DomainValidationError(f"max_weight cannot exceed 1.0, got {self.max_weight}")
        if self.min_weight > self.max_weight:
            raise DomainValidationError(
                f"min_weight ({self.min_weight}) cannot exceed max_weight ({self.max_weight})"
            )
        if self.max_gross_leverage <= Decimal("0.0"):
            raise DomainValidationError("max_gross_leverage must be strictly positive")
        if not (Decimal("0.0") <= self.min_cash_buffer <= Decimal("1.0")):
            raise DomainValidationError(f"min_cash_buffer must be in [0.0, 1.0], got {self.min_cash_buffer}")
        if self.max_turnover_per_rebalance is not None and self.max_turnover_per_rebalance <= Decimal("0.0"):
            raise DomainValidationError("max_turnover_per_rebalance must be strictly positive if specified")

        payload = {
            "min_weight": str(self.min_weight),
            "max_weight": str(self.max_weight),
            "max_gross_leverage": str(self.max_gross_leverage),
            "min_cash_buffer": str(self.min_cash_buffer),
            "max_turnover_per_rebalance": str(self.max_turnover_per_rebalance) if self.max_turnover_per_rebalance is not None else "",
        }
        object.__setattr__(self, "constraints_digest", _sha256_hexdigest(payload))
        return self


class RiskSnapshot(BaseModel):
    """Current account financial state and risk limits from the live execution ledger."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_id: str
    timestamp: datetime
    account_equity: Decimal
    cash_balance: Decimal
    margin_used: Decimal
    margin_headroom: Decimal
    margin_buffer_threshold: Decimal
    current_drawdown_pct: Decimal
    max_drawdown_limit_pct: Decimal
    is_kill_switch_active: bool
    snapshot_digest: str = ""

    @model_validator(mode="after")
    def validate_risk_invariants(self) -> "RiskSnapshot":
        if self.account_equity <= Decimal("0.0"):
            raise DomainValidationError(f"account_equity must be strictly positive, got {self.account_equity}")

        payload = {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "account_equity": str(self.account_equity),
            "cash_balance": str(self.cash_balance),
            "margin_used": str(self.margin_used),
            "margin_headroom": str(self.margin_headroom),
            "margin_buffer_threshold": str(self.margin_buffer_threshold),
            "current_drawdown_pct": str(self.current_drawdown_pct),
            "max_drawdown_limit_pct": str(self.max_drawdown_limit_pct),
            "is_kill_switch_active": self.is_kill_switch_active,
        }
        object.__setattr__(self, "snapshot_digest", _sha256_hexdigest(payload))
        return self


class AllocationCandidate(BaseModel):
    """Raw weight proposal generated by an individual allocator algorithm."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: str
    allocator_name: str
    asset_weights: Mapping[str, Decimal]
    cash_weight: Optional[Decimal] = None
    search_trials_k: int = 1
    trial_variance: float = 0.0
    in_sample_metrics: Mapping[str, Decimal] = Field(default_factory=dict)
    provenance: Mapping[str, str] = Field(default_factory=dict)
    candidate_digest: str = ""

    @model_validator(mode="before")
    @classmethod
    def validate_candidate_and_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_weights = data.get("asset_weights", {})
            cleaned_weights: dict[str, Decimal] = {}
            weight_sum = Decimal("0.0")

            prov_raw = data.get("provenance", {})
            if isinstance(prov_raw, dict):
                data["provenance"] = {str(k): str(v) for k, v in sorted(prov_raw.items())}
            else:
                data["provenance"] = {}

            for s, w in raw_weights.items():
                w_dec = Decimal(str(w))
                if not w_dec.is_finite() or w_dec < Decimal("0.0"):
                    raise DomainValidationError(f"Asset weight for {s} must be a non-negative finite Decimal: {w}")
                cleaned_weights[s.strip().upper()] = w_dec
                weight_sum += w_dec

            if weight_sum > Decimal("1.000000001"):
                raise DomainValidationError(f"Asset weights sum ({weight_sum}) exceeds 1.0.")

            cash_w = data.get("cash_weight")
            if cash_w is not None:
                cash_dec = Decimal(str(cash_w))
                if not cash_dec.is_finite() or cash_dec < Decimal("0.0"):
                    raise DomainValidationError(f"cash_weight must be non-negative finite Decimal: {cash_w}")
                data["cash_weight"] = cash_dec
            else:
                data["cash_weight"] = max(Decimal("0.0"), Decimal("1.0") - weight_sum)

            data["asset_weights"] = cleaned_weights
            trials_k = int(data.get("search_trials_k", 1))
            trial_var = float(data.get("trial_variance", 0.0))
            data["search_trials_k"] = trials_k
            data["trial_variance"] = trial_var

            payload = {
                "candidate_id": data.get("candidate_id"),
                "allocator_name": data.get("allocator_name"),
                "asset_weights": {k: str(v) for k, v in sorted(cleaned_weights.items())},
                "cash_weight": str(data["cash_weight"]),
                "search_trials_k": trials_k,
                "trial_variance": str(trial_var),
            }
            data["candidate_digest"] = _sha256_hexdigest(payload)
        return data


class AllocationEvaluation(BaseModel):
    """Objective out-of-sample economic and friction scorecard for an AllocationCandidate."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: str
    normalized_weights: Mapping[str, Decimal]
    normalized_cash_weight: Decimal
    oos_sharpe_ratio: Optional[Decimal]
    oos_cvar_95: Optional[Decimal]
    turnover_required: Decimal
    estimated_transaction_cost: Decimal
    net_expected_excess_return: Decimal
    hurdle_rate_cleared: bool
    constraints_satisfied: bool
    rank_score: Decimal
    evaluation_metadata: Mapping[str, str] = {}
    candidate_digest: str = ""
    evaluation_digest: str = ""

    @model_validator(mode="before")
    @classmethod
    def validate_evaluation_and_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            weights = data.get("normalized_weights", {})
            cash_w = Decimal(str(data.get("normalized_cash_weight", "0.0")))
            cleaned_w = {k.strip().upper(): Decimal(str(v)) for k, v in weights.items()}
            total_sum = sum(cleaned_w.values(), Decimal("0.0")) + cash_w

            if abs(total_sum - Decimal("1.0")) > Decimal("1e-6"):
                raise DomainValidationError(f"Normalized weights + cash must equal 1.0 exactly, got {total_sum}")

            data["normalized_weights"] = cleaned_w
            data["normalized_cash_weight"] = cash_w

            meta = data.get("evaluation_metadata", {})
            data["evaluation_metadata"] = {str(k): str(v) for k, v in sorted(meta.items())}

            cand_d = str(data.get("candidate_digest", ""))
            data["candidate_digest"] = cand_d

            payload = {
                "candidate_id": data.get("candidate_id"),
                "candidate_digest": cand_d,
                "normalized_weights": {k: str(v) for k, v in sorted(cleaned_w.items())},
                "normalized_cash_weight": str(cash_w),
                "rank_score": str(data.get("rank_score")),
                "hurdle_rate_cleared": data.get("hurdle_rate_cleared"),
                "constraints_satisfied": data.get("constraints_satisfied"),
                "evaluation_metadata": {str(k): str(v) for k, v in sorted(meta.items())},
            }
            data["evaluation_digest"] = _sha256_hexdigest(payload)
        return data


class AllocationDecision(BaseModel):
    """Authoritative, governance-approved target portfolio allocation ready for rebalance planning."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str
    selected_candidate_id: str
    allocator_name: str
    authorized_weights: Mapping[str, Decimal]
    cash_weight: Decimal
    authorization_timestamp: datetime
    is_fallback_baseline: bool
    gate_verdict: str
    rationale: str
    candidate_digest: str = ""
    evaluation_digest: str = ""
    risk_snapshot_digest: str = ""
    constraints_digest: str = ""
    governance_policy_version: str = "v1.0.0"
    decision_digest: str = ""

    @model_validator(mode="before")
    @classmethod
    def validate_decision_and_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            weights = data.get("authorized_weights", {})
            cash_w = Decimal(str(data.get("cash_weight", "0.0")))
            cleaned_w = {k.strip().upper(): Decimal(str(v)) for k, v in weights.items()}

            data["authorized_weights"] = cleaned_w
            data["cash_weight"] = cash_w

            ts = data.get("authorization_timestamp")
            ts_str = ts.isoformat() if isinstance(ts, datetime) else str(ts)

            cand_d = str(data.get("candidate_digest", ""))
            eval_d = str(data.get("evaluation_digest", ""))
            risk_d = str(data.get("risk_snapshot_digest", ""))
            const_d = str(data.get("constraints_digest", ""))
            gov_ver = str(data.get("governance_policy_version", "v1.0.0"))

            data["candidate_digest"] = cand_d
            data["evaluation_digest"] = eval_d
            data["risk_snapshot_digest"] = risk_d
            data["constraints_digest"] = const_d
            data["governance_policy_version"] = gov_ver

            payload = {
                "decision_id": data.get("decision_id"),
                "selected_candidate_id": data.get("selected_candidate_id"),
                "allocator_name": data.get("allocator_name"),
                "authorized_weights": {k: str(v) for k, v in sorted(cleaned_w.items())},
                "cash_weight": str(cash_w),
                "authorization_timestamp": ts_str,
                "gate_verdict": data.get("gate_verdict"),
                "candidate_digest": cand_d,
                "evaluation_digest": eval_d,
                "risk_snapshot_digest": risk_d,
                "constraints_digest": const_d,
                "governance_policy_version": gov_ver,
            }
            data["decision_digest"] = _sha256_hexdigest(payload)
        return data


class RebalancePlan(BaseModel):
    """Translation of AllocationDecision into desired portfolio position deltas and reference notionals."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str
    decision_id: str
    as_of: datetime
    current_weights: Mapping[str, Decimal]
    target_weights: Mapping[str, Decimal]
    realized_cash_weight: Decimal = Decimal("0.0")
    desired_notional_delta: Mapping[str, Decimal]
    desired_position_delta: Mapping[str, Decimal]
    reference_prices: Mapping[str, Decimal]
    estimated_rebalance_friction: Decimal
    friction_estimate_provenance: str = "PLANNER_LOCAL_SIZING_ESTIMATE_V1"
    decision_digest: str = ""
    plan_digest: str = ""

    @model_validator(mode="before")
    @classmethod
    def validate_plan_and_digest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            dec_d = str(data.get("decision_digest", ""))
            data["decision_digest"] = dec_d

            cleaned_curr_w = {k.strip().upper(): Decimal(str(v)) for k, v in data.get("current_weights", {}).items()}
            cleaned_target_w = {k.strip().upper(): Decimal(str(v)) for k, v in data.get("target_weights", {}).items()}
            cleaned_pos_delta = {k.strip().upper(): Decimal(str(v)) for k, v in data.get("desired_position_delta", {}).items()}
            cleaned_notional_delta = {k.strip().upper(): Decimal(str(v)) for k, v in data.get("desired_notional_delta", {}).items()}
            cleaned_ref_prices = {k.strip().upper(): Decimal(str(v)) for k, v in data.get("reference_prices", {}).items()}
            realized_cash = Decimal(str(data.get("realized_cash_weight", "0.0")))
            friction_prov = str(data.get("friction_estimate_provenance", "PLANNER_LOCAL_SIZING_ESTIMATE_V1"))

            data["current_weights"] = cleaned_curr_w
            data["target_weights"] = cleaned_target_w
            data["desired_position_delta"] = cleaned_pos_delta
            data["desired_notional_delta"] = cleaned_notional_delta
            data["reference_prices"] = cleaned_ref_prices
            data["realized_cash_weight"] = realized_cash
            data["friction_estimate_provenance"] = friction_prov

            payload = {
                "decision_digest": dec_d,
                "current_weights": {k: str(v) for k, v in sorted(cleaned_curr_w.items())},
                "target_weights": {k: str(v) for k, v in sorted(cleaned_target_w.items())},
                "realized_cash_weight": str(realized_cash),
                "desired_position_delta": {k: str(v) for k, v in sorted(cleaned_pos_delta.items())},
                "desired_notional_delta": {k: str(v) for k, v in sorted(cleaned_notional_delta.items())},
                "reference_prices": {k: str(v) for k, v in sorted(cleaned_ref_prices.items())},
                "friction_estimate_provenance": friction_prov,
            }
            data["plan_digest"] = _sha256_hexdigest(payload)
        return data


def recompute_digest(model: BaseModel) -> str:
    """Canonical recomputation of SHA-256 digest for any Phase 8 Portfolio Domain entity."""
    payload: dict[str, Any]
    if isinstance(model, PortfolioUniverse):
        payload = {
            "universe_id": model.universe_id,
            "assets": list(model.assets),
            "as_of": model.as_of.isoformat(),
        }
        return _sha256_hexdigest(payload)
    elif isinstance(model, AssetReturnPanel):
        payload = {
            "universe_id": model.universe_id,
            "timestamps": [t.isoformat() for t in model.timestamps],
            "symbols": list(model.symbols),
            "returns_matrix": [[str(v) for v in row] for row in model.returns_matrix],
            "frequency": model.frequency,
        }
        return _sha256_hexdigest(payload)
    elif isinstance(model, PortfolioConstraints):
        payload = {
            "min_weight": str(model.min_weight),
            "max_weight": str(model.max_weight),
            "max_gross_leverage": str(model.max_gross_leverage),
            "min_cash_buffer": str(model.min_cash_buffer),
            "max_turnover_per_rebalance": str(model.max_turnover_per_rebalance) if model.max_turnover_per_rebalance is not None else "",
        }
        return _sha256_hexdigest(payload)
    elif isinstance(model, RiskSnapshot):
        payload = {
            "snapshot_id": model.snapshot_id,
            "timestamp": model.timestamp.isoformat(),
            "account_equity": str(model.account_equity),
            "cash_balance": str(model.cash_balance),
            "margin_used": str(model.margin_used),
            "margin_headroom": str(model.margin_headroom),
            "margin_buffer_threshold": str(model.margin_buffer_threshold),
            "current_drawdown_pct": str(model.current_drawdown_pct),
            "max_drawdown_limit_pct": str(model.max_drawdown_limit_pct),
            "is_kill_switch_active": model.is_kill_switch_active,
        }
        return _sha256_hexdigest(payload)
    elif isinstance(model, AllocationCandidate):
        payload = {
            "candidate_id": model.candidate_id,
            "allocator_name": model.allocator_name,
            "asset_weights": {k: str(v) for k, v in sorted(model.asset_weights.items())},
            "cash_weight": str(model.cash_weight) if model.cash_weight is not None else "0.0",
            "search_trials_k": model.search_trials_k,
            "trial_variance": str(model.trial_variance),
        }
        return _sha256_hexdigest(payload)
    elif isinstance(model, AllocationEvaluation):
        payload = {
            "candidate_id": model.candidate_id,
            "candidate_digest": model.candidate_digest,
            "normalized_weights": {k: str(v) for k, v in sorted(model.normalized_weights.items())},
            "normalized_cash_weight": str(model.normalized_cash_weight),
            "rank_score": str(model.rank_score),
            "hurdle_rate_cleared": model.hurdle_rate_cleared,
            "constraints_satisfied": model.constraints_satisfied,
            "evaluation_metadata": {str(k): str(v) for k, v in sorted(model.evaluation_metadata.items())},
        }
        return _sha256_hexdigest(payload)
    elif isinstance(model, AllocationDecision):
        payload = {
            "decision_id": model.decision_id,
            "selected_candidate_id": model.selected_candidate_id,
            "allocator_name": model.allocator_name,
            "authorized_weights": {k: str(v) for k, v in sorted(model.authorized_weights.items())},
            "cash_weight": str(model.cash_weight),
            "authorization_timestamp": model.authorization_timestamp.isoformat(),
            "gate_verdict": model.gate_verdict,
            "candidate_digest": model.candidate_digest,
            "evaluation_digest": model.evaluation_digest,
            "risk_snapshot_digest": model.risk_snapshot_digest,
            "constraints_digest": model.constraints_digest,
            "governance_policy_version": model.governance_policy_version,
        }
        return _sha256_hexdigest(payload)
    elif isinstance(model, RebalancePlan):
        payload = {
            "decision_digest": model.decision_digest,
            "current_weights": {k: str(v) for k, v in sorted(model.current_weights.items())},
            "target_weights": {k: str(v) for k, v in sorted(model.target_weights.items())},
            "realized_cash_weight": str(model.realized_cash_weight),
            "desired_position_delta": {k: str(v) for k, v in sorted(model.desired_position_delta.items())},
            "desired_notional_delta": {k: str(v) for k, v in sorted(model.desired_notional_delta.items())},
            "reference_prices": {k: str(v) for k, v in sorted(model.reference_prices.items())},
            "friction_estimate_provenance": model.friction_estimate_provenance,
        }
        return _sha256_hexdigest(payload)
    raise ValueError(f"Unsupported model type for digest recomputation: {type(model)}")
