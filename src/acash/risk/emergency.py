"""Phase 9: Emergency Flattening Generator & Lifecycle Tracker (Slice 4).

Strictly enforces:
1. Emergency Intent != Positions Flattened:
   Intent Generated != Order Submitted != Order Filled != Portfolio Flattened.
2. Zero Direct Broker Wire Access:
   Phase 9 emits pure zero-target intents; Phase 7 executes, observes, and reconciles.
3. Deterministic Closing Deltas:
   For every open position with quantity q_i, target is 0.0 and delta is -q_i.
4. Completion Semantics:
   FLATTEN_COMPLETED is granted ONLY when authoritative PortfolioState and broker reconciliation
   confirm 0 gross exposure and 0 open position quantities.
5. Partial Fill & Residual Exposure Safety:
   Partial fills remain in FLATTEN_REQUESTED until 100% liquidated.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from typing import Mapping, Optional, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.portfolio import PortfolioState
from acash.core.domain.position import Position
from acash.core.domain.types import freeze_mapping
from acash.risk.kill_switch import KillSwitchEvent
from acash.risk.risk_schema import (
    EmergencyFlattenIntent,
    EmergencyFlattenStatus,
    KillSwitchState,
    _ensure_utc,
    _verify_finite_decimal,
)


class EmergencyFlattenGenerator:
    """Deterministic generator for EmergencyFlattenIntent envelopes."""

    @classmethod
    def generate_flatten_intent(
        cls,
        portfolio_state: PortfolioState,
        kill_switch_event: KillSwitchEvent,
        as_of: Optional[datetime] = None,
    ) -> EmergencyFlattenIntent:
        """Generate a deterministic zero-target EmergencyFlattenIntent from current PortfolioState.

        Args:
            portfolio_state: Current authoritative portfolio snapshot.
            kill_switch_event: Triggering kill switch event (must be in blocked state).
            as_of: Optional explicit UTC evaluation timestamp.

        Returns:
            EmergencyFlattenIntent with status FLATTEN_REQUESTED.
        """
        # Validate kill switch state authority
        if kill_switch_event.resulting_state not in (
            KillSwitchState.TRIPPED,
            KillSwitchState.PERSISTENTLY_BLOCKED,
        ):
            raise DataContractError(
                f"Cannot generate emergency flatten intent for non-blocked kill switch state: '{kill_switch_event.resulting_state.value}'."
            )

        now = _ensure_utc(as_of or datetime.now(timezone.utc))

        target_positions: dict[str, Decimal] = {}
        closing_deltas: dict[str, Decimal] = {}

        for sym, pos in portfolio_state.positions.items():
            if not isinstance(sym, str) or not sym.strip():
                raise DataContractError(f"Invalid position symbol: '{sym}'.")
            
            clean_sym = sym.strip().upper()
            curr_qty = _verify_finite_decimal(pos.quantity, f"positions[{clean_sym}].quantity", allow_negative=True)

            if curr_qty != Decimal("0.0"):
                target_positions[clean_sym] = Decimal("0.0")
                # Delta required to return quantity to 0: delta = 0.0 - curr_qty = -curr_qty
                closing_deltas[clean_sym] = -curr_qty

        intent_id = f"FLATTEN_{kill_switch_event.event_id}_{int(now.timestamp() * 1000)}"

        return EmergencyFlattenIntent(
            intent_id=intent_id,
            kill_switch_event_id=kill_switch_event.event_id,
            target_positions=target_positions,
            closing_deltas=closing_deltas,
            issued_at_utc=now,
            status=EmergencyFlattenStatus.FLATTEN_REQUESTED,
        )


class EmergencyFlattenTracker:
    """Authoritative tracker evaluating whether an EmergencyFlattenIntent has completed."""

    @classmethod
    def verify_flatten_completion(
        cls,
        intent: EmergencyFlattenIntent,
        latest_portfolio_state: PortfolioState,
        is_broker_reconciled: bool = True,
    ) -> Tuple[EmergencyFlattenStatus, Mapping[str, Decimal]]:
        """Verify whether an emergency flatten intent has achieved authoritative zero exposure.

        Args:
            intent: The active EmergencyFlattenIntent being tracked.
            latest_portfolio_state: Latest authoritative portfolio snapshot.
            is_broker_reconciled: Whether Phase 7 broker reconciliation has succeeded.

        Returns:
            (resulting_status, remaining_open_positions_mapping)
        """
        # Invariant: If broker is disconnected or unreconciled, we cannot declare completion
        if not is_broker_reconciled:
            remaining: dict[str, Decimal] = {}
            for sym, pos in latest_portfolio_state.positions.items():
                if pos.quantity != Decimal("0.0"):
                    remaining[sym] = pos.quantity
            return EmergencyFlattenStatus.FLATTEN_REQUESTED, freeze_mapping(remaining)

        # Inspect all position quantities
        remaining_positions: dict[str, Decimal] = {}
        for sym, pos in latest_portfolio_state.positions.items():
            dec_qty = _verify_finite_decimal(pos.quantity, f"portfolio_state.positions[{sym}].quantity", allow_negative=True)
            if dec_qty != Decimal("0.0"):
                remaining_positions[sym] = dec_qty

        # Verify gross exposure
        gross_exp = latest_portfolio_state.gross_exposure
        if not gross_exp.is_finite() or gross_exp < Decimal("0.0"):
            raise DataContractError(f"Invalid gross_exposure '{gross_exp}' in PortfolioState.")

        if len(remaining_positions) == 0 and gross_exp == Decimal("0.0"):
            return EmergencyFlattenStatus.FLATTEN_COMPLETED, freeze_mapping({})

        # Remaining exposure exists -> NOT COMPLETED (still FLATTEN_REQUESTED)
        return EmergencyFlattenStatus.FLATTEN_REQUESTED, freeze_mapping(remaining_positions)

    @classmethod
    def generate_residual_intent(
        cls,
        parent_intent: EmergencyFlattenIntent,
        latest_portfolio_state: PortfolioState,
        as_of: Optional[datetime] = None,
    ) -> Optional[EmergencyFlattenIntent]:
        """Generate a follow-up flatten intent for residual positions if partial fills occurred."""
        now = _ensure_utc(as_of or datetime.now(timezone.utc))

        target_positions: dict[str, Decimal] = {}
        closing_deltas: dict[str, Decimal] = {}

        for sym, pos in latest_portfolio_state.positions.items():
            clean_sym = sym.strip().upper()
            curr_qty = _verify_finite_decimal(pos.quantity, f"positions[{clean_sym}].quantity", allow_negative=True)
            if curr_qty != Decimal("0.0"):
                target_positions[clean_sym] = Decimal("0.0")
                closing_deltas[clean_sym] = -curr_qty

        if not target_positions:
            return None  # No residual exposure to flatten

        residual_id = f"FLATTEN_RESIDUAL_{parent_intent.intent_id}_{int(now.timestamp() * 1000)}"
        return EmergencyFlattenIntent(
            intent_id=residual_id,
            kill_switch_event_id=parent_intent.kill_switch_event_id,
            target_positions=target_positions,
            closing_deltas=closing_deltas,
            issued_at_utc=now,
            status=EmergencyFlattenStatus.FLATTEN_REQUESTED,
        )
