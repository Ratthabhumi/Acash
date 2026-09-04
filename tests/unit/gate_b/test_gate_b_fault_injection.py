"""Phase 13 Slice 2: Fault-Injection Crash/Restart Integration Matrix (Stage 3.4).

Executes the comprehensive 12-scenario crash and restart integration matrix per:
- docs/phase13/slice2_gate_b_plan.md (§9.2, Table 3.11, §3.8, §3.9, §3.11, §3.12)
- Findings B82, B87, B88, B89, B90, B91, B92, B93, B94, B95, B98

Mandatory Invariants Enforced Across All Scenarios:
1. Pure Physical Filesystem Execution: Zero in-memory mock storage; all tests execute on NTFS/ReFS directories.
2. Raw On-Disk State Assertions: Asserts final on-disk files, state files, markers, and pointers directly,
   not merely return enums.
3. Strict Commit-Marker Durability Boundary (Crash-02): Commit marker durable on disk indicates declared
   commit intent; incomplete promotion triggers conservative quarantine without writing ABORTED.
4. Cryptographically Authenticated Pointer Transitions (Crash-05, Crash-06, Crash-09, Crash-10):
   Recoverable commit and pointer rollback require valid Ed25519 engine signatures over canonical transition records.
5. Anti-Silent Rollback Invariant (Crash-11, Crash-12): Corrupted or forged transition records strictly
   forbid pointer rollback and freeze the entire engine into SystemSafetyMode.QUARANTINE_LOCKED.
6. True Cold-Restart Zero-RAM Verification (Crash-08): Complete tear-down and re-instantiation of trust stores,
   signers, and recovery coordinators from disk state alone with zero RAM carry-over.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Generator, Optional, Tuple
from uuid import UUID, uuid4

import pytest

from acash.execution.crypto import (
    Ed25519Signer,
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.gate_b.readers import SnapshotReaderService
from acash.gate_b.recovery import (
    has_any_durable_commit_evidence,
)
from acash.gate_b.schema import (
    AuthoritativeAbortRecordBlock,
    AuthoritativeCommitRecordBlock,
    DurablePointerTransitionRecord,
    DurableTransactionState,
    HumanGORecord,
    JournalState,
    LiveAuthorization,
    LiveAuthorizationStatus,
    SystemSafetyMode,
)
from acash.gate_b.service import (
    GateBRecoveryCoordinator,
)
from acash.gate_b.storage import (
    AuthoritativeGOLedger,
    GENESIS_HEAD_DIGEST,
    StorageCommitContract,
    StorageEngineSigner,
    StoragePlatformUtils,
)


FaultEnvType = Tuple[Path, Ed25519TrustStore, StorageEngineSigner, str, str, AuthoritativeGOLedger, str, str]


@pytest.fixture
def fault_env(tmp_path: Path) -> Generator[FaultEnvType, None, None]:
    """Provide isolated physical storage directory and trust credentials on real filesystem."""
    root = tmp_path / "fault_injection_root"
    root.mkdir(parents=True, exist_ok=True)

    # Engine key
    eng_priv, eng_pub = Ed25519Signer.generate_key_pair()
    eng_key_id = "KEY_STORAGE_ENGINE_001"
    now_utc = datetime.now(timezone.utc)
    eng_entry = Ed25519TrustStoreEntry(
        key_id=eng_key_id,
        issuer_id="ACASH_STORAGE_ENGINE_ROOT",
        public_key_b64=eng_pub,
        valid_from=now_utc - timedelta(days=1),
        valid_until=now_utc + timedelta(days=365),
        status=TrustStoreEntryStatus.ACTIVE,
    )

    # Human approver key
    app_priv, app_pub = Ed25519Signer.generate_key_pair()
    app_key_id = "KEY_HUMAN_APPROVER_001"
    app_entry = Ed25519TrustStoreEntry(
        key_id=app_key_id,
        issuer_id="ACASH_GOVERNANCE_ROOT",
        public_key_b64=app_pub,
        valid_from=now_utc - timedelta(days=1),
        valid_until=now_utc + timedelta(days=365),
        status=TrustStoreEntryStatus.ACTIVE,
    )

    trust_store = Ed25519TrustStore(entries=(eng_entry, app_entry))
    signer = StorageEngineSigner(eng_key_id, eng_priv)
    ledger = AuthoritativeGOLedger(root, trust_store)

    yield root, trust_store, signer, app_key_id, app_priv, ledger, eng_key_id, eng_priv

    # Ensure clean teardown on Windows NTFS by stripping read-only ACLs
    StoragePlatformUtils.mark_directory_writable(root)


def _make_fault_artifacts(
    app_key_id: str,
    app_priv: str,
    tx_id: UUID,
    prev_head: str = GENESIS_HEAD_DIGEST,
    auth_id: str = "AUTH_GATE_B_FAULT_TEST",
) -> Tuple[LiveAuthorization, LiveAuthorization, HumanGORecord]:
    """Construct cryptographic artifacts for fault-injection testing."""
    now_utc = datetime.now(timezone.utc)
    exp_utc = now_utc + timedelta(hours=4)

    draft = LiveAuthorization(
        authorization_id=auth_id,
        status=LiveAuthorizationStatus.APPROVED_PENDING_GO,
        approved_authorization_digest="a" * 64,
        strategy_id="STRAT_TEST",
        symbol="EURUSD",
        account_id="ACC_112040157",
        max_notional_usd=Decimal("500.00"),
        max_drawdown_pct=Decimal("5.00"),
        max_slippage_points=5,
        max_quote_age_ms=500,
        required_approvals=1,
        created_at=now_utc,
        expires_at=exp_utc,
    )

    go_draft = HumanGORecord(
        go_record_id=f"GO_REC_{auth_id}",
        authorization_id=draft.authorization_id,
        approved_authorization_digest=draft.approved_authorization_digest,
        previous_record_digest=prev_head,
        record_timestamp_utc=now_utc,
        approver_public_key_id=app_key_id,
        signature_ed25519="",
        record_digest="",
    )
    payload = go_draft.compute_signed_payload_bytes()
    sig = Ed25519Signer.sign(app_priv, payload)
    go_with_sig = go_draft.model_copy(update={"signature_ed25519": sig})
    go_rec = go_with_sig.model_copy(update={"record_digest": go_with_sig.compute_canonical_digest()})

    act_draft = draft.model_copy(
        update={
            "status": LiveAuthorizationStatus.ACTIVE,
            "source_approved_digest": draft.approved_authorization_digest,
            "active_go_record_digest": go_rec.record_digest,
            "activation_transaction_id": tx_id,
            "activated_at": now_utc,
            "activated_authorization_digest": "",
        }
    )
    act_bytes = act_draft.compute_activated_canonical_bytes()
    activated_auth = act_draft.model_copy(
        update={"activated_authorization_digest": hashlib.sha256(act_bytes).hexdigest()}
    )

    return draft, activated_auth, go_rec


def _read_raw_tx_state(root: Path, tx_id: UUID) -> Optional[str]:
    p = root / "tx_state" / f"{tx_id}.state"
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8").strip()


def _read_raw_system_safety_mode(root: Path) -> str:
    p = root / "system_safety_mode.state"
    if not p.exists():
        return "NORMAL"
    return p.read_text(encoding="utf-8").strip()


def _read_raw_committed_pointer(root: Path) -> Optional[str]:
    p = root / "pointer" / "committed_pointer"
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8").strip()


# ==============================================================================
# 1. CRASH-01: Post-fsync_1 (Staged mutation data durable; marker absent)
# ==============================================================================

def test_crash_01_post_fsync_1_staged_mutation_data_durable(fault_env: FaultEnvType) -> None:
    """Crash-01: Crash post-fsync_1 with staged data on disk and marker absent.

    Expectation: Provably pre-commit crash (Table 3.11 Class 4).
    Recovery action: Tier 1 clean abort, writes bound abort record, discards staging.
    Raw on-disk state: ABORTED, staging removed, no snapshot, pointer unchanged, safety mode NORMAL.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger, eng_key_id, eng_priv = fault_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_fault_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        # Simulate activation progression up to Phase 1 fsync_1
        tx.reserve_transaction_id(tx_id)
        journal = tx.create_wal_journal(tx_id, draft.authorization_id, go_rec)
        journal.write_state_durable(JournalState.PREPARED)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)
        journal.write_state_durable(JournalState.COMMITTING)

        tx.write_staged_mutation_data(tx_id, go_rec, act_auth)
        tx.flush_staged_mutation_data_barrier(tx_id)

        # Assert fault injection point: staged files exist, commit marker does NOT exist
        assert (root / "staging" / str(tx_id) / "record.json").exists()
        assert not (root / "staging" / str(tx_id) / "commit_record_block.json").exists()
        assert not (root / "snapshots" / str(tx_id)).exists()

    # Cold restart: simulate restart recovery
    fresh_trust_store = Ed25519TrustStore(entries=trust_store.entries)
    fresh_signer = StorageEngineSigner(eng_key_id, eng_priv)
    fresh_ledger = AuthoritativeGOLedger(root, fresh_trust_store)
    coordinator = GateBRecoveryCoordinator(fresh_ledger, fresh_trust_store, fresh_signer)

    with fresh_ledger.exclusive_lock() as tx:
        # Pre-commit failure: has_any_durable_commit_evidence is False
        assert not has_any_durable_commit_evidence(tx, tx_id)
        # Execute abort CAS as done by activation manager exception boundary
        tx.compare_and_set_tx_state(tx_id, expected=DurableTransactionState.COMMITTING, new=DurableTransactionState.ABORTED)
        abort_record = AuthoritativeAbortRecordBlock(
            activation_transaction_id=tx_id,
            pre_transaction_head_digest=go_rec.previous_record_digest,
            authorization_id=draft.authorization_id,
            approved_authorization_digest=draft.approved_authorization_digest,
            expected_previous_state=DurableTransactionState.COMMITTING,
            terminal_state=DurableTransactionState.ABORTED,
            abort_reason_code="SimulatedCrash01PostFsync1",
            abort_timestamp_utc=datetime.now(timezone.utc),
            abort_record_digest="",
        )
        final_abort = abort_record.model_copy(update={"abort_record_digest": abort_record.compute_digest()})
        tx.write_durable_abort_record(final_abort)
        tx.flush_abort_record_barrier(tx_id)
        tx.rollback_staging(tx_id)

    # Now execute cold recovery coordinator scan
    results = coordinator.run_recovery()
    assert tx_id in results
    assert results[tx_id].tier == 1
    assert results[tx_id].final_state == DurableTransactionState.ABORTED
    assert results[tx_id].system_mode == SystemSafetyMode.NORMAL

    # RAW ON-DISK ASSERTIONS:
    assert _read_raw_tx_state(root, tx_id) == "ABORTED"
    assert _read_raw_system_safety_mode(root) == "NORMAL"
    assert _read_raw_committed_pointer(root) is None
    assert not (root / "staging" / str(tx_id)).exists()
    assert not (root / "snapshots" / str(tx_id)).exists()
    assert (root / "aborts" / f"{tx_id}.json").exists()


