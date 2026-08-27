"""Market data provider abstract interface contract."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Sequence

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.market_data import Bar, MarketDataSnapshot


class IMarketDataProvider(ABC):
    """Abstract interface contract for point-in-time market data retrieval."""

    @abstractmethod
    def get_historical_bars(
        self,
        symbol: str,
        timeframe: BarTimeframe,
        start_utc: datetime,
        end_utc: datetime
    ) -> Sequence[Bar]:
        """Retrieve point-in-time historical candlestick bars within specified interval."""
        pass

    @abstractmethod
    def get_latest_snapshot(self, symbol: str) -> MarketDataSnapshot:
        """Retrieve the latest top-of-book market quote snapshot."""
        pass
