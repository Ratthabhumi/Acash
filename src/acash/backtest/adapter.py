"""Canonical Data Adapter and Event Ordering Policy for Backtesting Substrate (Phase 5).

Translates canonical Arrow tables (Trades, Order Book L2/L3, Bars) into an event stream
strictly sequenced by the Phase 3B 5-tuple total ordering contract:
(event_time_utc, source_order_key, message_rank, stream_id, row_sub_index)
Guarantees pure integer nanosecond timestamp extraction with zero float precision loss.
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


def extract_exact_nanoseconds(val: Any) -> int:
    """Extract integer nanoseconds using pure integer arithmetic, completely avoiding lossy float conversions."""
    if isinstance(val, int):
        if val < 10**17:  # Microseconds (e.g. 1768815000000000)
            return val * 1_000
        return val
    elif isinstance(val, datetime):
        dt_utc = val if val.tzinfo is not None else val.replace(tzinfo=timezone.utc)
        dt_utc = dt_utc.astimezone(timezone.utc)
        td = dt_utc - datetime(1970, 1, 1, tzinfo=timezone.utc)
        total_us = (td.days * 86400 + td.seconds) * 1_000_000 + td.microseconds
        return total_us * 1_000
    elif hasattr(val, "value"):  # PyArrow / Pandas timestamp scalar
        int_val = int(val.value)
        if int_val < 10**17:
            return int_val * 1_000
        return int_val
    else:
        int_raw = int(val)
        if int_raw < 10**17:
            return int_raw * 1_000
        return int_raw


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
        micros, nanos = divmod(self.event_timestamp_ns, 1_000)
        secs, us = divmod(micros, 1_000_000)
        return datetime.fromtimestamp(secs, tz=timezone.utc).replace(microsecond=us)

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
        has_source_key = "source_order_key" in table.column_names
        has_message_rank = "message_type_rank" in table.column_names
        has_row_sub_idx = "row_sub_index" in table.column_names

        for i in range(num_rows):
            ts_raw = pydict["timestamp_utc"][i]
            ts_ns = extract_exact_nanoseconds(ts_raw)

            source_key = (
                str(pydict["source_order_key"][i])
                if has_source_key
                else f"{symbol}:{stream_id}:{ts_ns}:{i:08d}"
            )
            message_rank = int(pydict["message_type_rank"][i]) if has_message_rank else 10
            row_sub_index = int(pydict["row_sub_index"][i]) if has_row_sub_idx else 0

            payload = {
                "open": Decimal(str(pydict["open"][i])),
                "high": Decimal(str(pydict["high"][i])),
                "low": Decimal(str(pydict["low"][i])),
                "close": Decimal(str(pydict["close"][i])),
                "volume": Decimal(str(pydict["volume"][i])),
                "bar_index": i,
            }
            if "vwap" in pydict:
                payload["vwap"] = Decimal(str(pydict["vwap"][i]))

            event = BacktestMarketEvent(
                event_type=BacktestEventType.BAR,
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
    def from_trades_table(
        table: pa.Table,
        symbol: str,
        stream_id: str = "TRADES",
    ) -> List[BacktestMarketEvent]:
        """Convert canonical trades table into BacktestMarketEvent stream."""
        events: List[BacktestMarketEvent] = []
        pydict = table.to_pydict()
        num_rows = table.num_rows
        has_source_key = "source_order_key" in table.column_names
        has_message_rank = "message_type_rank" in table.column_names
        has_row_sub_idx = "row_sub_index" in table.column_names

        for i in range(num_rows):
            ts_raw = pydict.get("exchange_time_utc", pydict.get("timestamp_utc"))[i]
            ts_ns = extract_exact_nanoseconds(ts_raw)

            source_key = (
                str(pydict["source_order_key"][i])
                if has_source_key
                else f"{symbol}:{stream_id}:{ts_ns}:{i:08d}"
            )
            message_rank = int(pydict["message_type_rank"][i]) if has_message_rank else 1
            row_sub_index = int(pydict["row_sub_index"][i]) if has_row_sub_idx else 0

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
    def from_depth_table(
        table: pa.Table,
        symbol: str,
        stream_id: str = "DEPTH",
    ) -> List[BacktestMarketEvent]:
        """Convert canonical Order Book L2/MBP table into BacktestMarketEvent stream."""
        events: List[BacktestMarketEvent] = []
        pydict = table.to_pydict()
        num_rows = table.num_rows
        has_source_key = "source_order_key" in table.column_names
        has_message_rank = "message_type_rank" in table.column_names
        has_row_sub_idx = "row_sub_index" in table.column_names

        for i in range(num_rows):
            ts_raw = pydict.get("exchange_time_utc", pydict.get("timestamp_utc"))[i]
            ts_ns = extract_exact_nanoseconds(ts_raw)

            source_key = (
                str(pydict["source_order_key"][i])
                if has_source_key
                else f"{symbol}:{stream_id}:{ts_ns}:{i:08d}"
            )
            message_rank = int(pydict["message_type_rank"][i]) if has_message_rank else 2
            row_sub_index = int(pydict["row_sub_index"][i]) if has_row_sub_idx else 0

            action = str(pydict.get("action", ["MODIFY"])[i]).upper()
            side = str(pydict.get("side", ["BID"])[i]).upper()
            price_val = pydict.get("price", [None])[i]
            size_val = pydict.get("size", [None])[i]

            payload = {
                "action": action,
                "side": side,
                "price": Decimal(str(price_val)) if price_val is not None else None,
                "size": Decimal(str(size_val)) if size_val is not None else None,
                "level_idx": int(pydict.get("level_idx", [0])[i]) if "level_idx" in pydict else None,
            }

            event_type = BacktestEventType.DEPTH_SNAPSHOT if "SNAPSHOT" in action else BacktestEventType.DEPTH_DELTA

            event = BacktestMarketEvent(
                event_type=event_type,
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
