"""Phase 13 Slice 2: Unit Tests for Gate B Disambiguated Snapshot Readers (Stage 3.2).

Verifies:
- Disambiguated reader APIs: read_active_committed_snapshot vs read_committed_snapshot (B81, B85)
- Invariant 1: Atomic & consistent reader boundary under single lock
- Invariant 2: Authoritative quarantine escalation path with fatal safety halt on write failure
- Invariant 3: Explicit cross-transaction identity binding across directory and commit manifest
- Tamper detection and fail-closed transition to QUARANTINE_LOCKED (B85, B86)
- Staging invisibility (B65): Readers observe strictly /snapshots/<tx_id>/
- AuthoritativeSnapshotView immutability (frozen=True, extra="forbid")
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import pytest
from typing import Generator, Optional
from uuid import UUID, uuid4

from acash.execution.crypto import (
    Ed25519Signer,
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.gate_b.exceptions import DataContractError, QuarantineError
from acash.gate_b.readers import (
    AuthoritativeSnapshotView,
    SnapshotReaderService,
)
from acash.gate_b.schema import (
    AuthoritativeCommitRecordBlock,
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
    StorageCommitContract,
    StorageEngineSigner,
    StoragePlatformUtils,
)

ReadersEnvType = tuple[Path, Ed25519TrustStore, StorageEngineSigner, str, str, AuthoritativeGOLedger]


@pytest.fixture
def readers_env(tmp_path: Path) -> Generator[ReadersEnvType, None, None]:
    root = tmp_path / "gate_b_readers"
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

    yield root, trust_store, signer, app_key_id, app_priv, ledger

    StoragePlatformUtils.mark_directory_writable(root)


def _make_dummy_artifacts(
    app_key_id: str,
    app_priv: str,
    tx_id: UUID,
    prev_head: str = GENESIS_HEAD_DIGEST,
    auth_id: str = "AUTH_GATE_B_TEST",
) -> tuple[LiveAuthorization, LiveAuthorization, HumanGORecord]:
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
        go_record_id=f"GO_REC_{tx_id}",
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

    act_draft = draft.model_copy(update={
        "status": LiveAuthorizationStatus.ACTIVE,
        "source_approved_digest": draft.approved_authorization_digest,
        "active_go_record_digest": go_rec.record_digest,
        "activation_transaction_id": tx_id,
        "activated_at": now_utc,
        "activated_authorization_digest": "",
    })
    act_bytes = act_draft.compute_activated_canonical_bytes()
    activated_auth = act_draft.model_copy(update={
        "activated_authorization_digest": hashlib.sha256(act_bytes).hexdigest()
    })

    return draft, activated_auth, go_rec


# ==============================================================================
# ACTIVE COMMITTED SNAPSHOT READER TESTS
# ==============================================================================

def test_read_active_committed_snapshot_success(readers_env: ReadersEnvType) -> None:
    """Assert reading active committed snapshot succeeds and returns validated view."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)
        commit_block = StorageCommitContract.execute_durable_commit(tx, tx_id, go_rec, draft, act_auth, signer)

    view = SnapshotReaderService.read_active_committed_snapshot(ledger)

    assert view.transaction_id == tx_id
    assert view.commit_record_block.mutation_manifest_digest == commit_block.mutation_manifest_digest
    assert view.record is not None
    assert view.record.record_digest == go_rec.record_digest
    assert view.head_digest == go_rec.record_digest
    assert view.authorization is not None
    assert view.authorization.status == LiveAuthorizationStatus.ACTIVE
    assert view.authorization.activated_authorization_digest == act_auth.activated_authorization_digest