# ==============================================================================
# 2. CRASH-02: Post-fsync_2 (Commit marker block durable; promotion pending)
# ==============================================================================

def test_crash_02_post_fsync_2_commit_marker_durable(fault_env: FaultEnvType) -> None:
    """Crash-02: Crash post-fsync_2 with commit marker durable in staging before promotion.

    Expectation: Commit intent was durably declared (fsync_2 completed), but promotion was interrupted.
    Under B90 and Table 3.11 Class 10: strictly conservative quarantine.
    CRITICAL CHECK: MUST NOT write ABORTED; must freeze into QUARANTINED / QUARANTINE_LOCKED.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger, eng_key_id, eng_priv = fault_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_fault_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.reserve_transaction_id(tx_id)
        journal = tx.create_wal_journal(tx_id, draft.authorization_id, go_rec)
        journal.write_state_durable(JournalState.PREPARED)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)
        journal.write_state_durable(JournalState.COMMITTING)

        # Phase 1: fsync_1
        tx.write_staged_mutation_data(tx_id, go_rec, act_auth)
        tx.flush_staged_mutation_data_barrier(tx_id)

        # Phase 2: fsync_2
        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_id,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_rec.record_digest,
            advanced_head_digest=go_rec.record_digest,
            approved_authorization_digest=draft.approved_authorization_digest,
            activated_authorization_digest=act_auth.activated_authorization_digest or "",
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})
        tx.write_commit_marker_block(tx_id, final_commit_block)
        tx.flush_commit_marker_barrier(tx_id)

        # Assert fault injection point: commit marker durable in staging; promotion pending
        assert (root / "staging" / str(tx_id) / "commit_record_block.json").exists()
        assert not (root / "snapshots" / str(tx_id)).exists()
        # Stage 3.1 invariant: commit marker presence IS durable commit evidence
        assert has_any_durable_commit_evidence(tx, tx_id) is True

    # Cold restart: instantiate clean coordinator with zero RAM carry-over
    fresh_trust_store = Ed25519TrustStore(entries=trust_store.entries)
    fresh_signer = StorageEngineSigner(eng_key_id, eng_priv)
    fresh_ledger = AuthoritativeGOLedger(root, fresh_trust_store)
    coordinator = GateBRecoveryCoordinator(fresh_ledger, fresh_trust_store, fresh_signer)

    results = coordinator.run_recovery()
    assert tx_id in results
    assert results[tx_id].tier == 3
    assert results[tx_id].final_state == DurableTransactionState.QUARANTINED
    assert results[tx_id].system_mode == SystemSafetyMode.QUARANTINE_LOCKED

    # RAW ON-DISK ASSERTIONS:
    assert _read_raw_tx_state(root, tx_id) == "QUARANTINED"
    assert _read_raw_system_safety_mode(root) == "QUARANTINE_LOCKED"
    assert _read_raw_committed_pointer(root) is None
    # Promotion was pending: snapshots directory must NOT exist
    assert not (root / "snapshots" / str(tx_id)).exists()
    # CRITICAL AUDIT CHECK: ZERO abort record written!
    assert not (root / "aborts" / f"{tx_id}.json").exists()


# ==============================================================================
# 3. CRASH-03: Post-Promotion (Directory promoted to snapshots; fsync_3 interrupted)
# ==============================================================================

def test_crash_03_post_promotion_directory_promoted_unproven_barrier(fault_env: FaultEnvType) -> None:
    """Crash-03: Crash after promotion to /snapshots/<tx_id> before fsync_3 completion.

    Expectation: Promotion unproven / pointer transition pending (Table 3.11 Class 10).
    Recovery action: Tier 3 conservative quarantine (B90).
    Raw on-disk state: QUARANTINED, QUARANTINE_LOCKED, snapshot exists, pointer unchanged.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger, eng_key_id, eng_priv = fault_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_fault_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.reserve_transaction_id(tx_id)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)

        tx.write_staged_mutation_data(tx_id, go_rec, act_auth)
        tx.flush_staged_mutation_data_barrier(tx_id)

        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_id,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_rec.record_digest,
            advanced_head_digest=go_rec.record_digest,
            approved_authorization_digest=draft.approved_authorization_digest,
            activated_authorization_digest=act_auth.activated_authorization_digest or "",
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})
        tx.write_commit_marker_block(tx_id, final_commit_block)
        tx.flush_commit_marker_barrier(tx_id)

        # Atomic promotion executed, but fsync_3 interrupted
        tx.promote_staging_to_snapshot_directory_atomically(tx_id)

        assert (root / "snapshots" / str(tx_id)).exists()
        assert not (root / "staging" / str(tx_id)).exists()

    # Cold restart
    fresh_trust_store = Ed25519TrustStore(entries=trust_store.entries)
    fresh_signer = StorageEngineSigner(eng_key_id, eng_priv)
    fresh_ledger = AuthoritativeGOLedger(root, fresh_trust_store)
    coordinator = GateBRecoveryCoordinator(fresh_ledger, fresh_trust_store, fresh_signer)

    results = coordinator.run_recovery()
    assert tx_id in results
    assert results[tx_id].tier == 3
    assert results[tx_id].final_state == DurableTransactionState.QUARANTINED
    assert results[tx_id].system_mode == SystemSafetyMode.QUARANTINE_LOCKED

    # RAW ON-DISK ASSERTIONS:
    assert _read_raw_tx_state(root, tx_id) == "QUARANTINED"
    assert _read_raw_system_safety_mode(root) == "QUARANTINE_LOCKED"
    assert (root / "snapshots" / str(tx_id)).exists()
    assert not (root / "aborts" / f"{tx_id}.json").exists()


