"""Phase 13: Crash/Restart State Recovery & Reconciliation.

Strictly enforces:
1. Schema-grounded state recovery from disk snapshot bound to OperationalLedger hash.
2. Clean recovery: verified ledger + snapshot matches broker.
3. Discrepancy halt: live broker position != local snapshot halts startup.
4. Fail-closed defense: corrupted ledger raises DataContractError immediately.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.core.serialization import CanonicalConfigSerializer
from acash.runtime.ledger import OperationalLedger
from acash.runtime.schema import OperationalCycleEvent


class RehydrationStatus(str, Enum):
    """Classification of the state rehydration outcome."""

    CLEAN_RECOVERY = "CLEAN_RECOVERY"
    DISCREPANCY_HALT = "DISCREPANCY_HALT"
    EMPTY_GENESIS = "EMPTY_GENESIS"


class PortfolioSnapshotStore:
    """Helper for reading and writing cryptographically verified PortfolioState snapshots."""

    @staticmethod
    def compute_digest(snapshot: PortfolioState) -> str:
        """Compute canonical SHA-256 digest of PortfolioState."""
        positions_payload = {}
        for sym, pos in sorted(snapshot.positions.items()):
            positions_payload[sym] = {
                "symbol": pos.symbol,
                "quantity": str(pos.quantity),
                "entry_price": str(pos.entry_price),
                "current_price": str(pos.current_price),
                "unrealized_pnl": str(pos.unrealized_pnl),
                "realized_pnl": str(pos.realized_pnl),
            }

        payload = {
            "timestamp_utc": snapshot.timestamp_utc.isoformat(),
            "positions": positions_payload,
            "cash_balance": str(snapshot.cash_balance),
            "total_equity": str(snapshot.total_equity),
            "margin_used": str(snapshot.margin_used),
            "gross_exposure": str(snapshot.gross_exposure),
            "net_exposure": str(snapshot.net_exposure),
            "unrealized_pnl": str(snapshot.unrealized_pnl),
            "realized_pnl": str(snapshot.realized_pnl),
        }
        canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    @classmethod
    def save_snapshot(cls, snapshot: PortfolioState, path: Path) -> str:
        """Serialize PortfolioState to disk and return computed digest."""
        path.parent.mkdir(parents=True, exist_ok=True)
        digest = cls.compute_digest(snapshot)
        data = {
            "digest": digest,
            "state": json.loads(snapshot.model_dump_json()),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return digest

    @classmethod
    def load_snapshot(cls, path: Path) -> PortfolioState:
        """Deserialize PortfolioState from disk JSON file."""
        if not path.exists():
            raise DataContractError(f"Snapshot file not found: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            state_data = data.get("state", data)
            return PortfolioState.model_validate(state_data)
        except Exception as e:
            raise DataContractError(f"Failed to load snapshot from '{path}': {e}") from e


class PortfolioStateRehydrator:
    """State rehydration engine verifying disk ledger, snapshot digests, and broker reality."""

    def __init__(
        self,
        ledger: OperationalLedger,
        snapshot_dir: Path,
        broker_adapter: Optional[Any] = None,
    ) -> None:
        self.ledger = ledger
        self.snapshot_dir = Path(snapshot_dir)
        self.broker_adapter = broker_adapter
        self._snapshot_store = PortfolioSnapshotStore()

    def _verify_snapshot_hash(
        self,
        snapshot: PortfolioState,
        expected_digest: str,
    ) -> bool:
        """Verify that computed digest matches expected digest from ledger event."""
        computed = self._snapshot_store.compute_digest(snapshot)
        return computed == expected_digest

    def rehydrate(
        self,
        as_of_utc: datetime,
    ) -> Tuple[PortfolioState, AccountState, RehydrationStatus]:
        """Rehydrate portfolio and account state from disk ledger, snapshots, and broker checks."""
        if as_of_utc.tzinfo is None:
            as_of_utc = as_of_utc.replace(tzinfo=timezone.utc)

        # 1. Audit Ledger Integrity (Vector V-08: corrupted ledger raises DataContractError)
        is_valid, event_count, head_digest = self.ledger.verify_ledger_integrity()
        if not is_valid:
            raise DataContractError(f"OperationalLedger integrity audit failed on '{self.ledger.path}'.")

        # 2. Empty Genesis Check
        if event_count == 0:
            genesis_portfolio = PortfolioState(
                timestamp_utc=as_of_utc,
                positions={},
                cash_balance=Decimal("100000.00"),
                total_equity=Decimal("100000.00"),
                margin_used=Decimal("0.0"),
                gross_exposure=Decimal("0.0"),
                net_exposure=Decimal("0.0"),
                unrealized_pnl=Decimal("0.0"),
                realized_pnl=Decimal("0.0"),
            )
            genesis_account = AccountState(
                account_id="GENESIS_DEMO_ACCOUNT",
                currency="USD",
                balance=Decimal("100000.00"),
                equity=Decimal("100000.00"),
                free_margin=Decimal("100000.00"),
                margin_level_pct=None,
                leverage=100.0,
                is_live=False,
                timestamp_utc=as_of_utc,
            )
            return genesis_portfolio, genesis_account, RehydrationStatus.EMPTY_GENESIS

        # 3. Read latest committed cycle event
        events = self.ledger.read_all_events()
        latest_event = events[-1]
        expected_digest = latest_event.portfolio_state_digest

        # Check for UNKNOWN execution state requiring authoritative reconciliation (Vector V-13)
        if latest_event.cycle_outcome.value == "UNKNOWN" or "UNKNOWN" in (latest_event.error_message or ""):
            if self.broker_adapter is None:
                raise DataContractError(
                    "CANNOT_REHYDRATE_UNKNOWN_WITHOUT_BROKER: Latest cycle is in UNKNOWN state and requires broker reconciliation."
                )

        # 4. Load Snapshot and Verify Hash (Vector V-07)
        snapshot_path = self.snapshot_dir / "portfolio_state.json"
        if not snapshot_path.exists():
            raise DataContractError(f"Missing portfolio state snapshot file at: {snapshot_path}")

        snapshot = self._snapshot_store.load_snapshot(snapshot_path)
        computed_digest = self._snapshot_store.compute_digest(snapshot)

        if expected_digest and computed_digest != expected_digest:
            raise DataContractError(
                f"SNAPSHOT_DIGEST_MISMATCH: expected digest '{expected_digest}', "
                f"but snapshot compute yielded '{computed_digest}'."
            )

        # Construct candidate recovered account
        recovered_account = AccountState(
            account_id="REHYDRATED_DEMO_ACCOUNT",
            currency="USD",
            balance=snapshot.cash_balance,
            equity=snapshot.total_equity,
            free_margin=snapshot.cash_balance,
            margin_level_pct=None,
            leverage=100.0,
            is_live=False,
            timestamp_utc=as_of_utc,
        )

        # 5. Broker Reconciliation Check if adapter provided (Vectors V-09, V-16)
        if self.broker_adapter is not None:
            # Check for live broker positions
            get_pos_fn = getattr(self.broker_adapter, "get_open_positions", None)
            if callable(get_pos_fn):
                broker_positions = get_pos_fn()
                # Compare position count and symbols
                if len(broker_positions) != len(snapshot.positions):
                    return snapshot, recovered_account, RehydrationStatus.DISCREPANCY_HALT

                for sym, snap_pos in snapshot.positions.items():
                    if sym not in broker_positions:
                        return snapshot, recovered_account, RehydrationStatus.DISCREPANCY_HALT
                    broker_pos = broker_positions[sym]
                    broker_qty = getattr(broker_pos, "quantity", None) or getattr(broker_pos, "volume", None)
                    if broker_qty is not None and Decimal(str(broker_qty)) != snap_pos.quantity:
                        return snapshot, recovered_account, RehydrationStatus.DISCREPANCY_HALT

            # Check for external divergence (Vector V-16)
            divergence_fn = getattr(self.broker_adapter, "check_divergence", None)
            if callable(divergence_fn) and divergence_fn():
                return snapshot, recovered_account, RehydrationStatus.DISCREPANCY_HALT

        return snapshot, recovered_account, RehydrationStatus.CLEAN_RECOVERY
