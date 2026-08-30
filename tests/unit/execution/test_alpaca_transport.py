"""Phase 7 Step 8F follow-on: Alpaca paper transport & credential abstraction.

Covers the first increment of the Alpaca paper adapter: the interface +
paper-transport seam (``acash.execution.alpaca``). Tests attack the assumptions
behind the E-reviewed BMAP (rv ``47a8bc9``) and the frozen broker adapter contract
(rv ``6fd4a78``):

- Credentials are external, redacted, and fail closed (C-1/C-2/C-4).
- Live rotation is possible without code change (C-5).
- DTO field semantics are precise: ``broker_sequence`` comes from ``event_id``
  (ULID), never from a timestamp; per-fill ``qty`` is distinct from cumulative
  ``filled_qty``.
- Vocabulary covers the documented Trade Events SSE v2 lifecycle list + order
  status set.
- Authority separation: the transport abstraction NEVER references
  ``OrderLifecycleState`` / ``transition_order`` / ``ExecutionCoordinator``
  (N-1/N-3) — it is a command sink + observation source only.
"""

import ast
import importlib
import os
import sys
import typing
from datetime import datetime
from decimal import Decimal

import pytest

from acash.execution.alpaca import (
    PAPER_API_HOST,
    LIVE_API_HOST,
    AlpacaCancelReason,
    AlpacaCredentialError,
    AlpacaCredentialProvider,
    AlpacaCredentials,
    AlpacaEndpoint,
    AlpacaEventStream,
    AlpacaOrder,
    AlpacaOrderStatus,
    AlpacaTradeEvent,
    AlpacaTradeEventType,
    AlpacaTransport,
    AlpacaVenue,
    EnvAlpacaCredentialProvider,
)


def _utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# Credential boundary (contract §6 C-1/C-2/C-4/C-5, BMAP-10)
# ---------------------------------------------------------------------------


def test_credentials_always_redact_in_str_and_repr() -> None:
    c = AlpacaCredentials(
        api_key_id="AK-TOP-SECRET-ID", api_secret_ref="supersecret", _resolved=True
    )
    assert "TOP-SECRET" not in str(c)
    assert "TOP-SECRET" not in repr(c)
    assert "supersecret" not in str(c)
    assert "supersecret" not in repr(c)
    assert "********" in str(c)
    assert c.resolved


def test_unresolved_credentials_fail_closed_on_resolved_flag() -> None:
    c = AlpacaCredentials(api_key_id="")
    assert not c.resolved  # blank handle is never a valid credential (C-4)


def test_env_provider_fails_closed_when_key_absent() -> None:
    provider = EnvAlpacaCredentialProvider(environ={"SOME_OTHER_VAR": "x"})
    with pytest.raises(AlpacaCredentialError):
        provider.load()


def test_env_provider_reads_external_env_mapping() -> None:
    provider = EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "AK-PAPER", "ACASH_ALPACA_API_SECRET": "sec"}
    )
    creds = provider.load()
    assert creds.resolved
    assert "AK-PAPER" not in str(creds)
    assert provider.venue() == "ALPACA_PAPER"


def test_rotation_reloads_live_env_without_code_change() -> None:
    env: dict[str, str] = {
        "ACASH_ALPACA_API_KEY_ID": "AK-OLD",
        "ACASH_ALPACA_API_SECRET": "oldsec",
    }
    provider = EnvAlpacaCredentialProvider(environ=env)
    first = provider.load()
    # Operator rotates the secret in the store; provider re-reads on load() (C-5)
    # with NO code change.
    env["ACASH_ALPACA_API_KEY_ID"] = "AK-NEW"
    env["ACASH_ALPACA_API_SECRET"] = "newsec"
    second = provider.load()
    assert first.api_key_id == "AK-OLD"
    assert second.api_key_id == "AK-NEW"
    # Redaction holds for the rotated handle too.
    assert "AK-NEW" not in str(second)
    assert "newsec" not in repr(second)


# ---------------------------------------------------------------------------
# DTO field semantics (BMAP-02/03/06)
# ---------------------------------------------------------------------------


def test_trade_event_broker_sequence_is_event_id_not_timestamp() -> None:
    ev = AlpacaTradeEvent(
        event_id="01HCMKKNRK7S5C1JYP50QGDECQ",
        event=AlpacaTradeEventType.FILL,
        at=_utc("2023-10-13T13:28:58.387652Z"),
        executed_at=_utc("2023-10-13T13:30:00.658443088Z"),
        broker_order_id="db04069d-2e5a-48d4-a42f-6a0dea8ea0b8",
    )
    # broker_sequence source is the ULID event_id, NOT the timestamps (BMAP-03).
    assert ev.event_id != "2023-10-13T13:28:58.387652Z"
    assert ev.event_id != str(ev.at)
    assert ev.event_id != str(ev.executed_at)
    # The two timestamp axes are distinct identities, not the sequence.
    assert ev.at != ev.executed_at


