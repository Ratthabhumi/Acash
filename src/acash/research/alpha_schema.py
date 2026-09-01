"""Phase 8.5 Canonical Domain Contracts & State Machine (Contract v1.3 Locked).

Strictly enforces:
1. Four-Way Separation of Concerns: Research (8.5) != Allocation (8) != Risk (9) != Execution (7).
2. Every Phase 8.5 state has capital_authority_usd == Decimal("0.00") (Zero Trading Authority).
3. RESEARCH_QUALIFIED certifies evidence completeness only, never live execution authorization.
4. Deterministic, forward-moving lifecycle state machine with zero retrospective mutation.
5. Strict economic decomposition: Net Trading Alpha = Gross - Friction; Rebates cannot alter Net Alpha.
6. Single canonical authority lineage: SHA-256 DAG binding hypothesis, trial ledger, validation, and policy.
"""

from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
import json
import math
from typing import Any, Dict, Mapping, Optional, Sequence, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer


def _verify_finite_decimal(v: Any, context: str = "value") -> Decimal:
    """Strict finite Decimal validation."""
    if isinstance(v, Decimal):
        if not v.is_finite():
            raise DataContractError(f"Non-finite Decimal {context} '{v}' encountered.")
        return v
    if isinstance(v, (int, float, str)):
        try:
            dec = Decimal(str(v))
            if not dec.is_finite():
                raise DataContractError(f"Non-finite {context} '{v}' encountered.")
            return dec
        except (InvalidOperation, OverflowError) as e:
            raise DataContractError(f"Invalid numeric representation for {context} '{v}'.") from e
    raise DataContractError(f"Unsupported type {type(v)} for Decimal {context}.")


# ---------------------------------------------------------------------------
# 1. Alpha Lifecycle State Machine
# ---------------------------------------------------------------------------


class AlphaLifecycleState(str, Enum):
    """Authoritative state machine for Alpha strategy lifecycle (Zero Capital Authority)."""

    # Core Progression States
    HYPOTHESIS = "HYPOTHESIS"
    RESEARCH_SEARCH = "RESEARCH_SEARCH"
    CANDIDATE = "CANDIDATE"
    STATISTICAL_VALIDATED = "STATISTICAL_VALIDATED"
    ECONOMIC_EDGE_QUALIFIED = "ECONOMIC_EDGE_QUALIFIED"
    FORWARD_PAPER_MONITORED = "FORWARD_PAPER_MONITORED"
    RESEARCH_QUALIFIED = "RESEARCH_QUALIFIED"

    # Explicit Terminal / Failure States
    REJECTED_STATISTICAL_GATE = "REJECTED_STATISTICAL_GATE"
    REJECTED_HURDLE_COLLAPSE = "REJECTED_HURDLE_COLLAPSE"
    DEGRADED_FORWARD_TEST = "DEGRADED_FORWARD_TEST"
    RETIRED_STRUCTURAL_BREAK = "RETIRED_STRUCTURAL_BREAK"


# Strict deterministic mapping of permitted forward state transitions
ALLOWED_LIFECYCLE_TRANSITIONS: Mapping[AlphaLifecycleState, Set[AlphaLifecycleState]] = {
    AlphaLifecycleState.HYPOTHESIS: {AlphaLifecycleState.RESEARCH_SEARCH},
    AlphaLifecycleState.RESEARCH_SEARCH: {AlphaLifecycleState.CANDIDATE},
    AlphaLifecycleState.CANDIDATE: {
        AlphaLifecycleState.STATISTICAL_VALIDATED,
        AlphaLifecycleState.REJECTED_STATISTICAL_GATE,
    },
    AlphaLifecycleState.STATISTICAL_VALIDATED: {
        AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED,
        AlphaLifecycleState.REJECTED_HURDLE_COLLAPSE,
    },
    AlphaLifecycleState.ECONOMIC_EDGE_QUALIFIED: {
        AlphaLifecycleState.FORWARD_PAPER_MONITORED,
        AlphaLifecycleState.DEGRADED_FORWARD_TEST,
    },
    AlphaLifecycleState.FORWARD_PAPER_MONITORED: {
        AlphaLifecycleState.RESEARCH_QUALIFIED,
        AlphaLifecycleState.DEGRADED_FORWARD_TEST,
    },
    AlphaLifecycleState.RESEARCH_QUALIFIED: {
        AlphaLifecycleState.RETIRED_STRUCTURAL_BREAK,
    },
    # Terminal / Rejection states have zero allowed outbound transitions
    AlphaLifecycleState.REJECTED_STATISTICAL_GATE: set(),
    AlphaLifecycleState.REJECTED_HURDLE_COLLAPSE: set(),
    AlphaLifecycleState.DEGRADED_FORWARD_TEST: set(),
    AlphaLifecycleState.RETIRED_STRUCTURAL_BREAK: set(),
}


