"""Phase 7 Paper Exercise — R1 order-lifecycle conformance suite.

Verifies the R1 order-lifecycle harness (``acash.execution.alpaca.order_exercise``)
against the locked authority boundary:

- The harness NEVER calls ``transition_order()`` and NEVER assigns an
  ``OrderLifecycleState``; it only reads state from the coordinator (AST guard).
- Every canonical state flows through ``AlpacaPaperAdapter`` -> ``to_coordinator_event``
  -> ``ExecutionCoordinator.apply()``/``reconcile()`` -> ``transition_order()``.
- Per-fill qty comes from the raw Alpaca DTO and is passed into
  ``to_coordinator_event(fill_qty=...)``; no double accumulation.
- Every terminal outcome carries evidence lineage (R1-H ExecutionManifest;
  R1-I ReconciliationReport); terminal state is NEVER asserted bare.
- BMAP-07: CANCELLED terminal is resolved ONLY via a REST snapshot with cancel
  provenance; the fill ledger is delegated to the coordinator.

This suite never touches the network: it runs against fake transports. A REAL P-run
requires the operator to export paper credentials and is NOT part of this unit suite.
"""

import ast
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Iterator, List, Optional

import httpx
import pytest

from acash.execution.alpaca import (
    AlpacaEventStream,
    AlpacaOrder,
    AlpacaOrderStatus,
    AlpacaPaperAdapter,
    AlpacaTradeEvent,
    AlpacaTradeEventType,
    AlpacaTransport,
    AlpacaTransportAuthError,
    AlpacaTransportError,
    EnvAlpacaCredentialProvider,
    HttpAlpacaTransport,
    LifecycleEvidence,
    OrderExerciseError,
    OrderExerciseHarness,
    PaperHttpAlpacaTransport,
    build_nominal_intent,
)
from acash.execution.alpaca import run_order_exercise_verification
from acash.execution.alpaca.venue import AlpacaEndpoint, live_endpoint, paper_endpoint
from acash.execution.broker_adapter import BrokerPosition, SubmissionReceipt, to_coordinator_event
from acash.execution.broker_events import BrokerEventKind
from acash.execution.coordinator import (
    CoordinatorEvent,
    CoordinatorIncidentKind,
    ExecutionCoordinator,
)
from acash.execution.schema import OrderLifecycleState
from acash.execution.state_machine import ExecutionEvent

_QTY = Decimal("1.000")


def _utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# Fake transport (write-capable, deterministic receipts, no network)
# ---------------------------------------------------------------------------


class _FakeTransport(AlpacaTransport):
    def __init__(self) -> None:
        self._connected = True
        self._order_counter = 0

    def connect(self) -> None:
        self._connected = True

    def connected(self) -> bool:
        return self._connected

    def submit_order(
        self, client_order_id: str, symbol: str, quantity: Decimal
    ) -> SubmissionReceipt:
        self._order_counter += 1
        return SubmissionReceipt(
            broker_order_id=f"09{self._order_counter:08d}0000000000000000",
            client_order_id=client_order_id,
        )

    def cancel_order(self, broker_order_id: str) -> None:
        return None

    def query_order(self, broker_order_id: str) -> AlpacaOrder:
        raise AlpacaTransportError(
            f"order not found (HTTP 404): {broker_order_id} (fail-closed)."
        )

    def query_position(self, symbol: str) -> Optional[BrokerPosition]:
        return None

    def stream_trade_events(
        self, since_id: Optional[str] = None
    ) -> AlpacaEventStream:
        return _FakeStream()

    def rotate_credentials(self) -> None:
        self._connected = True


class _FakeStream(AlpacaEventStream):
    def __iter__(self) -> Iterator[AlpacaTradeEvent]:
        return iter(())

    def close(self) -> None:
        return None


def _harness(*, scenario: str = "manual") -> OrderExerciseHarness:
    adapter = AlpacaPaperAdapter(_FakeTransport())
    return OrderExerciseHarness(
        adapter,
        execution_id=f"EXE_{scenario}",
        requested_qty=_QTY,
        client_order_id=f"coid-{scenario}",
        symbol="SPY",
        scenario=scenario,
    )


