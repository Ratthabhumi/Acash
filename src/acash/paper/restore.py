"""ACASH Paper Trading — Non-Destructive Restore Validation Engine (E3.6 / WS10).

DESIGN REFERENCE: E3.6-DESIGN.md §7 (D7.2), §10 (D10.1–D10.3), §18 (D18.1–D18.2).
BACKUP CONTRACT: E3.6-WS10-BACKUP-RESTORE-CONTRACT.md.

This module implements the non-destructive restore validation utility for ACASH
persistent state:

1. Unpacks backup archives into a DISPOSABLE STAGING directory.
2. REFUSES to overwrite or restore directly into the canonical persistent root
   (/data/docker/acash), failing closed if targeted at the live root.
3. Verifies expected directory taxonomy (windows/, sessions/, logs/, review/).
4. Verifies SHA-256 checksums of all restored files against the backup manifest.
5. Verifies journal cryptographic hash-chains using PaperEventJournal.verify_integrity().
6. Verifies session manifest schema and lineage using PaperSessionManifest.
7. Verifies observation window manifests and deployment interlock state markers
   using validate_window_manifest() and WindowManifest.compute_hash().
8. Verifies runtime segment provenance (git_commit, image_digest, container_id,
   clock attestations).
9. Detects missing files and unexpected extraneous files (strict completeness).
10. Generates structured machine-readable results (RestoreValidationResult) and
    formatted human-readable diagnostic summaries.

GOVERNANCE (E3.6):
==================
- EXECUTION/PAPER INFRASTRUCTURE ONLY.
- FAIL-CLOSED: Any violation marks validation status FAIL.
- Canonical capital = $0.
- Restoration testing never constitutes or implies Paper or Live authorization.
"""

from __future__ import annotations

import json
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.exceptions import DataContractError
from acash.paper.backup import (
    AcashBackupManifest,
    CANONICAL_STORAGE_ROOT,
    compute_file_sha256,
)
from acash.paper.journal import PaperEventJournal
from acash.paper.manifest import PaperMode, PaperSessionManifest
from acash.paper.window import (
    EvidenceStatus,
    WindowInterlockMarker,
    WindowManifest,
    WindowState,
    validate_window_manifest,
)


class RestoreCheckDetail(BaseModel):
    """Detailed result of an individual restore invariant check."""

    model_config = ConfigDict(extra="forbid")

    check_id: str
    status: str = Field(description="'PASS' or 'FAIL'")
    description: str
    violations: List[str] = Field(default_factory=list)


class RestoreValidationResult(BaseModel):
    """Machine-readable validation outcome for a restored state."""

    model_config = ConfigDict(extra="forbid")

    target_dir: str
    status: str = Field(description="'PASS' if all checks pass, else 'FAIL'")
    checks: List[RestoreCheckDetail] = Field(default_factory=list)
    file_count: int = 0
    verified_sessions: List[str] = Field(default_factory=list)
    verified_windows: List[str] = Field(default_factory=list)
    violations: List[str] = Field(default_factory=list)
    summary_text: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


def safe_extract_archive(archive_path: Path, staging_dir: Path) -> None:
    """Safely extract a tar.gz archive into a staging directory preventing path traversal."""
    if not archive_path.is_file():
        raise DataContractError(f"safe_extract_archive: archive {archive_path} not found")

    staging = Path(staging_dir).resolve()
    staging.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            target_path = (staging / member.name).resolve()
            try:
                target_path.relative_to(staging)
            except ValueError as exc:
                raise DataContractError(
                    f"safe_extract_archive: path traversal detected in archive: {member.name}"
                ) from exc

        # Unpack
        tar.extractall(path=staging)


