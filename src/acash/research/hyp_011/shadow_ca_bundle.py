"""CA evidence bundle contract (F19): raw-byte verification + source identity.

A 64-hex digest string alone proves nothing: anyone can invent one. A CA
evidence bundle binds a determination to PRESERVED RAW OFFICIAL BYTES plus
a verified sponsor/product identity. At dispatch the runner:

- reads the actual raw evidence bytes,
- recomputes SHA-256 over those bytes,
- compares against manifest AND determination source_sha256,
- validates sponsor/source/product identity (catches e.g. iShares product
  239707/IWB mislabeled as ACWI),
- recomputes no-event schedule digests from referenced raw schedule files.

No-event scope schedules are second evidence files inside the same bundle.
No network in this module. No broker access.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping
from urllib.parse import urlparse

from acash.core.domain.exceptions import DataContractError
from acash.research.hyp_011.shadow_ca import OFFICIAL_DOMAIN_FRAGMENTS, SPONSOR_BY_SYMBOL

CA_BUNDLE_SCHEMA_VERSION: int = 1
MANIFEST_FILENAME: str = "manifest.json"
EVIDENCE_SUBDIR: str = "evidence"

# Frozen official product identity per symbol (semantic identity, not URL).
# 239707 is IWB (iShares Russell 1000 ETF) — NEVER valid as ACWI evidence.
PRODUCT_IDENTITY_BY_SYMBOL: Dict[str, Dict[str, str]] = {
    "ACWI": {
        "product_id": "239600",
        "ticker": "ACWI",
        "cusip": "464288257",
        "sponsor": "BLACKROCK_ISHARES_OFFICIAL",
    },
    "AGG": {
        "product_id": "239458",
        "ticker": "AGG",
        "sponsor": "BLACKROCK_ISHARES_OFFICIAL",
    },
    "SPY": {
        "schedule": "SSGA_OFFICIAL_2026_DISTRIBUTIONS",
        "ticker": "SPY",
        "cusip": "78462F103",
        "sponsor": "STATE_STREET_SPDR_OFFICIAL",
    },
}

# Retrieval representation types (descriptive honesty, not a security tier).
# NORMALIZED_RETRIEVAL_REPRESENTATION: converted/normalized content (rendered
# Markdown, normalized text, re-serialized HTML) whose digest covers the
# PRESERVED bytes but which must NOT be described as byte-identical HTTP
# response bodies. RAW_HTTP_BODY: verbatim HTTP response bytes captured with
# response metadata. Both are digest-verified; the label prevents false
# byte-identity claims.
RETRIEVAL_REPRESENTATION_NORMALIZED: str = "NORMALIZED_RETRIEVAL_REPRESENTATION"
RETRIEVAL_REPRESENTATION_RAW_HTTP: str = "RAW_HTTP_BODY"
KNOWN_RETRIEVAL_REPRESENTATIONS = frozenset(
    {RETRIEVAL_REPRESENTATION_NORMALIZED, RETRIEVAL_REPRESENTATION_RAW_HTTP}
)

# Semantic identity markers that MUST be derivable from genuine preserved
# evidence bytes per symbol (F19). Ticker/product/CUSIP match case-sensitively
# (they are proper identifiers); sponsor display names match case-insensitively.
# Marker presence is necessary but not sufficient for full semantic parsing —
# see derive_evidence_identity_markers.
EVIDENCE_IDENTITY_MARKERS: Dict[str, Dict[str, List[str]]] = {
    "ACWI": {
        "ticker": ["ACWI"],
        "product_id": ["239600"],
        "cusip": ["464288257"],
    },
    "AGG": {
        "ticker": ["AGG"],
        "product_id": ["239458"],
    },
    "SPY": {
        "ticker": ["SPY"],
        "cusip": ["78462F103"],
        "sponsor": ["state street"],
    },
}


def _check_causality(retrieved_at_utc: str, processing_utc: datetime) -> None:
    try:
        retrieved = datetime.fromisoformat(retrieved_at_utc)
    except (ValueError, TypeError) as exc:
        raise DataContractError("CA_BUNDLE_RETRIEVED_MALFORMED.") from exc
    if retrieved.tzinfo is None:
        raise DataContractError("CA_BUNDLE_RETRIEVED_NAIVE.")
    if processing_utc.tzinfo is None:
        raise DataContractError("CA_PROCESSING_TS_MUST_BE_TIMEZONE_AWARE.")
    if retrieved.astimezone(timezone.utc) > processing_utc.astimezone(timezone.utc):
        raise DataContractError("CA_BUNDLE_FUTURE_RETRIEVAL.")


def _read_evidence_bytes(bundle_symbol_dir: Path, evidence_file: str) -> bytes:
    if not isinstance(evidence_file, str) or not evidence_file.strip():
        raise DataContractError("CA_BUNDLE_EVIDENCE_FILE_MISSING.")
    candidate = bundle_symbol_dir / EVIDENCE_SUBDIR / evidence_file.strip()
    try:
        resolved = candidate.resolve()
        base = (bundle_symbol_dir / EVIDENCE_SUBDIR).resolve()
    except OSError as exc:
        raise DataContractError(f"CA_BUNDLE_EVIDENCE_UNREADABLE: {exc}.") from exc
    if base not in resolved.parents:
        raise DataContractError("CA_BUNDLE_EVIDENCE_ESCAPES_BUNDLE.")
    if not resolved.is_file():
        raise DataContractError(
            f"CA_BUNDLE_EVIDENCE_ABSENT: {evidence_file.strip()}."
        )
    raw = resolved.read_bytes()
    if not raw:
        raise DataContractError("CA_BUNDLE_EVIDENCE_EMPTY.")
    return raw


def derive_evidence_identity_markers(raw: bytes, symbol: str) -> Dict[str, str]:
    """Derive semantic identity markers from preserved evidence bytes (F19).

    Parses the evidence representation itself for ticker / product / CUSIP /
    sponsor markers instead of trusting manifest claims. Every required marker
    for the symbol must be present or verification fails closed. Returns the
    canonical proven values on success.

    Boundary honesty: marker presence proves the bytes discuss the claimed
    product; it is not a full semantic parse of arbitrary page structures.
    """
    rules = EVIDENCE_IDENTITY_MARKERS.get(symbol)
    if not rules:
        raise DataContractError(f"CA_BUNDLE_UNKNOWN_SYMBOL: {symbol}.")
    if not raw:
        raise DataContractError(
            f"CA_BUNDLE_EVIDENCE_IDENTITY_UNPROVEN: {symbol} empty bytes."
        )
    try:
        text = raw.decode("utf-8", errors="strict")
    except (UnicodeDecodeError, ValueError) as exc:
        raise DataContractError(
            f"CA_BUNDLE_EVIDENCE_IDENTITY_UNPROVEN: {symbol} non-UTF-8 bytes."
        ) from exc
    lowered = text.lower()
    proven: Dict[str, str] = {}
    frozen = PRODUCT_IDENTITY_BY_SYMBOL.get(symbol, {})
    for field, markers in rules.items():
        hit = False
        for marker in markers:
            if field == "sponsor":
                if marker.lower() in lowered:
                    hit = True
                    break
            elif marker in text:
                hit = True
                break
        if not hit:
            raise DataContractError(
                f"CA_BUNDLE_EVIDENCE_IDENTITY_UNPROVEN: {symbol} {field} "
                f"marker absent from preserved evidence bytes."
            )
        proven[field] = str(frozen.get(field, markers[0]))
    return proven


def verify_evidence_bundle(
    bundle_symbol_dir: Path,
    symbol: str,
    session: date,
    processing_utc: datetime,
) -> Dict[str, Any]:
    """Verify one symbol's CA evidence bundle against raw preserved bytes."""
    expected_sponsor = SPONSOR_BY_SYMBOL.get(symbol)
    if not expected_sponsor:
        raise DataContractError(f"CA_BUNDLE_UNKNOWN_SYMBOL: {symbol}.")
    manifest_path = bundle_symbol_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise DataContractError(
            f"CA_BUNDLE_MANIFEST_ABSENT: {symbol} {session.isoformat()}."
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DataContractError(f"CA_BUNDLE_MANIFEST_CORRUPT: {exc}.") from exc
    if not isinstance(manifest, dict):
        raise DataContractError("CA_BUNDLE_MANIFEST_MALFORMED.")
    if manifest.get("schema_version") != CA_BUNDLE_SCHEMA_VERSION:
        raise DataContractError("CA_BUNDLE_SCHEMA_VERSION.")
    if manifest.get("symbol") != symbol:
        raise DataContractError(f"CA_BUNDLE_SYMBOL_MISMATCH: {symbol}.")
    if manifest.get("target_session") != session.isoformat():
        raise DataContractError(f"CA_BUNDLE_SESSION_MISMATCH: {symbol}.")
    if manifest.get("authority_source") != expected_sponsor:
        raise DataContractError(f"CA_BUNDLE_SPONSOR_MISMATCH: {symbol}.")
    official_url = manifest.get("official_url")
    if not isinstance(official_url, str) or not official_url.strip():
        raise DataContractError(f"CA_BUNDLE_URL_MISSING: {symbol}.")
    host = urlparse(official_url.strip()).netloc.lower()
    fragment = OFFICIAL_DOMAIN_FRAGMENTS.get(expected_sponsor, "")
    if not fragment or fragment not in host:
        raise DataContractError(
            f"CA_BUNDLE_DOMAIN_MISMATCH: {symbol} {host!r} lacks {fragment!r}."
        )
    expected_identity = PRODUCT_IDENTITY_BY_SYMBOL.get(symbol, {})
    declared_identity = manifest.get("product_identity")
    if not isinstance(declared_identity, dict) or {
        str(k): str(v) for k, v in declared_identity.items()
    } != expected_identity:
        raise DataContractError(
            f"CA_BUNDLE_PRODUCT_IDENTITY_MISMATCH: {symbol} {declared_identity!r} "
            f"!= frozen {expected_identity!r}."
        )
    scope_type = manifest.get("scope_type")
    if scope_type not in ("EVENT_EVIDENCE", "NO_EVENT_SCOPE"):
        raise DataContractError(f"CA_BUNDLE_SCOPE_TYPE_INVALID: {symbol}.")
    representation = manifest.get("retrieval_representation")
    if representation not in KNOWN_RETRIEVAL_REPRESENTATIONS:
        raise DataContractError(
            f"CA_BUNDLE_REPRESENTATION_UNKNOWN: {symbol} retrieval "
            f"representation must be one of "
            f"{sorted(KNOWN_RETRIEVAL_REPRESENTATIONS)}."
        )
    raw = _read_evidence_bytes(bundle_symbol_dir, manifest.get("evidence_file", ""))
    recomputed = hashlib.sha256(raw).hexdigest()
    declared_sha = manifest.get("evidence_sha256")
    if (
        not isinstance(declared_sha, str)
        or declared_sha.lower() != recomputed
    ):
        raise DataContractError(
            f"CA_BUNDLE_DIGEST_MISMATCH: {symbol} preserved bytes do not match "
            "the manifest digest (invented digests rejected)."
        )
    # F19: semantic identity MUST be derived from the preserved bytes, never
    # trusted from manifest claims alone. IWB/239707 bytes behind an
    # ACWI/239600 manifest fail here even when every digest matches, because
    # the ACWI markers are absent from IWB content. The manifest claim itself
    # is separately pinned to the frozen identity above.
    derived_identity = derive_evidence_identity_markers(raw, symbol)
    schedule = manifest.get("schedule_evidence")
    if scope_type == "NO_EVENT_SCOPE":
        if not isinstance(schedule, dict):
            raise DataContractError(
                f"CA_BUNDLE_SCHEDULE_REQUIRED: {symbol} no-event scope needs "
                "recomputed schedule evidence."
            )
        sched_raw = _read_evidence_bytes(
            bundle_symbol_dir, schedule.get("file", "")
        )
        sched_recomputed = hashlib.sha256(sched_raw).hexdigest()
        if (
            not isinstance(schedule.get("sha256"), str)
            or schedule["sha256"].lower() != sched_recomputed
        ):
            raise DataContractError(
                f"CA_BUNDLE_SCHEDULE_DIGEST_MISMATCH: {symbol}."
            )
    _check_causality(str(manifest.get("retrieved_at_utc") or ""), processing_utc)
    verified = dict(manifest)
    verified["evidence_sha256"] = recomputed
    verified["derived_evidence_identity"] = derived_identity
    return verified


def verify_determination_evidence_binding(
    determination_doc: Mapping[str, Any],
    verified_manifest: Mapping[str, Any],
    symbol: str,
) -> None:
    """Bind a determination to its verified bundle (no invented digests)."""
    if not isinstance(determination_doc, Mapping):
        raise DataContractError("CA_DETERMINATION_NOT_A_MAPPING.")
    det_sha = determination_doc.get("source_sha256")
    if (
        not isinstance(det_sha, str)
        or det_sha.lower() != str(verified_manifest.get("evidence_sha256")).lower()
    ):
        raise DataContractError(
            f"CA_DETERMINATION_DIGEST_NOT_BOUND: {symbol} source_sha256 is not "
            "the verified bundle evidence digest."
        )
    det_ref = determination_doc.get("evidence_ref")
    if (
        not isinstance(det_ref, str)
        or det_ref.strip() != str(verified_manifest.get("evidence_file")).strip()
    ):
        raise DataContractError(
            f"CA_DETERMINATION_REF_NOT_BOUND: {symbol} evidence_ref does not "
            "name the verified bundle evidence file."
        )
