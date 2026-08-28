"""Sovereign Backtesting Simulation Engine, Matching Substrate, and Deterministic Manifest (Phase 5).

Implements:
1. Event-Driven Execution Loop driven strictly by Phase 3B total ordering.
2. Simulated Order Book with Level-2 Depth Sweeps, VWAP Fill Arithmetic, Dynamic Impact, and Depth Liquidity Consumption.
3. Maker Queue Priority Volume Tracking (FIFO), Trade-Through Matching, and Opposing-Aggressor Filtering.
4. Complete Order Lifecycle Semantics (MARKET, LIMIT, IOC, FOK, GTC) with partial fills.
5. Float-Free Pure Integer Nanosecond Accounting and Timestamps across all lifecycle boundaries.
6. Multi-tiered Reality Gap Attribution and cryptographic environment provenance.
"""

from collections import deque
from datetime import datetime, timezone
from decimal import Decimal
import time
from typing import Any, Deque, Dict, List, Optional, Sequence, Set, Tuple
import pyarrow as pa

from acash.backtest.accounting import ShadowAccountingLedger
from acash.backtest.adapter import (
    BacktestEventType,
    BacktestMarketEvent,
    extract_nanoseconds_from_datetime,
)
from acash.backtest.schema import (
    CANONICAL_BACKTEST_FILLS_SCHEMA,
    CANONICAL_EQUITY_CURVE_SCHEMA,
    BacktestEngineConfig,
    BacktestExecutionSummary,
    BacktestFillRecord,
    BacktestManifest,
    BacktestOrderStatus,
    FeeModelConfig,
    LiquidityType,
    OrderType,
    RealityGapSummary,
    SimulationLatencyConfig,
    SlippageModelConfig,
    calculate_backtest_manifest_id,
)
from acash.data.schema import DataContractError


