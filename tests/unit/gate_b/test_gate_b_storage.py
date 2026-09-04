"""Phase 13 Slice 2: Unit Tests for Gate B Storage Substrate & Two-Phase Commit Engine (Stage 2).

Verifies Two-Phase Recoverable Commit, platform durability barriers, read-only ACLs,
atomic pointer switching, CAS state transitions, and authenticated anti-rollback safeguards.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from pathlib import Path
import pytest
import shutil
from typing import Generator
from uuid import uuid4

from acash.execution.crypto import (
    Ed25519Signer,
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.gate_b.exceptions import (
    DataContractError,
    StorageDurabilityError,
)
from acash.gate_b.schema import (
    AuthoritativeCommitRecordBlock,
    DurablePointerTransitionRecord,
    DurableTransactionState,
    HumanGORecord,
    JournalState,
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


@pytest.fixture
def storage_environment(tmp_path: Path) -> Generator[tuple[Path, Ed25519TrustStore, StorageEngineSigner, str, str], None, None]:
    root = tmp_path / "gate_b_storage"
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

    yield root, trust_store, signer, app_key_id, app_priv

    # Cleanup read-only attributes so tmp_path can be cleaned up
    StoragePlatformUtils.mark_directory_writable(root)


def _make_dummy_auth_and_go_record(
    app_key_id: str,
    app_priv: str,
    tx_id: uuid4,  # type: ignore[valid-type]
    prev_head: str = GENESIS_HEAD_DIGEST,
) -> tuple[LiveAuthorization, LiveAuthorization, HumanGORecord]:
    now_utc = datetime.now(timezone.utc)
    exp_utc = now_utc + timedelta(hours=4)

    # Approved draft
    draft = LiveAuthorization(
        authorization_id="AUTH_GATE_B_TEST",
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

    # Human GO Record
    go_draft = HumanGORecord(
        go_record_id="GO_REC_TEST_001",
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

    # Activated auth
    act_draft = draft.model_copy(update={
        "status": LiveAuthorizationStatus.ACTIVE,
        "source_approved_digest": draft.approved_authorization_digest,
        "active_go_record_digest": go_rec.record_digest,
        "activation_transaction_id": tx_id,
        "activated_at": now_utc,
        "activated_authorization_digest": "",
    })
    act_digest = act_draft.compute_activated_canonical_bytes()
    import hashlib
    activated_auth = act_draft.model_copy(update={
        "activated_authorization_digest": hashlib.sha256(act_digest).hexdigest()
    })

    return draft, activated_auth, go_rec


def test_storage_directory_skeleton_initialization(
    storage_environment: tuple[Path, Ed25519TrustStore, StorageEngineSigner, str, str],
) -> None:
    root, trust_store, _, _, _ = storage_environment
    ledger = AuthoritativeGOLedger(root, trust_store)
    with ledger.exclusive_lock() as tx:
        assert (root / "staging").is_dir()
        assert (root / "snapshots").is_dir()
        assert (root / "pointer").is_dir()
        assert (root / "aborts").is_dir()
        assert (root / "tx_state").is_dir()
        assert (root / "journal").is_dir()
        assert tx.current_head_digest == GENESIS_HEAD_DIGEST


def test_cas_state_transition_success(
    storage_environment: tuple[Path, Ed25519TrustStore, StorageEngineSigner, str, str],
) -> None:
    root, trust_store, _, _, _ = storage_environment
    ledger = AuthoritativeGOLedger(root, trust_store)
    tx_id = uuid4()

    with ledger.exclusive_lock() as tx:
        tx.reserve_transaction_id(tx_id)
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.PREPARED

        # CAS: PREPARED -> COMMITTING
        assert tx.compare_and_set_tx_state(tx_id, DurableTransactionState.PREPARED, DurableTransactionState.COMMITTING)
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.COMMITTING

        # CAS: COMMITTING -> COMMITTED
        assert tx.compare_and_set_tx_state(tx_id, DurableTransactionState.COMMITTING, DurableTransactionState.COMMITTED)
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.COMMITTED


def test_cas_state_transition_conflict(
    storage_environment: tuple[Path, Ed25519TrustStore, StorageEngineSigner, str, str],
) -> None:
    root, trust_store, _, _, _ = storage_environment
    ledger = AuthoritativeGOLedger(root, trust_store)
    tx_id = uuid4()

    with ledger.exclusive_lock() as tx:
        tx.reserve_transaction_id(tx_id)
        # Expected is COMMITTING, but current is PREPARED -> Conflict
        assert not tx.compare_and_set_tx_state(tx_id, DurableTransactionState.COMMITTING, DurableTransactionState.COMMITTED)
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.PREPARED


def test_two_phase_recoverable_commit_success(
    storage_environment: tuple[Path, Ed25519TrustStore, StorageEngineSigner, str, str],
) -> None:
    root, trust_store, signer, app_key_id, app_priv = storage_environment
    ledger = AuthoritativeGOLedger(root, trust_store)
    tx_id = uuid4()

    draft, activated, go_rec = _make_dummy_auth_and_go_record(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.reserve_transaction_id(tx_id)
        assert tx.compare_and_set_tx_state(tx_id, DurableTransactionState.PREPARED, DurableTransactionState.COMMITTING)

        commit_block = StorageCommitContract.execute_durable_commit(
            tx=tx,
            tx_id=tx_id,
            go_record=go_rec,
            approved_auth=draft,
            activated_auth=activated,
            engine_signer=signer,
        )

        assert commit_block.verify_manifest_integrity()
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.COMMITTED
        assert tx.get_current_active_transaction_id() == tx_id
        assert tx.current_head_digest == go_rec.record_digest

        # Verify snapshots/<tx_id>/ exists and staging/<tx_id>/ is gone
        assert tx.has_snapshot_directory(tx_id)
        assert not (root / "staging" / str(tx_id)).exists()

        # Verify transition record on disk
        trans_rec = tx.read_pointer_transition_record()
        assert trans_rec is not None
        assert trans_rec.new_tx_id == tx_id
        assert trans_rec.is_valid_transition(
            expected_tx_id=tx_id,
            expected_prev_tx_id=None,
            expected_manifest_digest=commit_block.mutation_manifest_digest,
            trust_store=trust_store,
        )


def test_snapshot_directory_read_only_acl_enforcement(
    storage_environment: tuple[Path, Ed25519TrustStore, StorageEngineSigner, str, str],
) -> None:
    """Test B75/B83: Mutating snapshot directory after publication barrier is rejected by ACLs."""
    root, trust_store, signer, app_key_id, app_priv = storage_environment
    ledger = AuthoritativeGOLedger(root, trust_store)
    tx_id = uuid4()

    draft, activated, go_rec = _make_dummy_auth_and_go_record(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.reserve_transaction_id(tx_id)
        tx.compare_and_set_tx_state(tx_id, DurableTransactionState.PREPARED, DurableTransactionState.COMMITTING)

        StorageCommitContract.execute_durable_commit(
            tx=tx,
            tx_id=tx_id,
            go_record=go_rec,
            approved_auth=draft,
            activated_auth=activated,
            engine_signer=signer,
        )

        snap_dir = root / "snapshots" / str(tx_id)
        record_file = snap_dir / "record.json"

        # Attempt to overwrite record.json inside read-only snapshot directory must raise PermissionError
        with pytest.raises(PermissionError):
            with open(record_file, "wb") as f:
                f.write(b"tampered_bytes")


def test_post_pointer_switch_cas_failure_rolls_back_to_authenticated_previous_pointer(
    storage_environment: tuple[Path, Ed25519TrustStore, StorageEngineSigner, str, str],
) -> None:
    """Test B88/B93: CAS failure after pointer switch rolls back to authenticated previous pointer."""
    root, trust_store, signer, app_key_id, app_priv = storage_environment
    ledger = AuthoritativeGOLedger(root, trust_store)

    # 1. Commit initial transaction (tx_1)
    tx1_id = uuid4()
    draft1, act1, go1 = _make_dummy_auth_and_go_record(app_key_id, app_priv, tx1_id, prev_head=GENESIS_HEAD_DIGEST)
    with ledger.exclusive_lock() as tx:
        tx.reserve_transaction_id(tx1_id)
        tx.compare_and_set_tx_state(tx1_id, DurableTransactionState.PREPARED, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx1_id, go1, draft1, act1, signer)
        assert tx.get_current_active_transaction_id() == tx1_id

    # 2. Attempt commit on tx_2 but simulate CAS failure
    tx2_id = uuid4()
    draft2, act2, go2 = _make_dummy_auth_and_go_record(app_key_id, app_priv, tx2_id, prev_head=go1.record_digest)
    with ledger.exclusive_lock() as tx:
        tx.reserve_transaction_id(tx2_id)
        tx.compare_and_set_tx_state(tx2_id, DurableTransactionState.PREPARED, DurableTransactionState.COMMITTING)

        # Execute up to step 5b manually
        tx.write_staged_mutation_data(tx2_id, go2, act2)
        tx.flush_staged_mutation_data_barrier(tx2_id)

        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx2_id,
            commit_timestamp_utc=datetime.now(timezone.utc),
            ledger_record_digest=go2.record_digest,
            advanced_head_digest=go2.record_digest,
            approved_authorization_digest=draft2.approved_authorization_digest,
            activated_authorization_digest=act2.activated_authorization_digest or "",
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})
        tx.write_commit_marker_block(tx2_id, final_block)
        tx.promote_staging_to_snapshot_directory_atomically(tx2_id)
        tx.mark_snapshot_directory_read_only(tx2_id)

        # Step 5a: create and sign transition record
        trans_draft = DurablePointerTransitionRecord(
            pointer_version=tx.get_next_pointer_version(),
            previous_tx_id=tx1_id,
            new_tx_id=tx2_id,
            transition_timestamp_utc=datetime.now(timezone.utc),
            commit_intent_digest=manifest_digest,
            previous_pointer_digest=tx.get_current_pointer_digest(),
            transition_record_digest="",
            engine_signature="",
            engine_key_id=signer.key_id,
        )
        rec_dig = trans_draft.compute_canonical_digest()
        sig = signer.sign(rec_dig.encode("utf-8"))
        final_trans = trans_draft.model_copy(update={"transition_record_digest": rec_dig, "engine_signature": sig})
        tx.write_durable_pointer_transition_record(final_trans)

        # Step 5b: switch pointer
        tx.switch_committed_snapshot_pointer_atomically(tx2_id)
        assert tx.get_current_active_transaction_id() == tx2_id

        # Step 5c CAS FAILS (simulate failure handler)
        tx.handle_post_pointer_switch_cas_failure(tx2_id, final_trans)

        # Assert pointer was rolled back to tx1_id because transition record is authentic
        assert tx.get_current_active_transaction_id() == tx1_id
        # Assert tx2_id entered QUARANTINED
        assert tx.get_durable_tx_state(tx2_id) == DurableTransactionState.QUARANTINED
        # Assert system entered QUARANTINE_LOCKED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


def test_post_pointer_switch_cas_failure_with_forged_transition_record_freezes_quarantine(
    storage_environment: tuple[Path, Ed25519TrustStore, StorageEngineSigner, str, str],
) -> None:
    """Test B88/B93 / Crash-12: If transition record signature is forged, rollback is FORBIDDEN."""
    root, trust_store, signer, app_key_id, app_priv = storage_environment
    ledger = AuthoritativeGOLedger(root, trust_store)

    tx1_id = uuid4()
    draft1, act1, go1 = _make_dummy_auth_and_go_record(app_key_id, app_priv, tx1_id, prev_head=GENESIS_HEAD_DIGEST)
    with ledger.exclusive_lock() as tx:
        tx.reserve_transaction_id(tx1_id)
        tx.compare_and_set_tx_state(tx1_id, DurableTransactionState.PREPARED, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx1_id, go1, draft1, act1, signer)

    tx2_id = uuid4()
    with ledger.exclusive_lock() as tx:
        # Switch pointer to tx2_id
        tx.switch_committed_snapshot_pointer_atomically(tx2_id)
        assert tx.get_current_active_transaction_id() == tx2_id

        # Forge transition record with attacker key
        forged_priv, _ = Ed25519Signer.generate_key_pair()
        trans_draft = DurablePointerTransitionRecord(
            pointer_version=2,
            previous_tx_id=tx1_id,
            new_tx_id=tx2_id,
            transition_timestamp_utc=datetime.now(timezone.utc),
            commit_intent_digest="forged_manifest" + "0" * 49,
            previous_pointer_digest=tx.get_current_pointer_digest(),
            transition_record_digest="",
            engine_signature="",
            engine_key_id=signer.key_id,
        )
        rec_dig = trans_draft.compute_canonical_digest()
        forged_sig = Ed25519Signer.sign(forged_priv, rec_dig.encode("utf-8"))
        forged_trans = trans_draft.model_copy(update={"transition_record_digest": rec_dig, "engine_signature": forged_sig})

        tx.handle_post_pointer_switch_cas_failure(tx2_id, forged_trans)

        # Rollback was strictly forbidden -> pointer was NOT restored
        assert tx.get_current_active_transaction_id() == tx2_id
        # State quarantined
        assert tx.get_durable_tx_state(tx2_id) == DurableTransactionState.QUARANTINED
        # System frozen in quarantine locked
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


def test_wal_journal_persistence(
    storage_environment: tuple[Path, Ed25519TrustStore, StorageEngineSigner, str, str],
) -> None:
    root, trust_store, _, _, _ = storage_environment
    ledger = AuthoritativeGOLedger(root, trust_store)
    tx_id = uuid4()

    with ledger.exclusive_lock() as tx:
        journal = tx.create_wal_journal(
            activation_transaction_id=tx_id,
            authorization_id="AUTH_TEST",
            go_record=None,
        )
        journal.write_state_durable(JournalState.PREPARED)
        assert journal.read_latest_state() == JournalState.PREPARED

        journal.write_state_durable(JournalState.COMMITTING)
        assert journal.read_latest_state() == JournalState.COMMITTING

        journal.write_state_durable(JournalState.COMMITTED)
        assert journal.read_latest_state() == JournalState.COMMITTED
