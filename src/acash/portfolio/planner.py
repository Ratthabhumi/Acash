"""Portfolio Rebalance Planner for Phase 8 Portfolio Engine.

Translates an authorized AllocationDecision into a deterministic RebalancePlan
containing position deltas and reference sizing notionals without crossing
into Phase 7 execution / broker authority.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import math
from typing import Mapping, Optional
from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.portfolio.schema import (
    AllocationDecision,
    PortfolioConstraints,
    RebalancePlan,
    recompute_digest,
)


class RoundingPolicy(str, Enum):
    """Deterministic rounding policies for target position quantities."""
    EXACT_FRACTIONAL = "EXACT_FRACTIONAL"
    FLOOR_INTEGER = "FLOOR_INTEGER"
    ROUND_NEAREST_INTEGER = "ROUND_NEAREST_INTEGER"
    REJECT_FRACTIONAL = "REJECT_FRACTIONAL"


class RebalancePlannerConfig(BaseModel):
    """Configuration for rebalance planning and sizing calculations."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    rounding_policy: RoundingPolicy = RoundingPolicy.EXACT_FRACTIONAL
    cost_per_share: Decimal = Decimal("0.005")
    cost_basis_bps: Decimal = Decimal("0.0005")  # 5 bps
    min_trade_notional: Decimal = Decimal("0.0")


