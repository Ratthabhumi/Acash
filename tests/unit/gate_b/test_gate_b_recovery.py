"""Phase 13 Slice 2: Unit Tests for Gate B Recovery Engine & Atomic Activation Manager (Stage 3.1).

Verifies:
- Blocker 1: Missing tx_state requires inspection of all durable commit evidence before Tier 1 abort
- Blocker 2: Fail-closed boundary checks durable commit evidence BEFORE writing terminal state
- Three-tier recovery decision tree starting strictly from tx_state (B92, B95)
- Proof of uncommitted state and strict B94 namespace separation
- Anti-silent rollback safeguards and forged transition rejection (B88, B93, Crash-12)
- Secondary WAL journal cannot elevate uncommitted state (B92)
- End-to-end atomic activation success path
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
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.execution.signing import (
    Ed25519Signer,
    StorageEngineSigner,
)
from acash.gate_b.exceptions import (
    DataContractError,
    PreLiveRiskAdmissionError,
    QuarantineError,
    StorageDurabilityError,
)
from acash.gate_b.recovery import (
    RecoveryDecisionTreeEngine,
    RecoveryResult,
    has_any_durable_commit_evidence,
    is_provably_uncommitted,
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
    AtomicActivationTransactionManager,
    GateBRecoveryCoordinator,
)
from acash.gate_b.storage import (
    AuthoritativeGOLedger,
    GENESIS_HEAD_DIGEST,
    LedgerStorageTransaction,
    StorageCommitContract,
    StoragePlatformUtils,
)


RecoveryEnvType = tuple[Path, Ed25519TrustStore, StorageEngineSigner, str, str, AuthoritativeGOLedger]


@pytest.fixture
def recovery_env(tmp_path: Path) -> Generator[RecoveryEnvType, None, None]:
    root = tmp_path / "gate_b_recovery"
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
) -> tuple[LiveAuthorization, LiveAuthorization, HumanGORecord]:
    now_utc = datetime.now(timezone.utc)
    exp_utc = now_utc + timedelta(hours=4)

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


def _has_staging(tx: LedgerStorageTransaction, tx_id: UUID) -> bool:
    return (tx._root / "staging" / str(tx_id)).exists()


def _read_authorization_from_snapshot(tx: LedgerStorageTransaction, tx_id: UUID) -> Optional[LiveAuthorization]:
    auth_file = tx._root / "snapshots" / str(tx_id) / "authorization.json"
    if not auth_file.exists():
        return None
    try:
        with open(auth_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            normalized = {}
            for k, v in data.items():
                if isinstance(v, dict) and "value" in v:
                    normalized[k] = v["value"]
                else:
                    normalized[k] = v
            return LiveAuthorization.model_validate(normalized)
    except Exception:
        return None


# ==============================================================================
# BLOCKER 1 TESTS: Missing tx_state Requires Commit Evidence Inspection
# ==============================================================================

def test_recovery_missing_tx_state_with_no_commit_evidence(recovery_env: RecoveryEnvType) -> None:
    """Blocker 1: Missing tx_state with provably zero commit evidence discards staging cleanly (Tier 1)."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()

    with ledger.exclusive_lock() as tx:
        # Create staging directory with scratch files
        stg = tx._get_staging_tx_dir(tx_id)
        stg.mkdir(parents=True, exist_ok=True)
        (stg / "scratch.tmp").write_text("uncommitted work", encoding="utf-8")
        assert _has_staging(tx, tx_id)

        # Assert no tx_state exists
        assert tx.get_durable_tx_state(tx_id) is None
        assert not has_any_durable_commit_evidence(tx, tx_id)

        result = RecoveryDecisionTreeEngine.evaluate_and_recover_transaction(tx, tx_id, trust_store, signer)

        assert result.tier == 1
        assert result.final_state == DurableTransactionState.ABORTED
        assert result.system_mode == SystemSafetyMode.NORMAL
        # Staging is discarded
        assert not _has_staging(tx, tx_id)
        assert tx.get_system_safety_mode() == SystemSafetyMode.NORMAL


