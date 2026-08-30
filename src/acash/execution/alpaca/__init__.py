"""Alpaca broker transport (Phase 7 Step 8F: 8F-2 Concrete Paper Transport).

This package provides the Alpaca credential seam, the typed venue
configuration, the transport abstraction plus its concrete paper HTTP/SSE
implementation, and the 8F-3 concrete ``AlpacaPaperAdapter`` that maps raw
Alpaca shapes onto the canonical ``BrokerRawEvent`` vocabulary. It contains NO
state authority and NO live credentials.

Authority separation (locked, contract §1 N-1/N-3): nothing here computes or
returns an ``OrderLifecycleState`` and nothing performs canonical normalization;
the 8F-3 adapter maps raw Alpaca shapes onto ``BrokerRawEvent`` and the engine
pump runs ``normalize_broker_event()`` (Step 8C).

Concrete transport invariants (8F-2):
- HTTP success != execution state transition (``SubmitReceipt``/cancel-request
  only; never a terminal canonical state).
- Paper-only enforcement in both layers: typed ``AlpacaEndpoint``/``AlpacaVenue``
  (derived base URL, not a free URL string) + paper transport hard-rejects
  non-paper at construction and re-asserts at ``connect()``.
- Fail-closed on timeout/network/auth (timeout -> ambiguity, not a terminal guess).

Adapter invariants (8F-3, locked): the adapter is a command sink + observation
source ONLY — no lifecycle state, no ``transition_order()``, no normalizer
authority. ``event_id`` -> ``broker_sequence`` verbatim (BMAP-03); POST ACK !=
FILLED; DELETE 204 != CANCELLED; timeout -> CONNECTION_LOST -> UNKNOWN;
canceled-without-provenance / overfill / non-terminal-in-flight -> fail-closed
``AlpacaAdapterMappingError`` (BMAP-01/06/07).
"""

from acash.execution.alpaca.adapter import (
    AlpacaAdapterMappingError,
    AlpacaPaperAdapter,
)
from acash.execution.alpaca.credentials import (
    ENV_ALPACA_API_KEY_ID,
    ENV_ALPACA_API_SECRET,
    LIVE_API_HOST,
    PAPER_API_HOST,
    AlpacaCredentialError,
    AlpacaCredentialProvider,
    AlpacaCredentials,
    EnvAlpacaCredentialProvider,
    PaperCredentialGuardError,
    assert_paper_venue,
    paper_credential_provider,
)
from acash.execution.alpaca.order_exercise import (
    LifecycleEvidence,
    OrderExerciseError,
    OrderExerciseHarness,
    build_execution_manifest,
    build_nominal_intent,
    build_reconciliation_report,
    run_order_exercise_verification,
)
from acash.execution.alpaca.paper_exercise import (
    PaperExerciseError,
    PaperReadOnlyEvidence,
    PositionProbe,
    build_read_only_transport,
    run_read_only_probes,
    run_read_only_verification,
)
from acash.execution.alpaca.transport import (
    AlpacaCancelReason,
    AlpacaEventStream,
    AlpacaNonCancellableError,
    AlpacaOrder,
    AlpacaOrderStatus,
    AlpacaTradeEvent,
    AlpacaTradeEventType,
    AlpacaTransport,
    AlpacaTransportAuthError,
    AlpacaTransportError,
    AlpacaTransportParseError,
    AlpacaTransportTimeoutError,
    AlpacaVenueMismatchError,
    HttpAlpacaTransport,
    PaperHttpAlpacaTransport,
)
from acash.execution.alpaca.venue import (
    AlpacaEndpoint,
    AlpacaVenue,
    live_endpoint,
    paper_endpoint,
)

__all__ = [
    "AlpacaAdapterMappingError",
    "AlpacaCancelReason",
    "AlpacaCredentialError",
    "AlpacaCredentialProvider",
    "AlpacaCredentials",
    "AlpacaEndpoint",
    "AlpacaEventStream",
    "AlpacaNonCancellableError",
    "AlpacaOrder",
    "AlpacaOrderStatus",
    "AlpacaPaperAdapter",
    "AlpacaTradeEvent",
    "AlpacaTradeEventType",
    "AlpacaTransport",
    "AlpacaTransportAuthError",
    "AlpacaTransportError",
    "AlpacaTransportParseError",
    "AlpacaTransportTimeoutError",
    "AlpacaVenue",
    "AlpacaVenueMismatchError",
    "ENV_ALPACA_API_KEY_ID",
    "ENV_ALPACA_API_SECRET",
    "EnvAlpacaCredentialProvider",
    "HttpAlpacaTransport",
    "LIVE_API_HOST",
    "LifecycleEvidence",
    "OrderExerciseError",
    "OrderExerciseHarness",
    "PAPER_API_HOST",
    "PaperCredentialGuardError",
    "PaperExerciseError",
    "PaperHttpAlpacaTransport",
    "PaperReadOnlyEvidence",
    "PositionProbe",
    "assert_paper_venue",
    "build_execution_manifest",
    "build_nominal_intent",
    "build_read_only_transport",
    "build_reconciliation_report",
    "live_endpoint",
    "paper_credential_provider",
    "paper_endpoint",
    "run_order_exercise_verification",
    "run_read_only_probes",
    "run_read_only_verification",
]
