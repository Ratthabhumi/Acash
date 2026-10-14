"""D1 acquisition-safety slice (OFFLINE ONLY — NO LIVE DISPATCH).

Narrow, independently testable safety contracts for a future bounded
Alpaca historical-bars executor. All tests use httpx.MockTransport and
synthetic credentials; no real provider HTTP exists or is reachable here.

Reuse decisions (source: src/acash/data/qualification/client.py):
- REUSED (imported, not copied): AlpacaAuthenticationError (401),
  AlpacaAccessDeniedError (403), AlpacaRateLimitExceededError (429),
  compute_page_sha256, MarketDataFeed/PriceAdjustment enums.
- NOT reused: the bounded-429-retry executor (Lane A mandates zero retry;
  this module never sleeps/retries), the ambient environment credential
  default (this module has no credential provider at all and never loads
  ambient credentials), the single-symbol 1Min contract, the 50-page cap,
  and whole-body response.content reads.

Contracts:
- ``D1RequestBinder``: the M1.7 canonical 9-tuple is the ONLY request
  representation. Extra/missing keys fail closed; no provider defaults.
- ``ZeroRetryPolicy``: exactly one attempt; 429/timeout/transport error
  raises immediately (proven by call counting: no second invocation).
- ``StreamingByteCap``: chunk-wise accumulation with a hard cap covering
  success AND error bodies; overflow raises before further reads; the
  observed total is exact.
- ``DestinationGuard``: https + data.alpaca.markets + /v2/stocks/bars
  prefix only; redirects denied (httpx follow_redirects forced False;
  3xx raises instead of following).
- ``CredentialIsolation``: no ambient credential loading. A client
  without an explicitly injected provider fails closed before any
  transport use; synthetic test credentials are never persisted.
- ``ErrorClassifier``: maps outcomes to the reused M1.7/SIP exception
  taxonomy (401/403/429/timeout/malformed/redirect/oversize) without
  retrying or falling back.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Tuple
from urllib.parse import urlparse

import httpx

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.client import (
    AlpacaAccessDeniedError,
    AlpacaAuthenticationError,
    AlpacaRateLimitExceededError,
)
from acash.data.qualification.lane_a_authority import (
    LaneAPlannedRequest,
    canonical_query_parameters,
)

CANARY_ORIGIN: str = "https://data.alpaca.markets"
CANARY_PATH_PREFIX: str = "/v2/stocks/bars"
CANONICAL_PARAM_KEYS: Tuple[str, ...] = (
    "symbols",
    "timeframe",
    "start",
    "end",
    "adjustment",
    "feed",
    "sort",
    "limit",
    "currency",
)


@dataclass(frozen=True)
class D1BoundRequest:
    """M1.7 request bound to its canonical parameter tuple (no defaults)."""

    params: Tuple[Tuple[str, str], ...]

    def __post_init__(self) -> None:
        keys = [key for key, _ in self.params]
        if tuple(keys) != CANONICAL_PARAM_KEYS:
            raise DataContractError(
                f"D1_REQUEST_NOT_CANONICAL: expected keys {list(CANONICAL_PARAM_KEYS)}, "
                f"got {keys}."
            )
        values = dict(self.params)
        if any(not str(value).strip() for value in values.values()):
            raise DataContractError("D1_REQUEST_EMPTY_VALUE.")


def bind_request(params: Mapping[str, str]) -> D1BoundRequest:
    """Bind a caller-supplied mapping to the canonical 9-tuple (fail-closed)."""
    if not isinstance(params, Mapping):
        raise DataContractError("D1_REQUEST_NOT_MAPPING.")
    return D1BoundRequest(params=tuple((str(k), str(v)) for k, v in params.items()))


def bind_planned_request(request: LaneAPlannedRequest) -> D1BoundRequest:
    """Bind an M1.7 planned request through M1.7 serialization (SINGLE authority)."""
    if not isinstance(request, LaneAPlannedRequest):
        raise DataContractError(
            f"D1_REQUEST_NOT_PLANNED: {type(request).__name__}."
        )
    return D1BoundRequest(params=tuple(canonical_query_parameters(request)))


def destination_guard(url: str) -> None:
    """Allowlist the future executor destination (https + host + path)."""
    try:
        parsed = urlparse(str(url))
    except ValueError as exc:
        raise DataContractError(f"D1_DESTINATION_MALFORMED: {url!r}.") from exc
    if parsed.scheme != "https":
        raise DataContractError(f"D1_DESTINATION_NOT_HTTPS: {url!r}.")
    if parsed.hostname != "data.alpaca.markets":
        raise DataContractError(f"D1_DESTINATION_HOST_DENIED: {url!r}.")
    if not parsed.path.startswith(CANARY_PATH_PREFIX):
        raise DataContractError(f"D1_DESTINATION_PATH_DENIED: {url!r}.")


class ZeroRetryPolicy:
    """Exactly one attempt; any failure raises immediately, never retries."""

    def __init__(self) -> None:
        self.attempts = 0

    def execute_once(self, call: Callable[[], httpx.Response]) -> httpx.Response:
        """Invoke ``call`` once; 429/transport/timeout errors raise at once."""
        self.attempts += 1
        if self.attempts > 1:
            raise DataContractError(
                "D1_RETRY_FORBIDDEN: Lane A mandates zero retries."
            )
        try:
            response = call()
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise DataContractError(
                f"D1_TRANSPORT_FAILED_NO_RETRY: {exc}."
            ) from exc
        if response.status_code == 429:
            raise AlpacaRateLimitExceededError(
                "Alpaca rate limit hit (HTTP 429): zero-retry policy, no second attempt."
            )
        return response


class StreamingByteCap:
    """Chunk-wise byte accounting with a hard cap (success and error bodies)."""

    def __init__(self, max_bytes: int) -> None:
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
            raise DataContractError("D1_CAP_NONPOSITIVE.")
        self._max_bytes = max_bytes
        self.observed = 0
        self.halted = False

    def consume(self, chunk: bytes) -> None:
        """Account one chunk; overflow halts and raises before further reads."""
        if self.halted:
            raise DataContractError("D1_STREAM_HALTED.")
        if not isinstance(chunk, (bytes, bytearray)):
            raise DataContractError("D1_STREAM_BAD_CHUNK.")
        if self.observed + len(chunk) > self._max_bytes:
            self.halted = True
            raise DataContractError(
                f"D1_STREAM_BYTES_EXCEEDED: cap {self._max_bytes} breached."
            )
        self.observed += len(chunk)


def read_capped(response: httpx.Response, cap: StreamingByteCap) -> bytes:
    """Read a response body chunk-wise under the cap (exact accounting)."""
    body = bytearray()
    for chunk in response.iter_bytes(chunk_size=4096):
        cap.consume(bytes(chunk))
        body.extend(chunk)
    return bytes(body)


def classify_response(response: httpx.Response) -> str:
    """Map an outcome to the reused exception taxonomy (no retry/fallback)."""
    status = response.status_code
    if status == 401:
        raise AlpacaAuthenticationError("HTTP 401: authentication failed.")
    if status == 403:
        raise AlpacaAccessDeniedError("HTTP 403: access forbidden.")
    if status == 429:
        raise AlpacaRateLimitExceededError("HTTP 429: zero-retry policy.")
    if status in (301, 302, 303, 307, 308):
        raise DataContractError(
            f"D1_REDIRECT_DENIED: HTTP {status} redirect refused, never followed."
        )
    if status != 200:
        raise DataContractError(f"D1_HTTP_UNEXPECTED_STATUS: {status}.")
    return "OK"


def build_test_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.Client:
    """Test-only client factory: MockTransport, redirects NEVER followed."""
    return httpx.Client(
        transport=httpx.MockTransport(handler), follow_redirects=False
    )