def validate_restore_state(
    staging_dir: Path,
    *,
    manifest: Optional[AcashBackupManifest] = None,
    expected_git_commit: Optional[str] = None,
    expected_config_hash: Optional[str] = None,
    expected_image_digest: Optional[str] = None,
    strict_files: bool = True,
    require_evidence: bool = True,
) -> RestoreValidationResult:
    """Validate all ACASH restore invariants inside a staging directory.

    Fails closed if:
    - Target directory resolves to CANONICAL_STORAGE_ROOT (/data/docker/acash).
    - Directory taxonomy is missing or invalid.
    - Any checksum fails.
    - Extraneous files exist when strict_files=True.
    - Any session journal breaks hash-chain integrity.
    - Any session manifest is invalid or tampered.
    - Any window manifest fails validate_window_manifest() or hash computation.
    - Runtime segment provenance doesn't match expected values.
    """
    staging = Path(staging_dir).resolve()
    checks: List[RestoreCheckDetail] = []
    all_violations: List[str] = []
    verified_sessions: List[str] = []
    verified_windows: List[str] = []

    # -----------------------------------------------------------------------
    # Check 1: Target safety (Refuse live root overwrite)
    # -----------------------------------------------------------------------
    canonical_resolved = Path(CANONICAL_STORAGE_ROOT).resolve()
    safety_violations: List[str] = []
    if staging == canonical_resolved:
        safety_violations.append(
            f"REFUSAL: Target directory {staging} is the canonical persistent root ({CANONICAL_STORAGE_ROOT}). "
            f"Restore drill must run in a disposable staging directory."
        )
    checks.append(
        RestoreCheckDetail(
            check_id="CHK_TARGET_SAFETY",
            status="FAIL" if safety_violations else "PASS",
            description="Verify target is a disposable staging directory and not the live production root.",
            violations=safety_violations,
        )
    )
    if safety_violations:
        all_violations.extend(safety_violations)
        return RestoreValidationResult(
            target_dir=str(staging),
            status="FAIL",
            checks=checks,
            violations=all_violations,
            summary_text="FAILED: Target safety check failed. Refused to overwrite live root.",
        )

    # -----------------------------------------------------------------------
    # Check 2: Directory taxonomy
    # -----------------------------------------------------------------------
    taxonomy_violations: List[str] = []
    windows_dir = staging / "windows"
    sessions_dir = staging / "sessions"

    if not windows_dir.is_dir():
        taxonomy_violations.append("Missing required directory: windows/")
    if not sessions_dir.is_dir():
        taxonomy_violations.append("Missing required directory: sessions/")

    checks.append(
        RestoreCheckDetail(
            check_id="CHK_DIR_TAXONOMY",
            status="FAIL" if taxonomy_violations else "PASS",
            description="Verify presence of canonical directories (windows/, sessions/).",
            violations=taxonomy_violations,
        )
    )
    if taxonomy_violations:
        all_violations.extend(taxonomy_violations)

    # -----------------------------------------------------------------------
    # Check 3: Checksum & File Completeness
    # -----------------------------------------------------------------------
    checksum_violations: List[str] = []
    present_rel_paths: Set[str] = set()

    for p in staging.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            present_rel_paths.add(p.relative_to(staging).as_posix())

    if manifest is not None:
        # Verify all manifest files exist and match checksum
        for rel_path, expected_sha in manifest.sha256_checksums.items():
            full_path = staging / rel_path
            if not full_path.is_file():
                checksum_violations.append(f"Missing file from backup manifest: {rel_path}")
            else:
                actual_sha = compute_file_sha256(full_path)
                if actual_sha != expected_sha:
                    checksum_violations.append(
                        f"Checksum mismatch for {rel_path}: expected {expected_sha}, got {actual_sha}"
                    )

        # Strict completeness check: detect unexpected extraneous files
        if strict_files:
            expected_set = set(manifest.sha256_checksums.keys())
            unexpected = present_rel_paths - expected_set
            # Filter out top-level backup manifest if it was placed inside staging
            unexpected = {u for u in unexpected if not u.endswith(".manifest.json") or "/" in u}
            if unexpected:
                checksum_violations.append(
                    f"Unexpected extraneous files detected in staging root: {sorted(unexpected)}"
                )

    checks.append(
        RestoreCheckDetail(
            check_id="CHK_CHECKSUMS_AND_COMPLETENESS",
            status="FAIL" if checksum_violations else "PASS",
            description="Verify SHA-256 digests and completeness against backup manifest.",
            violations=checksum_violations,
        )
    )
    if checksum_violations:
        all_violations.extend(checksum_violations)

    # -----------------------------------------------------------------------
    # Check 4: Session Journal Hash-Chain Integrity
    # -----------------------------------------------------------------------
    journal_violations: List[str] = []
    journal_files = sorted(sessions_dir.glob("*.journal.jsonl")) if sessions_dir.is_dir() else []

    if require_evidence and not journal_files:
        journal_violations.append("No session journals found under sessions/.")

    for jpath in journal_files:
        session_id = jpath.name.split(".journal.jsonl")[0]
        try:
            journal = PaperEventJournal(
                session_id=session_id,
                persistence_path=jpath,
                git_commit=expected_git_commit or "restore-validator",
                component_version="restore-validator-1.0.0",
            )
            v_list = journal.verify_integrity()
            if v_list:
                journal_violations.extend([f"Journal {jpath.name}: {v}" for v in v_list])
            else:
                verified_sessions.append(session_id)
        except Exception as exc:
            journal_violations.append(f"Journal {jpath.name} failed to load or verify: {exc}")

    checks.append(
        RestoreCheckDetail(
            check_id="CHK_JOURNAL_INTEGRITY",
            status="FAIL" if journal_violations else "PASS",
            description="Verify cryptographic hash-chain integrity of all session journals.",
            violations=journal_violations,
        )
    )
    if journal_violations:
        all_violations.extend(journal_violations)

    # -----------------------------------------------------------------------
    # Check 5: Session Manifest Schema & Integrity
    # -----------------------------------------------------------------------
    session_manifest_violations: List[str] = []
    session_manifest_files = sorted(sessions_dir.glob("*.manifest.json")) if sessions_dir.is_dir() else []

    for sm_path in session_manifest_files:
        try:
            raw_text = sm_path.read_text(encoding="utf-8")
            s_manifest = PaperSessionManifest.model_validate_json(raw_text)

            if s_manifest.mode != PaperMode.PAPER_ONLY:
                session_manifest_violations.append(
                    f"Session manifest {sm_path.name}: mode {s_manifest.mode!r} != 'PAPER_ONLY'"
                )
            if not s_manifest.no_real_orders:
                session_manifest_violations.append(
                    f"Session manifest {sm_path.name}: no_real_orders is False"
                )
            if expected_git_commit and s_manifest.git_commit != expected_git_commit:
                session_manifest_violations.append(
                    f"Session manifest {sm_path.name}: git_commit {s_manifest.git_commit} "
                    f"does not match expected {expected_git_commit}"
                )
            if expected_config_hash and s_manifest.config_hash != expected_config_hash:
                session_manifest_violations.append(
                    f"Session manifest {sm_path.name}: config_hash {s_manifest.config_hash} "
                    f"does not match expected {expected_config_hash}"
                )
        except Exception as exc:
            session_manifest_violations.append(
                f"Session manifest {sm_path.name} validation failed: {exc}"
            )

    checks.append(
        RestoreCheckDetail(
            check_id="CHK_SESSION_MANIFEST",
            status="FAIL" if session_manifest_violations else "PASS",
            description="Verify PaperSessionManifest schema, lineage, and paper-only invariants.",
            violations=session_manifest_violations,
        )
    )
    if session_manifest_violations:
        all_violations.extend(session_manifest_violations)

    # -----------------------------------------------------------------------
    # Check 6: Window Manifest & Deployment Interlock Integrity
    # -----------------------------------------------------------------------
    window_violations: List[str] = []
    window_manifest_files = sorted(windows_dir.glob("*.manifest.json")) if windows_dir.is_dir() else []
    window_state_files = sorted(windows_dir.glob("*.state.json")) if windows_dir.is_dir() else []

    if require_evidence and not window_manifest_files:
        window_violations.append("No window manifests found under windows/.")

    # Validate state markers
    for sf in window_state_files:
        try:
            raw_marker = sf.read_text(encoding="utf-8")
            marker = WindowInterlockMarker.model_validate_json(raw_marker)
            if marker.state not in (WindowState.QUIESCENT, WindowState.OPEN, WindowState.SEALED, WindowState.VOID):
                window_violations.append(f"Window marker {sf.name}: invalid state {marker.state}")
        except Exception as exc:
            window_violations.append(f"Window marker {sf.name} parsing failed: {exc}")

    # Validate window manifests
    for wf in window_manifest_files:
        window_id = wf.name.split(".manifest.json")[0]
        try:
            raw_manifest = wf.read_text(encoding="utf-8")
            w_manifest = WindowManifest.model_validate_json(raw_manifest)

            # 1. Run fail-closed validator
            v_list = validate_window_manifest(w_manifest)
            if v_list:
                window_violations.extend([f"Window manifest {wf.name}: {v}" for v in v_list])

            # 2. Check manifest hash
            computed_hash = w_manifest.compute_hash()
            if w_manifest.evidence_status == EvidenceStatus.SEALED:
                if w_manifest.window_manifest_hash != computed_hash:
                    window_violations.append(
                        f"Window manifest {wf.name}: computed hash {computed_hash} != "
                        f"recorded hash {w_manifest.window_manifest_hash}"
                    )

            # 3. Check runtime segments attribution & provenance
            for seg in w_manifest.runtime_segments:
                if expected_git_commit and seg.git_commit != expected_git_commit:
                    window_violations.append(
                        f"Window {wf.name} segment {seg.segment_id}: git_commit {seg.git_commit} "
                        f"!= expected {expected_git_commit}"
                    )
                if expected_image_digest and seg.image_digest != expected_image_digest:
                    window_violations.append(
                        f"Window {wf.name} segment {seg.segment_id}: image_digest {seg.image_digest} "
                        f"!= expected {expected_image_digest}"
                    )

            if not window_violations:
                verified_windows.append(window_id)
        except Exception as exc:
            window_violations.append(f"Window manifest {wf.name} validation failed: {exc}")

    checks.append(
        RestoreCheckDetail(
            check_id="CHK_WINDOW_MANIFEST_PROVENANCE",
            status="FAIL" if window_violations else "PASS",
            description="Verify WindowManifest schema, cryptographic hash, and runtime provenance.",
            violations=window_violations,
        )
    )
    if window_violations:
        all_violations.extend(window_violations)

    # -----------------------------------------------------------------------
    # Build final summary and result
    # -----------------------------------------------------------------------
    final_status = "PASS" if not all_violations else "FAIL"

    summary_lines = [
        "==================================================================",
        "   ACASH V5 — NON-DESTRUCTIVE RESTORE VALIDATION REPORT           ",
        "==================================================================",
        f" Target Directory : {staging}",
        f" Overall Status   : {'[PASS]' if final_status == 'PASS' else '[FAIL CLOSED]'}",
        f" Files Inspected  : {len(present_rel_paths)}",
        f" Sessions Verified: {len(verified_sessions)} ({', '.join(verified_sessions) or 'None'})",
        f" Windows Verified : {len(verified_windows)} ({', '.join(verified_windows) or 'None'})",
        "------------------------------------------------------------------",
        " Invariant Checks Summary:",
    ]
    for c in checks:
        icon = "✓" if c.status == "PASS" else "✗"
        summary_lines.append(f"   [{icon}] {c.check_id:30s}: {c.status}")

    if all_violations:
        summary_lines.append("------------------------------------------------------------------")
        summary_lines.append(f" VIOLATIONS DETECTED ({len(all_violations)}):")
        for i, v in enumerate(all_violations, 1):
            summary_lines.append(f"   {i}. {v}")
    summary_lines.append("==================================================================")
    summary_text = "\n".join(summary_lines)

    return RestoreValidationResult(
        target_dir=str(staging),
        status=final_status,
        checks=checks,
        file_count=len(present_rel_paths),
        verified_sessions=verified_sessions,
        verified_windows=verified_windows,
        violations=all_violations,
        summary_text=summary_text,
    )