def test_recovery_missing_tx_state_with_snapshot_evidence_quarantines(recovery_env: RecoveryEnvType) -> None:
    """Blocker 1: Missing tx_state when /snapshots/<tx_id> exists forces QUARANTINE_LOCKED (Tier 3)."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()

    with ledger.exclusive_lock() as tx:
        # Contradiction: No tx_state, but snapshot directory exists
        snap = tx._get_snapshot_tx_dir(tx_id)
        snap.mkdir(parents=True, exist_ok=True)
        (snap / "record.json").write_text("{}", encoding="utf-8")

        assert tx.get_durable_tx_state(tx_id) is None
        assert has_any_durable_commit_evidence(tx, tx_id)

        result = RecoveryDecisionTreeEngine.evaluate_and_recover_transaction(tx, tx_id, trust_store, signer)

        assert result.tier == 3
        assert result.final_state == DurableTransactionState.QUARANTINED
        assert result.system_mode == SystemSafetyMode.QUARANTINE_LOCKED
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


def test_recovery_missing_tx_state_with_pointer_evidence_quarantines(recovery_env: RecoveryEnvType) -> None:
    """Blocker 1: Missing tx_state when committed_pointer points to tx_id forces QUARANTINE_LOCKED (Tier 3)."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()

    with ledger.exclusive_lock() as tx:
        # Contradiction: No tx_state, but committed_pointer references tx_id
        tx.switch_committed_snapshot_pointer_atomically(tx_id)

        assert tx.get_durable_tx_state(tx_id) is None
        assert has_any_durable_commit_evidence(tx, tx_id)

        result = RecoveryDecisionTreeEngine.evaluate_and_recover_transaction(tx, tx_id, trust_store, signer)

        assert result.tier == 3
        assert result.final_state == DurableTransactionState.QUARANTINED
        assert result.system_mode == SystemSafetyMode.QUARANTINE_LOCKED
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


# ==============================================================================
# BLOCKER 2 TESTS: Authoritative Pre-Commit Decision Gate on Exception
# ==============================================================================

def test_transaction_manager_failure_after_snapshot_promotion_quarantines_without_writing_aborted(
    recovery_env: RecoveryEnvType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blocker 2: Failure after snapshot promotion MUST NOT write ABORTED; must enter QUARANTINE_LOCKED (Tier 3)."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id_dummy = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id_dummy)

    # Save draft in drafts dir
    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)

    manager = AtomicActivationTransactionManager(ledger, trust_store, signer)

    # Simulate failure in Phase 5: after promotion to snapshots, pointer switch fails
    def failing_switch(self: LedgerStorageTransaction, tid: UUID) -> None:
        raise RuntimeError("SIMULATED_FAILURE_POST_PROMOTION")

    monkeypatch.setattr(LedgerStorageTransaction, "switch_committed_snapshot_pointer_atomically", failing_switch)

    with pytest.raises(QuarantineError) as exc_info:
        manager.execute_activation(draft, go_rec)

    assert "ACTIVATION_COMMIT_UNCERTAIN" in str(exc_info.value)

    with ledger.exclusive_lock() as tx:
        # Find the transaction ID created during activation
        tx_ids = [UUID(f.stem) for f in (root / "tx_state").glob("*.state")]
        assert len(tx_ids) == 1
        active_tx_id = tx_ids[0]

        # INVARIANT: MUST NOT BE ABORTED! Must be QUARANTINED.
        assert tx.get_durable_tx_state(active_tx_id) == DurableTransactionState.QUARANTINED
        # INVARIANT: ZERO abort record written!
        assert tx.read_durable_abort_record(active_tx_id) is None
        # INVARIANT: System mode locked
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


