"""ACASH Paper Trading — Reconciliation Engine.

PaperReconciliationEngine cross-checks:
    Journal events ↔ Order records ↔ Fill records ↔ Portfolio state

Detects:
- Missing events (sequence gaps, missing layer coverage)
- Duplicate IDs (order_id, fill_id)
- Orphan fills (fill without a matching order)
- Orphan orders (order with no subsequent state transition)
- Position mismatch (journal fills ≠ portfolio position)
- Cash mismatch (fills + fees ≠ portfolio cash change)
- Hash chain failures (reported from journal.verify_integrity())

Reconciliation failure MUST be visible — never silently repair historical records.

This module is READ-ONLY with respect to the journal and portfolio state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from acash.paper.journal import JournalEvent, JournalEventType, JournalLayer, PaperEventJournal


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ReconciliationStatus(str, Enum):
    """Outcome of a reconciliation check."""

    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"   # Some checks passed, some failed
    NOT_RUN = "NOT_RUN"


# ---------------------------------------------------------------------------
# ReconciliationResult
# ---------------------------------------------------------------------------


@dataclass
class ReconciliationResult:
    """Result of a full reconciliation run."""

    status: ReconciliationStatus
    run_at_utc: datetime
    session_id: str

    # Counts
    total_events_checked: int = 0
    total_orders_checked: int = 0
    total_fills_checked: int = 0
    total_violations: int = 0

    # Violations — structured, never silently suppressed
    sequence_gaps: List[str] = field(default_factory=list)
    duplicate_event_ids: List[str] = field(default_factory=list)
    duplicate_order_ids: List[str] = field(default_factory=list)
    duplicate_fill_ids: List[str] = field(default_factory=list)
    orphan_fills: List[str] = field(default_factory=list)      # fill without order
    orphan_orders: List[str] = field(default_factory=list)     # order never filled/cancelled
    hash_chain_violations: List[str] = field(default_factory=list)
    position_mismatches: List[str] = field(default_factory=list)
    cash_mismatches: List[str] = field(default_factory=list)
    missing_layer_events: List[str] = field(default_factory=list)
    other_violations: List[str] = field(default_factory=list)

    def to_summary(self) -> Dict[str, Any]:
        """Return a concise summary for logging/journal."""
        return {
            "status": self.status.value,
            "run_at_utc": self.run_at_utc.isoformat(),
            "session_id": self.session_id,
            "total_events_checked": self.total_events_checked,
            "total_orders_checked": self.total_orders_checked,
            "total_fills_checked": self.total_fills_checked,
            "total_violations": self.total_violations,
            "sequence_gaps": self.sequence_gaps,
            "duplicate_event_ids": self.duplicate_event_ids,
            "hash_chain_violations": self.hash_chain_violations,
            "orphan_fills": self.orphan_fills,
            "orphan_orders": self.orphan_orders,
            "position_mismatches": self.position_mismatches,
            "cash_mismatches": self.cash_mismatches,
        }


# ---------------------------------------------------------------------------
# PaperReconciliationEngine
# ---------------------------------------------------------------------------


class PaperReconciliationEngine:
    """Cross-validate journal events against fill and position records.

    All methods are READ-ONLY. This engine NEVER modifies journal state.
    Violations are reported, never silently repaired.
    """

    def __init__(self, session_id: str, journal: PaperEventJournal) -> None:
        if not session_id or not session_id.strip():
            raise ValueError("PaperReconciliationEngine: session_id must be non-empty.")
        self._session_id = session_id
        self._journal = journal

    def run_full_reconciliation(
        self,
        *,
        expected_order_ids: Optional[Set[str]] = None,
        expected_fill_ids: Optional[Set[str]] = None,
        expected_net_position: Optional[Decimal] = None,
        expected_cash_change: Optional[Decimal] = None,
        cash_tolerance: Decimal = Decimal("0.01"),
        position_tolerance: Decimal = Decimal("0.0001"),
    ) -> ReconciliationResult:
        """Run all reconciliation checks and return a consolidated result.

        Args:
            expected_order_ids: Set of order IDs expected to appear in journal.
            expected_fill_ids: Set of fill IDs expected to appear in journal.
            expected_net_position: Expected net position from portfolio state.
            expected_cash_change: Expected net cash change from fills + fees.
            cash_tolerance: Decimal tolerance for cash mismatch check.
            position_tolerance: Decimal tolerance for position mismatch check.
        """
        now_utc = datetime.now(timezone.utc)
        result = ReconciliationResult(
            status=ReconciliationStatus.NOT_RUN,
            run_at_utc=now_utc,
            session_id=self._session_id,
        )

        events = self._journal.read_all()
        result.total_events_checked = len(events)

        # 1. Hash chain integrity
        chain_violations = self._journal.verify_integrity()
        result.hash_chain_violations.extend(chain_violations)

        # 2. Sequence gaps
        result.sequence_gaps.extend(self._check_sequence_gaps(events))

        # 3. Duplicate event IDs
        result.duplicate_event_ids.extend(self._check_duplicate_event_ids(events))

        # 4. Extract order and fill events
        order_events = [
            e for e in events if e.layer == JournalLayer.ORDER
        ]
        fill_events = [
            e for e in events if e.layer == JournalLayer.EXECUTION
        ]
        result.total_orders_checked = len(order_events)
        result.total_fills_checked = len(fill_events)

        # 5. Duplicate order IDs from journal
        result.duplicate_order_ids.extend(
            self._check_duplicate_payload_ids(order_events, "order_intent_id")
        )

        # 6. Duplicate fill IDs from journal
        result.duplicate_fill_ids.extend(
            self._check_duplicate_payload_ids(fill_events, "fill_id")
        )

        # 7. Orphan fills (fill → no matching order intent)
        seen_intent_ids = self._collect_payload_values(order_events, "order_intent_id")
        for fe in fill_events:
            ref_intent = fe.payload.get("order_intent_id") or fe.payload.get("intent_id")
            if ref_intent and ref_intent not in seen_intent_ids:
                result.orphan_fills.append(
                    f"Fill event {fe.event_id} references unknown order_intent_id={ref_intent}"
                )

        # 8. Orphan orders (order created but no fill/cancel/reject terminal event)
        result.orphan_orders.extend(self._check_orphan_orders(events))

        # 9. Position mismatch (if expected value given)
        if expected_net_position is not None:
            pos_violations = self._check_position_from_fills(
                fill_events, expected_net_position, position_tolerance
            )
            result.position_mismatches.extend(pos_violations)

        # 10. Cash mismatch (if expected value given)
        if expected_cash_change is not None:
            cash_violations = self._check_cash_from_fills(
                fill_events, expected_cash_change, cash_tolerance
            )
            result.cash_mismatches.extend(cash_violations)

        # 11. Cross-check expected IDs
        if expected_order_ids is not None:
            journal_intent_ids = self._collect_payload_values(
                order_events, "order_intent_id"
            )
            for oid in expected_order_ids:
                if oid not in journal_intent_ids:
                    result.missing_layer_events.append(
                        f"Expected order_intent_id {oid!r} not found in journal."
                    )

        if expected_fill_ids is not None:
            journal_fill_ids = self._collect_payload_values(fill_events, "fill_id")
            for fid in expected_fill_ids:
                if fid not in journal_fill_ids:
                    result.missing_layer_events.append(
                        f"Expected fill_id {fid!r} not found in journal."
                    )

        # Tally violations
        all_violations = (
            result.hash_chain_violations
            + result.sequence_gaps
            + result.duplicate_event_ids
            + result.duplicate_order_ids
            + result.duplicate_fill_ids
            + result.orphan_fills
            + result.orphan_orders
            + result.position_mismatches
            + result.cash_mismatches
            + result.missing_layer_events
            + result.other_violations
        )
        result.total_violations = len(all_violations)

        if result.total_violations == 0:
            result.status = ReconciliationStatus.PASS
        else:
            result.status = ReconciliationStatus.FAIL

        return result

    # ------------------------------------------------------------------
    # Private checks
    # ------------------------------------------------------------------

    def _check_sequence_gaps(self, events: List[JournalEvent]) -> List[str]:
        violations: List[str] = []
        expected = 0
        for ev in events:
            if ev.sequence != expected:
                violations.append(
                    f"Sequence gap: expected {expected}, got {ev.sequence} "
                    f"(event_id={ev.event_id})"
                )
            expected += 1
        return violations

    def _check_duplicate_event_ids(self, events: List[JournalEvent]) -> List[str]:
        seen: Set[str] = set()
        violations: List[str] = []
        for ev in events:
            if ev.event_id in seen:
                violations.append(f"Duplicate event_id: {ev.event_id}")
            seen.add(ev.event_id)
        return violations

    def _check_duplicate_payload_ids(
        self,
        events: List[JournalEvent],
        field_name: str,
    ) -> List[str]:
        seen: Set[str] = set()
        violations: List[str] = []
        for ev in events:
            val = ev.payload.get(field_name)
            if val is None:
                continue
            val_str = str(val)
            if val_str in seen:
                violations.append(
                    f"Duplicate {field_name}={val_str!r} in event {ev.event_id}"
                )
            seen.add(val_str)
        return violations

    def _collect_payload_values(
        self, events: List[JournalEvent], field_name: str
    ) -> Set[str]:
        result: Set[str] = set()
        for ev in events:
            val = ev.payload.get(field_name)
            if val is not None:
                result.add(str(val))
        return result

    def _check_orphan_orders(self, events: List[JournalEvent]) -> List[str]:
        """Find order intents with no terminal event (FILLED, CANCELLED, REJECTED)."""
        TERMINAL_TYPES = {
            JournalEventType.ORDER_REJECTED,
            JournalEventType.ORDER_CANCELLED,
            JournalEventType.ORDER_EXPIRED,
            JournalEventType.ORDER_FAILED,
            JournalEventType.FILL_SIMULATED,
            JournalEventType.PARTIAL_FILL_SIMULATED,
        }

        intent_ids: Dict[str, str] = {}  # intent_id → event_id
        terminated: Set[str] = set()

        for ev in events:
            if ev.event_type == JournalEventType.ORDER_INTENT_CREATED:
                iid = ev.payload.get("order_intent_id")
                if iid:
                    intent_ids[str(iid)] = ev.event_id

            if ev.event_type in TERMINAL_TYPES:
                iid = ev.payload.get("order_intent_id") or ev.payload.get("intent_id")
                if iid:
                    terminated.add(str(iid))

        # Fill events also mark termination via correlation_id matching
        violations: List[str] = []
        non_terminated = set(intent_ids.keys()) - terminated
        for iid in non_terminated:
            violations.append(
                f"Order intent {iid!r} has no terminal event (FILLED/CANCELLED/REJECTED/FAILED)"
            )
        return violations

    def _check_position_from_fills(
        self,
        fill_events: List[JournalEvent],
        expected_net_position: Decimal,
        tolerance: Decimal,
    ) -> List[str]:
        """Reconstruct net position from fill events and compare to expected."""
        net = Decimal("0")
        for fe in fill_events:
            qty = fe.payload.get("quantity") or fe.payload.get("fill_quantity")
            side = fe.payload.get("side") or fe.payload.get("order_side", "BUY")
            if qty is None:
                continue
            qty_d = Decimal(str(qty))
            if str(side).upper() in ("BUY", "LONG"):
                net += qty_d
            else:
                net -= qty_d

        diff = abs(net - expected_net_position)
        if diff > tolerance:
            return [
                f"Position mismatch: journal_reconstructed={net}, "
                f"expected={expected_net_position}, diff={diff} (tol={tolerance})"
            ]
        return []

    def _check_cash_from_fills(
        self,
        fill_events: List[JournalEvent],
        expected_cash_change: Decimal,
        tolerance: Decimal,
    ) -> List[str]:
        """Reconstruct net cash change from fills and fees."""
        total_cost = Decimal("0")
        for fe in fill_events:
            notional = fe.payload.get("fill_notional") or Decimal("0")
            fees = fe.payload.get("fees") or Decimal("0")
            total_cost += Decimal(str(notional)) + Decimal(str(fees))

        diff = abs(total_cost - abs(expected_cash_change))
        if diff > tolerance:
            return [
                f"Cash mismatch: journal_reconstructed={total_cost}, "
                f"expected={expected_cash_change}, diff={diff} (tol={tolerance})"
            ]
        return []
