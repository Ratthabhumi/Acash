"""Deterministic In-Memory Order Book State Reconstruction Engine (Phase 3B).

Strictly enforces:
- MBP (Market By Price - Level 2) vs MBO (Market By Order - Level 3) separation.
- Normalized Resulting Size Semantics:
  - MBP ADD/MODIFY: size is resulting absolute level size.
  - MBP CANCEL: size is resulting remaining level size (if 0, deletes level).
  - MBP DELETE: size = Decimal("0") (deletes level).
  - MBP CLEAR: price=None, size=None, side in {BID, ASK, ALL}.
  - MBO ADD: initial order size with FIFO priority.
  - MBO MODIFY: updated remaining order size (priority reset on price change).
  - MBO CANCEL: updated remaining order size (if 0, purged).
  - MBO DELETE: size = Decimal("0") (purged immediately).
- Strict ReconstructionOrderKey > snapshot_boundary eligibility.
- Contract-Driven Snapshot Completeness validation (FIXED_DEPTH_N, VARIABLE_DEPTH, SOURCE_DECLARED_COMPLETE).
- Granular Crossed Book State Classification (TRANSIENT, AUCTION_OR_HALT, INVALID_RECONSTRUCTION, PERSISTENT).
- STATE_UNORDERABLE rejection.
"""

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
import pyarrow as pa

from acash.data.orderbook.hashing import (
    ReconstructionOrderKey,
    create_delta_order_key,
    create_snapshot_frame_boundary,
)
from acash.data.orderbook.schema import (
    BookAction,
    BookDeltaType,
    BookSide,
    CrossedStateCategory,
    SnapshotShapePolicy,
    SourceOrderingPolicy,
)
from acash.data.schema import IntegrityViolationError

# ---------------------------------------------------------------------------
# State Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PriceLevel:
    """Represents an aggregated price level in the L2 depth ladder."""
    price: Decimal
    size: Decimal
    order_count: Optional[int] = None


@dataclass(frozen=True)
class OrderEntry:
    """Represents a discrete order in the L3 order book."""
    order_id: str
    side: str
    price: Decimal
    size: Decimal
    priority_idx: int


@dataclass
class DepthLadderState:
    """Represents the reconstructed Top-N Order Book depth state at a point in time."""
    stream_scope: Tuple[str, str, str, str]  # (source_id, channel_id, symbol, trading_date)
    exchange_time_utc: datetime
    source_order_key: str
    bids: List[PriceLevel]
    asks: List[PriceLevel]
    is_valid: bool = True
    status: str = "VALID"  # "VALID", "STATE_INVALID_GAP", "STATE_UNORDERABLE", "PARTIAL_SNAPSHOT_REJECTED"
    is_crossed: bool = False
    crossed_category: Optional[CrossedStateCategory] = None
    applied_deltas_count: int = 0


# ---------------------------------------------------------------------------
# MBP Order Book Reconstructor (Level 2)
# ---------------------------------------------------------------------------