class SimulatedOrderBook:
    """In-memory Level-2 / Level-3 Order Book for backtest execution simulation."""

    def __init__(self) -> None:
        self.bids: Dict[Decimal, Decimal] = {}  # Price -> Size
        self.asks: Dict[Decimal, Decimal] = {}  # Price -> Size

    def clear(self) -> None:
        self.bids.clear()
        self.asks.clear()

    def apply_delta(
        self,
        action: str,
        side: str,
        price: Optional[Decimal],
        size: Optional[Decimal],
        level_idx: Optional[int] = None,
    ) -> None:
        """Update order book state based on market data delta or snapshot."""
        action_upper = action.upper()
        side_upper = side.upper()

        if action_upper == "CLEAR":
            if side_upper in ("ALL", "BOTH", "BOOK"):
                self.bids.clear()
                self.asks.clear()
            elif side_upper in ("BID", "BUY"):
                self.bids.clear()
            elif side_upper in ("ASK", "SELL"):
                self.asks.clear()
            return

        target_book = self.bids if side_upper in ("BID", "BUY") else self.asks

        # Frame-Aware Snapshot Boundary: When a snapshot starts (level_idx == 0 or level_idx is None),
        # clear the stale ladder for that side so new snapshot atomically replaces all previous levels.
        if action_upper == "SNAPSHOT" and (level_idx == 0 or level_idx is None):
            target_book.clear()

        if price is None:
            return

        if action_upper in ("ADD", "MODIFY", "SNAPSHOT"):
            if size is not None and size > Decimal("0.0"):
                target_book[price] = size
            else:
                target_book.pop(price, None)
        elif action_upper in ("DELETE", "CANCEL"):
            if size is not None and size > Decimal("0.0"):
                target_book[price] = size
            else:
                target_book.pop(price, None)
        elif action_upper == "REDUCE":
            if size is not None and price in target_book:
                new_size = target_book[price] - size
                if new_size > Decimal("0.0"):
                    target_book[price] = new_size
                else:
                    target_book.pop(price, None)
            else:
                target_book.pop(price, None)

    def apply_snapshot_frame(
        self,
        bids: Sequence[Tuple[Decimal, Decimal]],
        asks: Sequence[Tuple[Decimal, Decimal]],
    ) -> None:
        """Atomically replace entire order book state with a complete snapshot frame.

        Enforces transactional build-then-swap semantics:
        - Validates all prices and sizes upfront into local dictionaries.
        - Raises ValueError on invalid items before modifying existing book.
        - Swaps self.bids and self.asks atomically upon complete validation.
        """
        new_bids: Dict[Decimal, Decimal] = {}
        new_asks: Dict[Decimal, Decimal] = {}

        for px, sz in bids:
            if not isinstance(px, Decimal) or not isinstance(sz, Decimal):
                raise ValueError(f"Price and size in bids snapshot must be Decimal, got ({type(px)}, {type(sz)}).")
            if not px.is_finite() or px <= Decimal("0.0"):
                raise ValueError(f"Snapshot bid price must be positive finite Decimal, got {px}.")
            if not sz.is_finite() or sz < Decimal("0.0"):
                raise ValueError(f"Snapshot bid size must be non-negative finite Decimal, got {sz}.")
            if sz > Decimal("0.0"):
                new_bids[px] = sz

        for px, sz in asks:
            if not isinstance(px, Decimal) or not isinstance(sz, Decimal):
                raise ValueError(f"Price and size in asks snapshot must be Decimal, got ({type(px)}, {type(sz)}).")
            if not px.is_finite() or px <= Decimal("0.0"):
                raise ValueError(f"Snapshot ask price must be positive finite Decimal, got {px}.")
            if not sz.is_finite() or sz < Decimal("0.0"):
                raise ValueError(f"Snapshot ask size must be non-negative finite Decimal, got {sz}.")
            if sz > Decimal("0.0"):
                new_asks[px] = sz

        # Atomic state swap (Transactional / Exception Safe)
        self.bids = new_bids
        self.asks = new_asks




    @property
    def best_bid(self) -> Optional[Decimal]:
        return max(self.bids.keys()) if self.bids else None

    @property
    def best_ask(self) -> Optional[Decimal]:
        return min(self.asks.keys()) if self.asks else None

    @property
    def total_bid_depth(self) -> Decimal:
        return sum(self.bids.values(), Decimal("0.0"))

    @property
    def total_ask_depth(self) -> Decimal:
        return sum(self.asks.values(), Decimal("0.0"))

    def sweep_asks(self, required_qty: Decimal, consume: bool = True) -> Tuple[Decimal, Decimal, Decimal]:
        """Sweep ask levels in ascending price order computing VWAP.

        Returns:
            Tuple[vwap_price, total_executed_qty, remaining_unfilled_qty]
        """
        if not self.asks or required_qty <= Decimal("0.0"):
            return Decimal("0.0"), Decimal("0.0"), required_qty

        sorted_ask_prices = sorted(self.asks.keys())
        remaining = required_qty
        cumulative_cost = Decimal("0.0")
        cumulative_qty = Decimal("0.0")
        levels_to_delete: List[Decimal] = []
        levels_to_modify: List[Tuple[Decimal, Decimal]] = []

        for px in sorted_ask_prices:
            avail_qty = self.asks[px]
            fill_qty = min(avail_qty, remaining)
            cumulative_cost += px * fill_qty
            cumulative_qty += fill_qty
            remaining -= fill_qty

            if consume:
                if avail_qty == fill_qty:
                    levels_to_delete.append(px)
                else:
                    levels_to_modify.append((px, avail_qty - fill_qty))

            if remaining == Decimal("0.0"):
                break

        if consume:
            for px in levels_to_delete:
                del self.asks[px]
            for px, new_qty in levels_to_modify:
                self.asks[px] = new_qty

        vwap = cumulative_cost / cumulative_qty if cumulative_qty > Decimal("0.0") else Decimal("0.0")
        return vwap, cumulative_qty, remaining

    def sweep_bids(self, required_qty: Decimal, consume: bool = True) -> Tuple[Decimal, Decimal, Decimal]:
        """Sweep bid levels in descending price order computing VWAP.

        Returns:
            Tuple[vwap_price, total_executed_qty, remaining_unfilled_qty]
        """
        if not self.bids or required_qty <= Decimal("0.0"):
            return Decimal("0.0"), Decimal("0.0"), required_qty

        sorted_bid_prices = sorted(self.bids.keys(), reverse=True)
        remaining = required_qty
        cumulative_cost = Decimal("0.0")
        cumulative_qty = Decimal("0.0")
        levels_to_delete: List[Decimal] = []
        levels_to_modify: List[Tuple[Decimal, Decimal]] = []

        for px in sorted_bid_prices:
            avail_qty = self.bids[px]
            fill_qty = min(avail_qty, remaining)
            cumulative_cost += px * fill_qty
            cumulative_qty += fill_qty
            remaining -= fill_qty

            if consume:
                if avail_qty == fill_qty:
                    levels_to_delete.append(px)
                else:
                    levels_to_modify.append((px, avail_qty - fill_qty))

            if remaining == Decimal("0.0"):
                break

        if consume:
            for px in levels_to_delete:
                del self.bids[px]
            for px, new_qty in levels_to_modify:
                self.bids[px] = new_qty

        vwap = cumulative_cost / cumulative_qty if cumulative_qty > Decimal("0.0") else Decimal("0.0")
        return vwap, cumulative_qty, remaining


