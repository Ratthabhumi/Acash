"""In-memory mock market data provider adapter with zero network connectivity."""

from datetime import datetime
from typing import Sequence

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.market_data import Bar, MarketDataSnapshot
from acash.core.interfaces.market_data import IMarketDataProvider


class MockMarketDataProvider(IMarketDataProvider):
    """Synthetic in-memory market data provider for unit and contract testing."""

    def __init__(self) -> None:
        self._bars: dict[str, list[Bar]] = {}
        self._snapshots: dict[str, MarketDataSnapshot] = {}

    def add_bars(self, symbol: str, bars: Sequence[Bar]) -> None:
        """Add synthetic bars for a given symbol."""
        sym = symbol.upper()
        if sym not in self._bars:
            self._bars[sym] = []
        self._bars[sym].extend(bars)
        # Keep sorted by event_start_utc
        self._bars[sym].sort(key=lambda b: b.event_start_utc)

    def set_snapshot(self, snapshot: MarketDataSnapshot) -> None:
        """Set the latest top-of-book market snapshot for a symbol."""
        self._snapshots[snapshot.symbol.upper()] = snapshot

    def get_historical_bars(
        self,
        symbol: str,
        timeframe: BarTimeframe,
        start_utc: datetime,
        end_utc: datetime
    ) -> Sequence[Bar]:
        """Retrieve stored historical bars matching symbol, timeframe, and time window."""
        sym = symbol.upper()
        if sym not in self._bars:
            return []

        return [
            b for b in self._bars[sym]
            if b.timeframe == timeframe and start_utc <= b.event_start_utc <= end_utc
        ]

    def get_latest_snapshot(self, symbol: str) -> MarketDataSnapshot:
        """Retrieve stored latest market snapshot for a symbol."""
        sym = symbol.upper()
        if sym not in self._snapshots:
            raise KeyError(f"No market snapshot available for symbol: {symbol}")
        return self._snapshots[sym]
