"""Phase 13 Slice 2: Recovery Engine & Proof of Uncommitted State (Stage 3.1).

Implements:
- Three-tier recovery decision tree starting strictly from authoritative tx_state (B92, B95)
- Disk-authoritative proof of pre-commit uncommitted state (is_provably_uncommitted) (B76, B80, B94)
- Strict B94 namespace separation (residual snapshots on abort force QUARANTINE_LOCKED)
- Missing tx_state commit evidence inspection (fail-closed to quarantine on ambiguity)
- Anti-silent rollback guards (B88, B93, Crash-12)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from acash.execution.crypto import Ed25519TrustStore
from acash.gate_b.exceptions import DataContractError, QuarantineError
from acash.gate_b.schema import (
    AuthoritativeAbortRecordBlock,
    AuthoritativeCommitRecordBlock,
    DurablePointerTransitionRecord,
    DurableTransactionState,
    HumanGORecord,
    JournalState,
    LiveAuthorization,
    SystemSafetyMode,
)
from acash.gate_b.storage import (
    GENESIS_HEAD_DIGEST,
    LedgerStorageTransaction,
    StorageEngineSigner,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecoveryResult:
    """Outcome of recovery decision tree execution."""

    tier: int
    final_state: DurableTransactionState
    system_mode: SystemSafetyMode
    details: str


def has_any_durable_commit_evidence(tx: LedgerStorageTransaction, tx_id: UUID) -> bool:
    """Inspect whether any durable filesystem evidence exists for transaction (Blocker 1 resolution).

    Checks:
    1. Does /snapshots/<tx_id>/ exist?
    2. Does pointer/committed_pointer reference tx_id?
    3. Does pointer/transition.json reference tx_id?
    4. Does a commit marker block exist in snapshot or staging?
    5. Has authoritative ledger head advanced beyond pre-transaction head?
    """
    if tx.has_snapshot_directory(tx_id):
        return True

    if tx.committed_pointer_references_transaction(tx_id):
        return True

    if tx.has_durable_commit_marker(tx_id):
        return True

    trans = tx.read_pointer_transition_record()
    if trans is not None and (trans.new_tx_id == tx_id or trans.previous_tx_id == tx_id):
        return True

    pre_head = tx.get_pre_transaction_head_digest_from_disk(tx_id)
    curr_head = tx.get_durable_head_digest()
    if curr_head != GENESIS_HEAD_DIGEST and curr_head != pre_head:
        return True

    return False


def is_provably_uncommitted(
    tx: LedgerStorageTransaction,
    tx_id: UUID,
    optional_in_memory_auth: Optional[LiveAuthorization] = None,
) -> bool:
    """Assert DISK-AUTHORITATIVE persistent proof that storage entered terminal ABORTED state (B76, B80, B94).

    Returns True ONLY if all abort proof criteria and strict namespace invariants hold.
    """
    try:
        abort_record = tx.read_durable_abort_record(tx_id)
        if abort_record is None or not abort_record.is_valid():
            return False

        if abort_record.compute_digest() != abort_record.abort_record_digest:
            return False

        if abort_record.activation_transaction_id != tx_id:
            return False

        durable_pre_head = tx.get_pre_transaction_head_digest_from_disk(tx_id)
        if abort_record.pre_transaction_head_digest != durable_pre_head:
            return False

        durable_draft_digest = tx.read_durable_draft_authorization_digest(abort_record.authorization_id)
        if durable_draft_digest and abort_record.approved_authorization_digest != durable_draft_digest:
            return False

        if abort_record.terminal_state != DurableTransactionState.ABORTED:
            return False

        if tx.get_durable_tx_state(tx_id) != DurableTransactionState.ABORTED:
            return False
        if not tx.assert_abort_is_terminal(tx_id):
            return False

        # CRITICAL B94 INVARIANT: Strict Namespace Separation
        # If /snapshots/<tx_id> exists AT ALL, this is a fatal contradiction!
        if tx.has_snapshot_directory(tx_id):
            tx.log_consistency_violation(f"Snapshot directory /snapshots/{tx_id} exists for aborted tx {tx_id}")
            return False

        if tx.committed_pointer_references_transaction(tx_id):
            tx.log_consistency_violation(f"Committed pointer references aborted tx {tx_id}")
            return False

        if tx.has_durable_commit_marker(tx_id):
            tx.log_consistency_violation(f"Commit marker present on aborted tx {tx_id}")
            return False

        if tx.get_durable_head_digest() != durable_pre_head:
            tx.log_consistency_violation(f"Head digest advanced on aborted tx {tx_id}")
            return False

        # CRITICAL B92 INVARIANT: Journal marked COMMITTED cannot exist for aborted transaction
        journal = tx.create_wal_journal(tx_id, "", None)
        if journal.read_latest_state() == JournalState.COMMITTED:
            tx.log_consistency_violation(f"Journal marked COMMITTED for aborted tx {tx_id}")
            return False

        if optional_in_memory_auth is not None:
            if abort_record.authorization_id != optional_in_memory_auth.authorization_id:
                return False
            if abort_record.approved_authorization_digest != optional_in_memory_auth.approved_authorization_digest:
                return False

        return True
    except Exception:
        return False


def read_commit_record_block_from_snapshot(
    tx: LedgerStorageTransaction, tx_id: UUID
) -> Optional[AuthoritativeCommitRecordBlock]:
    """Read and validate AuthoritativeCommitRecordBlock from snapshot directory."""
    marker_file = tx._snapshots_dir / str(tx_id) / "commit_record_block.json"
    if not marker_file.exists():
        return None
    try:
        with open(marker_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            normalized: Dict[str, Any] = {}
            for k, v in data.items():
                if isinstance(v, dict) and "value" in v:
                    normalized[k] = v["value"]
                else:
                    normalized[k] = v
            return AuthoritativeCommitRecordBlock.model_validate(normalized)
    except Exception:
        return None


class RecoveryDecisionTreeEngine:
    """Implements Unidirectional Three-Tier Recovery starting strictly from durable tx_state (B92, B95)."""

    @staticmethod
    def evaluate_and_recover_transaction(
        tx: LedgerStorageTransaction,
        tx_id: UUID,
        trust_store: Ed25519TrustStore,
        engine_signer: StorageEngineSigner,
    ) -> RecoveryResult:
        """Execute recovery decision tree starting strictly from tx_state (B92)."""
        tx_state = tx.get_durable_tx_state(tx_id)

        # -------------------------------------------------------------
        # CRITICAL B92 INVARIANT: Journal State is strictly secondary
        # If journal == COMMITTED but tx_state != COMMITTED, journal
        # MUST NEVER elevate transaction to COMMITTED (forces QUARANTINE_LOCKED).
        # -------------------------------------------------------------
        journal = tx.create_wal_journal(tx_id, "", None)
        if journal.read_latest_state() == JournalState.COMMITTED and tx_state != DurableTransactionState.COMMITTED:
            tx.log_consistency_violation(
                f"B92 VIOLATION: Journal marked COMMITTED for tx {tx_id} but tx_state is {tx_state}"
            )
            tx.set_tx_state_durable(tx_id, DurableTransactionState.QUARANTINED)
            tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)
            return RecoveryResult(
                tier=3,
                final_state=DurableTransactionState.QUARANTINED,
                system_mode=SystemSafetyMode.QUARANTINE_LOCKED,
                details=f"B92 divergence: Journal marked COMMITTED while tx_state is {tx_state} (cannot elevate state)",
            )

        # -------------------------------------------------------------
        # BRANCH 1: tx_state == COMMITTED (Tier 2 or Tier 3)
        # -------------------------------------------------------------
        if tx_state == DurableTransactionState.COMMITTED:
            trans = tx.read_pointer_transition_record()
            is_active_or_prev = (
                tx.committed_pointer_references_transaction(tx_id)
                or (trans is not None and trans.previous_tx_id == tx_id)
            )
            if not is_active_or_prev:
                tx.log_consistency_violation(f"COMMITTED state but pointer does not reference tx {tx_id}")
                tx.set_tx_state_durable(tx_id, DurableTransactionState.QUARANTINED)
                tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)
                return RecoveryResult(
                    tier=3,
                    final_state=DurableTransactionState.QUARANTINED,
                    system_mode=SystemSafetyMode.QUARANTINE_LOCKED,
                    details="COMMITTED state but pointer does not reference tx_id (fatal contradiction)",
                )

            commit_block = read_commit_record_block_from_snapshot(tx, tx_id)
            if commit_block is None:
                tx.log_consistency_violation(f"COMMITTED state but commit marker block missing for {tx_id}")
                tx.set_tx_state_durable(tx_id, DurableTransactionState.QUARANTINED)
                tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)
                return RecoveryResult(
                    tier=3,
                    final_state=DurableTransactionState.QUARANTINED,
                    system_mode=SystemSafetyMode.QUARANTINE_LOCKED,
                    details="COMMITTED state but commit marker block missing in snapshot",
                )

            if not tx.deep_verify_snapshot_manifest(tx_id, commit_block):
                tx.log_consistency_violation(f"COMMITTED state but manifest verification failed for {tx_id}")
                tx.set_tx_state_durable(tx_id, DurableTransactionState.QUARANTINED)
                tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)
                return RecoveryResult(
                    tier=3,
                    final_state=DurableTransactionState.QUARANTINED,
                    system_mode=SystemSafetyMode.QUARANTINE_LOCKED,
                    details="COMMITTED state but deep manifest verification failed (tampering detected)",
                )

            # Rebuild journal entry if missing or divergent
            journal = tx.create_wal_journal(tx_id, commit_block.approved_authorization_digest, None)
            if journal.read_latest_state() != JournalState.COMMITTED:
                try:
                    journal.write_state_durable(JournalState.COMMITTED)
                except Exception:
                    pass

            return RecoveryResult(
                tier=2,
                final_state=DurableTransactionState.COMMITTED,
                system_mode=SystemSafetyMode.NORMAL,
                details="Idempotent re-verification of committed transaction succeeded",
            )

        # -------------------------------------------------------------
        # BRANCH 2: tx_state == COMMITTING (In-flight commit recovery)
        # -------------------------------------------------------------
        if tx_state == DurableTransactionState.COMMITTING:
            pointer_active = tx.committed_pointer_references_transaction(tx_id)
            transition_record = tx.read_pointer_transition_record()

            # Check if pointer switched and transition record is cryptographically authentic (B88, B93)
            if pointer_active and transition_record is not None:
                valid_auth = transition_record.is_valid_transition(
                    expected_tx_id=tx_id,
                    expected_prev_tx_id=transition_record.previous_tx_id,
                    expected_manifest_digest=transition_record.commit_intent_digest,
                    trust_store=trust_store,
                )
                commit_block = read_commit_record_block_from_snapshot(tx, tx_id)
                manifest_valid = (
                    commit_block is not None
                    and commit_block.mutation_manifest_digest == transition_record.commit_intent_digest
                    and tx.deep_verify_snapshot_manifest(tx_id, commit_block)
                )

                if valid_auth and manifest_valid:
                    # Attempt CAS completion: COMMITTING -> COMMITTED
                    cas_ok = tx.compare_and_set_tx_state(
                        tx_id,
                        expected=DurableTransactionState.COMMITTING,
                        new=DurableTransactionState.COMMITTED,
                    )
                    if cas_ok:
                        if commit_block is not None:
                            tx.set_head_digest_durable(commit_block.advanced_head_digest)
                        journal = tx.create_wal_journal(tx_id, transition_record.commit_intent_digest, None)
                        try:
                            journal.write_state_durable(JournalState.COMMITTED)
                        except Exception:
                            pass
                        return RecoveryResult(
                            tier=2,
                            final_state=DurableTransactionState.COMMITTED,
                            system_mode=SystemSafetyMode.NORMAL,
                            details="In-flight commit recovered: CAS transition COMMITTING -> COMMITTED succeeded",
                        )
                    else:
                        tx.handle_post_pointer_switch_cas_failure(tx_id, transition_record)
                        return RecoveryResult(
                            tier=3,
                            final_state=DurableTransactionState.QUARANTINED,
                            system_mode=SystemSafetyMode.QUARANTINE_LOCKED,
                            details="CAS failed during in-flight commit recovery; rolled back pointer if authentic",
                        )
                else:
                    # Transition record unauthenticated or manifest invalid (Crash-12)
                    tx.set_tx_state_durable(tx_id, DurableTransactionState.QUARANTINED)
                    tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)
                    return RecoveryResult(
                        tier=3,
                        final_state=DurableTransactionState.QUARANTINED,
                        system_mode=SystemSafetyMode.QUARANTINE_LOCKED,
                        details="Pointer switched but transition record unauthenticated or manifest invalid",
                    )
            else:
                # Pointer transition absent or incomplete prior to pointer switch (Crash-04)
                tx.set_tx_state_durable(tx_id, DurableTransactionState.QUARANTINED)
                tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)
                return RecoveryResult(
                    tier=3,
                    final_state=DurableTransactionState.QUARANTINED,
                    system_mode=SystemSafetyMode.QUARANTINE_LOCKED,
                    details="In-flight commit without active pointer; conservative quarantine (B90)",
                )

        # -------------------------------------------------------------
        # BRANCH 3: tx_state == ABORTED (Tier 1 or Tier 3)
        # -------------------------------------------------------------
        if tx_state == DurableTransactionState.ABORTED:
            if is_provably_uncommitted(tx, tx_id):
                tx.rollback_staging(tx_id)
                return RecoveryResult(
                    tier=1,
                    final_state=DurableTransactionState.ABORTED,
                    system_mode=SystemSafetyMode.NORMAL,
                    details="Clean terminal abort proven: staging discarded, status remains APPROVED_PENDING_GO",
                )
            else:
                # Fatal B94 violation (e.g. residual /snapshots/<tx_id> exists)
                tx.set_tx_state_durable(tx_id, DurableTransactionState.QUARANTINED)
                tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)
                return RecoveryResult(
                    tier=3,
                    final_state=DurableTransactionState.QUARANTINED,
                    system_mode=SystemSafetyMode.QUARANTINE_LOCKED,
                    details="ABORTED state failed uncommitted proof (B94 contradiction or corrupt abort record)",
                )

        # -------------------------------------------------------------
        # BRANCH 4: tx_state == PREPARED or None (Missing) (Blocker 1 Resolution)
        # -------------------------------------------------------------
        if tx_state == DurableTransactionState.PREPARED or tx_state is None:
            # Check for any durable commit evidence before concluding abort
            if has_any_durable_commit_evidence(tx, tx_id):
                tx.log_consistency_violation(
                    f"Transaction {tx_id} state is {tx_state} but durable commit evidence exists!"
                )
                tx.set_tx_state_durable(tx_id, DurableTransactionState.QUARANTINED)
                tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)
                return RecoveryResult(
                    tier=3,
                    final_state=DurableTransactionState.QUARANTINED,
                    system_mode=SystemSafetyMode.QUARANTINE_LOCKED,
                    details=f"Missing or PREPARED tx_state with conflicting durable commit evidence (B92 contradiction)",
                )
            else:
                # Zero commit evidence exists; provably pre-commit
                tx.rollback_staging(tx_id)
                return RecoveryResult(
                    tier=1,
                    final_state=DurableTransactionState.ABORTED,
                    system_mode=SystemSafetyMode.NORMAL,
                    details="Clean pre-commit state with zero commit evidence: staging discarded",
                )

        # -------------------------------------------------------------
        # BRANCH 5: tx_state == QUARANTINED (Tier 3)
        # -------------------------------------------------------------
        tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)
        return RecoveryResult(
            tier=3,
            final_state=DurableTransactionState.QUARANTINED,
            system_mode=SystemSafetyMode.QUARANTINE_LOCKED,
            details="Transaction explicitly in QUARANTINED state; system safety mode locked",
        )