def validate_lifecycle_transition(
    current_state: AlphaLifecycleState,
    target_state: AlphaLifecycleState,
) -> None:
    """Validate that a lifecycle state transition is deterministic, forward-moving, and permitted.

    Raises:
        DataContractError: If the transition is illegal, retrospective, or from a terminal state.
    """
    if current_state == target_state:
        return

    allowed_targets = ALLOWED_LIFECYCLE_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        raise DataContractError(
            f"Illegal Alpha lifecycle transition from '{current_state.value}' to '{target_state.value}'. "
            f"Allowed transitions from '{current_state.value}' are: {[s.value for s in allowed_targets]}."
        )


# ---------------------------------------------------------------------------
# 2. Economic Decomposition & Rebate Isolation
# ---------------------------------------------------------------------------


class AlphaEconomicDecomposition(BaseModel):
    """Strict decomposition of gross trading returns, friction, and broker rebates.

    Enforces:
    - Net Trading Alpha = Gross Trading P&L - Realized Friction (Spread + Slippage + Commissions)
    - Total Economic Result = Net Trading Alpha + Broker Rebates
    - Net Trading Alpha is strictly independent of Broker Rebates.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    gross_trading_pnl_bps: Decimal
    realized_spread_slippage_bps: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    broker_commissions_bps: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    net_trading_alpha_bps: Decimal
    broker_rebate_income_bps: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    total_realized_economic_bps: Decimal

    @model_validator(mode="before")
    @classmethod
    def validate_finite_and_arithmetic_invariants(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        gross = _verify_finite_decimal(data.get("gross_trading_pnl_bps", Decimal("0.0")), "gross_trading_pnl_bps")
        spread = _verify_finite_decimal(data.get("realized_spread_slippage_bps", Decimal("0.0")), "realized_spread_slippage_bps")
        comm = _verify_finite_decimal(data.get("broker_commissions_bps", Decimal("0.0")), "broker_commissions_bps")
        net = _verify_finite_decimal(data.get("net_trading_alpha_bps", Decimal("0.0")), "net_trading_alpha_bps")
        rebate = _verify_finite_decimal(data.get("broker_rebate_income_bps", Decimal("0.0")), "broker_rebate_income_bps")
        total = _verify_finite_decimal(data.get("total_realized_economic_bps", Decimal("0.0")), "total_realized_economic_bps")

        if spread < Decimal("0.0"):
            raise DataContractError(f"realized_spread_slippage_bps cannot be negative: {spread}")
        if comm < Decimal("0.0"):
            raise DataContractError(f"broker_commissions_bps cannot be negative: {comm}")
        if rebate < Decimal("0.0"):
            raise DataContractError(f"broker_rebate_income_bps cannot be negative: {rebate}")

        # Invariant: Net = Gross - (Spread + Commission)
        expected_net = gross - (spread + comm)
        if abs(net - expected_net) > Decimal("1e-12"):
            raise DataContractError(
                f"Economic arithmetic violation: net_trading_alpha_bps ({net}) != "
                f"gross ({gross}) - costs ({spread + comm}) = {expected_net}."
            )

        # Invariant: Total = Net + Rebate
        expected_total = net + rebate
        if abs(total - expected_total) > Decimal("1e-12"):
            raise DataContractError(
                f"Economic arithmetic violation: total_realized_economic_bps ({total}) != "
                f"net ({net}) + rebate ({rebate}) = {expected_total}."
            )

        return data

    def is_economically_viable(self, hurdle_rate_bps: Decimal) -> bool:
        """Evaluate if trading alpha independently clears the hurdle rate with ZERO rebate credit."""
        _verify_finite_decimal(hurdle_rate_bps, "hurdle_rate_bps")
        return self.net_trading_alpha_bps >= hurdle_rate_bps


# ---------------------------------------------------------------------------
# 3. Computable Falsification Trigger
# ---------------------------------------------------------------------------


class FalsificationComparisonOperator(str, Enum):
    """Deterministic comparison operators for falsification assertions."""

    LESS_THAN = "LESS_THAN"
    GREATER_THAN = "GREATER_THAN"
    LESS_EQUAL = "LESS_EQUAL"
    GREATER_EQUAL = "GREATER_EQUAL"


class AlphaFalsificationTrigger(BaseModel):
    """Deterministic, computable invalidation trigger for alpha monitoring."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trigger_name: str = Field(min_length=1)
    metric_name: str = Field(min_length=1)
    threshold_value: Decimal
    comparison_operator: FalsificationComparisonOperator
    is_triggered: bool = False
    observed_value: Optional[Decimal] = None
    trigger_reason: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_finite_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "threshold_value" in data:
                _verify_finite_decimal(data["threshold_value"], "threshold_value")
            if data.get("observed_value") is not None:
                _verify_finite_decimal(data["observed_value"], "observed_value")
        return data


