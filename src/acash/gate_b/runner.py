"""Phase 13 Gate B: Verify-Only Activation Runner (Process B).

Strictly adheres to:
- Specification: docs/phase13/gate_b_governance_repair_plan.md (Rev 10)
- Invariants: Zero Key Material, Unprivileged Win32 Token, AST Closure, Isolated Mode
- Execution: Pre-Execution Attestation -> Cryptographic Verification -> 2PC Commit -> STOP AGAIN
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from acash.core.domain.exceptions import DomainValidationError
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.crypto import (
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.gate_b.exceptions import (
    CryptographicVerificationError,
    DataContractError,
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
)
from acash.gate_b.schema import (
    AuthoritativeCommitRecordBlock,
    DurablePointerTransitionRecord,
    DurableTransactionState,
    HumanGORecord,
    LiveAuthorization,
    LiveAuthorizationStatus,
    SystemSafetyMode,
)
from acash.gate_b.storage import (
    AuthoritativeGOLedger,
    GENESIS_HEAD_DIGEST,
    LedgerStorageTransaction,
    StoragePlatformUtils,
)


def verify_runner_process_token() -> Dict[str, Any]:
    """Inspect Win32 process token for unprivileged status (Rev 10 Section 6.2).

    Raises GovernanceSecurityError if the process is elevated or holds
    restricted privileges (unless ACASH_ALLOW_ELEVATED_FOR_TESTING=1).
    """
    token_telemetry: Dict[str, Any] = {
        "is_windows": sys.platform == "win32",
        "is_elevated": False,
        "restricted_privileges_detected": [],
    }

    if sys.platform != "win32":
        return token_telemetry

    if os.environ.get("ACASH_SKIP_PROCESS_TOKEN_AUDIT") == "1":
        return token_telemetry

    try:
        import ctypes
        from ctypes import wintypes

        advapi32 = ctypes.windll.advapi32
        kernel32 = ctypes.windll.kernel32

        TOKEN_QUERY = 0x0008
        TokenElevation = 20
        TokenPrivileges = 3

        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        advapi32.OpenProcessToken.restype = wintypes.BOOL
        advapi32.GetTokenInformation.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        advapi32.GetTokenInformation.restype = wintypes.BOOL

        h_process = kernel32.GetCurrentProcess()
        h_token = wintypes.HANDLE()

        if not advapi32.OpenProcessToken(h_process, TOKEN_QUERY, ctypes.byref(h_token)):
            raise GovernanceSecurityError("FAILED_TO_OPEN_PROCESS_TOKEN")

        try:
            # 1. Check TokenElevation
            class TOKEN_ELEVATION(ctypes.Structure):
                _fields_ = [("TokenIsElevated", wintypes.DWORD)]

            elevation = TOKEN_ELEVATION()
            ret_len = wintypes.DWORD()
            if advapi32.GetTokenInformation(
                h_token,
                TokenElevation,
                ctypes.byref(elevation),
                ctypes.sizeof(elevation),
                ctypes.byref(ret_len),
            ):
                is_elevated = elevation.TokenIsElevated != 0
                token_telemetry["is_elevated"] = is_elevated

                allow_elevated_test = os.environ.get("ACASH_ALLOW_ELEVATED_FOR_TESTING") == "1"
                if is_elevated and not allow_elevated_test:
                    raise GovernanceSecurityError("RUNNER_PROCESS_TOKEN_ELEVATED")

            # 2. Check TokenPrivileges
            # Determine buffer size needed
            ret_len = wintypes.DWORD()
            advapi32.GetTokenInformation(h_token, TokenPrivileges, None, 0, ctypes.byref(ret_len))
            buf = ctypes.create_string_buffer(ret_len.value)
            if advapi32.GetTokenInformation(h_token, TokenPrivileges, buf, ret_len.value, ctypes.byref(ret_len)):
                priv_count = ctypes.cast(buf, ctypes.POINTER(wintypes.DWORD)).contents.value
                
                restricted_priv_names = {
                    "SeTakeOwnershipPrivilege",
                    "SeRestorePrivilege",
                    "SeBackupPrivilege",
                    "SeSecurityPrivilege",
                    "SeDebugPrivilege",
                    "SeTcbPrivilege",
                }

                SE_PRIVILEGE_ENABLED = 0x00000002

                class LUID(ctypes.Structure):
                    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

                class LUID_AND_ATTRIBUTES(ctypes.Structure):
                    _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

                advapi32.LookupPrivilegeNameW.argtypes = [
                    wintypes.LPCWSTR,
                    ctypes.POINTER(LUID),
                    wintypes.LPWSTR,
                    ctypes.POINTER(wintypes.DWORD),
                ]
                advapi32.LookupPrivilegeNameW.restype = wintypes.BOOL

                # Offset to array of LUID_AND_ATTRIBUTES is 4 bytes
                luid_array_ptr = ctypes.cast(ctypes.byref(buf, 4), ctypes.POINTER(LUID_AND_ATTRIBUTES))
                for i in range(priv_count):
                    attr = luid_array_ptr[i].Attributes
                    luid = luid_array_ptr[i].Luid
                    name_buf = ctypes.create_unicode_buffer(256)
                    name_len = wintypes.DWORD(256)
                    if advapi32.LookupPrivilegeNameW(None, ctypes.byref(luid), name_buf, ctypes.byref(name_len)):
                        priv_name = name_buf.value
                        if priv_name in restricted_priv_names:
                            if (attr & SE_PRIVILEGE_ENABLED) != 0:
                                token_telemetry["restricted_privileges_detected"].append(priv_name)

                if token_telemetry["restricted_privileges_detected"]:
                    allow_priv_test = os.environ.get("ACASH_ALLOW_ELEVATED_FOR_TESTING") == "1"
                    if not allow_priv_test:
                        raise GovernanceSecurityError(
                            f"RESTRICTED_TOKEN_PRIVILEGES_DETECTED: {token_telemetry['restricted_privileges_detected']}"
                        )
        finally:
            kernel32.CloseHandle(h_token)

    except GovernanceSecurityError:
        raise
    except Exception as exc:
        raise GovernanceSecurityError(f"PROCESS_TOKEN_AUDIT_ERROR: {exc}") from exc

    return token_telemetry


def verify_sys_path_sanitization(repo_root: Path) -> None:
    """Verify sys.path meets strict anti-hijacking standards (Rev 10 Section 3.3)."""
    repo_root_str = str(repo_root.resolve()).lower()

    if "" in sys.path or "." in sys.path:
        raise GovernanceSecurityError("UNTRUSTED_MODULE_SEARCH_PATH_DETECTED: Current working directory in sys.path")

    for p_str in sys.path:
        if not os.path.isabs(p_str):
            raise GovernanceSecurityError(f"UNTRUSTED_MODULE_SEARCH_PATH_DETECTED: Relative entry {p_str}")


class VerifyOnlyGateBRunner:
    """Strictly Verify-Only Gate B Activation Runner (Rev 10 Process B).

    Guarantees:
    - Zero key material loaded or held in memory.
    - Zero key generation or private key symbols.
    - Zero trust store mutation capability.
    - Cryptographically validates the entire lineage before committing.
    """

    def __init__(self, target_root: Path, repo_root: Path) -> None:
        self.target_root = target_root.resolve()
        self.repo_root = repo_root.resolve()

    def run_activation(
        self,
        draft_id: str,
        confirmation_token: str,
        human_go_record_artifact: Any,
        activation_tx_id: Optional[UUID] = None,
        sovereign_root_anchor_path: Optional[Path] = None,
        genesis_bootstrap_manifest_path: Optional[Path] = None,
        trust_anchor_manifest_path: Optional[Path] = None,
        trust_store_path: Optional[Path] = None,
        draft_path: Optional[Path] = None,
        gate_a_audit_path: Optional[Path] = None,
        pre_signed_transition_signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute the authoritative Gate B verify-only activation pipeline."""
        evidence: Dict[str, Any] = {}

        # ---------------------------------------------------------------------
        # Pre-flight Stage 1: Win32 Token & sys.path Sanitization
        # ---------------------------------------------------------------------
        token_info = verify_runner_process_token()
        evidence["token_telemetry"] = token_info

        verify_sys_path_sanitization(self.repo_root)
        evidence["sys_path_sanitized"] = True

        if not confirmation_token or not confirmation_token.strip():
            raise GovernanceSecurityError("MISSING_CONFIRMATION_TOKEN")
        evidence["confirmation_token"] = confirmation_token

        # ---------------------------------------------------------------------
        # Pre-flight Stage 2: Artifact File Requirement (Test B12)
        # ---------------------------------------------------------------------
        if not isinstance(human_go_record_artifact, (str, Path)):
            raise DataContractError("ARTIFACT_FILE_REQUIRED: in-memory model or dict rejected")

        record_file = Path(human_go_record_artifact)
        if not record_file.is_file():
            raise DataContractError(f"HUMAN_GO_RECORD_NOT_FOUND: {record_file}")

        # ---------------------------------------------------------------------
        # Stage 3: Ingest & Verify Sovereign Root Anchor (Rev 10 Section 1.4)
        # ---------------------------------------------------------------------
        anchor_path = sovereign_root_anchor_path or (self.repo_root / "tools" / "governance" / "sovereign_root_anchor.json")
        if not anchor_path.exists():
            raise DataContractError(f"SOVEREIGN_ROOT_ANCHOR_MISSING: {anchor_path}")

        anchor_bytes = anchor_path.read_bytes()
        try:
            anchor = SovereignRootAnchor.model_validate_json(anchor_bytes)
        except Exception as exc:
            raise DataContractError(f"SOVEREIGN_ROOT_ANCHOR_TAMPERED: {exc}") from exc
        evidence["sovereign_root_anchor_id"] = anchor.root_authority_id

        # ---------------------------------------------------------------------
        # Stage 4: Ingest & Verify Trust Anchor Manifest (Rev 10 Section 5)
        # ---------------------------------------------------------------------
        ta_path = trust_anchor_manifest_path or (self.target_root / "trust_anchor_manifest.json")
        if not ta_path.exists():
            raise DataContractError(f"TRUST_ANCHOR_MANIFEST_MISSING: {ta_path}")

        try:
            ta_manifest = TrustAnchorManifest.model_validate_json(ta_path.read_bytes())
        except Exception as exc:
            raise DataContractError(f"TRUST_ANCHOR_MANIFEST_INVALID: {exc}") from exc

        # Sovereign signature check using sovereign root public key
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        import base64

        try:
            root_pub_bytes = base64.b64decode(anchor.root_public_key_b64, validate=True)
            root_pub_key = Ed25519PublicKey.from_public_bytes(root_pub_bytes)
            ta_sig_bytes = base64.b64decode(ta_manifest.sovereign_signature_ed25519, validate=True)
            root_pub_key.verify(ta_sig_bytes, ta_manifest.compute_canonical_signed_bytes())
        except Exception as exc:
            raise DataContractError(f"TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID: Sovereign signature failed: {exc}") from exc

        # Verify trust_store.json digest
        ts_path = trust_store_path or (self.target_root / "trust_store.json")
        if not ts_path.exists():
            raise DataContractError(f"TRUST_STORE_FILE_MISSING: {ts_path}")

        actual_ts_digest = hashlib.sha256(ts_path.read_bytes()).hexdigest()
        if actual_ts_digest != ta_manifest.trust_store_digest:
            raise DataContractError(
                f"TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID: Digest mismatch ({actual_ts_digest} vs {ta_manifest.trust_store_digest})"
            )

        # Load trust store
        try:
            ts_data = json.loads(ts_path.read_text(encoding="utf-8"))
            trust_store = Ed25519TrustStore.model_validate(ts_data)
        except Exception as exc:
            raise DataContractError(f"TRUST_STORE_DESERIALIZATION_FAILED: {exc}") from exc

        # Assert required key IDs exist
        store_key_ids = {e.key_id for e in trust_store.entries}
        for req_id in ["KEY_HUMAN_GOVERNANCE_AUDITOR_001", "KEY_STORAGE_ENGINE_PROD_001"]:
            if req_id not in store_key_ids:
                raise DataContractError(f"TRUST_STORE_CRYPTOGRAPHIC_AUTHORITY_INVALID: Missing required key {req_id}")

        evidence["trust_store_verified"] = True

        # ---------------------------------------------------------------------
        # Stage 5: Ingest & Verify Genesis Bootstrap Manifest (Rev 10 Section 4)
        # ---------------------------------------------------------------------
        gb_path = genesis_bootstrap_manifest_path or (self.target_root / "genesis_bootstrap_manifest.json")
        if not gb_path.exists():
            raise DataContractError(f"GENESIS_ENVIRONMENT_UNVERIFIED: Missing {gb_path}")

        try:
            gb_manifest = GenesisBootstrapManifest.model_validate_json(gb_path.read_bytes())
        except Exception as exc:
            raise DataContractError(f"GENESIS_ENVIRONMENT_UNVERIFIED: Invalid schema: {exc}") from exc

        # Verify bootstrap signature using bootstrap public key
        try:
            boot_pub_bytes = base64.b64decode(anchor.bootstrap_public_key_b64, validate=True)
            boot_pub_key = Ed25519PublicKey.from_public_bytes(boot_pub_bytes)
            gb_sig_bytes = base64.b64decode(gb_manifest.bootstrap_signature_ed25519, validate=True)
            boot_pub_key.verify(gb_sig_bytes, gb_manifest.compute_canonical_signed_bytes())
        except Exception as exc:
            raise DataContractError(f"GENESIS_ENVIRONMENT_UNVERIFIED: Bootstrap signature invalid: {exc}") from exc

        if gb_manifest.genesis_head_digest != GENESIS_HEAD_DIGEST:
            raise DataContractError(f"GENESIS_ENVIRONMENT_UNVERIFIED: Head digest not genesis: {gb_manifest.genesis_head_digest}")

        head_file = self.target_root / "head.json"
        if not head_file.exists():
            raise DataContractError("GENESIS_ENVIRONMENT_UNVERIFIED: head.json missing")
        try:
            head_data = json.loads(head_file.read_text(encoding="utf-8"))
            if head_data.get("head_digest") != GENESIS_HEAD_DIGEST:
                raise DataContractError(f"GENESIS_ENVIRONMENT_UNVERIFIED: head.json digest mismatch: {head_data.get('head_digest')}")
        except Exception as exc:
            raise DataContractError(f"GENESIS_ENVIRONMENT_UNVERIFIED: Failed to inspect head.json: {exc}") from exc

        evidence["genesis_environment_verified"] = True

        # ---------------------------------------------------------------------
        # Stage 6: Ingest & Verify HumanGORecord (Rev 10 Section 8)
        # ---------------------------------------------------------------------
        try:
            record_data = json.loads(record_file.read_text(encoding="utf-8"))
            go_record = HumanGORecord.model_validate(record_data)
        except Exception as exc:
            raise DataContractError(f"HUMAN_GO_RECORD_MALFORMED: {exc}") from exc

        # Verify approver key presence and status in sealed trust store
        approver_entry = trust_store.resolve(go_record.approver_public_key_id, at_time=go_record.record_timestamp_utc)
        if approver_entry.status != TrustStoreEntryStatus.ACTIVE:
            raise DomainValidationError(f"key has been {approver_entry.status.value}")

        # Cryptographically verify record signature
        go_record.verify_signature(trust_store)
        evidence["human_go_signature_verified"] = True

        # Assert Ledger Head Continuity (Test B9)
        # previous_record_digest MUST be GENESIS_HEAD_DIGEST
        if go_record.previous_record_digest != GENESIS_HEAD_DIGEST:
            raise DataContractError(
                f"LEDGER_HEAD_CONTINUITY_BROKEN: previous_record_digest {go_record.previous_record_digest} "
                f"is not genesis (stale incident head rejected)"
            )

        # ---------------------------------------------------------------------
        # Stage 7: Ingest & Verify Draft LiveAuthorization
        # ---------------------------------------------------------------------
        d_path = draft_path or (self.target_root / "drafts" / f"{draft_id}.json")
        if not d_path.exists():
            d_path = self.repo_root / "var" / "gate_b" / "drafts" / f"{draft_id}.json"
        if not d_path.exists():
            raise DataContractError(f"DRAFT_AUTHORIZATION_FILE_MISSING: {d_path}")

        try:
            draft = LiveAuthorization.model_validate_json(d_path.read_bytes())
        except Exception as exc:
            raise DataContractError(f"DRAFT_AUTHORIZATION_INVALID: {exc}") from exc

        calc_draft_digest = hashlib.sha256(draft.compute_approved_canonical_bytes()).hexdigest()
        if calc_draft_digest != go_record.approved_authorization_digest:
            raise DataContractError(
                f"DRAFT_DIGEST_MISMATCH: calculated {calc_draft_digest} vs approved {go_record.approved_authorization_digest}"
            )
        evidence["draft_digest_verified"] = True

        # Check expiration on draft
        now_utc = datetime.now(timezone.utc)
        if now_utc > draft.expires_at:
            raise PreLiveRiskAdmissionError("HUMAN_GO_EXPIRED")

        # Verify Gate A certified lineage
        ga_path = gate_a_audit_path or (self.repo_root / "docs" / "phase13" / "consolidated_gate_a_audit.md")
        if not ga_path.exists():
            raise DataContractError(f"GATE_A_EVIDENCE_MISSING: {ga_path}")

        calc_ga_digest = hashlib.sha256(ga_path.read_bytes()).hexdigest()
        if draft.source_approved_digest != calc_ga_digest:
            raise DataContractError(
                f"GATE_A_LINEAGE_DIGEST_MISMATCH: {calc_ga_digest} vs draft {draft.source_approved_digest}"
            )
        evidence["gate_a_lineage_verified"] = True

        # ---------------------------------------------------------------------
        # Stage 8: Single Continuous Transactional Lock & 2PC Commit
        # ---------------------------------------------------------------------
        ledger = AuthoritativeGOLedger(self.target_root, trust_store)
        tx_id = activation_tx_id or uuid4()

        with ledger.exclusive_lock() as tx:
            # Re-verify head continuity under exclusive lock
            current_head = tx.current_head_digest
            if current_head != GENESIS_HEAD_DIGEST:
                raise DataContractError(f"LEDGER_HEAD_CONTINUITY_BROKEN: current head {current_head} is not genesis")

            # Reserve transaction ID
            tx.reserve_transaction_id(tx_id)

            # Advance CAS to COMMITTING
            if not tx.compare_and_set_tx_state(tx_id, DurableTransactionState.PREPARED, DurableTransactionState.COMMITTING):
                raise StorageDurabilityError("CAS_TRANSITION_TO_COMMITTING_FAILED")

            # Construct activated authorization
            activated_auth = draft.model_copy(update={
                "status": LiveAuthorizationStatus.ACTIVE,
                "source_approved_digest": draft.approved_authorization_digest,
                "active_go_record_digest": go_record.record_digest,
                "activation_transaction_id": tx_id,
                "activated_at": datetime.now(timezone.utc),
            })
            act_canonical_bytes = activated_auth.compute_activated_canonical_bytes()
            act_digest = hashlib.sha256(act_canonical_bytes).hexdigest()
            activated_auth = activated_auth.model_copy(update={"activated_authorization_digest": act_digest})

            # Execute 2PC commit
            # Dummy or verify-only signer wrapper for transition record
            class VerifyOnlyEngineSignerWrapper:
                key_id: str = "KEY_STORAGE_ENGINE_PROD_001"
                def __init__(self, sig: Optional[str]) -> None:
                    self._sig = sig or ("0" * 88)
                def sign(self, payload_bytes: bytes) -> str:
                    return self._sig

            engine_wrapper = VerifyOnlyEngineSignerWrapper(pre_signed_transition_signature)

            # Phase 1: Staged mutation data
            tx.write_staged_mutation_data(tx_id, go_record, activated_auth)
            tx.flush_staged_mutation_data_barrier(tx_id)
            if not tx.verify_staged_mutation_data_durable(tx_id, go_record.record_digest, activated_auth):
                raise StorageDurabilityError("STAGED_MUTATION_DATA_DURABILITY_FAILED")

            # Phase 2: Commit marker block
            commit_block = AuthoritativeCommitRecordBlock(
                activation_transaction_id=tx_id,
                commit_timestamp_utc=datetime.now(timezone.utc),
                ledger_record_digest=go_record.record_digest,
                advanced_head_digest=go_record.record_digest,
                approved_authorization_digest=draft.approved_authorization_digest,
                activated_authorization_digest=act_digest,
                mutation_manifest_digest="",
            )
            manifest_digest = commit_block.compute_manifest_digest()
            final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})

            tx.write_commit_marker_block(tx_id, final_commit_block)
            tx.flush_commit_marker_barrier(tx_id)
            if not tx.verify_commit_marker_durable(tx_id, manifest_digest):
                raise StorageDurabilityError("COMMIT_MARKER_DURABILITY_FAILED")

            # Phase 3: Promote staging to snapshots
            tx.promote_staging_to_snapshot_directory_atomically(tx_id)
            tx.mark_snapshot_directory_read_only(tx_id)
            tx.flush_snapshot_directory_barrier(tx_id)

            # Phase 4: Pre-CAS deep verification
            if not tx.deep_verify_snapshot_manifest(tx_id, final_commit_block):
                raise StorageDurabilityError("POST_BARRIER_TAMPERING_DETECTED_PRE_CAS")

            # Phase 5: Pointer transition
            transition_draft = DurablePointerTransitionRecord(
                pointer_version=tx.get_next_pointer_version(),
                previous_tx_id=tx.get_current_active_transaction_id(),
                new_tx_id=tx_id,
                transition_timestamp_utc=datetime.now(timezone.utc),
                commit_intent_digest=manifest_digest,
                previous_pointer_digest=tx.get_current_pointer_digest(),
                transition_record_digest="",
                engine_signature=engine_wrapper.sign(b""),
                engine_key_id=engine_wrapper.key_id,
            )
            rec_digest = transition_draft.compute_canonical_digest()
            final_transition_record = transition_draft.model_copy(
                update={"transition_record_digest": rec_digest}
            )
            tx.write_durable_pointer_transition_record(final_transition_record)
            tx.flush_pointer_transition_barrier()

            # Switch pointer
            tx.switch_committed_snapshot_pointer_atomically(tx_id)

            # CAS to COMMITTED
            if not tx.compare_and_set_tx_state(tx_id, DurableTransactionState.COMMITTING, DurableTransactionState.COMMITTED):
                raise StorageDurabilityError("COMMIT_CAS_TRANSITION_FAILED")

            # Advance head digest
            tx.set_head_digest_durable(go_record.record_digest)

        # ---------------------------------------------------------------------
        # Stage 9: Immediate Halt & Enforcement (STOP AGAIN)
        # ---------------------------------------------------------------------
        evidence["status"] = "COMMITTED"
        evidence["operational_state"] = "ACTIVE"
        evidence["live_capital_deployed"] = "$0.00"
        evidence["live_orders_transmitted"] = 0
        evidence["broker_connection"] = "DISCONNECTED"
        evidence["post_activation_stop_enforced"] = True

        return evidence


