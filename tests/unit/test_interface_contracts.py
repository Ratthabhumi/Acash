"""Unit tests for interface contracts and abstract base class constraints."""

import pytest

from acash.core.interfaces.backtest import IBacktestEngine
from acash.core.interfaces.execution import IExecutionEngine
from acash.core.interfaces.features import IFeatureEngine
from acash.core.interfaces.ledger import IDecisionLedger
from acash.core.interfaces.market_data import IMarketDataProvider
from acash.core.interfaces.portfolio import IPortfolioOptimizer
from acash.core.interfaces.risk import IRiskEngine
from acash.core.interfaces.strategy import IStrategy
from acash.data.mock import MockMarketDataProvider
from acash.execution.mock import MockExecutionEngine
from acash.storage.mock import InMemoryDecisionLedger


def test_interfaces_cannot_be_instantiated_directly() -> None:
    interfaces = [
        IMarketDataProvider,
        IFeatureEngine,
        IStrategy,
        IPortfolioOptimizer,
        IRiskEngine,
        IBacktestEngine,
        IExecutionEngine,
        IDecisionLedger,
    ]

    for iface in interfaces:
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            iface()


def test_mock_adapters_implement_interfaces() -> None:
    exec_mock = MockExecutionEngine()
    assert isinstance(exec_mock, IExecutionEngine)

    data_mock = MockMarketDataProvider()
    assert isinstance(data_mock, IMarketDataProvider)

    ledger_mock = InMemoryDecisionLedger()
    assert isinstance(ledger_mock, IDecisionLedger)