# ---------------------------------------------------------------------------
# 4. Cryptographic Evidence Envelope: AlphaQualificationDossier
# ---------------------------------------------------------------------------


class AlphaQualificationDossier(BaseModel):
    """Cryptographic evidence envelope binding multi-phase research lineage.

    Invariants:
    - Dossier is an Evidence Envelope, NOT a proof generator.
    - Research qualification does NOT imply live trading or capital authorization ($0.00).
    - capital_authority_usd is strictly fixed to Decimal('0.00').
    - Lineage digests must be valid 64-character hex strings (SHA-256).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    alpha_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    lifecycle_state: AlphaLifecycleState

    # Cryptographic Lineage DAG (All must be 64-hex SHA-256 digests)
    hypothesis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    trial_ledger_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_report_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    governance_policy_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    # Economic & Falsification Evidence
    economic_decomposition: AlphaEconomicDecomposition
    falsification_triggers: Tuple[AlphaFalsificationTrigger, ...] = Field(default_factory=tuple)

    governance_policy_version: str = Field(default="v1.0")
    created_timestamp_utc: str

    # Non-negotiable Zero Capital Authority Invariant
    capital_authority_usd: Decimal = Field(default=Decimal("0.00"))

    # Sealed dossier digest
    dossier_digest: str = Field(default="", pattern=r"^([0-9a-f]{64})?$")

    @field_validator("capital_authority_usd")
    @classmethod
    def validate_zero_capital_authority(cls, v: Decimal) -> Decimal:
        dec = _verify_finite_decimal(v, "capital_authority_usd")
        if dec != Decimal("0.00"):
            raise DataContractError(
                f"Capital authority invariant violated! Every Phase 8.5 AlphaQualificationDossier "
                f"must have capital_authority_usd == 0.00, got: {dec}."
            )
        return dec

    @property
    def is_research_qualified(self) -> bool:
        """Certifies whether candidate holds RESEARCH_QUALIFIED evidence status."""
        return self.lifecycle_state == AlphaLifecycleState.RESEARCH_QUALIFIED

    def compute_dossier_digest(self) -> str:
        """Compute authoritative SHA-256 digest of the dossier envelope using CanonicalConfigSerializer."""
        d = {
            "alpha_id": self.alpha_id,
            "strategy_id": self.strategy_id,
            "lifecycle_state": self.lifecycle_state.value,
            "hypothesis_digest": self.hypothesis_digest,
            "trial_ledger_digest": self.trial_ledger_digest,
            "validation_report_digest": self.validation_report_digest,
            "governance_policy_digest": self.governance_policy_digest,
            "economic_decomposition": self.economic_decomposition.model_dump(mode="json"),
            "falsification_triggers": [t.model_dump(mode="json") for t in self.falsification_triggers],
            "governance_policy_version": self.governance_policy_version,
            "created_timestamp_utc": self.created_timestamp_utc,
            "capital_authority_usd": str(self.capital_authority_usd),
        }
        canonical_json = CanonicalConfigSerializer.to_canonical_json(d)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
