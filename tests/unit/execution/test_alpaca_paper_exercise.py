"""Phase 7 Paper Exercise — R0 read-only / non-destructive verification harness.

Conformance suite for ``acash.execution.alpaca.paper_exercise``:

- R0 is read-only BY CONSTRUCTION: the harness source references NO write method
  (``submit_order`` / ``cancel_order``), asserted structurally (AST) and by a
  counting fake transport.
- Fail-closed everywhere: absent credentials, network/auth failure at connect,
  unknown-order lookup that fabricates a state, or a cross-venue position all
  raise ``PaperExerciseError`` — evidence is never fabricated.
- ``EnvAlpacaCredentialProvider`` with no injected mapping reads the REAL
  process environment (operator-exported paper credentials are honored).
- The evidence DTO carries NO secret / account material.

This suite never touches the network: it runs against fake transports and an
empty/injected environment. A REAL P-run requires the operator to export
``ACASH_ALPACA_API_KEY_ID`` / ``ACASH_ALPACA_API_SECRET`` in the running
session; that run is NOT part of this unit suite.
"""

import ast
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterator, Optional

import pytest

from acash.execution.alpaca import (
    AlpacaEventStream,
    AlpacaOrder,
    AlpacaOrderStatus,
    AlpacaTradeEvent,
    AlpacaTradeEventType,
    AlpacaTransport,
    AlpacaTransportError,
    EnvAlpacaCredentialProvider,
    PaperExerciseError,
    PaperReadOnlyEvidence,
    build_read_only_transport,
    paper_endpoint,
    run_read_only_probes,
)
from acash.execution.broker_adapter import BrokerPosition, SubmissionReceipt

_UNKNOWN_ID = "00000000-0000-0000-0000-0000000000f0"


def _utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# Fake transports (read-only capable, write-method counters, fail-closed)
# ---------------------------------------------------------------------------


class _ReadOnlyFakeTransport(AlpacaTransport):
    """Read-only fake that counts ANY write attempt.

    ``submit_calls``/``cancel_calls`` stay 0 iff the harness is read-only. It
    raises on unknown-order lookups (transport-layer fail-closed) and returns a
    paper-venue position for the known symbols.
    """

    def __init__(self) -> None:
        self._connected = True
        self.submit_calls = 0
        self.cancel_calls = 0

    def connect(self) -> None:
        self._connected = True

    def connected(self) -> bool:
        return self._connected

    def submit_order(
        self, client_order_id: str, symbol: str, quantity: Decimal
    ) -> SubmissionReceipt:
        self.submit_calls += 1
        raise AssertionError("R0 harness must not call submit_order")

    def cancel_order(self, broker_order_id: str) -> None:
        self.cancel_calls += 1
        raise AssertionError("R0 harness must not call cancel_order")

    def query_order(self, broker_order_id: str) -> AlpacaOrder:
        raise AlpacaTransportError(
            f"order not found (HTTP 404): {broker_order_id} (fail-closed)."
        )

    def query_position(self, symbol: str) -> Optional[BrokerPosition]:
        if symbol in ("SPY", "AAPL"):
            return BrokerPosition(
                symbol=symbol, quantity=Decimal("10"), venue="ALPACA_PAPER"
            )
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


class _FabricatingOrderTransport(_ReadOnlyFakeTransport):
    """Pathological transport that ILLEGALLY fabricates a filled order for the
    random unknown id — the harness must fail closed, never accept it."""

    def query_order(self, broker_order_id: str) -> AlpacaOrder:
        return AlpacaOrder(
            broker_order_id=broker_order_id,
            client_order_id="made-up",
            symbol="SPY",
            status=AlpacaOrderStatus.FILLED,
            requested_qty=Decimal("1"),
            filled_qty=Decimal("1"),
            created_at=_utc("2026-01-01T00:00:00Z"),
            updated_at=_utc("2026-01-01T00:00:00Z"),
            filled_at=_utc("2026-01-01T00:00:01Z"),
        )


class _CrossVenueTransport(_ReadOnlyFakeTransport):
    """Transport whose broker position reports a NON-paper venue."""

    def query_position(self, symbol: str) -> Optional[BrokerPosition]:
        if symbol in ("SPY", "AAPL"):
            return BrokerPosition(
                symbol=symbol, quantity=Decimal("1"), venue="ALPACA_LIVE"
            )
        return None


# ---------------------------------------------------------------------------
# R0 harness: read-only BY CONSTRUCTION (structural AST guard)
# ---------------------------------------------------------------------------

_PAPER_EXERCISE_SRC = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "src", "acash",
    "execution", "alpaca", "paper_exercise.py",
)

# Write-side transport methods that MUST NEVER appear in the R0 harness.
_FORBIDDEN_METHODS = {"submit_order", "cancel_order"}


def _ast_method_names(path: str) -> set[str]:
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


def test_r0_harness_source_never_defines_write_methods() -> None:
    methods = _ast_method_names(_PAPER_EXERCISE_SRC)
    assert _FORBIDDEN_METHODS.isdisjoint(methods), (
        f"R0 harness must not define write methods, found: "
        f"{sorted(_FORBIDDEN_METHODS & methods)}"
    )


