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


def from_timestamp_ns(ns_val: int) -> int:
    """Explicitly convert integer nanoseconds without heuristic."""
    return int(ns_val)


def from_timestamp_us(us_val: int) -> int:
    """Explicitly convert integer microseconds to nanoseconds via pure integer multiplication."""
    return int(us_val) * 1_000


def extract_nanoseconds_from_datetime(val: datetime) -> int:
    """Convert datetime object to integer nanoseconds using pure integer arithmetic."""
    dt_utc = val if val.tzinfo is not None else val.replace(tzinfo=timezone.utc)
    dt_utc = dt_utc.astimezone(timezone.utc)
    td = dt_utc - datetime(1970, 1, 1, tzinfo=timezone.utc)
    total_us = (td.days * 86400 + td.seconds) * 1_000_000 + td.microseconds
    return total_us * 1_000


def extract_nanoseconds_from_scalar(scalar: pa.Scalar, col_type: Optional[pa.DataType] = None) -> int:
    """Extract integer nanoseconds from PyArrow scalar using explicit type metadata."""
    if scalar.as_py() is None:
        return 0

    target_type = col_type or scalar.type
    if pa.types.is_timestamp(target_type):
        unit = target_type.unit
        int_val = int(scalar.value)
        if unit == "ns":
            return int_val
        elif unit == "us":
            return int_val * 1_000
        elif unit == "ms":
            return int_val * 1_000_000
        elif unit == "s":
            return int_val * 1_000_000_000
    elif pa.types.is_int64(target_type):
        return int(scalar.as_py())

    val = scalar.as_py()
    if isinstance(val, datetime):
        return extract_nanoseconds_from_datetime(val)
    return int(val)