def test_transaction_manager_pre_commit_failure_clean_aborts(
    recovery_env: RecoveryEnvType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blocker 2: Pre-commit failure provably before snapshot promotion cleanly writes ABORTED (Tier 1)."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id_dummy = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id_dummy)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)

    manager = AtomicActivationTransactionManager(ledger, trust_store, signer)

    # Simulate failure in Phase 1: writing staged mutation data fails
    def failing_write_staged(self: LedgerStorageTransaction, tid: UUID, rec: HumanGORecord, act: LiveAuthorization) -> None:
        raise RuntimeError("SIMULATED_PRE_COMMIT_DISK_ERROR")

    monkeypatch.setattr(LedgerStorageTransaction, "write_staged_mutation_data", failing_write_staged)

    with pytest.raises(DataContractError) as exc_info:
        manager.execute_activation(draft, go_rec)

    assert "ACTIVATION_PRE_COMMIT_ABORTED" in str(exc_info.value)

    with ledger.exclusive_lock() as tx:
        tx_ids = [UUID(f.stem) for f in (root / "tx_state").glob("*.state")]
        assert len(tx_ids) == 1
        active_tx_id = tx_ids[0]

        # Terminal state must be ABORTED
        assert tx.get_durable_tx_state(active_tx_id) == DurableTransactionState.ABORTED
        abort_record = tx.read_durable_abort_record(active_tx_id)
        assert abort_record is not None
        assert abort_record.is_valid()
        assert abort_record.terminal_state == DurableTransactionState.ABORTED
        # Staging discarded
        assert not _has_staging(tx, active_tx_id)
        # System safety mode remains NORMAL
        assert tx.get_system_safety_mode() == SystemSafetyMode.NORMAL


# ==============================================================================
# PROOF OF UNCOMMITTED STATE & B94 NAMESPACE INVARIANTS
# ==============================================================================

def test_is_provably_uncommitted_valid_abort(recovery_env: RecoveryEnvType) -> None:
    """Assert is_provably_uncommitted succeeds for cleanly terminated abort."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()
    draft, _, _ = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.ABORTED)

        abort_block = AuthoritativeAbortRecordBlock(
            activation_transaction_id=tx_id,
            pre_transaction_head_digest=GENESIS_HEAD_DIGEST,
            authorization_id=draft.authorization_id,
            approved_authorization_digest=draft.approved_authorization_digest,
            expected_previous_state=DurableTransactionState.COMMITTING,
            terminal_state=DurableTransactionState.ABORTED,
            abort_reason_code="SimulatedPreCommitFailure",
            abort_timestamp_utc=datetime.now(timezone.utc),
            abort_record_digest="",
        )
        final_block = abort_block.model_copy(update={"abort_record_digest": abort_block.compute_digest()})
        tx.write_durable_abort_record(final_block)
        tx.flush_abort_record_barrier(tx_id)

        assert is_provably_uncommitted(tx, tx_id, draft) is True


def test_is_provably_uncommitted_fails_when_snapshot_dir_exists(recovery_env: RecoveryEnvType) -> None:
    """B94 Invariant: Residual /snapshots/<tx_id>/ directory invalidates proof of uncommitted state."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()
    draft, _, _ = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.ABORTED)

        abort_block = AuthoritativeAbortRecordBlock(
            activation_transaction_id=tx_id,
            pre_transaction_head_digest=GENESIS_HEAD_DIGEST,
            authorization_id=draft.authorization_id,
            approved_authorization_digest=draft.approved_authorization_digest,
            expected_previous_state=DurableTransactionState.COMMITTING,
            terminal_state=DurableTransactionState.ABORTED,
            abort_reason_code="SimulatedPreCommitFailure",
            abort_timestamp_utc=datetime.now(timezone.utc),
            abort_record_digest="",
        )
        final_block = abort_block.model_copy(update={"abort_record_digest": abort_block.compute_digest()})
        tx.write_durable_abort_record(final_block)
        tx.flush_abort_record_barrier(tx_id)

        # Fatal violation: snapshot dir exists for aborted transaction!
        (tx._root / "snapshots" / str(tx_id)).mkdir(parents=True, exist_ok=True)

        assert is_provably_uncommitted(tx, tx_id, draft) is False