def test_read_active_committed_snapshot_no_pointer_fails_closed(readers_env: ReadersEnvType) -> None:
    """Assert fail-closed rejection when no committed pointer exists."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env

    with pytest.raises(DataContractError) as exc_info:
        SnapshotReaderService.read_active_committed_snapshot(ledger)

    assert "NO_ACTIVE_COMMITTED_SNAPSHOT_AVAILABLE" in str(exc_info.value)


def test_read_active_committed_snapshot_uncommitted_state_fails_closed(readers_env: ReadersEnvType) -> None:
    """Assert fail-closed rejection when committed pointer points to uncommitted transaction."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_id = uuid4()

    with ledger.exclusive_lock() as tx:
        tx.reserve_transaction_id(tx_id)  # PREPARED
        tx.switch_committed_snapshot_pointer_atomically(tx_id)

    with pytest.raises(DataContractError) as exc_info:
        SnapshotReaderService.read_active_committed_snapshot(ledger)

    assert "ACTIVE_SNAPSHOT_TX_NOT_COMMITTED" in str(exc_info.value)


def test_read_active_committed_snapshot_tampered_entity_quarantines(readers_env: ReadersEnvType) -> None:
    """Assert tampering with snapshot operational entities trips fail-closed into QUARANTINE_LOCKED (B85, B86)."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx_id, go_rec, draft, act_auth, signer)

        # Tamper with snapshot record.json: modify signature bytes
        snap_dir = tx._get_snapshot_tx_dir(tx_id)
        StoragePlatformUtils.mark_directory_writable(snap_dir)
        rec_file = snap_dir / "record.json"
        data = json.loads(rec_file.read_text(encoding="utf-8"))
        data["record_digest"] = "f" * 64
        rec_file.write_text(json.dumps(data), encoding="utf-8")
        StoragePlatformUtils.mark_directory_read_only(snap_dir)

    with pytest.raises(QuarantineError) as exc_info:
        SnapshotReaderService.read_active_committed_snapshot(ledger)

    assert "ACTIVE_SNAPSHOT_CORRUPTED_ENTERING_QUARANTINE" in str(exc_info.value)

    with ledger.exclusive_lock() as tx:
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


def test_read_active_committed_snapshot_missing_marker_quarantines(readers_env: ReadersEnvType) -> None:
    """Assert missing commit marker block in active snapshot directory trips quarantine."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx_id, go_rec, draft, act_auth, signer)

        # Delete commit_record_block.json
        snap_dir = tx._get_snapshot_tx_dir(tx_id)
        StoragePlatformUtils.mark_directory_writable(snap_dir)
        (snap_dir / "commit_record_block.json").unlink()
        StoragePlatformUtils.mark_directory_read_only(snap_dir)

    with pytest.raises(QuarantineError) as exc_info:
        SnapshotReaderService.read_active_committed_snapshot(ledger)

    assert "ACTIVE_SNAPSHOT_CORRUPTED_ENTERING_QUARANTINE" in str(exc_info.value)

    with ledger.exclusive_lock() as tx:
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


# ==============================================================================
# HISTORICAL COMMITTED SNAPSHOT READER TESTS
# ==============================================================================

