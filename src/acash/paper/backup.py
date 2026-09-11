"""ACASH Paper Trading — Backup Manifest & Packaging Engine (E3.6 / WS10).

DESIGN REFERENCE: E3.6-DESIGN.md §7 (D7.2/D7.3), §10 (D10.1–D10.3), §18 (D18.1–D18.2).
BACKUP CONTRACT: E3.6-WS10-BACKUP-RESTORE-CONTRACT.md.

This module provides the canonical repository-side backup packaging and manifest
generation engine for ACASH persistent state:

1. Computes SHA-256 digests for all individual state files under the persistent root.
2. Formats a canonical, machine-readable AcashBackupManifest.
3. Packages persistent state into deterministic tar.gz archives.
4. Preserves O3 retention semantics (observation window policy + 7-day evidence retention).
5. Does NOT invent runtime values — git commits, timestamps, and hashes are collected
   from the real environment or explicitly supplied.

GOVERNANCE (E3.6):
==================
- EXECUTION/PAPER INFRASTRUCTURE ONLY.
- INFRASTRUCTURE READY != STRATEGY QUALIFIED != PAPER AUTHORIZED != LIVE AUTHORIZED.
- Canonical capital = $0.
- Creating or storing a backup never constitutes or implies Paper or Live authorization.
"""

from __future__ import annotations

import hashlib
import json
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer

CANONICAL_STORAGE_ROOT = "/data/docker/acash"
BACKUP_SCHEMA_VERSION = "1.0.0"
BACKUP_FORMAT_VERSION = "tar.gz+manifest-v1"
EVIDENCE_RETENTION_MARGIN_DAYS = 7


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 digest of a file in 64KB blocks."""
    if not file_path.is_file():
        raise DataContractError(f"compute_file_sha256: target {file_path} is not a regular file")
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class BackupFileInfo(BaseModel):
    """Metadata and SHA-256 for a single state file included in the backup."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Relative path within the storage root, using forward slashes.")
    size_bytes: int = Field(description="File size in bytes.")
    sha256: str = Field(description="SHA-256 hex digest of file content.")


class AcashBackupManifest(BaseModel):
    """Canonical sealed backup manifest (E3.6 WS10)."""

    model_config = ConfigDict(extra="forbid")

    backup_id: str = Field(description="Unique backup identifier, e.g. acash-backup-YYYYMMDDTHHMMSSZ.")
    created_at_utc: datetime = Field(description="UTC timestamp of backup creation.")
    storage_root: str = Field(
        default=CANONICAL_STORAGE_ROOT,
        description="Canonical persistent storage root on host.",
    )
    file_count: int = Field(description="Total number of state files included.")
    total_bytes: int = Field(description="Total uncompressed bytes across all files.")
    included_paths: List[str] = Field(
        default_factory=list,
        description="Sorted list of relative paths included in the backup.",
    )
    sha256_checksums: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping from relative path to SHA-256 checksum.",
    )
    files: List[BackupFileInfo] = Field(
        default_factory=list,
        description="Detailed file records.",
    )
    git_commit: str = Field(description="ACASH repository git commit.")
    config_hash: Optional[str] = Field(default=None, description="Configuration hash where available.")
    schema_version: str = Field(default=BACKUP_SCHEMA_VERSION, description="Backup manifest schema version.")
    backup_format_version: str = Field(
        default=BACKUP_FORMAT_VERSION,
        description="Packaging format version.",
    )
    archive_sha256: Optional[str] = Field(
        default=None,
        description="SHA-256 hex digest of the resulting tar.gz archive.",
    )
    evidence_retention_margin_days: int = Field(
        default=EVIDENCE_RETENTION_MARGIN_DAYS,
        description="Human Decision O3: 7-day margin beyond observation window duration.",
    )
    governance_marker: str = Field(
        default="E3.6_WS10_EXECUTION_INFRASTRUCTURE_ONLY",
        description="Explicit non-authorization governance label.",
    )


