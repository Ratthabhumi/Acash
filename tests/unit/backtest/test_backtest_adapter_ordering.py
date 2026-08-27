"""Unit Tests for Canonical Data Adapter, Float-Free Nanoseconds, and Phase 3B 5-Tuple Event Ordering (Phase 5)."""

from datetime import datetime, timezone
from decimal import Decimal
import pyarrow as pa
import pytest

from acash.backtest.adapter import (
    BacktestEventType,
    BacktestMarketEvent,
    CanonicalDataAdapter,
    extract_exact_nanoseconds,
    from_timestamp_ns,
    from_timestamp_us,
)
from acash.data.schema import DataContractError



def test_extract_exact_nanoseconds_float_free() -> None:
    """Verify exact integer extraction of nanoseconds without floating-point precision truncation."""
    # 1. Microseconds integer -> Nanoseconds integer (exact * 1000)
    us_ts = 1768815000123456
    assert from_timestamp_us(us_ts) == 1768815000123456000
    assert extract_exact_nanoseconds(us_ts, unit="us") == 1768815000123456000

    # 2. Nanoseconds integer -> Exact passthrough
    ns_ts = 1768815000123456789
    assert from_timestamp_ns(ns_ts) == 1768815000123456789
    assert extract_exact_nanoseconds(ns_ts, unit="ns") == 1768815000123456789

    # 3. Datetime object -> Integer microsecond nanosecond conversion
    dt = datetime(2026, 1, 19, 9, 30, 0, 123456, tzinfo=timezone.utc)
    extracted = extract_exact_nanoseconds(dt)
    assert extracted % 1_000_000_000 == 123456000



def _make_sample_bars_table() -> pa.Table:
    timestamps = [
        datetime(2026, 1, 19, 9, 30, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 19, 9, 31, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 19, 9, 32, 0, tzinfo=timezone.utc),
    ]
    return pa.Table.from_pydict(
        {
            "timestamp_utc": timestamps,
            "open": [Decimal("5000.00"), Decimal("5002.00"), Decimal("5001.00")],
            "high": [Decimal("5005.00"), Decimal("5004.00"), Decimal("5003.00")],
            "low": [Decimal("4998.00"), Decimal("5000.00"), Decimal("4999.00")],
            "close": [Decimal("5002.00"), Decimal("5001.00"), Decimal("5002.50")],
            "volume": [Decimal("100"), Decimal("150"), Decimal("120")],
        }
    )


def _make_sample_trades_table() -> pa.Table:
    timestamps = [
        datetime(2026, 1, 19, 9, 30, 15, tzinfo=timezone.utc),
        datetime(2026, 1, 19, 9, 30, 45, tzinfo=timezone.utc),
    ]
    return pa.Table.from_pydict(
        {
            "exchange_time_utc": timestamps,
            "trade_id": ["T-1", "T-2"],
            "source_order_key": ["key_001", "key_002"],
            "message_type_rank": [1, 1],
            "row_sub_index": [0, 0],
            "price": [Decimal("5001.00"), Decimal("5001.50")],
            "size": [Decimal("5.0"), Decimal("10.0")],
            "aggressor_side": ["BUY", "SELL"],
        }
    )


def _make_sample_depth_table() -> pa.Table:
    timestamps = [
        datetime(2026, 1, 19, 9, 30, 5, tzinfo=timezone.utc),
        datetime(2026, 1, 19, 9, 30, 10, tzinfo=timezone.utc),
    ]
    return pa.Table.from_pydict(
        {
            "exchange_time_utc": timestamps,
            "action": ["MODIFY", "MODIFY"],
            "side": ["BID", "ASK"],
            "price": [Decimal("5000.00"), Decimal("5002.00")],
            "size": [Decimal("10.0"), Decimal("15.0")],
            "level_idx": [0, 0],
            "source_order_key": ["dkey_001", "dkey_002"],
            "message_type_rank": [2, 2],
            "row_sub_index": [0, 0],
        }
    )


def test_adapter_event_conversion_and_merging_order() -> None:
    """Verify bars, trades, and depth streams are merged and ordered strictly by the 5-tuple."""
    bars_tbl = _make_sample_bars_table()
    trades_tbl = _make_sample_trades_table()
    depth_tbl = _make_sample_depth_table()

    bar_events = CanonicalDataAdapter.from_bars_table(bars_tbl, symbol="ES.FUT")
    trade_events = CanonicalDataAdapter.from_trades_table(trades_tbl, symbol="ES.FUT")
    depth_events = CanonicalDataAdapter.from_depth_table(depth_tbl, symbol="ES.FUT")

    assert len(bar_events) == 3
    assert len(trade_events) == 2
    assert len(depth_events) == 2

    merged = CanonicalDataAdapter.merge_and_sort_event_streams([bar_events, trade_events, depth_events])
    assert len(merged) == 7

    # Check timestamps and 5-tuple order are strictly non-decreasing
    for i in range(1, len(merged)):
        assert merged[i].order_tuple >= merged[i - 1].order_tuple

    # 1. Bar @ 9:30:00
    assert merged[0].event_type == BacktestEventType.BAR
    # 2. Depth Bid @ 9:30:05
    assert merged[1].event_type == BacktestEventType.DEPTH_DELTA
    # 3. Depth Ask @ 9:30:10
    assert merged[2].event_type == BacktestEventType.DEPTH_DELTA
    # 4. Trade @ 9:30:15
    assert merged[3].event_type == BacktestEventType.TRADE
    # 5. Trade @ 9:30:45
    assert merged[4].event_type == BacktestEventType.TRADE
    # 6. Bar @ 9:31:00
    assert merged[5].event_type == BacktestEventType.BAR