def test_is_provably_uncommitted_fails_when_pointer_references_aborted_tx(recovery_env: RecoveryEnvType) -> None:
    """Contradiction: Pointer referencing aborted transaction invalidates uncommitted proof."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()
    draft, _, _ = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.ABORTED)

        abort_block = AuthoritativeAbortRecordBlock(
            activation_transaction_id=tx_id,
            pre_transaction_head_digest=GENESIS_HEAD_DIGEST,
            authorization_id=draft.authorization_id,
            approved_authorization_digest=draft.approved_authorization_digest,
            expected_previous_state=DurableTransactionState.COMMITTING,
            terminal_state=DurableTransactionState.ABORTED,
            abort_reason_code="SimulatedPreCommitFailure",
            abort_timestamp_utc=datetime.now(timezone.utc),
            abort_record_digest="",
        )
        final_block = abort_block.model_copy(update={"abort_record_digest": abort_block.compute_digest()})
        tx.write_durable_abort_record(final_block)

        # Contradiction: pointer active for aborted transaction
        tx.switch_committed_snapshot_pointer_atomically(tx_id)

        assert is_provably_uncommitted(tx, tx_id, draft) is False


def test_is_provably_uncommitted_fails_when_commit_marker_present(recovery_env: RecoveryEnvType) -> None:
    """Contradiction: Commit marker block on aborted transaction invalidates uncommitted proof."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()
    draft, _, _ = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.ABORTED)

        abort_block = AuthoritativeAbortRecordBlock(
            activation_transaction_id=tx_id,
            pre_transaction_head_digest=GENESIS_HEAD_DIGEST,
            authorization_id=draft.authorization_id,
            approved_authorization_digest=draft.approved_authorization_digest,
            expected_previous_state=DurableTransactionState.COMMITTING,
            terminal_state=DurableTransactionState.ABORTED,
            abort_reason_code="SimulatedPreCommitFailure",
            abort_timestamp_utc=datetime.now(timezone.utc),
            abort_record_digest="",
        )
        final_block = abort_block.model_copy(update={"abort_record_digest": abort_block.compute_digest()})
        tx.write_durable_abort_record(final_block)

        # Contradiction: commit marker written to staging
        stg = tx._get_staging_tx_dir(tx_id)
        stg.mkdir(parents=True, exist_ok=True)
        (stg / "commit_record_block.json").write_text("{}", encoding="utf-8")

        assert is_provably_uncommitted(tx, tx_id, draft) is False


# ==============================================================================
# THREE-TIER RECOVERY DECISION TREE TESTS (B92, B95)
# ==============================================================================

def test_recovery_tier1_clean_abort_discards_staging(recovery_env: RecoveryEnvType) -> None:
    """Tier 1: Proven terminal abort discards staging and leaves status unchanged."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()
    draft, _, _ = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.ABORTED)

        abort_block = AuthoritativeAbortRecordBlock(
            activation_transaction_id=tx_id,
            pre_transaction_head_digest=GENESIS_HEAD_DIGEST,
            authorization_id=draft.authorization_id,
            approved_authorization_digest=draft.approved_authorization_digest,
            expected_previous_state=DurableTransactionState.COMMITTING,
            terminal_state=DurableTransactionState.ABORTED,
            abort_reason_code="CleanPreCommitAbort",
            abort_timestamp_utc=datetime.now(timezone.utc),
            abort_record_digest="",
        )
        final_block = abort_block.model_copy(update={"abort_record_digest": abort_block.compute_digest()})
        tx.write_durable_abort_record(final_block)
        tx.flush_abort_record_barrier(tx_id)

        stg = tx._get_staging_tx_dir(tx_id)
        stg.mkdir(parents=True, exist_ok=True)
        (stg / "staged.tmp").write_text("residual", encoding="utf-8")

        result = RecoveryDecisionTreeEngine.evaluate_and_recover_transaction(tx, tx_id, trust_store, signer)

        assert result.tier == 1
        assert result.final_state == DurableTransactionState.ABORTED
        assert result.system_mode == SystemSafetyMode.NORMAL
        assert not _has_staging(tx, tx_id)


def test_recovery_tier2_committed_idempotent_noop(recovery_env: RecoveryEnvType) -> None:
    """Tier 2: Fully committed transaction re-verifies idempotently and synchronizes journal."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)

        # Commit durable transaction
        commit_block = StorageCommitContract.execute_durable_commit(
            tx=tx,
            tx_id=tx_id,
            go_record=go_rec,
            approved_auth=draft,
            activated_auth=act_auth,
            engine_signer=signer,
        )

        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.COMMITTED

        # Clear journal to test journal reconstruction
        journal = tx.create_wal_journal(tx_id, draft.authorization_id, None)
        if journal.journal_path.exists():
            journal.journal_path.unlink()

        result = RecoveryDecisionTreeEngine.evaluate_and_recover_transaction(tx, tx_id, trust_store, signer)

        assert result.tier == 2
        assert result.final_state == DurableTransactionState.COMMITTED
        assert result.system_mode == SystemSafetyMode.NORMAL
        assert journal.read_latest_state() == JournalState.COMMITTED


