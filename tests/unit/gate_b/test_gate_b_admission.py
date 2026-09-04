"""Phase 13 Slice 2: Unit Tests for Gate B Pre-Live Risk Admission Engine (Stage 3.3).

Verifies the complete 9-stage sequential pre-live risk admission decision pipeline:
1. Safety Mode Guard: Strict fail-closed rejection under QUARANTINE_LOCKED.
2. Snapshot Reader Boundary: Atomic read under single consistent lock boundary.
3. LiveAuthorization & Currency Basis Assertion: Status, symbol, strategy, account, expiry, and USD basis.
4. Deterministic Position Size Bounding: Strict min(auth, gov) precedence, non-positive rejection, fail-closed if undefined.
5. HumanGO Cryptographic Re-Verification: Self-digest, active key in trust store, Ed25519 signature, lineage digests.
6. Ledger-Head Continuity Assertion: Snapshot head and current ledger head match active record.
7. MT5 Quote Freshness & Spread Invariants: Symbol match, age >= 0, age <= max_quote_age_ms, ask >= bid.
8. max_slippage_points & Worst-Case Notional Bounding:
   - slippage_price_delta = points * point_size [quote price units]
   - monetary_slippage_allowance = quantity * contract_size * slippage_price_delta [USD]
   - worst_case_price = ask + delta (BUY) or bid - delta (SELL) > 0
   - bounded_executable_notional = quantity * contract_size * worst_case_price <= max_notional_usd
9. Pre-Live Risk Admission Decision: Emits frozen, immutable decision with canonical SHA-256 digest.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Generator, Optional
from unittest.mock import PropertyMock, patch
from uuid import UUID, uuid4

from pydantic import ValidationError
import pytest

from acash.core.domain.enums import OrderSide
from acash.execution.crypto import (
    Ed25519Signer,
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.gate_b.admission import (
    GateBOrderAdmissionRequest,
    PreLiveRiskAdmissionDecision,
    PreLiveRiskAdmissionService,
    verify_human_go_record_integrity,
)
from acash.gate_b.exceptions import (
    CryptographicVerificationError,
    DataContractError,
    PreLiveRiskAdmissionError,
)
from acash.gate_b.readers import SnapshotReaderService
from acash.gate_b.schema import (
    AuthoritativeCommitRecordBlock,
    DurableTransactionState,
    HumanGORecord,
    LiveAuthorization,
    LiveAuthorizationStatus,
    MT5QuoteSnapshot,
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

AdmissionEnvType = tuple[
    Path,
    Ed25519TrustStore,
    StorageEngineSigner,
    str,  # app_key_id
    str,  # app_priv
    AuthoritativeGOLedger,
]


@pytest.fixture
def admission_env(tmp_path: Path) -> Generator[AdmissionEnvType, None, None]:
    """Fixture providing isolated ledger storage, keys, and trust store for admission tests."""
    root = tmp_path / "gate_b_admission"
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


def _setup_active_ledger_environment(
    env: AdmissionEnvType,
    *,
    max_notional_usd: Decimal = Decimal("500.00"),
    max_slippage_points: int = 5,
    max_quote_age_ms: int = 500,
    expires_in_hours: int = 4,
    strategy_id: str = "STRAT_MOMENTUM_01",
    symbol: str = "EURUSD",
    account_id: str = "ACC_112040157",
) -> tuple[AuthoritativeGOLedger, Ed25519TrustStore, LiveAuthorization, LiveAuthorization, HumanGORecord, UUID]:
    """Helper to commit a fully valid active authorization and human GO record."""
    root, trust_store, signer, app_key_id, app_priv, ledger = env
    tx_id = uuid4()
    now_utc = datetime.now(timezone.utc)
    exp_utc = now_utc + timedelta(hours=expires_in_hours)

    draft = LiveAuthorization(
        authorization_id=f"AUTH_{tx_id.hex[:8].upper()}",
        status=LiveAuthorizationStatus.APPROVED_PENDING_GO,
        approved_authorization_digest="a" * 64,
        strategy_id=strategy_id,
        symbol=symbol,
        account_id=account_id,
        max_notional_usd=max_notional_usd,
        max_drawdown_pct=Decimal("5.00"),
        max_slippage_points=max_slippage_points,
        max_quote_age_ms=max_quote_age_ms,
        required_approvals=1,
        created_at=now_utc,
        expires_at=exp_utc,
    )

    go_draft = HumanGORecord(
        go_record_id=f"GO_REC_{tx_id}",
        authorization_id=draft.authorization_id,
        approved_authorization_digest=draft.approved_authorization_digest,
        previous_record_digest=GENESIS_HEAD_DIGEST,
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

    with ledger.exclusive_lock() as tx:
        tx.save_draft_authorization(draft)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)
        StorageCommitContract.execute_durable_commit(tx, tx_id, go_rec, draft, activated_auth, signer)

    return ledger, trust_store, draft, activated_auth, go_rec, tx_id


def _make_quote(
    *,
    symbol: str = "EURUSD",
    bid: Decimal = Decimal("1.08500"),
    ask: Decimal = Decimal("1.08520"),
    point_size: Decimal = Decimal("0.00010"),
    contract_size: Decimal = Decimal("100000"),
    age_ms: float = 50.0,
) -> MT5QuoteSnapshot:
    """Helper to create a valid, fresh MT5QuoteSnapshot."""
    ts = datetime.now(timezone.utc) - timedelta(milliseconds=age_ms)
    return MT5QuoteSnapshot(
        symbol=symbol,
        bid=bid,
        ask=ask,
        point_size=point_size,
        contract_size=contract_size,
        timestamp_utc=ts,
    )


# ==============================================================================
# 1 & 2. NOMINAL ADMISSION SUCCESS PATHS (BUY & SELL)
# ==============================================================================

def test_evaluate_admission_buy_success(admission_env: AdmissionEnvType) -> None:
    """Assert nominal BUY order within risk bounds is admitted with exact decision schema."""
    ledger, trust_store, _, activated_auth, go_rec, tx_id = _setup_active_ledger_environment(
        admission_env, max_notional_usd=Decimal("500.00"), max_slippage_points=5
    )

    quote = _make_quote(bid=Decimal("1.08500"), ask=Decimal("1.08520"), point_size=Decimal("0.00010"))
    request = GateBOrderAdmissionRequest(
        request_id="REQ_BUY_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),  # 100 units
        quote=quote,
        account_id="ACC_112040157",
        account_currency="USD",
    )

    decision = PreLiveRiskAdmissionService.evaluate_admission(
        ledger, request, trust_store, max_position_size=Decimal("0.5")
    )

    assert decision.is_admitted is True
    assert decision.strategy_id == "STRAT_MOMENTUM_01"
    assert decision.symbol == "EURUSD"
    assert decision.side == OrderSide.BUY
    assert decision.quantity == Decimal("0.001")
    assert decision.effective_max_position_size == Decimal("0.5")
    assert decision.currency_basis == "USD"
    assert decision.reference_price == Decimal("1.08520")
    # 5 points * 0.00010 = 0.00050 quote price units
    assert decision.slippage_price_delta == Decimal("0.00050")
    # 0.001 * 100,000 * 0.00050 = 0.05 USD
    assert decision.monetary_slippage_allowance == Decimal("0.0500000")
    # worst_case_price = 1.08520 + 0.00050 = 1.08570
    assert decision.worst_case_price == Decimal("1.08570")
    # bounded_executable_notional = 100 * 1.08570 = 108.5700000 <= 500.00
    assert decision.bounded_executable_notional == Decimal("108.5700000")
    assert decision.max_notional_usd == Decimal("500.00")
    assert decision.activation_transaction_id == tx_id
    assert decision.head_digest == go_rec.record_digest
    assert len(decision.decision_digest) == 64
    assert decision.decision_id.startswith("ADM_")


def test_evaluate_admission_sell_success(admission_env: AdmissionEnvType) -> None:
    """Assert nominal SELL order within risk bounds is admitted with exact decision schema."""
    ledger, trust_store, _, _, go_rec, tx_id = _setup_active_ledger_environment(
        admission_env, max_notional_usd=Decimal("500.00"), max_slippage_points=5
    )

    quote = _make_quote(bid=Decimal("1.08500"), ask=Decimal("1.08520"), point_size=Decimal("0.00010"))
    request = GateBOrderAdmissionRequest(
        request_id="REQ_SELL_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.SELL,
        quantity=Decimal("0.001"),  # 100 units
        quote=quote,
        account_id="ACC_112040157",
        account_currency="USD",
    )

    decision = PreLiveRiskAdmissionService.evaluate_admission(
        ledger, request, trust_store, max_position_size=Decimal("0.5")
    )

    assert decision.is_admitted is True
    assert decision.side == OrderSide.SELL
    assert decision.reference_price == Decimal("1.08500")
    # worst_case_price for SELL = bid - slippage_price_delta = 1.08500 - 0.00050 = 1.08450
    assert decision.worst_case_price == Decimal("1.08450")
    # bounded_executable_notional = 100 * 1.08450 = 108.4500000 <= 500.00
    assert decision.bounded_executable_notional == Decimal("108.4500000")


# ==============================================================================
# 3, 4, 5, 6. DETERMINISTIC POSITION SIZE BOUNDING & PRECEDENCE TESTS
# ==============================================================================

def test_admission_uses_strictest_position_size_limit(admission_env: AdmissionEnvType) -> None:
    """Assert strict min(auth_limit, gov_limit) precedence when both limits are defined."""
    ledger, trust_store, _, activated_auth, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()

    # Case A: auth_limit (1.0) > gov_limit (0.5) -> effective_limit must be 0.5
    real_view = SnapshotReaderService.read_active_committed_snapshot(ledger)
    object.__setattr__(real_view.authorization, "max_position_size", Decimal("1.0"))
    with patch.object(SnapshotReaderService, "read_active_committed_snapshot", return_value=real_view):
        # Order quantity 0.004 exceeds gov_limit (0.003) -> must reject
        req_reject = GateBOrderAdmissionRequest(
            request_id="REQ_POS_REJ",
            strategy_id="STRAT_MOMENTUM_01",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=Decimal("0.004"),
            quote=quote,
        )
        # Test with gov_limit = 0.003
        with pytest.raises(PreLiveRiskAdmissionError, match="MAX_POSITION_SIZE_BREACH"):
            PreLiveRiskAdmissionService.evaluate_admission(
                ledger, req_reject, trust_store, max_position_size=Decimal("0.003")
            )

        # Order quantity 0.003 within gov_limit = 0.003 -> admits
        req_admit = req_reject.model_copy(update={"quantity": Decimal("0.003")})
        decision = PreLiveRiskAdmissionService.evaluate_admission(
            ledger, req_admit, trust_store, max_position_size=Decimal("0.003")
        )
        assert decision.effective_max_position_size == Decimal("0.003")

    # Case B: auth_limit (0.002) < gov_limit (0.005) -> effective_limit must be 0.002
    real_view2 = SnapshotReaderService.read_active_committed_snapshot(ledger)
    object.__setattr__(real_view2.authorization, "max_position_size", Decimal("0.002"))
    with patch.object(SnapshotReaderService, "read_active_committed_snapshot", return_value=real_view2):
        req_reject2 = req_reject.model_copy(update={"quantity": Decimal("0.003")})
        with pytest.raises(PreLiveRiskAdmissionError, match="MAX_POSITION_SIZE_BREACH"):
            PreLiveRiskAdmissionService.evaluate_admission(
                ledger, req_reject2, trust_store, max_position_size=Decimal("0.005")
            )

        req_admit2 = req_reject.model_copy(update={"quantity": Decimal("0.002")})
        decision2 = PreLiveRiskAdmissionService.evaluate_admission(
            ledger, req_admit2, trust_store, max_position_size=Decimal("0.005")
        )
        assert decision2.effective_max_position_size == Decimal("0.002")


def test_admission_rejects_undefined_position_size_limit(admission_env: AdmissionEnvType) -> None:
    """Assert fail-closed rejection when neither authorization nor governance defines max_position_size."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_UNDEF_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    with pytest.raises(PreLiveRiskAdmissionError, match="MAX_POSITION_SIZE_UNDEFINED"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=None
        )


