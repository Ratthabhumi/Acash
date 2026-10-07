"""Immutable create-once artifact writers for the Evidence Plane."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from acash.core.domain.exceptions import DataContractError
from acash.evidence.digest import content_sha256


def write_immutable_bytes(target_file: Path, content: bytes) -> str:
    """Write raw bytes to target_file exactly once. Fail closed if target already exists.

    Uses exclusive file creation ('xb'). Returns SHA-256 hex digest of the content.
    """
    if not isinstance(content, (bytes, bytearray)):
        raise DataContractError(
            f"EVIDENCE_WRITE_INVALID_CONTENT: expected bytes or bytearray, got {type(content).__name__}."
        )

    if not isinstance(target_file, Path):
        target_file = Path(target_file)

    if not target_file.is_absolute():
        raise DataContractError(
            f"EVIDENCE_WRITE_TARGET_NOT_ABSOLUTE: target_file must be an absolute path, got {target_file}."
        )

    if target_file.exists():
        raise DataContractError(
            f"EVIDENCE_FILE_EXISTS_IMMUTABLE: target file {target_file} already exists. Overwriting evidence is strictly forbidden."
        )

    target_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(target_file, "xb") as f:
            f.write(content)
    except FileExistsError as exc:
        raise DataContractError(
            f"EVIDENCE_FILE_EXISTS_IMMUTABLE: target file {target_file} already exists (concurrent collision)."
        ) from exc
    except OSError as exc:
        raise DataContractError(
            f"EVIDENCE_WRITE_IO_ERROR: failed to write {target_file}: {exc}."
        ) from exc

    return content_sha256(content)


def write_immutable_json(target_file: Path, document: Mapping[str, Any]) -> str:
    """Write mapping to target_file as UTF-8 formatted JSON exactly once.

    Fails closed if target_file exists or document cannot be serialized.
    Returns SHA-256 hex digest of the written JSON bytes.
    """
    if not isinstance(document, Mapping):
        raise DataContractError(
            f"EVIDENCE_WRITE_INVALID_DOCUMENT: expected Mapping, got {type(document).__name__}."
        )

    try:
        payload = json.dumps(
            document,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DataContractError(
            f"EVIDENCE_WRITE_JSON_SERIALIZATION_FAILED: {exc}."
        ) from exc

    return write_immutable_bytes(target_file, payload)