def test_read_committed_snapshot_by_id_historical_success(readers_env: ReadersEnvType) -> None:
    """Assert historical snapshot read by ID succeeds even when pointer has moved to new transaction (B85)."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env

    # 1. Commit tx1
    tx1_id = uuid4()
    draft1, act1, go1 = _make_dummy_artifacts(app_key_id, app_priv, tx1_id, auth_id="AUTH_1")
    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft1)
        tx.set_tx_state_durable(tx1_id, DurableTransactionState.COMMITTING)
        commit_block1 = StorageCommitContract.execute_durable_commit(tx, tx1_id, go1, draft1, act1, signer)

    # 2. Commit tx2 (pointer advances to tx2)
    tx2_id = uuid4()
    draft2, act2, go2 = _make_dummy_artifacts(
        app_key_id, app_priv, tx2_id, prev_head=go1.record_digest, auth_id="AUTH_2"
    )
    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft2)
        tx.set_tx_state_durable(tx2_id, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx2_id, go2, draft2, act2, signer)

    # Pointer references tx2
    with ledger.exclusive_lock() as tx:
        assert tx.committed_pointer_references_transaction(tx2_id)
        assert not tx.committed_pointer_references_transaction(tx1_id)

    # Historical read of retired tx1
    view1 = SnapshotReaderService.read_committed_snapshot(ledger, tx1_id)
    assert view1.transaction_id == tx1_id
    assert view1.commit_record_block.mutation_manifest_digest == commit_block1.mutation_manifest_digest
    assert view1.authorization is not None
    assert view1.authorization.authorization_id == "AUTH_1"

    # Current active read remains tx2
    active_view = SnapshotReaderService.read_active_committed_snapshot(ledger)
    assert active_view.transaction_id == tx2_id


def test_read_committed_snapshot_by_id_uncommitted_rejected(readers_env: ReadersEnvType) -> None:
    """Assert reading snapshot by ID fails closed if transaction is uncommitted (ABORTED or PREPARED)."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_id = uuid4()

    with ledger.exclusive_lock() as tx:
        tx.set_tx_state_durable(tx_id, DurableTransactionState.ABORTED)

    with pytest.raises(DataContractError) as exc_info:
        SnapshotReaderService.read_committed_snapshot(ledger, tx_id)

    assert "CANNOT_READ_UNCOMMITTED_SNAPSHOT" in str(exc_info.value)


def test_read_committed_snapshot_by_id_missing_directory_rejected(readers_env: ReadersEnvType) -> None:
    """Assert reading snapshot by ID fails closed if snapshot directory does not exist."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_id = uuid4()

    with ledger.exclusive_lock() as tx:
        # State says COMMITTED, but directory never created
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTED)

    with pytest.raises(DataContractError) as exc_info:
        SnapshotReaderService.read_committed_snapshot(ledger, tx_id)

    assert "SNAPSHOT_DIRECTORY_MISSING" in str(exc_info.value)


def test_read_committed_snapshot_by_id_tampered_manifest_quarantines(readers_env: ReadersEnvType) -> None:
    """Assert tampered manifest in historical snapshot triggers QUARANTINE_LOCKED."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx_id, go_rec, draft, act_auth, signer)

        # Tamper manifest digest in marker block
        snap_dir = tx._get_snapshot_tx_dir(tx_id)
        StoragePlatformUtils.mark_directory_writable(snap_dir)
        marker_file = snap_dir / "commit_record_block.json"
        data = json.loads(marker_file.read_text(encoding="utf-8"))
        data["mutation_manifest_digest"] = "e" * 64
        marker_file.write_text(json.dumps(data), encoding="utf-8")
        StoragePlatformUtils.mark_directory_read_only(snap_dir)

    with pytest.raises(QuarantineError):
        SnapshotReaderService.read_committed_snapshot(ledger, tx_id)

    with ledger.exclusive_lock() as tx:
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


# ==============================================================================
# INVARIANT 2 & 3: QUARANTINE ESCALATION & CROSS-TRANSACTION IDENTITY BINDING
# ==============================================================================

