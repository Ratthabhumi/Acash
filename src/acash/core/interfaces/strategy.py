"""Strategy abstract interface contract."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Mapping, Optional

from acash.core.domain.position import Position
from acash.core.domain.signal import Signal


class IStrategy(ABC):
    """Abstract interface contract for hypothesis-driven alpha signal generation."""

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Unique identifier for this strategy."""
        pass

    @abstractmethod
    def generate_signal(
        self,
        symbol: str,
        features: Mapping[str, Any],
        current_position: Optional[Position],
        timestamp_utc: datetime
    ) -> Optional[Signal]:
        """Generate directional signal based on calculated features and current position."""
        pass