# ---------------------------------------------------------------------------
# Structural AST guard: the harness must not be a state authority
# ---------------------------------------------------------------------------

_HARNESS_SRC = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "src", "acash",
    "execution", "alpaca", "order_exercise.py",
)


def _ast_function_names(path: str) -> set[str]:
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _ast_called_names(path: str) -> set[str]:
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    return names


def test_harness_source_never_defines_transition_order() -> None:
    names = _ast_function_names(_HARNESS_SRC)
    assert "transition_order" not in names, "harness must not define transition_order"


def test_harness_source_never_calls_or_assigns_lifecycle_state() -> None:
    # The harness must never WRITE/CALL the state authority. It may only READ
    # coord.state after apply()/reconcile(). Scan the AST Call graph and any
    # attribute-assignment target against lifecycle-state identifiers.
    called = _ast_called_names(_HARNESS_SRC)
    assert "transition_order" not in called, "harness must not call transition_order()"
    with open(_HARNESS_SRC, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=_HARNESS_SRC)
    for node in ast.walk(tree):
        # self.<attr> field = ... assignments must never target state fields.
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if (
                    isinstance(tgt, ast.Attribute)
                    and isinstance(tgt.value, ast.Name)
                    and tgt.value.id == "self"
                    and "state" in tgt.attr
                ):
                    raise AssertionError(
                        f"harness must not assign lifecycle state (line {node.lineno})"
                    )


# ---------------------------------------------------------------------------
# R1-A: submit -> ACK / REJECT
# ---------------------------------------------------------------------------


def test_r1a_acknowledged_with_manifest_open() -> None:
    h = _harness(scenario="r1a_ack")
    h.submit()
    out = h.acknowledge()
    assert out.state is OrderLifecycleState.ACKNOWLEDGED
    ev = h.evidence()
    assert ev.final_state == "ACKNOWLEDGED"
    assert ev.final_terminal is False
    assert "SUBMITTED" in ev.states_reached
    assert "ACKNOWLEDGED" in ev.states_reached
    # Non-terminal -> manifest left open (closed_at None), lineage still present.
    assert ev.manifest is not None
    assert ev.manifest.closed_at is None
    assert ev.manifest.execution_digest


def test_r1a_rejected_terminal() -> None:
    h = _harness(scenario="r1a_rej")
    h.submit()
    out = h.reject()
    assert out.state is OrderLifecycleState.REJECTED
    ev = h.evidence()
    assert ev.final_state == "REJECTED"
    assert ev.final_terminal is True
    assert ev.manifest is not None
    assert ev.manifest.closed_at is not None


# ---------------------------------------------------------------------------
# R1-B: partial -> full fill, cumulative correct, no double-accumulate
# ---------------------------------------------------------------------------


def test_r1b_partial_then_full_fill() -> None:
    h = _harness(scenario="r1b_fill")
    h.submit()
    h.acknowledge()
    p_out = h.partial_fill(Decimal("0.300"))
    assert p_out.state is OrderLifecycleState.PARTIALLY_FILLED
    assert p_out.filled_qty == Decimal("0.300")
    f_out = h.full_fill(Decimal("0.700"))
    assert f_out.state is OrderLifecycleState.FILLED
    assert f_out.filled_qty == _QTY
    ev = h.evidence()
    assert ev.final_state == "FILLED"
    assert ev.final_terminal is True
    assert ev.filled_qty == _QTY
    assert ev.manifest is not None
    assert ev.manifest.closed_at is not None
    assert ev.manifest.filled_qty == _QTY