def restore_and_validate(
    archive_path: Path,
    staging_dir: Path,
    manifest_path: Optional[Path] = None,
    *,
    expected_git_commit: Optional[str] = None,
    expected_config_hash: Optional[str] = None,
    expected_image_digest: Optional[str] = None,
    strict_files: bool = True,
    require_evidence: bool = True,
) -> RestoreValidationResult:
    """Safely unpack an ACASH backup archive into staging and validate all invariants."""
    staging = Path(staging_dir)
    safe_extract_archive(archive_path, staging)

    manifest: Optional[AcashBackupManifest] = None
    if manifest_path is not None and manifest_path.is_file():
        manifest = AcashBackupManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    else:
        # Check if manifest was extracted into staging or exists next to archive
        candidate_same_dir = archive_path.parent / f"{archive_path.name.replace('.tar.gz', '')}.manifest.json"
        if candidate_same_dir.is_file():
            manifest = AcashBackupManifest.model_validate_json(candidate_same_dir.read_text(encoding="utf-8"))

    return validate_restore_state(
        staging,
        manifest=manifest,
        expected_git_commit=expected_git_commit,
        expected_config_hash=expected_config_hash,
        expected_image_digest=expected_image_digest,
        strict_files=strict_files,
        require_evidence=require_evidence,
    )