def test_recovery_tier2_committing_with_valid_pointer_recovers_to_committed(recovery_env: RecoveryEnvType) -> None:
    """Tier 2: In-flight commit with active pointer and authentic transition CAS-recovers to COMMITTED."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)

        # Execute commit phases 1 through 5b, but omit Step 5c (CAS to COMMITTED)
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
        final_trans = transition_draft.model_copy(update={
            "transition_record_digest": rec_digest,
            "engine_signature": raw_sig,
        })
        tx.write_durable_pointer_transition_record(final_trans)
        tx.flush_pointer_transition_barrier()
        tx.switch_committed_snapshot_pointer_atomically(tx_id)

        # Simulating crash: tx_state is STILL COMMITTING on disk!
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.COMMITTING

        result = RecoveryDecisionTreeEngine.evaluate_and_recover_transaction(tx, tx_id, trust_store, signer)

        assert result.tier == 2
        assert result.final_state == DurableTransactionState.COMMITTED
        assert result.system_mode == SystemSafetyMode.NORMAL
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.COMMITTED
        assert tx.get_durable_head_digest() == go_rec.record_digest


def test_recovery_tier3_committing_with_forged_transition_signature_freezes_quarantine(recovery_env: RecoveryEnvType) -> None:
    """Tier 3 (B88, B93, Crash-12): Forged transition signature on in-flight commit freezes in QUARANTINE_LOCKED."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()
    draft, act_auth, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
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

        # Forged transition record: signed by an unknown attacker key
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
            engine_key_id="KEY_ATTACKER_UNTRUSTED",
        )
        rec_digest = transition_draft.compute_canonical_digest()
        forged_sig = Ed25519Signer.sign(attacker_priv, rec_digest.encode("utf-8"))
        final_trans = transition_draft.model_copy(update={
            "transition_record_digest": rec_digest,
            "engine_signature": forged_sig,
        })
        tx.write_durable_pointer_transition_record(final_trans)
        tx.switch_committed_snapshot_pointer_atomically(tx_id)

        result = RecoveryDecisionTreeEngine.evaluate_and_recover_transaction(tx, tx_id, trust_store, signer)

        assert result.tier == 3
        assert result.final_state == DurableTransactionState.QUARANTINED
        assert result.system_mode == SystemSafetyMode.QUARANTINE_LOCKED
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


def test_recovery_tier3_aborted_with_residual_snapshot_triggers_quarantine_locked(recovery_env: RecoveryEnvType) -> None:
    """Tier 3 (B94): Aborted transaction possessing residual snapshot forces QUARANTINE_LOCKED."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()
    draft, _, _ = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.ABORTED)

        abort_block = AuthoritativeAbortRecordBlock(
            activation_transaction_id=tx_id,
            pre_transaction_head_digest=GENESIS_HEAD_DIGEST,
            authorization_id=draft.authorization_id,
            approved_authorization_digest=draft.approved_authorization_digest,
            expected_previous_state=DurableTransactionState.COMMITTING,
            terminal_state=DurableTransactionState.ABORTED,
            abort_reason_code="SimulatedPreCommitFailure",
            abort_timestamp_utc=datetime.now(timezone.utc),
            abort_record_digest="",
        )
        final_block = abort_block.model_copy(update={"abort_record_digest": abort_block.compute_digest()})
        tx.write_durable_abort_record(final_block)

        # Fatal contradiction: snapshot directory exists for aborted tx
        (tx._root / "snapshots" / str(tx_id)).mkdir(parents=True, exist_ok=True)

        result = RecoveryDecisionTreeEngine.evaluate_and_recover_transaction(tx, tx_id, trust_store, signer)

        assert result.tier == 3
        assert result.final_state == DurableTransactionState.QUARANTINED
        assert result.system_mode == SystemSafetyMode.QUARANTINE_LOCKED
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


def test_recovery_journal_committed_cannot_override_uncommitted_tx_state(recovery_env: RecoveryEnvType) -> None:
    """Tier 3 (B92): Secondary WAL journal marked COMMITTED while tx_state is uncommitted cannot elevate state."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id = uuid4()
    draft, _, _ = _make_dummy_artifacts(app_key_id, app_priv, tx_id)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        # On-disk state is PREPARED (uncommitted)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.PREPARED)

        # Malformed / divergent journal claiming COMMITTED
        journal = tx.create_wal_journal(tx_id, draft.authorization_id, None)
        journal.write_state_durable(JournalState.COMMITTED)

        result = RecoveryDecisionTreeEngine.evaluate_and_recover_transaction(tx, tx_id, trust_store, signer)

        # B92: MUST NOT elevate to COMMITTED; must enter QUARANTINED
        assert result.tier == 3
        assert result.final_state == DurableTransactionState.QUARANTINED
        assert result.system_mode == SystemSafetyMode.QUARANTINE_LOCKED
        assert tx.get_durable_tx_state(tx_id) == DurableTransactionState.QUARANTINED
        assert tx.get_system_safety_mode() == SystemSafetyMode.QUARANTINE_LOCKED


