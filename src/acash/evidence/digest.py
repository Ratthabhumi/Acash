"""Cryptographic digests and canonical representations for the Evidence Plane."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, Sequence

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer

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

    Enforces single canonical authority: uses CanonicalConfigSerializer.
    """
    if not isinstance(manifest_dict, Mapping):
        raise DataContractError(
            f"EVIDENCE_MANIFEST_NOT_MAPPING: expected mapping, got {type(manifest_dict).__name__}."
        )
    try:
        return CanonicalConfigSerializer.compute_sha256(dict(manifest_dict))
    except (DataContractError, TypeError, ValueError) as exc:
        raise DataContractError(
            f"EVIDENCE_MANIFEST_SERIALIZATION_FAILED: {exc}."
        ) from exc


def ordered_page_chain_digest(pages: Sequence[Any]) -> str:
    """Compute ordered chain digest over a sequence of page provenance records.

    Binds full pagination provenance:
    - page_index
    - request_token
    - next_page_token
    - raw_bytes_sha256
    - item_count

    Uses CanonicalConfigSerializer to enforce deterministic, collision-free canonical serialization.
    Fails closed if the chain is empty or any element is missing or malformed.
    """
    if not pages:
        raise DataContractError(
            "EVIDENCE_PAGE_CHAIN_EMPTY: cannot compute digest of an empty page sequence."
        )

    chain_entries = []
    for idx, page in enumerate(pages):
        if hasattr(page, "page_index"):
            page_index = getattr(page, "page_index")
            request_token = getattr(page, "request_token")
            next_page_token = getattr(page, "next_page_token")
            raw_bytes_sha256 = getattr(page, "raw_bytes_sha256")
            item_count = getattr(page, "item_count")
        elif isinstance(page, Mapping):
            try:
                page_index = page["page_index"]
                request_token = page.get("request_token")
                next_page_token = page.get("next_page_token")
                raw_bytes_sha256 = page["raw_bytes_sha256"]
                item_count = page["item_count"]
            except KeyError as exc:
                raise DataContractError(
                    f"EVIDENCE_PAGE_RECORD_MISSING_KEY: index {idx} missing {exc}."
                ) from exc
        else:
            raise DataContractError(
                f"EVIDENCE_PAGE_RECORD_INVALID_TYPE: index {idx} has invalid type {type(page).__name__}."
            )

        if not isinstance(page_index, int) or isinstance(page_index, bool) or page_index < 0:
            raise DataContractError(
                f"EVIDENCE_PAGE_INDEX_INVALID: index {idx} page_index must be non-negative int, got {page_index}."
            )
        if request_token is not None and not isinstance(request_token, str):
            raise DataContractError(
                f"EVIDENCE_REQUEST_TOKEN_INVALID: index {idx} request_token must be str or None, got {type(request_token).__name__}."
            )
        if next_page_token is not None and not isinstance(next_page_token, str):
            raise DataContractError(
                f"EVIDENCE_NEXT_TOKEN_INVALID: index {idx} next_page_token must be str or None, got {type(next_page_token).__name__}."
            )
        if (
            not isinstance(raw_bytes_sha256, str)
            or not _HEX64_PATTERN.match(raw_bytes_sha256)
        ):
            raise DataContractError(
                f"EVIDENCE_PAGE_DIGEST_INVALID: element at index {idx} is not a valid 64-char hex SHA-256."
            )
        if not isinstance(item_count, int) or isinstance(item_count, bool) or item_count < 0:
            raise DataContractError(
                f"EVIDENCE_ITEM_COUNT_INVALID: index {idx} item_count must be non-negative int, got {item_count}."
            )

        chain_entries.append(
            {
                "page_index": page_index,
                "request_token": request_token,
                "next_page_token": next_page_token,
                "raw_bytes_sha256": raw_bytes_sha256,
                "item_count": item_count,
            }
        )

    return CanonicalConfigSerializer.compute_sha256(chain_entries)