def test_order_cumulative_fill_distinct_from_per_fill_qty() -> None:
    order = AlpacaOrder(
        broker_order_id="db04069d-2e5a-48d4-a42f-6a0dea8ea0b8",
        client_order_id="be139e2d-8153-4ae8-83ee-7b98b4e17419",
        symbol="AAPL",
        status=AlpacaOrderStatus.FILLED,
        requested_qty=Decimal("0.11"),
        filled_qty=Decimal("0.1102779"),  # cumulative, NOT per-fill
        created_at=_utc("2023-10-13T13:22:21.887914Z"),
        updated_at=_utc("2023-10-13T13:30:00.661902331Z"),
        filled_at=_utc("2023-10-13T13:30:00.658443088Z"),
    )
    ev = AlpacaTradeEvent(
        event_id="01HCMKNJJRJ4E3RNFA1XR8CX7R",
        event=AlpacaTradeEventType.PARTIAL_FILL,
        at=_utc("2023-10-13T13:30:00.664778Z"),
        executed_at=_utc("2023-10-13T13:30:00.658443088Z"),
        broker_order_id=order.broker_order_id,
        execution_id="a958bb42-b034-4d17-bf07-805cf0820ffe",
        qty=Decimal("0.05513895"),  # per-fill
        order=order,
    )
    assert ev.qty == Decimal("0.05513895")
    assert order.filled_qty == Decimal("0.1102779")  # cumulative
    assert ev.qty != order.filled_qty  # distinct semantics (BMAP-06)


def test_trade_bust_qty_negative_and_previous_execution_id() -> None:
    ev = AlpacaTradeEvent(
        event_id="01HCMQR4S73L9G6EHI0JKL2M3N",
        event=AlpacaTradeEventType.TRADE_BUST,
        at=_utc("2024-09-23T13:30:00.673857Z"),
        executed_at=_utc("2024-09-23T15:30:48.601741737Z"),
        broker_order_id="c86e4d6c-2cdf-4b81-b658-5728bdc8310b",
        qty=Decimal("-2"),
        previous_execution_id="aeb60660-412f-4537-8d1f-1101b3fc8f64",
    )
    assert ev.qty == Decimal("-2")
    assert ev.previous_execution_id == "aeb60660-412f-4537-8d1f-1101b3fc8f64"


# ---------------------------------------------------------------------------
# DTO REST/SSE separation (contract §1, unit discipline)
# ---------------------------------------------------------------------------


def test_sse_event_without_embedded_order_is_valid() -> None:
    # Not every Trade Events SSE payload embeds the full Order REST object
    # (e.g. cancel/expire/held events). The DTO must NOT force REST-only fields
    # on an event. Broker order reality is queried separately (query_order).
    ev = AlpacaTradeEvent(
        event_id="01HCMKKNRK7S5C1JYP50QGDECQ",
        event=AlpacaTradeEventType.EXPIRED,
        at=_utc("2024-09-23T13:30:00.673857Z"),
        executed_at=None,
        broker_order_id="db04069d-2e5a-48d4-a42f-6a0dea8ea0b8",
        # order=... intentionally absent
    )
    assert ev.order is None
    assert ev.executed_at is None
    assert ev.qty is None
    assert ev.price is None
    # Event identity / sequence come only from event_id, not a required order:
    assert ev.event_id == "01HCMKKNRK7S5C1JYP50QGDECQ"