def test_admission_rejects_non_positive_position_size_limit(admission_env: AdmissionEnvType) -> None:
    """Assert strict fail-closed rejection when position size limit is zero or negative (no silent normalization)."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_NONPOS_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    # 1. Zero governance limit
    with pytest.raises(PreLiveRiskAdmissionError, match="INVALID_GOVERNANCE_POSITION_LIMIT.*must be positive"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0")
        )

    # 2. Negative governance limit
    with pytest.raises(PreLiveRiskAdmissionError, match="INVALID_GOVERNANCE_POSITION_LIMIT.*must be positive"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("-0.5")
        )

    # 3. Zero authorization limit
    real_view3 = SnapshotReaderService.read_active_committed_snapshot(ledger)
    object.__setattr__(real_view3.authorization, "max_position_size", Decimal("0"))
    with patch.object(SnapshotReaderService, "read_active_committed_snapshot", return_value=real_view3):
        with pytest.raises(PreLiveRiskAdmissionError, match="INVALID_AUTHORIZATION_POSITION_LIMIT.*must be positive"):
            PreLiveRiskAdmissionService.evaluate_admission(
                ledger, request, trust_store, max_position_size=Decimal("1.0")
            )

    # 4. Negative authorization limit
    real_view4 = SnapshotReaderService.read_active_committed_snapshot(ledger)
    object.__setattr__(real_view4.authorization, "max_position_size", Decimal("-1.0"))
    with patch.object(SnapshotReaderService, "read_active_committed_snapshot", return_value=real_view4):
        with pytest.raises(PreLiveRiskAdmissionError, match="INVALID_AUTHORIZATION_POSITION_LIMIT.*must be positive"):
            PreLiveRiskAdmissionService.evaluate_admission(
                ledger, request, trust_store, max_position_size=Decimal("1.0")
            )


def test_evaluate_admission_rejects_max_position_size_breach(admission_env: AdmissionEnvType) -> None:
    """Assert single order exceeding effective max_position_size ceiling is rejected."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_BREACH_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.5001"),
        quote=quote,
    )

    with pytest.raises(PreLiveRiskAdmissionError, match="MAX_POSITION_SIZE_BREACH"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0.5000")
        )


