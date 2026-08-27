"""Unit tests for domain models, deep immutability, finite value validation, and invariants."""

from datetime import datetime, timezone
from decimal import Decimal
import math
import pytest
from pydantic import ValidationError

from acash.core.domain.enums import AssetClass, BarTimeframe, OrderSide, OrderStatus, OrderType
from acash.core.domain.exceptions import DomainValidationError, InvariantViolationError
from acash.core.domain.execution import Fill, Order
from acash.core.domain.instrument import Instrument
from acash.core.domain.market_data import Bar, MarketDataSnapshot
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.core.domain.signal import RiskAssessment, Signal, TargetAllocation


def test_instrument_validation(sample_instrument: Instrument) -> None:
    assert sample_instrument.symbol == "BTC-USD"
    assert sample_instrument.asset_class == AssetClass.CRYPTO
    assert sample_instrument.tick_size == Decimal("0.01")

    # Immutability
    with pytest.raises(ValidationError):
        setattr(sample_instrument, "symbol", "ETH-USD")

    # Zero/negative tick size
    with pytest.raises(DomainValidationError):
        Instrument(
            symbol="BTC-USD",
            asset_class=AssetClass.CRYPTO,
            base_currency="BTC",
            quote_currency="USD",
            tick_size=Decimal("0.00"),
            lot_size=Decimal("0.0001"),
            min_order_quantity=Decimal("0.001"),
        )


def test_decimal_nan_and_infinity_rejection(sample_time: datetime) -> None:
    # NaN rejection
    with pytest.raises((DomainValidationError, ValidationError)):
        Position(
            symbol="BTC-USD",
            quantity=Decimal("NaN"),
            entry_price=Decimal("50000.00"),
            current_price=Decimal("50200.00"),
            unrealized_pnl=Decimal("200.00"),
            realized_pnl=Decimal("0.00"),
            timestamp_utc=sample_time,
        )

    # Infinity rejection
    with pytest.raises((DomainValidationError, ValidationError)):
        Bar(
            symbol="BTC-USD",
            timeframe=BarTimeframe.M1,
            event_start_utc=sample_time,
            event_end_utc=sample_time,
            knowledge_time_utc=sample_time,
            open=Decimal("Infinity"),
            high=Decimal("50500.00"),
            low=Decimal("49800.00"),
            close=Decimal("50200.00"),
            volume=Decimal("12.5"),
        )


def test_float_nan_and_infinity_rejection(sample_time: datetime) -> None:
    # NaN rejection on Signal direction
    with pytest.raises(DomainValidationError):
        Signal(
            strategy_id="MOM_01",
            symbol="BTC-USD",
            direction=float("nan"),
            expected_return=0.05,
            uncertainty=0.1,
            horizon_seconds=3600,
            timestamp_utc=sample_time,
        )

    # Infinity rejection on Signal expected_return
    with pytest.raises(DomainValidationError):
        Signal(
            strategy_id="MOM_01",
            symbol="BTC-USD",
            direction=0.5,
            expected_return=float("inf"),
            uncertainty=0.1,
            horizon_seconds=3600,
            timestamp_utc=sample_time,
        )

    # NaN in TargetAllocation weights
    with pytest.raises(DomainValidationError):
        TargetAllocation(
            weights={"BTC-USD": float("nan")},
            cash_weight=0.5,
            rationale="Test",
            timestamp_utc=sample_time,
        )


