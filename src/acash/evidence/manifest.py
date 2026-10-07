"""Canonical manifest models for the Retrieval Evidence Plane."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.evidence.digest import (
    canonical_manifest_sha256,
    ordered_page_chain_digest,
)
from acash.evidence.writer import write_immutable_json

_HEX40_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class RetrievalPageRecord:
    """Provenance record of an individual retrieved data page."""

    page_index: int
    request_token: Optional[str]
    next_page_token: Optional[str]
    item_count: int
    raw_bytes_sha256: str
    page_file: str
    rate_limit_headers: Mapping[str, str]
    retrieved_at_utc: str

    def __post_init__(self) -> None:
        if self.page_index < 0:
            raise DataContractError(
                f"PAGE_RECORD_INVALID_INDEX: page_index must be >= 0, got {self.page_index}."
            )
        if self.item_count < 0:
            raise DataContractError(
                f"PAGE_RECORD_INVALID_COUNT: item_count must be >= 0, got {self.item_count}."
            )
        if not isinstance(self.raw_bytes_sha256, str) or not _HEX64_PATTERN.match(self.raw_bytes_sha256):
            raise DataContractError(
                f"PAGE_RECORD_INVALID_DIGEST: raw_bytes_sha256 must be 64-char hex SHA-256, got {self.raw_bytes_sha256}."
            )
        if not self.page_file or "/" in self.page_file or "\\" in self.page_file:
            raise DataContractError(
                f"PAGE_RECORD_INVALID_FILENAME: page_file must be a relative basename, got {self.page_file}."
            )
        try:
            datetime.fromisoformat(self.retrieved_at_utc)
        except (ValueError, TypeError) as exc:
            raise DataContractError(
                f"PAGE_RECORD_INVALID_TIMESTAMP: retrieved_at_utc must be ISO-8601, got {self.retrieved_at_utc}."
            ) from exc

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_index": self.page_index,
            "request_token": self.request_token,
            "next_page_token": self.next_page_token,
            "item_count": self.item_count,
            "raw_bytes_sha256": self.raw_bytes_sha256,
            "page_file": self.page_file,
            "rate_limit_headers": dict(self.rate_limit_headers),
            "retrieved_at_utc": self.retrieved_at_utc,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RetrievalPageRecord":
        return cls(
            page_index=int(data["page_index"]),
            request_token=data.get("request_token"),
            next_page_token=data.get("next_page_token"),
            item_count=int(data["item_count"]),
            raw_bytes_sha256=str(data["raw_bytes_sha256"]),
            page_file=str(data["page_file"]),
            rate_limit_headers=dict(data.get("rate_limit_headers", {})),
            retrieved_at_utc=str(data["retrieved_at_utc"]),
        )


@dataclass(frozen=True)
class RetrievalRunManifest:
    """Canonical run manifest summarizing an entire retrieval invocation."""

    run_id: str
    authority_id: str
    session: str
    capability: str
    symbol: str
    runtime_sha: str
    page_records: Tuple[RetrievalPageRecord, ...]
    page_chain_sha256: str
    total_items: int
    total_requests: int
    status: str
    error_message: Optional[str]
    created_at_utc: str
    manifest_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.run_id or not isinstance(self.run_id, str):
            raise DataContractError("RUN_MANIFEST_EMPTY_RUN_ID.")
        if not self.authority_id or not isinstance(self.authority_id, str):
            raise DataContractError("RUN_MANIFEST_EMPTY_AUTHORITY_ID.")
        if not self.session or not isinstance(self.session, str):
            raise DataContractError("RUN_MANIFEST_EMPTY_SESSION.")
        if not self.capability or not isinstance(self.capability, str):
            raise DataContractError("RUN_MANIFEST_EMPTY_CAPABILITY.")
        if not self.symbol or not isinstance(self.symbol, str):
            raise DataContractError("RUN_MANIFEST_EMPTY_SYMBOL.")
        if not isinstance(self.runtime_sha, str) or not _HEX40_PATTERN.match(self.runtime_sha):
            raise DataContractError(
                f"RUN_MANIFEST_INVALID_RUNTIME_SHA: runtime_sha must be 40-char git commit SHA, got {self.runtime_sha}."
            )
        if self.page_records:
            expected_chain = ordered_page_chain_digest([p.raw_bytes_sha256 for p in self.page_records])
            if self.page_chain_sha256 != expected_chain:
                raise DataContractError(
                    f"RUN_MANIFEST_CHAIN_DIGEST_MISMATCH: declared {self.page_chain_sha256} != expected {expected_chain}."
                )
            expected_items = sum(p.item_count for p in self.page_records)
            if self.total_items != expected_items:
                raise DataContractError(
                    f"RUN_MANIFEST_ITEM_COUNT_MISMATCH: declared {self.total_items} != expected {expected_items}."
                )
        else:
            if self.status == "COMPLETED":
                raise DataContractError("RUN_MANIFEST_COMPLETED_WITHOUT_PAGES.")
        if self.total_requests < len(self.page_records):
            raise DataContractError(
                f"RUN_MANIFEST_REQUEST_COUNT_INVALID: total_requests ({self.total_requests}) < pages ({len(self.page_records)})."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "run_id": self.run_id,
            "authority_id": self.authority_id,
            "session": self.session,
            "capability": self.capability,
            "symbol": self.symbol,
            "runtime_sha": self.runtime_sha,
            "page_records": [p.to_dict() for p in self.page_records],
            "page_chain_sha256": self.page_chain_sha256,
            "total_items": self.total_items,
            "total_requests": self.total_requests,
            "status": self.status,
            "error_message": self.error_message,
            "created_at_utc": self.created_at_utc,
        }

    def manifest_sha256(self) -> str:
        """Calculate canonical SHA-256 digest of this manifest."""
        return canonical_manifest_sha256(self.to_dict())

    def write_immutable(self, target_file: Path) -> str:
        """Persist this manifest immutably to target_file."""
        return write_immutable_json(target_file, self.to_dict())