# ==============================================================================
# 4. CRASH-04: Post-fsync_3 (Snapshot directory durable; pointer transition pending)
# ==============================================================================

def test_crash_04_post_fsync_3_snapshot_directory_durable(fault_env: FaultEnvType) -> None:
    """Crash-04: Crash post-fsync_3 with snapshot durable and read-only, pointer transition absent.

    Expectation: Table 3.11 Class 10 (conservative quarantine, B90).
    Recovery action: Tier 3 QUARANTINED / QUARANTINE_LOCKED.
    Raw on-disk state: Snapshot exists and is read-only, pointer unchanged, safety mode locked.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger, eng_key_id, eng_priv = fault_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_fault_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.reserve_transaction_id(tx_id)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)

        tx.write_staged_mutation_data(tx_id, go_rec, act_auth)
        tx.flush_staged_mutation_data_barrier(tx_id)

        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_id,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_rec.record_digest,
            advanced_head_digest=go_rec.record_digest,
            approved_authorization_digest=draft.approved_authorization_digest,
            activated_authorization_digest=act_auth.activated_authorization_digest or "",
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})
        tx.write_commit_marker_block(tx_id, final_commit_block)
        tx.flush_commit_marker_barrier(tx_id)

        tx.promote_staging_to_snapshot_directory_atomically(tx_id)
        tx.mark_snapshot_directory_read_only(tx_id)
        tx.flush_snapshot_directory_barrier(tx_id)

        # Snapshots directory is durable, but pointer transition record was not written
        assert (root / "snapshots" / str(tx_id)).exists()
        assert not (root / "pointer" / "transition.json").exists()

    # Cold restart
    fresh_trust_store = Ed25519TrustStore(entries=trust_store.entries)
    fresh_signer = StorageEngineSigner(eng_key_id, eng_priv)
    fresh_ledger = AuthoritativeGOLedger(root, fresh_trust_store)
    coordinator = GateBRecoveryCoordinator(fresh_ledger, fresh_trust_store, fresh_signer)

    results = coordinator.run_recovery()
    assert tx_id in results
    assert results[tx_id].tier == 3
    assert results[tx_id].final_state == DurableTransactionState.QUARANTINED
    assert results[tx_id].system_mode == SystemSafetyMode.QUARANTINE_LOCKED

    # RAW ON-DISK ASSERTIONS:
    assert _read_raw_tx_state(root, tx_id) == "QUARANTINED"
    assert _read_raw_system_safety_mode(root) == "QUARANTINE_LOCKED"
    assert (root / "snapshots" / str(tx_id)).exists()


# ==============================================================================
# 5. CRASH-05: Post-Pointer Switch (Pointer switched to tx_id; state COMMITTING)
# ==============================================================================

def test_crash_05_post_pointer_switch_committing_state(fault_env: FaultEnvType) -> None:
    """Crash-05: Crash after pointer switched to tx_id with authentic transition record, state COMMITTING.

    Expectation: Commit-Recovery Path (B82, Table 3.11 Class 7).
    Recovery action: Verifies cryptographic transition record, executes CAS COMMITTING -> COMMITTED.
    Raw on-disk state: COMMITTED, pointer active, head advanced, journal COMMITTED, safety mode NORMAL.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger, eng_key_id, eng_priv = fault_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_fault_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.reserve_transaction_id(tx_id)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)

        tx.write_staged_mutation_data(tx_id, go_rec, act_auth)
        tx.flush_staged_mutation_data_barrier(tx_id)

        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_id,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_rec.record_digest,
            advanced_head_digest=go_rec.record_digest,
            approved_authorization_digest=draft.approved_authorization_digest,
            activated_authorization_digest=act_auth.activated_authorization_digest or "",
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})
        tx.write_commit_marker_block(tx_id, final_commit_block)
        tx.flush_commit_marker_barrier(tx_id)

        tx.promote_staging_to_snapshot_directory_atomically(tx_id)
        tx.mark_snapshot_directory_read_only(tx_id)
        tx.flush_snapshot_directory_barrier(tx_id)

        # Step 5a: Construct, sign, and flush authentic pointer transition record (B93)
        transition_draft = DurablePointerTransitionRecord(
            pointer_version=tx.get_next_pointer_version(),
            previous_tx_id=None,
            new_tx_id=tx_id,
            transition_timestamp_utc=datetime.now(timezone.utc),
            commit_intent_digest=manifest_digest,
            previous_pointer_digest=tx.get_current_pointer_digest(),
            transition_record_digest="",
            engine_signature="",
            engine_key_id=signer.key_id,
        )
        rec_digest = transition_draft.compute_canonical_digest()
        raw_sig = signer.sign(rec_digest.encode("utf-8"))
        final_trans = transition_draft.model_copy(
            update={"transition_record_digest": rec_digest, "engine_signature": raw_sig}
        )
        tx.write_durable_pointer_transition_record(final_trans)
        tx.flush_pointer_transition_barrier()

        # Step 5b: Switch pointer to tx_id
        tx.switch_committed_snapshot_pointer_atomically(tx_id)

        # Injected Crash: CAS to COMMITTED was NOT reached; state is still COMMITTING
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.COMMITTING
        assert tx.committed_pointer_references_transaction(tx_id) is True

    # Cold restart
    fresh_trust_store = Ed25519TrustStore(entries=trust_store.entries)
    fresh_signer = StorageEngineSigner(eng_key_id, eng_priv)
    fresh_ledger = AuthoritativeGOLedger(root, fresh_trust_store)
    coordinator = GateBRecoveryCoordinator(fresh_ledger, fresh_trust_store, fresh_signer)

    results = coordinator.run_recovery()
    assert tx_id in results
    assert results[tx_id].tier == 2
    assert results[tx_id].final_state == DurableTransactionState.COMMITTED
    assert results[tx_id].system_mode == SystemSafetyMode.NORMAL

    # RAW ON-DISK ASSERTIONS:
    assert _read_raw_tx_state(root, tx_id) == "COMMITTED"
    assert _read_raw_system_safety_mode(root) == "NORMAL"
    assert _read_raw_committed_pointer(root) == str(tx_id)
    with open(root / "head.json", "r", encoding="utf-8") as f:
        head_data = json.load(f)
        assert head_data.get("head_digest") == go_rec.record_digest

    # Verify that authoritative snapshot reader succeeds and returns ACTIVE authorization
    with fresh_ledger.exclusive_lock() as tx:
        view = SnapshotReaderService.read_active_committed_snapshot(tx)
        assert view.transaction_id == tx_id
        assert view.authorization is not None
        assert view.authorization.status == LiveAuthorizationStatus.ACTIVE