# ==============================================================================
# 7 & 8. CURRENCY BASIS & MONETARY UNIT SEMANTICS CONTRACTS
# ==============================================================================

def test_evaluate_admission_rejects_notional_currency_basis_mismatch(admission_env: AdmissionEnvType) -> None:
    """Assert non-USD account currency or non-USD quote currency is strictly rejected."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()

    # 1. Non-USD account currency
    req_eur_account = GateBOrderAdmissionRequest(
        request_id="REQ_CURR_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
        account_currency="EUR",
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="CURRENCY_BASIS_MISMATCH.*Account currency 'EUR'"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, req_eur_account, trust_store, max_position_size=Decimal("0.5")
        )

    # 2. Non-USD quote currency (e.g. EURGBP)
    ledger_cross, trust_store_cross, _, _, _, _ = _setup_active_ledger_environment(
        admission_env, symbol="EURGBP"
    )
    quote_cross = _make_quote(symbol="EURGBP")
    req_cross = GateBOrderAdmissionRequest(
        request_id="REQ_CURR_002",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURGBP",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote_cross,
    )
    with pytest.raises(PreLiveRiskAdmissionError, match="CURRENCY_BASIS_MISMATCH.*quote currency is not 'USD'"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger_cross, req_cross, trust_store_cross, max_position_size=Decimal("0.5")
        )


def test_admission_decision_slippage_buffer_unit_contract(admission_env: AdmissionEnvType) -> None:
    """Assert slippage_price_delta is in quote price units and monetary_slippage_allowance is in USD."""
    ledger, trust_store, _, auth, _, _ = _setup_active_ledger_environment(
        admission_env, max_slippage_points=10
    )
    quote = _make_quote(point_size=Decimal("0.00010"), contract_size=Decimal("100000"))
    request = GateBOrderAdmissionRequest(
        request_id="REQ_UNIT_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.002"),  # 200 units
        quote=quote,
    )

    decision = PreLiveRiskAdmissionService.evaluate_admission(
        ledger, request, trust_store, max_position_size=Decimal("0.5")
    )

    # Unit checks
    expected_price_delta = Decimal("10") * Decimal("0.00010")  # 0.00100 quote units
    assert decision.slippage_price_delta == expected_price_delta

    expected_monetary_slippage = Decimal("0.002") * Decimal("100000") * expected_price_delta  # 0.20 USD
    assert decision.monetary_slippage_allowance == expected_monetary_slippage
    assert decision.monetary_slippage_allowance == Decimal("0.2000000")
    assert decision.currency_basis == "USD"


# ==============================================================================
# 9. CONSISTENT LOCK BOUNDARY (INVARIANT 1)
# ==============================================================================

def test_admission_enforces_single_consistent_lock_boundary(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission works under both AuthoritativeGOLedger and LedgerStorageTransaction."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_LOCK_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    # 1. Pass AuthoritativeGOLedger directly
    decision_ledger = PreLiveRiskAdmissionService.evaluate_admission(
        ledger, request, trust_store, max_position_size=Decimal("0.5")
    )
    assert decision_ledger.is_admitted is True

    # 2. Pass existing LedgerStorageTransaction without re-acquiring lock
    with ledger.exclusive_lock() as tx:
        decision_tx = PreLiveRiskAdmissionService.evaluate_admission(
            tx, request, trust_store, max_position_size=Decimal("0.5")
        )
        assert decision_tx.is_admitted is True
        assert decision_tx.activation_transaction_id == decision_ledger.activation_transaction_id


# ==============================================================================
# 10. SYSTEM SAFETY MODE GUARD (STAGE 1)
# ==============================================================================

def test_evaluate_admission_rejects_system_quarantine(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed immediately when system is in QUARANTINE_LOCKED."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    with ledger.exclusive_lock() as tx:
        tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)

    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_QUAR_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    with pytest.raises(PreLiveRiskAdmissionError, match="SYSTEM_QUARANTINED_PENDING_FORENSIC_AUDIT"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0.5")
        )


# ==============================================================================
# 11, 12, 13, 14, 15, 16. SNAPSHOT & AUTHORIZATION INTEGRITY (STAGES 2 & 3)
# ==============================================================================

def test_evaluate_admission_rejects_no_active_snapshot(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when no active committed snapshot exists."""
    _, trust_store, _, _, _, ledger = admission_env
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_NOSNAP_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    with pytest.raises(PreLiveRiskAdmissionError, match="ACTIVE_COMMITTED_SNAPSHOT_UNAVAILABLE"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0.5")
        )


