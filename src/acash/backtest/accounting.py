"""ACASH Independent Double-Entry Shadow Ledger & Accounting Verifier (Phase 5).

Strictly decouples Balance-Sheet View from Performance Attribution View to prevent Realized PnL
double-counting and verifies substrate fills with exact tolerance:
|AccountingResidual| <= 1e-10
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from acash.data.schema import DataContractError


ACCOUNTING_TOLERANCE = Decimal("0.0000000001")  # 1e-10


class ShadowPositionState(BaseModel):
    """Immutable state snapshot of a single instrument position within shadow ledger."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    quantity: Decimal = Decimal("0.0")  # Signed: > 0 Long, < 0 Short
    avg_entry_price: Decimal = Decimal("0.0")
    current_market_price: Decimal = Decimal("0.0")
    multiplier: Decimal = Decimal("1.0")
    realized_pnl: Decimal = Decimal("0.0")  # Cumulative realized PnL for this position
    unrealized_pnl: Decimal = Decimal("0.0")

    @property
    def is_flat(self) -> bool:
        return self.quantity == Decimal("0.0")

    @property
    def position_value(self) -> Decimal:
        """Mark-to-market position value."""
        return self.quantity * self.current_market_price * self.multiplier


class ShadowAccountingLedger:
    """Independent shadow double-entry ledger verifying execution substrate equity and conservation."""

    def __init__(
        self,
        starting_cash: Decimal = Decimal("100000.00"),
        base_currency: str = "USD",
    ) -> None:
        if starting_cash <= Decimal("0.0"):
            raise DataContractError(f"Starting cash must be strictly positive: {starting_cash}")

        self.starting_cash: Decimal = starting_cash
        self.base_currency: str = base_currency

        # State Variables (Balance-Sheet View)
        self.cash_balance: Decimal = starting_cash
        self.positions: Dict[str, ShadowPositionState] = {}

        # Attribution Variables (Performance Attribution View)
        self.cumulative_external_cash_flows: Decimal = Decimal("0.0")
        self.cumulative_realized_pnl: Decimal = Decimal("0.0")
        self.cumulative_fees_paid: Decimal = Decimal("0.0")
        self.cumulative_financing_costs: Decimal = Decimal("0.0")

    # ---------------------------------------------------------------------
    # Dual Accounting Views
    # ---------------------------------------------------------------------

    def calculate_balance_sheet_equity(self) -> Decimal:
        """View A: Balance-Sheet (State Snapshot) View.

        Equity = CashBalance + sum(Mark-to-Market Position Value).
        """
        total_pos_value = sum((pos.position_value for pos in self.positions.values()), Decimal("0.0"))
        return self.cash_balance + total_pos_value

    def calculate_performance_attribution_equity(self) -> Decimal:
        """View B: Performance Attribution (Flow Reconciliation) View.

        Equity = Starting Equity + Cash Flows + Realized PnL + Unrealized PnL - Fees - Financing.
        """
        total_unrealized = sum((pos.unrealized_pnl for pos in self.positions.values()), Decimal("0.0"))
        return (
            self.starting_cash
            + self.cumulative_external_cash_flows
            + self.cumulative_realized_pnl
            + total_unrealized
            - self.cumulative_fees_paid
            - self.cumulative_financing_costs
        )

    def verify_internal_conservation(self) -> None:
        """Enforce Anti-Double-Counting Invariant: Balance-Sheet Equity == Performance Attribution Equity."""
        eq_bs = self.calculate_balance_sheet_equity()
        eq_pa = self.calculate_performance_attribution_equity()
        discrepancy = abs(eq_bs - eq_pa)

        if discrepancy > ACCOUNTING_TOLERANCE:
            raise DataContractError(
                f"Double-entry accounting conservation violation: "
                f"Balance-Sheet Equity ({eq_bs}) != Performance Attribution Equity ({eq_pa}), "
                f"Discrepancy: {discrepancy} > {ACCOUNTING_TOLERANCE}"
            )

    def verify_substrate_equity(self, substrate_equity: Decimal) -> Decimal:
        """Verify substrate equity against shadow ledger within tolerance."""
        acash_equity = self.calculate_balance_sheet_equity()
        residual = abs(acash_equity - substrate_equity)

        if residual > ACCOUNTING_TOLERANCE:
            raise DataContractError(
                f"Substrate accounting discrepancy exceeds tolerance: "
                f"ACASH Equity ({acash_equity}) - Substrate Equity ({substrate_equity}) = {residual} > {ACCOUNTING_TOLERANCE}"
            )
        return residual

    # ---------------------------------------------------------------------
    # Market Price Updates & Fill Processing
    # ---------------------------------------------------------------------

    def update_market_price(self, symbol: str, market_price: Decimal) -> None:
        """Revalue unrealized PnL of open position with current market price."""
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        if pos.is_flat:
            new_unrealized = Decimal("0.0")
        else:
            # Unrealized PnL = quantity * (current_market_price - avg_entry_price) * multiplier
            new_unrealized = pos.quantity * (market_price - pos.avg_entry_price) * pos.multiplier

        self.positions[symbol] = pos.model_copy(
            update={
                "current_market_price": market_price,
                "unrealized_pnl": new_unrealized,
            }
        )
        self.verify_internal_conservation()

    def process_fill(
        self,
        symbol: str,
        side: str,
        fill_price: Decimal,
        fill_qty: Decimal,
        fee_paid: Decimal = Decimal("0.0"),
        multiplier: Decimal = Decimal("1.0"),
    ) -> Tuple[Decimal, Decimal]:
        """Process execution fill using signed-quantity position arithmetic with multiplier support.

        Returns:
            Tuple[realized_pnl_delta, new_equity]
        """
        if fill_qty <= Decimal("0.0"):
            raise DataContractError(f"Fill quantity must be positive: {fill_qty}")
        if fill_price <= Decimal("0.0"):
            raise DataContractError(f"Fill price must be positive: {fill_price}")
        if fee_paid < Decimal("0.0"):
            raise DataContractError(f"Fee paid cannot be negative: {fee_paid}")
        if multiplier <= Decimal("0.0"):
            raise DataContractError(f"Multiplier must be positive: {multiplier}")

        side_upper = side.upper()
        if side_upper not in ("BUY", "SELL"):
            raise DataContractError(f"Invalid fill side: {side}")

        # Determine signed fill delta
        signed_qty_delta = fill_qty if side_upper == "BUY" else -fill_qty

        # Get existing position state
        pos = self.positions.get(
            symbol,
            ShadowPositionState(
                symbol=symbol,
                quantity=Decimal("0.0"),
                avg_entry_price=Decimal("0.0"),
                current_market_price=fill_price,
                multiplier=multiplier,
                realized_pnl=Decimal("0.0"),
                unrealized_pnl=Decimal("0.0"),
            ),
        )

        old_qty = pos.quantity
        new_qty = old_qty + signed_qty_delta
        realized_pnl_delta = Decimal("0.0")

        # -----------------------------------------------------------------
        # Scenario Arithmetic (Signed 8-Scenario Alignment with Phase 1)
        # -----------------------------------------------------------------
        if old_qty == Decimal("0.0"):
            # Scenario 1: Opening new position from flat
            new_avg_entry = fill_price
            self.cash_balance -= (signed_qty_delta * fill_price * multiplier) + fee_paid

        elif (old_qty > 0 and signed_qty_delta > 0) or (old_qty < 0 and signed_qty_delta < 0):
            # Scenario 2: Increasing existing position in same direction
            total_cost = (abs(old_qty) * pos.avg_entry_price) + (fill_qty * fill_price)
            new_avg_entry = total_cost / abs(new_qty)
            self.cash_balance -= (signed_qty_delta * fill_price * multiplier) + fee_paid

        elif (old_qty > 0 and signed_qty_delta < 0) or (old_qty < 0 and signed_qty_delta > 0):
            # Reducing or reversing existing position
            closed_qty = min(abs(old_qty), fill_qty)

            if old_qty > 0:
                # Closing Long
                realized_pnl_delta = closed_qty * (fill_price - pos.avg_entry_price) * multiplier
            else:
                # Closing Short
                realized_pnl_delta = closed_qty * (pos.avg_entry_price - fill_price) * multiplier

            if abs(new_qty) == Decimal("0.0"):
                # Scenario 3: Exact position closing to flat
                new_avg_entry = Decimal("0.0")
            elif (old_qty > 0 and new_qty > 0) or (old_qty < 0 and new_qty < 0):
                # Scenario 4: Partial reduction
                new_avg_entry = pos.avg_entry_price
            else:
                # Scenario 5: Full reversal (e.g. Long 10 -> Sell 15 -> Short 5)
                new_avg_entry = fill_price

            # Cash flow: return capital of closed portion + realized PnL - new opening cost - fee
            self.cash_balance -= (signed_qty_delta * fill_price * multiplier) + fee_paid

        else:
            new_avg_entry = fill_price
            self.cash_balance -= (signed_qty_delta * fill_price * multiplier) + fee_paid

        # Update attribution trackers
        self.cumulative_realized_pnl += realized_pnl_delta
        self.cumulative_fees_paid += fee_paid

        # Revalue unrealized PnL
        new_unrealized = Decimal("0.0") if new_qty == Decimal("0.0") else new_qty * (fill_price - new_avg_entry) * multiplier

        self.positions[symbol] = ShadowPositionState(
            symbol=symbol,
            quantity=new_qty,
            avg_entry_price=new_avg_entry,
            current_market_price=fill_price,
            multiplier=multiplier,
            realized_pnl=pos.realized_pnl + realized_pnl_delta,
            unrealized_pnl=new_unrealized,
        )

        # Enforce conservation invariant
        self.verify_internal_conservation()

        return realized_pnl_delta, self.calculate_balance_sheet_equity()
