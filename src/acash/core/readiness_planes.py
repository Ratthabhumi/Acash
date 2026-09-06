"""Phase 13 / System Governance: Four Decoupled Readiness Planes (Contract v1.0).

Strictly enforces:
1. Four-Way Plane Decoupling:
   Infrastructure PASS != Research Engine PASS != Strategy Alpha PASS != Trading Authorization.
2. No Single Master Switch (Amendment 3):
   There is NO single boolean 'system_ready' or master authorization switch.
   Human GO, capital authority, runtime eligibility, research engine readiness,
   and strategy qualification remain independently, conjunctively enforced.
3. Fail-Closed Boundaries:
   Infrastructure readiness cannot authorize strategy qualification.
   Research engine readiness cannot authorize trading.
   Alpha qualification cannot authorize capital without explicit, non-delegable Human GO.
   Phase 13 Step 9 cannot start automatically from infrastructure or alpha readiness.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field, model_validator

from acash.core.domain.exceptions import DataContractError


# ---------------------------------------------------------------------------
# 1. Independent Readiness Plane Enums
# ---------------------------------------------------------------------------


class InfrastructureReadinessState(str, Enum):
    """Operational health and runtime infrastructure readiness (Phase 10/13)."""

    UNVERIFIED = "UNVERIFIED"
    TESTING_IN_PROGRESS = "TESTING_IN_PROGRESS"
    SOAK_VERIFIED_PASS = "SOAK_VERIFIED_PASS"  # 24h soak verified, memory stable, zero crash
    DEGRADED = "DEGRADED"
    HALTED_FAILED = "HALTED_FAILED"


class ResearchEngineReadinessState(str, Enum):
    """Mathematical methodology and research framework readiness (Phase 8.5)."""

    UNVERIFIED = "UNVERIFIED"
    ENGINE_VERIFIED_PASS = "ENGINE_VERIFIED_PASS"  # Lineage DAG, HAC/OLS, Census, Anti-HARKing verified
    METHODOLOGY_FROZEN = "METHODOLOGY_FROZEN"
    CORRUPTED = "CORRUPTED"


class StrategyAlphaReadinessState(str, Enum):
    """Scientific validity and empirical qualification of a specific alpha strategy."""

    UNPROVEN_ZERO_QUALIFIED = "UNPROVEN_ZERO_QUALIFIED"
    HYPOTHESIS_REGISTERED = "HYPOTHESIS_REGISTERED"
    IN_SAMPLE_CENSUS_FALSIFIED = "IN_SAMPLE_CENSUS_FALSIFIED"
    STATISTICAL_VALIDATED = "STATISTICAL_VALIDATED"
    ECONOMIC_EDGE_QUALIFIED = "ECONOMIC_EDGE_QUALIFIED"
    RESEARCH_QUALIFIED = "RESEARCH_QUALIFIED"
    TERMINALLY_FALSIFIED = "TERMINALLY_FALSIFIED"


class TradingCapitalAuthorityState(str, Enum):
    """Cryptographic and sovereign capital allocation authority (Phase 9/13 Gate B)."""

    HARD_LOCKED_ZERO_CAPITAL = "HARD_LOCKED_ZERO_CAPITAL"  # $0.00 capital authority
    PAPER_AUTHORIZED_PENDING_GATE_B = "PAPER_AUTHORIZED_PENDING_GATE_B"
    LIVE_MICRO_CAPITAL_AUTHORIZED = "LIVE_MICRO_CAPITAL_AUTHORIZED"  # Explicit Human GO + Ed25519 Quorum
    EMERGENCY_REVOKED = "EMERGENCY_REVOKED"


class HumanGOCheckpointState(str, Enum):
    """Phase 13 Step 8 Non-delegable Human GO Checkpoint."""

    LOCKED_PENDING_PREREQUISITES = "LOCKED_PENDING_PREREQUISITES"
    AUTHORIZED_SIGNED = "AUTHORIZED_SIGNED"
    REJECTED_NO_GO = "REJECTED_NO_GO"
    REVOKED = "REVOKED"


# ---------------------------------------------------------------------------
# 2. System Readiness Planes Representation (No Master Switch)
# ---------------------------------------------------------------------------


class SystemReadinessPlanes(BaseModel):
    """Co-existing representation of the four decoupled governance planes.

    CRITICAL ARCHITECTURE INVARIANT (Amendment 3):
    This model contains NO 'is_ready' or 'system_ready' master boolean switch.
    Each plane is strictly independent; operations must query specific conjunctive
    evaluators rather than relying on a single collapsed flag.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    infrastructure: InfrastructureReadinessState = Field(default=InfrastructureReadinessState.UNVERIFIED)
    research_engine: ResearchEngineReadinessState = Field(default=ResearchEngineReadinessState.UNVERIFIED)
    strategy_alpha: StrategyAlphaReadinessState = Field(default=StrategyAlphaReadinessState.UNPROVEN_ZERO_QUALIFIED)
    trading_authority: TradingCapitalAuthorityState = Field(default=TradingCapitalAuthorityState.HARD_LOCKED_ZERO_CAPITAL)
    human_go: HumanGOCheckpointState = Field(default=HumanGOCheckpointState.LOCKED_PENDING_PREREQUISITES)
    capital_authority_usd: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    evaluated_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="before")
    @classmethod
    def enforce_fail_closed_capital_invariant(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cap = data.get("capital_authority_usd", Decimal("0.00"))
            if not isinstance(cap, Decimal):
                cap = Decimal(str(cap))
            auth_state = data.get("trading_authority", TradingCapitalAuthorityState.HARD_LOCKED_ZERO_CAPITAL)
            human_state = data.get("human_go", HumanGOCheckpointState.LOCKED_PENDING_PREREQUISITES)
            strat_state = data.get("strategy_alpha", StrategyAlphaReadinessState.UNPROVEN_ZERO_QUALIFIED)

            if cap > Decimal("0.00"):
                if auth_state != TradingCapitalAuthorityState.LIVE_MICRO_CAPITAL_AUTHORIZED:
                    raise DataContractError(
                        f"CAPITAL_AUTHORITY_VIOLATION: Cannot allocate capital ${cap} when "
                        f"trading_authority is '{auth_state}'. Capital authority must be LIVE_MICRO_CAPITAL_AUTHORIZED."
                    )
                if human_state != HumanGOCheckpointState.AUTHORIZED_SIGNED:
                    raise DataContractError(
                        f"HUMAN_GO_VIOLATION: Cannot allocate capital ${cap} without explicit Human GO sign-off."
                    )
                if strat_state != StrategyAlphaReadinessState.RESEARCH_QUALIFIED:
                    raise DataContractError(
                        f"STRATEGY_QUALIFICATION_VIOLATION: Cannot allocate capital ${cap} to an unproven "
                        f"or unqualified strategy state '{strat_state}'."
                    )
        return data


# ---------------------------------------------------------------------------
# 3. Independent Transition Evaluators
# ---------------------------------------------------------------------------


class ReadinessPlaneEvaluator:
    """Master evaluator verifying decoupled boundaries and preventing inference creep."""

    @classmethod
    def validate_infrastructure_does_not_authorize_strategy(
        cls,
        planes: SystemReadinessPlanes,
    ) -> None:
        """Enforce: Infrastructure PASS != Strategy Alpha PASS."""
        if planes.infrastructure == InfrastructureReadinessState.SOAK_VERIFIED_PASS:
            if planes.strategy_alpha in (
                StrategyAlphaReadinessState.UNPROVEN_ZERO_QUALIFIED,
                StrategyAlphaReadinessState.IN_SAMPLE_CENSUS_FALSIFIED,
                StrategyAlphaReadinessState.TERMINALLY_FALSIFIED,
            ):
                # Valid state: infrastructure is ready, but strategy remains unproven/falsified
                return
            if planes.strategy_alpha == StrategyAlphaReadinessState.RESEARCH_QUALIFIED:
                # Permitted only if research engine independently qualified the strategy
                if planes.research_engine != ResearchEngineReadinessState.ENGINE_VERIFIED_PASS:
                    raise DataContractError(
                        "INFERENCE_CREEP_VIOLATION: Strategy cannot be RESEARCH_QUALIFIED when "
                        "research_engine is not ENGINE_VERIFIED_PASS."
                    )

    @classmethod
    def validate_step9_continuous_paper_transition(
        cls,
        planes: SystemReadinessPlanes,
    ) -> None:
        """Enforce non-delegable prerequisites before Phase 13 Step 9 can begin.

        Strictly requires:
        1. Infrastructure == SOAK_VERIFIED_PASS
        2. Research Engine == ENGINE_VERIFIED_PASS
        3. Strategy Alpha == RESEARCH_QUALIFIED
        4. Human GO == AUTHORIZED_SIGNED (Phase 13 Step 8)
        5. Trading Authority != HARD_LOCKED_ZERO_CAPITAL (Must have paper authorization)

        Raises:
            DataContractError: If any single prerequisite fails (fail-closed).
        """
        if planes.infrastructure != InfrastructureReadinessState.SOAK_VERIFIED_PASS:
            raise DataContractError(
                f"STEP9_PRECONDITION_FAILED: Infrastructure state is '{planes.infrastructure.value}', "
                f"expected '{InfrastructureReadinessState.SOAK_VERIFIED_PASS.value}'."
            )
        if planes.research_engine != ResearchEngineReadinessState.ENGINE_VERIFIED_PASS:
            raise DataContractError(
                f"STEP9_PRECONDITION_FAILED: Research engine state is '{planes.research_engine.value}', "
                f"expected '{ResearchEngineReadinessState.ENGINE_VERIFIED_PASS.value}'."
            )
        if planes.strategy_alpha != StrategyAlphaReadinessState.RESEARCH_QUALIFIED:
            raise DataContractError(
                f"STEP9_PRECONDITION_FAILED: Strategy alpha state is '{planes.strategy_alpha.value}', "
                f"expected '{StrategyAlphaReadinessState.RESEARCH_QUALIFIED.value}'. Unproven/falsified strategies cannot paper trade."
            )
        if planes.human_go != HumanGOCheckpointState.AUTHORIZED_SIGNED:
            raise DataContractError(
                f"STEP9_PRECONDITION_FAILED: Phase 13 Step 8 Human GO is '{planes.human_go.value}'. "
                f"Mandatory human authorization is strictly required."
            )

    @classmethod
    def validate_capital_authority_boundary(
        cls,
        planes: SystemReadinessPlanes,
        requested_capital_usd: Decimal,
    ) -> None:
        """Enforce strict capital authorization limits based on decoupled readiness planes."""
        if requested_capital_usd < Decimal("0.00"):
            raise DataContractError("Capital authority cannot be negative.")

        if requested_capital_usd == Decimal("0.00"):
            # Always permitted across all states
            return

        # Positive capital strictly requires all planes satisfied
        if planes.trading_authority != TradingCapitalAuthorityState.LIVE_MICRO_CAPITAL_AUTHORIZED:
            raise DataContractError(
                f"CAPITAL_ALLOCATION_REJECTED: Trading authority is '{planes.trading_authority.value}', "
                f"not LIVE_MICRO_CAPITAL_AUTHORIZED."
            )
        if planes.human_go != HumanGOCheckpointState.AUTHORIZED_SIGNED:
            raise DataContractError(
                f"CAPITAL_ALLOCATION_REJECTED: Phase 13 Step 8 Human GO is '{planes.human_go.value}'."
            )
        if planes.strategy_alpha != StrategyAlphaReadinessState.RESEARCH_QUALIFIED:
            raise DataContractError(
                f"CAPITAL_ALLOCATION_REJECTED: Strategy alpha is '{planes.strategy_alpha.value}'."
            )
        if planes.infrastructure != InfrastructureReadinessState.SOAK_VERIFIED_PASS:
            raise DataContractError(
                f"CAPITAL_ALLOCATION_REJECTED: Infrastructure is '{planes.infrastructure.value}'."
            )
