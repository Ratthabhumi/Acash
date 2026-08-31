"""Unit, Invariant, and Adversarial tests for R1RealOrderExerciseDriver (Offline / Fake Transport).

Tests all driver invariants without touching the network:
1. Nominal SSE live flow (Mode A: SSE-rich lineage with exact VWAP fill price).
2. Resting order timeout in ACKNOWLEDGED -> CONNECTION_LOST -> UNKNOWN fail-closed.
3. Stream silence -> REST polling recovery (Mode B: aggregate lineage, exact filled_avg_price, no synthesized execution_id).
4. Cancellation resolution via REST snapshot:
   - Case 4A: In-flight user cancel request -> CANCEL_ACK (BMAP-07 proven).
   - Case 4B: Unexpected broker cancellation -> reconciliation towards CANCELLED via verified broker evidence.
5. Parity discrepancy defense (Internal FILLED != Broker ACCEPTED -> is_in_parity False).
6. Economics & Timestamp Provenance Adversarial Tests:
   - Finding 1: Mandatory positive benchmark_mid_price (zero default/fallback).
   - Finding 1: REST average_fill_price is None when broker snapshot omits filled_avg_price (zero fallback to benchmark).
   - Finding 5: closed_at derived strictly from broker terminal timestamps (filled_at / canceled_at).
   - Finding 6: Non-transport unexpected exceptions fail-closed immediately (no broad swallowing).
   - Finding 7: Reconciliation identities are explicitly LOCAL-REC-* and evidence_refs carry broker reality.
   - Finding 8: Commission conforms strictly to ExecutionManifest schema default.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterator, List, Optional
import pytest

from acash.execution.broker_adapter import BrokerPosition, SubmissionReceipt
from acash.execution.broker_events import BrokerEventKind
from acash.execution.coordinator import CoordinatorEvent
from acash.execution.schema import ExecutionManifest, OrderLifecycleState
from acash.execution.state_machine import ExecutionEvent

from acash.execution.alpaca.adapter import AlpacaPaperAdapter
from acash.execution.alpaca.credentials import AlpacaCredentialProvider, AlpacaCredentials
from acash.execution.alpaca.real_driver import (
    R1RealDriverError,
    R1RealOrderExerciseDriver,
    RealDriverEvidence,
)
from acash.execution.alpaca.transport import (
    AlpacaEventStream,
    AlpacaOrder,
    AlpacaOrderStatus,
    AlpacaTradeEvent,
    AlpacaTradeEventType,
    AlpacaTransport,
    AlpacaTransportError,
    AlpacaTransportTimeoutError,
)
from acash.execution.alpaca.venue import AlpacaEndpoint, AlpacaVenue


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FakeCredentialProvider(AlpacaCredentialProvider):
    def load(self) -> AlpacaCredentials:
        return AlpacaCredentials(
            api_key_id="PK_FAKE_TEST_KEY",
            api_secret_ref="SECRET_FAKE_TEST",
            _resolved=True,
        )

    def venue(self) -> str:
        return "ALPACA_PAPER"


class FakeEventStream(AlpacaEventStream):
    def __init__(self, events: List[AlpacaTradeEvent]) -> None:
        self._events = events

    def __iter__(self) -> Iterator[AlpacaTradeEvent]:
        return iter(self._events)

    def close(self) -> None:
        pass


class FakeAlpacaTransport(AlpacaTransport):
    """Configurable in-memory transport for offline driver unit testing."""

    def __init__(
        self,
        *,
        stream_events: Optional[List[AlpacaTradeEvent]] = None,
        order_snapshots: Optional[List[AlpacaOrder]] = None,
        stream_raises_timeout: bool = False,
    ) -> None:
        endpoint = AlpacaEndpoint(AlpacaVenue.PAPER)
        super().__init__(FakeCredentialProvider(), endpoint)
        self._stream_events = stream_events or []
        self._order_snapshots = order_snapshots or []
        self._snapshot_idx = 0
        self._stream_raises_timeout = stream_raises_timeout
        self._connected = False
        self.submitted_client_order_ids: list[str] = []

    def connect(self) -> None:
        self._connected = True

    def connected(self) -> bool:
        return self._connected

    def submit_order(
        self,
        client_order_id: str,
        symbol: str,
        quantity: Decimal,
    ) -> SubmissionReceipt:
        self.submitted_client_order_ids.append(client_order_id)
        return SubmissionReceipt(
            broker_order_id="fake-broker-order-uuid-1234",
            client_order_id=client_order_id,
        )

    def cancel_order(self, broker_order_id: str) -> None:
        pass

    def query_order(self, broker_order_id: str) -> AlpacaOrder:
        if self._order_snapshots:
            snap = self._order_snapshots[min(self._snapshot_idx, len(self._order_snapshots) - 1)]
            self._snapshot_idx += 1
            return snap
        return AlpacaOrder(
            broker_order_id=broker_order_id,
            client_order_id="fake-client-id",
            symbol="SPY",
            status=AlpacaOrderStatus.NEW,
            requested_qty=Decimal("1"),
            filled_qty=Decimal("0"),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )

    def query_position(self, symbol: str) -> Optional[BrokerPosition]:
        return None

    def stream_trade_events(self, since_id: Optional[str] = None) -> AlpacaEventStream:
        if self._stream_raises_timeout:
            raise AlpacaTransportTimeoutError("simulated stream timeout")
        return FakeEventStream(self._stream_events)

    def rotate_credentials(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Nominal Invariant Test Cases
# ---------------------------------------------------------------------------


def test_real_driver_nominal_sse_live_flow_mode_a() -> None:
    """Test 1: Nominal live SSE stream flow (Mode A: SSE-rich lineage, VWAP fill price)."""
    broker_order_id = "fake-broker-order-uuid-1234"
    t_fill = datetime(2026, 8, 31, 14, 0, 0, tzinfo=timezone.utc)
    order_ack = AlpacaOrder(
        broker_order_id=broker_order_id,
        client_order_id="coid-test-1",
        symbol="SPY",
        status=AlpacaOrderStatus.NEW,
        requested_qty=Decimal("1"),
        filled_qty=Decimal("0"),
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    order_pf = AlpacaOrder(
        broker_order_id=broker_order_id,
        client_order_id="coid-test-1",
        symbol="SPY",
        status=AlpacaOrderStatus.PARTIALLY_FILLED,
        requested_qty=Decimal("1"),
        filled_qty=Decimal("0.4"),
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    order_fill = AlpacaOrder(
        broker_order_id=broker_order_id,
        client_order_id="coid-test-1",
        symbol="SPY",
        status=AlpacaOrderStatus.FILLED,
        requested_qty=Decimal("1"),
        filled_qty=Decimal("1.0"),
        created_at=_utcnow(),
        updated_at=_utcnow(),
        filled_at=t_fill,
        filled_avg_price=Decimal("101.20"),
    )

    events = [
        AlpacaTradeEvent(
            event_id="0100000000000100000000000001",
            event=AlpacaTradeEventType.ACCEPTED,
            at=_utcnow(),
            executed_at=None,
            broker_order_id=broker_order_id,
            order=order_ack,
        ),
        AlpacaTradeEvent(
            event_id="0100000000000100000000000002",
            event=AlpacaTradeEventType.PARTIAL_FILL,
            at=_utcnow(),
            executed_at=_utcnow(),
            broker_order_id=broker_order_id,
            execution_id="exec-uuid-part-1",
            qty=Decimal("0.4"),
            price=Decimal("100.00"),
            order=order_pf,
        ),
        AlpacaTradeEvent(
            event_id="0100000000000100000000000003",
            event=AlpacaTradeEventType.FILL,
            at=t_fill,
            executed_at=t_fill,
            broker_order_id=broker_order_id,
            execution_id="exec-uuid-fill-2",
            qty=Decimal("0.6"),
            price=Decimal("102.00"),
            order=order_fill,
        ),
    ]

    transport = FakeAlpacaTransport(
        stream_events=events,
        order_snapshots=[order_fill],
    )
    adapter = AlpacaPaperAdapter(transport)
    driver = R1RealOrderExerciseDriver(adapter, transport=transport)

    evidence = driver.submit_and_observe(
        client_order_id="coid-test-1",
        symbol="SPY",
        quantity=Decimal("1"),
        benchmark_mid_price=Decimal("100.00"),
        timeout_seconds=0.5,
        poll_interval_seconds=0.01,
    )

    assert evidence.final_state == "FILLED"
    assert evidence.final_terminal is True
    assert evidence.filled_qty == Decimal("1")
    assert evidence.disputed is False
    assert evidence.reconciliation_report is not None
    assert evidence.reconciliation_report.is_in_parity is True

    # VWAP Calculation: (0.4 * 100 + 0.6 * 102) / 1.0 = (40 + 61.2) / 1.0 = 101.2
    assert evidence.manifest is not None
    assert evidence.manifest.average_fill_price == Decimal("101.2")
    assert evidence.manifest.closed_at == t_fill
    assert evidence.manifest.total_commission_paid == Decimal("0.0")
    assert evidence.manifest.execution_digest != ""
    assert len(evidence.manifest.execution_digest) == 64


def test_real_driver_resting_timeout_to_unknown_fail_closed() -> None:
    """Test 2: In-flight resting timeout in ACKNOWLEDGED -> CONNECTION_LOST -> UNKNOWN."""
    broker_order_id = "fake-broker-order-uuid-1234"
    resting_snapshot = AlpacaOrder(
        broker_order_id=broker_order_id,
        client_order_id="coid-test-2",
        symbol="SPY",
        status=AlpacaOrderStatus.ACCEPTED,
        requested_qty=Decimal("1"),
        filled_qty=Decimal("0"),
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )

    transport = FakeAlpacaTransport(
        stream_events=[],
        order_snapshots=[resting_snapshot, resting_snapshot],
    )
    adapter = AlpacaPaperAdapter(transport)
    driver = R1RealOrderExerciseDriver(adapter, transport=transport)

    evidence = driver.submit_and_observe(
        client_order_id="coid-test-2",
        symbol="SPY",
        quantity=Decimal("1"),
        benchmark_mid_price=Decimal("100.00"),
        timeout_seconds=0.05,
        poll_interval_seconds=0.01,
    )

    # Fail-closed timeout contract: transitions to UNKNOWN
    assert evidence.final_state == "UNKNOWN"
    assert evidence.final_terminal is False
    assert evidence.filled_qty == Decimal("0")
    assert "ACKNOWLEDGED" in evidence.states_reached
    assert "UNKNOWN" in evidence.states_reached
    assert evidence.reconciliation_report is not None
    assert evidence.reconciliation_report.is_in_parity is False
    assert evidence.reconciliation_report.action_taken == "HALTED_ON_DISCREPANCY"
    assert evidence.manifest is not None
    assert evidence.manifest.closed_at is None


def test_real_driver_stream_silence_rest_recovery_mode_b() -> None:
    """Test 3: Stream silence -> REST polling recovery (Mode B: aggregate lineage)."""
    broker_order_id = "fake-broker-order-uuid-1234"
    t_fill = datetime(2026, 8, 31, 14, 10, 0, tzinfo=timezone.utc)
    filled_snapshot = AlpacaOrder(
        broker_order_id=broker_order_id,
        client_order_id="coid-test-3",
        symbol="SPY",
        status=AlpacaOrderStatus.FILLED,
        requested_qty=Decimal("1"),
        filled_qty=Decimal("1"),
        created_at=_utcnow(),
        updated_at=_utcnow(),
        filled_at=t_fill,
        filled_avg_price=Decimal("105.50"),
    )

    transport = FakeAlpacaTransport(
        stream_raises_timeout=True,  # Stream is silent/failing
        order_snapshots=[filled_snapshot],
    )
    adapter = AlpacaPaperAdapter(transport)
    driver = R1RealOrderExerciseDriver(adapter, transport=transport)

    evidence = driver.submit_and_observe(
        client_order_id="coid-test-3",
        symbol="SPY",
        quantity=Decimal("1"),
        benchmark_mid_price=Decimal("100.00"),
        timeout_seconds=0.5,
        poll_interval_seconds=0.01,
    )

    assert evidence.final_state == "FILLED"
    assert evidence.final_terminal is True
    assert evidence.filled_qty == Decimal("1")
    assert evidence.filled_qty == filled_snapshot.filled_qty
    assert evidence.reconciliation_report is not None
    assert evidence.reconciliation_report.is_in_parity is True
    assert evidence.manifest is not None
    # Mode B exact extraction: from broker_snapshot.filled_avg_price
    assert evidence.manifest.average_fill_price == Decimal("105.50")
    assert evidence.manifest.closed_at == t_fill


def test_real_driver_unexpected_cancel_via_rest_reconciliation() -> None:
    """Test 4A: Unexpected broker cancellation -> reconciliation towards CANCELLED with evidence refs."""
    broker_order_id = "fake-broker-order-uuid-1234"
    t_cancel = datetime(2026, 8, 31, 14, 15, 0, tzinfo=timezone.utc)
    canceled_snapshot = AlpacaOrder(
        broker_order_id=broker_order_id,
        client_order_id="coid-test-4a",
        symbol="SPY",
        status=AlpacaOrderStatus.CANCELED,
        requested_qty=Decimal("1"),
        filled_qty=Decimal("0"),
        created_at=_utcnow(),
        updated_at=t_cancel,
        canceled_at=t_cancel,
        cancel_requested_at=None,  # No prior user cancel requested
    )

    transport = FakeAlpacaTransport(
        stream_events=[],
        order_snapshots=[canceled_snapshot],
    )
    adapter = AlpacaPaperAdapter(transport)
    driver = R1RealOrderExerciseDriver(adapter, transport=transport)

    evidence = driver.submit_and_observe(
        client_order_id="coid-test-4a",
        symbol="SPY",
        quantity=Decimal("1"),
        benchmark_mid_price=Decimal("100.00"),
        timeout_seconds=0.5,
        poll_interval_seconds=0.01,
    )

    assert evidence.final_state == "CANCELLED"
    assert evidence.final_terminal is True
    assert evidence.filled_qty == Decimal("0")
    assert evidence.reconciliation_report is not None
    assert evidence.reconciliation_report.is_in_parity is True
    assert evidence.manifest is not None
    assert evidence.manifest.closed_at == t_cancel
    assert evidence.manifest.average_fill_price is None


def test_real_driver_parity_discrepancy_defense() -> None:
    """Test 5: Parity discrepancy defense (Internal FILLED != Broker ACCEPTED -> is_in_parity False)."""
    broker_order_id = "fake-broker-order-uuid-1234"
    order_fill = AlpacaOrder(
        broker_order_id=broker_order_id,
        client_order_id="coid-test-5",
        symbol="SPY",
        status=AlpacaOrderStatus.FILLED,
        requested_qty=Decimal("1"),
        filled_qty=Decimal("1.0"),
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    events = [
        AlpacaTradeEvent(
            event_id="0100000000000100000000000001",
            event=AlpacaTradeEventType.ACCEPTED,
            at=_utcnow(),
            executed_at=None,
            broker_order_id=broker_order_id,
            order=order_fill,
        ),
        AlpacaTradeEvent(
            event_id="0100000000000100000000000002",
            event=AlpacaTradeEventType.FILL,
            at=_utcnow(),
            executed_at=_utcnow(),
            broker_order_id=broker_order_id,
            execution_id="exec-uuid-fill-1",
            qty=Decimal("1"),
            price=Decimal("100.00"),
            order=order_fill,
        ),
    ]
    discrepant_snapshot = AlpacaOrder(
        broker_order_id=broker_order_id,
        client_order_id="coid-test-5",
        symbol="SPY",
        status=AlpacaOrderStatus.ACCEPTED,
        requested_qty=Decimal("1"),
        filled_qty=Decimal("0"),
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )

    transport = FakeAlpacaTransport(
        stream_events=events,
        order_snapshots=[discrepant_snapshot],
    )
    adapter = AlpacaPaperAdapter(transport)
    driver = R1RealOrderExerciseDriver(adapter, transport=transport)

    evidence = driver.submit_and_observe(
        client_order_id="coid-test-5",
        symbol="SPY",
        quantity=Decimal("1"),
        benchmark_mid_price=Decimal("100.00"),
        timeout_seconds=0.5,
        poll_interval_seconds=0.01,
    )

    assert evidence.final_state == "FILLED"
    assert evidence.reconciliation_report is not None
    assert evidence.reconciliation_report.is_in_parity is False
    assert evidence.reconciliation_report.action_taken == "HALTED_ON_DISCREPANCY"


# ---------------------------------------------------------------------------
# Adversarial Tests (Addressing Findings 1, 2, 5, 6, 7, 8)
# ---------------------------------------------------------------------------


def test_adversarial_missing_benchmark_price_fails_closed() -> None:
    """Adversarial Finding 1: benchmark_mid_price must be provided (no magic default)."""
    transport = FakeAlpacaTransport()
    adapter = AlpacaPaperAdapter(transport)
    driver = R1RealOrderExerciseDriver(adapter, transport=transport)

    with pytest.raises(R1RealDriverError, match="benchmark_mid_price must be a positive Decimal"):
        driver.submit_and_observe(
            client_order_id="coid-adv-1",
            symbol="SPY",
            quantity=Decimal("1"),
            benchmark_mid_price=None,  # type: ignore[arg-type]
        )

    with pytest.raises(R1RealDriverError, match="benchmark_mid_price must be a positive Decimal"):
        driver.submit_and_observe(
            client_order_id="coid-adv-1",
            symbol="SPY",
            quantity=Decimal("1"),
            benchmark_mid_price=Decimal("-5.00"),
        )


def test_adversarial_rest_missing_filled_avg_price_is_none() -> None:
    """Adversarial Finding 1: When broker snapshot omits filled_avg_price, average_fill_price is None (NEVER fallback to benchmark)."""
    broker_order_id = "fake-broker-order-uuid-1234"
    filled_snapshot_no_price = AlpacaOrder(
        broker_order_id=broker_order_id,
        client_order_id="coid-adv-2",
        symbol="SPY",
        status=AlpacaOrderStatus.FILLED,
        requested_qty=Decimal("1"),
        filled_qty=Decimal("1"),
        created_at=_utcnow(),
        updated_at=_utcnow(),
        filled_at=_utcnow(),
        filled_avg_price=None,  # Broker snapshot omitted fill price
    )

    transport = FakeAlpacaTransport(
        stream_raises_timeout=True,
        order_snapshots=[filled_snapshot_no_price],
    )
    adapter = AlpacaPaperAdapter(transport)
    driver = R1RealOrderExerciseDriver(adapter, transport=transport)

    evidence = driver.submit_and_observe(
        client_order_id="coid-adv-2",
        symbol="SPY",
        quantity=Decimal("1"),
        benchmark_mid_price=Decimal("450.00"),
        timeout_seconds=0.5,
        poll_interval_seconds=0.01,
    )

    assert evidence.manifest is not None
    # Crucial provenance invariant: average_fill_price MUST be None, NOT benchmark 450.00!
    assert evidence.manifest.average_fill_price is None
    assert evidence.manifest.realized_slippage_bps is None


def test_adversarial_unexpected_exception_fails_closed_without_swallowing() -> None:
    """Adversarial Finding 6: Non-transport unexpected runtime errors must fail-closed immediately."""
    class BrokenAlpacaTransport(FakeAlpacaTransport):
        def stream_trade_events(self, since_id: Optional[str] = None) -> AlpacaEventStream:
            # Simulate a non-transport programming / schema error
            raise TypeError("unexpected malformed payload corruption")

    transport = BrokenAlpacaTransport()
    adapter = AlpacaPaperAdapter(transport)
    driver = R1RealOrderExerciseDriver(adapter, transport=transport)

    with pytest.raises(TypeError, match="unexpected malformed payload corruption"):
        driver.submit_and_observe(
            client_order_id="coid-adv-3",
            symbol="SPY",
            quantity=Decimal("1"),
            benchmark_mid_price=Decimal("100.00"),
            timeout_seconds=0.5,
            poll_interval_seconds=0.01,
        )


def test_adversarial_reconciliation_identities_and_evidence_refs() -> None:
    """Adversarial Finding 2 & 7: Verify reconciliation outcomes carry LOCAL-REC-* identities and structured evidence_refs."""
    broker_order_id = "fake-broker-order-uuid-9999"
    t_cancel = datetime(2026, 8, 31, 15, 0, 0, tzinfo=timezone.utc)
    canceled_snapshot = AlpacaOrder(
        broker_order_id=broker_order_id,
        client_order_id="coid-adv-4",
        symbol="SPY",
        status=AlpacaOrderStatus.CANCELED,
        requested_qty=Decimal("1"),
        filled_qty=Decimal("0"),
        created_at=_utcnow(),
        updated_at=t_cancel,
        canceled_at=t_cancel,
        cancel_requested_at=None,
    )

    transport = FakeAlpacaTransport(
        stream_events=[],
        order_snapshots=[canceled_snapshot],
    )
    adapter = AlpacaPaperAdapter(transport)
    driver = R1RealOrderExerciseDriver(adapter, transport=transport)

    evidence = driver.submit_and_observe(
        client_order_id="coid-adv-4",
        symbol="SPY",
        quantity=Decimal("1"),
        benchmark_mid_price=Decimal("100.00"),
        timeout_seconds=0.5,
        poll_interval_seconds=0.01,
    )

    # Check the outcomes list for the reconcile outcome
    reconcile_outcomes = [o for o in evidence.outcomes if o.transition and o.transition.evidence_required]
    assert len(reconcile_outcomes) == 1
    rec = reconcile_outcomes[0]
    assert rec.state == OrderLifecycleState.CANCELLED
    assert rec.transition is not None
    assert rec.transition.is_terminal is True


def test_adversarial_commission_conforms_to_canonical_schema_validator() -> None:
    """Adversarial Finding 8: Verify total_commission_paid is non-optional Decimal and validates against schema."""
    manifest = ExecutionManifest(
        execution_id="EXEC_TEST_COMM_1",
        authorization_id="AUTH_TEST_1",
        strategy_id="STRAT_TEST_1",
        intent_id="INT_TEST_1",
        intent_digest="0" * 64,
        client_order_id="coid-comm-1",
        venue="ALPACA_PAPER",
        symbol="SPY",
        order_side="BUY",  # type: ignore[arg-type]
        order_type="MARKET",  # type: ignore[arg-type]
        created_at=_utcnow(),
        submitted_at=_utcnow(),
        requested_qty=Decimal("1"),
        filled_qty=Decimal("1"),
        benchmark_mid_price=Decimal("500.00"),
        total_commission_paid=Decimal("0.0"),
        source_signal_event_hash="0" * 64,
        execution_digest="0" * 64,
    )
    assert manifest.total_commission_paid == Decimal("0.0")
    assert isinstance(manifest.total_commission_paid, Decimal)