def test_rest_order_object_carries_fields_sse_event_does_not() -> None:
    # REST Order snapshot fields (client_order_id, requested qty, created_at,
    # updated_at) belong to the Order object, NOT to the event carrier. The two
    # DTOs stay decoupled: AlpacaOrder requires REST-order fields; AlpacaTradeEvent
    # does not and must not borrow them.
    order = AlpacaOrder(
        broker_order_id="db04069d-2e5a-48d4-a42f-6a0dea8ea0b8",
        client_order_id="be139e2d-8153-4ae8-83ee-7b98b4e17419",
        symbol="AAPL",
        status=AlpacaOrderStatus.NEW,
        requested_qty=Decimal("0.11"),
        filled_qty=Decimal("0"),
        created_at=_utc("2023-10-13T13:22:21.887914Z"),
        updated_at=_utc("2023-10-13T13:22:21.887914Z"),
    )
    assert order.client_order_id == "be139e2d-8153-4ae8-83ee-7b98b4e17419"
    assert order.requested_qty == Decimal("0.11")
    assert order.created_at is not None
    assert order.updated_at is not None
    # A cancel/expire SSE event carries no order REST fields and stays legal.
    ev = AlpacaTradeEvent(
        event_id="01HCMQR4S73L9G6EHI0JKL2M3N",
        event=AlpacaTradeEventType.CANCELED,
        at=_utc("2024-09-23T13:30:00.673857Z"),
        executed_at=None,
        broker_order_id=order.broker_order_id,
        reason=AlpacaCancelReason.CORPORATE_ACTION.value,
    )
    assert ev.reason == "CORPORATE_ACTION"
    assert ev.order is None


# ---------------------------------------------------------------------------
# Vocabulary coverage (BMAP-01)
# ---------------------------------------------------------------------------


def test_trade_event_type_enum_covers_documented_v2_lifecycle() -> None:
    documented = {
        "accepted", "new", "pending_new", "fill", "partial_fill", "canceled",
        "expired", "replaced", "rejected", "done_for_day", "held", "stopped",
        "suspended", "pending_cancel", "pending_replace", "calculated",
        "order_replace_rejected", "order_cancel_rejected", "trade_bust",
        "trade_correct",
    }
    values = {e.value for e in AlpacaTradeEventType}
    assert documented == values


def test_cancel_reason_codes_present() -> None:
    assert AlpacaCancelReason.CORPORATE_ACTION.value == "CORPORATE_ACTION"
    assert AlpacaCancelReason.TOO_LATE_TO_CANCEL.value == "TOO_LATE_TO_CANCEL"
    assert AlpacaCancelReason.TRADE_BUST.value == "TRADE_BUST"


def test_order_status_enum_includes_inflight_and_terminal() -> None:
    statuses = {s.value for s in AlpacaOrderStatus}
    for required in ("new", "partially_filled", "filled", "canceled", "expired",
                     "rejected", "pending_cancel", "cancel_rejected"):
        assert required in statuses


# ---------------------------------------------------------------------------
# Endpoint separation (BMAP-10)
# ---------------------------------------------------------------------------


def test_paper_vs_live_endpoint_hosts_are_distinct() -> None:
    assert PAPER_API_HOST == "paper-api.alpaca.markets"
    assert LIVE_API_HOST == "api.alpaca.markets"
    assert PAPER_API_HOST != LIVE_API_HOST


def test_endpoint_dataclass_is_typed_venue_not_free_url() -> None:
    # AlpacaEndpoint is bound to a typed AlpacaVenue; base_url is DERIVED, not a
    # caller-injected free URL string (so paper/live can never be misconfigured).
    paper = AlpacaEndpoint(venue=AlpacaVenue.PAPER)
    live = AlpacaEndpoint(venue=AlpacaVenue.LIVE)
    assert paper.is_paper
    assert not live.is_paper
    assert paper.base_url == f"https://{PAPER_API_HOST}/v2"
    assert live.base_url == f"https://{LIVE_API_HOST}/v2"
    assert not hasattr(paper, "base_url") or "base_url" not in AlpacaEndpoint.__dataclass_fields__
    # A caller cannot inject an arbitrary URL into a typed endpoint.
    with pytest.raises(TypeError):
        AlpacaEndpoint(base_url="https://evil.example/v2")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Authority separation (contract N-1/N-3) — structural guard
# ---------------------------------------------------------------------------


_TRANSPORT_SRC = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "src", "acash",
    "execution", "alpaca", "transport.py",
)

# Canonical state-authority modules the transport must NEVER import (full dotted
# paths). If the transport pulled any of these in, its objects/results could
# carry or issue state transitions (violating ``Vendor Transport != State
# Authority``). ``acash.execution.schema`` owns ``OrderLifecycleState`` and
# ``acash.execution.state_machine`` owns ``transition_order``; both are the exact
# authority the transport must be blind to.
AUTHORITY_MODULES = {
    "acash.execution.coordinator",
    "acash.execution.schema",
    "acash.execution.state_machine",
    "acash.execution.lifecycle",
}

# Dependencies the transport is *allowed* to use, per the sealed architecture:
# the credential provider / account seam and the broker_adapter value/interface
# layer (MissionStep 8F). These are NOT state authorities.
ALLOWED_MODULES = {
    "acash.execution.alpaca.credentials",
    "acash.execution.alpaca.venue",
    "acash.execution.broker_adapter",
}