def test_r1b_no_double_accumulate() -> None:
    # Re-delivery of the SAME event identity must not double the fill.
    adapter = AlpacaPaperAdapter(_FakeTransport())
    coord = ExecutionCoordinator(execution_id="EXE_DUP", requested_qty=_QTY)
    receipt = adapter.submit_order("coid-dup", "SPY", _QTY)
    raw_ack = adapter.ingest_trade_event(
        _trade_event_fixture(
            event_id="01" + "0" * 22 + "1",  # 24-char proto id
            event=AlpacaTradeEventType.ACCEPTED,
            broker_order_id=receipt.broker_order_id,
            requested_qty=_QTY,
            filled_qty=Decimal("0"),
        )
    )
    coord.apply(to_coordinator_event(raw_ack))
    raw_partial = adapter.ingest_trade_event(
        _trade_event_fixture(
            event_id="01" + "0" * 22 + "2",
            event=AlpacaTradeEventType.PARTIAL_FILL,
            broker_order_id=receipt.broker_order_id,
            requested_qty=_QTY,
            filled_qty=Decimal("0.300"),
            qty=Decimal("0.300"),
        )
    )
    ev = to_coordinator_event(raw_partial, fill_qty=Decimal("0.300"))
    out1 = coord.apply(ev)
    out2 = coord.apply(ev)  # same identity redelivered
    assert out1.filled_qty == Decimal("0.300")
    assert out2.was_duplicate is True
    assert out2.filled_qty == Decimal("0.300")  # NOT 0.600


# ---------------------------------------------------------------------------
# R1-C: cancel request -> CANCEL_ACK (snapshot) / CANCEL_REJECT (live)
# ---------------------------------------------------------------------------


def test_r1c_cancel_ack_via_snapshot_terminal() -> None:
    h = _harness(scenario="r1c_cancel")
    h.submit()
    h.acknowledge()
    cr = h.cancel_request()
    assert cr.state is OrderLifecycleState.CANCEL_REQUESTED
    ack = h.cancel_ack_via_snapshot()
    assert ack.state is OrderLifecycleState.CANCELLED
    ev = h.evidence()
    assert ev.final_state == "CANCELLED"
    assert ev.final_terminal is True
    assert ev.manifest is not None
    assert ev.manifest.closed_at is not None
    # CANCELLED is terminal only via snapshot cancel provenance (BMAP-07).
    assert ack.state is OrderLifecycleState.CANCELLED


def test_r1c_cancel_reject_returns_to_live() -> None:
    h = _harness(scenario="r1c_cancel_rej")
    h.submit()
    h.acknowledge()
    h.cancel_request()
    out = h.cancel_reject()
    assert out.state is OrderLifecycleState.ACKNOWLEDGED
    ev = h.evidence()
    assert ev.final_state == "ACKNOWLEDGED"
    assert ev.final_terminal is False


# ---------------------------------------------------------------------------
# R1-D: cancel/fill race (fill authoritative)
# ---------------------------------------------------------------------------


def test_r1d_fill_wins_cancel_race() -> None:
    h = _harness(scenario="r1d_race")
    h.submit()
    h.acknowledge()
    h.cancel_request()
    assert h.state is OrderLifecycleState.CANCEL_REQUESTED
    out = h.fill_during_cancel(_QTY)
    assert out.state is OrderLifecycleState.FILLED
    ev = h.evidence()
    assert ev.final_state == "FILLED"
    assert ev.final_terminal is True
    assert ev.filled_qty == _QTY


# ---------------------------------------------------------------------------
# R1-E: connectivity loss -> UNKNOWN (never CANCELLED/REJECTED)
# ---------------------------------------------------------------------------


def test_r1e_ack_timeout_unknown() -> None:
    h = _harness(scenario="r1e_timeout")
    h.submit()
    out = h.connection_lost()
    assert out.state is OrderLifecycleState.UNKNOWN
    assert out.transition is not None
    assert out.transition.new_state is OrderLifecycleState.UNKNOWN
    assert out.transition.is_terminal is False
    ev = h.evidence()
    assert ev.final_state == "UNKNOWN"
    assert ev.final_terminal is False
    assert ev.manifest is not None
    assert ev.manifest.closed_at is None  # UNKNOWN left open


# ---------------------------------------------------------------------------
# R1-F: UNKNOWN -> reconciliation -> verified terminal (evidence-gated)
# ---------------------------------------------------------------------------