def test_read_committed_snapshot_rejects_cross_transaction_identity_mismatch(readers_env: ReadersEnvType) -> None:
    """Invariant 3: Reject and quarantine when snapshot directory tx_A contains commit block claiming tx_B."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_a = uuid4()
    tx_b = uuid4()
    draft_b, act_b, go_b = _make_dummy_artifacts(app_key_id, app_priv, tx_b)

    with ledger.exclusive_lock() as tx:
        # Set tx_A state to COMMITTED
        tx.set_tx_state_durable(tx_a, DurableTransactionState.COMMITTED)

        # Create directory /snapshots/<tx_A>/ but write commit block containing tx_B!
        snap_a = tx._get_snapshot_tx_dir(tx_a)
        snap_a.mkdir(parents=True, exist_ok=True)

        mismatched_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_b,  # Mismatch!
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_b.record_digest,
            advanced_head_digest=go_b.record_digest,
            approved_authorization_digest=draft_b.approved_authorization_digest,
            activated_authorization_digest=act_b.activated_authorization_digest or "",
            mutation_manifest_digest="x" * 64,
        )
        (snap_a / "commit_record_block.json").write_text(
            mismatched_block.model_dump_json(), encoding="utf-8"
        )
        (snap_a / "record.json").write_text(go_b.model_dump_json(), encoding="utf-8")
        (snap_a / "authorization.json").write_text(act_b.model_dump_json(), encoding="utf-8")

    with pytest.raises(QuarantineError) as exc_info:
        SnapshotReaderService.read_committed_snapshot(ledger, tx_a)

    assert "CROSS_TRANSACTION_IDENTITY_MISMATCH" in str(exc_info.value)

    with ledger.exclusive_lock() as tx:
        assert tx.get_durable_tx_state(tx_a) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


def test_read_committed_snapshot_rejects_manifest_cross_transaction_identity_mismatch(
    readers_env: ReadersEnvType,
) -> None:
    """Invariant 3 (4-Point Identity Alignment): Directory=tx_A, CommitBlock=tx_A, but Manifest=tx_B.

    Even if commit_block claims tx_A and deep manifest verification passes entity hashes,
    the reader MUST detect manifest.activation_transaction_id == tx_B != tx_A and quarantine.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_a = uuid4()
    tx_b = uuid4()
    draft_b, act_b, go_b = _make_dummy_artifacts(app_key_id, app_priv, tx_b)

    with ledger.exclusive_lock() as tx:
        tx.set_tx_state_durable(tx_a, DurableTransactionState.COMMITTED)
        snap_a = tx._get_snapshot_tx_dir(tx_a)
        snap_a.mkdir(parents=True, exist_ok=True)

        # Commit block claims tx_A and computes matching digest over act_b and go_b
        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_a,  # Claims tx_A!
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_b.record_digest,
            advanced_head_digest=go_b.record_digest,
            approved_authorization_digest=draft_b.approved_authorization_digest,
            activated_authorization_digest=act_b.activated_authorization_digest or "",
            mutation_manifest_digest="placeholder",
        )
        digest = commit_block.compute_manifest_digest()
        commit_block_valid = commit_block.model_copy(update={"mutation_manifest_digest": digest})

        (snap_a / "commit_record_block.json").write_text(
            commit_block_valid.model_dump_json(), encoding="utf-8"
        )
        (snap_a / "record.json").write_text(go_b.model_dump_json(), encoding="utf-8")
        (snap_a / "head.json").write_text(
            json.dumps({"head_digest": go_b.record_digest}), encoding="utf-8"
        )
        # Manifest artifact (authorization.json) explicitly contains activation_transaction_id = tx_b!
        (snap_a / "authorization.json").write_text(act_b.model_dump_json(), encoding="utf-8")
        StoragePlatformUtils.mark_directory_read_only(snap_a)

    with pytest.raises(QuarantineError) as exc_info:
        SnapshotReaderService.read_committed_snapshot(ledger, tx_a)

    assert "CROSS_TRANSACTION_MANIFEST_IDENTITY_MISMATCH" in str(exc_info.value)

    with ledger.exclusive_lock() as tx:
        assert tx.get_durable_tx_state(tx_a) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


