"""Phase 13 Slice 2: Disambiguated Snapshot Readers & Quarantine Boundaries (Stage 3.2).

Implements:
- AuthoritativeSnapshotView (§3.10, B85): Immutable, validated snapshot view
- SnapshotReaderService (§3.10, B65, B75, B81, B85, B86):
  - read_active_committed_snapshot(): Follows pointer under atomic lock boundary
  - read_committed_snapshot(tx_id): Historical snapshot reader with explicit identity binding
- Invariant 1: Atomic & consistent reader boundary under single lock
- Invariant 2: Authoritative quarantine escalation path with fatal safety halt on write failure
- Invariant 3: Explicit cross-transaction identity binding across directory, block, and manifest
- Staging invisibility (B65): Readers observe strictly /snapshots/<tx_id>/
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import logging
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from acash.gate_b.exceptions import DataContractError, QuarantineError
from acash.gate_b.schema import (
    AuthoritativeCommitRecordBlock,
    DurableTransactionState,
    HumanGORecord,
    LiveAuthorization,
    SystemSafetyMode,
)
from acash.gate_b.storage import AuthoritativeGOLedger, LedgerStorageTransaction

logger = logging.getLogger(__name__)


class AuthoritativeSnapshotView(BaseModel):
    """Immutable, validated runtime view of a committed snapshot (§3.10, B85)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    transaction_id: UUID = Field(description="Storage transaction ID of snapshot.")
    commit_record_block: AuthoritativeCommitRecordBlock = Field(
        description="Authoritative manifest binding all entities."
    )
    record: Optional[HumanGORecord] = Field(
        default=None,
        description="Bound HumanGORecord from snapshot.",
    )
    head_digest: str = Field(description="Authoritative advanced head digest.")
    authorization: Optional[LiveAuthorization] = Field(
        default=None,
        description="Bound LiveAuthorization artifact from snapshot.",
    )


