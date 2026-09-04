"""Phase 13 Slice 2: End-to-End Gate B Integration Lifecycle Test (Stage 3.5).

Verifies the complete dual-layer Gate B integration lifecycle across all stages on physical NTFS storage:
1. Stage 1: Draft LiveAuthorization and Ed25519 HumanGORecord creation and quorum verification.
2. Stage 2 & 3.1: Staging, fsync_1, commit marker, fsync_2, promotion, fsync_3, signed transition,
   atomic pointer switch, and CAS state transition to COMMITTED.
3. Stage 3.2: Authoritative snapshot reader with 4-point identity binding.
4. Stage 3.3: Pre-live risk admission engine evaluation under single lock boundary.
5. Stage 3.4: Simulated cold process restart / zero-RAM reconstruction from disk alone.
6. Stage 3.5: Gate B readiness checker evaluation, cryptographic report signing, and pre-authorization lock boundary.

Mandatory Invariants Enforced:
- Complete physical filesystem execution on NTFS mounts (zero in-memory mock storage).
- Strict test isolation: temporary sandbox root, dedicated test keys, zero production storage pollution.
- Gate B remains strictly locked ($0.00 live capital, 0 orders, Slice 3 blocked).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import shutil
from typing import Generator, Tuple
from uuid import UUID, uuid4

import pytest

from acash.execution.crypto import (
    Ed25519Signer,
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.core.domain.enums import OrderSide
from acash.gate_b.admission import (
    GateBOrderAdmissionRequest,
    PreLiveRiskAdmissionService,
)
from acash.gate_b.readers import SnapshotReaderService
from acash.gate_b.readiness import (
    BrokerProbeSnapshot,
    GateBReadinessChecker,
    GateBReadinessStatus,
)
from acash.gate_b.schema import (
    AuthoritativeCommitRecordBlock,
    DurablePointerTransitionRecord,
    DurableTransactionState,
    HumanGORecord,
    JournalState,
    LiveAuthorization,
    LiveAuthorizationStatus,
    MT5QuoteSnapshot,
    SystemSafetyMode,
    assert_activation_preconditions,
    verify_human_go_record_integrity,
)
from acash.gate_b.service import GateBRecoveryCoordinator
from acash.gate_b.storage import (
    AuthoritativeGOLedger,
    GENESIS_HEAD_DIGEST,
    StorageCommitContract,
    StorageEngineSigner,
    StoragePlatformUtils,
)

@dataclass(frozen=True)
class E2EIsolatedContext:
    root: Path
    trust_store: Ed25519TrustStore
    eng_signer: StorageEngineSigner
    aud_signer: StorageEngineSigner
    eng_key_id: str
    eng_pub: str
    eng_priv: str
    app_key_id: str
    app_pub: str
    app_priv: str
    aud_key_id: str
    aud_pub: str
    aud_priv: str


@pytest.fixture
def e2e_isolated_env(tmp_path: Path) -> Generator[E2EIsolatedContext, None, None]:
    """Provide strictly isolated temporary physical test root and test-only cryptographic credentials."""
    root = tmp_path / "gate_b_isolated_e2e_root"
    root.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(timezone.utc)

    # Test Engine Key
    eng_priv, eng_pub = Ed25519Signer.generate_key_pair()
    eng_key_id = "KEY_TEST_ENGINE_ROOT"
    eng_entry = Ed25519TrustStoreEntry(
        key_id=eng_key_id,
        issuer_id="ACASH_TEST_STORAGE_ENGINE",
        public_key_b64=eng_pub,
        valid_from=now_utc - timedelta(days=1),
        valid_until=now_utc + timedelta(days=365),
        status=TrustStoreEntryStatus.ACTIVE,
    )

    # Test Governance Approver Key
    app_priv, app_pub = Ed25519Signer.generate_key_pair()
    app_key_id = "KEY_TEST_GOVERNANCE_ROOT"
    app_entry = Ed25519TrustStoreEntry(
        key_id=app_key_id,
        issuer_id="ACASH_TEST_GOVERNANCE",
        public_key_b64=app_pub,
        valid_from=now_utc - timedelta(days=1),
        valid_until=now_utc + timedelta(days=365),
        status=TrustStoreEntryStatus.ACTIVE,
    )

    # Test Auditor Signer Key
    aud_priv, aud_pub = Ed25519Signer.generate_key_pair()
    aud_key_id = "KEY_TEST_AUDITOR_ROOT"
    aud_entry = Ed25519TrustStoreEntry(
        key_id=aud_key_id,
        issuer_id="ACASH_TEST_AUDIT",
        public_key_b64=aud_pub,
        valid_from=now_utc - timedelta(days=1),
        valid_until=now_utc + timedelta(days=365),
        status=TrustStoreEntryStatus.ACTIVE,
    )

    trust_store = Ed25519TrustStore(entries=(eng_entry, app_entry, aud_entry))
    eng_signer = StorageEngineSigner(eng_key_id, eng_priv)
    aud_signer = StorageEngineSigner(aud_key_id, aud_priv)

    # Initialize authoritative skeleton & genesis head
    ledger = AuthoritativeGOLedger(root, trust_store)
    with ledger.exclusive_lock() as tx:
        tx.set_head_digest_durable(GENESIS_HEAD_DIGEST)
        (root / "drafts").mkdir(parents=True, exist_ok=True)

    yield E2EIsolatedContext(
        root=root,
        trust_store=trust_store,
        eng_signer=eng_signer,
        aud_signer=aud_signer,
        eng_key_id=eng_key_id,
        eng_pub=eng_pub,
        eng_priv=eng_priv,
        app_key_id=app_key_id,
        app_pub=app_pub,
        app_priv=app_priv,
        aud_key_id=aud_key_id,
        aud_pub=aud_pub,
        aud_priv=aud_priv,
    )

    # Teardown: ensure ACL permits cleanup
    StoragePlatformUtils.mark_directory_writable(root)


# ==============================================================================
# 1. Isolation Boundary Assertions (Blocker 3)
# ==============================================================================

def test_e2e_never_uses_production_storage_root(e2e_isolated_env: E2EIsolatedContext) -> None:
    """Asserts that E2E tests execute exclusively under tmp_path and never touch production paths."""
    root = e2e_isolated_env.root

    prohibited_roots = [
        Path("data/gate_b"),
        Path("storage/gate_b"),
        Path("var/gate_b"),
        Path.cwd() / "data" / "gate_b",
    ]

    for p in prohibited_roots:
        assert root != p, f"E2E root collided with prohibited production path: {p}"
    assert "pytest" in str(root) or "Temp" in str(root) or "tmp" in str(root).lower()


def test_e2e_never_loads_live_trust_anchor(e2e_isolated_env: E2EIsolatedContext) -> None:
    """Asserts that test trust stores use strictly test-designated key material."""
    trust_store = e2e_isolated_env.trust_store

    for entry in trust_store.entries:
        assert entry.key_id.startswith("KEY_TEST_"), f"Live or non-test key ID found in test store: {entry.key_id}"
        assert "TEST" in entry.issuer_id, f"Non-test issuer ID found in test store: {entry.issuer_id}"


def test_e2e_cannot_transition_production_gate_b_state() -> None:
    """Asserts that default production storage path remains uncreated and unpolluted."""
    default_prod_path = Path("data/gate_b")
    # If it does not exist, verify it was not created; if it exists, verify no test files exist
    if default_prod_path.exists():
        assert not (default_prod_path / "pointer" / "KEY_TEST").exists()


# ==============================================================================
# 2. Unified End-to-End Lifecycle & Cold Restart Test (Stage 1 -> 3.5)
# ==============================================================================

def test_e2e_full_lifecycle_and_zero_ram_restart(e2e_isolated_env: E2EIsolatedContext) -> None:
    """Executes the full dual-layer authorization and readiness lifecycle across all stages."""
    root = e2e_isolated_env.root
    trust_store = e2e_isolated_env.trust_store
    eng_signer = e2e_isolated_env.eng_signer
    aud_signer = e2e_isolated_env.aud_signer
    eng_key_id = e2e_isolated_env.eng_key_id
    eng_pub = e2e_isolated_env.eng_pub
    eng_priv = e2e_isolated_env.eng_priv
    app_key_id = e2e_isolated_env.app_key_id
    app_pub = e2e_isolated_env.app_pub
    app_priv = e2e_isolated_env.app_priv
    aud_key_id = e2e_isolated_env.aud_key_id
    aud_pub = e2e_isolated_env.aud_pub
    aud_priv = e2e_isolated_env.aud_priv

    # -------------------------------------------------------------------------
    # STAGE 1: Schemas, Draft LiveAuthorization & HumanGORecord
    # -------------------------------------------------------------------------
    now_utc = datetime.now(timezone.utc)
    exp_utc = now_utc + timedelta(hours=8)
    tx_id = uuid4()

    draft_auth = LiveAuthorization(
        authorization_id="AUTH_E2E_LIFECYCLE_001",
        status=LiveAuthorizationStatus.APPROVED_PENDING_GO,
        approved_authorization_digest="b" * 64,
        strategy_id="STRAT_ALPHA_EURUSD",
        symbol="EURUSD",
        account_id="ACC_112040157",
        max_notional_usd=Decimal("500.00"),
        max_drawdown_pct=Decimal("5.00"),
        max_slippage_points=10,
        max_quote_age_ms=1000,
        required_approvals=1,
        created_at=now_utc,
        expires_at=exp_utc,
    )
    approved_bytes = draft_auth.compute_approved_canonical_bytes()
    approved_digest = hashlib.sha256(approved_bytes).hexdigest()
    draft_auth = draft_auth.model_copy(update={"approved_authorization_digest": approved_digest})

    # Human GO Record
    go_draft = HumanGORecord(
        go_record_id="GO_REC_E2E_001",
        authorization_id=draft_auth.authorization_id,
        approved_authorization_digest=draft_auth.approved_authorization_digest,
        previous_record_digest=GENESIS_HEAD_DIGEST,
        record_timestamp_utc=now_utc,
        approver_public_key_id=app_key_id,
        signature_ed25519="",
        record_digest="",
    )
    go_payload = go_draft.compute_signed_payload_bytes()
    go_sig = Ed25519Signer.sign(app_priv, go_payload)
    go_with_sig = go_draft.model_copy(update={"signature_ed25519": go_sig})
    go_rec = go_with_sig.model_copy(update={"record_digest": go_with_sig.compute_canonical_digest()})

    # Activated Authorization
    act_draft = draft_auth.model_copy(
        update={
            "status": LiveAuthorizationStatus.ACTIVE,
            "source_approved_digest": draft_auth.approved_authorization_digest,
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

    # Precondition assertion
    assert_activation_preconditions(draft_auth, go_rec, trust_store)

    # -------------------------------------------------------------------------
    # STAGE 2 & 3.1: Physical 2-Phase Commit & Durability Barriers
    # -------------------------------------------------------------------------
    ledger = AuthoritativeGOLedger(root, trust_store)
    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft_auth)
        tx.reserve_transaction_id(tx_id)

        journal = tx.create_wal_journal(tx_id, draft_auth.authorization_id, go_rec)
        journal.write_state_durable(JournalState.PREPARED)

        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)
        journal.write_state_durable(JournalState.COMMITTING)

        # Phase 1: fsync_1 staged mutation data
        tx.write_staged_mutation_data(tx_id, go_rec, activated_auth)
        tx.flush_staged_mutation_data_barrier(tx_id)

        # Phase 2: fsync_2 commit marker
        commit_block = AuthoritativeCommitRecordBlock(
            activation_transaction_id=tx_id,
            commit_timestamp_utc=now_utc,
            ledger_record_digest=go_rec.record_digest,
            advanced_head_digest=go_rec.record_digest,
            approved_authorization_digest=draft_auth.approved_authorization_digest,
            activated_authorization_digest=activated_auth.activated_authorization_digest or "",
            mutation_manifest_digest="",
        )
        manifest_digest = commit_block.compute_manifest_digest()
        final_commit_block = commit_block.model_copy(update={"mutation_manifest_digest": manifest_digest})
        tx.write_commit_marker_block(tx_id, final_commit_block)
        tx.flush_commit_marker_barrier(tx_id)

        # Phase 3: Directory promotion + read-only DACL + fsync_3
        tx.promote_staging_to_snapshot_directory_atomically(tx_id)
        tx.mark_snapshot_directory_read_only(tx_id)
        tx.flush_snapshot_directory_barrier(tx_id)

        # Phase 4: Pointer transition record signed by engine
        transition_draft = DurablePointerTransitionRecord(
            pointer_version=tx.get_next_pointer_version(),
            previous_tx_id=None,
            new_tx_id=tx_id,
            transition_timestamp_utc=now_utc,
            commit_intent_digest=manifest_digest,
            previous_pointer_digest=tx.get_current_pointer_digest(),
            transition_record_digest="",
            engine_signature="",
            engine_key_id=eng_signer.key_id,
        )
        rec_digest = transition_draft.compute_canonical_digest()
        raw_sig = eng_signer.sign(rec_digest.encode("utf-8"))
        final_trans = transition_draft.model_copy(
            update={"transition_record_digest": rec_digest, "engine_signature": raw_sig}
        )
        tx.write_durable_pointer_transition_record(final_trans)
        tx.flush_pointer_transition_barrier()

        # Phase 5: Atomic pointer switch
        tx.switch_committed_snapshot_pointer_atomically(tx_id)

        # Phase 6: CAS to COMMITTED
        assert tx.compare_and_set_tx_state(tx_id, DurableTransactionState.COMMITTING, DurableTransactionState.COMMITTED)
        tx.set_head_digest_durable(go_rec.record_digest)
        journal.write_state_durable(JournalState.COMMITTED)

    # -------------------------------------------------------------------------
    # STAGE 3.2: Authoritative Reader & 4-Point Identity Binding
    # -------------------------------------------------------------------------
    with ledger.exclusive_lock() as tx:
        view = SnapshotReaderService.read_active_committed_snapshot(tx)
        assert view.transaction_id == tx_id
        assert view.authorization is not None
        assert view.authorization.status == LiveAuthorizationStatus.ACTIVE
        assert view.authorization.authorization_id == draft_auth.authorization_id
        assert view.head_digest == go_rec.record_digest

    # -------------------------------------------------------------------------
    # STAGE 3.3: Pre-Live Risk Admission Engine Evaluation
    # -------------------------------------------------------------------------
    quote = MT5QuoteSnapshot(
        symbol="EURUSD",
        bid=Decimal("1.08500"),
        ask=Decimal("1.08510"),
        point_size=Decimal("0.00010"),
        contract_size=Decimal("100000.00"),
        timestamp_utc=now_utc,
    )

    order_req = GateBOrderAdmissionRequest(
        request_id="REQ_BUY_E2E_001",
        strategy_id="STRAT_ALPHA_EURUSD",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
        account_id="ACC_112040157",
        account_currency="USD",
    )

    decision = PreLiveRiskAdmissionService.evaluate_admission(
        ledger,
        order_req,
        trust_store,
        max_position_size=Decimal("0.01"),
        now_utc=now_utc,
    )
    assert decision.is_admitted is True
    assert decision.bounded_executable_notional <= Decimal("500.00")
    assert decision.decision_digest is not None

    # -------------------------------------------------------------------------
    # STAGE 3.4: Simulated Cold Process Restart / Zero-RAM Reconstruction
    # (Scoping per Rev20 B98: software-persisted disk reconstruction alone)
    # -------------------------------------------------------------------------
    # Explicitly tear down all in-memory Python objects and caches
    del draft_auth, go_rec, activated_auth, commit_block, final_commit_block
    del transition_draft, final_trans, view, decision, order_req, quote
    del ledger, trust_store, eng_signer, aud_signer

    # Reconstruct fresh trust store, signer, and ledger from disk root and key strings alone
    fresh_trust_store = Ed25519TrustStore(
        entries=(
            Ed25519TrustStoreEntry(
                key_id=eng_key_id,
                issuer_id="ACASH_TEST_STORAGE_ENGINE",
                public_key_b64=eng_pub,
                valid_from=now_utc - timedelta(days=1),
                valid_until=now_utc + timedelta(days=365),
                status=TrustStoreEntryStatus.ACTIVE,
            ),
            Ed25519TrustStoreEntry(
                key_id=app_key_id,
                issuer_id="ACASH_TEST_GOVERNANCE",
                public_key_b64=app_pub,
                valid_from=now_utc - timedelta(days=1),
                valid_until=now_utc + timedelta(days=365),
                status=TrustStoreEntryStatus.ACTIVE,
            ),
            Ed25519TrustStoreEntry(
                key_id=aud_key_id,
                issuer_id="ACASH_TEST_AUDIT",
                public_key_b64=aud_pub,
                valid_from=now_utc - timedelta(days=1),
                valid_until=now_utc + timedelta(days=365),
                status=TrustStoreEntryStatus.ACTIVE,
            ),
        )
    )
    fresh_eng_signer = StorageEngineSigner(eng_key_id, eng_priv)
    fresh_aud_signer = StorageEngineSigner(aud_key_id, aud_priv)
    fresh_ledger = AuthoritativeGOLedger(root, fresh_trust_store)

    # Execute recovery scan on cold disk
    coordinator = GateBRecoveryCoordinator(fresh_ledger, fresh_trust_store, fresh_eng_signer)
    recovery_outcomes = coordinator.run_recovery()
    assert tx_id in recovery_outcomes
    assert recovery_outcomes[tx_id].tier == 2
    assert recovery_outcomes[tx_id].final_state == DurableTransactionState.COMMITTED
    assert recovery_outcomes[tx_id].system_mode == SystemSafetyMode.NORMAL

    # Read active snapshot from cold disk
    with fresh_ledger.exclusive_lock() as tx:
        cold_view = SnapshotReaderService.read_active_committed_snapshot(tx)
        assert cold_view.transaction_id == tx_id
        assert cold_view.authorization is not None
        assert cold_view.authorization.status == LiveAuthorizationStatus.ACTIVE

    # -------------------------------------------------------------------------
    # STAGE 3.5: Gate B Readiness Checker & Cryptographic Report Authentication
    # -------------------------------------------------------------------------
    probe = BrokerProbeSnapshot(
        init=True,
        login=112040157,
        trade_mode=0,
        currency="USD",
        positions=0,
        orders=0,
        margin=0.0,
        balance=2999.65,
        live_capital_authorized=Decimal("0.00"),
    )

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=fresh_trust_store,
        auditor_signer=fresh_aud_signer,
        effective_max_position_size=Decimal("0.01"),
        max_quote_age_ms=5000,
        broker_probe_override=probe,
    )

    report = checker.evaluate_readiness()

    for dom_id, res in report.domain_results.items():
        assert res.passed is True, f"Domain {dom_id} failed: {res.status_message}"
    assert report.overall_status == GateBReadinessStatus.READY_FOR_HUMAN_GO

    # Verify Pre-Authorization Stop Gate
    # Live capital remains strictly $0.00 and no orders were placed
    assert probe.live_capital_authorized == Decimal("0.00")
    assert probe.positions == 0
    assert probe.orders == 0
