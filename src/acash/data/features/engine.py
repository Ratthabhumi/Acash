"""Pure Mathematical Microstructure Feature Engine (Phase 3C).

Strictly enforces:
- Downstream mathematical interpretation only.
- Pure functions without side effects or mutable global state.
- Deterministic tie-breaking (POC / Value Area lower-price-first, boundary level inclusion).
- Exact zero-volume and zero-depth handling (returns None without division-by-zero or infinite ratios).
- Zero trading strategy / BUY-SELL logic.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union
import pyarrow as pa

from acash.data.features.schema import (
    CANONICAL_BOOK_FEATURES_SCHEMA,
    CANONICAL_TRADE_FEATURES_SCHEMA,
    BookFeaturesConfig,
    TradeFeaturesConfig,
)
from acash.data.orderbook.reconstruction import DepthLadderState, PriceLevel
from acash.data.schema import DataContractError

# ---------------------------------------------------------------------------
# Mathematical Core Functions
# ---------------------------------------------------------------------------


DECIMAL_18_PRECISION: Decimal = Decimal("1e-18")


def to_decimal18(val: Optional[Union[Decimal, float, str, int]]) -> Optional[Decimal]:
    """Quantize numeric value to exact 18 scale decimal."""
    if val is None:
        return None
    if isinstance(val, float):
        d = Decimal(f"{val:.18f}")
    elif isinstance(val, Decimal):
        d = val
    else:
        d = Decimal(str(val))
    return d.quantize(DECIMAL_18_PRECISION)


def calculate_session_vwap_and_dispersion(
    trades: Sequence[Tuple[Decimal, Decimal]],
) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """Calculate exact Session VWAP and volume-weighted dispersion (standard deviation).

    Args:
        trades: Sequence of (price, size) tuples.

    Returns:
        (vwap, volume_weighted_std) or (None, None) if total volume is zero.
    """
    if not trades:
        return None, None

    total_volume = Decimal("0")
    weighted_price_sum = Decimal("0")

    for px, sz in trades:
        if sz > Decimal("0"):
            total_volume += sz
            weighted_price_sum += px * sz

    if total_volume <= Decimal("0"):
        return None, None

    vwap = (weighted_price_sum / total_volume).quantize(DECIMAL_18_PRECISION)

    # Compute volume-weighted standard deviation
    weighted_variance_sum = Decimal("0")
    for px, sz in trades:
        if sz > Decimal("0"):
            diff = px - vwap
            weighted_variance_sum += (diff * diff) * sz

    variance = weighted_variance_sum / total_volume
    std_val = variance.sqrt().quantize(DECIMAL_18_PRECISION)

    return vwap, std_val




def calculate_volume_profile(
    trades: Sequence[Tuple[Decimal, Decimal]],
    value_area_pct: Decimal = Decimal("0.70"),
    tick_size: Decimal = Decimal("0.25"),
) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
    """Calculate Point of Control (POC), Value Area High (VAH), and Value Area Low (VAL).

    Deterministic Invariants:
    1. Zero Volume: Returns (None, None, None).
    2. POC Tie-Breaker: When multiple prices share maximum volume, selects the lowest price.
    3. Value Area Expansion Tie-Breaker: When upper and lower adjacent volumes are equal, expands lower price level first.
    4. Boundary Inclusion: The price level whose addition causes accumulated volume >= target is fully included.

    Returns:
        (poc_price, vah_price, val_price)
    """
    if not trades:
        return None, None, None

    price_volume: Dict[Decimal, Decimal] = defaultdict(Decimal)
    total_volume = Decimal("0")

    for px, sz in trades:
        if sz > Decimal("0"):
            price_volume[px] += sz
            total_volume += sz

    if total_volume <= Decimal("0") or not price_volume:
        return None, None, None

    # 1. Determine POC (Point of Control)
    max_vol = Decimal("-1")
    poc_price = Decimal("0")

    # Sort prices ascending to guarantee lower price selection on tie
    for px in sorted(price_volume.keys()):
        vol = price_volume[px]
        if vol > max_vol:
            max_vol = vol
            poc_price = px

    # 2. Value Area Expansion
    target_volume = total_volume * value_area_pct
    accumulated_volume = max_vol
    value_area_set = {poc_price}

    all_prices_sorted = sorted(price_volume.keys())
    poc_idx = all_prices_sorted.index(poc_price)
    up_idx = poc_idx + 1
    down_idx = poc_idx - 1

    while accumulated_volume < target_volume and (up_idx < len(all_prices_sorted) or down_idx >= 0):
        up_vol = price_volume[all_prices_sorted[up_idx]] if up_idx < len(all_prices_sorted) else Decimal("-1")
        down_vol = price_volume[all_prices_sorted[down_idx]] if down_idx >= 0 else Decimal("-1")

        if down_vol == Decimal("-1") and up_vol == Decimal("-1"):
            break

        # Equal volume or down > up -> expand lower price first
        if down_vol >= up_vol and down_vol != Decimal("-1"):
            px_down = all_prices_sorted[down_idx]
            value_area_set.add(px_down)
            accumulated_volume += down_vol
            down_idx -= 1
        elif up_vol != Decimal("-1"):
            px_up = all_prices_sorted[up_idx]
            value_area_set.add(px_up)
            accumulated_volume += up_vol
            up_idx += 1

    val_price = min(value_area_set)
    vah_price = max(value_area_set)

    return poc_price, vah_price, val_price


def calculate_footprint_analytics(
    trades: Sequence[Dict[str, Any]],
    config: TradeFeaturesConfig,
) -> Dict[str, Any]:
    """Calculate Bar Delta, Price-Level Diagonal Imbalances, Stacked Imbalances, and Absorption.

    Deterministic Invariants:
    - Diagonal Buy Imbalance (P + tick vs P):
        V_sell(P) == 0 -> True iff V_buy(P + tick) >= min_imbalance_volume_diff
        V_sell(P) > 0 -> True iff V_buy(P + tick) >= ratio * V_sell(P) and diff >= min_diff
    - Diagonal Sell Imbalance (P vs P + tick):
        V_buy(P + tick) == 0 -> True iff V_sell(P) >= min_imbalance_volume_diff
        V_buy(P + tick) > 0 -> True iff V_sell(P) >= ratio * V_buy(P + tick) and diff >= min_diff
    - Stacked Imbalance: >= config.stacked_imbalance_min_levels consecutive price levels.
    """
    if not trades:
        return {
            "buy_volume": Decimal("0"),
            "sell_volume": Decimal("0"),
            "delta": Decimal("0"),
            "has_stacked_buy_imbalance": False,
            "has_stacked_sell_imbalance": False,
            "is_absorption_bar": False,
        }

    buy_volume = Decimal("0")
    sell_volume = Decimal("0")
    price_buy_vol: Dict[Decimal, Decimal] = defaultdict(Decimal)
    price_sell_vol: Dict[Decimal, Decimal] = defaultdict(Decimal)
    all_prices: Set[Decimal] = set()


    for trd in trades:
        px = trd["price"] if isinstance(trd["price"], Decimal) else Decimal(str(trd["price"]))
        sz = trd["size"] if isinstance(trd["size"], Decimal) else Decimal(str(trd["size"]))
        side = str(trd["aggressor_side"]).upper()

        all_prices.add(px)
        if side == "BUY":
            buy_volume += sz
            price_buy_vol[px] += sz
        elif side == "SELL":
            sell_volume += sz
            price_sell_vol[px] += sz
        else:
            # Unknown split evenly
            half = sz / Decimal("2")
            buy_volume += half
            sell_volume += half
            price_buy_vol[px] += half
            price_sell_vol[px] += half

    delta = buy_volume - sell_volume
    sorted_prices = sorted(all_prices)
    tick = config.tick_size
    ratio = config.imbalance_ratio
    min_diff = config.min_imbalance_volume_diff

    # Evaluate Diagonal Imbalances across consecutive price ticks
    buy_imbalances: Dict[Decimal, bool] = {}
    sell_imbalances: Dict[Decimal, bool] = {}

    for i in range(len(sorted_prices) - 1):
        p_low = sorted_prices[i]
        p_high = sorted_prices[i + 1]

        # Only evaluate adjacent prices within 1 tick distance
        if (p_high - p_low) == tick:
            v_buy_high = price_buy_vol[p_high]
            v_sell_low = price_sell_vol[p_low]

            # 1. Buy Diagonal Imbalance at p_high vs p_low
            if v_sell_low == Decimal("0"):
                is_buy_imb = v_buy_high >= min_diff
            else:
                is_buy_imb = (v_buy_high >= ratio * v_sell_low) and ((v_buy_high - v_sell_low) >= min_diff)
            buy_imbalances[p_high] = is_buy_imb

            # 2. Sell Diagonal Imbalance at p_low vs p_high
            if v_buy_high == Decimal("0"):
                is_sell_imb = v_sell_low >= min_diff
            else:
                is_sell_imb = (v_sell_low >= ratio * v_buy_high) and ((v_sell_low - v_buy_high) >= min_diff)
            sell_imbalances[p_low] = is_sell_imb

    # Detect Stacked Imbalances (>= N consecutive levels)
    def check_stacked(imbalances: Dict[Decimal, bool], min_stacked: int) -> bool:
        consecutive = 0
        for p in sorted(imbalances.keys()):
            if imbalances[p]:
                consecutive += 1
                if consecutive >= min_stacked:
                    return True
            else:
                consecutive = 0
        return False

    has_stacked_buy = check_stacked(buy_imbalances, config.stacked_imbalance_min_levels)
    has_stacked_sell = check_stacked(sell_imbalances, config.stacked_imbalance_min_levels)

    # Detect Absorption: high volume spike at bar extreme with zero price progression
    is_absorption = False
    if len(sorted_prices) >= 2:
        high_p = sorted_prices[-1]
        low_p = sorted_prices[0]
        avg_vol = (buy_volume + sell_volume) / Decimal(str(len(sorted_prices)))
        high_vol = price_buy_vol[high_p] + price_sell_vol[high_p]
        low_vol = price_buy_vol[low_p] + price_sell_vol[low_p]

        threshold = avg_vol * config.absorption_volume_multiplier
        if (high_vol >= threshold and high_vol > Decimal("0")) or (low_vol >= threshold and low_vol > Decimal("0")):
            is_absorption = True

    return {
        "buy_volume": buy_volume,
        "sell_volume": sell_volume,
        "delta": delta,
        "has_stacked_buy_imbalance": has_stacked_buy,
        "has_stacked_sell_imbalance": has_stacked_sell,
        "is_absorption_bar": is_absorption,
    }


def calculate_book_microstructure(
    ladder_state: DepthLadderState,
    config: Optional[BookFeaturesConfig] = None,
) -> Dict[str, Any]:
    """Calculate Order Book Microstructure Signals (Spread, Micro-Price, Top-N OBI, Depth).

    Deterministic Invariants:
    - Total Depth == 0 -> spread=0, micro_price=None, obi=0.
    - Top-N OBI = (sum(w_j * Q_bid) - sum(w_j * Q_ask)) / (sum(w_j * Q_bid) + sum(w_j * Q_ask)).
    - Top-N Depth-Weighted BBO Micro-Price:
        P_micro = ((sum(w_j * Q_bid)) * P_ask,0 + (sum(w_j * Q_ask)) * P_bid,0) / (total_weighted_depth).
    """
    cfg = config or BookFeaturesConfig()
    bids = ladder_state.bids
    asks = ladder_state.asks

    if not bids or not asks:
        return {
            "spread": Decimal("0"),
            "micro_price": None,
            "obi_top1": Decimal("0"),
            "obi_top5": Decimal("0"),
            "obi_top10": Decimal("0"),
            "total_bid_depth": Decimal("0"),
            "total_ask_depth": Decimal("0"),
            "is_crossed": ladder_state.is_crossed,
        }

    p_bid0 = bids[0].price
    p_ask0 = asks[0].price
    spread = p_ask0 - p_bid0

    def compute_weighted_depth(levels: List[PriceLevel], n: int) -> Decimal:
        w_depth = Decimal("0")
        for j, lvl in enumerate(levels[:n]):
            w = Decimal("1") / Decimal(str(j + 1)) if cfg.use_linear_depth_weights else Decimal("1")
            w_depth += w * lvl.size
        return w_depth

    # Total unweighted depths
    total_bid_depth = sum(lvl.size for lvl in bids)
    total_ask_depth = sum(lvl.size for lvl in asks)

    # Top-1, Top-5, Top-10 OBI
    def compute_obi(n: int) -> Decimal:
        w_bid = compute_weighted_depth(bids, n)
        w_ask = compute_weighted_depth(asks, n)
        denom = w_bid + w_ask
        if denom <= Decimal("0"):
            return Decimal("0")
        return (w_bid - w_ask) / denom

    obi_1 = to_decimal18(compute_obi(1)) or Decimal("0")
    obi_5 = to_decimal18(compute_obi(5)) or Decimal("0")
    obi_10 = to_decimal18(compute_obi(10)) or Decimal("0")

    # Top-N Depth-Weighted BBO Micro-Price (Top 5 depth weights)
    w_bid_5 = compute_weighted_depth(bids, 5)
    w_ask_5 = compute_weighted_depth(asks, 5)
    denom_5 = w_bid_5 + w_ask_5

    if denom_5 > Decimal("0"):
        micro_price = to_decimal18((w_bid_5 * p_ask0 + w_ask_5 * p_bid0) / denom_5)
    else:
        micro_price = None

    return {
        "spread": to_decimal18(spread) or Decimal("0"),
        "micro_price": micro_price,
        "obi_top1": obi_1,
        "obi_top5": obi_5,
        "obi_top10": obi_10,
        "total_bid_depth": to_decimal18(total_bid_depth) or Decimal("0"),
        "total_ask_depth": to_decimal18(total_ask_depth) or Decimal("0"),
        "is_crossed": ladder_state.is_crossed,
    }


# ---------------------------------------------------------------------------
# Table Extraction Orchestrators
# ---------------------------------------------------------------------------


def compute_trade_features_table(
    trades_table: pa.Table,
    symbol: str,
    trading_date: date,
    config: Optional[TradeFeaturesConfig] = None,
) -> pa.Table:
    """Compute time-windowed trade flow microstructure features from canonical trades table."""
    cfg = config or TradeFeaturesConfig()

    if trades_table.num_rows == 0:
        return pa.Table.from_batches([], schema=CANONICAL_TRADE_FEATURES_SCHEMA)

    pydict = trades_table.to_pydict()
    num_rows = trades_table.num_rows

    trades_records = []
    for i in range(num_rows):
        trades_records.append({
            "exchange_time_utc": pydict["exchange_time_utc"][i],
            "price": pydict["price"][i] if isinstance(pydict["price"][i], Decimal) else Decimal(str(pydict["price"][i])),
            "size": pydict["size"][i] if isinstance(pydict["size"][i], Decimal) else Decimal(str(pydict["size"][i])),
            "aggressor_side": str(pydict["aggressor_side"][i]),
        })

    # Sort trades chronologically
    trades_records.sort(key=lambda x: x["exchange_time_utc"])

    # Partition into time bars of interval seconds
    interval_delta = timedelta(seconds=cfg.bar_interval_seconds)
    min_t = trades_records[0]["exchange_time_utc"]
    # Truncate min_t to interval boundary
    epoch_sec = int(min_t.timestamp())
    bar_start_sec = (epoch_sec // cfg.bar_interval_seconds) * cfg.bar_interval_seconds
    current_bar_start = datetime.fromtimestamp(bar_start_sec, tz=timezone.utc)

    bars: List[Dict[str, Any]] = []
    current_bar_trades: List[Dict[str, Any]] = []
    session_cumulative_trades: List[Tuple[Decimal, Decimal]] = []
    cvd_accumulator = Decimal("0")

    trade_idx = 0
    while trade_idx < len(trades_records):
        current_bar_end = current_bar_start + interval_delta
        current_bar_trades.clear()

        while trade_idx < len(trades_records) and trades_records[trade_idx]["exchange_time_utc"] < current_bar_end:
            trd = trades_records[trade_idx]
            current_bar_trades.append(trd)
            session_cumulative_trades.append((trd["price"], trd["size"]))
            trade_idx += 1

        if current_bar_trades:
            # Compute Bar OHLCV
            prices = [t["price"] for t in current_bar_trades]
            bar_open = prices[0]
            bar_high = max(prices)
            bar_low = min(prices)
            bar_close = prices[-1]
            bar_volume = sum(t["size"] for t in current_bar_trades)

            # Footprint & Delta
            fp = calculate_footprint_analytics(current_bar_trades, cfg)
            cvd_accumulator += fp["delta"]

            # Session VWAP & Dispersion (Cumulative from session start)
            vwap, vwap_std = calculate_session_vwap_and_dispersion(session_cumulative_trades)

            # Session Volume Profile & Value Area (Cumulative)
            poc_px, vah_px, val_px = calculate_volume_profile(
                session_cumulative_trades,
                value_area_pct=cfg.value_area_pct,
                tick_size=cfg.tick_size,
            )

            bars.append({
                "symbol": symbol,
                "trading_date": trading_date,
                "bar_start_utc": current_bar_start,
                "bar_end_utc": current_bar_end,
                "open": to_decimal18(bar_open),
                "high": to_decimal18(bar_high),
                "low": to_decimal18(bar_low),
                "close": to_decimal18(bar_close),
                "volume": to_decimal18(bar_volume),
                "buy_volume": to_decimal18(fp["buy_volume"]),
                "sell_volume": to_decimal18(fp["sell_volume"]),
                "delta": to_decimal18(fp["delta"]),
                "cvd": to_decimal18(cvd_accumulator),
                "vwap": to_decimal18(vwap),
                "vwap_std": to_decimal18(vwap_std),
                "poc_price": to_decimal18(poc_px),
                "vah_price": to_decimal18(vah_px),
                "val_price": to_decimal18(val_px),
                "has_stacked_buy_imbalance": fp["has_stacked_buy_imbalance"],
                "has_stacked_sell_imbalance": fp["has_stacked_sell_imbalance"],
                "is_absorption_bar": fp["is_absorption_bar"],
            })


        current_bar_start = current_bar_end

    if not bars:
        return pa.Table.from_batches([], schema=CANONICAL_TRADE_FEATURES_SCHEMA)

    table_data = {col: [b[col] for b in bars] for col in CANONICAL_TRADE_FEATURES_SCHEMA.names}
    return pa.Table.from_pydict(table_data, schema=CANONICAL_TRADE_FEATURES_SCHEMA)


def compute_book_features_table(
    ladder_states: Sequence[DepthLadderState],
    config: Optional[BookFeaturesConfig] = None,
) -> pa.Table:
    """Compute book microstructure features table from a sequence of point-in-time reconstructed ladder states."""
    cfg = config or BookFeaturesConfig()

    if not ladder_states:
        return pa.Table.from_batches([], schema=CANONICAL_BOOK_FEATURES_SCHEMA)

    rows = []
    for state in ladder_states:
        micro = calculate_book_microstructure(state, cfg)
        sym = state.stream_scope[2]
        t_d = date.fromisoformat(state.stream_scope[3])

        rows.append({
            "symbol": sym,
            "trading_date": t_d,
            "exchange_time_utc": state.exchange_time_utc,
            "knowledge_time_utc": state.exchange_time_utc,  # Observation time anchor
            "spread": micro["spread"],
            "micro_price": micro["micro_price"],
            "obi_top1": micro["obi_top1"],
            "obi_top5": micro["obi_top5"],
            "obi_top10": micro["obi_top10"],
            "total_bid_depth": micro["total_bid_depth"],
            "total_ask_depth": micro["total_ask_depth"],
            "is_crossed": micro["is_crossed"],
        })

    table_data = {col: [r[col] for r in rows] for col in CANONICAL_BOOK_FEATURES_SCHEMA.names}
    return pa.Table.from_pydict(table_data, schema=CANONICAL_BOOK_FEATURES_SCHEMA)
