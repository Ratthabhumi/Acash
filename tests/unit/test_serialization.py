"""Unit tests for domain model JSON and dictionary serialization and deserialization."""

from datetime import datetime, timezone
from decimal import Decimal
import json

from acash.core.domain.audit import DecisionRecord
from acash.core.domain.execution import Fill, Order
from acash.core.domain.instrument import Instrument
from acash.core.domain.market_data import Bar, MarketDataSnapshot
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.core.domain.signal import RiskAssessment, Signal, TargetAllocation


def test_serialization_roundtrips(
    sample_instrument: Instrument,
    sample_bar: Bar,
    sample_snapshot: MarketDataSnapshot,
    sample_position: Position,
    sample_portfolio: PortfolioState,
    sample_account: AccountState,
    sample_order: Order,
    sample_fill: Fill,
    sample_time: datetime,
) -> None:
    # 1. Instrument
    inst_dict = sample_instrument.model_dump()
    inst_recovered = Instrument(**inst_dict)
    assert inst_recovered == sample_instrument

    # 2. Bar
    bar_json = sample_bar.model_dump_json()
    bar_recovered = Bar.model_validate_json(bar_json)
    assert bar_recovered == sample_bar

    # 3. MarketDataSnapshot
    snap_json = sample_snapshot.model_dump_json()
    snap_recovered = MarketDataSnapshot.model_validate_json(snap_json)
    assert snap_recovered == sample_snapshot

    # 4. Position
    pos_json = sample_position.model_dump_json()
    pos_recovered = Position.model_validate_json(pos_json)
    assert pos_recovered == sample_position

    # 5. PortfolioState (with nested MappingProxyType positions)
    port_dict = sample_portfolio.model_dump()
    port_recovered = PortfolioState(**port_dict)
    assert port_recovered.total_equity == sample_portfolio.total_equity
    assert port_recovered.positions["BTC-USD"].quantity == Decimal("1.0")

    # 6. AccountState
    acc_json = sample_account.model_dump_json()
    acc_recovered = AccountState.model_validate_json(acc_json)
    assert acc_recovered == sample_account

    # 7. Order
    order_json = sample_order.model_dump_json()
    order_recovered = Order.model_validate_json(order_json)
    assert order_recovered == sample_order

    # 8. Fill
    fill_json = sample_fill.model_dump_json()
    fill_recovered = Fill.model_validate_json(fill_json)
    assert fill_recovered == sample_fill

    # 9. Signal, TargetAllocation, RiskAssessment, DecisionRecord
    signal = Signal(
        strategy_id="STRAT_1",
        symbol="BTC-USD",
        direction=1.0,
        expected_return=0.08,
        uncertainty=0.15,
        horizon_seconds=3600,
        timestamp_utc=sample_time,
    )
    target = TargetAllocation(
        weights={"BTC-USD": 0.5},
        cash_weight=0.5,
        rationale="Trend Following",
        timestamp_utc=sample_time,
    )
    risk = RiskAssessment(
        approved=True,
        adjusted_weights={"BTC-USD": 0.5},
        rejection_reason=None,
        max_drawdown_pct=0.05,
        risk_utilization_pct=0.5,
        timestamp_utc=sample_time,
    )
    decision = DecisionRecord(
        decision_id="DEC_001",
        timestamp_utc=sample_time,
        inputs_snapshot_ref="snap_ref_01",
        signal_ref="sig_01",
        target_allocation=target,
        risk_assessment=risk,
        correlation_id="corr_001",
        schema_version="1.0.0",
    )

    dec_json = decision.model_dump_json()
    dec_recovered = DecisionRecord.model_validate_json(dec_json)
    assert dec_recovered.decision_id == decision.decision_id
    assert dec_recovered.correlation_id == decision.correlation_id
    assert dec_recovered.target_allocation is not None
    assert dec_recovered.target_allocation.weights["BTC-USD"] == 0.5
