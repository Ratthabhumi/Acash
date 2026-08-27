"""Shared fixtures for ACASH unit tests."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from acash.core.domain.enums import AssetClass, BarTimeframe, OrderSide, OrderStatus, OrderType
from acash.core.domain.execution import Fill, Order
from acash.core.domain.instrument import Instrument
from acash.core.domain.market_data import Bar, MarketDataSnapshot
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.core.domain.signal import RiskAssessment, Signal, TargetAllocation


@pytest.fixture
def sample_time() -> datetime:
    return datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_instrument() -> Instrument:
    return Instrument(
        symbol="BTC-USD",
        asset_class=AssetClass.CRYPTO,
        base_currency="BTC",
        quote_currency="USD",
        tick_size=Decimal("0.01"),
        lot_size=Decimal("0.0001"),
        min_order_quantity=Decimal("0.001"),
    )


@pytest.fixture
def sample_bar(sample_time: datetime) -> Bar:
    return Bar(
        symbol="BTC-USD",
        timeframe=BarTimeframe.M1,
        event_start_utc=sample_time,
        event_end_utc=sample_time,
        knowledge_time_utc=sample_time,
        open=Decimal("50000.00"),
        high=Decimal("50500.00"),
        low=Decimal("49800.00"),
        close=Decimal("50200.00"),
        volume=Decimal("12.5"),
        provenance_hash="hash_123",
    )


@pytest.fixture
def sample_snapshot(sample_time: datetime) -> MarketDataSnapshot:
    return MarketDataSnapshot(
        symbol="BTC-USD",
        bid=Decimal("50190.00"),
        ask=Decimal("50210.00"),
        bid_size=Decimal("1.5"),
        ask_size=Decimal("2.0"),
        last_price=Decimal("50200.00"),
        timestamp_utc=sample_time,
    )


@pytest.fixture
def sample_position(sample_time: datetime) -> Position:
    return Position(
        symbol="BTC-USD",
        quantity=Decimal("1.0"),
        entry_price=Decimal("50000.00"),
        current_price=Decimal("50200.00"),
        unrealized_pnl=Decimal("200.00"),
        realized_pnl=Decimal("0.00"),
        timestamp_utc=sample_time,
    )


@pytest.fixture
def sample_portfolio(sample_time: datetime, sample_position: Position) -> PortfolioState:
    return PortfolioState(
        timestamp_utc=sample_time,
        positions={"BTC-USD": sample_position},
        cash_balance=Decimal("10000.00"),
        total_equity=Decimal("60200.00"),  # 10000 cash + (1.0 * 50200)
        margin_used=Decimal("0.00"),
        gross_exposure=Decimal("50200.00"),
        net_exposure=Decimal("50200.00"),
        unrealized_pnl=Decimal("200.00"),
        realized_pnl=Decimal("0.00"),
    )


@pytest.fixture
def sample_account(sample_time: datetime) -> AccountState:
    return AccountState(
        account_id="ACC_001",
        currency="USD",
        balance=Decimal("10000.00"),
        equity=Decimal("60200.00"),
        free_margin=Decimal("60200.00"),
        margin_level_pct=None,
        leverage=1.0,
        is_live=False,
        timestamp_utc=sample_time,
    )


@pytest.fixture
def sample_order(sample_time: datetime) -> Order:
    return Order(
        order_id="ORD_001",
        symbol="BTC-USD",
        order_type=OrderType.LIMIT,
        side=OrderSide.BUY,
        quantity=Decimal("0.5"),
        price_limit=Decimal("50000.00"),
        status=OrderStatus.PENDING,
        idempotency_key="idemp_001",
        correlation_id="corr_001",
        created_at_utc=sample_time,
    )


@pytest.fixture
def sample_fill(sample_time: datetime) -> Fill:
    return Fill(
        fill_id="FILL_001",
        order_id="ORD_001",
        symbol="BTC-USD",
        side=OrderSide.BUY,
        fill_price=Decimal("50000.00"),
        fill_quantity=Decimal("0.5"),
        fee=Decimal("2.50"),
        slippage=Decimal("0.00"),
        correlation_id="corr_001",
        timestamp_utc=sample_time,
    )
