"""Risk engine abstract interface contract."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.signal import RiskAssessment, TargetAllocation


class IRiskEngine(ABC):
    """Abstract interface contract for deterministic hard risk evaluation."""

    @abstractmethod
    def evaluate_allocation(
        self,
        target_allocation: TargetAllocation,
        portfolio_state: PortfolioState,
        account_state: Optional[AccountState],
        timestamp_utc: datetime
    ) -> RiskAssessment:
        """Evaluate candidate target allocation against hard portfolio and drawdown constraints."""
        pass
