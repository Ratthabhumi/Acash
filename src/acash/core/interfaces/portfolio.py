"""Portfolio optimizer abstract interface contract."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Sequence

from acash.core.domain.portfolio import PortfolioState
from acash.core.domain.signal import Signal, TargetAllocation


class IPortfolioOptimizer(ABC):
    """Abstract interface contract for portfolio capital allocation."""

    @abstractmethod
    def calculate_target_allocation(
        self,
        signals: Sequence[Signal],
        current_portfolio: PortfolioState,
        timestamp_utc: datetime
    ) -> TargetAllocation:
        """Compute candidate target portfolio weights across available opportunities."""
        pass