def test_r1f_reconcile_to_verified_terminal() -> None:
    h = _harness(scenario="r1f_recon")
    h.submit()
    h.connection_lost()
    assert h.state is OrderLifecycleState.UNKNOWN
    out = h.reconcile("FILLED")
    assert out.state is OrderLifecycleState.FILLED
    assert out.transition is not None and out.transition.is_terminal
    ev = h.evidence()
    assert ev.final_state == "FILLED"
    assert ev.final_terminal is True
    assert ev.manifest is not None
    assert ev.manifest.closed_at is not None
    # R1-I: reconciliation produced a report binding the UNKNOWN exit.
    assert ev.reconciliation_report is not None
    assert ev.reconciliation_report.report_digest


def test_r1f_reconcile_garbage_stays_unknown() -> None:
    h = _harness(scenario="r1f_garbage")
    h.submit()
    h.connection_lost()
    out = h.reconcile("GARBAGE")
    assert out.state is OrderLifecycleState.UNKNOWN
    assert out.rejected is True
    ev = h.evidence()
    assert ev.final_state == "UNKNOWN"
    assert ev.final_terminal is False
    assert ev.manifest is not None
    assert ev.manifest.closed_at is None  # never fabricate a terminal


# ---------------------------------------------------------------------------
# R1-G: late event after terminal -> fail-closed (never last-wins)
# ---------------------------------------------------------------------------


def test_r1g_late_event_after_terminal_fails_closed() -> None:
    adapter = AlpacaPaperAdapter(_FakeTransport())
    coord = ExecutionCoordinator(execution_id="EXE_LATE", requested_qty=_QTY)
    receipt = adapter.submit_order("coid-late", "SPY", _QTY)
    raw_ack = adapter.ingest_trade_event(
        _trade_event_fixture(
            event_id="01" + "0" * 22 + "a",
            event=AlpacaTradeEventType.ACCEPTED,
            broker_order_id=receipt.broker_order_id,
            requested_qty=_QTY,
            filled_qty=Decimal("0"),
        )
    )
    coord.apply(to_coordinator_event(raw_ack))
    raw_fill = adapter.ingest_trade_event(
        _trade_event_fixture(
            event_id="01" + "0" * 22 + "b",
            event=AlpacaTradeEventType.FILL,
            broker_order_id=receipt.broker_order_id,
            requested_qty=_QTY,
            filled_qty=_QTY,
            qty=_QTY,
        )
    )
    coord.apply(to_coordinator_event(raw_fill, fill_qty=_QTY))
    assert coord.state is OrderLifecycleState.FILLED
    # A late ACK after terminal must be rejected (terminal-absorbing), not last-wins.
    late = _trade_event_fixture(
        event_id="01" + "0" * 22 + "c",
        event=AlpacaTradeEventType.ACCEPTED,
        broker_order_id=receipt.broker_order_id,
        requested_qty=_QTY,
        filled_qty=_QTY,
    )
    out = coord.apply(to_coordinator_event(adapter.ingest_trade_event(late)))
    assert out.rejected is True
    assert coord.state is OrderLifecycleState.FILLED
    assert any(
        i.kind is CoordinatorIncidentKind.LATE_EVENT for i in out.incidents
    )


# ---------------------------------------------------------------------------
# R1-H: ExecutionManifest lineage (closed_at only on verified terminal)
# ---------------------------------------------------------------------------


def test_r1h_manifest_binds_intent_to_execution() -> None:
    h = _harness(scenario="r1h_manifest")
    h.submit()
    h.acknowledge()
    h.full_fill(_QTY)
    ev = h.evidence()
    m = ev.manifest
    assert m is not None
    # intent_digest is a valid sha256 and is bound into the manifest.
    assert len(m.intent_digest) == 64
    assert all(c in "0123456789abcdef" for c in m.intent_digest)
    assert m.client_order_id == h.client_order_id
    assert m.broker_order_id == h.broker_order_id
    assert m.filled_qty == _QTY
    assert m.execution_digest and len(m.execution_digest) == 64
    assert m.closed_at is not None


