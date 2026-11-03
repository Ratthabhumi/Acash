"""Read-only reconciliation of broker evidence against the opening baseline and the journal.

This module answers one question per piece of Owner evidence: *is this already inside what ACASH
knows, or is it a gap that needs an Owner decision?* It never writes a file, never edits the
snapshot, baseline or journal, and never turns a broker screenshot into a market price.

Terms kept strictly apart:

- **Opening baseline** — quantities frozen from the saved snapshot at the first recorded event.
- **Journal event** — a completed trade the Owner recorded afterwards (ODR-005).
- **Broker observation** — a screen reading at a timestamp; evidence, not a canonical price.
- **Cash scope** — Dime! FCD and the securities account are different balance sheets; this module
  never transfers between them and never books a debit from an order that predates the baseline.

Precision policy: the quantity a broker order displays and the quantity the holdings screen
displays are both preserved verbatim. A difference at display precision (<= 1e-7 shares) is
reported as ``DISPLAY_PRECISION_DIFFERENCE``; it is never rounded away or silently reconciled.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# A broker order and a holdings screen may print the same fractional position at different display
# precision. Anything at or below this is a display artefact, not a position difference.
DISPLAY_TOLERANCE = Decimal("1e-7")
PRECISION_POLICY = "PRESERVE_BOTH; differences <= 1e-7 shares are reported, never rounded"
CASH_SCOPE_POLICY = "FCD_AND_SECURITIES_CASH_ARE_SEPARATE; no transfer is inferred"

IN_BASELINE = "PRE_BASELINE_IN_BASELINE"
BASELINE_OMITTED = "OPENING_BASELINE_POSITION_OMITTED"
IN_JOURNAL = "POST_BASELINE_IN_JOURNAL"
POST_BASELINE_MISSING = "POST_BASELINE_MISSING"
PENDING = "POSITION_RECONCILIATION_PENDING"

EXACT = "EXACT_MATCH"
DISPLAY_DIFFERENCE = "DISPLAY_PRECISION_DIFFERENCE"
SUBSTANTIVE = "SUBSTANTIVE_DIFFERENCE"


@dataclass(frozen=True)
class OrderEvidence:
    """One completed broker order, as read from the broker's own history screen."""

    order_id: str
    portfolio: str
    security_id: str
    side: str
    executed_at: datetime
    quantity: Decimal
    price: Decimal
    amount: Decimal
    currency: str
    fee: Optional[Decimal] = None  # None means not established; never assume zero

    @property
    def fee_status(self) -> str:
        return "FEE_ESTABLISHED" if self.fee is not None else "FEE_NOT_ESTABLISHED"


@dataclass(frozen=True)
class HoldingEvidence:
    """One holdings-screen observation: portfolio, security, observed quantity and its timestamp."""

    portfolio: str
    security_id: str
    quantity: Decimal
    observed_at: datetime
    price: Optional[Decimal] = None


@dataclass(frozen=True)
class BaselinePosition:
    account_ref: str
    security_id: str
    quantity: Decimal
    sub_portfolio: Optional[str] = None


def compare_quantities(baseline: Optional[Decimal], observed: Optional[Decimal]) -> Dict[str, Any]:
    """Compare two displayed quantities without rounding either of them."""
    if baseline is None or observed is None:
        return {"status": PENDING, "code": "QUANTITY_EVIDENCE_MISSING",
                "baseline": _s(baseline), "observed": _s(observed), "delta": None}
    delta = observed - baseline
    status = EXACT if delta == 0 else DISPLAY_DIFFERENCE if abs(delta) <= DISPLAY_TOLERANCE else SUBSTANTIVE
    return {"status": status, "code": status, "baseline": _s(baseline), "observed": _s(observed),
            "delta": _s(delta), "policy": PRECISION_POLICY}


def classify_order(order: OrderEvidence, baseline: Sequence[BaselinePosition],
                   journal_order_ids: Sequence[str], cutoff: datetime) -> Dict[str, Any]:
    """Decide where one order belongs: baseline, journal, or an Owner decision.

    A pre-baseline order is evidence of how a position arose; it is never replayed as a new
    economic event and therefore never debits cash a second time.
    """
    ids = set(journal_order_ids)
    held = [p for p in baseline if p.security_id == order.security_id]
    held_quantity = sum((p.quantity for p in held), Decimal(0)) if held else None
    out: Dict[str, Any] = {
        "order_id": order.order_id, "portfolio": order.portfolio, "security_id": order.security_id,
        "side": order.side, "executed_at": order.executed_at.isoformat(),
        "cutoff": cutoff.isoformat(), "pre_baseline": order.executed_at <= cutoff,
        "fee_status": order.fee_status, "cash_effect": "NONE_EVIDENCE_ONLY",
        "evidence_only": True, "requires_owner_confirmation": False,
    }
    if order.order_id in ids:
        out.update(decision=IN_JOURNAL, code=IN_JOURNAL,
                   detail="already recorded; zero new events, zero new cash movement")
        return out
    if order.executed_at <= cutoff:
        if held_quantity is not None:
            out.update(decision=IN_BASELINE, code=IN_BASELINE, baseline_quantity=_s(held_quantity),
                       quantity_check=compare_quantities(held_quantity, order.quantity),
                       detail="the opening baseline already reflects this holding; link as evidence only")
        else:
            out.update(decision=BASELINE_OMITTED, code=BASELINE_OMITTED, baseline_quantity=None,
                       quantity_check=compare_quantities(None, order.quantity),
                       requires_owner_confirmation=True,
                       detail="traded before the cutoff but absent from the baseline: a versioned "
                              "baseline amendment needs the Owner's explicit confirmation")
        return out
    out.update(decision=POST_BASELINE_MISSING, code=POST_BASELINE_MISSING,
               requires_owner_confirmation=True,
               detail="after the cutoff and not in the journal: record it under ODR-005 if confirmed")
    return out