class MbpOrderBookReconstructor:
    """Deterministic In-Memory Reconstructor for Level 2 (Market By Price) Order Books."""

    def __init__(
        self,
        stream_scope: Tuple[str, str, str, str],
        ordering_policy: SourceOrderingPolicy = SourceOrderingPolicy.OPAQUE,
        max_transient_crossed_deltas: int = 3,
    ) -> None:
        self.stream_scope = stream_scope
        self.ordering_policy = ordering_policy
        self.max_transient_crossed_deltas = max_transient_crossed_deltas

        # State storage: price -> PriceLevel
        self._bids: Dict[Decimal, PriceLevel] = {}
        self._asks: Dict[Decimal, PriceLevel] = {}

        self._snapshot_boundary: Optional[ReconstructionOrderKey] = None
        self._last_order_key: Optional[ReconstructionOrderKey] = None
        self._latest_exchange_time: Optional[datetime] = None
        self._latest_source_order_key: Optional[str] = None

        self._is_initialized: bool = False
        self._is_valid: bool = False
        self._status: str = "UNINITIALIZED"
        self._applied_deltas_count: int = 0
        self._consecutive_crossed_deltas: int = 0

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    @property
    def status(self) -> str:
        return self._status

    def apply_snapshot_frame(
        self,
        snapshot_table: pa.Table,
        shape_policy: SnapshotShapePolicy = SnapshotShapePolicy.FIXED_DEPTH_N,
        expected_depth_n: Optional[int] = None,
    ) -> bool:
        """Initialize or reset the book state from an atomic complete Snapshot Frame.

        Rejects partial or incomplete frames according to the declared shape_policy.
        """
        if snapshot_table.num_rows == 0:
            self._is_valid = False
            self._status = "PARTIAL_SNAPSHOT_REJECTED"
            return False

        pydict = snapshot_table.to_pydict()
        num_rows = snapshot_table.num_rows

        # 1. Verify Stream Scope
        for i in range(num_rows):
            scope = (
                str(pydict["source_id"][i]),
                str(pydict["channel_id"][i]),
                str(pydict["symbol"][i]),
                str(pydict["trading_date"][i]),
            )
            if scope != self.stream_scope:
                raise IntegrityViolationError(
                    f"Snapshot frame stream scope {scope} does not match reconstructor scope {self.stream_scope}"
                )

        # 2. Verify is_snapshot_complete flag
        if not all(pydict["is_snapshot_complete"]):
            self._is_valid = False
            self._status = "PARTIAL_SNAPSHOT_REJECTED"
            return False

        # 3. Shape policy verification
        bids_in_frame: Dict[int, PriceLevel] = {}
        asks_in_frame: Dict[int, PriceLevel] = {}

        for i in range(num_rows):
            side = str(pydict["side"][i]).upper()
            lvl = int(pydict["level_idx"][i])
            px = pydict["price"][i] if isinstance(pydict["price"][i], Decimal) else Decimal(str(pydict["price"][i]))
            sz = pydict["size"][i] if isinstance(pydict["size"][i], Decimal) else Decimal(str(pydict["size"][i]))
            cnt = pydict["order_count"][i]

            pl = PriceLevel(price=px, size=sz, order_count=cnt)
            if side == "BID":
                bids_in_frame[lvl] = pl
            elif side == "ASK":
                asks_in_frame[lvl] = pl

        if shape_policy == SnapshotShapePolicy.FIXED_DEPTH_N:
            depth_n = expected_depth_n or max(len(bids_in_frame), len(asks_in_frame), 1)
            # Verify continuous 0..N-1 levels
            bid_levels = set(bids_in_frame.keys())
            ask_levels = set(asks_in_frame.keys())
            expected_set = set(range(depth_n))
            if not (expected_set.issubset(bid_levels) and expected_set.issubset(ask_levels)):
                self._is_valid = False
                self._status = "PARTIAL_SNAPSHOT_REJECTED"
                return False

        # 4. Clear existing state & populate from snapshot
        self._bids.clear()
        self._asks.clear()

        for pl in bids_in_frame.values():
            if pl.size > Decimal("0"):
                self._bids[pl.price] = pl

        for pl in asks_in_frame.values():
            if pl.size > Decimal("0"):
                self._asks[pl.price] = pl

        # 5. Set Snapshot Boundary Anchor
        first_t = pydict["exchange_time_utc"][0]
        first_order_key = str(pydict["source_order_key"][0])
        self._latest_exchange_time = first_t
        self._latest_source_order_key = first_order_key

        self._snapshot_boundary = create_snapshot_frame_boundary(
            exchange_time_utc=first_t,
            source_order_key=first_order_key,
        )
        self._last_order_key = self._snapshot_boundary

        self._is_initialized = True
        self._is_valid = True
        self._status = "VALID"
        self._applied_deltas_count = 0
        self._consecutive_crossed_deltas = 0
        return True

    def apply_delta(
        self,
        exchange_time_utc: datetime,
        source_order_key: str,
        action_sub_idx: int,
        action: str,
        side: str,
        price: Optional[Decimal] = None,
        size: Optional[Decimal] = None,
        order_count: Optional[int] = None,
        is_auction_session: bool = False,
    ) -> bool:
        """Apply an incremental MBP delta to the reconstructed state.

        Strictly enforces delta.ReconstructionOrder > snapshot.SnapshotBoundary.
        """
        if not self._is_initialized or not self._is_valid or self._snapshot_boundary is None:
            return False

        # 1. Compute delta order key and verify strict eligibility
        delta_key = create_delta_order_key(
            exchange_time_utc=exchange_time_utc,
            source_order_key=source_order_key,
            action_sub_idx=action_sub_idx,
        )

        if delta_key <= self._snapshot_boundary:
            # Delta precedes or is part of the snapshot frame anchor; ignore to avoid double application
            return False

        if self._last_order_key is not None and delta_key < self._last_order_key:
            # Out-of-order delta arrival
            if self.ordering_policy == SourceOrderingPolicy.OPAQUE:
                # Disallow unorderable mutations
                self._is_valid = False
                self._status = "STATE_UNORDERABLE"
                return False

        self._last_order_key = delta_key
        self._latest_exchange_time = exchange_time_utc
        self._latest_source_order_key = source_order_key

        action_norm = action.upper()
        side_norm = side.upper()

        # 2. Execute Normalized Action Mechanics
        if action_norm == BookAction.CLEAR:
            if side_norm == "BID":
                self._bids.clear()
            elif side_norm == "ASK":
                self._asks.clear()
            elif side_norm == "ALL":
                self._bids.clear()
                self._asks.clear()

        elif action_norm == BookAction.ADD:
            if price is None or size is None or size <= Decimal("0"):
                return False
            pl = PriceLevel(price=price, size=size, order_count=order_count)
            if side_norm == "BID":
                self._bids[price] = pl
            elif side_norm == "ASK":
                self._asks[price] = pl

        elif action_norm == BookAction.MODIFY:
            if price is None or size is None:
                return False
            if size <= Decimal("0"):
                # Size reduced to 0 -> remove level
                if side_norm == "BID":
                    self._bids.pop(price, None)
                elif side_norm == "ASK":
                    self._asks.pop(price, None)
            else:
                pl = PriceLevel(price=price, size=size, order_count=order_count)
                if side_norm == "BID":
                    self._bids[price] = pl
                elif side_norm == "ASK":
                    self._asks[price] = pl

        elif action_norm == BookAction.CANCEL:
            if price is None:
                return False
            rem_size = size if size is not None else Decimal("0")
            if rem_size <= Decimal("0"):
                if side_norm == "BID":
                    self._bids.pop(price, None)
                elif side_norm == "ASK":
                    self._asks.pop(price, None)
            else:
                pl = PriceLevel(price=price, size=rem_size, order_count=order_count)
                if side_norm == "BID":
                    self._bids[price] = pl
                elif side_norm == "ASK":
                    self._asks[price] = pl

        elif action_norm == BookAction.DELETE:
            if price is not None:
                if side_norm == "BID":
                    self._bids.pop(price, None)
                elif side_norm == "ASK":
                    self._asks.pop(price, None)

        self._applied_deltas_count += 1
        return True

    def get_ladder_state(self, top_n: int = 10, is_auction_session: bool = False) -> DepthLadderState:
        """Emit the current Top-N reconstructed Depth Ladder state."""
        # Sort Bids descending
        sorted_bids = [
            self._bids[px] for px in sorted(self._bids.keys(), reverse=True)
        ][:top_n]

        # Sort Asks ascending
        sorted_asks = [
            self._asks[px] for px in sorted(self._asks.keys())
        ][:top_n]

        # Check crossed state
        is_crossed = False
        crossed_cat: Optional[CrossedStateCategory] = None

        if sorted_bids and sorted_asks:
            top_bid = sorted_bids[0].price
            top_ask = sorted_asks[0].price
            if top_bid >= top_ask:
                is_crossed = True
                self._consecutive_crossed_deltas += 1

                if is_auction_session:
                    crossed_cat = CrossedStateCategory.CROSSED_AUCTION_OR_HALT
                elif self._consecutive_crossed_deltas <= self.max_transient_crossed_deltas:
                    crossed_cat = CrossedStateCategory.CROSSED_TRANSIENT
                else:
                    crossed_cat = CrossedStateCategory.CROSSED_PERSISTENT_ANOMALY
            else:
                self._consecutive_crossed_deltas = 0
        else:
            self._consecutive_crossed_deltas = 0

        t = self._latest_exchange_time or datetime(1970, 1, 1, tzinfo=timezone.utc)
        k = self._latest_source_order_key or ""

        return DepthLadderState(
            stream_scope=self.stream_scope,
            exchange_time_utc=t,
            source_order_key=k,
            bids=sorted_bids,
            asks=sorted_asks,
            is_valid=self._is_valid,
            status=self._status,
            is_crossed=is_crossed,
            crossed_category=crossed_cat,
            applied_deltas_count=self._applied_deltas_count,
        )


