"""D3-01 offline streaming evidence proof (OFFLINE ONLY — NO LIVE DISPATCH).

Smallest useful enforcement for the Lane A byte contract: identity-only
streaming reads with exact accounting, built on the D1 safety slice and
M1.8.1 evidence hashing. All tests use httpx.MockTransport; no real
provider HTTP exists or is reachable here.

Contract (PROPOSAL status until ratified — see admit_byte_population):
- Identity content encoding ONLY. Any response carrying a
  ``content-encoding`` other than ``identity`` (including gzip/deflate)
  is rejected BEFORE any body byte is consumed: a declared encoding is
  never trusted as proof of actual server behavior, and a single
  cap/hash cannot honestly cover two different byte populations.
- Raw wire bytes are streamed via ``iter_raw()`` and hashed incrementally,
  so the recorded digest is the digest of exactly what was counted and
  stored — no second pass, no re-read.
- ``Content-Length``, when present and parseable under identity coding,
  must equal the observed total exactly; mismatch (either direction)
  halts and fails closed. Unparseable values are treated as absent (this
  mirrors the established ``lane_a_d1_safety.read_capped`` policy; it is
  NOT a new network policy and is recorded, not silently ratified).
- ``Content-Length`` malformed-absent policy (RECORDED, two options):
  (a) treat unparseable as absent [current, matches D1]; or (b) reject
  fail-closed. Neither is ratified for real dispatch here.
- Any iterator failure — declared HTTPX transport/stream errors AND
  unexpected non-HTTPX exceptions — halts (poisons) the cap before
  propagating, so no partial or ambiguous read can later be reused as
  successful evidence. Declared transport errors are reclassified as
  ``DataContractError``; unknown errors propagate UNCHANGED after
  poisoning, so programming faults are never disguised as contract
  outcomes.
- Attempt budgets are conserved: failed/interrupted reads consume their
  reservation; no retry, no refund, no resume.

BOUNDED-MEMORY BOUNDARY (explicit, not overclaimed):
- Counted bytes: ``cap.observed`` <= cap + (size of one upstream chunk).
- Retained body: <= cap. The breaching chunk raises in ``consume`` BEFORE
  ``body.extend``, so it is never retained.
- Upstream transport / decoder allocations: NOT bounded by this layer.
  httpx 0.28.1 ``Response.iter_raw`` re-chunks via ``ByteChunker``, whose
  ``decode`` materializes the entire ``raw_stream_bytes`` chunk as a list
  of slices; passing a ``chunk_size`` therefore bounds neither the upstream
  chunk nor peak memory. No hard resident-memory bound is claimed, and no
  ``chunk_size`` is set (it would only add a slice list).

What this does NOT establish: production streaming enforcement, target-
host crash durability, entitlement, or acquisition authority. Those remain
external prerequisites with LANE_A = UNISSUED.
"""

from __future__ import annotations

import hashlib
from typing import Tuple

import httpx

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_d1_safety import StreamingByteCap
from acash.data.qualification.manifest import compute_page_sha256

IDENTITY_ENCODINGS = ("", "identity")


def read_identity_capped(
    response: httpx.Response, cap: StreamingByteCap
) -> Tuple[bytes, str]:
    """Stream identity-encoded body under the cap; return (body, sha256).

    The response MUST come from a streaming request (``client.stream``):
    an eagerly read response (``client.get``) has already consumed its
    stream, and re-reading it would silently bypass byte accounting —
    such responses fail closed here. Fails closed on: non-identity
    content coding, cap overflow, midstream transport failure, and
    Content-Length disagreement. The returned digest is computed
    incrementally over the exact counted bytes.
    """
    if response.is_stream_consumed:
        raise DataContractError(
            "D3_RESPONSE_ALREADY_CONSUMED: streaming reads require an "
            "unconsumed streaming response; eagerly read bodies bypass "
            "byte accounting."
        )
    coding = response.headers.get("content-encoding", "")
    if coding.strip().lower() not in IDENTITY_ENCODINGS:
        raise DataContractError(
            f"D3_IDENTITY_ENCODING_REJECTED: content-encoding {coding!r} "
            "is not identity; refusing to conflate coded and raw bytes."
        )
    declared: int | None = None
    raw_length = response.headers.get("content-length")
    if raw_length is not None:
        try:
            declared = int(str(raw_length).strip())
        except (ValueError, TypeError):
            declared = None
    digest = hashlib.sha256()
    body = bytearray()
    observed_before = cap.observed
    try:
        for chunk in response.iter_raw():
            raw_chunk = bytes(chunk)
            cap.consume(raw_chunk)
            digest.update(raw_chunk)
            body.extend(raw_chunk)
    except DataContractError:
        raise
    except (httpx.RequestError, httpx.StreamError) as exc:
        # StreamClosed/StreamConsumed extend RuntimeError, not
        # RequestError: both families must halt the cap explicitly.
        cap.halted = True
        raise DataContractError(
            f"D3_STREAM_INTERRUPTED: midstream transport failure: {exc}."
        ) from exc
    except Exception:
        # Any OTHER iterator failure (e.g. a raising generator) must still
        # poison the cap: an un-poisoned cap would let an ambiguous read be
        # reused as successful evidence. Re-raise UNCHANGED (no wrapping) so
        # programming errors are diagnosed, not disguised as transport
        # contract outcomes. BaseException (KeyboardInterrupt/SystemExit)
        # is intentionally not caught.
        cap.halted = True
        raise
    if declared is not None and declared != cap.observed - observed_before:
        cap.halted = True
        raise DataContractError(
            f"D3_BODY_LENGTH_MISMATCH: declared Content-Length {declared} != "
            f"observed {cap.observed - observed_before}."
        )
    raw_body = bytes(body)
    if compute_page_sha256(raw_body) != digest.hexdigest():
        raise DataContractError("D3_DIGEST_INTERNAL_MISMATCH.")
    return raw_body, digest.hexdigest()