def test_deep_immutability(sample_time: datetime, sample_position: Position) -> None:
    # 1. Mutating input dictionary after construction should NOT affect model
    raw_positions = {"BTC-USD": sample_position}
    portfolio = PortfolioState(
        timestamp_utc=sample_time,
        positions=raw_positions,
        cash_balance=Decimal("10000.00"),
        total_equity=Decimal("60200.00"),
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("50200.00"),
        net_exposure=Decimal("50200.00"),
        unrealized_pnl=Decimal("200.00"),
        realized_pnl=Decimal("0.00"),
    )

    new_pos = Position(
        symbol="ETH-USD",
        quantity=Decimal("10.0"),
        entry_price=Decimal("3000.00"),
        current_price=Decimal("3000.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
        timestamp_utc=sample_time,
    )
    raw_positions["ETH-USD"] = new_pos
    assert "ETH-USD" not in portfolio.positions

    # 2. Mutating model's mapping directly must raise TypeError
    with pytest.raises(TypeError):
        portfolio.positions["ETH-USD"] = new_pos  # type: ignore

    # 3. Mutating TargetAllocation weights directly must raise TypeError
    raw_weights = {"BTC-USD": 0.6}
    target = TargetAllocation(
        weights=raw_weights,
        cash_weight=0.4,
        rationale="Momentum",
        timestamp_utc=sample_time,
    )
    raw_weights["ETH-USD"] = 0.4
    assert "ETH-USD" not in target.weights

    with pytest.raises(TypeError):
        target.weights["ETH-USD"] = 0.4  # type: ignore


def test_candlestick_geometry_invariants(sample_time: datetime) -> None:
    # High < Open
    with pytest.raises(InvariantViolationError):
        Bar(
            symbol="BTC-USD",
            timeframe=BarTimeframe.M1,
            event_start_utc=sample_time,
            event_end_utc=sample_time,
            knowledge_time_utc=sample_time,
            open=Decimal("50000.00"),
            high=Decimal("49900.00"),  # high < open
            low=Decimal("49500.00"),
            close=Decimal("49800.00"),
            volume=Decimal("10.0"),
        )

    # Low > Close
    with pytest.raises(InvariantViolationError):
        Bar(
            symbol="BTC-USD",
            timeframe=BarTimeframe.M1,
            event_start_utc=sample_time,
            event_end_utc=sample_time,
            knowledge_time_utc=sample_time,
            open=Decimal("50000.00"),
            high=Decimal("50500.00"),
            low=Decimal("50100.00"),  # low > close
            close=Decimal("50000.00"),
            volume=Decimal("10.0"),
        )


def test_temporal_ordering_invariants(sample_time: datetime) -> None:
    future_time = datetime(2026, 8, 27, 13, 0, 0, tzinfo=timezone.utc)
    past_time = datetime(2026, 8, 27, 11, 0, 0, tzinfo=timezone.utc)

    # event_end < event_start
    with pytest.raises(InvariantViolationError):
        Bar(
            symbol="BTC-USD",
            timeframe=BarTimeframe.M1,
            event_start_utc=sample_time,
            event_end_utc=past_time,
            knowledge_time_utc=sample_time,
            open=Decimal("50000.00"),
            high=Decimal("50500.00"),
            low=Decimal("49800.00"),
            close=Decimal("50200.00"),
            volume=Decimal("10.0"),
        )

    # knowledge_time < event_end
    with pytest.raises(InvariantViolationError):
        Bar(
            symbol="BTC-USD",
            timeframe=BarTimeframe.M1,
            event_start_utc=sample_time,
            event_end_utc=future_time,
            knowledge_time_utc=sample_time,  # precedes event_end
            open=Decimal("50000.00"),
            high=Decimal("50500.00"),
            low=Decimal("49800.00"),
            close=Decimal("50200.00"),
            volume=Decimal("10.0"),
        )


def test_market_snapshot_spread_invariants(sample_time: datetime) -> None:
    # Inverted spread: ask < bid
    with pytest.raises(InvariantViolationError):
        MarketDataSnapshot(
            symbol="BTC-USD",
            bid=Decimal("50200.00"),
            ask=Decimal("50100.00"),
            bid_size=Decimal("1.0"),
            ask_size=Decimal("1.0"),
            last_price=Decimal("50150.00"),
            timestamp_utc=sample_time,
        )


def test_target_allocation_semantic_boundary(sample_time: datetime) -> None:
    # TargetAllocation does NOT enforce sum(weights) + cash_weight = 1.0 in Phase 1
    target = TargetAllocation(
        weights={"BTC-USD": 0.8, "ETH-USD": 0.7},  # Gross = 1.5 (leveraged)
        cash_weight=-0.5,
        rationale="Leveraged allocation",
        timestamp_utc=sample_time,
    )
    assert target.weights["BTC-USD"] == 0.8
    assert target.weights["ETH-USD"] == 0.7
    assert target.cash_weight == -0.5


def test_order_status_lifecycle(sample_order: Order) -> None:
    assert sample_order.status == OrderStatus.PENDING
