"""Manifest schemas and canonical hashing specifications for Gate B Governance Repair (Rev 10).

Adheres strictly to:
- Specification: docs/phase13/gate_b_governance_repair_plan.md (Rev 10)
- Invariants: ACASH-RELEASE-TREE-V1, ACASH-RUNTIME-ENV-V1, Strict Fail-Closed
- AST Closure: ZERO key generation or private key symbols.
"""

from datetime import datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import unicodedata

from pydantic import BaseModel, ConfigDict, Field

from acash.gate_b.exceptions import DataContractError


class ReleaseManifest(BaseModel):
    """Authoritative Release Manifest schema (Rev 10 Section 3.5)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_version: int = Field(default=1, description="Schema version.")
    release_tag: str = Field(description="Audited release tag, e.g. v1.0.0-gate-b.")
    release_commit_sha: str = Field(description="Exact Git commit SHA of frozen release baseline.")
    bootstrapper_artifact_sha256: str = Field(
        description="Exact SHA-256 of tools/governance/bin/acash-bootstrapper.exe."
    )
    bootstrapper_authenticode_thumbprint: str = Field(
        description="Authoritative SHA-256 thumbprint of External Release Authority Authenticode certificate."
    )
    launcher_artifact_sha256: str = Field(
        description="Exact SHA-256 of tools/governance/launch_runner.py."
    )
    executable_tree_digest: str = Field(
        description="Canonical SHA-256 tree digest using ACASH-RELEASE-TREE-V1."
    )
    python_interpreter_sha256: str = Field(
        description="Exact SHA-256 of authoritative python.exe binary."
    )
    dependency_lock_digest: str = Field(
        description="Exact SHA-256 of uv.lock."
    )
    runtime_dependencies_tree_digest: str = Field(
        description="Deterministic SHA-256 tree digest using ACASH-RUNTIME-ENV-V1."
    )
    sovereign_root_anchor_digest: str = Field(
        description="Exact SHA-256 digest of sovereign_root_anchor.json."
    )
    release_timestamp_utc: datetime = Field(description="UTC timestamp of release authorization.")
    release_authority_key_id: str = Field(
        description="Key ID of the External Release Authority."
    )
    release_authority_signature_ed25519: str = Field(
        description="Hex-encoded Ed25519 signature over canonical release manifest payload."
    )

    def compute_canonical_signed_bytes(self) -> bytes:
        """Compute canonical JSON bytes over manifest fields excluding the signature."""
        payload = {
            "bootstrapper_artifact_sha256": self.bootstrapper_artifact_sha256,
            "bootstrapper_authenticode_thumbprint": self.bootstrapper_authenticode_thumbprint,
            "dependency_lock_digest": self.dependency_lock_digest,
            "executable_tree_digest": self.executable_tree_digest,
            "launcher_artifact_sha256": self.launcher_artifact_sha256,
            "manifest_version": self.manifest_version,
            "python_interpreter_sha256": self.python_interpreter_sha256,
            "release_authority_key_id": self.release_authority_key_id,
            "release_commit_sha": self.release_commit_sha,
            "release_tag": self.release_tag,
            "release_timestamp_utc": self.release_timestamp_utc.isoformat(),
            "runtime_dependencies_tree_digest": self.runtime_dependencies_tree_digest,
            "sovereign_root_anchor_digest": self.sovereign_root_anchor_digest,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class GenesisBootstrapManifest(BaseModel):
    """Authoritative Genesis Bootstrap Manifest schema (Rev 10 Section 4.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_version: int = Field(default=1, description="Schema version.")
    root_id: str = Field(description="Unique stable identifier of fresh storage root.")
    genesis_head_digest: str = Field(
        description="Canonical genesis head digest (must be GENESIS_HEAD_DIGEST)."
    )
    trust_store_digest: str = Field(description="Expected SHA-256 of trust_store.json.")
    trust_anchor_manifest_digest: str = Field(
        description="Expected SHA-256 of trust_anchor_manifest.json."
    )
    incident_archive_manifest_digest: str = Field(
        description="SHA-256 tree manifest of var/gate_b_incident_archive/."
    )
    bootstrap_timestamp_utc: datetime = Field(description="UTC timestamp of bootstrap ceremony.")
    bootstrap_signer_key_id: str = Field(
        description="Cryptographic identifier of sovereign bootstrapping key."
    )
    bootstrap_signature_ed25519: str = Field(
        description="Hex-encoded Ed25519 signature over canonical payload bytes."
    )

    def compute_canonical_signed_bytes(self) -> bytes:
        """Compute canonical JSON bytes over manifest fields excluding the signature."""
        payload = {
            "bootstrap_signer_key_id": self.bootstrap_signer_key_id,
            "bootstrap_timestamp_utc": self.bootstrap_timestamp_utc.isoformat(),
            "genesis_head_digest": self.genesis_head_digest,
            "incident_archive_manifest_digest": self.incident_archive_manifest_digest,
            "manifest_version": self.manifest_version,
            "root_id": self.root_id,
            "trust_anchor_manifest_digest": self.trust_anchor_manifest_digest,
            "trust_store_digest": self.trust_store_digest,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class TrustAnchorManifest(BaseModel):
    """Authoritative Trust Anchor Manifest schema (Rev 10 Section 5.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_version: int = Field(default=1, description="Schema version.")
    ceremony_id: str = Field(description="Identifier of sovereign key ceremony.")
    trust_store_digest: str = Field(description="Exact SHA-256 digest of canonical trust_store.json.")
    trust_store_key_ids: Tuple[str, ...] = Field(
        description="Explicit tuple of registered key IDs (e.g. KEY_HUMAN_GOVERNANCE_AUDITOR_001)."
    )
    ceremony_timestamp_utc: datetime = Field(description="UTC timestamp of key ceremony.")
    sovereign_signer_key_id: str = Field(
        description="Key ID of sovereign authority that authorized this trust store."
    )
    sovereign_signature_ed25519: str = Field(
        description="Hex-encoded Ed25519 signature over canonical manifest payload bytes."
    )

    def compute_canonical_signed_bytes(self) -> bytes:
        """Compute canonical JSON bytes over manifest fields excluding the signature."""
        payload = {
            "ceremony_id": self.ceremony_id,
            "ceremony_timestamp_utc": self.ceremony_timestamp_utc.isoformat(),
            "manifest_version": self.manifest_version,
            "sovereign_signer_key_id": self.sovereign_signer_key_id,
            "trust_store_digest": self.trust_store_digest,
            "trust_store_key_ids": list(self.trust_store_key_ids),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class SovereignRootAnchor(BaseModel):
    """Sovereign Root Anchor schema stored in sovereign_root_anchor.json."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    anchor_version: int = Field(default=1, description="Anchor schema version.")
    root_authority_id: str = Field(description="ID of the sovereign root authority.")
    root_public_key_b64: str = Field(description="Base64-encoded Ed25519 root public key.")
    bootstrap_public_key_b64: str = Field(description="Base64-encoded Ed25519 bootstrap public key.")
    release_public_key_b64: str = Field(description="Base64-encoded Ed25519 release public key.")
    authenticode_thumbprint: str = Field(description="SHA-256 thumbprint of Authenticode certificate.")


class HumanGORecordPayload(BaseModel):
    """Canonical HumanGORecordPayload schema (Rev 10 Section 8)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    go_record_id: str
    authorization_id: str
    approved_authorization_digest: str
    source_approved_digest: str
    previous_record_digest: str
    account_id: str
    symbol: str
    max_notional_usd: Decimal
    max_drawdown_pct: Decimal
    record_timestamp_utc: datetime
    expires_at_utc: datetime
    approver_public_key_id: str

    def compute_canonical_signed_bytes(self) -> bytes:
        """Compute canonical JSON bytes for signing."""
        payload = {
            "account_id": self.account_id,
            "approved_authorization_digest": self.approved_authorization_digest,
            "approver_public_key_id": self.approver_public_key_id,
            "authorization_id": self.authorization_id,
            "expires_at_utc": self.expires_at_utc.isoformat(),
            "go_record_id": self.go_record_id,
            "max_drawdown_pct": str(self.max_drawdown_pct),
            "max_notional_usd": str(self.max_notional_usd),
            "previous_record_digest": self.previous_record_digest,
            "record_timestamp_utc": self.record_timestamp_utc.isoformat(),
            "source_approved_digest": self.source_approved_digest,
            "symbol": self.symbol,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


# -----------------------------------------------------------------------------
# Canonical Hashing Algorithms: ACASH-RELEASE-TREE-V1 & ACASH-RUNTIME-ENV-V1
# -----------------------------------------------------------------------------

def is_reparse_point(path: Path) -> bool:
    """Check if a path is an NTFS reparse point or symlink."""
    try:
        import ctypes
        FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attrs != 0xFFFFFFFF and (attrs & FILE_ATTRIBUTE_REPARSE_POINT) != 0:
            return True
    except Exception:
        pass
    return path.is_symlink()


def compute_acash_release_tree_v1(repo_root: Path) -> Tuple[str, bytes]:
    """Compute ACASH-RELEASE-TREE-V1 canonical digest over codebase (Rev 10 Section 3.4).

    Returns:
        (hex_digest, canonical_payload_bytes)
    """
    repo_root = repo_root.resolve()

    excluded_rel_exact: Set[str] = {
        "release_manifest.json",
        "pyproject.toml.bak",
    }

    # Inclusion prefixes / exact paths
    # src/**, tools/governance/** (excluding bin/), pyproject.toml, uv.lock
    candidate_paths: List[Path] = []

    # Check top-level files
    for root_file in ["pyproject.toml", "uv.lock"]:
        p = repo_root / root_file
        if p.is_file():
            candidate_paths.append(p)

    # Check directories
    for search_dir in [repo_root / "src", repo_root / "tools" / "governance"]:
        if not search_dir.exists():
            continue
        for root, dirs, files in os.walk(search_dir):
            root_path = Path(root)
            # Exclude tools/governance/bin
            rel_root = root_path.relative_to(repo_root).as_posix()
            if rel_root.startswith("tools/governance/bin") or rel_root == "tools/governance/bin":
                continue
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            for f in files:
                candidate_paths.append(root_path / f)

    # Process and filter candidates
    leaf_entries: List[Tuple[str, str]] = []
    case_map: Dict[str, str] = {}

    for file_path in candidate_paths:
        # Reparse point check
        if is_reparse_point(file_path):
            raise DataContractError(f"REPARSE_POINT_DETECTED: {file_path}")

        # Compute relative POSIX path
        rel_path = file_path.relative_to(repo_root).as_posix()

        # Unicode NFC normalization
        rel_path = unicodedata.normalize("NFC", rel_path)

        # Strict exclusion filters
        if rel_path in excluded_rel_exact:
            continue
        if rel_path.startswith("tools/governance/bin/"):
            continue
        if rel_path.startswith("var/"):
            continue
        if rel_path.startswith(".git/") or rel_path.startswith(".github/"):
            continue
        if any(rel_path.endswith(ext) for ext in [".sig", ".signature", ".sha256", ".pyc", ".pyo", ".pyd", ".tmp", ".log", ".bak"]):
            continue
        if "/__pycache__/" in rel_path or rel_path.startswith("__pycache__/"):
            continue
        if any(part.startswith(".") for part in rel_path.split("/")):
            # Ignore hidden cache dirs (.pytest_cache, .mypy_cache, etc.)
            continue

        # Case collision check
        lower_key = rel_path.lower()
        if lower_key in case_map and case_map[lower_key] != rel_path:
            raise DataContractError(f"CASE_COLLISION_DETECTED: {rel_path} vs {case_map[lower_key]}")
        case_map[lower_key] = rel_path

        # Leaf SHA-256 over raw binary bytes
        raw_bytes = file_path.read_bytes()
        leaf_sha = hashlib.sha256(raw_bytes).hexdigest()
        leaf_entries.append((rel_path, leaf_sha))

    # Sort lexicographically by canonical relative path in UTF-8 byte order
    leaf_entries.sort(key=lambda x: x[0].encode("utf-8"))

    # Assemble canonical payload
    # "ACASH-RELEASE-TREE-V1\0" || sum(canonical_rel_path_i || "\0" || H_leaf_i || "\n")
    payload_parts = [b"ACASH-RELEASE-TREE-V1\x00"]
    for rel_path, leaf_sha in leaf_entries:
        payload_parts.append(rel_path.encode("utf-8") + b"\x00" + leaf_sha.encode("ascii") + b"\n")

    canonical_payload = b"".join(payload_parts)
    tree_digest = hashlib.sha256(canonical_payload).hexdigest()
    return tree_digest, canonical_payload


def compute_acash_runtime_env_v1(site_packages_dir: Path) -> Tuple[str, bytes]:
    """Compute ACASH-RUNTIME-ENV-V1 canonical digest over site-packages (Rev 10 Section 3.2).

    Returns:
        (hex_digest, canonical_payload_bytes)
    """
    site_packages_dir = site_packages_dir.resolve()
    if not site_packages_dir.exists():
        raise DataContractError(f"SITE_PACKAGES_NOT_FOUND: {site_packages_dir}")

    allowed_suffixes = {".py", ".pyd", ".dll", ".so", ".json", ".txt"}
    excluded_names = {"RECORD", "INSTALLER", "direct_url.json"}

    leaf_entries: List[Tuple[str, str]] = []

    for root, dirs, files in os.walk(site_packages_dir):
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        root_path = Path(root)
        for f in files:
            p = root_path / f
            if is_reparse_point(p):
                raise DataContractError(f"REPARSE_POINT_DETECTED_IN_VENV: {p}")
            rel_posix = p.relative_to(site_packages_dir).as_posix()
            rel_posix = unicodedata.normalize("NFC", rel_posix)

            # Check exclusions
            if f in excluded_names and ".dist-info" in rel_posix:
                continue
            if f.endswith(".pyc") or f.endswith(".pyo") or f.endswith(".pyd.tmp"):
                continue

            # Check inclusions
            suffix = p.suffix.lower()
            is_metadata = rel_posix.endswith(".dist-info/METADATA") or rel_posix.endswith(".dist-info/entry_points.txt")
            if suffix in allowed_suffixes or is_metadata:
                raw_bytes = p.read_bytes()
                leaf_sha = hashlib.sha256(raw_bytes).hexdigest()
                leaf_entries.append((rel_posix, leaf_sha))

    # Sort lexicographically by relative path
    leaf_entries.sort(key=lambda x: x[0].encode("utf-8"))

    # Assemble payload: "ACASH-RUNTIME-ENV-V1\0" || sum(rel_posix || "\0" || leaf_sha || "\n")
    payload_parts = [b"ACASH-RUNTIME-ENV-V1\x00"]
    for rel_posix, leaf_sha in leaf_entries:
        payload_parts.append(rel_posix.encode("utf-8") + b"\x00" + leaf_sha.encode("ascii") + b"\n")

    canonical_payload = b"".join(payload_parts)
    runtime_digest = hashlib.sha256(canonical_payload).hexdigest()
    return runtime_digest, canonical_payload
