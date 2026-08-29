"""Order Book Reconstruction Engine interface (Phase 3B)."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple
import pyarrow as pa

from acash.data.orderbook.reconstruction import (
    DepthLadderState,
    MbpOrderBookReconstructor,
    SnapshotShapePolicy,
)


class OrderBookReconstructionEngine:
    """Convenience engine wrapper for reconstructing order book states from snapshots and deltas."""

    def __init__(self, stream_scope: Optional[Tuple[str, str, str, str]] = None) -> None:
        self.stream_scope = stream_scope or ("DEFAULT", "L2", "ES", "2026-01-19")
        self.reconstructor = MbpOrderBookReconstructor(stream_scope=self.stream_scope)

    def process_snapshot(self, snapshot_table: pa.Table) -> DepthLadderState:
        """Process an initial or full snapshot table and return the resulting DepthLadderState."""
        pydict = snapshot_table.to_pydict()
        num_rows = snapshot_table.num_rows

        if num_rows > 0 and "source_id" not in pydict:
            sym = str(pydict["symbol"][0]) if "symbol" in pydict else "ES"
            t0 = pydict["exchange_time_utc"][0] if "exchange_time_utc" in pydict else datetime.now(timezone.utc)
            t_date = t0.strftime("%Y-%m-%d") if hasattr(t0, "strftime") else "2026-01-19"
            self.stream_scope = ("DEFAULT", "L2", sym, t_date)
            self.reconstructor = MbpOrderBookReconstructor(stream_scope=self.stream_scope)

            enhanced_data = dict(pydict)
            enhanced_data["source_id"] = ["DEFAULT"] * num_rows
            enhanced_data["channel_id"] = ["L2"] * num_rows
            enhanced_data["trading_date"] = [t_date] * num_rows
            enhanced_data["snapshot_id"] = [f"SNAP_{i}" for i in range(num_rows)]
            enhanced_data["source_order_key"] = ["0"] * num_rows
            enhanced_data["is_snapshot_complete"] = [True] * num_rows
            enhanced_data["depth_level"] = list(range(num_rows))
            snapshot_table = pa.Table.from_pydict(enhanced_data)

        self.reconstructor.apply_snapshot_frame(snapshot_table, shape_policy=SnapshotShapePolicy.VARIABLE_DEPTH)
        return self.reconstructor.get_ladder_state()