def test_read_active_committed_snapshot_rejects_manifest_cross_transaction_identity_mismatch(
    readers_env: ReadersEnvType,
) -> None:
    """Invariant 3 (Active Reader): Pointer=tx_A, CommitBlock=tx_A, but Manifest=tx_B."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_a = uuid4()
    tx_b = uuid4()
    draft_b, act_b, go_b = _make_dummy_artifacts(app_key_id, app_priv, tx_b)

    with ledger.exclusive_lock() as tx:
        tx.set_tx_state_durable(tx_a, DurableTransactionState.COMMITTED)
        tx.switch_committed_snapshot_pointer_atomically(tx_a)
        snap_a = tx._get_snapshot_tx_dir(tx_a)
        snap_a.mkdir(parents=True, exist_ok=True)

        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_a,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go_b.record_digest,
            advanced_head_digest=go_b.record_digest,
            approved_authorization_digest=draft_b.approved_authorization_digest,
            activated_authorization_digest=act_b.activated_authorization_digest or "",
            mutation_manifest_digest="placeholder",
        )
        digest = commit_block.compute_manifest_digest()
        commit_block_valid = commit_block.model_copy(update={"mutation_manifest_digest": digest})

        (snap_a / "commit_record_block.json").write_text(
            commit_block_valid.model_dump_json(), encoding="utf-8"
        )
        (snap_a / "record.json").write_text(go_b.model_dump_json(), encoding="utf-8")
        (snap_a / "head.json").write_text(
            json.dumps({"head_digest": go_b.record_digest}), encoding="utf-8"
        )
        (snap_a / "authorization.json").write_text(act_b.model_dump_json(), encoding="utf-8")
        StoragePlatformUtils.mark_directory_read_only(snap_a)

    with pytest.raises(QuarantineError) as exc_info:
        SnapshotReaderService.read_active_committed_snapshot(ledger)

    assert "CROSS_TRANSACTION_MANIFEST_IDENTITY_MISMATCH" in str(exc_info.value)

    with ledger.exclusive_lock() as tx:
        assert tx.get_durable_tx_state(tx_a) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


def test_reader_quarantine_succeeds_even_if_forensic_logging_fails(
    readers_env: ReadersEnvType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invariant 2 (Hardening): Failure of forensic audit logging does not impede quarantine escalation."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx_id, go_rec, draft, act_auth, signer)

        # Tamper snapshot record to trigger quarantine escalation
        snap_dir = tx._get_snapshot_tx_dir(tx_id)
        StoragePlatformUtils.mark_directory_writable(snap_dir)
        (snap_dir / "record.json").write_text("{\"corrupted\": true}", encoding="utf-8")
        StoragePlatformUtils.mark_directory_read_only(snap_dir)

    # Monkeypatch log_consistency_violation to simulate logging disk write error
    def failing_log(self: LedgerStorageTransaction, msg: str) -> None:
        raise OSError("SIMULATED_LOG_FILE_IO_FAILURE")

    monkeypatch.setattr(LedgerStorageTransaction, "log_consistency_violation", failing_log)

    with pytest.raises(QuarantineError) as exc_info:
        SnapshotReaderService.read_active_committed_snapshot(ledger)

    assert "ACTIVE_SNAPSHOT_CORRUPTED_ENTERING_QUARANTINE" in str(exc_info.value)

    # Quarantine state must still be durably locked despite logging failure
    with ledger.exclusive_lock() as tx:
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


def test_reader_quarantine_escalation_failure_fails_closed(
    readers_env: ReadersEnvType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invariant 2: When writing quarantine state to storage fails, system executes fatal safety halt."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx_id, go_rec, draft, act_auth, signer)

        # Tamper snapshot record to trigger deep verification failure
        snap_dir = tx._get_snapshot_tx_dir(tx_id)
        StoragePlatformUtils.mark_directory_writable(snap_dir)
        (snap_dir / "record.json").write_text("{\"corrupted\": true}", encoding="utf-8")
        StoragePlatformUtils.mark_directory_read_only(snap_dir)

    # Monkeypatch set_tx_state_durable to simulate storage I/O failure during quarantine attempt
    def failing_set_tx_state(self: LedgerStorageTransaction, tid: UUID, st: DurableTransactionState) -> None:
        raise OSError("SIMULATED_DISK_IO_FAILURE_DURING_QUARANTINE")

    monkeypatch.setattr(LedgerStorageTransaction, "set_tx_state_durable", failing_set_tx_state)

    with pytest.raises(QuarantineError) as exc_info:
        SnapshotReaderService.read_active_committed_snapshot(ledger)

    # Invariant 2: Must be fatal safety halt, never return degraded data or swallow exception
    assert "QUARANTINE_ESCALATION_FAILED_FATAL_SAFETY_HALT" in str(exc_info.value)


# ==============================================================================
# STAGING INVISIBILITY, IMMUTABILITY & LOCK BOUNDARY TESTS
# ==============================================================================

def test_uncommitted_mutations_are_invisible_to_authoritative_readers(readers_env: ReadersEnvType) -> None:
    """B65: Staged mutations in /staging/<tx_id>/ are completely invisible to both reader methods."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        # Write files into staging ONLY
        tx.write_staged_mutation_data(tx_id, go_rec, act_auth)
        stg_dir = tx._get_staging_tx_dir(tx_id)
        assert stg_dir.exists()

    # Neither active reader nor by-ID reader can see uncommitted staging mutations
    with pytest.raises(DataContractError) as exc_active:
        SnapshotReaderService.read_active_committed_snapshot(ledger)
    assert "NO_ACTIVE_COMMITTED_SNAPSHOT_AVAILABLE" in str(exc_active.value)

    with pytest.raises(DataContractError) as exc_by_id:
        SnapshotReaderService.read_committed_snapshot(ledger, tx_id)
    assert "CANNOT_READ_UNCOMMITTED_SNAPSHOT" in str(exc_by_id.value)