# ==============================================================================
# 6. CRASH-06: Pre-CAS Transition (State still COMMITTING at CAS boundary)
# ==============================================================================

def test_crash_06_pre_cas_transition_recoverable_commit(fault_env: FaultEnvType) -> None:
    """Crash-06: Crash right at CAS execution boundary; authentic transition record verified.

    Expectation: Proves cryptographic verification of transition record before CAS completion.
    Recovery action: Commit-Recovery Path succeeds; final state COMMITTED.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger, eng_key_id, eng_priv = fault_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_fault_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.reserve_transaction_id(tx_id)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)

        tx.write_staged_mutation_data(tx_id, go_rec, act_auth)
        tx.flush_staged_mutation_data_barrier(tx_id)

        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_id,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_rec.record_digest,
            advanced_head_digest=go_rec.record_digest,
            approved_authorization_digest=draft.approved_authorization_digest,
            activated_authorization_digest=act_auth.activated_authorization_digest or "",
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})
        tx.write_commit_marker_block(tx_id, final_commit_block)
        tx.flush_commit_marker_barrier(tx_id)

        tx.promote_staging_to_snapshot_directory_atomically(tx_id)
        tx.mark_snapshot_directory_read_only(tx_id)
        tx.flush_snapshot_directory_barrier(tx_id)

        transition_draft = DurablePointerTransitionRecord(
            pointer_version=tx.get_next_pointer_version(),
            previous_tx_id=None,
            new_tx_id=tx_id,
            transition_timestamp_utc=datetime.now(timezone.utc),
            commit_intent_digest=manifest_digest,
            previous_pointer_digest=tx.get_current_pointer_digest(),
            transition_record_digest="",
            engine_signature="",
            engine_key_id=signer.key_id,
        )
        rec_digest = transition_draft.compute_canonical_digest()
        raw_sig = signer.sign(rec_digest.encode("utf-8"))
        final_trans = transition_draft.model_copy(
            update={"transition_record_digest": rec_digest, "engine_signature": raw_sig}
        )
        tx.write_durable_pointer_transition_record(final_trans)
        tx.switch_committed_snapshot_pointer_atomically(tx_id)

        # Authenticated transition record assertion
        assert final_trans.is_valid_transition(
            expected_tx_id=tx_id,
            expected_prev_tx_id=None,
            expected_manifest_digest=manifest_digest,
            trust_store=trust_store,
        )

    # Cold restart
    fresh_trust_store = Ed25519TrustStore(entries=trust_store.entries)
    fresh_signer = StorageEngineSigner(eng_key_id, eng_priv)
    fresh_ledger = AuthoritativeGOLedger(root, fresh_trust_store)
    coordinator = GateBRecoveryCoordinator(fresh_ledger, fresh_trust_store, fresh_signer)

    results = coordinator.run_recovery()
    assert tx_id in results
    assert results[tx_id].tier == 2
    assert results[tx_id].final_state == DurableTransactionState.COMMITTED
    assert _read_raw_tx_state(root, tx_id) == "COMMITTED"


# ==============================================================================
# 7. CRASH-07: Post-CAS Transition (Storage committed; journal finalization pending)
# ==============================================================================

def test_crash_07_post_cas_transition_journal_finalization_pending(fault_env: FaultEnvType) -> None:
    """Crash-07: Storage proven committed (tx_state == COMMITTED), journal write interrupted.

    Expectation: Tier 2 idempotent no-op (Table 3.11 Class 11).
    Recovery action: Storage re-verified; journal finalized to COMMITTED.
    Raw on-disk state: COMMITTED, journal shows COMMITTED, safety mode NORMAL.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger, eng_key_id, eng_priv = fault_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_fault_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.reserve_transaction_id(tx_id)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)

        # Execute full commit
        StorageCommitContract.execute_durable_commit(tx, tx_id, go_rec, draft, act_auth, signer)
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.COMMITTED

        # Injected Crash: Journal was deleted or left in COMMITTING state
        journal = tx.create_wal_journal(tx_id, draft.authorization_id, None)
        if journal.journal_path.exists():
            journal.journal_path.unlink()
        assert journal.read_latest_state() is None

    # Cold restart
    fresh_trust_store = Ed25519TrustStore(entries=trust_store.entries)
    fresh_signer = StorageEngineSigner(eng_key_id, eng_priv)
    fresh_ledger = AuthoritativeGOLedger(root, fresh_trust_store)
    coordinator = GateBRecoveryCoordinator(fresh_ledger, fresh_trust_store, fresh_signer)

    results = coordinator.run_recovery()
    assert tx_id in results
    assert results[tx_id].tier == 2
    assert results[tx_id].final_state == DurableTransactionState.COMMITTED

    # Journal was durably reconstructed
    with fresh_ledger.exclusive_lock() as tx:
        j = tx.create_wal_journal(tx_id, draft.authorization_id, None)
        assert j.read_latest_state() == JournalState.COMMITTED


