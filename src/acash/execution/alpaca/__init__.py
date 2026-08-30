"""Alpaca broker transport (Phase 7 Step 8F: 8F-2 Concrete Paper Transport).

This package provides the Alpaca credential seam, the typed venue
configuration, and the transport abstraction plus its concrete paper HTTP/SSE
implementation. It contains NO state authority and NO live credentials.

Authority separation (locked, contract §1 N-1/N-3): nothing here computes or
returns an ``OrderLifecycleState`` and nothing performs canonical normalization;
the adapter maps raw Alpaca shapes onto ``BrokerRawEvent`` and the engine pump
runs ``normalize_broker_event()`` (Step 8C).

Concrete transport invariants (8F-2):
- HTTP success != execution state transition (``SubmitReceipt``/cancel-request
  only; never a terminal canonical state).
- Paper-only enforcement in both layers: typed ``AlpacaEndpoint``/``AlpacaVenue``
  (derived base URL, not a free URL string) + paper transport hard-rejects
  non-paper at construction and re-asserts at ``connect()``.
- Fail-closed on timeout/network/auth (timeout -> ambiguity, not a terminal guess).
"""

from acash.execution.alpaca.credentials import (
    ENV_ALPACA_API_KEY_ID,
    ENV_ALPACA_API_SECRET,
    LIVE_API_HOST,
    PAPER_API_HOST,
    AlpacaCredentialError,
    AlpacaCredentialProvider,
    AlpacaCredentials,
    EnvAlpacaCredentialProvider,
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
    "AlpacaCancelReason",
    "AlpacaCredentialError",
    "AlpacaCredentialProvider",
    "AlpacaCredentials",
    "AlpacaEndpoint",
    "AlpacaEventStream",
    "AlpacaNonCancellableError",
    "AlpacaOrder",
    "AlpacaOrderStatus",
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
    "PAPER_API_HOST",
    "PaperHttpAlpacaTransport",
    "live_endpoint",
    "paper_endpoint",
]
