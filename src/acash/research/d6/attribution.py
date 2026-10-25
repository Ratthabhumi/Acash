"""D6 V36 accounting attribution (exact identities; not causal attribution).

Broker: NAV_T = initial + contributions + sum price P&L at open + gross
distributions - withholding - slippage - commissions - regulatory fees.
Household: adds savings at saving-date H.10, FX translation and remittance
frictions. Every decomposition is checked against the modelled wealth.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Mapping

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.accounting import D6Result
from acash.research.d6.funding import FundingPlan

ZERO = Decimal("0")
DECIMAL_DIVISION_TOLERANCE = Decimal("1e-18")


def broker_attribution(
    result: D6Result, initial_nav: Decimal, last_closes: Mapping[str, Decimal]
) -> Dict[str, Decimal]:
    parts: Dict[str, Decimal] = {"initial": initial_nav, "contributions": result.contributed}
    symbols = sorted(set(result.holdings) | {t.symbol for t in result.trades} | {e.symbol for e in result.entitlements})
    slippage = ZERO
    for sym in symbols:
        try:
            value = result.holdings.get(sym, ZERO) * last_closes[sym] if result.holdings.get(sym, ZERO) else ZERO
        except KeyError:
            raise DataContractError(f"ATTRIB_MISSING_LAST_CLOSE: {sym}.") from None
        for t in (t for t in result.trades if t.symbol == sym):
            sign = Decimal(-1) if t.side == "BUY" else Decimal(1)
            value += sign * t.quantity * t.open_price
            slippage += (t.fill_price - t.open_price) * t.quantity * -sign
        parts[f"price_{sym}"] = value
        ents = [e for e in result.entitlements if e.symbol == sym]
        parts[f"distributions_{sym}"] = sum((e.gross for e in ents), ZERO)
        parts[f"withholding_{sym}"] = -sum((e.withheld for e in ents), ZERO)
    parts["slippage"] = -slippage
    parts["commissions"] = -result.commissions
    parts["regulatory_fees"] = -result.regulatory_fees
    if sum(parts.values(), ZERO) != result.terminal_nav:
        raise DataContractError("ATTRIB_BROKER_IDENTITY_FAILED.")
    return parts


def household_attribution(
    plan: FundingPlan,
    broker: Mapping[str, Decimal],
    terminal_nav: Decimal,
    terminal_rate: Decimal,
) -> Dict[str, Decimal]:
    """Household USD wealth = broker NAV + in-transit USD + unremitted THB at the terminal rate."""
    if terminal_rate <= ZERO:
        raise DataContractError("ATTRIB_NONPOSITIVE_TERMINAL_RATE.")
    savings_ref = sum((thb / rate for _, thb, rate in plan.savings), ZERO)
    remitted_at_remit = sum((r.thb_balance / r.rate for r in plan.remittances), ZERO)
    remitted_saved = sum((r.saved_usd_ref for r in plan.remittances), ZERO)
    unremitted_value = plan.unremitted_thb / terminal_rate
    broker_pnl = sum((v for k, v in broker.items() if k not in ("initial", "contributions")), ZERO)
    if plan.scenario.cadence is None:
        fx_translation = ZERO
        frictions = {"sender_fees": ZERO, "fx_spread": ZERO, "intermediary": ZERO, "cent_rounding": ZERO}
    else:
        fx_translation = remitted_at_remit - remitted_saved + unremitted_value - plan.unremitted_saved_usd_ref
        frictions = {
            "sender_fees": -sum((r.sender_fee_usd_ref for r in plan.remittances), ZERO),
            "fx_spread": -sum((r.spread_cost_usd for r in plan.remittances), ZERO),
            "intermediary": -sum((r.intermediary_fee_usd for r in plan.remittances), ZERO),
            "cent_rounding": -sum((r.rounding_usd for r in plan.remittances), ZERO),
        }
    parts = {
        "initial": broker["initial"],
        "savings_at_saving_rate": savings_ref,
        "fx_translation": fx_translation,
        **frictions,
        "broker_pnl": broker_pnl,
    }
    household = terminal_nav + plan.in_transit_usd + unremitted_value
    if abs(sum(parts.values(), ZERO) - household) > DECIMAL_DIVISION_TOLERANCE:
        raise DataContractError("ATTRIB_HOUSEHOLD_IDENTITY_FAILED.")
    parts["household_usd"] = household
    return parts


__all__ = ["broker_attribution", "household_attribution"]
