"""Phase 10: Operational Event Ledger & Telemetry Store (Slice 3).

Strictly enforces:
1. Append-Only Persistence:
   Appends immutable OperationalCycleEvent records to a JSON Lines disk ledger.
2. Cryptographic SHA-256 Event Chaining:
   Event[n].previous_event_digest == Event[n-1].event_digest (genesis == "0" * 64).
3. Monotonic Sequence & Duplicate Protection:
   Sequence numbers must strictly increment by 1 (0, 1, 2, ...). Duplicate cycle_id or sequence is rejected.
4. Tamper & Corruption Fail-Closed Defense:
   Detects corrupted lines, digest mismatches, or broken hash chains upon load and raises DataContractError.
5. Replay & Audit Verification:
   Provides verify_ledger_integrity() to audit entire historical ledger without mutating state.
6. Zero Execution Authority:
   Ledger is an evidence repository; it has zero broker wire or decision authority.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import List, Optional, Sequence, Set, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.runtime.schema import (
    OperationalCycleEvent,
    _ensure_utc,
    _validate_sha256,
)

GENESIS_PREVIOUS_DIGEST = "0" * 64


class OperationalLedger:
    """Thread-safe append-only operational event ledger with cryptographic hash chaining."""

    def __init__(self, persistence_path: Path) -> None:
        self.path: Path = Path(persistence_path)
        self._lock = threading.Lock()
        self._last_event_digest: str = GENESIS_PREVIOUS_DIGEST
        self._last_sequence: int = -1
        self._recorded_cycle_ids: Set[str] = set()
        self._event_count: int = 0

        # Ensure parent directory exists
        if not self.path.parent.exists():
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise DataContractError(f"Failed to create ledger directory '{self.path.parent}': {e}") from e

        # If file exists, replay and verify entire chain on startup
        if self.path.exists() and self.path.stat().st_size > 0:
            self._replay_and_verify_existing_ledger()

    @property
    def event_count(self) -> int:
        """Return total number of committed events."""
        with self._lock:
            return self._event_count

    @property
    def last_event_digest(self) -> str:
        """Return the digest of the most recently appended event (or genesis zeros)."""
        with self._lock:
            return self._last_event_digest

    @property
    def last_sequence(self) -> int:
        """Return the sequence number of the most recently appended event (or -1 if empty)."""
        with self._lock:
            return self._last_sequence

    def _replay_and_verify_existing_ledger(self) -> None:
        """Read and verify all events in the ledger from disk, enforcing fail-closed integrity."""
        expected_prev_digest = GENESIS_PREVIOUS_DIGEST
        expected_seq = 0
        seen_cycle_ids: Set[str] = set()
        count = 0

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    raw_line = line.strip()
                    if not raw_line:
                        continue  # Skip empty lines

                    try:
                        data = json.loads(raw_line)
                    except Exception as e:
                        raise DataContractError(
                            f"Ledger Corrupted at line {line_num}: invalid JSON: {e}"
                        ) from e

                    try:
                        event = OperationalCycleEvent(**data)
                    except Exception as e:
                        raise DataContractError(
                            f"Ledger Corrupted at line {line_num}: invalid OperationalCycleEvent: {e}"
                        ) from e

                    # Verify sequence monotonicity
                    if event.cycle_identity.sequence_number != expected_seq:
                        raise DataContractError(
                            f"Ledger Sequence Corruption at line {line_num}: expected sequence {expected_seq}, got {event.cycle_identity.sequence_number}."
                        )

                    # Verify previous digest chain
                    if event.previous_event_digest != expected_prev_digest:
                        raise DataContractError(
                            f"Ledger Hash Chain Broken at line {line_num}: expected previous_event_digest '{expected_prev_digest}', got '{event.previous_event_digest}'."
                        )

                    # Verify cycle_id uniqueness
                    cid = event.cycle_identity.cycle_id
                    if cid in seen_cycle_ids:
                        raise DataContractError(
                            f"Ledger Duplicate Cycle ID at line {line_num}: cycle_id '{cid}' already committed."
                        )

                    seen_cycle_ids.add(cid)
                    expected_prev_digest = event.event_digest
                    expected_seq += 1
                    count += 1
        except (OSError, IOError) as e:
            raise DataContractError(f"Ledger read failure on '{self.path}': {e}") from e

        self._last_event_digest = expected_prev_digest
        self._last_sequence = expected_seq - 1
        self._recorded_cycle_ids = seen_cycle_ids
        self._event_count = count

    def append_event(self, event: OperationalCycleEvent) -> None:
        """Append an OperationalCycleEvent to the disk ledger with cryptographic chaining."""
        with self._lock:
            expected_seq = self._last_sequence + 1
            if event.cycle_identity.sequence_number != expected_seq:
                raise DataContractError(
                    f"Invalid Event Sequence: expected {expected_seq}, got {event.cycle_identity.sequence_number}."
                )

            if event.previous_event_digest != self._last_event_digest:
                raise DataContractError(
                    f"Broken Event Chain: expected previous_event_digest '{self._last_event_digest}', got '{event.previous_event_digest}'."
                )

            cid = event.cycle_identity.cycle_id
            if cid in self._recorded_cycle_ids:
                raise DataContractError(
                    f"Duplicate Event Rejected: cycle_id '{cid}' already recorded in ledger."
                )

            # Serialize to canonical single-line JSON
            try:
                line = event.model_dump_json() + "\n"
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
            except (OSError, IOError) as e:
                raise DataContractError(f"Ledger write failure on '{self.path}': {e}") from e

            self._recorded_cycle_ids.add(cid)
            self._last_event_digest = event.event_digest
            self._last_sequence = expected_seq
            self._event_count += 1

    def read_all_events(self) -> List[OperationalCycleEvent]:
        """Read and return all committed events from disk."""
        with self._lock:
            if not self.path.exists() or self.path.stat().st_size == 0:
                return []

            events: List[OperationalCycleEvent] = []
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    raw_line = line.strip()
                    if raw_line:
                        events.append(OperationalCycleEvent(**json.loads(raw_line)))
            return events

    def verify_ledger_integrity(self) -> Tuple[bool, int, str]:
        """Audit the full ledger file and return (is_valid, event_count, head_digest)."""
        with self._lock:
            expected_prev_digest = GENESIS_PREVIOUS_DIGEST
            expected_seq = 0
            seen_cycle_ids: Set[str] = set()

            if not self.path.exists() or self.path.stat().st_size == 0:
                return True, 0, GENESIS_PREVIOUS_DIGEST

            with open(self.path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    raw_line = line.strip()
                    if not raw_line:
                        continue

                    data = json.loads(raw_line)
                    event = OperationalCycleEvent(**data)

                    if event.cycle_identity.sequence_number != expected_seq:
                        raise DataContractError(f"Sequence mismatch at line {line_num}")
                    if event.previous_event_digest != expected_prev_digest:
                        raise DataContractError(f"Chain broken at line {line_num}")
                    if event.cycle_identity.cycle_id in seen_cycle_ids:
                        raise DataContractError(f"Duplicate cycle_id at line {line_num}")

                    seen_cycle_ids.add(event.cycle_identity.cycle_id)
                    expected_prev_digest = event.event_digest
                    expected_seq += 1

            return True, expected_seq, expected_prev_digest