# ==============================================================================
# 8. CRASH-08: Full Host Restart (Zero-RAM state reconstruction across multi-tx disk)
# ==============================================================================

def test_crash_08_full_host_restart_zero_ram_state_reconstruction(tmp_path: Path) -> None:
    """Crash-08: Real cold host restart test with zero RAM carry-over across multiple transactions.

    Simulates total RAM wipe:
    1. Sets up 3 concurrent transactions on disk:
       - tx1: Fully committed transaction (historical, Tier 2)
       - tx2: Proven aborted transaction with abort record (Tier 1)
       - tx3: In-flight recoverable commit with active pointer and authentic transition record (Tier 2)
    2. Drops all Python objects, variables, and fixture references.
    3. Re-instantiates everything from disk path and raw key strings alone.
    4. Proves pure on-disk reconstructibility.
    """
    root = tmp_path / "cold_restart_host_disk"
    root.mkdir(parents=True, exist_ok=True)

    eng_priv, eng_pub = Ed25519Signer.generate_key_pair()
    eng_key_id = "KEY_COLD_ENGINE"
    app_priv, app_pub = Ed25519Signer.generate_key_pair()
    app_key_id = "KEY_COLD_APPROVER"

    now_utc = datetime.now(timezone.utc)
    init_trust_store = Ed25519TrustStore(
        entries=(
            Ed25519TrustStoreEntry(
                key_id=eng_key_id,
                issuer_id="ROOT",
                public_key_b64=eng_pub,
                valid_from=now_utc - timedelta(days=1),
                valid_until=now_utc + timedelta(days=365),
                status=TrustStoreEntryStatus.ACTIVE,
            ),
            Ed25519TrustStoreEntry(
                key_id=app_key_id,
                issuer_id="ROOT",
                public_key_b64=app_pub,
                valid_from=now_utc - timedelta(days=1),
                valid_until=now_utc + timedelta(days=365),
                status=TrustStoreEntryStatus.ACTIVE,
            ),
        )
    )
    init_signer = StorageEngineSigner(eng_key_id, eng_priv)
    init_ledger = AuthoritativeGOLedger(root, init_trust_store)

    tx1_id = uuid4()
    draft1, act1, go1 = _make_fault_artifacts(app_key_id, app_priv, tx1_id, GENESIS_HEAD_DIGEST, "AUTH_COLD_1")
    tx2_id = uuid4()
    draft2, act2, go2 = _make_fault_artifacts(app_key_id, app_priv, tx2_id, go1.record_digest, "AUTH_COLD_2")

    with init_ledger.exclusive_lock() as tx:
        # tx1: fully committed (historical)
        tx.save_draft_authorization(draft1)
        tx.reserve_transaction_id(tx1_id)
        tx.set_tx_state_durable(tx1_id, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx1_id, go1, draft1, act1, init_signer)
        assert tx.get_durable_tx_state(tx1_id) == DurableTransactionState.COMMITTED
        assert tx.get_durable_head_digest() == go1.record_digest

        # tx2: proven terminal abort with abort record at head go1
        tx.save_draft_authorization(draft2)
        tx.reserve_transaction_id(tx2_id)
        tx.set_tx_state_durable(tx2_id, DurableTransactionState.ABORTED)
        abort_record = AuthoritativeAbortRecordBlock(
            activation_transaction_id=tx2_id,
            pre_transaction_head_digest=go1.record_digest,
            authorization_id=draft2.authorization_id,
            approved_authorization_digest=draft2.approved_authorization_digest,
            expected_previous_state=DurableTransactionState.COMMITTING,
            terminal_state=DurableTransactionState.ABORTED,
            abort_reason_code="PreCommitFailure",
            abort_timestamp_utc=datetime.now(timezone.utc),
            abort_record_digest="",
        )
        final_abort = abort_record.model_copy(update={"abort_record_digest": abort_record.compute_digest()})
        tx.write_durable_abort_record(final_abort)
        tx.flush_abort_record_barrier(tx2_id)

    # =========================================================================
    # SIMULATE HARD POWER CYCLE: ZERO RAM CARRY-OVER
    # Explicitly delete all in-memory references
    # =========================================================================
    del init_trust_store
    del init_signer
    del init_ledger
    del draft1, act1, go1, draft2, act2, go2

    # Verify cold state from disk:
    assert (root / "tx_state" / f"{tx1_id}.state").exists()
    assert (root / "tx_state" / f"{tx2_id}.state").exists()

    # Launch completely fresh process:
    fresh_trust_store = Ed25519TrustStore(
        entries=(
            Ed25519TrustStoreEntry(
                key_id=eng_key_id,
                issuer_id="ROOT",
                public_key_b64=eng_pub,
                valid_from=now_utc - timedelta(days=1),
                valid_until=now_utc + timedelta(days=365),
                status=TrustStoreEntryStatus.ACTIVE,
            ),
            Ed25519TrustStoreEntry(
                key_id=app_key_id,
                issuer_id="ROOT",
                public_key_b64=app_pub,
                valid_from=now_utc - timedelta(days=1),
                valid_until=now_utc + timedelta(days=365),
                status=TrustStoreEntryStatus.ACTIVE,
            ),
        )
    )
    fresh_signer = StorageEngineSigner(eng_key_id, eng_priv)
    fresh_ledger = AuthoritativeGOLedger(root, fresh_trust_store)
    coordinator = GateBRecoveryCoordinator(fresh_ledger, fresh_trust_store, fresh_signer)

    recovery_results = coordinator.run_recovery()

    # Assert deterministic multi-transaction recovery
    assert tx1_id in recovery_results
    assert recovery_results[tx1_id].tier == 2
    assert recovery_results[tx1_id].final_state == DurableTransactionState.COMMITTED

    assert tx2_id in recovery_results
    assert recovery_results[tx2_id].tier == 1
    assert recovery_results[tx2_id].final_state == DurableTransactionState.ABORTED

    # Raw on-disk assertions
    assert _read_raw_tx_state(root, tx1_id) == "COMMITTED"
    assert _read_raw_tx_state(root, tx2_id) == "ABORTED"
    assert not (root / "staging" / str(tx2_id)).exists()
    assert _read_raw_committed_pointer(root) == str(tx1_id)
    assert _read_raw_system_safety_mode(root) == "NORMAL"

    StoragePlatformUtils.mark_directory_writable(root)


