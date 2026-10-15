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
- ``build_executor_client``: the future executor transport with pinned
  posture (no redirects, no ambient proxy inheritance, TLS always verified,
  explicit timeout).

Ledger authority decision (C4 audit outcome): the single canonical source
of truth for the future acquisition attempt ledger is M1.8.1
``DurableAttemptJournal`` (create-once runs, append-only lines, completion
markers, no-resume classification). ``ZeroRetryPolicy`` remains the
execution policy (attempt counting without sleep/retry), and the canary
``ReservationJournal`` (unmerged PR #32) is NOT a second ledger: no third
ledger will be invented. Durable file-sync is ordering/an-observation of
best effort only — it is NOT proof of crash/power-loss durability, and any
future real dispatch stays blocked until the target filesystem demonstrates
the required durability semantics.
Reservation ordering (specified dispatch procedure, proven by the offline
end-to-end test, not by production code — no executor exists here):
create_run binds authority; a request-specific RESERVED attempt (seq 1,
carrying the bound-request digest) is recorded and read back verified
BEFORE any dispatch; terminal failures settle ABORTED; ambiguous failures
settle nothing (INTERRUPTED, conserved). M1.8.1 performs no flush/fsync on
append — verified by source inspection — so crash durability is unproven
and is recorded as blocking, never inferred.

OPEN CONTRACT QUESTIONS (unresolved authority decisions, recorded — never
silently defaulted):
- ``asof``: the governed M1.7 nine-field canonical request has no ``asof``
  field (locked by regression test). Official Alpaca semantics give ``asof``
  a current-day default for symbol mapping. Assessment: immaterial for the
  frozen canary scope (VOO/BND/GLD/BIL exhibit no mapping change across
  2026-09-28..2026-10-02), but MATERIAL in general — a default that varies
  with request time breaks point-in-time reproducibility. Appending ``asof``
  as a tenth field (or any scope/digest change) requires a separately
  reviewed contract migration; until then the future dispatch gate fails
  closed on any request outside the frozen nine-field shape.
- Daily end semantics: ``end`` is the inclusive calendar date exactly as
  bound (2026-10-02 means the full session; never silently expanded).
- Production trust root: no hardcoded approval keys, no fabricated signed
  approval, no environment variable treated as operator authorization, no
  ambient credential loading exist or may exist here. An independently
  governed production trust root plus real operator-held entitlement
  material (verified in a separate authorized process) are required before
  any real executor becomes active; until then only fail-closed denial
  paths are implemented.
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
    """Allowlist the future executor destination (exact origin + exact path).

    Destination identity is scheme + netloc + path, compared exactly:
    - https only;
    - netloc must equal ``data.alpaca.markets`` exactly (no userinfo, no
      explicit port — ``urlparse().hostname`` alone would strip both);
    - path must equal ``/v2/stocks/bars`` exactly after rejecting any
      percent-encoding (encoded separators or traversal could normalize
      differently downstream; the canonical destination is never encoded);
    - query strings and fragments are denied: request parameters travel
      exclusively through the canonical 9-tuple binding, and a query
      embedded in the URL would bypass that single authority.
    """
    try:
        parsed = urlparse(str(url))
    except ValueError as exc:
        raise DataContractError(f"D1_DESTINATION_MALFORMED: {url!r}.") from exc
    if parsed.scheme != "https":
        raise DataContractError(f"D1_DESTINATION_NOT_HTTPS: {url!r}.")
    if parsed.netloc != "data.alpaca.markets":
        raise DataContractError(f"D1_DESTINATION_ORIGIN_DENIED: {url!r}.")
    if "%" in parsed.path:
        raise DataContractError(f"D1_DESTINATION_ENCODED_PATH: {url!r}.")
    if parsed.path != CANARY_PATH_PREFIX:
        raise DataContractError(f"D1_DESTINATION_PATH_DENIED: {url!r}.")
    if parsed.query or parsed.fragment:
        raise DataContractError(f"D1_DESTINATION_QUERY_FRAGMENT_DENIED: {url!r}.")


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
    """Read a response body chunk-wise under the cap (exact accounting).

    Accounting unit (definition): DECODED content bytes yielded by the
    transport iterator. This is exactly the byte population that lands in
    memory and in evidence. It excludes HTTP headers, chunked-transfer
    framing, and TLS framing, which are never counted and never claimed.
    When the provider applies a content coding, the decoded (inflated)
    bytes are what the cap constrains: the stricter bound is preserved and
    wire-byte counts are never reported.

    Post-conditions: on success the returned body length equals the
    cap-observed delta for this call; on overflow or midstream transport
    failure the cap is halted (poisoned against reuse) and nothing is
    returned. A declared Content-Length is cross-checked for exact
    equality when — and only when — no content coding is present (an
    encoded length is not comparable to decoded bytes) and the header
    parses as an integer; an unparseable header is treated as absent and
    recorded in the docstring trail, never silently.
    """
    declared: int | None = None
    if "content-encoding" not in response.headers:
        raw_length = response.headers.get("content-length")
        if raw_length is not None:
            try:
                declared = int(str(raw_length).strip())
            except (ValueError, TypeError):
                declared = None
    body = bytearray()
    observed_before = cap.observed
    try:
        for chunk in response.iter_bytes(chunk_size=4096):
            cap.consume(bytes(chunk))
            body.extend(chunk)
    except DataContractError:
        raise
    except httpx.RequestError as exc:
        cap.halted = True
        raise DataContractError(
            f"D1_STREAM_INTERRUPTED: midstream transport failure: {exc}."
        ) from exc
    if declared is not None and declared != cap.observed - observed_before:
        cap.halted = True
        raise DataContractError(
            f"D1_BODY_LENGTH_MISMATCH: declared Content-Length {declared} != "
            f"observed {cap.observed - observed_before}."
        )
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
    if 300 <= status < 400:
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


def build_executor_client(timeout_seconds: float = 30.0) -> httpx.Client:
    """Construct the future executor transport with pinned safety posture.

    - Redirects NEVER followed (3xx is classified fail-closed instead).
    - Ambient proxy environment NEVER inherited (``trust_env=False``): proxy
      settings from the process environment cannot reroute provider traffic.
    - TLS verification always on; explicit timeout (no ambient default).
    """
    if (
        not isinstance(timeout_seconds, (int, float))
        or isinstance(timeout_seconds, bool)
        or timeout_seconds <= 0
    ):
        raise DataContractError("D1_CLIENT_TIMEOUT_NONPOSITIVE.")
    return httpx.Client(
        follow_redirects=False,
        trust_env=False,
        verify=True,
        timeout=float(timeout_seconds),
    )