def test_evaluate_admission_rejects_inactive_authorization(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when authorization status is not ACTIVE."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_INACT_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    real_view = SnapshotReaderService.read_active_committed_snapshot(ledger)
    object.__setattr__(real_view.authorization, "status", LiveAuthorizationStatus.APPROVED_PENDING_GO)
    with patch.object(SnapshotReaderService, "read_active_committed_snapshot", return_value=real_view):
        with pytest.raises(PreLiveRiskAdmissionError, match="AUTHORIZATION_INACTIVE"):
            PreLiveRiskAdmissionService.evaluate_admission(
                ledger, request, trust_store, max_position_size=Decimal("0.5")
            )


def test_evaluate_admission_rejects_strategy_mismatch(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when request strategy does not match authorization."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_MISMATCH_001",
        strategy_id="STRAT_DIFFERENT",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    with pytest.raises(PreLiveRiskAdmissionError, match="STRATEGY_MISMATCH"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0.5")
        )


def test_evaluate_admission_rejects_symbol_mismatch(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when request symbol does not match authorization."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote(symbol="GBPUSD")
    request = GateBOrderAdmissionRequest(
        request_id="REQ_SYM_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="GBPUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    with pytest.raises(PreLiveRiskAdmissionError, match="SYMBOL_MISMATCH"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0.5")
        )


def test_evaluate_admission_rejects_account_mismatch(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when request account ID does not match authorization."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_ACC_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
        account_id="ACC_WRONG_999",
    )

    with pytest.raises(PreLiveRiskAdmissionError, match="ACCOUNT_MISMATCH"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0.5")
        )


def test_evaluate_admission_rejects_expired_authorization(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when authorization has expired."""
    ledger, trust_store, _, auth, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_EXP_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    past_time = auth.expires_at + timedelta(seconds=1)
    with pytest.raises(PreLiveRiskAdmissionError, match="AUTHORIZATION_EXPIRED"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0.5"), now_utc=past_time
        )


# ==============================================================================
# 17, 18, 19, 20. CRYPTOGRAPHIC INTEGRITY & LINEAGE (STAGE 5)
# ==============================================================================

def test_evaluate_admission_rejects_corrupted_go_record_digest(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when HumanGORecord self-digest is corrupted."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_CORRUPT_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    real_view = SnapshotReaderService.read_active_committed_snapshot(ledger)
    assert real_view.record is not None
    corrupted_record = real_view.record.model_copy(update={"record_digest": "f" * 64})
    object.__setattr__(real_view, "record", corrupted_record)
    with patch.object(SnapshotReaderService, "read_active_committed_snapshot", return_value=real_view):
        with pytest.raises(CryptographicVerificationError, match="GO_RECORD_DIGEST_CORRUPTED"):
            PreLiveRiskAdmissionService.evaluate_admission(
                ledger, request, trust_store, max_position_size=Decimal("0.5")
            )


def test_evaluate_admission_rejects_revoked_approver_key(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when approver key in trust store is REVOKED."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_REVOKED_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    # Revoke approver key in trust store
    entry = trust_store.resolve("KEY_HUMAN_APPROVER_001")
    assert entry is not None
    revoked_entry = entry.model_copy(update={"status": TrustStoreEntryStatus.REVOKED})
    other_entries = tuple(e for e in trust_store.entries if e.key_id != "KEY_HUMAN_APPROVER_001")
    revoked_trust_store = Ed25519TrustStore(entries=other_entries + (revoked_entry,))

    with pytest.raises(CryptographicVerificationError, match="APPROVER_KEY_REVOKED_OR_UNRESOLVED"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, revoked_trust_store, max_position_size=Decimal("0.5")
        )


def test_evaluate_admission_rejects_invalid_go_signature(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when HumanGORecord signature is invalid."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_SIG_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    real_view = SnapshotReaderService.read_active_committed_snapshot(ledger)
    assert real_view.record is not None
    # Compute valid self-digest for mutated signature to bypass 5.1 and reach 5.3
    bad_sig = "a" * 88
    tampered_rec = real_view.record.model_copy(update={"signature_ed25519": bad_sig})
    tampered_rec = tampered_rec.model_copy(update={"record_digest": tampered_rec.compute_canonical_digest()})
    object.__setattr__(real_view, "record", tampered_rec)
    with patch.object(SnapshotReaderService, "read_active_committed_snapshot", return_value=real_view):
        with pytest.raises(CryptographicVerificationError, match="HUMAN_GO_SIGNATURE_INVALID"):
            PreLiveRiskAdmissionService.evaluate_admission(
                ledger, request, trust_store, max_position_size=Decimal("0.5")
            )


def test_evaluate_admission_rejects_active_go_record_digest_desync(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when auth.active_go_record_digest mismatches bound record."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_DESYNC_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    real_view = SnapshotReaderService.read_active_committed_snapshot(ledger)
    object.__setattr__(real_view.authorization, "active_go_record_digest", "0" * 64)
    with patch.object(SnapshotReaderService, "read_active_committed_snapshot", return_value=real_view):
        with pytest.raises(PreLiveRiskAdmissionError, match="AUTHORIZATION_DESYNC.*active_go_record_digest"):
            PreLiveRiskAdmissionService.evaluate_admission(
                ledger, request, trust_store, max_position_size=Decimal("0.5")
            )


# ==============================================================================
# 21. LEDGER HEAD CONTINUITY (STAGE 6)
# ==============================================================================

def test_evaluate_admission_rejects_ledger_head_divergence(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when authoritative ledger head diverges from active record."""
    ledger, trust_store, _, _, go_rec, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_HEAD_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    # Advance authoritative ledger head beyond active snapshot record
    with ledger.exclusive_lock() as tx:
        tx.set_head_digest_durable("f" * 64)

    with pytest.raises(PreLiveRiskAdmissionError, match="AUTHORIZATION_DESYNC.*has advanced beyond active record"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0.5")
        )


# ==============================================================================
# 22, 23, 24. MT5 QUOTE FRESHNESS & SPREAD INVARIANTS (STAGE 7)
# ==============================================================================

def test_evaluate_admission_rejects_quote_symbol_mismatch(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when quote symbol mismatches authorized symbol."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote(symbol="USDJPY")
    request = GateBOrderAdmissionRequest(
        request_id="REQ_QS_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    with pytest.raises(PreLiveRiskAdmissionError, match="QUOTE_SYMBOL_MISMATCH"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0.5")
        )


def test_evaluate_admission_rejects_stale_quote(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when MT5 quote exceeds max_quote_age_ms."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(
        admission_env, max_quote_age_ms=100
    )
    # Quote age 200ms > SLA 100ms
    stale_quote = _make_quote(age_ms=250.0)
    request = GateBOrderAdmissionRequest(
        request_id="REQ_STALE_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=stale_quote,
    )

    with pytest.raises(PreLiveRiskAdmissionError, match="STALE_QUOTE"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0.5")
        )


def test_evaluate_admission_rejects_inverted_spread(admission_env: AdmissionEnvType) -> None:
    """Assert evaluate_admission fails closed when market quote has bid > ask."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    # Inverted spread: bid 1.08600 > ask 1.08500
    inverted_quote = _make_quote(bid=Decimal("1.08600"), ask=Decimal("1.08500"))
    request = GateBOrderAdmissionRequest(
        request_id="REQ_INV_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=inverted_quote,
    )

    with pytest.raises(PreLiveRiskAdmissionError, match="INVALID_QUOTE.*Inverted market spread"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0.5")
        )


# ==============================================================================
# 25. WORST-CASE NOTIONAL BOUNDING (STAGE 8)
# ==============================================================================

def test_evaluate_admission_rejects_worst_case_notional_breach(admission_env: AdmissionEnvType) -> None:
    """Assert order where nominal notional passes but worst-case notional breaches max_notional_usd is rejected.

    Math:
    - quantity = 0.0046 lots (460 units)
    - ask = 1.08520
    - slippage_points = 50 points = 50 * 0.00010 = 0.00500
    - worst_case_price = 1.08520 + 0.00500 = 1.09020
    - Nominal notional = 460 * 1.08520 = 499.192 USD (<= 500.00 USD authorized)
    - Bounded worst-case notional = 460 * 1.09020 = 501.492 USD (> 500.00 USD authorized)
    """
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(
        admission_env, max_notional_usd=Decimal("500.00"), max_slippage_points=50
    )
    quote = _make_quote(ask=Decimal("1.08520"), point_size=Decimal("0.00010"))
    request = GateBOrderAdmissionRequest(
        request_id="REQ_NOTIONAL_BREACH",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.0046"),  # 460 units
        quote=quote,
    )

    with pytest.raises(PreLiveRiskAdmissionError, match="WORST_CASE_NOTIONAL_BREACH"):
        PreLiveRiskAdmissionService.evaluate_admission(
            ledger, request, trust_store, max_position_size=Decimal("0.5")
        )


# ==============================================================================
# 26. DECISION IMMUTABILITY & EXTRA FORBID
# ==============================================================================

def test_admission_decision_immutability_and_extra_forbid(admission_env: AdmissionEnvType) -> None:
    """Assert GateBOrderAdmissionRequest and PreLiveRiskAdmissionDecision enforce frozen=True and extra='forbid'."""
    ledger, trust_store, _, _, _, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_IMMUT_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    # 1. GateBOrderAdmissionRequest is frozen
    with pytest.raises(ValidationError):
        setattr(request, "quantity", Decimal("0.002"))

    # 2. GateBOrderAdmissionRequest forbids extra fields
    with pytest.raises(ValidationError):
        GateBOrderAdmissionRequest(
            request_id="REQ_EXTRA",
            strategy_id="STRAT_MOMENTUM_01",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=Decimal("0.001"),
            quote=quote,
            unauthorized_field="malicious",  # type: ignore[call-arg]
        )

    # 3. PreLiveRiskAdmissionDecision is frozen
    decision = PreLiveRiskAdmissionService.evaluate_admission(
        ledger, request, trust_store, max_position_size=Decimal("0.5")
    )
    with pytest.raises(ValidationError):
        setattr(decision, "is_admitted", False)

    # 4. PreLiveRiskAdmissionDecision forbids extra fields
    decision_dict = decision.model_dump()
    decision_dict["extra_injected"] = "tamper"
    with pytest.raises(ValidationError):
        PreLiveRiskAdmissionDecision(**decision_dict)


# ==============================================================================
# 27. SAME TRANSACTION OBSERVATION BOUNDARY (INVARIANT 1 & AUDIT REVISION)
# ==============================================================================

def test_admission_humango_verification_uses_same_transaction_observation(
    admission_env: AdmissionEnvType,
) -> None:
    """Assert HumanGO verification and admission pipeline enforce identical transaction observation.

    If storage transaction context (tx) and ledger object belong to different generations
    or different roots, evaluation strictly fails closed with TRANSACTION_OBSERVATION_DESYNC
    and cannot produce an admitted decision.
    """
    root, trust_store, signer, app_key_id, app_priv, ledger = admission_env
    # Setup initial valid active state (Generation A)
    _, _, draft, activated_auth, go_rec, _ = _setup_active_ledger_environment(admission_env)
    quote = _make_quote()
    request = GateBOrderAdmissionRequest(
        request_id="REQ_SAME_OBS_001",
        strategy_id="STRAT_MOMENTUM_01",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        quote=quote,
    )

    # 1. Within an open transaction context on Generation A, force ledger to Generation B
    with ledger.exclusive_lock() as tx_gen_a:
        assert tx_gen_a.current_head_digest == go_rec.record_digest

        with patch.object(
            AuthoritativeGOLedger,
            "current_head_digest",
            new_callable=PropertyMock,
            return_value="b" * 64,
        ):
            with pytest.raises(
                PreLiveRiskAdmissionError,
                match="TRANSACTION_OBSERVATION_DESYNC.*diverges from transaction context head",
            ):
                PreLiveRiskAdmissionService.evaluate_admission(
                    tx_gen_a,
                    request,
                    trust_store,
                    ledger=ledger,
                    max_position_size=Decimal("0.5"),
                )

    # 2. Test foreign ledger with different root
    foreign_root = root.parent / "foreign_ledger_root"
    foreign_ledger = AuthoritativeGOLedger(foreign_root, trust_store)
    with ledger.exclusive_lock() as tx:
        with pytest.raises(
            PreLiveRiskAdmissionError,
            match="TRANSACTION_OBSERVATION_DESYNC.*does not match ledger root",
        ):
            PreLiveRiskAdmissionService.evaluate_admission(
                tx,
                request,
                trust_store,
                ledger=foreign_ledger,
                max_position_size=Decimal("0.5"),
            )

    # 3. Direct verification of verify_human_go_record_integrity using tx
    with ledger.exclusive_lock() as tx:
        # Calling with matching tx succeeds
        verify_human_go_record_integrity(
            bound_record=go_rec,
            trust_store=trust_store,
            tx=tx,
            auth=activated_auth,
        )

        # Mutating active_go_record_digest causes failure
        desync_auth = activated_auth.model_copy(update={"active_go_record_digest": "0" * 64})
        with pytest.raises(PreLiveRiskAdmissionError, match="AUTHORIZATION_DESYNC"):
            verify_human_go_record_integrity(
                bound_record=go_rec,
                trust_store=trust_store,
                tx=tx,
                auth=desync_auth,
            )