def test_authoritative_snapshot_view_immutability() -> None:
    """Assert AuthoritativeSnapshotView is immutable (frozen) and rejects extra fields."""
    tx_id = uuid4()
    commit_block = AuthoritativeCommitRecordBlock(
        activation_transaction_id=tx_id,
        commit_timestamp_utc=datetime.now(timezone.utc),
        ledger_record_digest="a" * 64,
        advanced_head_digest="b" * 64,
        approved_authorization_digest="c" * 64,
        activated_authorization_digest="d" * 64,
        mutation_manifest_digest="e" * 64,
    )

    view = AuthoritativeSnapshotView(
        transaction_id=tx_id,
        commit_record_block=commit_block,
        head_digest="b" * 64,
    )

    # Immutability: frozen model cannot be mutated
    with pytest.raises(Exception):
        setattr(view, "head_digest", "x" * 64)

    # Extra fields forbidden: extra="forbid"
    with pytest.raises(Exception):
        AuthoritativeSnapshotView(
            transaction_id=tx_id,
            commit_record_block=commit_block,
            head_digest="b" * 64,
            unexpected_field="disallowed",  # type: ignore[call-arg]
        )


def test_snapshot_readers_respect_consistent_lock_boundary(readers_env: ReadersEnvType) -> None:
    """Invariant 1: Reader operations function identically with AuthoritativeGOLedger and LedgerStorageTransaction."""
    root, trust_store, signer, app_key_id, app_priv, ledger = readers_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx_id, go_rec, draft, act_auth, signer)

        # 1. Reader called directly within caller's held LedgerStorageTransaction
        view_direct = SnapshotReaderService.read_active_committed_snapshot(tx)
        assert view_direct.transaction_id == tx_id

        view_by_id_direct = SnapshotReaderService.read_committed_snapshot(tx, tx_id)
        assert view_by_id_direct.transaction_id == tx_id

    # 2. Reader called with AuthoritativeGOLedger (acquires lock boundary)
    view_ledger = SnapshotReaderService.read_active_committed_snapshot(ledger)
    assert view_ledger.transaction_id == tx_id

    view_by_id_ledger = SnapshotReaderService.read_committed_snapshot(ledger, tx_id)
    assert view_by_id_ledger.transaction_id == tx_id
