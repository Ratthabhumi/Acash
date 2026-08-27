"""Backtest simulation engine abstract interface contract."""

from abc import ABC, abstractmethod
from typing import Any, Mapping


class IBacktestEngine(ABC):
    """Abstract interface contract for backtesting simulation engines."""

    @abstractmethod
    def run_simulation(
        self,
        strategy_config: Mapping[str, Any],
        market_data_config: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Execute simulation run and return summary metrics."""
        pass