def extract_exact_nanoseconds(val: Any, unit: Optional[str] = None) -> int:
    """Extract integer nanoseconds with explicit unit or type awareness."""
    if isinstance(val, int):
        if unit == "us":
            return val * 1_000
        elif unit == "ns":
            return val
        elif unit == "ms":
            return val * 1_000_000
        elif unit == "s":
            return val * 1_000_000_000
        else:
            # Type-safe fallback if unit omitted
            return val
    elif isinstance(val, datetime):
        return extract_nanoseconds_from_datetime(val)
    elif isinstance(val, pa.Scalar):
        return extract_nanoseconds_from_scalar(val)
    elif hasattr(val, "value"):  # PyArrow / Pandas timestamp scalar
        return extract_nanoseconds_from_scalar(val)

    else:
        return int(val)


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
        """Derive UTC datetime from nanosecond timestamp using integer divmod."""
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
        num_rows = table.num_rows
        has_source_key = "source_order_key" in table.column_names
        has_message_rank = "message_type_rank" in table.column_names
        has_row_sub_idx = "row_sub_index" in table.column_names

        ts_col = table["timestamp_utc"]
        open_col = table["open"]
        high_col = table["high"]
        low_col = table["low"]
        close_col = table["close"]
        vol_col = table["volume"]
        vwap_col = table["vwap"] if "vwap" in table.column_names else None
        source_key_col = table["source_order_key"] if has_source_key else None
        msg_rank_col = table["message_type_rank"] if has_message_rank else None
        row_sub_col = table["row_sub_index"] if has_row_sub_idx else None

        for i in range(num_rows):
            ts_ns = extract_nanoseconds_from_scalar(ts_col[i], ts_col.type)

            source_key = (
                str(source_key_col[i].as_py())
                if source_key_col is not None
                else f"{symbol}:{stream_id}:{ts_ns}:{i:08d}"
            )
            message_rank = int(msg_rank_col[i].as_py()) if msg_rank_col is not None else 10
            row_sub_index = int(row_sub_col[i].as_py()) if row_sub_col is not None else 0

            payload = {
                "open": Decimal(str(open_col[i].as_py())),
                "high": Decimal(str(high_col[i].as_py())),
                "low": Decimal(str(low_col[i].as_py())),
                "close": Decimal(str(close_col[i].as_py())),
                "volume": Decimal(str(vol_col[i].as_py())),
                "bar_index": i,
            }
            if vwap_col is not None:
                payload["vwap"] = Decimal(str(vwap_col[i].as_py()))

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
        num_rows = table.num_rows
        has_source_key = "source_order_key" in table.column_names
        has_message_rank = "message_type_rank" in table.column_names
        has_row_sub_idx = "row_sub_index" in table.column_names

        ts_col = table["exchange_time_utc"] if "exchange_time_utc" in table.column_names else table["timestamp_utc"]
        trade_id_col = table["trade_id"] if "trade_id" in table.column_names else None
        price_col = table["price"]
        size_col = table["size"]
        side_col = table["aggressor_side"] if "aggressor_side" in table.column_names else None
        source_key_col = table["source_order_key"] if has_source_key else None
        msg_rank_col = table["message_type_rank"] if has_message_rank else None
        row_sub_col = table["row_sub_index"] if has_row_sub_idx else None

        for i in range(num_rows):
            ts_ns = extract_nanoseconds_from_scalar(ts_col[i], ts_col.type)

            source_key = (
                str(source_key_col[i].as_py())
                if source_key_col is not None
                else f"{symbol}:{stream_id}:{ts_ns}:{i:08d}"
            )
            message_rank = int(msg_rank_col[i].as_py()) if msg_rank_col is not None else 1
            row_sub_index = int(row_sub_col[i].as_py()) if row_sub_col is not None else 0

            payload = {
                "trade_id": str(trade_id_col[i].as_py()) if trade_id_col is not None else f"T-{i}",
                "price": Decimal(str(price_col[i].as_py())),
                "size": Decimal(str(size_col[i].as_py())),
                "aggressor_side": str(side_col[i].as_py()) if side_col is not None else "UNKNOWN",
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
        num_rows = table.num_rows
        has_source_key = "source_order_key" in table.column_names
        has_message_rank = "message_type_rank" in table.column_names
        has_row_sub_idx = "row_sub_index" in table.column_names

        ts_col = table["exchange_time_utc"] if "exchange_time_utc" in table.column_names else table["timestamp_utc"]
        action_col = table["action"] if "action" in table.column_names else None
        side_col = table["side"] if "side" in table.column_names else None
        price_col = table["price"] if "price" in table.column_names else None
        size_col = table["size"] if "size" in table.column_names else None
        level_col = table["level_idx"] if "level_idx" in table.column_names else None
        source_key_col = table["source_order_key"] if has_source_key else None
        msg_rank_col = table["message_type_rank"] if has_message_rank else None
        row_sub_col = table["row_sub_index"] if has_row_sub_idx else None

        for i in range(num_rows):
            ts_ns = extract_nanoseconds_from_scalar(ts_col[i], ts_col.type)

            source_key = (
                str(source_key_col[i].as_py())
                if source_key_col is not None
                else f"{symbol}:{stream_id}:{ts_ns}:{i:08d}"
            )
            message_rank = int(msg_rank_col[i].as_py()) if msg_rank_col is not None else 2
            row_sub_index = int(row_sub_col[i].as_py()) if row_sub_col is not None else 0

            action = str(action_col[i].as_py()).upper() if action_col is not None else "MODIFY"
            side = str(side_col[i].as_py()).upper() if side_col is not None else "BID"
            price_val = price_col[i].as_py() if price_col is not None else None
            size_val = size_col[i].as_py() if size_col is not None else None

            payload = {
                "action": action,
                "side": side,
                "price": Decimal(str(price_val)) if price_val is not None else None,
                "size": Decimal(str(size_val)) if size_val is not None else None,
                "level_idx": int(level_col[i].as_py()) if level_col is not None else 0,
            }

            event_type = (
                BacktestEventType.DEPTH_SNAPSHOT
                if action in ("SNAPSHOT", "CLEAR")
                else BacktestEventType.DEPTH_DELTA
            )

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
        """Merge and sort multiple event streams strictly using the Phase 3B total ordering contract."""
        all_events: List[BacktestMarketEvent] = []
        for stream in streams:
            all_events.extend(stream)

        all_events.sort(key=lambda ev: ev.order_tuple)
        return all_events
