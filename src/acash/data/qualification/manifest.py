"""Deterministic SHA-256 hashing and provenance manifest generator for historical SIP retrieval."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import subprocess
from typing import Any, Dict, List, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.qualification.models import (
    HistoricalSipBar,
    SipPageMetadata,
    SipProvenanceManifest,
    SourceQualificationStatus,
    VwapAuthorityStatus,
)


def compute_page_sha256(raw_bytes: bytes) -> str:
    """Compute standard SHA-256 hex digest of a single page's raw payload bytes."""
    return hashlib.sha256(raw_bytes).hexdigest()


def compute_framed_composite_sha256(pages_raw_bytes: Sequence[bytes]) -> str:
    """Compute length-prefixed composite SHA-256 over an ordered sequence of page payloads.

    Framing rule:
        For each page payload b_i, encode an 8-byte big-endian unsigned integer of len(b_i)
        followed by b_i itself: struct.pack('>Q', len(b_i)) + b_i.

    This eliminates concatenation ambiguity between JSON payloads and guarantees that
    page boundary shifts or page reordering produce distinct cryptographic digests.
    """
    hasher = hashlib.sha256()
    for page_bytes in pages_raw_bytes:
        hasher.update(struct.pack(">Q", len(page_bytes)))
        hasher.update(page_bytes)
    return hasher.hexdigest()


def compute_canonical_bars_sha256(bars: Sequence[HistoricalSipBar]) -> str:
    """Compute deterministic SHA-256 over normalized canonical bar representations."""
    hasher = hashlib.sha256()
    for b in bars:
        vwap_str = f"{b.provider_vwap}" if b.provider_vwap is not None else "NONE"
        tc_str = f"{b.trade_count}" if b.trade_count is not None else "NONE"
        record_line = (
            f"{b.timestamp_utc.isoformat()}|{b.open}|{b.high}|{b.low}|{b.close}|"
            f"{b.volume}|{tc_str}|{vwap_str}\n"
        )
        hasher.update(record_line.encode("utf-8"))
    return hasher.hexdigest()


def get_git_info(cwd: Optional[Path] = None) -> Tuple[str, bool]:
    """Retrieve current git commit SHA and dirty-state flag safely."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        status_out = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        is_dirty = bool(status_out)
        return commit, is_dirty
    except Exception:
        return "UNKNOWN", False


def build_sip_provenance_manifest(
    *,
    manifest_id: str,
    symbol: str,
    feed_requested: str,
    feed_response_provenance: str,
    timeframe: str,
    adjustment: str,
    requested_start_utc: str,
    requested_end_utc: str,
    retrieval_timestamp_utc: str,
    pages_metadata: Sequence[SipPageMetadata],
    pages_raw_bytes: Sequence[bytes],
    bars: Sequence[HistoricalSipBar],
    source_qualification_status: SourceQualificationStatus,
    vwap_authority_status: VwapAuthorityStatus,
    warnings: Sequence[str] = (),
    failure_reason: Optional[str] = None,
    git_commit_sha: Optional[str] = None,
    git_dirty: Optional[bool] = None,
) -> SipProvenanceManifest:
    """Construct a frozen SipProvenanceManifest with complete cryptographic provenance."""
    if len(pages_metadata) != len(pages_raw_bytes):
        raise DataContractError(
            f"pages_metadata count ({len(pages_metadata)}) must equal pages_raw_bytes count ({len(pages_raw_bytes)})."
        )

    composite_raw_sha256 = compute_framed_composite_sha256(pages_raw_bytes)
    canonical_bars_sha256 = compute_canonical_bars_sha256(bars)

    if git_commit_sha is None or git_dirty is None:
        detected_commit, detected_dirty = get_git_info()
        commit_sha = git_commit_sha or detected_commit
        dirty = git_dirty if git_dirty is not None else detected_dirty
    else:
        commit_sha = git_commit_sha
        dirty = git_dirty

    first_bar_ts = bars[0].timestamp_utc.isoformat() if bars else None
    last_bar_ts = bars[-1].timestamp_utc.isoformat() if bars else None

    return SipProvenanceManifest(
        manifest_id=manifest_id,
        provider="alpaca",
        endpoint="https://data.alpaca.markets/v2/stocks/{symbol}/bars",
        symbol=symbol,
        feed_requested=feed_requested,
        feed_response_provenance=feed_response_provenance,
        timeframe=timeframe,
        adjustment=adjustment,
        requested_start_utc=requested_start_utc,
        requested_end_utc=requested_end_utc,
        retrieval_timestamp_utc=retrieval_timestamp_utc,
        page_count=len(pages_metadata),
        pages=list(pages_metadata),
        composite_raw_payload_sha256=composite_raw_sha256,
        canonical_bars_sha256=canonical_bars_sha256,
        record_count=len(bars),
        first_bar_timestamp_utc=first_bar_ts,
        last_bar_timestamp_utc=last_bar_ts,
        git_commit_sha=commit_sha,
        git_dirty=dirty,
        schema_version="1.0.0",
        source_qualification_status=source_qualification_status,
        vwap_authority_status=vwap_authority_status,
        warnings=list(warnings),
        failure_reason=failure_reason,
    )


def serialize_manifest_to_json(manifest: SipProvenanceManifest) -> str:
    """Serialize manifest deterministically to JSON using CanonicalConfigSerializer."""
    return CanonicalConfigSerializer.to_canonical_json(manifest.model_dump())
