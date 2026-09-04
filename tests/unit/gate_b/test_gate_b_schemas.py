"""Phase 13 Slice 2: Unit Tests for Gate B Schemas & Cryptographic DTOs (Stage 1).

Verifies Pydantic schema validation, canonical JSON serialization, cryptographic
signatures, digest derivation, quote invariants, and state/mode distinctions per Rev 20.
"""

import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from uuid import uuid4

import pytest

from acash.execution.crypto import (
    Ed25519Signer,
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.gate_b.exceptions import (
    CryptographicVerificationError,
    DataContractError,
    PreLiveRiskAdmissionError,
)
from acash.gate_b.schema import (
    AuthoritativeAbortRecordBlock,
    AuthoritativeCommitRecordBlock,
    AuthoritativeLedgerProtocol,
    DurablePointerTransitionRecord,
    DurableTransactionState,
    HumanGORecord,
    JournalState,
    LiveAuthorization,
    LiveAuthorizationStatus,
    MT5QuoteSnapshot,
    SystemSafetyMode,
    assert_activation_preconditions,
    calculate_worst_case_notional,
    verify_human_go_record_integrity,
)


class MockLedger(AuthoritativeLedgerProtocol):
    def __init__(self, head_digest: str) -> None:
        self._head = head_digest

    @property
    def current_head_digest(self) -> str:
        return self._head


@pytest.fixture
def trust_store_and_key() -> tuple[Ed25519TrustStore, str, str]:
    priv_b64, pub_b64 = Ed25519Signer.generate_key_pair()
    key_id = "KEY_GO_001"
    now_utc = datetime.now(timezone.utc)
    entry = Ed25519TrustStoreEntry(
        key_id=key_id,
        issuer_id="ACASH_GOVERNANCE_ROOT",
        public_key_b64=pub_b64,
        valid_from=now_utc - timedelta(days=1),
        valid_until=now_utc + timedelta(days=365),
        status=TrustStoreEntryStatus.ACTIVE,
    )
    store = Ed25519TrustStore(entries=(entry,))
    return store, key_id, priv_b64


def test_live_authorization_schema_and_approved_canonical_bytes() -> None:
    now_utc = datetime.now(timezone.utc)
    exp_utc = now_utc + timedelta(hours=4)
    auth = LiveAuthorization(
        authorization_id="AUTH_GATE_B_001",
        status=LiveAuthorizationStatus.APPROVED_PENDING_GO,
        approved_authorization_digest="e" * 64,
        strategy_id="STRAT_EURUSD_MICRO",
        symbol="EURUSD",
        account_id="ACC_112040157",
        max_notional_usd=Decimal("500.00"),
        max_drawdown_pct=Decimal("5.00"),
        max_slippage_points=5,
        max_quote_age_ms=500,
        required_approvals=2,
        created_at=now_utc,
        expires_at=exp_utc,
    )
    assert auth.status == LiveAuthorizationStatus.APPROVED_PENDING_GO
    assert auth.authorization_digest == "e" * 64
    bytes_approved = auth.compute_approved_canonical_bytes()
    assert isinstance(bytes_approved, bytes)
    assert b"AUTH_GATE_B_001" in bytes_approved


def test_live_authorization_activated_canonical_bytes_includes_activated_at() -> None:
    """Test B97: activated_at must be canonically included in activated digest payload."""
    now_utc = datetime.now(timezone.utc)
    exp_utc = now_utc + timedelta(hours=4)
    act_utc = now_utc + timedelta(minutes=5)
    tx_id = uuid4()
    go_digest = "g" * 64

    auth = LiveAuthorization(
        authorization_id="AUTH_GATE_B_001",
        status=LiveAuthorizationStatus.ACTIVE,
        approved_authorization_digest="e" * 64,
        source_approved_digest="e" * 64,
        active_go_record_digest=go_digest,
        activation_transaction_id=tx_id,
        activated_at=act_utc,
        strategy_id="STRAT_EURUSD_MICRO",
        symbol="EURUSD",
        account_id="ACC_112040157",
        max_notional_usd=Decimal("500.00"),
        max_drawdown_pct=Decimal("5.00"),
        max_slippage_points=5,
        max_quote_age_ms=500,
        required_approvals=2,
        created_at=now_utc,
        expires_at=exp_utc,
    )
    activated_bytes = auth.compute_activated_canonical_bytes()
    assert act_utc.isoformat().encode("utf-8") in activated_bytes
    assert str(tx_id).encode("utf-8") in activated_bytes
    assert go_digest.encode("utf-8") in activated_bytes


def test_live_authorization_incomplete_activation_metadata_fails_closed() -> None:
    now_utc = datetime.now(timezone.utc)
    exp_utc = now_utc + timedelta(hours=4)
    auth = LiveAuthorization(
        authorization_id="AUTH_GATE_B_001",
        status=LiveAuthorizationStatus.APPROVED_PENDING_GO,
        approved_authorization_digest="e" * 64,
        strategy_id="STRAT_EURUSD_MICRO",
        symbol="EURUSD",
        account_id="ACC_112040157",
        max_notional_usd=Decimal("500.00"),
        max_drawdown_pct=Decimal("5.00"),
        max_slippage_points=5,
        max_quote_age_ms=500,
        required_approvals=2,
        created_at=now_utc,
        expires_at=exp_utc,
    )
    with pytest.raises(DataContractError, match="INCOMPLETE_ACTIVATION_METADATA_FOR_DIGEST"):
        auth.compute_activated_canonical_bytes()


def test_human_go_record_signing_and_verification(
    trust_store_and_key: tuple[Ed25519TrustStore, str, str],
) -> None:
    trust_store, key_id, priv_b64 = trust_store_and_key
    now_utc = datetime.now(timezone.utc)
    prev_head = "0" * 64
    app_digest = "a" * 64

    draft = HumanGORecord(
        go_record_id="GO_REC_001",
        authorization_id="AUTH_GATE_B_001",
        approved_authorization_digest=app_digest,
        previous_record_digest=prev_head,
        record_timestamp_utc=now_utc,
        approver_public_key_id=key_id,
        signature_ed25519="",
        record_digest="",
    )
    payload_to_sign = draft.compute_signed_payload_bytes()
    sig_b64 = Ed25519Signer.sign(priv_b64, payload_to_sign)

    with_sig = draft.model_copy(update={"signature_ed25519": sig_b64})
    rec_digest = with_sig.compute_canonical_digest()
    final_record = with_sig.model_copy(update={"record_digest": rec_digest})

    ledger = MockLedger(head_digest=prev_head)
    verify_human_go_record_integrity(final_record, trust_store, ledger)


def test_human_go_record_tamper_signature_fails(
    trust_store_and_key: tuple[Ed25519TrustStore, str, str],
) -> None:
    trust_store, key_id, priv_b64 = trust_store_and_key
    now_utc = datetime.now(timezone.utc)
    prev_head = "0" * 64
    app_digest = "a" * 64

    draft = HumanGORecord(
        go_record_id="GO_REC_001",
        authorization_id="AUTH_GATE_B_001",
        approved_authorization_digest=app_digest,
        previous_record_digest=prev_head,
        record_timestamp_utc=now_utc,
        approver_public_key_id=key_id,
        signature_ed25519="",
        record_digest="",
    )
    sig_b64 = Ed25519Signer.sign(priv_b64, draft.compute_signed_payload_bytes())
    # Guarantee corrupted signature differs from original
    corrupted_sig = ("A" if sig_b64[0] != "A" else "B") + sig_b64[1:]

    tampered = draft.model_copy(update={"signature_ed25519": corrupted_sig})
    tampered_digest = tampered.compute_canonical_digest()
    final_tampered = tampered.model_copy(update={"record_digest": tampered_digest})

    ledger = MockLedger(head_digest=prev_head)
    with pytest.raises(CryptographicVerificationError):
        verify_human_go_record_integrity(final_tampered, trust_store, ledger)


def test_human_go_record_head_continuity_broken_fails(
    trust_store_and_key: tuple[Ed25519TrustStore, str, str],
) -> None:
    trust_store, key_id, priv_b64 = trust_store_and_key
    now_utc = datetime.now(timezone.utc)
    prev_head = "0" * 64

    draft = HumanGORecord(
        go_record_id="GO_REC_001",
        authorization_id="AUTH_GATE_B_001",
        approved_authorization_digest="a" * 64,
        previous_record_digest=prev_head,
        record_timestamp_utc=now_utc,
        approver_public_key_id=key_id,
        signature_ed25519="",
        record_digest="",
    )
    sig_b64 = Ed25519Signer.sign(priv_b64, draft.compute_signed_payload_bytes())
    with_sig = draft.model_copy(update={"signature_ed25519": sig_b64})
    rec_digest = with_sig.compute_canonical_digest()
    final_record = with_sig.model_copy(update={"record_digest": rec_digest})

    # Ledger head does not match prev_head
    ledger = MockLedger(head_digest="different_head_digest_" + "0" * 42)
    with pytest.raises(CryptographicVerificationError, match="GO_LEDGER_CONTINUITY_BROKEN"):
        verify_human_go_record_integrity(final_record, trust_store, ledger)


def test_durable_pointer_transition_record_valid_transition(
    trust_store_and_key: tuple[Ed25519TrustStore, str, str],
) -> None:
    """Test B93: Transition record cryptographic signature and invariant VALID_TRANSITION."""
    trust_store, key_id, priv_b64 = trust_store_and_key
    now_utc = datetime.now(timezone.utc)
    prev_tx_id = uuid4()
    new_tx_id = uuid4()
    manifest_digest = "m" * 64
    prev_pointer_digest = "p" * 64

    draft = DurablePointerTransitionRecord(
        pointer_version=2,
        previous_tx_id=prev_tx_id,
        new_tx_id=new_tx_id,
        transition_timestamp_utc=now_utc,
        commit_intent_digest=manifest_digest,
        previous_pointer_digest=prev_pointer_digest,
        transition_record_digest="",
        engine_signature="",
        engine_key_id=key_id,
    )
    rec_digest = draft.compute_canonical_digest()
    sig_b64 = Ed25519Signer.sign(priv_b64, rec_digest.encode("utf-8"))

    record = draft.model_copy(update={
        "transition_record_digest": rec_digest,
        "engine_signature": sig_b64,
    })

    assert record.is_valid_transition(
        expected_tx_id=new_tx_id,
        expected_prev_tx_id=prev_tx_id,
        expected_manifest_digest=manifest_digest,
        trust_store=trust_store,
    )


def test_durable_pointer_transition_record_forged_signature_fails(
    trust_store_and_key: tuple[Ed25519TrustStore, str, str],
) -> None:
    """Test B93 / Crash-12: Injected transition record with forged signature fails validation."""
    trust_store, key_id, priv_b64 = trust_store_and_key
    now_utc = datetime.now(timezone.utc)
    prev_tx_id = uuid4()
    new_tx_id = uuid4()
    manifest_digest = "m" * 64
    prev_pointer_digest = "p" * 64

    # Generate a forged key pair
    forged_priv_b64, _ = Ed25519Signer.generate_key_pair()

    draft = DurablePointerTransitionRecord(
        pointer_version=2,
        previous_tx_id=prev_tx_id,
        new_tx_id=new_tx_id,
        transition_timestamp_utc=now_utc,
        commit_intent_digest=manifest_digest,
        previous_pointer_digest=prev_pointer_digest,
        transition_record_digest="",
        engine_signature="",
        engine_key_id=key_id,
    )
    rec_digest = draft.compute_canonical_digest()
    forged_sig = Ed25519Signer.sign(forged_priv_b64, rec_digest.encode("utf-8"))

    record = draft.model_copy(update={
        "transition_record_digest": rec_digest,
        "engine_signature": forged_sig,
    })

    # Must evaluate to False, rejecting unauthenticated rollback
    assert not record.is_valid_transition(
        expected_tx_id=new_tx_id,
        expected_prev_tx_id=prev_tx_id,
        expected_manifest_digest=manifest_digest,
        trust_store=trust_store,
    )


def test_authoritative_abort_record_block_integrity() -> None:
    now_utc = datetime.now(timezone.utc)
    tx_id = uuid4()
    block = AuthoritativeAbortRecordBlock(
        activation_transaction_id=tx_id,
        pre_transaction_head_digest="0" * 64,
        authorization_id="AUTH_GATE_B_001",
        approved_authorization_digest="a" * 64,
        expected_previous_state=DurableTransactionState.COMMITTING,
        terminal_state=DurableTransactionState.ABORTED,
        abort_reason_code="TIMEOUT",
        abort_timestamp_utc=now_utc,
        abort_record_digest="",
    )
    digest = block.compute_digest()
    final_block = block.model_copy(update={"abort_record_digest": digest})
    assert final_block.is_valid()

    corrupt_block = final_block.model_copy(update={"abort_reason_code": "TAMPERED"})
    assert not corrupt_block.is_valid()


def test_authoritative_commit_record_block_manifest_integrity() -> None:
    now_utc = datetime.now(timezone.utc)
    tx_id = uuid4()
    block = AuthoritativeCommitRecordBlock(
        activation_transaction_id=tx_id,
        commit_timestamp_utc=now_utc,
        ledger_record_digest="l" * 64,
        advanced_head_digest="h" * 64,
        approved_authorization_digest="a" * 64,
        activated_authorization_digest="act" + "0" * 61,
        mutation_manifest_digest="",
    )
    digest = block.compute_manifest_digest()
    final_block = block.model_copy(update={"mutation_manifest_digest": digest})
    assert final_block.verify_manifest_integrity()

    tampered_block = final_block.model_copy(update={"advanced_head_digest": "corrupted" + "0" * 55})
    assert not tampered_block.verify_manifest_integrity()


def test_mt5_quote_snapshot_valid_fresh() -> None:
    now_utc = datetime.now(timezone.utc)
    quote = MT5QuoteSnapshot(
        symbol="EURUSD",
        bid=Decimal("1.08500"),
        ask=Decimal("1.08510"),
        point_size=Decimal("0.00001"),
        contract_size=Decimal("100000"),
        timestamp_utc=now_utc - timedelta(milliseconds=100),
    )
    quote.assert_valid_and_fresh(max_quote_age_ms=500)
    assert calculate_worst_case_notional(Decimal("0.01"), quote, 5) > Decimal("1085.00")


def test_mt5_quote_snapshot_future_timestamp_rejected() -> None:
    now_utc = datetime.now(timezone.utc)
    quote = MT5QuoteSnapshot(
        symbol="EURUSD",
        bid=Decimal("1.08500"),
        ask=Decimal("1.08510"),
        point_size=Decimal("0.00001"),
        contract_size=Decimal("100000"),
        timestamp_utc=now_utc + timedelta(seconds=10),
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="FUTURE_TIMESTAMP_ANOMALY"):
        quote.assert_valid_and_fresh(max_quote_age_ms=500)


def test_mt5_quote_snapshot_stale_quote_rejected() -> None:
    now_utc = datetime.now(timezone.utc)
    quote = MT5QuoteSnapshot(
        symbol="EURUSD",
        bid=Decimal("1.08500"),
        ask=Decimal("1.08510"),
        point_size=Decimal("0.00001"),
        contract_size=Decimal("100000"),
        timestamp_utc=now_utc - timedelta(seconds=5),
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="STALE_QUOTE"):
        quote.assert_valid_and_fresh(max_quote_age_ms=500)


def test_mt5_quote_snapshot_inverted_spread_rejected() -> None:
    now_utc = datetime.now(timezone.utc)
    quote = MT5QuoteSnapshot(
        symbol="EURUSD",
        bid=Decimal("1.08520"),
        ask=Decimal("1.08510"),  # ask < bid
        point_size=Decimal("0.00001"),
        contract_size=Decimal("100000"),
        timestamp_utc=now_utc - timedelta(milliseconds=50),
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="INVALID_QUOTE: Inverted market spread"):
        quote.assert_valid_and_fresh(max_quote_age_ms=500)


def test_quarantine_transaction_state_vs_system_safety_mode_distinction() -> None:
    """Test B95: Verify distinct contracts between DurableTransactionState and SystemSafetyMode."""
    # Enums must be distinct types and distinct values
    q_state: object = DurableTransactionState.QUARANTINED
    q_mode: object = SystemSafetyMode.QUARANTINE_LOCKED
    assert DurableTransactionState.QUARANTINED.value == "QUARANTINED"
    assert SystemSafetyMode.QUARANTINE_LOCKED.value == "QUARANTINE_LOCKED"
    assert q_state != q_mode
    assert type(q_state) is not type(q_mode)
