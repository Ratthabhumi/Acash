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
  (a) treat unparseable as absent [V1, matches D1]; or (b) reject
  fail-closed [V2 amendment, owner-directed 2026-10-23]. Neither is
  ratified for real dispatch here. V2 rejects ambiguous, malformed or
  negative lengths BEFORE body iteration; V1 is retained unchanged for
  reproducibility of reviewed evidence.
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
import re
from typing import Tuple

import httpx

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_d1_safety import StreamingByteCap
from acash.data.qualification.manifest import compute_page_sha256

IDENTITY_ENCODINGS = ("", "identity")

BYTE_CONTRACT_V1 = "IDENTITY_ONLY_RAW_RESPONSE_BODY_V1"
BYTE_CONTRACT_V2 = "IDENTITY_ONLY_RAW_RESPONSE_BODY_V2"
D3_OBSERVED_BYTE_BUDGET = 524_288

_CONTENT_LENGTH_DIGITS = re.compile(r"[0-9]+")


def _lenient_declared_length(response: httpx.Response) -> int | None:
    """V1 behavior: unparseable Content-Length is treated as absent."""
    raw_length = response.headers.get("content-length")
    if raw_length is None:
        return None
    try:
        return int(str(raw_length).strip())
    except (ValueError, TypeError):
        return None


def _strict_declared_length(
    response: httpx.Response, cap: StreamingByteCap
) -> int | None:
    """V2 amendment: reject ambiguous, malformed or negative lengths early.

    A missing header is allowed (chunk accounting remains authoritative).
    Present headers must be exactly one field whose value is 1*DIGIT per
    RFC 9110; whitespace, signs, commas, multiple fields and any other
    syntax fail closed BEFORE the response body iterator is touched.
    """
    values = response.headers.get_list("content-length")
    if not values:
        return None
    if len(values) != 1:
        cap.halted = True
        raise DataContractError(
            "D3_CONTENT_LENGTH_AMBIGUOUS: multiple Content-Length headers "
            f"({values!r}); refusing to choose a declared length."
        )
    raw = values[0]
    if not _CONTENT_LENGTH_DIGITS.fullmatch(raw):
        cap.halted = True
        raise DataContractError(
            f"D3_CONTENT_LENGTH_MALFORMED: {raw!r} is not a 1*DIGIT "
            "Content-Length; rejecting before body iteration."
        )
    return int(raw)


def _read_identity_capped(
    response: httpx.Response,
    cap: StreamingByteCap,
    *,
    strict_length: bool,
    reject_poisons_cap: bool,
) -> Tuple[bytes, str]:
    if reject_poisons_cap and cap.halted:
        raise DataContractError(
            "D1_STREAM_HALTED: the byte cap was already poisoned by a failed "
            "or interrupted read; no reuse is permitted."
        )
    if response.is_stream_consumed:
        if reject_poisons_cap:
            cap.halted = True
        raise DataContractError(
            "D3_RESPONSE_ALREADY_CONSUMED: streaming reads require an "
            "unconsumed streaming response; eagerly read bodies bypass "
            "byte accounting."
        )
    coding = response.headers.get("content-encoding", "")
    if coding.strip().lower() not in IDENTITY_ENCODINGS:
        if reject_poisons_cap:
            cap.halted = True
        raise DataContractError(
            f"D3_IDENTITY_ENCODING_REJECTED: content-encoding {coding!r} "
            "is not identity; refusing to conflate coded and raw bytes."
        )
    if strict_length:
        declared = _strict_declared_length(response, cap)
    else:
        declared = _lenient_declared_length(response)
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


def read_identity_capped(
    response: httpx.Response, cap: StreamingByteCap
) -> Tuple[bytes, str]:
    """V1: stream identity body; unparseable Content-Length is absent.

    Preserved unchanged for reproducibility of previously reviewed
    evidence. New work should use :func:`read_identity_capped_v2`.
    """
    return _read_identity_capped(
        response, cap, strict_length=False, reject_poisons_cap=False
    )


def read_identity_capped_v2(
    response: httpx.Response, cap: StreamingByteCap
) -> Tuple[bytes, str]:
    """V2 amendment: fail closed on ambiguous/malformed/negative length.

    Status: PROPOSED_AMENDMENT (owner-directed 2026-10-23), NOT ratified.
    No live dispatch or acquisition authority is implied.

    Differences from V1, all applied BEFORE ``iter_raw()``:
    - Present Content-Length must be exactly one field of 1*DIGIT.
    - Multiple fields, whitespace, signs, commas or non-digits halt the
      cap and raise ``DataContractError`` with zero body bytes consumed.
    - A rejected non-identity encoding or an already-consumed response
      poisons the cap; a halted cap is rejected before any read.
    - A missing header remains allowed; chunk accounting is authoritative.

    Unchanged: identity-only encoding, raw-byte counting, 524,288 observed
    bytes per approved invocation (no reset on failure), zero retry, no
    alternate-feed substitution, post-read oversized-chunk disclosure, no
    hard memory bound.
    """
    return _read_identity_capped(
        response, cap, strict_length=True, reject_poisons_cap=True
    )
