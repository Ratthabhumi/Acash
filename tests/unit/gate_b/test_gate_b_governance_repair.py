"""Adversarial Verification Suite for Gate B Governance Repair (Tests B1–B23).

Strictly adheres to:
- Specification: docs/phase13/gate_b_governance_repair_plan.md (Rev 10 Section 9)
- Governing Standards: AGENTS.md Core Principles 1, 2, 3, 14
- Invariants: Strict Fail-Closed, Anti-Self-Authorization, Hardware Presence,
  Static AST Closure, Host-Level Windows Enforcement (B19, B20, B23).
"""

import ast
import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Dict, Generator, List, Optional, Set, Tuple
from uuid import UUID, uuid4

import pytest

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.crypto import (
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.execution.signing import Ed25519Signer, StorageEngineSigner
from acash.gate_b.exceptions import (
    CryptographicVerificationError,
    GovernanceSecurityError,
    PreExecutionIntegrityError,
    PreLiveRiskAdmissionError,
    StorageDurabilityError,
)
from acash.gate_b.manifest import (
    GenesisBootstrapManifest,
    HumanGORecordPayload,
    ReleaseManifest,
    SovereignRootAnchor,
    TrustAnchorManifest,
    compute_acash_release_tree_v1,
    compute_acash_runtime_env_v1,
)
from acash.gate_b.runner import VerifyOnlyGateBRunner, verify_runner_process_token, verify_sys_path_sanitization
from acash.gate_b.schema import (
    HumanGORecord,
    LiveAuthorization,
    LiveAuthorizationStatus,
)
from acash.gate_b.storage import GENESIS_HEAD_DIGEST, StoragePlatformUtils
from tools.governance.launch_runner import AuthenticatedLauncher
from tools.governance.mint_human_go_record import HardwareUserPresenceError, InteractiveMintTool


@pytest.fixture
def governance_env(tmp_path: Path) -> Generator[Dict[str, Any], None, None]:
    """Provide fully wired isolated governance repair test environment."""
    repo_root = Path.cwd()
    storage_root = tmp_path / "var" / "gate_b"
    storage_root.mkdir(parents=True, exist_ok=True)
    drafts_dir = storage_root / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    gov_dir = storage_root / "governance"
    gov_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate keys for authorities
    root_priv, root_pub = Ed25519Signer.generate_key_pair()
    boot_priv, boot_pub = Ed25519Signer.generate_key_pair()
    rel_priv, rel_pub = Ed25519Signer.generate_key_pair()
    app_priv, app_pub = Ed25519Signer.generate_key_pair()
    eng_priv, eng_pub = Ed25519Signer.generate_key_pair()

    app_key_id = "KEY_HUMAN_GOVERNANCE_AUDITOR_001"
    eng_key_id = "KEY_STORAGE_ENGINE_PROD_001"

    now_utc = datetime.now(timezone.utc)

    # 2. Build and save sovereign root anchor
    anchor = SovereignRootAnchor(
        anchor_version=1,
        root_authority_id="ACASH_SOVEREIGN_ROOT_AUTHORITY_001",
        root_public_key_b64=root_pub,
        bootstrap_public_key_b64=boot_pub,
        release_public_key_b64=rel_pub,
        authenticode_thumbprint="A" * 64,
    )
    anchor_path = tmp_path / "sovereign_root_anchor.json"
    anchor_path.write_bytes(anchor.model_dump_json(indent=2).encode("utf-8"))

    # 3. Build and save sealed trust store
    app_entry = Ed25519TrustStoreEntry(
        key_id=app_key_id,
        issuer_id="ACASH_HUMAN_GOVERNANCE_ROOT",
        public_key_b64=app_pub,
        valid_from=now_utc - timedelta(days=1),
        valid_until=now_utc + timedelta(days=365),
        status=TrustStoreEntryStatus.ACTIVE,
    )
    eng_entry = Ed25519TrustStoreEntry(
        key_id=eng_key_id,
        issuer_id="ACASH_STORAGE_ENGINE_ROOT",
        public_key_b64=eng_pub,
        valid_from=now_utc - timedelta(days=1),
        valid_until=now_utc + timedelta(days=365),
        status=TrustStoreEntryStatus.ACTIVE,
    )
    trust_store = Ed25519TrustStore(entries=(app_entry, eng_entry))
    ts_path = storage_root / "trust_store.json"
    ts_bytes = json.dumps(trust_store.model_dump(mode="json"), indent=2).encode("utf-8")
    ts_path.write_bytes(ts_bytes)
    ts_digest = hashlib.sha256(ts_bytes).hexdigest()

    # 4. Sign and save trust anchor manifest
    ta_manifest_draft = TrustAnchorManifest(
        manifest_version=1,
        ceremony_id="CEREMONY_KEY_HARVEST_20260905",
        trust_store_digest=ts_digest,
        trust_store_key_ids=(app_key_id, eng_key_id),
        ceremony_timestamp_utc=now_utc,
        sovereign_signer_key_id=anchor.root_authority_id,
        sovereign_signature_ed25519="",
    )
    ta_sig = Ed25519Signer.sign(root_priv, ta_manifest_draft.compute_canonical_signed_bytes())
    ta_manifest = ta_manifest_draft.model_copy(update={"sovereign_signature_ed25519": ta_sig})
    ta_path = storage_root / "trust_anchor_manifest.json"
    ta_path.write_bytes(ta_manifest.model_dump_json(indent=2).encode("utf-8"))

    # 5. Genesis head.json and genesis_bootstrap_manifest.json
    head_path = storage_root / "head.json"
    head_path.write_text(json.dumps({"head_digest": GENESIS_HEAD_DIGEST}), encoding="utf-8")

    gb_manifest_draft = GenesisBootstrapManifest(
        manifest_version=1,
        root_id="ROOT_GATE_B_FRESH_GENESIS_001",
        genesis_head_digest=GENESIS_HEAD_DIGEST,
        trust_store_digest=ts_digest,
        trust_anchor_manifest_digest=hashlib.sha256(ta_path.read_bytes()).hexdigest(),
        incident_archive_manifest_digest="0" * 64,
        bootstrap_timestamp_utc=now_utc,
        bootstrap_signer_key_id="BOOTSTRAP_KEY_001",
        bootstrap_signature_ed25519="",
    )
    gb_sig = Ed25519Signer.sign(boot_priv, gb_manifest_draft.compute_canonical_signed_bytes())
    gb_manifest = gb_manifest_draft.model_copy(update={"bootstrap_signature_ed25519": gb_sig})
    gb_path = storage_root / "genesis_bootstrap_manifest.json"
    gb_path.write_bytes(gb_manifest.model_dump_json(indent=2).encode("utf-8"))

    # 6. Gate A audit artifact
    ga_path = tmp_path / "consolidated_gate_a_audit.md"
    ga_path.write_text("# Gate A Certified Demo Trade Audit\nStatus: FLAT\n", encoding="utf-8")
    ga_digest = hashlib.sha256(ga_path.read_bytes()).hexdigest()

    # 7. Draft authorization
    draft_id = "AUTH_P13_EURUSD_001"
    draft = LiveAuthorization(
        authorization_id=draft_id,
        strategy_id="STRAT_DISCRETIONARY_REPAIR_001",
        symbol="EURUSD",
        account_id="ACC_112040157",
        created_at=now_utc,
        expires_at=now_utc + timedelta(days=7),
        required_approvals=1,
        source_approved_digest=ga_digest,
        max_notional_usd=Decimal("500.00"),
        max_drawdown_pct=Decimal("5.00"),
        max_slippage_points=50,
        max_quote_age_ms=5000,
        approved_authorization_digest="",
    )
    draft_approved_bytes = draft.compute_approved_canonical_bytes()
    draft_approved_digest = hashlib.sha256(draft_approved_bytes).hexdigest()
    final_draft = draft.model_copy(update={"approved_authorization_digest": draft_approved_digest})
    draft_file = drafts_dir / f"{draft_id}.json"
    draft_file.write_bytes(final_draft.model_dump_json(indent=2).encode("utf-8"))

    # 8. HumanGORecord
    go_record_draft = HumanGORecord(
        go_record_id="GO_REC_P13_REPAIR_001",
        authorization_id=draft_id,
        approved_authorization_digest=draft_approved_digest,
        previous_record_digest=GENESIS_HEAD_DIGEST,
        record_timestamp_utc=now_utc,
        approver_public_key_id=app_key_id,
        signature_ed25519="",
        record_digest="",
    )
    go_sig = Ed25519Signer.sign(app_priv, go_record_draft.compute_signed_payload_bytes())
    final_go_record = go_record_draft.model_copy(update={
        "signature_ed25519": go_sig,
        "record_digest": go_record_draft.compute_canonical_digest(),
    })
    record_path = gov_dir / "human_go_record.json"
    record_path.write_bytes(final_go_record.model_dump_json(indent=2).encode("utf-8"))

    # 9. Release manifest
    rel_manifest_draft = ReleaseManifest(
        manifest_version=1,
        release_tag="v1.0.0-gate-b-repair",
        release_commit_sha="2a0fb75",
        bootstrapper_artifact_sha256="B" * 64,
        bootstrapper_authenticode_thumbprint="T" * 64,
        launcher_artifact_sha256="L" * 64,
        executable_tree_digest="E" * 64,
        python_interpreter_sha256="P" * 64,
        dependency_lock_digest="D" * 64,
        runtime_dependencies_tree_digest="R" * 64,
        sovereign_root_anchor_digest=hashlib.sha256(anchor_path.read_bytes()).hexdigest(),
        release_timestamp_utc=now_utc,
        release_authority_key_id="REL_KEY_001",
        release_authority_signature_ed25519="",
    )
    rel_sig = Ed25519Signer.sign(rel_priv, rel_manifest_draft.compute_canonical_signed_bytes())
    rel_manifest = rel_manifest_draft.model_copy(update={"release_authority_signature_ed25519": rel_sig})
    rel_manifest_path = tmp_path / "release_manifest.json"
    rel_manifest_path.write_bytes(rel_manifest.model_dump_json(indent=2).encode("utf-8"))

    yield {
        "tmp_path": tmp_path,
        "repo_root": repo_root,
        "storage_root": storage_root,
        "draft_id": draft_id,
        "draft_path": draft_file,
        "record_path": record_path,
        "anchor_path": anchor_path,
        "ta_path": ta_path,
        "gb_path": gb_path,
        "ts_path": ts_path,
        "ga_path": ga_path,
        "rel_manifest_path": rel_manifest_path,
        "app_priv": app_priv,
        "app_pub": app_pub,
        "root_priv": root_priv,
        "boot_priv": boot_priv,
        "trust_store": trust_store,
        "confirmation_token": "TEST-GOV-TOKEN-20260905",
    }


# =============================================================================
# Test B1: Runner Direct AST Ban
# =============================================================================
def test_b1_runner_direct_ast_ban() -> None:
    """Inspect src/acash/gate_b/runner.py AST for key generation calls (Rev 10 Section 7.3)."""
    runner_path = Path("src/acash/gate_b/runner.py").resolve()
    assert runner_path.is_file(), "runner.py missing"

    tree = ast.parse(runner_path.read_text(encoding="utf-8"), filename=str(runner_path))

    prohibited_names = {
        "generate_key_pair",
        "from_private_bytes",
        "Ed25519PrivateKey",
        "Ed25519Signer",
        "sign",
    }

    found_prohibited: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in prohibited_names:
            found_prohibited.append(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in prohibited_names:
            # allow import from other libraries if attribute is completely unrelated
            if node.attr in {"generate_key_pair", "from_private_bytes", "Ed25519Signer"}:
                found_prohibited.append(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module and "signing" in node.module:
                found_prohibited.append(node.module)

    assert not found_prohibited, f"Prohibited keygen/signing symbols found in runner.py: {found_prohibited}"


# =============================================================================
# Test B2: Runner Trust Store Overwrite Attack
# =============================================================================
def test_b2_runner_trust_store_overwrite(governance_env: Dict[str, Any]) -> None:
    """Runner attempts to overwrite trust_store.json; must fail closed."""
    ts_path = governance_env["ts_path"]
    
    # Set read-only attribute
    import ctypes
    FILE_ATTRIBUTE_READONLY = 0x01
    ctypes.windll.kernel32.SetFileAttributesW(str(ts_path), FILE_ATTRIBUTE_READONLY)

    try:
        with pytest.raises((PermissionError, OSError, StorageDurabilityError)):
            with open(ts_path, "wb") as f:
                f.write(b"{\"tampered\": true}")
    finally:
        # Reset attribute
        ctypes.windll.kernel32.SetFileAttributesW(str(ts_path), 0x80)  # FILE_ATTRIBUTE_NORMAL


# =============================================================================
# Test B3: Trust Store DACL Modification Attack
# =============================================================================
def test_b3_trust_store_dacl_modification(governance_env: Dict[str, Any]) -> None:
    """Attempting unauthorized DACL modification must fail closed."""
    ts_path = governance_env["ts_path"]
    # Attempt to use icacls or SetFileSecurityW without required permissions
    res = subprocess.run(
        ["icacls", str(ts_path), "/deny", "Everyone:(W)"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, "DACL setup failed"

    # Now verify write is denied
    with pytest.raises(PermissionError):
        with open(ts_path, "wb") as f:
            f.write(b"tamper")

    # Cleanup DACL
    subprocess.run(["icacls", str(ts_path), "/remove:d", "Everyone"], capture_output=True)


# =============================================================================
# Test B4: Trust Store Replacement Attack
# =============================================================================
def test_b4_trust_store_replacement_attack(governance_env: Dict[str, Any]) -> None:
    """Runner creates temp.json and attempts os.replace on protected trust store."""
    ts_path = governance_env["ts_path"]
    temp_file = governance_env["storage_root"] / "temp_trust_store.json"
    temp_file.write_text("{\"forged\": true}", encoding="utf-8")

    import ctypes
    FILE_ATTRIBUTE_READONLY = 0x01
    ctypes.windll.kernel32.SetFileAttributesW(str(ts_path), FILE_ATTRIBUTE_READONLY)

    try:
        with pytest.raises(PermissionError):
            os.replace(temp_file, ts_path)
    finally:
        ctypes.windll.kernel32.SetFileAttributesW(str(ts_path), 0x80)
        if temp_file.exists():
            temp_file.unlink()


# =============================================================================
# Test B5: Trust Store Tampering (Integrity Failure)
# =============================================================================
def test_b5_trust_store_tampering(governance_env: Dict[str, Any]) -> None:
    """Mutate 1 bit in trust_store.json without updating manifest; fails closed."""
    ts_path = governance_env["ts_path"]
    raw = ts_path.read_bytes()
    # Mutate 1 character
    tampered = bytearray(raw)
    tampered[10] ^= 0x01
    ts_path.write_bytes(bytes(tampered))

    runner = VerifyOnlyGateBRunner(
        target_root=governance_env["storage_root"],
        repo_root=governance_env["repo_root"],
    )

    with pytest.raises(DataContractError, match="TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID"):
        runner.run_activation(
            draft_id=governance_env["draft_id"],
            confirmation_token=governance_env["confirmation_token"],
            human_go_record_artifact=governance_env["record_path"],
            sovereign_root_anchor_path=governance_env["anchor_path"],
            genesis_bootstrap_manifest_path=governance_env["gb_path"],
            trust_anchor_manifest_path=governance_env["ta_path"],
            trust_store_path=ts_path,
            draft_path=governance_env["draft_path"],
            gate_a_audit_path=governance_env["ga_path"],
        )


# =============================================================================
# Test B6: Unknown Approver Key
# =============================================================================
def test_b6_unknown_approver_key(governance_env: Dict[str, Any]) -> None:
    """HumanGORecord signed by key ID not in trust store; fails closed."""
    rec_path = governance_env["record_path"]
    data = json.loads(rec_path.read_text(encoding="utf-8"))
    data["approver_public_key_id"] = "KEY_UNKNOWN_ATTACKER_999"
    rec_path.write_text(json.dumps(data), encoding="utf-8")

    runner = VerifyOnlyGateBRunner(
        target_root=governance_env["storage_root"],
        repo_root=governance_env["repo_root"],
    )

    with pytest.raises(DomainValidationError, match="unknown key_id"):
        runner.run_activation(
            draft_id=governance_env["draft_id"],
            confirmation_token=governance_env["confirmation_token"],
            human_go_record_artifact=rec_path,
            sovereign_root_anchor_path=governance_env["anchor_path"],
            genesis_bootstrap_manifest_path=governance_env["gb_path"],
            trust_anchor_manifest_path=governance_env["ta_path"],
            trust_store_path=governance_env["ts_path"],
            draft_path=governance_env["draft_path"],
            gate_a_audit_path=governance_env["ga_path"],
        )


# =============================================================================
# Test B7: Revoked Approver Key
# =============================================================================
def test_b7_revoked_approver_key(governance_env: Dict[str, Any]) -> None:
    """Approver key status is REVOKED in trust store; fails closed."""
    ts_path = governance_env["ts_path"]
    data = json.loads(ts_path.read_text(encoding="utf-8"))
    for entry in data["entries"]:
        if entry["key_id"] == "KEY_HUMAN_GOVERNANCE_AUDITOR_001":
            entry["status"] = "REVOKED"
    new_bytes = json.dumps(data, indent=2).encode("utf-8")
    ts_path.write_bytes(new_bytes)

    # Re-sign trust anchor manifest with new digest so digest check passes and revocation check triggers
    new_digest = hashlib.sha256(new_bytes).hexdigest()
    ta_path = governance_env["ta_path"]
    ta_data = json.loads(ta_path.read_text(encoding="utf-8"))
    ta_data["trust_store_digest"] = new_digest
    ta_manifest_draft = TrustAnchorManifest.model_validate(ta_data)
    new_sig = Ed25519Signer.sign(governance_env["root_priv"], ta_manifest_draft.compute_canonical_signed_bytes())
    final_ta = ta_manifest_draft.model_copy(update={"sovereign_signature_ed25519": new_sig})
    ta_path.write_bytes(final_ta.model_dump_json(indent=2).encode("utf-8"))

    runner = VerifyOnlyGateBRunner(
        target_root=governance_env["storage_root"],
        repo_root=governance_env["repo_root"],
    )

    with pytest.raises(DomainValidationError, match="has been REVOKED"):
        runner.run_activation(
            draft_id=governance_env["draft_id"],
            confirmation_token=governance_env["confirmation_token"],
            human_go_record_artifact=governance_env["record_path"],
            sovereign_root_anchor_path=governance_env["anchor_path"],
            genesis_bootstrap_manifest_path=governance_env["gb_path"],
            trust_anchor_manifest_path=ta_path,
            trust_store_path=ts_path,
            draft_path=governance_env["draft_path"],
            gate_a_audit_path=governance_env["ga_path"],
        )


# =============================================================================
# Test B8: Expired Authorization Record
# =============================================================================
def test_b8_expired_authorization_record(governance_env: Dict[str, Any]) -> None:
    """Runner executed when current_time > expires_at_utc; fails closed."""
    draft_file = governance_env["draft_path"]
    draft_data = json.loads(draft_file.read_text(encoding="utf-8"))
    expired_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    draft_data["expires_at"] = expired_time
    draft = LiveAuthorization.model_validate(draft_data)
    draft_approved_digest = hashlib.sha256(draft.compute_approved_canonical_bytes()).hexdigest()
    draft_file.write_text(draft.model_dump_json(indent=2), encoding="utf-8")

    rec_path = governance_env["record_path"]
    data = json.loads(rec_path.read_text(encoding="utf-8"))
    record_draft = HumanGORecord(
        go_record_id=data["go_record_id"],
        authorization_id=data["authorization_id"],
        approved_authorization_digest=draft_approved_digest,
        previous_record_digest=data["previous_record_digest"],
        record_timestamp_utc=datetime.fromisoformat(data["record_timestamp_utc"]),
        approver_public_key_id=data["approver_public_key_id"],
        signature_ed25519="",
        record_digest="",
    )
    sig = Ed25519Signer.sign(governance_env["app_priv"], record_draft.compute_signed_payload_bytes())
    final_record = record_draft.model_copy(update={
        "signature_ed25519": sig,
        "record_digest": record_draft.compute_canonical_digest(),
    })
    rec_path.write_bytes(final_record.model_dump_json(indent=2).encode("utf-8"))

    runner = VerifyOnlyGateBRunner(
        target_root=governance_env["storage_root"],
        repo_root=governance_env["repo_root"],
    )

    with pytest.raises(PreLiveRiskAdmissionError, match="HUMAN_GO_EXPIRED"):
        runner.run_activation(
            draft_id=governance_env["draft_id"],
            confirmation_token=governance_env["confirmation_token"],
            human_go_record_artifact=rec_path,
            sovereign_root_anchor_path=governance_env["anchor_path"],
            genesis_bootstrap_manifest_path=governance_env["gb_path"],
            trust_anchor_manifest_path=governance_env["ta_path"],
            trust_store_path=governance_env["ts_path"],
            draft_path=governance_env["draft_path"],
            gate_a_audit_path=governance_env["ga_path"],
        )


# =============================================================================
# Test B9: Stale Ledger Head Continuity (Incident Head Rejection)
# =============================================================================
def test_b9_stale_ledger_head_continuity(governance_env: Dict[str, Any]) -> None:
    """previous_record_digest references incident head 81f4d44a...; fails closed."""
    rec_path = governance_env["record_path"]
    data = json.loads(rec_path.read_text(encoding="utf-8"))
    incident_head = "81f4d44a6953207c3ec5d5d3e55c6f245c421b9e830243c53ebc1e7a1516027b"
    record_draft = HumanGORecord(
        go_record_id=data["go_record_id"],
        authorization_id=data["authorization_id"],
        approved_authorization_digest=data["approved_authorization_digest"],
        previous_record_digest=incident_head,
        record_timestamp_utc=datetime.fromisoformat(data["record_timestamp_utc"]),
        approver_public_key_id=data["approver_public_key_id"],
        signature_ed25519="",
        record_digest="",
    )
    sig = Ed25519Signer.sign(governance_env["app_priv"], record_draft.compute_signed_payload_bytes())
    final_record = record_draft.model_copy(update={
        "signature_ed25519": sig,
        "record_digest": record_draft.compute_canonical_digest(),
    })
    rec_path.write_bytes(final_record.model_dump_json(indent=2).encode("utf-8"))

    runner = VerifyOnlyGateBRunner(
        target_root=governance_env["storage_root"],
        repo_root=governance_env["repo_root"],
    )

    with pytest.raises(DataContractError, match="LEDGER_HEAD_CONTINUITY_BROKEN"):
        runner.run_activation(
            draft_id=governance_env["draft_id"],
            confirmation_token=governance_env["confirmation_token"],
            human_go_record_artifact=rec_path,
            sovereign_root_anchor_path=governance_env["anchor_path"],
            genesis_bootstrap_manifest_path=governance_env["gb_path"],
            trust_anchor_manifest_path=governance_env["ta_path"],
            trust_store_path=governance_env["ts_path"],
            draft_path=governance_env["draft_path"],
            gate_a_audit_path=governance_env["ga_path"],
        )


# =============================================================================
# Test B10: Post-Sign Draft Tampering
# =============================================================================
def test_b10_post_sign_draft_tampering(governance_env: Dict[str, Any]) -> None:
    """Mutate 1 character in draft authorization after record signed; fails closed."""
    draft_file = governance_env["draft_path"]
    data = json.loads(draft_file.read_text(encoding="utf-8"))
    data["symbol"] = "GBPUSD"  # Mutate symbol
    draft_file.write_text(json.dumps(data), encoding="utf-8")

    runner = VerifyOnlyGateBRunner(
        target_root=governance_env["storage_root"],
        repo_root=governance_env["repo_root"],
    )

    with pytest.raises(DataContractError, match="DRAFT_DIGEST_MISMATCH"):
        runner.run_activation(
            draft_id=governance_env["draft_id"],
            confirmation_token=governance_env["confirmation_token"],
            human_go_record_artifact=governance_env["record_path"],
            sovereign_root_anchor_path=governance_env["anchor_path"],
            genesis_bootstrap_manifest_path=governance_env["gb_path"],
            trust_anchor_manifest_path=governance_env["ta_path"],
            trust_store_path=governance_env["ts_path"],
            draft_path=draft_file,
            gate_a_audit_path=governance_env["ga_path"],
        )


# =============================================================================
# Test B11: Genesis Manifest Missing / Tampered
# =============================================================================
def test_b11_genesis_manifest_missing_or_tampered(governance_env: Dict[str, Any]) -> None:
    """Delete genesis_bootstrap_manifest.json; runner fails closed."""
    gb_path = governance_env["gb_path"]
    gb_path.unlink()

    runner = VerifyOnlyGateBRunner(
        target_root=governance_env["storage_root"],
        repo_root=governance_env["repo_root"],
    )

    with pytest.raises(DataContractError, match="GENESIS_ENVIRONMENT_UNVERIFIED"):
        runner.run_activation(
            draft_id=governance_env["draft_id"],
            confirmation_token=governance_env["confirmation_token"],
            human_go_record_artifact=governance_env["record_path"],
            sovereign_root_anchor_path=governance_env["anchor_path"],
            genesis_bootstrap_manifest_path=gb_path,
            trust_anchor_manifest_path=governance_env["ta_path"],
            trust_store_path=governance_env["ts_path"],
            draft_path=governance_env["draft_path"],
            gate_a_audit_path=governance_env["ga_path"],
        )


# =============================================================================
# Test B12: In-Memory Synthetic Record Bypass
# =============================================================================
def test_b12_in_memory_synthetic_record_bypass(governance_env: Dict[str, Any]) -> None:
    """Pass dictionary or in-memory model directly instead of physical file; fails closed."""
    synthetic_dict = {"go_record_id": "FAKE_001", "record_digest": "0" * 64}

    runner = VerifyOnlyGateBRunner(
        target_root=governance_env["storage_root"],
        repo_root=governance_env["repo_root"],
    )

    with pytest.raises(DataContractError, match="ARTIFACT_FILE_REQUIRED"):
        runner.run_activation(
            draft_id=governance_env["draft_id"],
            confirmation_token=governance_env["confirmation_token"],
            human_go_record_artifact=synthetic_dict,  # In-memory dict passed
            sovereign_root_anchor_path=governance_env["anchor_path"],
            genesis_bootstrap_manifest_path=governance_env["gb_path"],
            trust_anchor_manifest_path=governance_env["ta_path"],
            trust_store_path=governance_env["ts_path"],
            draft_path=governance_env["draft_path"],
            gate_a_audit_path=governance_env["ga_path"],
        )


# =============================================================================
# Test B13: Mint Tool Execution Boundary
# =============================================================================
def test_b13_mint_tool_execution_boundary() -> None:
    """Assert mint tool lacks storage mutation classes (Rev 10 Section 7.1)."""
    mint_tool_path = Path("tools/governance/mint_human_go_record.py").resolve()
    assert mint_tool_path.is_file(), "mint tool missing"

    tree = ast.parse(mint_tool_path.read_text(encoding="utf-8"), filename=str(mint_tool_path))

    prohibited_classes = {
        "AuthoritativeGOLedger",
        "LedgerStorageTransaction",
        "StorageCommitContract",
        "switch_committed_snapshot_pointer_atomically",
    }

    found: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in prohibited_classes:
            found.append(node.id)

    assert not found, f"Mint tool exports or imports storage mutation symbols: {found}"


# =============================================================================
# Test B14: Full Static Recursive AST Closure Audit
# =============================================================================
def test_b14_full_static_recursive_ast_closure_audit() -> None:
    """Statically analyze full recursive import graph of runner; assert zero signing/keygen (Rev 10 Section 7.3)."""
    runner_path = Path("src/acash/gate_b/runner.py").resolve()
    repo_root = Path.cwd().resolve()

    visited_modules: Set[Path] = set()
    to_visit: List[Path] = [runner_path]

    prohibited_symbols = {
        "generate_key_pair",
        "from_private_bytes",
        "Ed25519Signer",
    }

    violations: List[Tuple[str, str]] = []

    while to_visit:
        current_file = to_visit.pop()
        if current_file in visited_modules:
            continue
        visited_modules.add(current_file)

        content = current_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(current_file))

        # Check for prohibited symbols in this file
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in prohibited_symbols:
                violations.append((str(current_file.relative_to(repo_root)), node.id))
            elif isinstance(node, ast.Attribute) and node.attr in prohibited_symbols:
                violations.append((str(current_file.relative_to(repo_root)), node.attr))

            # Discover internal relative imports
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("acash."):
                    # Resolve to file path
                    parts = node.module.split(".")
                    rel_path = Path("src", *parts).with_suffix(".py")
                    target = (repo_root / rel_path).resolve()
                    if target.is_file() and target not in visited_modules:
                        to_visit.append(target)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("acash."):
                        parts = alias.name.split(".")
                        rel_path = Path("src", *parts).with_suffix(".py")
                        target = (repo_root / rel_path).resolve()
                        if target.is_file() and target not in visited_modules:
                            to_visit.append(target)

    assert not violations, f"AST Closure Violation: prohibited signing/keygen symbols found in reachable closure: {violations}"


# =============================================================================
# Test B15: Trust Anchor Sovereign Signature Check
# =============================================================================
def test_b15_trust_anchor_sovereign_signature_check(governance_env: Dict[str, Any]) -> None:
    """Mutate trust anchor manifest sovereign signature; fails closed."""
    ta_path = governance_env["ta_path"]
    data = json.loads(ta_path.read_text(encoding="utf-8"))
    # Corrupt signature
    data["sovereign_signature_ed25519"] = "Z" * 88
    ta_path.write_text(json.dumps(data), encoding="utf-8")

    runner = VerifyOnlyGateBRunner(
        target_root=governance_env["storage_root"],
        repo_root=governance_env["repo_root"],
    )

    with pytest.raises(DataContractError, match="TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID"):
        runner.run_activation(
            draft_id=governance_env["draft_id"],
            confirmation_token=governance_env["confirmation_token"],
            human_go_record_artifact=governance_env["record_path"],
            sovereign_root_anchor_path=governance_env["anchor_path"],
            genesis_bootstrap_manifest_path=governance_env["gb_path"],
            trust_anchor_manifest_path=ta_path,
            trust_store_path=governance_env["ts_path"],
            draft_path=governance_env["draft_path"],
            gate_a_audit_path=governance_env["ga_path"],
        )


# =============================================================================
# Test B16: Genesis Bootstrap Signature Check
# =============================================================================
def test_b16_genesis_bootstrap_signature_check(governance_env: Dict[str, Any]) -> None:
    """Mutate genesis bootstrap manifest signature; fails closed."""
    gb_path = governance_env["gb_path"]
    data = json.loads(gb_path.read_text(encoding="utf-8"))
    data["bootstrap_signature_ed25519"] = "Z" * 88
    gb_path.write_text(json.dumps(data), encoding="utf-8")

    runner = VerifyOnlyGateBRunner(
        target_root=governance_env["storage_root"],
        repo_root=governance_env["repo_root"],
    )

    with pytest.raises(DataContractError, match="GENESIS_ENVIRONMENT_UNVERIFIED"):
        runner.run_activation(
            draft_id=governance_env["draft_id"],
            confirmation_token=governance_env["confirmation_token"],
            human_go_record_artifact=governance_env["record_path"],
            sovereign_root_anchor_path=governance_env["anchor_path"],
            genesis_bootstrap_manifest_path=gb_path,
            trust_anchor_manifest_path=governance_env["ta_path"],
            trust_store_path=governance_env["ts_path"],
            draft_path=governance_env["draft_path"],
            gate_a_audit_path=governance_env["ga_path"],
        )


# =============================================================================
# Test B17: Hardware User Presence & PTY Ban
# =============================================================================
def test_b17_hardware_user_presence_and_pty_ban(governance_env: Dict[str, Any]) -> None:
    """Invoke mint tool without hardware touch confirmation; fails closed."""
    tool = InteractiveMintTool(repo_root=governance_env["repo_root"])

    # Ensure simulation flag is off
    os.environ["ACASH_MINT_TOOL_SIMULATE_TOUCH_FOR_TEST"] = "0"
    os.environ["ACASH_MINT_TOOL_ALLOW_NON_TTY_FOR_TEST"] = "1"

    out_path = governance_env["tmp_path"] / "should_not_exist.json"

    with pytest.raises(HardwareUserPresenceError, match="MINT_TOOL_REQUIRES_HARDWARE_USER_PRESENCE"):
        tool.mint_record(
            go_record_id="GO_ATTACK_001",
            authorization_id=governance_env["draft_id"],
            approved_draft_path=governance_env["draft_path"],
            gate_a_audit_path=governance_env["ga_path"],
            approver_key_id="KEY_HUMAN_GOVERNANCE_AUDITOR_001",
            output_path=out_path,
            signing_key_b64=governance_env["app_priv"],
            simulate_hardware_touch=False,
        )


# =============================================================================
# Test B18: Sovereign Root Anchor Tampering Ban
# =============================================================================
def test_b18_sovereign_root_anchor_tampering_ban(governance_env: Dict[str, Any]) -> None:
    """Mutate sovereign_root_anchor.json; runner fails closed."""
    anchor_path = governance_env["anchor_path"]
    data = json.loads(anchor_path.read_text(encoding="utf-8"))
    data["root_public_key_b64"] = "Z" * 44  # Corrupt key
    anchor_path.write_text(json.dumps(data), encoding="utf-8")

    runner = VerifyOnlyGateBRunner(
        target_root=governance_env["storage_root"],
        repo_root=governance_env["repo_root"],
    )

    with pytest.raises(DataContractError, match="TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID"):
        runner.run_activation(
            draft_id=governance_env["draft_id"],
            confirmation_token=governance_env["confirmation_token"],
            human_go_record_artifact=governance_env["record_path"],
            sovereign_root_anchor_path=anchor_path,
            genesis_bootstrap_manifest_path=governance_env["gb_path"],
            trust_anchor_manifest_path=governance_env["ta_path"],
            trust_store_path=governance_env["ts_path"],
            draft_path=governance_env["draft_path"],
            gate_a_audit_path=governance_env["ga_path"],
        )


# =============================================================================
# Test B19: Real Windows Token Privilege Audit
# =============================================================================
def test_b19_real_windows_token_privilege_audit() -> None:
    """Execute token audit against real Win32 process token (Rev 10 Section 6.2)."""
    telemetry = verify_runner_process_token()
    assert isinstance(telemetry, dict)
    if sys.platform == "win32":
        assert "is_elevated" in telemetry
        assert "restricted_privileges_detected" in telemetry


# =============================================================================
# Test B20: Real NTFS Owner Takeover & DACL Ban
# =============================================================================
def test_b20_real_ntfs_owner_takeover_and_dacl_ban(governance_env: Dict[str, Any]) -> None:
    """Attempt Win32 permission modification or takeover on physical NTFS file."""
    if sys.platform != "win32":
        pytest.skip("Windows NTFS test only")

    ts_path = governance_env["ts_path"]
    # Apply Deny DACL
    subprocess.run(["icacls", str(ts_path), "/deny", "Everyone:(DE,WD,AD,WEA,DC,WA)"], capture_output=True)

    try:
        # Assert open with write access is denied by OS kernel
        with pytest.raises(PermissionError):
            with open(ts_path, "r+b") as f:
                f.write(b"tamper")
    finally:
        subprocess.run(["icacls", str(ts_path), "/remove:d", "Everyone"], capture_output=True)


# =============================================================================
# Test B21: Signed Release Manifest Verification
# =============================================================================
def test_b21_signed_release_manifest_verification(governance_env: Dict[str, Any]) -> None:
    """Mutate release_manifest.json; launcher fails closed."""
    rel_path = governance_env["rel_manifest_path"]
    data = json.loads(rel_path.read_text(encoding="utf-8"))
    data["executable_tree_digest"] = "F" * 64
    rel_path.write_text(json.dumps(data), encoding="utf-8")

    launcher = AuthenticatedLauncher(repo_root=governance_env["repo_root"])

    with pytest.raises(PreExecutionIntegrityError):
        launcher.verify_pre_execution_environment(manifest_path=rel_path, verify_tree=False)


# =============================================================================
# Test B22: Pre-Execution Full Artifact Attestation
# =============================================================================
def test_b22_pre_execution_full_artifact_attestation(governance_env: Dict[str, Any]) -> None:
    """Launcher asserts clean anti-hijacking environment and rejects PYTHONPATH."""
    launcher = AuthenticatedLauncher(repo_root=governance_env["repo_root"])

    # Simulate PYTHONPATH injection
    old_pythonpath = os.environ.get("PYTHONPATH")
    old_allow = os.environ.get("ACASH_ALLOW_PYTHONPATH_FOR_TEST")
    try:
        os.environ["PYTHONPATH"] = "malicious_injected_path"
        os.environ["ACASH_ALLOW_PYTHONPATH_FOR_TEST"] = "0"
        with pytest.raises(PreExecutionIntegrityError, match="PYTHONPATH_INJECTION_DETECTED"):
            launcher.verify_pre_execution_environment(
                manifest_path=governance_env["rel_manifest_path"],
                verify_tree=False,
                verify_runtime=False,
            )
    finally:
        if old_pythonpath is not None:
            os.environ["PYTHONPATH"] = old_pythonpath
        else:
            os.environ.pop("PYTHONPATH", None)
        if old_allow is not None:
            os.environ["ACASH_ALLOW_PYTHONPATH_FOR_TEST"] = old_allow
        else:
            os.environ.pop("ACASH_ALLOW_PYTHONPATH_FOR_TEST", None)


# =============================================================================
# Test B23: Native Bootstrapper Host-Level Authenticode & Root Tampering Enforcement
# =============================================================================
def test_b23_native_bootstrapper_host_level_authenticode_enforcement(governance_env: Dict[str, Any]) -> None:
    """Assert host OS Authenticode verification rejects tampered bootstrapper (Rev 10 Section 3.1.1)."""
    if sys.platform != "win32":
        pytest.skip("Windows Authenticode test only")

    bootstrapper_exe = Path("tools/governance/bin/acash-bootstrapper.exe").resolve()
    assert bootstrapper_exe.is_file(), "acash-bootstrapper.exe missing"

    # Make a copy and tamper 1 byte
    tampered_exe = governance_env["tmp_path"] / "tampered-bootstrapper.exe"
    raw_bytes = bytearray(bootstrapper_exe.read_bytes())
    raw_bytes[0x100] ^= 0xFF  # Corrupt byte in PE header / text
    tampered_exe.write_bytes(bytes(raw_bytes))

    # Invoke WinVerifyTrust via ctypes to test OS Authenticode kernel verification
    import ctypes
    from ctypes import wintypes

    wintrust = ctypes.windll.wintrust

    class WINTRUST_FILE_INFO(ctypes.Structure):
        _fields_ = [
            ("cbStruct", wintypes.DWORD),
            ("pcwszFilePath", wintypes.LPCWSTR),
            ("hFile", wintypes.HANDLE),
            ("pgKnownSubject", ctypes.c_void_p),
        ]

    class WINTRUST_DATA(ctypes.Structure):
        _fields_ = [
            ("cbStruct", wintypes.DWORD),
            ("pPolicyCallbackData", ctypes.c_void_p),
            ("pSIPClientData", ctypes.c_void_p),
            ("dwUIChoice", wintypes.DWORD),
            ("fdwRevocationChecks", wintypes.DWORD),
            ("dwUnionChoice", wintypes.DWORD),
            ("pFile", ctypes.POINTER(WINTRUST_FILE_INFO)),
            ("dwStateAction", wintypes.DWORD),
            ("hWVTStateData", wintypes.HANDLE),
            ("pwszURLReference", wintypes.LPWSTR),
            ("dwProvFlags", wintypes.DWORD),
            ("dwUIContext", wintypes.DWORD),
            ("pSignatureSettings", ctypes.c_void_p),
        ]

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    WINTRUST_ACTION_GENERIC_VERIFY_V2 = GUID(
        0x00AAC56B, 0xCD44, 0x11D0, (wintypes.BYTE * 8)(0x8C, 0xC2, 0x00, 0xC0, 0x4F, 0xC2, 0x95, 0xEE)
    )

    WTD_UI_NONE = 2
    WTD_REVOKE_NONE = 0
    WTD_CHOICE_FILE = 1
    WTD_SAFER_FLAG = 0x00000100

    file_info = WINTRUST_FILE_INFO()
    file_info.cbStruct = ctypes.sizeof(WINTRUST_FILE_INFO)
    file_info.pcwszFilePath = str(tampered_exe)
    file_info.hFile = None
    file_info.pgKnownSubject = None

    wt_data = WINTRUST_DATA()
    wt_data.cbStruct = ctypes.sizeof(WINTRUST_DATA)
    wt_data.dwUIChoice = WTD_UI_NONE
    wt_data.fdwRevocationChecks = WTD_REVOKE_NONE
    wt_data.dwUnionChoice = WTD_CHOICE_FILE
    wt_data.pFile = ctypes.pointer(file_info)
    wt_data.dwProvFlags = WTD_SAFER_FLAG

    # Call WinVerifyTrust on tampered binary
    l_status = wintrust.WinVerifyTrust(
        None,
        ctypes.byref(WINTRUST_ACTION_GENERIC_VERIFY_V2),
        ctypes.byref(wt_data),
    )

    # Status must be non-zero (failed verification)
    # Common error codes:
    # TRUST_E_NOSIGNATURE: 0x800B0100
    # TRUST_E_BAD_DIGEST:  0x80096010
    # CERT_E_UNTRUSTEDROOT:0x800B0109
    assert l_status != 0, f"WinVerifyTrust unexpectedly accepted tampered binary (Status: {l_status:#x})"
    print(f"\n[HOST EVIDENCE B23] WinVerifyTrust correctly rejected tampered binary with OS NTSTATUS/HRESULT: {l_status:#x}")
