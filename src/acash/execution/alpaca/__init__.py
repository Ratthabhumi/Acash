"""Alpaca broker transport abstraction (Phase 7 Step 8F follow-on).

Step 1 of the Alpaca paper adapter: **interface + paper transport abstraction**.
This package defines the credential provider seam and the transport seam that a
future ``AlpacaPaperAdapter`` (an implementation of ``BrokerAdapter``) will
delegate to. It contains NO concrete HTTP/SDK wiring, NO network I/O, NO live
credentials, and NO state authority.

Authority separation (contract §1 N-1/N-3): nothing here computes or returns an
``OrderLifecycleState`` and nothing performs canonical normalization; the adapter
maps raw Alpaca shapes onto ``BrokerRawEvent`` and the engine pump runs
``normalize_broker_event()`` (Step 8C).
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
    AlpacaEndpoint,
    AlpacaEventStream,
    AlpacaOrder,
    AlpacaOrderStatus,
    AlpacaTradeEvent,
    AlpacaTradeEventType,
    AlpacaTransport,
)

__all__ = [
    "AlpacaCancelReason",
    "AlpacaCredentialError",
    "AlpacaCredentialProvider",
    "AlpacaCredentials",
    "AlpacaEndpoint",
    "AlpacaEventStream",
    "AlpacaOrder",
    "AlpacaOrderStatus",
    "AlpacaTradeEvent",
    "AlpacaTradeEventType",
    "AlpacaTransport",
    "ENV_ALPACA_API_KEY_ID",
    "ENV_ALPACA_API_SECRET",
    "EnvAlpacaCredentialProvider",
    "LIVE_API_HOST",
    "PAPER_API_HOST",
]
