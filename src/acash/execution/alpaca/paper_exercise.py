"""Phase 7 Paper Exercise — R0 read-only / non-destructive verification harness.

The Paper Exercise checkpoint builds P-evidence (empirically exercised against a
real Alpaca **paper** environment). It is strictly gated behind the locked rule:

$$\boxed{\text{E} \neq \text{P}}$$

before any order lifecycle is exercised, the harness FIRST runs a read-only,
non-destructive verification (R0). R0 never mutates broker state: it probes
connectivity, the credentialed paper session, read-only REST queries, and the
fail-closed path for unknown orders. It NEVER calls ``submit_order`` /
``cancel_order`` / any write endpoint.

Security boundary (locked, BMAP-10 / credential contract §6):
- Credentials come ONLY from the environment (``EnvAlpacaCredentialProvider``
  via ``paper_credential_provider()``); nothing is committed to source/config.
- The venue is hard-pinned to ``ALPACA_PAPER`` (``paper_endpoint()`` +
  ``paper_credential_provider()``). A non-paper venue / live credential is
  rejected by the transport guard before any request is made.
- The evidence DTO carries NO secret material.

This module is read-only BY CONSTRUCTION: the R0 harness references only
``connect`` / ``connected`` / ``query_position`` / ``query_order`` from the
transport seam. ``submit_order`` / ``cancel_order`` are absent from this file
(asserted structurally by the conformance suite).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence, Tuple

from acash.execution.alpaca.credentials import paper_credential_provider
from acash.execution.alpaca.transport import (
    AlpacaTransport,
    AlpacaTransportError,
    PaperHttpAlpacaTransport,
)
from acash.execution.alpaca.venue import paper_endpoint


@dataclass(frozen=True)
class PositionProbe:
    """Read-only position probe result for a single symbol.

    ``present=False`` means the broker reports no position for the symbol
    (REST 404 -> ``None``), NOT that we fabricated a zero position. ``venue`` is
    the broker-reported venue (must equal the paper venue).
    """

    symbol: str
    present: bool
    quantity: Optional[Decimal] = None
    venue: Optional[str] = None


@dataclass(frozen=True)
class PaperReadOnlyEvidence:
    """Structured R0 read-only verification evidence (no secret material).

    Lineage fields: venue (always ``ALPACA_PAPER``), credential resolution
    succeeded/failed (never the credential material), connected state, position
    probes, and whether an unknown-order lookup failed closed as required.
    ``recorded_at_utc`` is the local observation time of this evidence record.
    """

    venue: str
    credentials_resolved: bool
    connected: bool
    position_probes: Tuple[PositionProbe, ...]
    unknown_order_lookup_fail_closed: bool
    recorded_at_utc: datetime


class PaperExerciseError(Exception):
    """Fail-closed R0 harness error (never exposes secret / account material).

    Distinct from the transport seam so callers can route R0 failures to the
    reconciliation path without confusing them with a broker reply.
    """


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Read-only symbols probed by the R0 harness (no position expected on an empty
# paper account; present=False is the normal, honest result).
_KNOWN_SYMBOLS: Tuple[str, ...] = ("SPY", "AAPL", "MSFT", "GOOGL")

# A UUID that is never a real order; used to prove unknown-order fail-closed.
_UNKNOWN_ORDER_ID = "00000000-0000-0000-0000-0000000000f0"


def build_read_only_transport() -> PaperHttpAlpacaTransport:
    """Construct the paper-only, read-only R0 transport.

    Hard-pins credentials to ``ALPACA_PAPER`` and the endpoint to the paper
    domain. Construction fails closed if the venue/credential guard rejects the
    wiring; ``connect()`` fails closed if the credential material is absent.
    """
    return PaperHttpAlpacaTransport(
        provider=paper_credential_provider(),
        endpoint=paper_endpoint(),
    )


def run_read_only_probes(
    transport: AlpacaTransport,
    *,
    position_symbols: Sequence[str] = _KNOWN_SYMBOLS,
) -> PaperReadOnlyEvidence:
    """Execute read-only probes against an injected transport (testable core).

    Non-destructive by construction: only ``connect`` / ``connected`` /
    ``query_position`` / ``query_order`` are touched. Any read-only failure
    raises ``PaperExerciseError`` (fail-closed) rather than returning a green
    record. ``credentials_resolved=True`` means an authenticated session was
    established through ``connect()``; the credential material itself never
    appears in the evidence.
    """
    try:
        transport.connect()
    except AlpacaTransportError as exc:
        raise PaperExerciseError(
            "R0 paper verification failed at connect (credentials absent / "
            "transport auth); refusing to fabricate read-only evidence."
        ) from exc

    connected = transport.connected()

    position_probes: Tuple[PositionProbe, ...] = ()
    for symbol in position_symbols:
        try:
            pos = transport.query_position(symbol)
        except AlpacaTransportError as exc:
            raise PaperExerciseError(
                f"R0 position probe failed for {symbol}; refusing to fabricate "
                "read-only evidence."
            ) from exc
        probe = PositionProbe(
            symbol=symbol,
            present=pos is not None,
            quantity=pos.quantity if pos is not None else None,
            venue=pos.venue if pos is not None else None,
        )
        position_probes = (*position_probes, probe)
        # A broker position reported under a non-paper venue breaks the
        # paper-only boundary; fail closed, never silently accept it.
        if pos is not None and pos.venue != "ALPACA_PAPER":
            raise PaperExerciseError(
                f"R0 position probe venue {pos.venue!r} != ALPACA_PAPER "
                "(cross-venue guard fail-closed)."
            )

    # Unknown-order lookup MUST fail closed (never a fabricated terminal state):
    #   - transport raises AlpacaTransportError (404 / unknown)  -> fail-closed OK
    #   - transport returns None   -> explicit unknown           -> fail-closed OK
    #   - transport returns an Order object for a random UUID    -> broker
    #     fabricated/guessed a state                             -> FAIL closed
    unknown_order_lookup_fail_closed = False
    try:
        result = transport.query_order(_UNKNOWN_ORDER_ID)
    except AlpacaTransportError:
        unknown_order_lookup_fail_closed = True
    else:
        if result is None:
            unknown_order_lookup_fail_closed = True
        else:
            raise PaperExerciseError(
                f"R0 unknown-order lookup returned an order object for "
                f"{_UNKNOWN_ORDER_ID}; broker must fail-closed for unknown orders."
            )

    return PaperReadOnlyEvidence(
        venue="ALPACA_PAPER",
        credentials_resolved=True,
        connected=connected,
        position_probes=position_probes,
        unknown_order_lookup_fail_closed=unknown_order_lookup_fail_closed,
        recorded_at_utc=_utcnow(),
    )


def run_read_only_verification() -> PaperReadOnlyEvidence:
    """Run the R0 read-only paper verification (production entry point).

    Builds the paper-only transport from the environment and executes the
    read-only probes. Fail-closed: absent/invalid credentials raise
    ``PaperExerciseError`` before any probe runs.
    """
    return run_read_only_probes(build_read_only_transport())