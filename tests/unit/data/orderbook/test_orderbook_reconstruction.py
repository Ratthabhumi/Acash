"""Unit tests for In-Memory Deterministic Order Book State Reconstructors (Phase 3B)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pyarrow as pa
import pytest

from acash.data.orderbook.reconstruction import (
    MbpOrderBookReconstructor,
    MboOrderBookReconstructor,
)
from acash.data.orderbook.schema import (
    CANONICAL_BOOK_SNAPSHOT_SCHEMA,
    CrossedStateCategory,
    SnapshotShapePolicy,
)


def _make_depth_snapshot_table(levels_n: int = 3) -> pa.Table:
    """Helper to build a balanced Top-N depth snapshot."""
    base_t = datetime(2026, 1, 19, 14, 30, 0, 0, tzinfo=timezone.utc)
    bids_px = [Decimal(f"{5000 - i * 0.25:.2f}") for i in range(levels_n)]
    asks_px = [Decimal(f"{5000.50 + i * 0.25:.2f}") for i in range(levels_n)]

    rows = []
    # Bids
    for i, px in enumerate(bids_px):
        rows.append({
            "source_id": "CME", "channel_id": "310", "symbol": "ES.FUT", "trading_date": date(2026, 1, 19),
            "exchange_time_utc": base_t, "feed_time_utc": None,
            "knowledge_time_utc": base_t + timedelta(seconds=1),
            "source_seq_num": 1000, "source_order_key": "00000000000000001000",
            "snapshot_id": "snap_001", "is_snapshot_complete": True,
            "side": "BID", "level_idx": i, "price": px, "size": Decimal("10"), "order_count": 2,
        })
    # Asks
    for i, px in enumerate(asks_px):
        rows.append({
            "source_id": "CME", "channel_id": "310", "symbol": "ES.FUT", "trading_date": date(2026, 1, 19),
            "exchange_time_utc": base_t, "feed_time_utc": None,
            "knowledge_time_utc": base_t + timedelta(seconds=1),
            "source_seq_num": 1000, "source_order_key": "00000000000000001000",
            "snapshot_id": "snap_001", "is_snapshot_complete": True,
            "side": "ASK", "level_idx": i, "price": px, "size": Decimal("15"), "order_count": 3,
        })

    pydict = {k: [r[k] for r in rows] for k in rows[0].keys()}
    return pa.Table.from_pydict(pydict, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)


def test_mbp_reconstruction_lifecycle() -> None:
    """Verify MBP reconstructor initialises from snapshot and applies normalized actions accurately."""
    stream_scope = ("CME", "310", "ES.FUT", "2026-01-19")
    reconstructor = MbpOrderBookReconstructor(stream_scope=stream_scope)

    snap_table = _make_depth_snapshot_table(levels_n=3)
    assert reconstructor.apply_snapshot_frame(snap_table)

    state0 = reconstructor.get_ladder_state(top_n=5)
    assert state0.is_valid
    assert len(state0.bids) == 3
    assert len(state0.asks) == 3
    assert state0.bids[0].price == Decimal("5000.00")
    assert state0.asks[0].price == Decimal("5000.50")

    # 1. Apply ADD (new higher bid @ 5000.25 -> spread narrows)
    t1 = datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc)
    reconstructor.apply_delta(
        exchange_time_utc=t1,
        source_order_key="00000000000000001001",
        action_sub_idx=0,
        action="ADD",
        side="BID",
        price=Decimal("5000.25"),
        size=Decimal("20"),
    )
    state1 = reconstructor.get_ladder_state(top_n=5)
    assert state1.bids[0].price == Decimal("5000.25")
    assert state1.bids[0].size == Decimal("20")

    # 2. Apply MODIFY (resulting absolute size update on Ask @ 5000.50 from 15 to 40)
    t2 = datetime(2026, 1, 19, 14, 30, 0, 200, tzinfo=timezone.utc)
    reconstructor.apply_delta(
        exchange_time_utc=t2,
        source_order_key="00000000000000001002",
        action_sub_idx=0,
        action="MODIFY",
        side="ASK",
        price=Decimal("5000.50"),
        size=Decimal("40"),
    )
    state2 = reconstructor.get_ladder_state(top_n=5)
    assert state2.asks[0].price == Decimal("5000.50")
    assert state2.asks[0].size == Decimal("40")

    # 3. Apply CANCEL (resulting remaining size on Bid @ 5000.25 reduced to 0 -> removes level)
    t3 = datetime(2026, 1, 19, 14, 30, 0, 300, tzinfo=timezone.utc)
    reconstructor.apply_delta(
        exchange_time_utc=t3,
        source_order_key="00000000000000001003",
        action_sub_idx=0,
        action="CANCEL",
        side="BID",
        price=Decimal("5000.25"),
        size=Decimal("0"),
    )
    state3 = reconstructor.get_ladder_state(top_n=5)
    assert state3.bids[0].price == Decimal("5000.00")

    # 4. Apply CLEAR (clears all asks)
    t4 = datetime(2026, 1, 19, 14, 30, 0, 400, tzinfo=timezone.utc)
    reconstructor.apply_delta(
        exchange_time_utc=t4,
        source_order_key="00000000000000001004",
        action_sub_idx=0,
        action="CLEAR",
        side="ASK",
    )
    state4 = reconstructor.get_ladder_state(top_n=5)
    assert len(state4.asks) == 0
    assert len(state4.bids) == 3


def test_mbp_partial_snapshot_rejected() -> None:
    """Verify that incomplete snapshots are rejected under FIXED_DEPTH_N policy."""
    stream_scope = ("CME", "310", "ES.FUT", "2026-01-19")
    reconstructor = MbpOrderBookReconstructor(stream_scope=stream_scope)

    data = {
        "source_id": ["CME"],
        "channel_id": ["310"],
        "symbol": ["ES.FUT"],
        "trading_date": [date(2026, 1, 19)],
        "exchange_time_utc": [datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)],
        "feed_time_utc": [None],
        "knowledge_time_utc": [datetime(2026, 1, 19, 14, 30, 1, tzinfo=timezone.utc)],
        "source_seq_num": [1000],
        "source_order_key": ["00000000000000001000"],
        "snapshot_id": ["snap_incomplete"],
        "is_snapshot_complete": [False],  # Incomplete!
        "side": ["BID"],
        "level_idx": [0],
        "price": [Decimal("5000.25")],
        "size": [Decimal("10")],
        "order_count": [1],
    }
    table = pa.Table.from_pydict(data, schema=CANONICAL_BOOK_SNAPSHOT_SCHEMA)

    assert not reconstructor.apply_snapshot_frame(table, shape_policy=SnapshotShapePolicy.FIXED_DEPTH_N)
    assert reconstructor.status == "PARTIAL_SNAPSHOT_REJECTED"


def test_crossed_book_classification() -> None:
    """Verify crossed book states are accurately classified (TRANSIENT vs PERSISTENT vs AUCTION)."""
    stream_scope = ("CME", "310", "ES.FUT", "2026-01-19")
    reconstructor = MbpOrderBookReconstructor(stream_scope=stream_scope, max_transient_crossed_deltas=2)

    snap_table = _make_depth_snapshot_table(levels_n=2)  # BBO: Bid 5000.00, Ask 5000.50
    reconstructor.apply_snapshot_frame(snap_table)

    # 1. Delta crossed quotes: Bid 5001.00 >= Ask 5000.50 (Crossed delta 1)
    t1 = datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc)
    reconstructor.apply_delta(
        exchange_time_utc=t1,
        source_order_key="00000000000000001001",
        action_sub_idx=0,
        action="ADD",
        side="BID",
        price=Decimal("5001.00"),
        size=Decimal("10"),
    )
    s1 = reconstructor.get_ladder_state(top_n=5)
    assert s1.is_crossed
    assert s1.crossed_category == CrossedStateCategory.CROSSED_TRANSIENT

    # 2. Delta 2 still crossed (consecutive = 2 <= max 2 -> still TRANSIENT)
    t2 = datetime(2026, 1, 19, 14, 30, 0, 200, tzinfo=timezone.utc)
    reconstructor.apply_delta(
        exchange_time_utc=t2,
        source_order_key="00000000000000001002",
        action_sub_idx=0,
        action="MODIFY",
        side="BID",
        price=Decimal("5001.00"),
        size=Decimal("15"),
    )
    s2 = reconstructor.get_ladder_state(top_n=5)
    assert s2.is_crossed
    assert s2.crossed_category == CrossedStateCategory.CROSSED_TRANSIENT

    # 3. Delta 3 still crossed (consecutive = 3 > max 2 -> transitions to PERSISTENT)
    t3 = datetime(2026, 1, 19, 14, 30, 0, 300, tzinfo=timezone.utc)
    reconstructor.apply_delta(
        exchange_time_utc=t3,
        source_order_key="00000000000000001003",
        action_sub_idx=0,
        action="MODIFY",
        side="BID",
        price=Decimal("5001.00"),
        size=Decimal("20"),
    )
    s3 = reconstructor.get_ladder_state(top_n=5)
    assert s3.is_crossed
    assert s3.crossed_category == CrossedStateCategory.CROSSED_PERSISTENT_ANOMALY

    # 4. In Auction session -> CROSSED_AUCTION_OR_HALT
    s_auc = reconstructor.get_ladder_state(top_n=5, is_auction_session=True)
    assert s_auc.is_crossed
    assert s_auc.crossed_category == CrossedStateCategory.CROSSED_AUCTION_OR_HALT


def test_mbo_order_queue_fifo_priority_and_projection() -> None:
    """Verify MBO reconstructor tracks discrete orders, resets priority on price modify, and projects L2 view."""
    stream_scope = ("CME", "310", "ES.FUT", "2026-01-19")
    reconstructor = MboOrderBookReconstructor(stream_scope=stream_scope)

    # 1. Add order 1 (@ 5000.00, size 10)
    t1 = datetime(2026, 1, 19, 14, 30, 0, 100, tzinfo=timezone.utc)
    reconstructor.apply_delta(
        exchange_time_utc=t1,
        source_order_key="00000000000000001001",
        action_sub_idx=0,
        action="ADD",
        side="BID",
        order_id="ORD_1",
        price=Decimal("5000.00"),
        size=Decimal("10"),
    )

    # 2. Add order 2 (@ 5000.00, size 15) -> aggregates to size 25, order_count 2
    t2 = datetime(2026, 1, 19, 14, 30, 0, 200, tzinfo=timezone.utc)
    reconstructor.apply_delta(
        exchange_time_utc=t2,
        source_order_key="00000000000000001002",
        action_sub_idx=0,
        action="ADD",
        side="BID",
        order_id="ORD_2",
        price=Decimal("5000.00"),
        size=Decimal("15"),
    )

    l2_state1 = reconstructor.get_ladder_state(top_n=5)
    assert len(l2_state1.bids) == 1
    assert l2_state1.bids[0].price == Decimal("5000.00")
    assert l2_state1.bids[0].size == Decimal("25")
    assert l2_state1.bids[0].order_count == 2

    # 3. Modify order 1 price to 5000.25 -> now two price levels
    t3 = datetime(2026, 1, 19, 14, 30, 0, 300, tzinfo=timezone.utc)
    reconstructor.apply_delta(
        exchange_time_utc=t3,
        source_order_key="00000000000000001003",
        action_sub_idx=0,
        action="MODIFY",
        side="BID",
        order_id="ORD_1",
        price=Decimal("5000.25"),
        size=Decimal("10"),
    )
    l2_state2 = reconstructor.get_ladder_state(top_n=5)
    assert len(l2_state2.bids) == 2
    assert l2_state2.bids[0].price == Decimal("5000.25")
    assert l2_state2.bids[0].size == Decimal("10")
    assert l2_state2.bids[1].price == Decimal("5000.00")
    assert l2_state2.bids[1].size == Decimal("15")
