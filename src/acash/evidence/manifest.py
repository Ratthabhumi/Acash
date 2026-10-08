"""Canonical manifest models for the Retrieval Evidence Plane (V1.1 Provider/Consumer Neutral)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.evidence.digest import (
    canonical_manifest_sha256,
    ordered_page_chain_digest,
)
from acash.evidence.writer import write_immutable_json

_HEX40_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")

VALID_RETRIEVAL_STATUSES = frozenset(
    {
        "RETRIEVED",
        "PARTIAL",
        "ENTITLEMENT_DENIED",
        "AUTHENTICATION_FAILED",
        "HTTP_FAILED",
        "MALFORMED_RESPONSE",
    }
)


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
        if (
            not isinstance(self.page_index, int)
            or isinstance(self.page_index, bool)
            or self.page_index < 0
        ):
            raise DataContractError(
                f"PAGE_RECORD_INVALID_INDEX: page_index must be >= 0 int, got {self.page_index}."
            )
        if (
            not isinstance(self.item_count, int)
            or isinstance(self.item_count, bool)
            or self.item_count < 0
        ):
            raise DataContractError(
                f"PAGE_RECORD_INVALID_COUNT: item_count must be >= 0 int, got {self.item_count}."
            )
        if not isinstance(self.raw_bytes_sha256, str) or not _HEX64_PATTERN.match(
            self.raw_bytes_sha256
        ):
            raise DataContractError(
                f"PAGE_RECORD_INVALID_DIGEST: raw_bytes_sha256 must be 64-char hex SHA-256, got {self.raw_bytes_sha256}."
            )
        if not self.page_file or "/" in self.page_file or "\\" in self.page_file:
            raise DataContractError(
                f"PAGE_RECORD_INVALID_FILENAME: page_file must be a relative basename, got {self.page_file}."
            )
        try:
            ts = datetime.fromisoformat(self.retrieved_at_utc)
            if ts.tzinfo is None:
                raise DataContractError(
                    f"PAGE_RECORD_INVALID_TIMESTAMP: retrieved_at_utc must be timezone-aware, got {self.retrieved_at_utc}."
                )
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
        if not isinstance(data, Mapping):
            raise DataContractError(
                f"PAGE_RECORD_NOT_MAPPING: expected mapping, got {type(data).__name__}."
            )
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
    """Canonical run manifest summarizing an entire retrieval invocation.

    Evidence Plane V1.1: Provider- and consumer-neutral schema.
    Domain-specific scope and identifiers live in subject_metadata.
    """

    run_id: str
    consumer_id: str
    operation: str
    subject_metadata: Mapping[str, Any]
    runtime_sha: str
    page_records: Tuple[RetrievalPageRecord, ...]
    page_chain_sha256: str
    item_count: int
    operation_count: int
    status: str
    created_at_utc: str
    schema_version: str = "1.1"
    authority_ref: Optional[str] = None
    authority_sha256: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.run_id or not isinstance(self.run_id, str):
            raise DataContractError("RUN_MANIFEST_EMPTY_RUN_ID.")
        if not self.consumer_id or not isinstance(self.consumer_id, str):
            raise DataContractError("RUN_MANIFEST_EMPTY_CONSUMER_ID.")
        if not self.operation or not isinstance(self.operation, str):
            raise DataContractError("RUN_MANIFEST_EMPTY_OPERATION.")
        if not isinstance(self.subject_metadata, Mapping):
            raise DataContractError("RUN_MANIFEST_INVALID_SUBJECT_METADATA: must be a mapping.")
        if not isinstance(self.runtime_sha, str) or not _HEX40_PATTERN.match(self.runtime_sha):
            raise DataContractError(
                f"RUN_MANIFEST_INVALID_RUNTIME_SHA: runtime_sha must be 40-char git commit SHA, got {self.runtime_sha}."
            )
        if self.authority_sha256 is not None:
            if not isinstance(self.authority_sha256, str) or not _HEX64_PATTERN.match(
                self.authority_sha256
            ):
                raise DataContractError(
                    f"RUN_MANIFEST_INVALID_AUTHORITY_SHA: authority_sha256 must be 64-char hex SHA-256, got {self.authority_sha256}."
                )
        if self.status not in VALID_RETRIEVAL_STATUSES:
            raise DataContractError(
                f"RUN_MANIFEST_INVALID_STATUS: '{self.status}' not in {sorted(VALID_RETRIEVAL_STATUSES)}."
            )
        try:
            ts = datetime.fromisoformat(self.created_at_utc)
            if ts.tzinfo is None:
                raise DataContractError("RUN_MANIFEST_NAIVE_TIMESTAMP: created_at_utc must be timezone-aware.")
        except (ValueError, TypeError) as exc:
            raise DataContractError(
                f"RUN_MANIFEST_INVALID_TIMESTAMP: created_at_utc must be ISO-8601, got {self.created_at_utc}."
            ) from exc

        if (
            not isinstance(self.operation_count, int)
            or isinstance(self.operation_count, bool)
            or self.operation_count < 0
        ):
            raise DataContractError(
                f"RUN_MANIFEST_OPERATION_COUNT_INVALID: operation_count must be >= 0 int, got {self.operation_count}."
            )

        if self.page_records:
            expected_chain = ordered_page_chain_digest(self.page_records)
            if self.page_chain_sha256 != expected_chain:
                raise DataContractError(
                    f"RUN_MANIFEST_CHAIN_DIGEST_MISMATCH: declared {self.page_chain_sha256} != expected {expected_chain}."
                )
            expected_items = sum(p.item_count for p in self.page_records)
            if self.item_count != expected_items:
                raise DataContractError(
                    f"RUN_MANIFEST_ITEM_COUNT_MISMATCH: declared {self.item_count} != expected {expected_items}."
                )
            if self.operation_count < len(self.page_records):
                raise DataContractError(
                    f"RUN_MANIFEST_OPERATION_COUNT_INVALID: operation_count ({self.operation_count}) < pages ({len(self.page_records)})."
                )
        else:
            if self.status == "RETRIEVED":
                raise DataContractError("RUN_MANIFEST_RETRIEVED_WITHOUT_PAGES.")
            if self.item_count != 0:
                raise DataContractError(
                    f"RUN_MANIFEST_ITEM_COUNT_NONZERO_EMPTY_PAGES: got {self.item_count}."
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "consumer_id": self.consumer_id,
            "operation": self.operation,
            "subject_metadata": dict(self.subject_metadata),
            "runtime_sha": self.runtime_sha,
            "authority_ref": self.authority_ref,
            "authority_sha256": self.authority_sha256,
            "page_records": [p.to_dict() for p in self.page_records],
            "page_chain_sha256": self.page_chain_sha256,
            "item_count": self.item_count,
            "operation_count": self.operation_count,
            "status": self.status,
            "error_message": self.error_message,
            "created_at_utc": self.created_at_utc,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RetrievalRunManifest":
        if not isinstance(data, Mapping):
            raise DataContractError(
                f"RUN_MANIFEST_NOT_MAPPING: expected mapping, got {type(data).__name__}."
            )
        page_records = tuple(
            RetrievalPageRecord.from_dict(p) for p in data.get("page_records", [])
        )
        return cls(
            schema_version=str(data.get("schema_version", "1.1")),
            run_id=str(data["run_id"]),
            consumer_id=str(data["consumer_id"]),
            operation=str(data["operation"]),
            subject_metadata=dict(data.get("subject_metadata", {})),
            runtime_sha=str(data["runtime_sha"]),
            authority_ref=data.get("authority_ref"),
            authority_sha256=data.get("authority_sha256"),
            page_records=page_records,
            page_chain_sha256=str(data["page_chain_sha256"]),
            item_count=int(data["item_count"]),
            operation_count=int(data.get("operation_count", len(page_records))),
            status=str(data["status"]),
            error_message=data.get("error_message"),
            created_at_utc=str(data["created_at_utc"]),
        )

    def manifest_sha256(self) -> str:
        """Calculate canonical SHA-256 digest of this manifest."""
        return canonical_manifest_sha256(self.to_dict())

    def write_immutable(self, target_file: Path) -> str:
        """Persist this manifest immutably to target_file."""
        return write_immutable_json(target_file, self.to_dict())
