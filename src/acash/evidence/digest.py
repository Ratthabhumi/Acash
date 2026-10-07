"""Cryptographic digests and canonical representations for the Evidence Plane."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from acash.core.domain.exceptions import DataContractError

_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def content_sha256(data: bytes | str) -> str:
    """Compute deterministic SHA-256 hex digest of raw bytes or UTF-8 string."""
    if isinstance(data, str):
        payload = data.encode("utf-8")
    elif isinstance(data, (bytes, bytearray)):
        payload = bytes(data)
    else:
        raise DataContractError(
            f"EVIDENCE_DIGEST_BAD_TYPE: expected bytes or str, got {type(data).__name__}."
        )
    return hashlib.sha256(payload).hexdigest()


def canonical_manifest_sha256(manifest_dict: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 digest of a manifest document.

    Enforces deterministic formatting: sort_keys=True, compact separators=(',', ':').
    """
    if not isinstance(manifest_dict, Mapping):
        raise DataContractError(
            f"EVIDENCE_MANIFEST_NOT_MAPPING: expected mapping, got {type(manifest_dict).__name__}."
        )
    try:
        canonical_json = json.dumps(
            manifest_dict,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise DataContractError(
            f"EVIDENCE_MANIFEST_SERIALIZATION_FAILED: {exc}."
        ) from exc
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def ordered_page_chain_digest(page_digests: Sequence[str]) -> str:
    """Compute ordered chain digest over a sequence of page content SHA-256 hex digests.

    Fails closed if the chain is empty or any element is not a valid 64-char hex string.
    """
    if not page_digests:
        raise DataContractError(
            "EVIDENCE_PAGE_CHAIN_EMPTY: cannot compute digest of an empty page sequence."
        )
    for idx, digest in enumerate(page_digests):
        if not isinstance(digest, str) or not _HEX64_PATTERN.match(digest):
            raise DataContractError(
                f"EVIDENCE_PAGE_DIGEST_INVALID: element at index {idx} is not a valid 64-char hex SHA-256."
            )
    chain_bytes = "\n".join(page_digests).encode("utf-8")
    return hashlib.sha256(chain_bytes).hexdigest()
