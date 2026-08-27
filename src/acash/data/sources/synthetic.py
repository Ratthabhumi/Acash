"""Deterministic synthetic market data generator for testing and validation."""

import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional, Sequence, Tuple, Union
import pyarrow as pa

from acash.data.schema import CANONICAL_ARROW_SCHEMA
from acash.data.sources.base import IDataSourceAdapter


class SyntheticSourceAdapter(IDataSourceAdapter):
    """Generates synthetic deterministic market data bars for unit tests."""

    def __init__(
        self,
        source_id: str = "synthetic_mock",
        symbol: str = "BTC/USDT",
        timeframe: str = "M1",
        start_time_utc: datetime = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
        bar_count: int = 100,
        initial_price: Decimal = Decimal("50000.00"),
        price_step: Decimal = Decimal("10.00"),
        volume_per_bar: Decimal = Decimal("1.50"),
        bar_duration: timedelta = timedelta(minutes=1),
    ) -> None:
        self.source_id = source_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_time_utc = start_time_utc
        self.bar_count = bar_count
        self.initial_price = initial_price
        self.price_step = price_step
        self.volume_per_bar = volume_per_bar
        self.bar_duration = bar_duration

    def generate_table(self) -> pa.Table:
        """Generate deterministic PyArrow table conforming to CANONICAL_ARROW_SCHEMA."""
        source_ids: list[str] = []
        symbols: list[str] = []
        timeframes: list[str] = []
        event_starts: list[datetime] = []
        event_ends: list[datetime] = []
        knowledge_times: list[datetime] = []
        revision_seqs: list[int] = []
        opens: list[Decimal] = []
        highs: list[Decimal] = []
        lows: list[Decimal] = []
        closes: list[Decimal] = []
        volumes: list[Decimal] = []
        quote_volumes: list[Decimal] = []
        trade_counts: list[int] = []

        curr_time = self.start_time_utc
        curr_price = self.initial_price

        for i in range(self.bar_count):
            estart = curr_time
            eend = curr_time + self.bar_duration
            know = eend

            o = curr_price
            c = curr_price + (self.price_step if i % 2 == 0 else -self.price_step)
            h = max(o, c) + Decimal("5.00")
            l = min(o, c) - Decimal("5.00")
            v = self.volume_per_bar
            qv = v * ((o + c) / Decimal("2.0"))
            tc = 50 + (i % 10)

            source_ids.append(self.source_id)
            symbols.append(self.symbol)
            timeframes.append(self.timeframe)
            event_starts.append(estart)
            event_ends.append(eend)
            knowledge_times.append(know)
            revision_seqs.append(1)
            opens.append(o)
            highs.append(h)
            lows.append(l)
            closes.append(c)
            volumes.append(v)
            quote_volumes.append(qv)
            trade_counts.append(tc)

            curr_price = c
            curr_time = eend

        pydict = {
            "source_id": source_ids,
            "symbol": symbols,
            "timeframe": timeframes,
            "event_start_utc": event_starts,
            "event_end_utc": event_ends,
            "knowledge_time_utc": knowledge_times,
            "revision_seq": revision_seqs,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "quote_volume": quote_volumes,
            "trade_count": trade_counts,
        }
        return pa.Table.from_pydict(pydict, schema=CANONICAL_ARROW_SCHEMA)

    def read_source(self, source_path_or_uri: Union[str, Path] = "synthetic://default") -> Tuple[bytes, pa.Table]:
        """Return deterministic bytes and generated PyArrow table."""
        table = self.generate_table()
        # Generate canonical representation bytes
        raw_repr = json.dumps({
            "source_id": self.source_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "bar_count": self.bar_count,
            "start_time": self.start_time_utc.isoformat(),
        }).encode("utf-8")
        return raw_repr, table
