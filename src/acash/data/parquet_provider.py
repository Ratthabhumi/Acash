"""Parquet and DuckDB-backed Market Data Provider implementation.

Connects the canonical local Parquet/DuckDB storage layer (DuckDBStorage) to the
canonical IMarketDataProvider interface for offline research and paper-trading rehearsal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional, Sequence, Tuple, Union

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.core.domain.market_data import Bar, MarketDataSnapshot
from acash.core.interfaces.market_data import IMarketDataProvider
from acash.data.storage import DuckDBStorage


class ParquetMarketDataProvider(IMarketDataProvider):
    """Canonical Parquet/DuckDB implementation of IMarketDataProvider.

    Queries local immutable Parquet parts via DuckDBStorage point-in-time analytical engine.
    Preserves strict fail-closed semantics, bi-temporal metadata, exact Decimal precision,
    and deterministic ordering without fabricating, forward-filling, or interpolating data.
    """

    def __init__(
        self,
        storage: Optional[DuckDBStorage] = None,
        *,
        as_of_knowledge_time_utc: Optional[datetime] = None,
        allow_offline_derived_snapshot: bool = False,
        default_timeframe: BarTimeframe = BarTimeframe.M1,
    ) -> None:
        """Initialize provider with DuckDBStorage instance and optional configuration.

        Args:
            storage: Existing DuckDBStorage instance. Defaults to DuckDBStorage().
            as_of_knowledge_time_utc: Optional fixed point-in-time knowledge horizon.
                When configured, all historical queries evaluate revisions known on or before
                this pinned timestamp. When None, each query dynamically bounds
                as_of_knowledge_time_utc to the requested end_utc.
            allow_offline_derived_snapshot: Explicit flag allowing get_latest_snapshot()
                to emit an OFFLINE REHEARSAL DERIVED snapshot from OHLCV bars. Defaults to False
                (fail-closed) because OHLCV storage does not contain real top-of-book quotes.
            default_timeframe: BarTimeframe used when deriving offline rehearsal snapshots.
        """
        self._storage = storage or DuckDBStorage()
        if as_of_knowledge_time_utc is not None:
            if as_of_knowledge_time_utc.tzinfo is None:
                raise DataContractError(
                    "as_of_knowledge_time_utc must be a timezone-aware UTC datetime."
                )
            self._as_of_knowledge_time_utc: Optional[datetime] = as_of_knowledge_time_utc.astimezone(
                timezone.utc
            )
        else:
            self._as_of_knowledge_time_utc = None

        self._allow_offline_derived_snapshot = allow_offline_derived_snapshot
        self._default_timeframe = default_timeframe

    @property
    def storage(self) -> DuckDBStorage:
        """Return the underlying DuckDBStorage engine."""
        return self._storage

    @property
    def as_of_knowledge_time_utc(self) -> Optional[datetime]:
        """Return the pinned vintage knowledge timestamp if configured."""
        return self._as_of_knowledge_time_utc

    def get_historical_bars(
        self,
        symbol: str,
        timeframe: BarTimeframe,
        start_utc: datetime,
        end_utc: datetime,
    ) -> Sequence[Bar]:
        """Retrieve point-in-time historical candlestick bars within specified interval.

        Conforms strictly to the canonical IMarketDataProvider contract.

        Args:
            symbol: Target market asset identifier (e.g. 'BTC/USDT', 'EURUSD').
            timeframe: Canonical BarTimeframe enum.
            start_utc: Interval start timestamp (inclusive, timezone-aware UTC).
            end_utc: Interval end timestamp (inclusive, timezone-aware UTC).

        Returns:
            Sequence[Bar]: Deterministically ordered tuple of Bar instances sorted by
                event_start_utc ASC. Returns an empty tuple () if no records exist.
        """
        # 1. Validate Symbol
        if not symbol or not symbol.strip():
            raise DomainValidationError("Symbol must be a non-empty string.")
        norm_symbol = symbol.strip().upper()

        # 2. Validate Timeframe
        if not isinstance(timeframe, BarTimeframe):
            try:
                timeframe = BarTimeframe(timeframe)
            except (ValueError, TypeError) as exc:
                raise DataContractError(f"Unsupported or invalid timeframe: {timeframe!r}") from exc

        # 3. Validate Timezone Awareness & Interval Geometry
        if not isinstance(start_utc, datetime) or start_utc.tzinfo is None:
            raise DataContractError("start_utc must be a timezone-aware UTC datetime.")
        if not isinstance(end_utc, datetime) or end_utc.tzinfo is None:
            raise DataContractError("end_utc must be a timezone-aware UTC datetime.")

        start_norm = start_utc.astimezone(timezone.utc)
        end_norm = end_utc.astimezone(timezone.utc)

        if start_norm > end_norm:
            raise DataContractError(
                f"start_utc ({start_norm.isoformat()}) cannot be later than end_utc ({end_norm.isoformat()})."
            )

        # 4. Resolve Point-in-Time Knowledge Horizon
        # When constructor pinned vintage exists, use it; otherwise bound strictly to end_utc.
        as_of = (
            self._as_of_knowledge_time_utc
            if self._as_of_knowledge_time_utc is not None
            else end_norm
        )

        # 5. Query Canonical Storage Layer
        table = self._storage.query_point_in_time(
            symbol=norm_symbol,
            timeframe=timeframe.value,
            as_of_knowledge_time_utc=as_of,
            start_utc=start_norm,
            end_utc=end_norm,
        )

        if table.num_rows == 0:
            return ()

        # 6. Transform Arrow Rows to Validated Domain Bar Models
        bars: list[Bar] = []
        for row in table.to_pylist():
            # Ensure timestamps are timezone-aware UTC
            ev_start = row["event_start_utc"]
            if ev_start.tzinfo is None:
                ev_start = ev_start.replace(tzinfo=timezone.utc)
            else:
                ev_start = ev_start.astimezone(timezone.utc)

            ev_end = row["event_end_utc"]
            if ev_end.tzinfo is None:
                ev_end = ev_end.replace(tzinfo=timezone.utc)
            else:
                ev_end = ev_end.astimezone(timezone.utc)

            know_time = row["knowledge_time_utc"]
            if know_time.tzinfo is None:
                know_time = know_time.replace(tzinfo=timezone.utc)
            else:
                know_time = know_time.astimezone(timezone.utc)

            # Preserve exact Decimal precision
            open_price = Decimal(str(row["open"]))
            high_price = Decimal(str(row["high"]))
            low_price = Decimal(str(row["low"]))
            close_price = Decimal(str(row["close"]))
            volume_qty = Decimal(str(row["volume"]))

            bar = Bar(
                symbol=norm_symbol,
                timeframe=timeframe,
                event_start_utc=ev_start,
                event_end_utc=ev_end,
                knowledge_time_utc=know_time,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume_qty,
                provenance_hash=None,
            )
            bars.append(bar)

        # 7. Enforce Deterministic Event Start Sorting
        bars.sort(key=lambda b: b.event_start_utc)
        return tuple(bars)

    def get_latest_snapshot(self, symbol: str) -> MarketDataSnapshot:
        """Retrieve the latest top-of-book market quote snapshot.

        Strict Fail-Closed Behavior:
        Historical Parquet storage stores OHLCV candlestick records, NOT live L1 orderbook
        quotes (bid/ask/depth). In accordance with AGENTS.md §1 Zero Unverified Claims,
        calling this method fails closed by default.

        If allow_offline_derived_snapshot=True was explicitly set at construction,
        an OFFLINE PAPER/REHEARSAL DERIVATION snapshot is constructed from the latest bar
        matching the formula established in ForwardMarketDataFeeder.

        Raises:
            DataContractError: When allow_offline_derived_snapshot=False (the default).
            KeyError: When no market data exists in storage for the symbol.
        """
        if not symbol or not symbol.strip():
            raise DomainValidationError("Symbol must be a non-empty string.")
        norm_symbol = symbol.strip().upper()

        if not self._allow_offline_derived_snapshot:
            raise DataContractError(
                f"TOP_OF_BOOK_UNAVAILABLE: ParquetMarketDataProvider manages historical OHLCV "
                f"bars for symbol '{norm_symbol}', not live top-of-book quotes. Real bid/ask "
                f"book data is not present in OHLCV storage. For paper rehearsal, supply a "
                f"historical bar iterator to ForwardMarketDataFeeder(historical_iterator=...)."
            )

        # Offline Paper / Rehearsal Derived Snapshot Mode
        as_of = (
            self._as_of_knowledge_time_utc
            if self._as_of_knowledge_time_utc is not None
            else datetime.now(timezone.utc)
        )

        table = self._storage.query_point_in_time(
            symbol=norm_symbol,
            timeframe=self._default_timeframe.value,
            as_of_knowledge_time_utc=as_of,
        )

        if table.num_rows == 0:
            raise KeyError(f"No market data available in storage for symbol: '{norm_symbol}'.")

        # Slice latest row
        last_row = table.slice(table.num_rows - 1, 1).to_pylist()[0]
        close_price = Decimal(str(last_row["close"]))

        # Use canonical test rehearsal spread matching ForwardMarketDataFeeder:102
        half_spread = Decimal("0.0001")
        bid_price = max(Decimal("0.00000001"), close_price - half_spread)
        ask_price = close_price + half_spread

        ts_utc = last_row["event_end_utc"]
        if ts_utc.tzinfo is None:
            ts_utc = ts_utc.replace(tzinfo=timezone.utc)
        else:
            ts_utc = ts_utc.astimezone(timezone.utc)

        return MarketDataSnapshot(
            symbol=norm_symbol,
            bid=bid_price,
            ask=ask_price,
            bid_size=Decimal("100"),
            ask_size=Decimal("100"),
            last_price=close_price,
            timestamp_utc=ts_utc,
        )