# ---------------------------------------------------------------------------
# MBO Order Book Reconstructor (Level 3)
# ---------------------------------------------------------------------------


class MboOrderBookReconstructor:
    """Deterministic In-Memory Reconstructor for Level 3 (Market By Order) Discrete Order Queues."""

    def __init__(
        self,
        stream_scope: Tuple[str, str, str, str],
        ordering_policy: SourceOrderingPolicy = SourceOrderingPolicy.OPAQUE,
    ) -> None:
        self.stream_scope = stream_scope
        self.ordering_policy = ordering_policy

        # Order storage: order_id -> OrderEntry
        self._orders: Dict[str, OrderEntry] = {}
        self._priority_counter: int = 0

        self._last_order_key: Optional[ReconstructionOrderKey] = None
        self._latest_exchange_time: Optional[datetime] = None
        self._latest_source_order_key: Optional[str] = None

        self._is_initialized: bool = True
        self._is_valid: bool = True
        self._status: str = "VALID"
        self._applied_deltas_count: int = 0

    def apply_delta(
        self,
        exchange_time_utc: datetime,
        source_order_key: str,
        action_sub_idx: int,
        action: str,
        side: str,
        order_id: str,
        price: Optional[Decimal] = None,
        size: Optional[Decimal] = None,
    ) -> bool:
        """Apply an incremental MBO discrete order delta."""
        if not order_id:
            raise IntegrityViolationError("MBO delta requires non-empty order_id")

        delta_key = create_delta_order_key(
            exchange_time_utc=exchange_time_utc,
            source_order_key=source_order_key,
            action_sub_idx=action_sub_idx,
        )

        if self._last_order_key is not None and delta_key < self._last_order_key:
            if self.ordering_policy == SourceOrderingPolicy.OPAQUE:
                self._is_valid = False
                self._status = "STATE_UNORDERABLE"
                return False

        self._last_order_key = delta_key
        self._latest_exchange_time = exchange_time_utc
        self._latest_source_order_key = source_order_key

        action_norm = action.upper()
        side_norm = side.upper()

        if action_norm == BookAction.ADD:
            if price is None or size is None or size <= Decimal("0"):
                return False
            self._priority_counter += 1
            self._orders[order_id] = OrderEntry(
                order_id=order_id,
                side=side_norm,
                price=price,
                size=size,
                priority_idx=self._priority_counter,
            )

        elif action_norm == BookAction.MODIFY:
            if order_id not in self._orders or size is None:
                return False
            existing = self._orders[order_id]
            if size <= Decimal("0"):
                self._orders.pop(order_id, None)
            else:
                new_price = price if price is not None else existing.price
                # If price changed, priority resets (loses queue position)
                if new_price != existing.price:
                    self._priority_counter += 1
                    p_idx = self._priority_counter
                else:
                    p_idx = existing.priority_idx

                self._orders[order_id] = OrderEntry(
                    order_id=order_id,
                    side=existing.side,
                    price=new_price,
                    size=size,
                    priority_idx=p_idx,
                )

        elif action_norm == BookAction.CANCEL:
            if order_id in self._orders:
                rem_size = size if size is not None else Decimal("0")
                if rem_size <= Decimal("0"):
                    self._orders.pop(order_id, None)
                else:
                    existing = self._orders[order_id]
                    self._orders[order_id] = OrderEntry(
                        order_id=order_id,
                        side=existing.side,
                        price=existing.price,
                        size=rem_size,
                        priority_idx=existing.priority_idx,
                    )

        elif action_norm == BookAction.DELETE:
            self._orders.pop(order_id, None)

        self._applied_deltas_count += 1
        return True

    def get_ladder_state(self, top_n: int = 10) -> DepthLadderState:
        """Aggregate active discrete orders into price levels and project the canonical Top-N L2 view."""
        bid_agg: Dict[Decimal, Tuple[Decimal, int]] = {}  # price -> (total_size, order_count)
        ask_agg: Dict[Decimal, Tuple[Decimal, int]] = {}

        for order in self._orders.values():
            if order.side == "BID":
                tot_sz, cnt = bid_agg.get(order.price, (Decimal("0"), 0))
                bid_agg[order.price] = (tot_sz + order.size, cnt + 1)
            elif order.side == "ASK":
                tot_sz, cnt = ask_agg.get(order.price, (Decimal("0"), 0))
                ask_agg[order.price] = (tot_sz + order.size, cnt + 1)

        sorted_bids = [
            PriceLevel(price=px, size=tot_sz, order_count=cnt)
            for px, (tot_sz, cnt) in sorted(bid_agg.items(), key=lambda x: x[0], reverse=True)
        ][:top_n]

        sorted_asks = [
            PriceLevel(price=px, size=tot_sz, order_count=cnt)
            for px, (tot_sz, cnt) in sorted(ask_agg.items(), key=lambda x: x[0])
        ][:top_n]

        t = self._latest_exchange_time or datetime(1970, 1, 1, tzinfo=timezone.utc)
        k = self._latest_source_order_key or ""

        return DepthLadderState(
            stream_scope=self.stream_scope,
            exchange_time_utc=t,
            source_order_key=k,
            bids=sorted_bids,
            asks=sorted_asks,
            is_valid=self._is_valid,
            status=self._status,
            applied_deltas_count=self._applied_deltas_count,
        )