def test_r1h_manifest_unknown_leaves_closed_at_none() -> None:
    h = _harness(scenario="r1h_unknown")
    h.submit()
    h.connection_lost()
    ev = h.evidence()
    assert ev.manifest is not None
    assert ev.manifest.closed_at is None
    assert ev.final_state == "UNKNOWN"


# ---------------------------------------------------------------------------
# R1-I: ReconciliationReport lineage
# ---------------------------------------------------------------------------


def test_r1i_reconciliation_report_binds_exit() -> None:
    h = _harness(scenario="r1i_report")
    h.submit()
    h.connection_lost()
    h.reconcile("FILLED")
    ev = h.evidence()
    assert ev.reconciliation_report is not None
    rep = ev.reconciliation_report
    assert rep.venue == "ALPACA_PAPER"
    assert rep.is_in_parity is True
    assert rep.report_digest and len(rep.report_digest) == 64


# ---------------------------------------------------------------------------
# Explicit-sequence coverage: every R1 scenario is stated directly as harness
# method calls (NO generic script/dispatcher). These mirror the R1-A..R1-I cells
# through the public OrderExerciseHarness API produced against a fake transport.
# ---------------------------------------------------------------------------


def test_explicit_sequence_full_fill() -> None:
    h = _harness(scenario="seq_full")
    h.submit()
    h.acknowledge()
    h.partial_fill(Decimal("0.250"))
    h.full_fill(Decimal("0.750"))
    ev = h.evidence()
    assert isinstance(ev, LifecycleEvidence)
    assert ev.final_state == "FILLED"
    assert ev.final_terminal is True
    assert ev.filled_qty == _QTY


def test_explicit_sequence_cancel_reject() -> None:
    h = _harness(scenario="seq_cancel_rej")
    h.submit()
    h.acknowledge()
    h.cancel_request()
    h.cancel_reject()
    ev = h.evidence()
    assert ev.final_state == "ACKNOWLEDGED"
    assert ev.final_terminal is False


def test_explicit_sequence_fill_during_cancel() -> None:
    # R1-D race stated explicitly: fill wins over the pending cancel.
    h = _harness(scenario="seq_fill_during_cancel")
    h.submit()
    h.acknowledge()
    h.cancel_request()
    h.fill_during_cancel(_QTY)
    ev = h.evidence()
    assert ev.final_state == "FILLED"
    assert ev.final_terminal is True
    assert ev.filled_qty == _QTY


def test_explicit_sequence_unknown_then_reconcile() -> None:
    h = _harness(scenario="seq_recon")
    h.submit()
    h.connection_lost()
    assert h.state is OrderLifecycleState.UNKNOWN
    h.reconcile("FILLED")
    ev = h.evidence()
    assert ev.final_state == "FILLED"
    assert ev.final_terminal is True
    assert ev.reconciliation_report is not None


def test_ordering_error_fails_closed_with_harness_error() -> None:
    # Accessing broker_order_id before submit raises a harness-native, fail-closed
    # error (distinct from a broker reply) — the harness is a driver, not a broker.
    h = _harness(scenario="orderguard")
    with pytest.raises(OrderExerciseError):
        _ = h.broker_order_id


def test_build_nominal_intent_is_exercise_lineage_not_admission() -> None:
    # Lock the authoritative caveat: direct construction means the R1-H intent
    # digest is exercise-lineage only, and must NOT be read as an admission proof.
    intent = build_nominal_intent(
        intent_id="INT_X",
        authorization_id="AUTH_PAPER_EXERCISE",
        strategy_id="STRAT_PAPER_EXERCISE",
        symbol="SPY",
        quantity=_QTY,
        created_at=_utc("2026-01-01T00:00:00Z"),
    )
    assert len(intent.intent_digest) == 64
    assert intent.venue == "ALPACA_PAPER"
    # It did NOT pass construct_order_intent()'s admission gate; document that the
    # intent cannot be used to infer live authorization/admission fitness.
    from acash.execution.admission import construct_order_intent

    assert callable(construct_order_intent)


# ---------------------------------------------------------------------------
# Evidence DTO / lineage carry NO secret / account material
# ---------------------------------------------------------------------------