class RebalancePlanner:
    """Deterministic planner constructing RebalancePlan from approved AllocationDecision."""

    def __init__(self, config: Optional[RebalancePlannerConfig] = None) -> None:
        self.config = config or RebalancePlannerConfig()

    def generate_plan(
        self,
        decision: AllocationDecision,
        account_equity: Decimal,
        current_positions: Mapping[str, Decimal],
        reference_prices: Mapping[str, Decimal],
        constraints: PortfolioConstraints,
        as_of: Optional[datetime] = None,
    ) -> RebalancePlan:
        """Construct deterministic RebalancePlan from authorized AllocationDecision."""
        plan_ts = as_of or datetime.now(timezone.utc)

        # 1. Cryptographic Decision Digest & Lineage Verification
        if not decision.decision_digest or recompute_digest(decision) != decision.decision_digest:
            raise DataContractError(
                "AllocationDecision cryptographic digest verification failed or digest is missing."
            )

        # 2. Valuation Epoch Consistency
        if as_of is not None and as_of < decision.authorization_timestamp:
            raise DataContractError(
                f"Valuation as_of ({as_of.isoformat()}) precedes decision authorization timestamp ({decision.authorization_timestamp.isoformat()})."
            )

        # 3. Decision Approval Status Verification
        if decision.gate_verdict not in (
            "APPROVED_INVESTABLE_ALLOCATION",
            "PRE_RISK_GATE_KILL_SWITCH_ACTIVE",
            "PRE_RISK_GATE_DRAWDOWN_LIMIT_BREACHED",
            "PRE_RISK_GATE_MARGIN_BUFFER_BREACHED",
            "CONSTRAINT_INFEASIBLE",
            "REJECT_NO_ELIGIBLE_CANDIDATE",
        ):
            raise DataContractError(
                f"Cannot generate RebalancePlan from unapproved or unknown decision verdict: '{decision.gate_verdict}'."
            )

        # 4. Account Equity Invariants
        if not account_equity.is_finite() or account_equity <= Decimal("0.0"):
            raise DataContractError(f"account_equity must be a strictly positive finite Decimal, got {account_equity}")

        # 5. Clean and Collect Symbol Universe & Validate Long-Only
        cleaned_curr_pos = {k.strip().upper(): Decimal(str(v)) for k, v in current_positions.items()}
        cleaned_ref_prices = {k.strip().upper(): Decimal(str(v)) for k, v in reference_prices.items()}
        target_weights = {k.strip().upper(): Decimal(str(v)) for k, v in decision.authorized_weights.items()}

        # Verify all current positions are finite and non-negative (long-only)
        for sym, q in cleaned_curr_pos.items():
            if not q.is_finite():
                raise DataContractError(f"Current position for '{sym}' must be a finite Decimal, got {q}")
            if q < Decimal("0.0"):
                raise DataContractError(
                    f"Negative position ({q}) for '{sym}' violates strict long-only contract. Short positions are unsupported."
                )

        all_symbols = sorted(set(list(target_weights.keys()) + list(cleaned_curr_pos.keys())))

        # 6. Reference Price Verification for all active or target assets
        for sym in all_symbols:
            curr_q = cleaned_curr_pos.get(sym, Decimal("0.0"))
            target_w = target_weights.get(sym, Decimal("0.0"))

            if curr_q != Decimal("0.0") or target_w != Decimal("0.0"):
                if sym not in cleaned_ref_prices:
                    raise DataContractError(f"Missing required reference price for symbol '{sym}'.")
                p = cleaned_ref_prices[sym]
                if not p.is_finite() or p <= Decimal("0.0"):
                    raise DataContractError(
                        f"Reference price for symbol '{sym}' must be strictly positive and finite, got {p}."
                    )

        # 7. Compute Current Weights, Raw Target Quantities, and Apply Rounding
        curr_weights_out: dict[str, Decimal] = {}
        realized_target_weights_out: dict[str, Decimal] = {}
        realized_target_quantities: dict[str, Decimal] = {}
        pos_deltas: dict[str, Decimal] = {}
        notional_deltas: dict[str, Decimal] = {}
        total_friction = Decimal("0.0")
        realized_risky_val_sum = Decimal("0.0")

        is_cash_decision = (
            decision.is_fallback_baseline
            or decision.allocator_name == "CASH"
            or decision.gate_verdict != "APPROVED_INVESTABLE_ALLOCATION"
        )

        for sym in all_symbols:
            curr_q = cleaned_curr_pos.get(sym, Decimal("0.0"))
            target_w = target_weights.get(sym, Decimal("0.0"))
            price = cleaned_ref_prices.get(sym, Decimal("1.0"))

            curr_val = curr_q * price
            curr_w = curr_val / account_equity
            curr_weights_out[sym] = curr_w

            # If decision is cash-fallback or target weight is zero -> target quantity is 0
            if is_cash_decision or target_w == Decimal("0.0"):
                target_q = Decimal("0.0")
            else:
                target_val = account_equity * target_w
                raw_target_q = target_val / price
                target_q = self._apply_rounding(raw_target_q, sym)

            realized_target_quantities[sym] = target_q
            realized_val = target_q * price
            realized_w = realized_val / account_equity
            realized_target_weights_out[sym] = realized_w
            realized_risky_val_sum += realized_val

            delta_q = target_q - curr_q
            delta_val = delta_q * price

            pos_deltas[sym] = delta_q
            notional_deltas[sym] = delta_val

            # Estimate friction (sizing/execution estimate only)
            abs_delta_q = abs(delta_q)
            abs_delta_val = abs(delta_val)
            trade_friction = (abs_delta_q * self.config.cost_per_share) + (abs_delta_val * self.config.cost_basis_bps)
            total_friction += trade_friction

        # 8. Compute Realized Residual Cash Weight & Post-Rounding Constraint Validation
        realized_gross_leverage = sum(realized_target_weights_out.values(), Decimal("0.0"))
        realized_cash_weight = max(Decimal("0.0"), Decimal("1.0") - realized_gross_leverage)

        if not is_cash_decision:
            # Independent Post-Rounding Feasibility Check
            for sym, w in realized_target_weights_out.items():
                if w < constraints.min_weight - Decimal("1e-4") or w > constraints.max_weight + Decimal("1e-4"):
                    raise DataContractError(
                        f"Post-rounding realized weight for '{sym}' ({w}) breaches constraints [{constraints.min_weight}, {constraints.max_weight}]."
                    )
            if realized_cash_weight < constraints.min_cash_buffer - Decimal("1e-4"):
                raise DataContractError(
                    f"Post-rounding realized cash ({realized_cash_weight}) falls below min_cash_buffer ({constraints.min_cash_buffer})."
                )
            if realized_gross_leverage > constraints.max_gross_leverage + Decimal("1e-4"):
                raise DataContractError(
                    f"Post-rounding gross leverage ({realized_gross_leverage}) exceeds max_gross_leverage ({constraints.max_gross_leverage})."
                )
        else:
            realized_cash_weight = Decimal("1.0")

        # 9. Build and Return Canonical RebalancePlan
        return RebalancePlan(
            plan_id=f"PLAN_{decision.decision_id}_{int(plan_ts.timestamp())}",
            decision_id=decision.decision_id,
            decision_digest=decision.decision_digest,
            as_of=plan_ts,
            current_weights=curr_weights_out,
            target_weights=realized_target_weights_out,
            realized_cash_weight=realized_cash_weight,
            desired_position_delta=pos_deltas,
            desired_notional_delta=notional_deltas,
            reference_prices={s: cleaned_ref_prices[s] for s in all_symbols if s in cleaned_ref_prices},
            estimated_rebalance_friction=total_friction,
            friction_estimate_provenance="PLANNER_LOCAL_SIZING_ESTIMATE_V1",
        )

    def _apply_rounding(self, raw_q: Decimal, symbol: str) -> Decimal:
        """Apply configured rounding policy to target quantity."""
        if self.config.rounding_policy == RoundingPolicy.EXACT_FRACTIONAL:
            return raw_q
        elif self.config.rounding_policy == RoundingPolicy.FLOOR_INTEGER:
            return Decimal(int(math.floor(float(raw_q))))
        elif self.config.rounding_policy == RoundingPolicy.ROUND_NEAREST_INTEGER:
            return Decimal(round(float(raw_q)))
        elif self.config.rounding_policy == RoundingPolicy.REJECT_FRACTIONAL:
            int_q = Decimal(int(raw_q))
            if raw_q != int_q:
                raise DataContractError(
                    f"Fractional target quantity {raw_q} rejected under REJECT_FRACTIONAL policy for '{symbol}'."
                )
            return int_q
        raise DataContractError(f"Unsupported RoundingPolicy: {self.config.rounding_policy}")
