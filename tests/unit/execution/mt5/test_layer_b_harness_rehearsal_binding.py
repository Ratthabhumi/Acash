"""Unit regression test suite for Phase 13 Layer B Harness Rehearsal Binding.

Verifies:
1. B-2 Multi-position shadowing regression:
   - When multiple position lifecycles exist in broker history (Position A older, Position B newer),
     querying exit deal for Position A strictly returns Exit A bound to Position A's lifecycle,
     NEVER Exit B (even though Exit B is newer/later).
2. B-2 Fail-closed invariant on missing exit deal:
   - If no exit deal exists matching entry deal's position_ticket, select_authoritative_exit_deal
     fails closed with DataContractError immediately.
3. B-1 Canonical A-3 Intent & 4-Tier Lifecycle Invariant:
   - Harness constants strictly define CANONICAL_A3_INTENT = "INT_DEMO_A3_1788516518".
   - validate_a3_lifecycle_binding validates the complete 4-tier relationship:
     intent_id -> deal_ticket -> order_ticket -> position_ticket.
   - Any mutation (off-by-one intent, wrong deal, wrong order, wrong position) strictly fails closed.
   - Frozen layer_b_evidence_a3.json contains exact matching canonical identifiers.
4. B-2 Deterministic multiple exit deal tie-breaking:
   - If multiple exit deals match the position lifecycle, the latest authoritative exit deal
     is deterministically selected via (deal_time_utc ms, deal_ticket) ascending sort.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Sequence

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.execution.mt5.enums import MT5DealEntry, MT5DealType
from acash.execution.mt5.schemas import MT5DealReality
from scripts.phase13_layer_b_harness import (
    CANONICAL_A3_DEAL_TICKET,
    CANONICAL_A3_INTENT,
    CANONICAL_A3_ORDER_TICKET,
    CANONICAL_A3_POSITION_TICKET,
    select_authoritative_exit_deal,
    validate_a3_lifecycle_binding,
)


def _make_deal(
    *,
    deal_ticket: int,
    order_ticket: int,
    position_ticket: int,
    symbol: str = "EURUSD",
    deal_type: MT5DealType = MT5DealType.DEAL_TYPE_BUY,
    volume: Decimal = Decimal("0.01"),
    price: Decimal = Decimal("1.16282"),
    deal_time_utc: datetime,
    comment: str = "",
) -> MT5DealReality:
    return MT5DealReality(
        deal_ticket=deal_ticket,
        order_ticket=order_ticket,
        position_ticket=position_ticket,
        symbol=symbol,
        deal_type=deal_type,
        volume=volume,
        price=price,
        commission=Decimal("0.0"),
        fee=Decimal("0.0"),
        swap=Decimal("0.0"),
        profit=Decimal("0.0"),
        deal_time_utc=deal_time_utc,
        comment=comment,
        magic=13001,
        entry=MT5DealEntry.DEAL_ENTRY_IN if deal_type == MT5DealType.DEAL_TYPE_BUY else MT5DealEntry.DEAL_ENTRY_OUT,
    )


class TestLayerBHarnessRehearsalBinding:
    """Regression test suite for B-1 and B-2 harness bindings."""

    def test_scenario_1_multi_position_shadowing_regression(self) -> None:
        """B-2 Regression: Position A query returns Exit A, NOT newer Exit B.

        Historical EURUSD trade history scenario:
        - Position A (older):
            Entry A: ticket 10071863196, pos 10355518139, time T0
            Exit A:  ticket 10073606868, pos 10355518139, time T1
        - Position B (newer):
            Entry B: ticket 20000000002, pos 20000000001, time T2
            Exit B:  ticket 20000000003, pos 20000000001, time T3
        """
        t0 = datetime(2026, 9, 4, 8, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 9, 4, 9, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 9, 4, 11, 0, 0, tzinfo=timezone.utc)

        entry_a = _make_deal(
            deal_ticket=10071863196,
            order_ticket=10355518139,
            position_ticket=10355518139,
            deal_type=MT5DealType.DEAL_TYPE_BUY,
            deal_time_utc=t0,
        )
        exit_a = _make_deal(
            deal_ticket=10073606868,
            order_ticket=10355518139,
            position_ticket=10355518139,
            deal_type=MT5DealType.DEAL_TYPE_SELL,
            deal_time_utc=t1,
        )
        entry_b = _make_deal(
            deal_ticket=20000000002,
            order_ticket=20000000001,
            position_ticket=20000000001,
            deal_type=MT5DealType.DEAL_TYPE_BUY,
            deal_time_utc=t2,
        )
        exit_b = _make_deal(
            deal_ticket=20000000003,
            order_ticket=20000000001,
            position_ticket=20000000001,
            deal_type=MT5DealType.DEAL_TYPE_SELL,
            deal_time_utc=t3,
        )

        all_deals: Sequence[MT5DealReality] = (entry_a, exit_a, entry_b, exit_b)

        # Querying exit deal for Position A MUST return Exit A, NEVER Exit B
        selected_exit_a = select_authoritative_exit_deal(entry_a, all_deals)
        assert selected_exit_a.deal_ticket == exit_a.deal_ticket
        assert selected_exit_a.position_ticket == entry_a.position_ticket
        assert selected_exit_a.deal_ticket != exit_b.deal_ticket

        # Querying exit deal for Position B MUST return Exit B
        selected_exit_b = select_authoritative_exit_deal(entry_b, all_deals)
        assert selected_exit_b.deal_ticket == exit_b.deal_ticket
        assert selected_exit_b.position_ticket == entry_b.position_ticket

    def test_scenario_2_missing_exit_fails_closed(self) -> None:
        """B-2 Invariant: Missing exit deal for position lifecycle fails closed."""
        t0 = datetime(2026, 9, 4, 8, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 9, 4, 9, 0, 0, tzinfo=timezone.utc)

        entry_a = _make_deal(
            deal_ticket=10071863196,
            order_ticket=10355518139,
            position_ticket=10355518139,
            deal_type=MT5DealType.DEAL_TYPE_BUY,
            deal_time_utc=t0,
        )
        # Only deals for an unrelated position exist in history
        unrelated_exit = _make_deal(
            deal_ticket=99999999999,
            order_ticket=88888888888,
            position_ticket=88888888888,
            deal_type=MT5DealType.DEAL_TYPE_SELL,
            deal_time_utc=t1,
        )

        with pytest.raises(DataContractError, match="No exit deal found matching position lifecycle 10355518139"):
            select_authoritative_exit_deal(entry_a, (entry_a, unrelated_exit))

    def test_scenario_3_canonical_a3_intent_and_lifecycle_invariant(self) -> None:
        """B-1 Invariant: A-11 harness uses canonical INT_DEMO_A3_1788516518 and validates 4-tier lifecycle."""
        # 1. Exact identifier equality constants
        assert CANONICAL_A3_INTENT == "INT_DEMO_A3_1788516518"
        assert CANONICAL_A3_DEAL_TICKET == 10071863196
        assert CANONICAL_A3_ORDER_TICKET == 10355518139
        assert CANONICAL_A3_POSITION_TICKET == 10355518139

        t0 = datetime(2026, 9, 4, 8, 29, 55, tzinfo=timezone.utc)
        valid_entry = _make_deal(
            deal_ticket=CANONICAL_A3_DEAL_TICKET,
            order_ticket=CANONICAL_A3_ORDER_TICKET,
            position_ticket=CANONICAL_A3_POSITION_TICKET,
            deal_type=MT5DealType.DEAL_TYPE_BUY,
            deal_time_utc=t0,
        )

        # 2. Nominal validation passes
        validate_a3_lifecycle_binding(valid_entry, CANONICAL_A3_INTENT)

        # 3. Off-by-one intent mismatch fails closed
        with pytest.raises(DataContractError, match="Intent lineage mismatch"):
            validate_a3_lifecycle_binding(valid_entry, "INT_DEMO_A3_1788516517")

        # 4. Mutated deal ticket fails closed
        mutated_deal = _make_deal(
            deal_ticket=99999999999,
            order_ticket=CANONICAL_A3_ORDER_TICKET,
            position_ticket=CANONICAL_A3_POSITION_TICKET,
            deal_type=MT5DealType.DEAL_TYPE_BUY,
            deal_time_utc=t0,
        )
        with pytest.raises(DataContractError, match="Entry deal ticket mismatch"):
            validate_a3_lifecycle_binding(mutated_deal, CANONICAL_A3_INTENT)

        # 5. Mutated order ticket fails closed
        mutated_order = _make_deal(
            deal_ticket=CANONICAL_A3_DEAL_TICKET,
            order_ticket=99999999999,
            position_ticket=CANONICAL_A3_POSITION_TICKET,
            deal_type=MT5DealType.DEAL_TYPE_BUY,
            deal_time_utc=t0,
        )
        with pytest.raises(DataContractError, match="Entry order ticket mismatch"):
            validate_a3_lifecycle_binding(mutated_order, CANONICAL_A3_INTENT)

        # 6. Mutated position ticket fails closed
        mutated_pos = _make_deal(
            deal_ticket=CANONICAL_A3_DEAL_TICKET,
            order_ticket=CANONICAL_A3_ORDER_TICKET,
            position_ticket=99999999999,
            deal_type=MT5DealType.DEAL_TYPE_BUY,
            deal_time_utc=t0,
        )
        with pytest.raises(DataContractError, match="Entry position ticket mismatch"):
            validate_a3_lifecycle_binding(mutated_pos, CANONICAL_A3_INTENT)

        # 7. Cross-check against frozen layer_b_evidence_a3.json
        a3_path = Path("docs/phase13/layer_b_evidence_a3.json")
        assert a3_path.exists(), "layer_b_evidence_a3.json must exist"
        a3_data = json.loads(a3_path.read_text(encoding="utf-8"))
        assert a3_data["intent_id"] == CANONICAL_A3_INTENT
        assert a3_data["deal_ticket"] == CANONICAL_A3_DEAL_TICKET
        assert a3_data["order_ticket"] == CANONICAL_A3_ORDER_TICKET

    def test_scenario_4_deterministic_multiple_exit_selection(self) -> None:
        """B-2 Determinism: Multiple exits for same position lifecycle select latest authoritative exit."""
        t0 = datetime(2026, 9, 4, 8, 0, 0, tzinfo=timezone.utc)
        t_exit1 = datetime(2026, 9, 4, 8, 30, 0, tzinfo=timezone.utc)
        t_exit2 = datetime(2026, 9, 4, 8, 45, 0, tzinfo=timezone.utc)

        entry = _make_deal(
            deal_ticket=10071863196,
            order_ticket=10355518139,
            position_ticket=10355518139,
            deal_type=MT5DealType.DEAL_TYPE_BUY,
            deal_time_utc=t0,
        )
        # Partial close 1 (earlier)
        exit_early = _make_deal(
            deal_ticket=10073000001,
            order_ticket=10355518139,
            position_ticket=10355518139,
            deal_type=MT5DealType.DEAL_TYPE_SELL,
            volume=Decimal("0.005"),
            deal_time_utc=t_exit1,
        )
        # Final close 2 (later)
        exit_latest = _make_deal(
            deal_ticket=10073000002,
            order_ticket=10355518139,
            position_ticket=10355518139,
            deal_type=MT5DealType.DEAL_TYPE_SELL,
            volume=Decimal("0.005"),
            deal_time_utc=t_exit2,
        )

        # Even if passed in reverse order, deterministic sorting must return the latest exit
        deals_reversed = (exit_latest, entry, exit_early)
        selected = select_authoritative_exit_deal(entry, deals_reversed)
        assert selected.deal_ticket == exit_latest.deal_ticket
        assert selected.deal_time_utc == t_exit2

        # Tie-breaking with same timestamp: higher deal ticket wins
        exit_tie1 = _make_deal(
            deal_ticket=10073000010,
            order_ticket=10355518139,
            position_ticket=10355518139,
            deal_type=MT5DealType.DEAL_TYPE_SELL,
            deal_time_utc=t_exit2,
        )
        exit_tie2 = _make_deal(
            deal_ticket=10073000020,
            order_ticket=10355518139,
            position_ticket=10355518139,
            deal_type=MT5DealType.DEAL_TYPE_SELL,
            deal_time_utc=t_exit2,
        )
        selected_tie = select_authoritative_exit_deal(entry, (exit_tie1, exit_tie2))
        assert selected_tie.deal_ticket == 10073000020