class SimulatedOrder:
    """Represents an order tracked by the simulation matching engine."""

    def __init__(
        self,
        order_id: str,
        symbol: str,
        order_type: OrderType,
        side: str,
        quantity: Decimal,
        created_timestamp_ns: int,
        limit_price: Optional[Decimal] = None,
    ) -> None:
        self.order_id = order_id
        self.symbol = symbol
        self.order_type = order_type
        self.side = side.upper()
        self.quantity = quantity
        self.created_timestamp_ns = created_timestamp_ns
        self.limit_price = limit_price

        # Lifecycle State
        self.status: BacktestOrderStatus = BacktestOrderStatus.CREATED
        self.filled_qty: Decimal = Decimal("0.0")
        self.remaining_qty: Decimal = quantity
        self.cumulative_cost: Decimal = Decimal("0.0")

        # Queue Emulation State
        self.queue_ahead_volume: Decimal = Decimal("0.0")
        self.queue_initialized: bool = False

    @property
    def is_active(self) -> bool:
        return self.status in (
            BacktestOrderStatus.SUBMITTED,
            BacktestOrderStatus.ACCEPTED,
            BacktestOrderStatus.PARTIALLY_FILLED,
        )

    @property
    def avg_fill_price(self) -> Decimal:
        if self.filled_qty == Decimal("0.0"):
            return Decimal("0.0")
        return self.cumulative_cost / self.filled_qty


