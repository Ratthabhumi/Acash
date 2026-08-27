"""Canonical Data Adapter and Event Ordering Policy for Backtesting Substrate (Phase 5).

Translates canonical Arrow tables (Trades, Order Book L2/L3, Bars) into an event stream
strictly sequenced by the Phase 3B 5-tuple total ordering contract:
(event_time_utc, source_order_key, message_rank, stream_id, row_sub_index)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import pyarrow as pa

from acash.data.schema import DataContractError


class BacktestEventType(str, Enum):
    """Event classification in backtesting stream."""

    TRADE = "TRADE"
    DEPTH_SNAPSHOT = "DEPTH_SNAPSHOT"
    DEPTH_DELTA = "DEPTH_DELTA"
    BAR = "BAR"


@dataclass(frozen=True)
class BacktestMarketEvent:
    """Canonical event fed into the backtest substrate event loop."""

    event_type: BacktestEventType
    symbol: str
    event_timestamp_ns: int
    source_order_key: str
    message_rank: int
    stream_id: str
    row_sub_index: int
    payload: Dict[str, Any]

    @property
    def event_time_utc(self) -> datetime:
        """Derive UTC datetime from nanosecond timestamp."""
        return datetime.fromtimestamp(self.event_timestamp_ns / 1_000_000_000, tz=timezone.utc)

    @property
    def order_tuple(self) -> Tuple[int, str, int, str, int]:
        """5-tuple total ordering key aligning with Phase 3B Data Contract."""
        return (
            self.event_timestamp_ns,
            self.source_order_key,
            self.message_rank,
            self.stream_id,
            self.row_sub_index,
        )

    def __lt__(self, other: "BacktestMarketEvent") -> bool:
        return self.order_tuple < other.order_tuple


class CanonicalDataAdapter:
    """Adapts canonical PyArrow tables into strictly sorted BacktestMarketEvent streams."""

    @staticmethod
    def from_bars_table(
        table: pa.Table,
        symbol: str,
        stream_id: str = "BARS",
    ) -> List[BacktestMarketEvent]:
        """Convert canonical bars table into BacktestMarketEvent stream."""
        events: List[BacktestMarketEvent] = []
        pydict = table.to_pydict()
        num_rows = table.num_rows

        for i in range(num_rows):
            ts = pydict["timestamp_utc"][i]
            if isinstance(ts, datetime):
                ts_ns = int(ts.timestamp() * 1_000_000_000)
            elif isinstance(ts, int):
                ts_ns = ts * 1_000 if ts < 10**16 else ts  # microsecond or nanosecond
            else:
                ts_ns = int(ts)

            source_key = f"bar_{i:08d}"
            payload = {
                "open": Decimal(str(pydict["open"][i])),
                "high": Decimal(str(pydict["high"][i])),
                "low": Decimal(str(pydict["low"][i])),
                "close": Decimal(str(pydict["close"][i])),
                "volume": Decimal(str(pydict["volume"][i])),
                "bar_index": i,
            }

            event = BacktestMarketEvent(
                event_type=BacktestEventType.BAR,
                symbol=symbol,
                event_timestamp_ns=ts_ns,
                source_order_key=source_key,
                message_rank=10,
                stream_id=stream_id,
                row_sub_index=0,
                payload=payload,
            )
            events.append(event)

        return events

    @staticmethod
    def from_trades_table(
        table: pa.Table,
        symbol: str,
        stream_id: str = "TRADES",
    ) -> List[BacktestMarketEvent]:
        """Convert canonical trades table into BacktestMarketEvent stream."""
        events: List[BacktestMarketEvent] = []
        pydict = table.to_pydict()
        num_rows = table.num_rows

        for i in range(num_rows):
            ts = pydict["exchange_time_utc"][i]
            if isinstance(ts, datetime):
                ts_ns = int(ts.timestamp() * 1_000_000_000)
            elif isinstance(ts, int):
                ts_ns = ts
            else:
                ts_ns = int(ts)

            source_key = str(pydict.get("source_order_key", [f"trade_{i:08d}"])[i])
            message_rank = int(pydict.get("message_type_rank", [1])[i])
            row_sub_index = int(pydict.get("row_sub_index", [0])[i])

            payload = {
                "trade_id": str(pydict.get("trade_id", [f"T-{i}"])[i]),
                "price": Decimal(str(pydict["price"][i])),
                "size": Decimal(str(pydict["size"][i])),
                "aggressor_side": str(pydict.get("aggressor_side", ["UNKNOWN"])[i]),
            }

            event = BacktestMarketEvent(
                event_type=BacktestEventType.TRADE,
                symbol=symbol,
                event_timestamp_ns=ts_ns,
                source_order_key=source_key,
                message_rank=message_rank,
                stream_id=stream_id,
                row_sub_index=row_sub_index,
                payload=payload,
            )
            events.append(event)

        return events

    @staticmethod
    def merge_and_sort_event_streams(
        streams: List[List[BacktestMarketEvent]],
    ) -> List[BacktestMarketEvent]:
        """Merge multiple event streams and enforce deterministic 5-tuple total ordering."""
        merged: List[BacktestMarketEvent] = []
        for stream in streams:
            merged.extend(stream)

        # Sort strictly by the 5-tuple order_tuple
        merged.sort(key=lambda ev: ev.order_tuple)

        # Validate total monotonic ordering
        for i in range(1, len(merged)):
            if merged[i].order_tuple < merged[i - 1].order_tuple:
                raise DataContractError(
                    f"Event stream total ordering violation at index {i}: "
                    f"{merged[i].order_tuple} < {merged[i-1].order_tuple}"
                )

        return merged