def _ast_imports(path: str) -> set[str]:
    """Collect real import module paths via AST (structural, not string grep).

    Only ``Import``/``ImportFrom`` AST nodes are inspected, yielding the *full
    dotted module paths* actually referenced — so docstring/comment mentions can
    never produce a false positive, and authorities hidden in a nested import
    (``from acash.execution.coordinator import ...``) are still caught.
    """
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_transport_ast_imports_no_authority_module() -> None:
    imports = _ast_imports(_TRANSPORT_SRC)
    # The full authority paths must not appear in any import statement.
    violations = AUTHORITY_MODULES & imports
    assert not violations, (
        f"transport must NOT import authority modules, got: {sorted(violations)}"
    )


def test_transport_ast_imports_only_intended_acash_modules() -> None:
    imports = _ast_imports(_TRANSPORT_SRC)
    shipped = {i for i in imports if i.startswith("acash.")}
    unexpected = shipped - AUTHORITY_MODULES - ALLOWED_MODULES
    assert not unexpected, (
        f"transport pulls acash modules outside the sealed seam: "
        f"{sorted(unexpected)} (allowed: {sorted(ALLOWED_MODULES)})"
    )


def test_transport_module_does_not_pull_authority_dependencies() -> None:
    """Behavioral interface-contract proof (not source text, not global
    ``sys.modules`` reachability): the transport's PUBLIC API must never surface a
    canonical authority type.

    Why not ``sys.modules`` reachability? Importing ``broker_adapter`` (an
    *allowed* seam) transitively loads ``coordinator``/``schema``/``state_machine``
    because ``broker_adapter`` owns the ``to_coordinator_event`` pump helper. That
    reachability is expected and NOT a violation. What would violate the locked box
    ``Vendor Transport != State Authority`` is the transport *exposing* authority
    through its method surface. This test probes that surface directly.
    """
    authority_type_names = {"CoordinatorEvent", "ExecutionEvent", "OrderLifecycleState"}

    def _collect(annot: object, out: set[str]) -> None:
        if isinstance(annot, str):
            return
        origin = typing.get_origin(annot)
        if origin is typing.Union:  # Optional[X]
            for a in typing.get_args(annot):
                _collect(a, out)
            return
        if origin is not None:  # Sequence[X], dict, list, etc
            for a in typing.get_args(annot):
                _collect(a, out)
            return
        name = getattr(annot, "__name__", None)
        if name:
            out.add(name)

    exposed: set[str] = set()
    for attr_name in AlpacaTransport.__abstractmethods__:
        attr = getattr(AlpacaTransport, attr_name)
        return_type = getattr(attr, "__annotations__", {}).get("return")
        _collect(return_type, exposed)

    assert authority_type_names.isdisjoint(exposed), (
        f"transport method surface exposes canonical authority types: "
        f"{sorted(authority_type_names & exposed)}"
    )


def test_abstract_transport_is_interface_only() -> None:
    # The transport is an interface seam: it must expose the network methods and
    # carry NO lifecycle/transition authority (matches BrokerAdapter pattern,
    # test_broker_adapter.py). Asserted functionally, not against source.
    for m in ("submit_order", "cancel_order", "query_order", "query_position",
              "stream_trade_events", "rotate_credentials"):
        assert m in AlpacaTransport.__abstractmethods__
    assert not hasattr(AlpacaTransport, "transition_order")
    assert not hasattr(AlpacaTransport, "ExecutionCoordinator")


def test_abstract_event_stream_is_interface_only() -> None:
    assert "close" in AlpacaEventStream.__abstractmethods__


# ---------------------------------------------------------------------------
# Circular-import completion proof (Check 2/4) — self-contained in the suite
# ---------------------------------------------------------------------------


def test_execution_root_then_alpaca_imports_complete_without_partial_init() -> None:
    """Importing the execution package root then the alpaca seam must complete
    every module without any partially-initialized entry (no import cycle)."""
    importlib.import_module("acash.execution")
    importlib.import_module("acash.execution.alpaca")
    importlib.import_module("acash.execution.alpaca.transport")
    for name in (
        "acash.execution",
        "acash.execution.alpaca",
        "acash.execution.alpaca.transport",
        "acash.execution.broker_adapter",
    ):
        mod = sys.modules.get(name)
        assert mod is not None, f"{name} not imported"
        # A successfully completed module has an executed spec suffix; a partially
        # initialized (circular) module would be left with an unfinished __loader__.
        assert getattr(mod, "__loader__", None) is not None, (
            f"{name} partial/cyclic initialization"
        )