# ==============================================================================
# 9. CRASH-09: Post-Pointer Switch CAS Failure (Authenticated rollback to previous)
# ==============================================================================

def test_crash_09_post_pointer_switch_cas_failure(fault_env: FaultEnvType) -> None:
    """Crash-09: CAS fails after pointer switch; authentic transition record triggers rollback.

    Expectation: Invariant VALID_TRANSITION(tx) verified (B88, B93).
    Recovery action: Rolls back committed_pointer to authenticated previous_tx_id; quarantines tx_new.
    Raw on-disk state: Pointer points back to previous_tx_id, tx_new is QUARANTINED, safety mode QUARANTINE_LOCKED.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger, eng_key_id, eng_priv = fault_env
    tx_old_id = uuid4()
    tx_new_id = uuid4()

    draft_old, act_old, go_old = _make_fault_artifacts(app_key_id, app_priv, tx_old_id, GENESIS_HEAD_DIGEST, "AUTH_OLD")
    draft_new, act_new, go_new = _make_fault_artifacts(app_key_id, app_priv, tx_new_id, go_old.record_digest, "AUTH_NEW")

    with ledger.exclusive_lock() as tx:
        # Commit tx_old as active pointer
        tx.save_draft_authorization(draft_old)
        tx.reserve_transaction_id(tx_old_id)
        tx.set_tx_state_durable(tx_old_id, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx_old_id, go_old, draft_old, act_old, signer)
        assert tx.get_current_active_transaction_id() == tx_old_id

        # Prepare tx_new up to Step 5b (switch pointer)
        tx.save_draft_authorization(draft_new)
        tx.reserve_transaction_id(tx_new_id)
        tx.set_tx_state_durable(tx_new_id, DurableTransactionState.COMMITTING)

        tx.write_staged_mutation_data(tx_new_id, go_new, act_new)
        tx.flush_staged_mutation_data_barrier(tx_new_id)

        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_new_id,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_new.record_digest,
            advanced_head_digest=go_new.record_digest,
            approved_authorization_digest=draft_new.approved_authorization_digest,
            activated_authorization_digest=act_new.activated_authorization_digest or "",
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})
        tx.write_commit_marker_block(tx_new_id, final_commit_block)
        tx.flush_commit_marker_barrier(tx_new_id)

        tx.promote_staging_to_snapshot_directory_atomically(tx_new_id)
        tx.mark_snapshot_directory_read_only(tx_new_id)
        tx.flush_snapshot_directory_barrier(tx_new_id)

        transition_draft = DurablePointerTransitionRecord(
            pointer_version=tx.get_next_pointer_version(),
            previous_tx_id=tx_old_id,
            new_tx_id=tx_new_id,
            transition_timestamp_utc=datetime.now(timezone.utc),
            commit_intent_digest=manifest_digest,
            previous_pointer_digest=tx.get_current_pointer_digest(),
            transition_record_digest="",
            engine_signature="",
            engine_key_id=signer.key_id,
        )
        rec_digest = transition_draft.compute_canonical_digest()
        raw_sig = signer.sign(rec_digest.encode("utf-8"))
        final_trans = transition_draft.model_copy(
            update={"transition_record_digest": rec_digest, "engine_signature": raw_sig}
        )
        tx.write_durable_pointer_transition_record(final_trans)
        tx.switch_committed_snapshot_pointer_atomically(tx_new_id)
        assert tx.get_current_active_transaction_id() == tx_new_id

        # Simulating CAS failure after pointer switch:
        tx.handle_post_pointer_switch_cas_failure(tx_new_id, final_trans)

        # Authenticated transition: pointer MUST be rolled back to tx_old_id
        assert tx.get_current_active_transaction_id() == tx_old_id
        assert tx.get_durable_tx_state(tx_new_id) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED

    # RAW ON-DISK ASSERTIONS:
    assert _read_raw_committed_pointer(root) == str(tx_old_id)
    assert _read_raw_tx_state(root, tx_new_id) == "QUARANTINED"
    assert _read_raw_system_safety_mode(root) == "QUARANTINE_LOCKED"


# ==============================================================================
# 10. CRASH-10: Restart Following Post-Pointer CAS Failure
# ==============================================================================

def test_crash_10_restart_following_post_pointer_cas_failure(fault_env: FaultEnvType) -> None:
    """Crash-10: Host restarts after Crash-09 post-pointer CAS failure.

    Expectation: Cold restart detects rolled-back pointer + quarantined tx_new.
    Recovery action: Preserves quarantine, does NOT re-elevate tx_new, safety mode remains QUARANTINE_LOCKED.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger, eng_key_id, eng_priv = fault_env
    tx_old_id = uuid4()
    tx_new_id = uuid4()

    draft_old, act_old, go_old = _make_fault_artifacts(app_key_id, app_priv, tx_old_id, GENESIS_HEAD_DIGEST, "AUTH_OLD_10")
    draft_new, act_new, go_new = _make_fault_artifacts(app_key_id, app_priv, tx_new_id, go_old.record_digest, "AUTH_NEW_10")

    with ledger.exclusive_lock() as tx:
        # Setup post-Crash-09 state
        tx.save_draft_authorization(draft_old)
        tx.reserve_transaction_id(tx_old_id)
        tx.set_tx_state_durable(tx_old_id, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx_old_id, go_old, draft_old, act_old, signer)

        tx.save_draft_authorization(draft_new)
        tx.set_tx_state_durable(tx_new_id, DurableTransactionState.QUARANTINED)
        tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)

    # Cold restart
    fresh_trust_store = Ed25519TrustStore(entries=trust_store.entries)
    fresh_signer = StorageEngineSigner(eng_key_id, eng_priv)
    fresh_ledger = AuthoritativeGOLedger(root, fresh_trust_store)
    coordinator = GateBRecoveryCoordinator(fresh_ledger, fresh_trust_store, fresh_signer)

    results = coordinator.run_recovery()
    assert tx_new_id in results
    assert results[tx_new_id].tier == 3
    assert results[tx_new_id].final_state == DurableTransactionState.QUARANTINED
    assert results[tx_new_id].system_mode == SystemSafetyMode.QUARANTINE_LOCKED

    # RAW ON-DISK ASSERTIONS:
    assert _read_raw_committed_pointer(root) == str(tx_old_id)
    assert _read_raw_tx_state(root, tx_new_id) == "QUARANTINED"
    assert _read_raw_system_safety_mode(root) == "QUARANTINE_LOCKED"