def test_r0_harness_source_never_references_write_methods() -> None:
    # Real imports into the module are the write surface: if a write method was
    # imported AND called, the conformance fake would catch execution; the AST
    # import scan is a second, structural net (no hidden reference).
    with open(_PAPER_EXERCISE_SRC, encoding="utf-8") as fh:
        src = fh.read()
    for name in _FORBIDDEN_METHODS:
        # Only flag a REAL attribute access like "transport.submit_order".
        assert f".{name}" not in src, (
            f"R0 harness references write method {name!r}; read-only violated."
        )


# ---------------------------------------------------------------------------
# R0 harness: read-only execution (fake transport counts writes)
# ---------------------------------------------------------------------------


def test_r0_happy_path_is_read_only_and_points_to_paper() -> None:
    fake = _ReadOnlyFakeTransport()
    ev = run_read_only_probes(fake)
    assert isinstance(ev, PaperReadOnlyEvidence)
    assert ev.venue == "ALPACA_PAPER"
    assert ev.credentials_resolved is True
    assert ev.connected is True
    assert ev.unknown_order_lookup_fail_closed is True
    assert fake.submit_calls == 0
    assert fake.cancel_calls == 0


def test_r0_position_probes_reflect_discovery_not_fabrication() -> None:
    fake = _ReadOnlyFakeTransport()
    ev = run_read_only_probes(fake)
    by_symbol = {p.symbol: p for p in ev.position_probes}
    # SPY/AAPL exist on the fake -> present with quantity under paper venue.
    assert by_symbol["SPY"].present is True
    assert by_symbol["SPY"].quantity == Decimal("10")
    assert by_symbol["SPY"].venue == "ALPACA_PAPER"
    assert by_symbol["AAPL"].present is True
    # Unknown-to-broker symbol -> absent, NOT fabricated zero.
    assert by_symbol["MSFT"].present is False
    assert by_symbol["MSFT"].quantity is None
    assert by_symbol["MSFT"].venue is None


def test_r0_never_fabricates_for_unknown_order() -> None:
    with pytest.raises(PaperExerciseError):
        run_read_only_probes(_FabricatingOrderTransport())


def test_r0_cross_venue_position_fails_closed() -> None:
    with pytest.raises(PaperExerciseError):
        run_read_only_probes(_CrossVenueTransport())


# ---------------------------------------------------------------------------
# R0 harness: fail-closed on connect / credential boundary
# ---------------------------------------------------------------------------


class _ConnectFailureTransport(_ReadOnlyFakeTransport):
    def connect(self) -> None:
        raise AlpacaTransportError("transport auth/network failed")


def test_r0_fails_closed_when_connect_transport_error() -> None:
    with pytest.raises(PaperExerciseError):
        run_read_only_probes(_ConnectFailureTransport())


def test_r0_builder_is_paper_only_transport() -> None:
    t = build_read_only_transport()
    assert t.endpoint.is_paper
    assert t.endpoint.base_url == "https://paper-api.alpaca.markets/v2"


# ---------------------------------------------------------------------------
# EnvAlpacaCredentialProvider reads the REAL process environment by default
# ---------------------------------------------------------------------------


def test_env_provider_default_reads_real_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Operator exports paper credentials into the running session (the selected
    # injection method). The default provider (no injected mapping) MUST honor
    # them — this is the prerequisite for the real P-run.
    monkeypatch.setenv("ACASH_ALPACA_API_KEY_ID", "AK-PAPER-OPERATOR")
    monkeypatch.setenv("ACASH_ALPACA_API_SECRET", "paper-operator-secret")
    provider = EnvAlpacaCredentialProvider()  # no environ, no explicit args
    creds = provider.load()
    assert creds.resolved
    assert creds.api_key_id == "AK-PAPER-OPERATOR"
    assert "AK-PAPER-OPERATOR" not in str(creds)
    assert "paper-operator-secret" not in repr(creds)


def test_env_provider_default_fails_closed_when_env_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ACASH_ALPACA_API_KEY_ID", raising=False)
    monkeypatch.delenv("ACASH_ALPACA_API_SECRET", raising=False)
    provider = EnvAlpacaCredentialProvider()
    with pytest.raises(Exception, match="API key id is absent"):
        provider.load()


# ---------------------------------------------------------------------------
# Evidence DTO carries NO secret material
# ---------------------------------------------------------------------------


def test_r0_evidence_dto_carries_no_secret_material() -> None:
    ev = PaperReadOnlyEvidence(
        venue="ALPACA_PAPER",
        credentials_resolved=True,
        connected=True,
        position_probes=(),
        unknown_order_lookup_fail_closed=True,
        recorded_at_utc=datetime.now(timezone.utc),
    )
    text = (str(ev) + repr(ev)).lower()
    for fragment in ("api_key", "secret", "AK-", "apca-"):
        assert fragment not in text
    # The venue string is the only identifier the evidence exposes.
    assert "alpaca_paper" in text or "ALPACA_PAPER" in text


def test_r0_evidence_recorded_at_is_utc() -> None:
    ev = PaperReadOnlyEvidence(
        venue="ALPACA_PAPER",
        credentials_resolved=True,
        connected=True,
        position_probes=(),
        unknown_order_lookup_fail_closed=True,
        recorded_at_utc=datetime.now(timezone.utc),
    )
    assert ev.recorded_at_utc.tzinfo is not None
    assert ev.recorded_at_utc.utcoffset() is not None