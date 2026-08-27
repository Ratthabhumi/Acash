"""Feature engine abstract interface contract."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Mapping, Sequence

from acash.core.domain.market_data import Bar


class IFeatureEngine(ABC):
    """Abstract interface contract for feature computation with point-in-time anti-leakage."""

    @abstractmethod
    def compute_features(
        self,
        symbol: str,
        bars: Sequence[Bar],
        knowledge_time_utc: datetime
    ) -> Mapping[str, Any]:
        """Compute point-in-time analytical features strictly up to knowledge_time_utc."""
        pass