# ==============================================================================
# END-TO-END TRANSACTION MANAGER & COORDINATOR SUCCESS PATH
# ==============================================================================

def test_transaction_manager_activation_success_path(recovery_env: RecoveryEnvType) -> None:
    """Full end-to-end atomic strategy activation lifecycle from draft to ACTIVE."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env
    tx_id_dummy = uuid4()
    draft, _, go_rec = _make_dummy_artifacts(app_key_id, app_priv, tx_id_dummy)

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)

    manager = AtomicActivationTransactionManager(ledger, trust_store, signer)
    activated_auth = manager.execute_activation(draft, go_rec)

    assert activated_auth.status == LiveAuthorizationStatus.ACTIVE
    assert activated_auth.activated_at is not None
    assert activated_auth.activated_at.tzinfo == timezone.utc
    assert activated_auth.activation_transaction_id is not None
    assert activated_auth.activated_authorization_digest is not None
    assert activated_auth.active_go_record_digest == go_rec.record_digest

    with ledger.exclusive_lock() as tx:
        committed_tx_id = activated_auth.activation_transaction_id
        assert tx.get_durable_tx_state(committed_tx_id) == DurableTransactionState.COMMITTED
        assert tx.committed_pointer_references_transaction(committed_tx_id) is True
        assert tx.get_durable_head_digest() == go_rec.record_digest
        assert tx.get_system_safety_mode() == SystemSafetyMode.NORMAL

        # Snapshot read-only verification
        snap_dir = tx._get_snapshot_tx_dir(committed_tx_id)
        assert snap_dir.exists()
        auth_from_snap = _read_authorization_from_snapshot(tx, committed_tx_id)
        assert auth_from_snap is not None
        assert auth_from_snap.status == LiveAuthorizationStatus.ACTIVE
        assert auth_from_snap.activated_authorization_digest == activated_auth.activated_authorization_digest


def test_recovery_coordinator_startup_scan(recovery_env: RecoveryEnvType) -> None:
    """GateBRecoveryCoordinator scans storage substrate and executes recovery on all unfinalized transactions."""
    root, trust_store, signer, app_key_id, app_priv, ledger = recovery_env

    # 1. Setup a clean committed transaction
    tx1_id = uuid4()
    draft1, act1, go1 = _make_dummy_artifacts(app_key_id, app_priv, tx1_id)
    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft1)
        tx.set_tx_state_durable(tx1_id, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx1_id, go1, draft1, act1, signer)

    # 2. Setup an uncommitted transaction with scratch staging (should clean abort)
    tx2_id = uuid4()
    with ledger.exclusive_lock() as tx:
        tx.reserve_transaction_id(tx2_id)  # PREPARED
        stg = tx._get_staging_tx_dir(tx2_id)
        stg.mkdir(parents=True, exist_ok=True)
        (stg / "stg.tmp").write_text("abandoned", encoding="utf-8")

    coordinator = GateBRecoveryCoordinator(ledger, trust_store, signer)
    results = coordinator.run_recovery()

    assert tx1_id in results
    assert results[tx1_id].tier == 2
    assert results[tx1_id].final_state == DurableTransactionState.COMMITTED

    assert tx2_id in results
    assert results[tx2_id].tier == 1
    assert results[tx2_id].final_state == DurableTransactionState.ABORTED

    with ledger.exclusive_lock() as tx:
        assert not _has_staging(tx, tx2_id)
        assert tx.get_system_safety_mode() == SystemSafetyMode.NORMAL
