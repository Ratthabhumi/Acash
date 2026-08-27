"""Unit Tests for Shadow Double-Entry Accounting Ledger and Conservation Invariants (Phase 5)."""

from decimal import Decimal
import pytest

from acash.backtest.accounting import (
    ACCOUNTING_TOLERANCE,
    ShadowAccountingLedger,
)
from acash.data.schema import DataContractError


def test_shadow_accounting_anti_double_counting_invariants() -> None:
    """Verify Balance-Sheet Equity identically matches Performance Attribution Equity across full trade lifecycle."""
    ledger = ShadowAccountingLedger(
        starting_cash=Decimal("100000.00"),
        base_currency="USD",
    )

    # Initial state
    assert ledger.calculate_balance_sheet_equity() == Decimal("100000.00")
    assert ledger.calculate_performance_attribution_equity() == Decimal("100000.00")
    ledger.verify_internal_conservation()

    # Step 1: Open Long 10 @ 5000 with fee $2.00
    realized_pnl1, eq1 = ledger.process_fill(
        symbol="ES.FUT",
        side="BUY",
        fill_price=Decimal("5000.00"),
        fill_qty=Decimal("10.0"),
        fee_paid=Decimal("2.00"),
    )
    assert realized_pnl1 == Decimal("0.0")
    assert ledger.cash_balance == Decimal("100000.00") - Decimal("50000.00") - Decimal("2.00")  # 49998.00
    # Equity = Cash (49998) + Unrealized (10 * 0) = 49998 + 50000 = 99998 (Starting 100000 - Fee 2)
    assert ledger.calculate_balance_sheet_equity() == Decimal("99998.00")
    assert ledger.calculate_performance_attribution_equity() == Decimal("99998.00")
    ledger.verify_internal_conservation()

    # Step 2: Price increases to 5010 -> Unrealized PnL = 10 * 10 = +$100
    ledger.update_market_price("ES.FUT", Decimal("5010.00"))
    assert ledger.positions["ES.FUT"].unrealized_pnl == Decimal("100.00")
    assert ledger.calculate_balance_sheet_equity() == Decimal("100098.00")
    assert ledger.calculate_performance_attribution_equity() == Decimal("100098.00")
    ledger.verify_internal_conservation()

    # Step 3: Partial Close (Sell 6 @ 5010) with fee $1.20
    # Realized PnL = 6 * (5010 - 5000) = +$60.00
    realized_pnl2, eq2 = ledger.process_fill(
        symbol="ES.FUT",
        side="SELL",
        fill_price=Decimal("5010.00"),
        fill_qty=Decimal("6.0"),
        fee_paid=Decimal("1.20"),
    )
    assert realized_pnl2 == Decimal("60.00")
    # Remaining pos: Long 4 @ 5000. Unrealized = 4 * 10 = $40.00.
    # Cumulative realized PnL = $60.00, Cumulative fees = $3.20.
    assert ledger.positions["ES.FUT"].quantity == Decimal("4.0")
    assert ledger.calculate_balance_sheet_equity() == Decimal("100096.80")
    assert ledger.calculate_performance_attribution_equity() == Decimal("100096.80")
    ledger.verify_internal_conservation()

    # Step 4: Reversal from Long 4 to Short 6 (Sell 10 @ 5015) with fee $2.00
    # Closes Long 4 -> Realized PnL = 4 * (5015 - 5000) = +$60.00
    # Opens Short 6 @ 5015
    realized_pnl3, eq3 = ledger.process_fill(
        symbol="ES.FUT",
        side="SELL",
        fill_price=Decimal("5015.00"),
        fill_qty=Decimal("10.0"),
        fee_paid=Decimal("2.00"),
    )
    assert realized_pnl3 == Decimal("60.00")
    assert ledger.positions["ES.FUT"].quantity == Decimal("-6.0")
    assert ledger.positions["ES.FUT"].avg_entry_price == Decimal("5015.00")
    assert ledger.positions["ES.FUT"].unrealized_pnl == Decimal("0.0")

    # Conservation must remain exact
    ledger.verify_internal_conservation()
    assert ledger.calculate_balance_sheet_equity() == ledger.calculate_performance_attribution_equity()


def test_substrate_equity_verification_tolerance() -> None:
    """Verify substrate equity verification allows residuals within 1e-10 and rejects larger discrepancies."""
    ledger = ShadowAccountingLedger(starting_cash=Decimal("100000.00"))

    # Valid matching within tolerance
    residual = ledger.verify_substrate_equity(Decimal("100000.00000000005"))
    assert residual <= ACCOUNTING_TOLERANCE

    # Discrepancy outside tolerance raises DataContractError
    with pytest.raises(DataContractError, match="discrepancy exceeds tolerance"):
        ledger.verify_substrate_equity(Decimal("100001.00"))


def test_invalid_accounting_inputs_raise_contract_error() -> None:
    """Verify invalid cash, side, or negative quantity raises DataContractError."""
    with pytest.raises(DataContractError, match="strictly positive"):
        ShadowAccountingLedger(starting_cash=Decimal("0.0"))

    ledger = ShadowAccountingLedger(starting_cash=Decimal("50000.00"))

    with pytest.raises(DataContractError, match="must be positive"):
        ledger.process_fill("ES.FUT", "BUY", Decimal("5000.00"), Decimal("-1.0"))

    with pytest.raises(DataContractError, match="Invalid fill side"):
        ledger.process_fill("ES.FUT", "HOLD", Decimal("5000.00"), Decimal("1.0"))