def grouping_change(baseline_securities: Sequence[str], observed_securities: Sequence[str]) -> Dict[str, Any]:
    """Compare security membership of one portfolio (e.g. Newwave four -> five)."""
    before, after = set(baseline_securities), set(observed_securities)
    added, removed = sorted(after - before), sorted(before - after)
    return {"status": "PORTFOLIO_GROUPING_CHANGED" if added or removed else "PORTFOLIO_GROUPING_UNCHANGED",
            "added": added, "removed": removed, "baseline_count": len(before), "observed_count": len(after)}


def plan_baseline_amendment(position: BaselinePosition, observed: HoldingEvidence,
                            cutoffs: datetime) -> Dict[str, Any]:
    """Preview a versioned baseline amendment; never applies it without ``confirmed=True``."""
    return {"kind": "BASELINE_AMENDMENT_PREVIEW", "requires_owner_confirmation": True,
            "applied": False, "account_ref": position.account_ref, "security_id": observed.security_id,
            "observed_at": observed.observed_at.isoformat(), "cutoff": cutoffs.isoformat(),
            "quantity_check": compare_quantities(position.quantity, observed.quantity),
            "cash_effect": "NONE_EVIDENCE_ONLY", "portfolio": observed.portfolio or position.sub_portfolio,
            "note": "the original baseline stays intact; a confirmed amendment is a new versioned record"}


def reconcile(orders: Sequence[OrderEvidence], holdings: Sequence[HoldingEvidence],
              baseline: Sequence[BaselinePosition], journal_order_ids: Sequence[str],
              cutoff: datetime) -> Dict[str, Any]:
    """Sanitized summary: codes and counts only, no balances and no prices."""
    classified = [classify_order(o, baseline, journal_order_ids, cutoff) for o in orders]
    counts: Dict[str, int] = {}
    for row in classified:
        counts[row["decision"]] = counts.get(row["decision"], 0) + 1
    observations: List[Dict[str, Any]] = []
    for h in holdings:
        held = [p for p in baseline if p.security_id == h.security_id]
        base_quantity = sum((p.quantity for p in held), Decimal(0)) if held else None
        observations.append({"portfolio": h.portfolio, "security_id": h.security_id,
                             "observed_at": h.observed_at.isoformat(),
                             "quantity_check": compare_quantities(base_quantity, h.quantity),
                             "in_baseline": bool(held)})
    pending = [row for row in classified if row["requires_owner_confirmation"]]
    return {"status": PENDING if pending or any(o["quantity_check"]["status"] != EXACT for o in observations)
            else "RECONCILED", "decisions": classified, "decision_counts": counts,
            "observations": observations, "pending_owner_confirmation": [r["order_id"] for r in pending],
            "precision_policy": PRECISION_POLICY, "cash_scope_policy": CASH_SCOPE_POLICY}


def _s(value: Optional[Decimal]) -> Optional[str]:
    return None if value is None else format(value, "f")


def _dt(text: Any) -> datetime:
    if not isinstance(text, str):
        raise ValueError("timestamp required")
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        raise ValueError("timezone required")
    return moment


def _dec(value: Any) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("decimal required") from None
    if not number.is_finite():
        raise ValueError("finite decimal required")
    return number


def _load_evidence(path: Path) -> Dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("evidence document must be an object")
    orders = [OrderEvidence(order_id=str(o["order_id"]), portfolio=str(o["portfolio"]),
                            security_id=str(o["security_id"]), side=str(o["side"]),
                            executed_at=_dt(o["executed_at"]), quantity=_dec(o["quantity"]),
                            price=_dec(o["price"]), amount=_dec(o["amount"]),
                            currency=str(o["currency"]),
                            fee=None if o.get("fee") is None else _dec(o["fee"]))
              for o in doc.get("orders", [])]
    holdings = [HoldingEvidence(portfolio=str(h["portfolio"]), security_id=str(h["security_id"]),
                                quantity=_dec(h["quantity"]), observed_at=_dt(h["observed_at"]))
                for h in doc.get("holdings", [])]
    baseline = [BaselinePosition(account_ref=str(b["account_ref"]), security_id=str(b["security_id"]),
                                 quantity=_dec(b["quantity"]), sub_portfolio=b.get("sub_portfolio"))
                for b in doc.get("baseline", [])]
    cutoff = _dt(doc["cutoff"])
    journal_ids = [str(i) for i in doc.get("journal_order_ids", [])]
    return {"orders": orders, "holdings": holdings, "baseline": baseline,
            "cutoff": cutoff, "journal_order_ids": journal_ids}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Local, sanitized audit: reads an evidence file the Owner prepared and prints codes only."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: python -m acash.invest.reconciliation <evidence.json>")
        return 2
    try:
        evidence = _load_evidence(Path(args[0]))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "EVIDENCE_INVALID", "code": type(exc).__name__}))
        return 2
    summary = reconcile(**evidence)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "RECONCILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