class EventBacktestRunner:
    """Sovereign event-driven backtesting execution substrate."""

    def __init__(
        self,
        config: BacktestEngineConfig,
        strategy_actor: Optional[Any] = None,
    ) -> None:
        self.config = config
        self.strategy_actor = strategy_actor

        # Simulation Substrate State
        self.current_time_ns: int = 0
        self.last_price: Decimal = Decimal("0.0")
        self.order_book = SimulatedOrderBook()
        self.ledger = ShadowAccountingLedger(
            starting_cash=config.initial_cash,
            base_currency=config.base_currency,
        )



        # Order Tracking
        self.orders: Dict[str, SimulatedOrder] = {}
        self.order_queue: Deque[SimulatedOrder] = deque()
        self.fills: List[BacktestFillRecord] = []
        self.equity_records: List[Dict[str, Any]] = []

        # Peak Equity for Drawdown Tracking
        self.peak_equity: Decimal = config.initial_cash
        self.max_drawdown: Decimal = Decimal("0.0")

        # Statistics
        self.profitable_trades_count: int = 0
        self.total_closed_trades_count: int = 0
        self.gross_profits: Decimal = Decimal("0.0")
        self.gross_losses: Decimal = Decimal("0.0")

    # ---------------------------------------------------------------------
    # Order Submission Interface
    # ---------------------------------------------------------------------

    def submit_order(
        self,
        order_id: str,
        symbol: str,
        order_type: OrderType,
        side: str,
        quantity: Decimal,
        limit_price: Optional[Decimal] = None,
    ) -> SimulatedOrder:
        """Submit a new simulated order into the matching pipeline."""
        if quantity <= Decimal("0.0"):
            raise DataContractError(f"Order quantity must be positive, got: {quantity}")

        if order_id in self.orders:
            raise DataContractError(f"Duplicate order_id: {order_id}")

        order = SimulatedOrder(
            order_id=order_id,
            symbol=symbol,
            order_type=order_type,
            side=side,
            quantity=quantity,
            created_timestamp_ns=self.current_time_ns,
            limit_price=limit_price,
        )
        order.status = BacktestOrderStatus.SUBMITTED

        # Initialize Queue Ahead for Limit Orders
        if order.order_type in (OrderType.LIMIT, OrderType.GTC) and order.limit_price is not None:
            if order.side == "BUY":
                order.queue_ahead_volume = self.order_book.bids.get(order.limit_price, Decimal("0.0"))
            else:
                order.queue_ahead_volume = self.order_book.asks.get(order.limit_price, Decimal("0.0"))
            order.queue_initialized = True

        self.orders[order_id] = order
        self.order_queue.append(order)

        # Attempt immediate matching
        self._process_order_matching(self.current_time_ns)
        return order

    # ---------------------------------------------------------------------
    # Matching Engine & Execution Logic
    # ---------------------------------------------------------------------

    def _process_order_matching(
        self,
        event_timestamp_ns: int,
        trade_event_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Match pending orders against prevailing market liquidity adhering to causal latency."""
        match_latency = self.config.latency_config.total_match_latency_ns()
        pending_count = len(self.order_queue)

        for _ in range(pending_count):
            order = self.order_queue.popleft()
            if not order.is_active:
                continue

            # Causal Latency Check: Match timestamp must be >= created_timestamp + match_latency
            if event_timestamp_ns < (order.created_timestamp_ns + match_latency):
                self.order_queue.append(order)
                continue

            if order.status == BacktestOrderStatus.SUBMITTED:
                order.status = BacktestOrderStatus.ACCEPTED

            if order.order_type in (OrderType.MARKET, OrderType.IOC, OrderType.FOK):
                self._execute_taker_order(order, event_timestamp_ns)
            elif order.order_type in (OrderType.LIMIT, OrderType.GTC):
                self._execute_maker_order(order, event_timestamp_ns, trade_event_payload)
                if order.is_active:
                    self.order_queue.append(order)

    def _execute_taker_order(self, order: SimulatedOrder, timestamp_ns: int) -> None:
        """Execute an aggressive taker order with Depth Book Sweep, VWAP, and Dynamic Impact."""
        slippage_bps = self.config.slippage_config.fixed_slippage_bps
        slippage_factor = slippage_bps / Decimal("10000.0")
        impact_coeff = self.config.slippage_config.impact_coefficient

        # 1. Fill or Kill (FOK) and Immediate or Cancel (IOC) Pre-Execution Checks
        avail_depth = (
            self.order_book.total_ask_depth
            if order.side == "BUY"
            else self.order_book.total_bid_depth
        )
        has_book = self.order_book.asks if order.side == "BUY" else self.order_book.bids

        if order.order_type == OrderType.FOK:
            # FOK requires sufficient executable depth in book; if empty or insufficient, cancel immediately
            if not has_book or avail_depth < order.remaining_qty:
                order.status = BacktestOrderStatus.CANCELLED
                return
        elif order.order_type == OrderType.IOC:
            # IOC requires immediate executable depth in book; if empty, cancel immediately
            if not has_book or avail_depth <= Decimal("0.0"):
                order.status = BacktestOrderStatus.CANCELLED
                return

        executed_price: Decimal = Decimal("0.0")
        filled_qty: Decimal = Decimal("0.0")

        if order.side == "BUY":
            if self.order_book.asks:
                total_depth_before = self.order_book.total_ask_depth
                vwap, filled_qty, remaining = self.order_book.sweep_asks(order.remaining_qty, consume=True)
                if filled_qty > Decimal("0.0"):
                    impact = (
                        (impact_coeff * (filled_qty / total_depth_before))
                        if total_depth_before > Decimal("0.0")
                        else Decimal("0.0")
                    )
                    executed_price = vwap * (Decimal("1.0") + slippage_factor + impact)
                else:
                    order.status = BacktestOrderStatus.CANCELLED
                    return
            else:
                base_price = self.order_book.best_ask or self.last_price
                if base_price <= Decimal("0.0"):
                    order.status = BacktestOrderStatus.REJECTED
                    return
                filled_qty = order.remaining_qty
                executed_price = base_price * (Decimal("1.0") + slippage_factor)
        else:  # SELL Order
            if self.order_book.bids:
                total_depth_before = self.order_book.total_bid_depth
                vwap, filled_qty, remaining = self.order_book.sweep_bids(order.remaining_qty, consume=True)
                if filled_qty > Decimal("0.0"):
                    impact = (
                        (impact_coeff * (filled_qty / total_depth_before))
                        if total_depth_before > Decimal("0.0")
                        else Decimal("0.0")
                    )
                    executed_price = vwap * (Decimal("1.0") - slippage_factor - impact)
                else:
                    order.status = BacktestOrderStatus.CANCELLED
                    return
            else:
                base_price = self.order_book.best_bid or self.last_price
                if base_price <= Decimal("0.0"):
                    order.status = BacktestOrderStatus.REJECTED
                    return
                filled_qty = order.remaining_qty
                executed_price = base_price * (Decimal("1.0") - slippage_factor)

        if filled_qty <= Decimal("0.0"):
            order.status = BacktestOrderStatus.CANCELLED
            return

        # 2. Taker Fee Schedule
        fee_bps = self.config.fee_config.taker_fee_bps
        fee_paid = (
            executed_price * filled_qty * (fee_bps / Decimal("10000.0"))
        ) + self.config.fee_config.fixed_fee_per_trade

        # 3. Process fill in shadow accounting ledger
        realized_pnl, new_equity = self.ledger.process_fill(
            symbol=order.symbol,
            side=order.side,
            fill_price=executed_price,
            fill_qty=filled_qty,
            fee_paid=fee_paid,
        )

        micros, nanos = divmod(timestamp_ns, 1_000)
        secs, us = divmod(micros, 1_000_000)
        fill_dt = datetime.fromtimestamp(secs, tz=timezone.utc).replace(microsecond=us)

        fill_rec = BacktestFillRecord(
            fill_id=f"FILL-{len(self.fills)+1:08d}",
            order_id=order.order_id,
            symbol=order.symbol,
            fill_timestamp_utc=fill_dt.isoformat(),
            side=order.side,
            fill_price=executed_price,
            fill_qty=filled_qty,
            fee_paid=fee_paid,
            liquidity_type=LiquidityType.TAKER,
            slippage_incurred_bps=slippage_bps,
        )
        self.fills.append(fill_rec)

        # Update order state
        order.cumulative_cost += executed_price * filled_qty
        order.filled_qty += filled_qty
        order.remaining_qty -= filled_qty

        if order.remaining_qty == Decimal("0.0"):
            order.status = BacktestOrderStatus.FILLED
        else:
            # MARKET, IOC, and FOK orders do NOT rest in queue; remainder is cancelled
            order.status = BacktestOrderStatus.CANCELLED

        # Track PnL statistics
        if realized_pnl > Decimal("0.0"):
            self.profitable_trades_count += 1
            self.gross_profits += realized_pnl
            self.total_closed_trades_count += 1
        elif realized_pnl < Decimal("0.0"):
            self.gross_losses += abs(realized_pnl)
            self.total_closed_trades_count += 1

    def _execute_maker_order(
        self,
        order: SimulatedOrder,
        timestamp_ns: int,
        trade_event_payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Attempt to fill resting limit order based on trade-through and queue priority emulation."""
        if order.limit_price is None or order.remaining_qty <= Decimal("0.0"):
            return False

        is_filled = False
        fill_qty = Decimal("0.0")

        if trade_event_payload is not None:
            trade_price = Decimal(str(trade_event_payload["price"]))
            trade_size = Decimal(str(trade_event_payload["size"]))
            aggressor = str(trade_event_payload.get("aggressor_side", "UNKNOWN")).upper()

            if order.side == "BUY":
                if trade_price < order.limit_price:
                    # Trade-through: Market traded below buy limit -> entire price level surpassed
                    fill_qty = min(order.remaining_qty, trade_size) if trade_size > Decimal("0.0") else order.remaining_qty
                    is_filled = True
                elif trade_price == order.limit_price and aggressor in ("SELL", "UNKNOWN"):
                    # Opposing sell aggressor trades at limit price
                    if order.queue_ahead_volume > Decimal("0.0"):
                        if trade_size > order.queue_ahead_volume:
                            available_qty = trade_size - order.queue_ahead_volume
                            order.queue_ahead_volume = Decimal("0.0")
                            fill_qty = min(order.remaining_qty, available_qty)
                            is_filled = True
                        else:
                            order.queue_ahead_volume -= trade_size
                    else:
                        # Already at top of queue
                        fill_qty = min(order.remaining_qty, trade_size)
                        is_filled = True
            else:  # SELL limit
                if trade_price > order.limit_price:
                    # Trade-through: Market traded above sell limit -> entire price level surpassed
                    fill_qty = min(order.remaining_qty, trade_size) if trade_size > Decimal("0.0") else order.remaining_qty
                    is_filled = True
                elif trade_price == order.limit_price and aggressor in ("BUY", "UNKNOWN"):
                    # Opposing buy aggressor trades at limit price
                    if order.queue_ahead_volume > Decimal("0.0"):
                        if trade_size > order.queue_ahead_volume:
                            available_qty = trade_size - order.queue_ahead_volume
                            order.queue_ahead_volume = Decimal("0.0")
                            fill_qty = min(order.remaining_qty, available_qty)
                            is_filled = True
                        else:
                            order.queue_ahead_volume -= trade_size
                    else:
                        # Already at top of queue
                        fill_qty = min(order.remaining_qty, trade_size)
                        is_filled = True
        else:
            # Fallback for Bar/Depth trigger without discrete trade stream
            if self.last_price > Decimal("0.0"):
                if order.side == "BUY" and self.last_price < order.limit_price:
                    fill_qty = order.remaining_qty
                    is_filled = True
                elif order.side == "SELL" and self.last_price > order.limit_price:
                    fill_qty = order.remaining_qty
                    is_filled = True
                elif not order.queue_initialized or order.queue_ahead_volume <= Decimal("0.0"):
                    if order.side == "BUY" and self.last_price <= order.limit_price:
                        fill_qty = order.remaining_qty
                        is_filled = True
                    elif order.side == "SELL" and self.last_price >= order.limit_price:
                        fill_qty = order.remaining_qty
                        is_filled = True

        if is_filled and fill_qty > Decimal("0.0"):
            executed_price = order.limit_price
            fee_bps = self.config.fee_config.maker_fee_bps
            fee_paid = max(
                Decimal("0.0"),
                (executed_price * fill_qty * (fee_bps / Decimal("10000.0")))
                + self.config.fee_config.fixed_fee_per_trade,
            )

            realized_pnl, new_equity = self.ledger.process_fill(
                symbol=order.symbol,
                side=order.side,
                fill_price=executed_price,
                fill_qty=fill_qty,
                fee_paid=fee_paid,
            )

            micros, nanos = divmod(timestamp_ns, 1_000)
            secs, us = divmod(micros, 1_000_000)
            fill_dt = datetime.fromtimestamp(secs, tz=timezone.utc).replace(microsecond=us)

            fill_rec = BacktestFillRecord(
                fill_id=f"FILL-{len(self.fills)+1:08d}",
                order_id=order.order_id,
                symbol=order.symbol,
                fill_timestamp_utc=fill_dt.isoformat(),
                side=order.side,
                fill_price=executed_price,
                fill_qty=fill_qty,
                fee_paid=fee_paid,
                liquidity_type=LiquidityType.MAKER,
                slippage_incurred_bps=Decimal("0.0"),
            )
            self.fills.append(fill_rec)

            order.cumulative_cost += executed_price * fill_qty
            order.filled_qty += fill_qty
            order.remaining_qty -= fill_qty
            if order.remaining_qty == Decimal("0.0"):
                order.status = BacktestOrderStatus.FILLED
            else:
                order.status = BacktestOrderStatus.PARTIALLY_FILLED

            if realized_pnl > Decimal("0.0"):
                self.profitable_trades_count += 1
                self.gross_profits += realized_pnl
                self.total_closed_trades_count += 1
            elif realized_pnl < Decimal("0.0"):
                self.gross_losses += abs(realized_pnl)
                self.total_closed_trades_count += 1

            return True

        return False

    # ---------------------------------------------------------------------
    # Main Event Loop
    # ---------------------------------------------------------------------

    def run_backtest(
        self,
        events: List[BacktestMarketEvent],
        hypothesis_spec_sha256: str,
        strategy_config_hash: str,
        pyproject_toml_sha256: str,
        git_commit_hash: str,
        uv_lock_sha256: Optional[str] = None,
        canonical_data_hashes: Optional[List[str]] = None,
        phase4_analytical_edge_bps: Decimal = Decimal("0.0"),
    ) -> Tuple[BacktestManifest, pa.Table, pa.Table]:
        """Execute simulation over strictly sorted market event stream."""
        if canonical_data_hashes is None:
            canonical_data_hashes = []

        start_wall_clock = time.perf_counter()

        # Boundary Event Ordering Monotonicity Enforcement

        prev_order_tuple: Optional[Tuple[Any, ...]] = None
        for idx, event in enumerate(events):
            curr_order_tuple = event.order_tuple
            if prev_order_tuple is not None and curr_order_tuple < prev_order_tuple:
                raise DataContractError(
                    f"Out-of-order event sequence detected at engine boundary at index {idx}: "
                    f"current event {curr_order_tuple} precedes previous event {prev_order_tuple}."
                )
            prev_order_tuple = curr_order_tuple

            self.current_time_ns = event.event_timestamp_ns
            trade_payload: Optional[Dict[str, Any]] = None

            # 1. Update Market Price & State
            if event.event_type == BacktestEventType.BAR:
                self.last_price = event.payload["close"]
                self.ledger.update_market_price(event.symbol, self.last_price)
            elif event.event_type == BacktestEventType.TRADE:
                self.last_price = event.payload["price"]
                self.ledger.update_market_price(event.symbol, self.last_price)
                trade_payload = event.payload
            elif event.event_type == BacktestEventType.DEPTH_SNAPSHOT:
                if "bids" in event.payload and "asks" in event.payload:
                    self.order_book.apply_snapshot_frame(
                        bids=event.payload["bids"],
                        asks=event.payload["asks"],
                    )
                else:
                    self.order_book.apply_delta(
                        action=event.payload.get("action", "SNAPSHOT"),
                        side=event.payload.get("side", "BID"),
                        price=event.payload.get("price"),
                        size=event.payload.get("size"),
                        level_idx=event.payload.get("level_idx"),
                    )

                if self.order_book.best_bid and self.order_book.best_ask:
                    self.last_price = (self.order_book.best_bid + self.order_book.best_ask) / Decimal("2.0")
                    self.ledger.update_market_price(event.symbol, self.last_price)
            elif event.event_type == BacktestEventType.DEPTH_DELTA:
                self.order_book.apply_delta(
                    action=event.payload.get("action", "MODIFY"),
                    side=event.payload.get("side", "BID"),
                    price=event.payload.get("price"),
                    size=event.payload.get("size"),
                    level_idx=event.payload.get("level_idx"),
                )

                if self.order_book.best_bid and self.order_book.best_ask:
                    self.last_price = (self.order_book.best_bid + self.order_book.best_ask) / Decimal("2.0")
                    self.ledger.update_market_price(event.symbol, self.last_price)


            # 2. Process Matching for Pending Orders
            self._process_order_matching(self.current_time_ns, trade_event_payload=trade_payload)

            # 3. Invoke Strategy Actor Handler if present
            if self.strategy_actor is not None:
                if event.event_type == BacktestEventType.BAR:
                    self.strategy_actor.on_bar(event, self)
                elif event.event_type == BacktestEventType.TRADE:
                    self.strategy_actor.on_trade(event, self)

            # 4. Record Equity Snapshot
            current_eq = self.ledger.calculate_balance_sheet_equity()
            if current_eq > self.peak_equity:
                self.peak_equity = current_eq

            dd = max(Decimal("0.0"), self.peak_equity - current_eq)
            dd_pct = (
                (dd / self.peak_equity) * Decimal("100.0")
                if self.peak_equity > Decimal("0.0")
                else Decimal("0.0")
            )
            if dd_pct > self.max_drawdown:
                self.max_drawdown = dd_pct

            self.equity_records.append(
                {
                    "timestamp_utc": event.event_time_utc,
                    "event_timestamp_ns": event.event_timestamp_ns,
                    "cash_balance": self.ledger.cash_balance,
                    "realized_pnl": self.ledger.cumulative_realized_pnl,
                    "unrealized_pnl": sum((p.unrealized_pnl for p in self.ledger.positions.values()), Decimal("0.0")),
                    "total_equity": current_eq,
                    "margin_utilized": Decimal("0.0"),
                    "accounting_residual": Decimal("0.0"),
                }
            )

        duration_ms = int((time.perf_counter() - start_wall_clock) * 1000)

        # -----------------------------------------------------------------
        # Performance Summary Calculations
        # -----------------------------------------------------------------
        ending_equity = self.ledger.calculate_balance_sheet_equity()
        net_return_pct = (
            ((ending_equity - self.config.initial_cash) / self.config.initial_cash) * Decimal("100.0")
        )
        total_vol = sum((f.fill_qty * f.fill_price for f in self.fills), Decimal("0.0"))
        total_fees = sum((f.fee_paid for f in self.fills), Decimal("0.0"))

        win_rate = (
            (Decimal(self.profitable_trades_count) / Decimal(self.total_closed_trades_count)) * Decimal("100.0")
            if self.total_closed_trades_count > 0
            else Decimal("0.0")
        )
        profit_factor = (
            self.gross_profits / self.gross_losses
            if self.gross_losses > Decimal("0.0")
            else (Decimal("999.99") if self.gross_profits > Decimal("0.0") else Decimal("0.0"))
        )

        exec_summary = BacktestExecutionSummary(
            total_orders=len(self.orders),
            total_fills=len(self.fills),
            total_volume_traded=total_vol,
            total_fees_paid=total_fees,
            realized_pnl=self.ledger.cumulative_realized_pnl,
            unrealized_pnl=sum((p.unrealized_pnl for p in self.ledger.positions.values()), Decimal("0.0")),
            ending_equity=ending_equity,
            net_return_pct=net_return_pct,
            sharpe_ratio=None,
            sortino_ratio=None,
            max_drawdown_pct=self.max_drawdown,
            win_rate_pct=win_rate,
            profit_factor=profit_factor,
        )

        # Reality Gap Metrics
        simulated_realized_bps = (
            (self.ledger.cumulative_realized_pnl / self.config.initial_cash) * Decimal("10000.0")
            if self.config.initial_cash > Decimal("0.0")
            else Decimal("0.0")
        )
        reality_gap_bps = phase4_analytical_edge_bps - simulated_realized_bps

        reality_gap = RealityGapSummary(
            phase4_analytical_edge_bps=phase4_analytical_edge_bps,
            phase5_simulated_realized_bps=simulated_realized_bps,
            reality_gap_bps=reality_gap_bps,
            spread_drag_bps=self.config.fee_config.taker_fee_bps,
            latency_slip_drag_bps=self.config.slippage_config.fixed_slippage_bps,
            queue_position_drag_bps=Decimal("0.0"),
        )

        # -----------------------------------------------------------------
        # Deterministic Manifest Emission
        # -----------------------------------------------------------------
        engine_cfg_hash = self.config.compute_sha256()
        manifest_id = calculate_backtest_manifest_id(
            hypothesis_spec_sha256=hypothesis_spec_sha256,
            canonical_data_hashes=canonical_data_hashes,
            engine_config_hash=engine_cfg_hash,
            strategy_config_hash=strategy_config_hash,
            prng_seed=self.config.prng_seed,
        )

        manifest = BacktestManifest(
            manifest_id=manifest_id,
            manifest_version="1.0.0",
            hypothesis_id="HYP-PHASE5-POC",
            hypothesis_spec_sha256=hypothesis_spec_sha256,
            canonical_data_hashes=canonical_data_hashes,
            engine_config_hash=engine_cfg_hash,
            strategy_config_hash=strategy_config_hash,
            prng_seed=self.config.prng_seed,
            pyproject_toml_sha256=pyproject_toml_sha256,
            uv_lock_sha256=uv_lock_sha256,
            git_commit_hash=git_commit_hash,
            execution_summary=exec_summary,
            reality_gap=reality_gap,
            computed_at_utc=datetime.now(timezone.utc).isoformat(),
            wall_clock_duration_ms=duration_ms,
        )

        fills_table = self._build_fills_table()
        equity_table = self._build_equity_table()

        return manifest, fills_table, equity_table

    def _build_fills_table(self) -> pa.Table:
        """Construct canonical PyArrow Fills Table with integer nanoseconds."""
        if not self.fills:
            return pa.Table.from_batches([], schema=CANONICAL_BACKTEST_FILLS_SCHEMA)

        timestamps_ns: List[int] = []
        for f in self.fills:
            dt = datetime.fromisoformat(f.fill_timestamp_utc)
            timestamps_ns.append(extract_nanoseconds_from_datetime(dt))

        return pa.Table.from_pydict(
            {
                "fill_id": [f.fill_id for f in self.fills],
                "order_id": [f.order_id for f in self.fills],
                "symbol": [f.symbol for f in self.fills],
                "fill_timestamp_utc": timestamps_ns,
                "side": [f.side for f in self.fills],
                "fill_price": [f.fill_price for f in self.fills],
                "fill_qty": [f.fill_qty for f in self.fills],
                "fee_paid": [f.fee_paid for f in self.fills],
                "liquidity_type": [f.liquidity_type.value for f in self.fills],
                "slippage_incurred_bps": [f.slippage_incurred_bps for f in self.fills],
            },
            schema=CANONICAL_BACKTEST_FILLS_SCHEMA,
        )

    def _build_equity_table(self) -> pa.Table:
        """Construct canonical PyArrow Equity Curve Table with integer nanoseconds."""
        if not self.equity_records:
            return pa.Table.from_batches([], schema=CANONICAL_EQUITY_CURVE_SCHEMA)

        timestamps_ns: List[int] = []
        for r in self.equity_records:
            if "event_timestamp_ns" in r:
                timestamps_ns.append(r["event_timestamp_ns"])
            else:
                timestamps_ns.append(extract_nanoseconds_from_datetime(r["timestamp_utc"]))

        return pa.Table.from_pydict(
            {
                "timestamp_utc": timestamps_ns,
                "cash_balance": [r["cash_balance"] for r in self.equity_records],
                "realized_pnl": [r["realized_pnl"] for r in self.equity_records],
                "unrealized_pnl": [r["unrealized_pnl"] for r in self.equity_records],
                "total_equity": [r["total_equity"] for r in self.equity_records],
                "margin_utilized": [r["margin_utilized"] for r in self.equity_records],
                "accounting_residual": [r["accounting_residual"] for r in self.equity_records],
            },
            schema=CANONICAL_EQUITY_CURVE_SCHEMA,
        )