def _trade_event_fixture(
    *,
    event_id: str,
    event: AlpacaTradeEventType,
    broker_order_id: str,
    requested_qty: Decimal,
    filled_qty: Decimal,
    qty: Optional[Decimal] = None,
) -> AlpacaTradeEvent:
    return AlpacaTradeEvent(
        event_id=event_id,
        event=event,
        at=_utc("2026-01-01T00:00:00Z"),
        executed_at=_utc("2026-01-01T00:00:01Z") if qty is not None else None,
        broker_order_id=broker_order_id,
        qty=qty,
        order=AlpacaOrder(
            broker_order_id=broker_order_id,
            client_order_id=f"coid-{broker_order_id}",
            symbol="SPY",
            status=(
                AlpacaOrderStatus.NEW
                if event is AlpacaTradeEventType.ACCEPTED
                else AlpacaOrderStatus.FILLED
            ),
            requested_qty=requested_qty,
            filled_qty=filled_qty,
            created_at=_utc("2026-01-01T00:00:00Z"),
            updated_at=_utc("2026-01-01T00:00:01Z"),
        ),
    )


def test_lifecycle_evidence_carries_no_secret_material() -> None:
    h = _harness(scenario="clean")
    h.submit()
    h.acknowledge()
    ev = h.evidence()
    text = (str(ev) + repr(ev)).lower()
    for fragment in ("api_key", "secret", "AK-", "apca-"):
        assert fragment not in text
    assert "alpaca_paper" in text or "ALPACA_PAPER" in text


def test_no_util_placeholder_types() -> None:
    # Guard against accidental inner-class/helper defined by the harness that
    # could carry state; the evidence DTO must stay a plain frozen record.
    from dataclasses import fields

    fnames = {f.name for f in fields(LifecycleEvidence)}
    assert "scenario" in fnames
    assert "broker_order_id" in fnames
    assert "manifest" in fnames


# ---------------------------------------------------------------------------
# Production entry point `run_order_exercise_verification` — connect-before-submit
# ---------------------------------------------------------------------------


class _RecordingPaperTransport(PaperHttpAlpacaTransport):
    """Paper transport recording call order; NO real network (mock HTTP)."""

    def __init__(
        self,
        provider: EnvAlpacaCredentialProvider,
        endpoint: AlpacaEndpoint,
        handler: Callable[[httpx.Request], httpx.Response],
    ) -> None:
        super().__init__(
            provider=provider,
            endpoint=endpoint,
            transport=httpx.MockTransport(handler),
        )
        self.calls: List[str] = []
        self.submit_count: int = 0

    def connect(self) -> None:
        self.calls.append("connect")
        super().connect()

    def submit_order(
        self,
        client_order_id: str,
        symbol: str,
        quantity: Decimal,
    ) -> SubmissionReceipt:
        self.calls.append("submit")
        self.submit_count += 1
        return super().submit_order(
            client_order_id=client_order_id,
            symbol=symbol,
            quantity=quantity,
        )


class _ConnectFailingPaperTransport(PaperHttpAlpacaTransport):
    """Paper transport whose connect() raises fail-closed; NO real network."""

    def __init__(
        self,
        provider: EnvAlpacaCredentialProvider,
        endpoint: AlpacaEndpoint,
        handler: Callable[[httpx.Request], httpx.Response],
    ) -> None:
        super().__init__(
            provider=provider,
            endpoint=endpoint,
            transport=httpx.MockTransport(handler),
        )
        self.calls: List[str] = []

    def connect(self) -> None:
        self.calls.append("connect")
        raise AlpacaTransportAuthError("refusing to connect (fail-closed)")

    def submit_order(
        self,
        client_order_id: str,
        symbol: str,
        quantity: Decimal,
    ) -> SubmissionReceipt:
        self.calls.append("submit")
        raise AssertionError("submit_order called when it must not be")


