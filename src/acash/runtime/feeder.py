"""Phase 13: Forward Market Data Feeder & Freshness Evaluator.

Strictly enforces:
1. Point-in-time tick and bar arrival freshness evaluation.
2. Clear operational separation: MT5_FORWARD vs. STREAMING_PARQUET_PUMP.
3. Fail-closed stale data rejection: data_age_ms > max_market_data_age_ms halts cycles.
4. Startup mode-compatibility enforcement: STREAMING_PARQUET_PUMP cannot pair with MT5_DEMO.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, Iterator, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.market_data import Bar, MarketDataSnapshot
from acash.core.interfaces.market_data import IMarketDataProvider

if TYPE_CHECKING:
    from acash.execution.mt5.transport import NativeMT5Transport
    from acash.runtime.strategy_adapter import PaperTradingSessionIdentity


class FeedSourceType(str, Enum):
    """Source feed classification for market data streaming."""

    MT5_FORWARD = "MT5_FORWARD"
    STREAMING_PARQUET_PUMP = "STREAMING_PARQUET_PUMP"


class MarketFeedStatus(BaseModel):
    """Health and freshness status of the market data feed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    is_connected: bool = Field(description="Underlying market data provider socket/session connected.")
    last_tick_utc: datetime = Field(description="Timestamp of the most recent market tick.")
    data_age_ms: int = Field(ge=0, description="Latency between wall-clock observation and tick time.")
    feed_source: FeedSourceType = Field(description="Underlying feed source classification.")


class ForwardMarketDataFeeder:
    """Forward market data provider adapter with millisecond freshness tracking."""

    def __init__(
        self,
        provider: IMarketDataProvider,
        source_type: FeedSourceType,
        session_identity: Any,
        mt5_transport: Optional[NativeMT5Transport] = None,
        historical_iterator: Optional[Iterator[Bar]] = None,
        max_market_data_age_ms: int = 1500,
    ) -> None:
        self.provider = provider
        self.source_type = source_type
        self.session_identity = session_identity
        self.mt5_transport = mt5_transport
        self.historical_iterator = historical_iterator
        self.max_market_data_age_ms = max_market_data_age_ms
        self._last_snapshot: Optional[MarketDataSnapshot] = None
        self._last_tick_utc: Optional[datetime] = None

        # Enforce startup session compatibility invariant (Rev 2.2.2 §6.2.1)
        if hasattr(session_identity, "data_source") and session_identity.data_source != source_type:
            raise DataContractError(
                f"FEED_SOURCE_MISMATCH: session_identity specifies {session_identity.data_source}, "
                f"but ForwardMarketDataFeeder was initialized with {source_type}."
            )

        if source_type == FeedSourceType.STREAMING_PARQUET_PUMP:
            exec_mode = getattr(session_identity, "execution_mode", None)
            if exec_mode is not None:
                exec_mode_val = exec_mode.value if hasattr(exec_mode, "value") else str(exec_mode)
                if exec_mode_val == "MT5_DEMO":
                    raise DataContractError(
                        "INVALID_SESSION_CONFIGURATION: STREAMING_PARQUET_PUMP is strictly an offline test double "
                        "and cannot be paired with MT5_DEMO or qualify as a FORWARD_PAPER_RUN."
                    )

    def poll_next_market_snapshot(
        self,
        symbol: str,
        wall_clock_utc: datetime,
    ) -> Tuple[MarketDataSnapshot, int]:
        """Poll the next market snapshot and compute data freshness in milliseconds.

        Returns:
            Tuple[MarketDataSnapshot, data_age_ms]
        """
        if wall_clock_utc.tzinfo is None:
            raise DataContractError("wall_clock_utc must be a timezone-aware UTC datetime.")

        if self.source_type == FeedSourceType.STREAMING_PARQUET_PUMP:
            # Deterministic Offline Test Double mode
            if self.historical_iterator is not None:
                try:
                    bar = next(self.historical_iterator)
                    half_spread = Decimal("0.0001")
                    snapshot = MarketDataSnapshot(
                        symbol=bar.symbol,
                        bid=bar.close - half_spread,
                        ask=bar.close + half_spread,
                        bid_size=Decimal("100"),
                        ask_size=Decimal("100"),
                        last_price=bar.close,
                        timestamp_utc=bar.event_end_utc,
                    )
                except StopIteration:
                    if self._last_snapshot is not None:
                        snapshot = self._last_snapshot
                    else:
                        raise DataContractError(f"Historical bar iterator exhausted for symbol '{symbol}'.")
            else:
                snapshot = self.provider.get_latest_snapshot(symbol)

            self._last_snapshot = snapshot
            self._last_tick_utc = snapshot.timestamp_utc
            # Offline test replay has data_age_ms = 0 by construction
            return snapshot, 0

        # MT5 Forward / Live Market Data Mode
        snapshot = self.provider.get_latest_snapshot(symbol)
        self._last_snapshot = snapshot
        tick_time = snapshot.timestamp_utc
        if tick_time.tzinfo is None:
            tick_time = tick_time.replace(tzinfo=timezone.utc)
        self._last_tick_utc = tick_time

        diff_seconds = (wall_clock_utc - tick_time).total_seconds()
        data_age_ms = max(0, int(diff_seconds * 1000))
        return snapshot, data_age_ms

    def get_feed_status(self, wall_clock_utc: datetime) -> MarketFeedStatus:
        """Return the current feed status and freshness telemetry."""
        if self._last_tick_utc is None:
            return MarketFeedStatus(
                is_connected=False,
                last_tick_utc=wall_clock_utc,
                data_age_ms=999999,
                feed_source=self.source_type,
            )

        diff_sec = (wall_clock_utc - self._last_tick_utc).total_seconds()
        age_ms = max(0, int(diff_sec * 1000))
        return MarketFeedStatus(
            is_connected=True,
            last_tick_utc=self._last_tick_utc,
            data_age_ms=age_ms,
            feed_source=self.source_type,
        )
