"""Phase 13 Slice 2: Gate B Activation Transaction Manager & Recovery Coordinator (Stage 3.1).

Implements:
- AtomicActivationTransactionManager (§3.8, B38, B54, B56, B61, B64, B65, B67, B69, B70, B73, B75, B76, B77, B79, B82, B88, B93, B95, B97)
- Blocker 2 Resolution: Authoritative Decision Gate on exception BEFORE writing terminal state
- Pre-commit failures cleanly abort and discard staging (Tier 1)
- Post-boundary failures strictly enter QUARANTINE_LOCKED without writing ABORTED (Tier 3)
- GateBRecoveryCoordinator: Storage substrate recovery orchestration and startup consistency scan
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from acash.execution.crypto import Ed25519TrustStore
from acash.gate_b.exceptions import (
    CryptographicVerificationError,
    DataContractError,
    PreLiveRiskAdmissionError,
    QuarantineError,
    StorageDurabilityError,
)
from acash.gate_b.recovery import (
    RecoveryDecisionTreeEngine,
    RecoveryInspectionResult,
    RecoveryResult,
    has_any_durable_commit_evidence,
    is_provably_uncommitted,
)
from acash.gate_b.schema import (
    AuthoritativeAbortRecordBlock,
    AuthoritativeCommitRecordBlock,
    AuthoritativeLedgerProtocol,
    DurableTransactionState,
    HumanGORecord,
    JournalState,
    LiveAuthorization,
    LiveAuthorizationStatus,
    SystemSafetyMode,
    assert_activation_preconditions,
    verify_human_go_record_integrity,
)
from acash.gate_b.storage import (
    AuthoritativeGOLedger,
    LedgerStorageTransaction,
    StorageCommitContract,
    StorageEngineSigner,
)

logger = logging.getLogger(__name__)


class AtomicActivationTransactionManager:
    """Coordinates atomic live strategy activation transactions under exclusive ledger lock.

    Guarantees:
    - Preflight verification of SystemSafetyMode == NORMAL (B95)
    - Cryptographic verification of human GO record and trust store key validity
    - Derivation lineage invariant: auth.approved_authorization_digest == go_record.approved_authorization_digest (B79)
    - Ledger head continuity CAS: go_record.previous_record_digest == tx.current_head_digest
    - WAL journal progression: PREPARED -> COMMITTING -> COMMITTED / ABORTED / QUARANTINED
    - Two-phase recoverable commit via StorageCommitContract
    - Blocker 2 Fail-Closed Boundary: Checks durable commit evidence before any terminal state write
    """

    def __init__(
        self,
        ledger: AuthoritativeGOLedger,
        trust_store: Ed25519TrustStore,
        engine_signer: StorageEngineSigner,
    ) -> None:
        self._ledger = ledger
        self._trust_store = trust_store
        self._engine_signer = engine_signer

    def execute_activation(
        self,
        auth: LiveAuthorization,
        go_record: HumanGORecord,
    ) -> LiveAuthorization:
        """Execute atomic strategy activation lifecycle under exclusive ledger lock."""
        return self.execute_atomic_activation(
            auth=auth,
            go_record=go_record,
            trust_store=self._trust_store,
            ledger=self._ledger,
            engine_signer=self._engine_signer,
        )

    @classmethod
    def execute_atomic_activation(
        cls,
        auth: LiveAuthorization,
        go_record: HumanGORecord,
        trust_store: Ed25519TrustStore,
        ledger: AuthoritativeGOLedger,
        engine_signer: StorageEngineSigner,
    ) -> LiveAuthorization:
        """Execute atomic strategy activation lifecycle."""
        with ledger.exclusive_lock() as tx:
            # 1. Preflight: Assert system safety mode is NORMAL (B95)
            safety_mode = tx.get_system_safety_mode()
            if safety_mode == SystemSafetyMode.QUARANTINE_LOCKED:
                raise QuarantineError(
                    f"SYSTEM_SAFETY_MODE_QUARANTINE_LOCKED: Cannot activate strategy while system is in {safety_mode}"
                )
            if safety_mode != SystemSafetyMode.NORMAL:
                raise PreLiveRiskAdmissionError(
                    f"SYSTEM_SAFETY_MODE_NOT_NORMAL: Expected NORMAL, got {safety_mode}"
                )

            # 2. Cryptographic Preconditions & Signature Verification
            assert_activation_preconditions(auth, go_record, trust_store)
            verify_human_go_record_integrity(go_record, trust_store, ledger)

            # 3. Derivation Lineage Invariant: AUTH_CHAIN_VALID(tx) (B79, B97)
            if auth.approved_authorization_digest != go_record.approved_authorization_digest:
                raise PreLiveRiskAdmissionError(
                    f"DERIVATION_LINEAGE_MISMATCH: auth.approved_authorization_digest "
                    f"({auth.approved_authorization_digest}) != go_record.approved_authorization_digest "
                    f"({go_record.approved_authorization_digest})"
                )
            if auth.authorization_id != go_record.authorization_id:
                raise PreLiveRiskAdmissionError(
                    f"AUTHORIZATION_ID_MISMATCH: auth.authorization_id ({auth.authorization_id}) "
                    f"!= go_record.authorization_id ({go_record.authorization_id})"
                )

            # 4. CAS check on ledger head continuity
            if go_record.previous_record_digest != tx.current_head_digest:
                raise PreLiveRiskAdmissionError(
                    f"HEAD_CONTINUITY_CAS_FAILED: go_record references head {go_record.previous_record_digest}, "
                    f"but current durable head is {tx.current_head_digest}"
                )

            # 5. Reserve unique activation_transaction_id
            tx_id = uuid4()
            if tx.has_transaction_id(tx_id):
                raise DataContractError(f"DUPLICATE_TRANSACTION_ID_REJECTED: {tx_id}")
            tx.reserve_transaction_id(tx_id)  # Persists tx_state = PREPARED

            # 6. Stage WAL journal: PREPARED -> COMMITTING
            journal = tx.create_wal_journal(tx_id, auth.authorization_id, go_record)
            journal.write_state_durable(JournalState.PREPARED)
            tx.set_tx_state_durable(tx_id, DurableTransactionState.COMMITTING)
            journal.write_state_durable(JournalState.COMMITTING)

            # 7. Construct activated LiveAuthorization artifact (B73, B77, B97)
            now_utc = datetime.now(timezone.utc)
            activated_draft = auth.model_copy(
                update={
                    "status": LiveAuthorizationStatus.ACTIVE,
                    "source_approved_digest": auth.approved_authorization_digest,
                    "active_go_record_digest": go_record.record_digest,
                    "activation_transaction_id": tx_id,
                    "activated_at": now_utc,
                }
            )
            act_digest = hashlib.sha256(activated_draft.compute_activated_canonical_bytes()).hexdigest()
            activated_auth = activated_draft.model_copy(update={"activated_authorization_digest": act_digest})

            # 8. Execute Two-Phase Commit with Fail-Closed Exception Boundary (Blocker 2 Resolution)
            try:
                StorageCommitContract.execute_durable_commit(
                    tx=tx,
                    tx_id=tx_id,
                    go_record=go_record,
                    approved_auth=auth,
                    activated_auth=activated_auth,
                    engine_signer=engine_signer,
                )
                try:
                    journal.write_state_durable(JournalState.COMMITTED)
                except Exception:
                    pass
                return activated_auth

            except Exception as exc:
                logger.error("Exception during durable commit for tx %s: %s", tx_id, exc)

                # Anomaly check: Did transaction reach COMMITTED before error was raised?
                if tx.get_durable_tx_state(tx_id) == DurableTransactionState.COMMITTED:
                    logger.warning("Transaction %s reached COMMITTED despite commit phase exception: %s", tx_id, exc)
                    return activated_auth

                # Authoritative Decision Gate (Blocker 2):
                # Inspect durable filesystem evidence before modifying state
                if has_any_durable_commit_evidence(tx, tx_id):
                    # POST-BOUNDARY / AMBIGUOUS FAILURE:
                    # Strictly forbidden to write ABORTED! Must quarantine (Blocker 2).
                    tx.log_consistency_violation(
                        f"ACTIVATION_COMMIT_UNCERTAIN: tx {tx_id} failed with post-boundary evidence: {exc}"
                    )
                    tx.set_tx_state_durable(tx_id, DurableTransactionState.QUARANTINED)
                    tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)
                    try:
                        journal.write_state_durable(JournalState.QUARANTINED)
                    except Exception:
                        pass
                    raise QuarantineError(
                        f"ACTIVATION_COMMIT_UNCERTAIN: System entered QUARANTINE_LOCKED for tx {tx_id}: {exc}"
                    ) from exc
                else:
                    # PROVABLY PRE-COMMIT FAILURE:
                    # Safe to cleanly abort (Blocker 2).
                    tx.compare_and_set_tx_state(
                        tx_id,
                        expected=DurableTransactionState.COMMITTING,
                        new=DurableTransactionState.ABORTED,
                    )
                    # Write authoritative abort record block
                    abort_record = AuthoritativeAbortRecordBlock(
                        activation_transaction_id=tx_id,
                        pre_transaction_head_digest=go_record.previous_record_digest,
                        authorization_id=auth.authorization_id,
                        approved_authorization_digest=auth.approved_authorization_digest,
                        expected_previous_state=DurableTransactionState.COMMITTING,
                        terminal_state=DurableTransactionState.ABORTED,
                        abort_reason_code=type(exc).__name__,
                        abort_timestamp_utc=datetime.now(timezone.utc),
                        abort_record_digest="",
                    )
                    final_abort_record = abort_record.model_copy(
                        update={"abort_record_digest": abort_record.compute_digest()}
                    )
                    tx.write_durable_abort_record(final_abort_record)
                    tx.flush_abort_record_barrier(tx_id)
                    tx.rollback_staging(tx_id)
                    try:
                        journal.write_state_durable(JournalState.ABORTED)
                    except Exception:
                        pass
                    raise DataContractError(f"ACTIVATION_PRE_COMMIT_ABORTED: {exc}") from exc


class GateBRecoveryCoordinator:
    """Coordinates startup recovery scan across all transactions in storage substrate."""

    def __init__(
        self,
        ledger: AuthoritativeGOLedger,
        trust_store: Ed25519TrustStore,
        engine_signer: StorageEngineSigner,
    ) -> None:
        self._ledger = ledger
        self._trust_store = trust_store
        self._engine_signer = engine_signer

    def run_recovery(self) -> Dict[UUID, RecoveryResult]:
        """Scan storage substrate for unfinalized transactions and execute recovery decision tree."""
        results: Dict[UUID, RecoveryResult] = {}
        with self._ledger.exclusive_lock() as tx:
            discovered_tx_ids: Set[UUID] = set()

            # 1. Discover from tx_state/
            tx_state_dir = tx._root / "tx_state"
            if tx_state_dir.exists():
                for f in tx_state_dir.glob("*.state"):
                    try:
                        discovered_tx_ids.add(UUID(f.stem))
                    except ValueError:
                        pass

            # 2. Discover from staging/
            staging_dir = tx._root / "staging"
            if staging_dir.exists():
                for p in staging_dir.iterdir():
                    if p.is_dir():
                        try:
                            discovered_tx_ids.add(UUID(p.name))
                        except ValueError:
                            pass

            # 3. Discover from snapshots/
            snapshots_dir = tx._root / "snapshots"
            if snapshots_dir.exists():
                for p in snapshots_dir.iterdir():
                    if p.is_dir():
                        try:
                            discovered_tx_ids.add(UUID(p.name))
                        except ValueError:
                            pass

            # 4. Discover from committed_pointer
            active_tx_id = tx.get_current_active_transaction_id()
            if active_tx_id is not None:
                discovered_tx_ids.add(active_tx_id)

            # Process in deterministic order
            sorted_tx_ids = sorted(discovered_tx_ids, key=lambda u: str(u))

            for tx_id in sorted_tx_ids:
                res = RecoveryDecisionTreeEngine.evaluate_and_recover_transaction(
                    tx=tx,
                    tx_id=tx_id,
                    trust_store=self._trust_store,
                    engine_signer=self._engine_signer,
                )
                results[tx_id] = res

        return results

    def inspect_recovery_state(self) -> Dict[UUID, RecoveryInspectionResult]:
        """Scan storage substrate for transactions and evaluate recovery state strictly read-only (Stage 3.5).

        GUARANTEE: Performs zero file writes, zero rename operations, and zero state alterations.
        """
        results: Dict[UUID, RecoveryInspectionResult] = {}
        with self._ledger.exclusive_lock() as tx:
            discovered_tx_ids: Set[UUID] = set()

            # 1. Discover from tx_state/
            tx_state_dir = tx._root / "tx_state"
            if tx_state_dir.exists():
                for f in tx_state_dir.glob("*.state"):
                    try:
                        discovered_tx_ids.add(UUID(f.stem))
                    except ValueError:
                        pass

            # 2. Discover from staging/
            staging_dir = tx._root / "staging"
            if staging_dir.exists():
                for p in staging_dir.iterdir():
                    if p.is_dir():
                        try:
                            discovered_tx_ids.add(UUID(p.name))
                        except ValueError:
                            pass

            # 3. Discover from snapshots/
            snapshots_dir = tx._root / "snapshots"
            if snapshots_dir.exists():
                for p in snapshots_dir.iterdir():
                    if p.is_dir():
                        try:
                            discovered_tx_ids.add(UUID(p.name))
                        except ValueError:
                            pass

            # 4. Discover from committed_pointer
            active_tx_id = tx.get_current_active_transaction_id()
            if active_tx_id is not None:
                discovered_tx_ids.add(active_tx_id)

            # Process in deterministic order
            sorted_tx_ids = sorted(discovered_tx_ids, key=lambda u: str(u))

            for tx_id in sorted_tx_ids:
                res = RecoveryDecisionTreeEngine.inspect_transaction_state(
                    tx=tx,
                    tx_id=tx_id,
                    trust_store=self._trust_store,
                )
                results[tx_id] = res

        return results