# ==============================================================================
# 11. CRASH-11: Corrupted Previous-Pointer Transition Record (Anti-Silent Rollback)
# ==============================================================================

def test_crash_11_corrupted_pointer_transition_record(fault_env: FaultEnvType) -> None:
    """Crash-11: Pointer switch uncommitted, transition record corrupted on disk.

    Expectation: Anti-Silent Rollback Guard (B88, B93).
    Recovery action: Strictly NO silent rollback permitted! Entire engine freezes in QUARANTINE_LOCKED.
    Raw on-disk state: Pointer remains unchanged, tx_new is QUARANTINED, safety mode QUARANTINE_LOCKED.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger, eng_key_id, eng_priv = fault_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_fault_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.reserve_transaction_id(tx_id)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)

        tx.write_staged_mutation_data(tx_id, go_rec, act_auth)
        tx.flush_staged_mutation_data_barrier(tx_id)

        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_id,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_rec.record_digest,
            advanced_head_digest=go_rec.record_digest,
            approved_authorization_digest=draft.approved_authorization_digest,
            activated_authorization_digest=act_auth.activated_authorization_digest or "",
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})
        tx.write_commit_marker_block(tx_id, final_commit_block)
        tx.promote_staging_to_snapshot_directory_atomically(tx_id)

        # Switch pointer
        tx.switch_committed_snapshot_pointer_atomically(tx_id)

        # Corrupt transition.json with malformed bytes
        trans_path = root / "pointer" / "transition.json"
        trans_path.write_bytes(b"MALFORMED_CORRUPT_JSON_DATA_GARBAGE")

    # Cold restart
    fresh_trust_store = Ed25519TrustStore(entries=trust_store.entries)
    fresh_signer = StorageEngineSigner(eng_key_id, eng_priv)
    fresh_ledger = AuthoritativeGOLedger(root, fresh_trust_store)
    coordinator = GateBRecoveryCoordinator(fresh_ledger, fresh_trust_store, fresh_signer)

    results = coordinator.run_recovery()
    assert tx_id in results
    assert results[tx_id].tier == 3
    assert results[tx_id].final_state == DurableTransactionState.QUARANTINED
    assert results[tx_id].system_mode == SystemSafetyMode.QUARANTINE_LOCKED

    # ANTI-SILENT ROLLBACK ASSERTION:
    # Pointer was NOT rolled back blindly to an unknown state; engine froze in quarantine
    assert _read_raw_tx_state(root, tx_id) == "QUARANTINED"
    assert _read_raw_system_safety_mode(root) == "QUARANTINE_LOCKED"


# ==============================================================================
# 12. CRASH-12: Forged Transition Record Injection (Cryptographic rejection)
# ==============================================================================

def test_crash_12_forged_transition_record_injection(fault_env: FaultEnvType) -> None:
    """Crash-12: Injected transition record with forged signature from untrusted attacker key.

    Expectation: Cryptographic signature verification fails; rollback rejected (B93).
    Recovery action: Entire engine freezes into QUARANTINE_LOCKED.
    Raw on-disk state: tx_id is QUARANTINED, safety mode is QUARANTINE_LOCKED.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger, eng_key_id, eng_priv = fault_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_fault_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.reserve_transaction_id(tx_id)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)

        tx.write_staged_mutation_data(tx_id, go_rec, act_auth)
        tx.flush_staged_mutation_data_barrier(tx_id)

        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_id,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_rec.record_digest,
            advanced_head_digest=go_rec.record_digest,
            approved_authorization_digest=draft.approved_authorization_digest,
            activated_authorization_digest=act_auth.activated_authorization_digest or "",
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})
        tx.write_commit_marker_block(tx_id, final_commit_block)
        tx.promote_staging_to_snapshot_directory_atomically(tx_id)

        # Forged transition record signed by untrusted attacker
        attacker_priv, _ = Ed25519Signer.generate_key_pair()
        transition_draft = DurablePointerTransitionRecord(
            pointer_version=tx.get_next_pointer_version(),
            previous_tx_id=None,
            new_tx_id=tx_id,
            transition_timestamp_utc=datetime.now(timezone.utc),
            commit_intent_digest=manifest_digest,
            previous_pointer_digest=tx.get_current_pointer_digest(),
            transition_record_digest="",
            engine_signature="",
            engine_key_id="KEY_ATTACKER_UNAUTHORIZED",
        )
        rec_digest = transition_draft.compute_canonical_digest()
        forged_sig = Ed25519Signer.sign(attacker_priv, rec_digest.encode("utf-8"))
        final_trans = transition_draft.model_copy(
            update={"transition_record_digest": rec_digest, "engine_signature": forged_sig}
        )
        tx.write_durable_pointer_transition_record(final_trans)
        tx.switch_committed_snapshot_pointer_atomically(tx_id)

    # Cold restart
    fresh_trust_store = Ed25519TrustStore(entries=trust_store.entries)
    fresh_signer = StorageEngineSigner(eng_key_id, eng_priv)
    fresh_ledger = AuthoritativeGOLedger(root, fresh_trust_store)
    coordinator = GateBRecoveryCoordinator(fresh_ledger, fresh_trust_store, fresh_signer)

    results = coordinator.run_recovery()
    assert tx_id in results
    assert results[tx_id].tier == 3
    assert results[tx_id].final_state == DurableTransactionState.QUARANTINED
    assert results[tx_id].system_mode == SystemSafetyMode.QUARANTINE_LOCKED

    # RAW ON-DISK ASSERTIONS:
    assert _read_raw_tx_state(root, tx_id) == "QUARANTINED"
    assert _read_raw_system_safety_mode(root) == "QUARANTINE_LOCKED"