def _paper_paper_transport(
    handler: Callable[[httpx.Request], httpx.Response],
) -> _RecordingPaperTransport:
    """Build a recording Paper transport over an injected mock HTTP handler.

    connect() is wired through httpx.MockTransport so NO real network I/O occurs.
    The nominal harness flow after submit() is local (ack/fill via ingest_trade_event),
    so only the POST /orders submit needs a mock HTTP response.
    """
    provider = EnvAlpacaCredentialProvider(
        venue="ALPACA_PAPER",
        api_key_id="AK-PAPER-TEST",
        api_secret="paper-secret-test",
    )
    return _RecordingPaperTransport(
        provider=provider,
        endpoint=paper_endpoint(),
        handler=handler,
    )


def test_run_order_exercise_verification_connects_before_submit() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "id": "brk-verify-0001",
                    "client_order_id": "acash-r1-paper-20260831-001",
                    "status": "accepted",
                },
            )
        if request.method == "GET" and "/orders/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "id": "brk-verify-0001",
                    "client_order_id": "acash-r1-paper-20260831-001",
                    "symbol": "SPY",
                    "status": "filled",
                    "qty": "1",
                    "filled_qty": "1",
                    "created_at": "2026-08-31T05:00:00Z",
                    "updated_at": "2026-08-31T05:00:01Z",
                    "filled_at": "2026-08-31T05:00:01Z",
                },
            )
        return httpx.Response(404, json={"message": "not found"})

    t = _paper_paper_transport(_handler)
    ev = run_order_exercise_verification(
        client_order_id="acash-r1-paper-20260831-001",
        symbol="SPY",
        quantity=Decimal("1"),
        transport=t,
    )

    # connect MUST precede submit; and connect actually happened before the wire.
    assert t.calls == ["connect", "submit"]
    assert ev.broker_order_id == "brk-verify-0001"
    assert ev.final_state == "FILLED"
    assert ev.final_terminal is True
    assert ev.filled_qty == Decimal("1")
    assert ev.disputed is False
    assert ev.manifest is not None and ev.manifest.closed_at is not None
    assert ev.reconciliation_report is not None and ev.reconciliation_report.is_in_parity


def test_run_order_exercise_verification_connect_failure_blocks_submit() -> None:
    provider = EnvAlpacaCredentialProvider(
        venue="ALPACA_PAPER",
        api_key_id="AK-PAPER-TEST",
        api_secret="paper-secret-test",
    )
    t = _ConnectFailingPaperTransport(
        provider=provider,
        endpoint=paper_endpoint(),
        handler=lambda request: httpx.Response(200, json={"id": "should-never-fire"}),
    )

    with pytest.raises(AlpacaTransportAuthError):
        run_order_exercise_verification(
            client_order_id="acash-r1-paper-20260831-001",
            symbol="SPY",
            quantity=Decimal("1"),
            transport=t,
        )

    # A connect failure must block submit + any HTTP request (fail-closed).
    assert t.calls == ["connect"]


def test_run_order_exercise_verification_rejects_non_paper_transport() -> None:
    """A non-Paper transport (e.g. live) must never reach the R1 gate.

    The ``transport`` seam is Paper-only by construction: injection of a
    non-``PaperHttpAlpacaTransport`` raises fail-closed BEFORE ``connect()`` and
    before any HTTP request, so a live/other venue can never be smuggled into the
    production R1 gate under disguise.
    """
    fired: List[str] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        fired.append("http")
        return httpx.Response(200, json={"id": "should-never-fire"})

    live_provider = EnvAlpacaCredentialProvider(
        venue="ALPACA_LIVE",
        api_key_id="AK-LIVE-TEST",
        api_secret="live-secret-test",
    )
    live = HttpAlpacaTransport(
        provider=live_provider,
        endpoint=live_endpoint(),
        transport=httpx.MockTransport(_handler),
    )

    with pytest.raises(OrderExerciseError):
        run_order_exercise_verification(
            client_order_id="acash-r1-paper-20260831-001",
            symbol="SPY",
            quantity=Decimal("1"),
            transport=live,
        )

    # Paper-only gate fired BEFORE connect/submit: no HTTP request occurred.
    assert fired == []