def collect_storage_files(storage_root: Path) -> List[Path]:
    """Collect all regular state files under the storage root, sorted deterministically."""
    if not storage_root.exists() or not storage_root.is_dir():
        raise DataContractError(f"collect_storage_files: root {storage_root} does not exist or is not a directory")

    collected: List[Path] = []
    for p in storage_root.rglob("*"):
        if p.is_file():
            # Skip hidden files or transient locks if any
            if p.name.startswith(".") or p.suffix == ".lock":
                continue
            collected.append(p)
    collected.sort(key=lambda x: x.relative_to(storage_root).as_posix())
    return collected


def generate_backup_manifest(
    storage_root: Path,
    *,
    git_commit: str,
    config_hash: Optional[str] = None,
    backup_id: Optional[str] = None,
    created_at_utc: Optional[datetime] = None,
) -> AcashBackupManifest:
    """Inspect the storage root, compute checksums for all files, and build the manifest."""
    if not git_commit or git_commit == "unknown":
        raise DataContractError("generate_backup_manifest: git_commit must be known and non-empty (D1.4).")

    root = Path(storage_root)
    now = created_at_utc or datetime.now(timezone.utc)
    ts_str = now.strftime("%Y%m%dT%H%M%SZ")
    bid = backup_id or f"acash-backup-{ts_str}"

    state_files = collect_storage_files(root)
    file_records: List[BackupFileInfo] = []
    checksums: Dict[str, str] = {}
    included_paths: List[str] = []
    total_bytes = 0

    for file_path in state_files:
        rel_path = file_path.relative_to(root).as_posix()
        size = file_path.stat().st_size
        sha = compute_file_sha256(file_path)

        file_records.append(BackupFileInfo(path=rel_path, size_bytes=size, sha256=sha))
        checksums[rel_path] = sha
        included_paths.append(rel_path)
        total_bytes += size

    return AcashBackupManifest(
        backup_id=bid,
        created_at_utc=now,
        storage_root=CANONICAL_STORAGE_ROOT,
        file_count=len(file_records),
        total_bytes=total_bytes,
        included_paths=included_paths,
        sha256_checksums=checksums,
        files=file_records,
        git_commit=git_commit,
        config_hash=config_hash,
    )


def create_acash_backup_archive(
    storage_root: Path,
    output_dir: Path,
    *,
    git_commit: str,
    config_hash: Optional[str] = None,
    backup_id: Optional[str] = None,
) -> Tuple[Path, Path, AcashBackupManifest]:
    """Package the persistent storage root into a tar.gz archive and write its manifest.

    Returns:
        (archive_path, manifest_path, manifest_object)
    """
    root = Path(storage_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    manifest = generate_backup_manifest(
        root,
        git_commit=git_commit,
        config_hash=config_hash,
        backup_id=backup_id,
    )

    archive_path = out / f"{manifest.backup_id}.tar.gz"
    manifest_path = out / f"{manifest.backup_id}.manifest.json"
    sha_path = out / f"{manifest.backup_id}.sha256"

    # Create tar.gz deterministically
    with tarfile.open(archive_path, "w:gz") as tar:
        for rel_path in manifest.included_paths:
            full_path = root / rel_path
            # Normalize tar info
            tarinfo = tar.gettarinfo(full_path, arcname=rel_path)
            tarinfo.uid = 10001
            tarinfo.gid = 10001
            tarinfo.uname = "paper"
            tarinfo.gname = "paper"
            if full_path.is_file():
                with open(full_path, "rb") as f:
                    tar.addfile(tarinfo, f)

    # Compute archive SHA-256
    archive_sha = compute_file_sha256(archive_path)
    manifest = manifest.model_copy(update={"archive_sha256": archive_sha})

    # Write manifest JSON
    manifest_json = manifest.model_dump_json(indent=2) + "\n"
    manifest_path.write_text(manifest_json, encoding="utf-8")

    # Write SHA256 checksum file (standard format)
    sha_content = f"{archive_sha}  {archive_path.name}\n"
    sha_path.write_text(sha_content, encoding="utf-8")

    return archive_path, manifest_path, manifest