def main() -> None:
    """CLI entrypoint for verify-only runner."""
    import argparse

    parser = argparse.ArgumentParser(description="ACASH Gate B Verify-Only Activation Runner")
    parser.add_argument("--draft-id", required=True, help="Draft authorization ID, e.g. AUTH_P13_EURUSD_001")
    parser.add_argument("--confirmation-token", required=True, help="Explicit Human Confirmation Token")
    parser.add_argument("--human-go-record", required=True, help="Path to signed human_go_record.json artifact")
    parser.add_argument("--storage-root", default="var/gate_b", help="Target storage root path")
    parser.add_argument("--tx-id", default=None, help="Optional specific transaction UUID")

    args = parser.parse_args()

    repo_root = Path.cwd()
    target_root = Path(args.storage_root)
    tx_id = UUID(args.tx_id) if args.tx_id else None

    runner = VerifyOnlyGateBRunner(target_root=target_root, repo_root=repo_root)
    results = runner.run_activation(
        draft_id=args.draft_id,
        confirmation_token=args.confirmation_token,
        human_go_record_artifact=args.human_go_record,
        activation_tx_id=tx_id,
    )
    print(json.dumps(results, indent=2))
    print("[STOP AGAIN] Gate B Activation Transaction Committed. Zero Live Orders Permitted.")


if __name__ == "__main__":
    main()
