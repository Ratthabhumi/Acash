"""ACASH Paper Trading — Daily Snapshot Store.

DailySnapshot captures an end-of-day operational summary for audit.
Snapshots reference the underlying event journal (not replace it).

DailySnapshotStore appends snapshots to a persistent JSON Lines file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer


@dataclass
class DailySnapshot:
    """End-of-day operational summary for one trading day.

    References the underlying event journal; does NOT replace it.
    """

    snapshot_id: str
    session_id: str
    trading_date: date
    captured_at_utc: datetime

    # Portfolio state
    starting_equity: Decimal
    ending_equity: Decimal
    pnl: Decimal
    cash: Decimal

    # Activity counts
    trade_count: int
    order_count: int
    rejected_order_count: int
    signal_count: int
    risk_rejection_count: int

    # System health
    system_incident_count: int
    feed_disconnect_count: int
    stale_data_count: int
    exception_count: int
    reconciliation_failures: int
    journal_integrity_status: str

    # Journal references
    first_event_sequence: int
    last_event_sequence: int
    first_event_hash: str
    last_event_hash: str

    # Labels
    governance_label: str = "OBSERVED_PAPER_DATA_ONLY"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "session_id": self.session_id,
            "trading_date": self.trading_date.isoformat(),
            "captured_at_utc": self.captured_at_utc.isoformat(),
            "starting_equity": str(self.starting_equity),
            "ending_equity": str(self.ending_equity),
            "pnl": str(self.pnl),
            "cash": str(self.cash),
            "trade_count": self.trade_count,
            "order_count": self.order_count,
            "rejected_order_count": self.rejected_order_count,
            "signal_count": self.signal_count,
            "risk_rejection_count": self.risk_rejection_count,
            "system_incident_count": self.system_incident_count,
            "feed_disconnect_count": self.feed_disconnect_count,
            "stale_data_count": self.stale_data_count,
            "exception_count": self.exception_count,
            "reconciliation_failures": self.reconciliation_failures,
            "journal_integrity_status": self.journal_integrity_status,
            "first_event_sequence": self.first_event_sequence,
            "last_event_sequence": self.last_event_sequence,
            "first_event_hash": self.first_event_hash,
            "last_event_hash": self.last_event_hash,
            "governance_label": self.governance_label,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DailySnapshot":
        return cls(
            snapshot_id=d["snapshot_id"],
            session_id=d["session_id"],
            trading_date=date.fromisoformat(d["trading_date"]),
            captured_at_utc=datetime.fromisoformat(d["captured_at_utc"]),
            starting_equity=Decimal(d["starting_equity"]),
            ending_equity=Decimal(d["ending_equity"]),
            pnl=Decimal(d["pnl"]),
            cash=Decimal(d["cash"]),
            trade_count=int(d["trade_count"]),
            order_count=int(d["order_count"]),
            rejected_order_count=int(d.get("rejected_order_count", 0)),
            signal_count=int(d.get("signal_count", 0)),
            risk_rejection_count=int(d.get("risk_rejection_count", 0)),
            system_incident_count=int(d.get("system_incident_count", 0)),
            feed_disconnect_count=int(d.get("feed_disconnect_count", 0)),
            stale_data_count=int(d.get("stale_data_count", 0)),
            exception_count=int(d.get("exception_count", 0)),
            reconciliation_failures=int(d.get("reconciliation_failures", 0)),
            journal_integrity_status=d.get("journal_integrity_status", "NOT_CHECKED"),
            first_event_sequence=int(d.get("first_event_sequence", 0)),
            last_event_sequence=int(d.get("last_event_sequence", 0)),
            first_event_hash=d.get("first_event_hash", "0" * 64),
            last_event_hash=d.get("last_event_hash", "0" * 64),
            governance_label=d.get("governance_label", "OBSERVED_PAPER_DATA_ONLY"),
        )


class DailySnapshotStore:
    """Append-only store for daily snapshots. Never overwrites existing snapshots."""

    def __init__(self, persistence_path: Path) -> None:
        self._path = Path(persistence_path)
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise DataContractError(
                f"DailySnapshotStore: cannot create directory '{self._path.parent}': {exc}"
            ) from exc

    def append(self, snapshot: DailySnapshot) -> None:
        """Append a snapshot. Fail-closed on persistence failure."""
        try:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(snapshot.to_dict()) + "\n")
                fh.flush()
        except Exception as exc:
            raise DataContractError(
                f"DailySnapshotStore: persistence failure for snapshot "
                f"'{snapshot.snapshot_id}': {exc}"
            ) from exc

    def read_all(self) -> List[DailySnapshot]:
        """Read all snapshots from disk."""
        if not self._path.exists():
            return []
        snapshots: List[DailySnapshot] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line_num, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    snapshots.append(DailySnapshot.from_dict(d))
                except Exception as exc:
                    raise DataContractError(
                        f"DailySnapshotStore: corrupted snapshot at line {line_num}: {exc}"
                    ) from exc
        return snapshots
