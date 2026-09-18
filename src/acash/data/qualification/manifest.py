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
    OFFICIAL_CONTRACT_FEED,
    OFFICIAL_CONTRACT_PROVIDER,
    OFFICIAL_CONTRACT_RECORDED_AT_UTC,
    OFFICIAL_CONTRACT_REFERENCES,
    OFFICIAL_CONTRACT_SEMANTICS,
    ProvenanceBasis,
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
    provenance_basis: ProvenanceBasis = ProvenanceBasis.UNVERIFIED,
    timeframe: str,
    adjustment: str,
    asof: Optional[str] = None,
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
    source_contract_provider: str = OFFICIAL_CONTRACT_PROVIDER,
    source_contract_feed: str = OFFICIAL_CONTRACT_FEED,
    source_contract_references: Sequence[str] = OFFICIAL_CONTRACT_REFERENCES,
    source_contract_recorded_at_utc: str = OFFICIAL_CONTRACT_RECORDED_AT_UTC,
    source_contract_semantics: str = OFFICIAL_CONTRACT_SEMANTICS,
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
        provenance_basis=provenance_basis,
        timeframe=timeframe,
        adjustment=adjustment,
        asof=asof,
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
        source_contract_provider=source_contract_provider,
        source_contract_feed=source_contract_feed,
        source_contract_references=list(source_contract_references),
        source_contract_recorded_at_utc=source_contract_recorded_at_utc,
        source_contract_semantics=source_contract_semantics,
        warnings=list(warnings),
        failure_reason=failure_reason,
    )


def serialize_manifest_to_json(manifest: SipProvenanceManifest) -> str:
    """Serialize manifest deterministically to formatted JSON."""
    return json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True)


def save_evidence_package(
    *,
    evidence_dir: Path,
    manifest: SipProvenanceManifest,
    pages_raw_bytes: Sequence[bytes],
) -> Path:
    """Persist exact raw response page bytes and manifest.json using atomic writes.

    Layout:
      evidence_dir/
        page-0001.raw.json
        page-0002.raw.json
        ...
        manifest.json

    Requirements:
    - Writes exact raw bytes without parsing or re-serializing.
    - Uses atomic write pattern (.tmp rename).
    - Verifies raw byte length and raw SHA-256 against manifest page metadata.

    Returns:
      Path to saved manifest.json.
    """
    evidence_dir.mkdir(parents=True, exist_ok=True)

    if len(pages_raw_bytes) != len(manifest.pages):
        raise DataContractError(
            f"pages_raw_bytes count ({len(pages_raw_bytes)}) must equal manifest.pages count ({len(manifest.pages)})."
        )

    for i, raw_bytes in enumerate(pages_raw_bytes, start=1):
        filename = f"page-{i:04d}.raw.json"
        raw_path = evidence_dir / filename
        tmp_path = evidence_dir / f"{filename}.tmp"

        page_meta = manifest.pages[i - 1]
        calc_sha = compute_page_sha256(raw_bytes)
        if calc_sha != page_meta.raw_sha256:
            raise DataContractError(
                f"Page {i} raw byte SHA-256 ({calc_sha}) does not match manifest ({page_meta.raw_sha256})."
            )
        if len(raw_bytes) != page_meta.byte_length:
            raise DataContractError(
                f"Page {i} raw byte length ({len(raw_bytes)}) does not match manifest ({page_meta.byte_length})."
            )

        tmp_path.write_bytes(raw_bytes)
        tmp_path.replace(raw_path)

    manifest_path = evidence_dir / "manifest.json"
    manifest_tmp = evidence_dir / "manifest.json.tmp"
    manifest_json = serialize_manifest_to_json(manifest)
    manifest_tmp.write_text(manifest_json, encoding="utf-8")
    manifest_tmp.replace(manifest_path)

    return manifest_path


def verify_persisted_evidence_package(evidence_dir: Path) -> Tuple[bool, List[str]]:
    """Verify persisted raw artifacts against manifest.json.

    Reads back persisted raw page bytes, recomputes SHA-256 digests and length-prefixed
    framed composite SHA-256, and confirms equality with manifest values.

    Returns:
        (is_valid, list_of_error_messages)
    """
    manifest_path = evidence_dir / "manifest.json"
    if not manifest_path.exists():
        return False, [f"Manifest file not found: {manifest_path}"]

    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest = SipProvenanceManifest.model_validate_json(manifest_text)
    except Exception as e:
        return False, [f"Failed to read or parse manifest.json: {e}"]

    errors: List[str] = []
    reloaded_raw_bytes: List[bytes] = []

    for page_meta in manifest.pages:
        page_file = evidence_dir / page_meta.relative_artifact_path
        if not page_file.exists():
            errors.append(f"Missing raw page file: {page_file}")
            continue

        raw_bytes = page_file.read_bytes()
        if len(raw_bytes) != page_meta.byte_length:
            errors.append(
                f"Page {page_meta.page_index} length mismatch: disk {len(raw_bytes)} != manifest {page_meta.byte_length}"
            )
        calc_sha = compute_page_sha256(raw_bytes)
        if calc_sha != page_meta.raw_sha256:
            errors.append(
                f"Page {page_meta.page_index} SHA-256 mismatch: disk {calc_sha} != manifest {page_meta.raw_sha256}"
            )
        reloaded_raw_bytes.append(raw_bytes)

    if not errors and len(reloaded_raw_bytes) == len(manifest.pages):
        calc_composite_sha = compute_framed_composite_sha256(reloaded_raw_bytes)
        if calc_composite_sha != manifest.composite_raw_payload_sha256:
            errors.append(
                f"Composite framed SHA-256 mismatch: disk {calc_composite_sha} != manifest {manifest.composite_raw_payload_sha256}"
            )

    return (len(errors) == 0, errors)