def _read_commit_record_block_from_snapshot(
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


def _read_record_from_snapshot(
    tx: LedgerStorageTransaction, tx_id: UUID
) -> Optional[HumanGORecord]:
    """Read and validate HumanGORecord from snapshot directory."""
    rec_file = tx._snapshots_dir / str(tx_id) / "record.json"
    if not rec_file.exists():
        return None
    try:
        with open(rec_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            normalized: Dict[str, Any] = {}
            for k, v in data.items():
                if isinstance(v, dict) and "value" in v:
                    normalized[k] = v["value"]
                else:
                    normalized[k] = v
            return HumanGORecord.model_validate(normalized)
    except Exception:
        return None


def _read_authorization_from_snapshot(
    tx: LedgerStorageTransaction, tx_id: UUID
) -> Optional[LiveAuthorization]:
    """Read and validate LiveAuthorization from snapshot directory."""
    auth_file = tx._snapshots_dir / str(tx_id) / "authorization.json"
    if not auth_file.exists():
        return None
    try:
        with open(auth_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            normalized: Dict[str, Any] = {}
            for k, v in data.items():
                if isinstance(v, dict) and "value" in v:
                    normalized[k] = v["value"]
                else:
                    normalized[k] = v
            return LiveAuthorization.model_validate(normalized)
    except Exception:
        return None


@contextmanager
def _resolve_transaction_context(
    storage: Union[LedgerStorageTransaction, AuthoritativeGOLedger],
) -> Generator[LedgerStorageTransaction, None, None]:
    """Ensure consistent lock boundary across all reader inspection operations (Invariant 1)."""
    if isinstance(storage, AuthoritativeGOLedger):
        with storage.exclusive_lock() as tx:
            yield tx
    elif isinstance(storage, LedgerStorageTransaction):
        yield storage
    else:
        raise DataContractError(
            f"INVALID_STORAGE_TYPE: Expected AuthoritativeGOLedger or LedgerStorageTransaction, got {type(storage)}"
        )


def _escalate_quarantine(
    tx: LedgerStorageTransaction,
    tx_id: UUID,
    violation_message: str,
) -> None:
    """Escalate a detected snapshot integrity violation to persistent quarantine (Invariant 2).

    If attempting to write quarantine state to storage fails, executes fatal safety halt.
    """
    try:
        tx.log_consistency_violation(violation_message)
        tx.set_tx_state_durable(tx_id, DurableTransactionState.QUARANTINED)
        tx.set_system_safety_mode(SystemSafetyMode.QUARANTINE_LOCKED)
    except Exception as esc_exc:
        logger.critical(
            "FATAL_SAFETY_HALT: Failed to persist quarantine state for corrupted tx %s: %s",
            tx_id,
            esc_exc,
        )
        raise QuarantineError(
            f"QUARANTINE_ESCALATION_FAILED_FATAL_SAFETY_HALT: Could not persist quarantine state for tx {tx_id}: {esc_exc}"
        ) from esc_exc

    raise QuarantineError(
        f"ACTIVE_SNAPSHOT_CORRUPTED_ENTERING_QUARANTINE: {violation_message}"
    )


class SnapshotReaderService:
    """Disambiguated, consistent reader contracts over versioned snapshots (B81, B85)."""

    @staticmethod
    def read_active_committed_snapshot(
        storage: Union[LedgerStorageTransaction, AuthoritativeGOLedger],
    ) -> AuthoritativeSnapshotView:
        """Fetch current active committed snapshot via disambiguated reader API (B81, B85).

        Operates under an atomic consistent lock boundary (Invariant 1).
        """
        with _resolve_transaction_context(storage) as tx:
            # 1. Read committed pointer atomically
            active_tx_id = tx.get_current_active_transaction_id()
            if active_tx_id is None:
                raise DataContractError("NO_ACTIVE_COMMITTED_SNAPSHOT_AVAILABLE")

            # 2. Verify durable transaction state is COMMITTED (B82, B85)
            state = tx.get_durable_tx_state(active_tx_id)
            if state != DurableTransactionState.COMMITTED:
                raise DataContractError(
                    f"ACTIVE_SNAPSHOT_TX_NOT_COMMITTED: Active tx {active_tx_id} state is {state}"
                )

            # 3. Verify snapshot directory exists
            if not tx.has_snapshot_directory(active_tx_id):
                raise DataContractError(
                    f"SNAPSHOT_DIRECTORY_MISSING: Snapshot directory for active tx {active_tx_id} does not exist"
                )

            # 4. Read commit record block
            commit_block = _read_commit_record_block_from_snapshot(tx, active_tx_id)
            if commit_block is None:
                _escalate_quarantine(
                    tx,
                    active_tx_id,
                    f"Commit marker block missing in active snapshot directory for tx {active_tx_id}",
                )

            # 5. Invariant 3: Explicit Cross-Transaction Identity Binding
            assert commit_block is not None
            if commit_block.activation_transaction_id != active_tx_id:
                _escalate_quarantine(
                    tx,
                    active_tx_id,
                    f"CROSS_TRANSACTION_IDENTITY_MISMATCH: Active pointer tx {active_tx_id} "
                    f"!= commit_block.activation_transaction_id {commit_block.activation_transaction_id}",
                )

            # 6. Verify internal manifest integrity (B77, B79)
            if not commit_block.verify_manifest_integrity():
                _escalate_quarantine(
                    tx,
                    active_tx_id,
                    f"Commit marker block manifest integrity verification failed for active tx {active_tx_id}",
                )

            # 7. Deep manifest verification prior to visibility (B75, B86)
            if not tx.deep_verify_snapshot_manifest(active_tx_id, commit_block):
                _escalate_quarantine(
                    tx,
                    active_tx_id,
                    f"Deep manifest verification failed for active snapshot tx {active_tx_id} (tampering detected)",
                )

            # 8. Read operational entities from snapshot
            record = _read_record_from_snapshot(tx, active_tx_id)
            auth = _read_authorization_from_snapshot(tx, active_tx_id)

            return AuthoritativeSnapshotView(
                transaction_id=active_tx_id,
                commit_record_block=commit_block,
                record=record,
                head_digest=commit_block.advanced_head_digest,
                authorization=auth,
            )

    @staticmethod
    def read_committed_snapshot(
        storage: Union[LedgerStorageTransaction, AuthoritativeGOLedger],
        tx_id: UUID,
    ) -> AuthoritativeSnapshotView:
        """Read historical committed snapshot by transaction ID without relying on active pointer (B85).

        Operates under an atomic consistent lock boundary (Invariant 1).
        """
        with _resolve_transaction_context(storage) as tx:
            # 1. Verify durable transaction state is COMMITTED
            state = tx.get_durable_tx_state(tx_id)
            if state != DurableTransactionState.COMMITTED:
                raise DataContractError(
                    f"CANNOT_READ_UNCOMMITTED_SNAPSHOT: Transaction {tx_id} state is {state}"
                )

            # 2. Verify snapshot directory exists
            if not tx.has_snapshot_directory(tx_id):
                raise DataContractError(
                    f"SNAPSHOT_DIRECTORY_MISSING: Snapshot directory for tx {tx_id} does not exist"
                )

            # 3. Read commit record block
            commit_block = _read_commit_record_block_from_snapshot(tx, tx_id)
            if commit_block is None:
                _escalate_quarantine(
                    tx,
                    tx_id,
                    f"Commit marker block missing in snapshot directory for tx {tx_id}",
                )

            # 4. Invariant 3: Explicit Cross-Transaction Identity Binding
            assert commit_block is not None
            if commit_block.activation_transaction_id != tx_id:
                _escalate_quarantine(
                    tx,
                    tx_id,
                    f"CROSS_TRANSACTION_IDENTITY_MISMATCH: Directory tx_id {tx_id} "
                    f"!= commit_block.activation_transaction_id {commit_block.activation_transaction_id}",
                )

            # 5. Verify internal manifest integrity (B77, B79)
            if not commit_block.verify_manifest_integrity():
                _escalate_quarantine(
                    tx,
                    tx_id,
                    f"Commit marker block manifest integrity verification failed for tx {tx_id}",
                )

            # 6. Deep manifest verification prior to visibility (B75, B86)
            if not tx.deep_verify_snapshot_manifest(tx_id, commit_block):
                _escalate_quarantine(
                    tx,
                    tx_id,
                    f"Deep manifest verification failed for snapshot tx {tx_id} (tampering detected)",
                )

            # 7. Read operational entities from snapshot
            record = _read_record_from_snapshot(tx, tx_id)
            auth = _read_authorization_from_snapshot(tx, tx_id)

            return AuthoritativeSnapshotView(
                transaction_id=tx_id,
                commit_record_block=commit_block,
                record=record,
                head_digest=commit_block.advanced_head_digest,
                authorization=auth,
            )
