"""Unit Tests for Canonical Data Adapter and Phase 3B 5-Tuple Event Ordering (Phase 5)."""

from datetime import datetime, timezone
from decimal import Decimal
import pyarrow as pa
import pytest

from acash.backtest.adapter import (
    BacktestEventType,
    BacktestMarketEvent,
    CanonicalDataAdapter,
)
from acash.data.schema import DataContractError


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


def test_adapter_event_conversion_and_merging_order() -> None:
    """Verify bars and trades streams are merged and ordered strictly by the 5-tuple."""
    bars_tbl = _make_sample_bars_table()
    trades_tbl = _make_sample_trades_table()

    bar_events = CanonicalDataAdapter.from_bars_table(bars_tbl, symbol="ES.FUT")
    trade_events = CanonicalDataAdapter.from_trades_table(trades_tbl, symbol="ES.FUT")

    assert len(bar_events) == 3
    assert len(trade_events) == 2

    merged = CanonicalDataAdapter.merge_and_sort_event_streams([bar_events, trade_events])
    assert len(merged) == 5

    # Check timestamps are strictly non-decreasing
    for i in range(1, len(merged)):
        assert merged[i].order_tuple >= merged[i - 1].order_tuple

    # First event is Bar at 9:30:00
    assert merged[0].event_type == BacktestEventType.BAR
    # Second event is Trade at 9:30:15
    assert merged[1].event_type == BacktestEventType.TRADE
    # Third event is Trade at 9:30:45
    assert merged[2].event_type == BacktestEventType.TRADE
    # Fourth event is Bar at 9:31:00
    assert merged[3].event_type == BacktestEventType.BAR
