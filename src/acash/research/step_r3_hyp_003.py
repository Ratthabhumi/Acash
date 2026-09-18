"""Phase 14 Step R3 Research Engine: In-Sample Search Trial Census for HYP_003.

Hypothesis: HYP_003 (Opening Range Breakout on SPY — MEC-0013 Price-Only Mechanics)
Primary Cells: Exactly K = 4 frozen cells:
  1. ORB_5M_LONG
  2. ORB_5M_SHORT
  3. ORB_15M_LONG
  4. ORB_15M_SHORT

Temporal Scope: 2017-01-01 through 2022-12-31 (In-Sample ONLY; 1,492 qualified sessions)
OOS Boundary:   >= 2023-01-01 (STRICTLY SEALED / UNREAD / FORBIDDEN)

Strict Anti-HARKing Invariants:
- Fixed K = 4 declared == executed == reported.
- Zero parameter tuning, zero cell pruning, zero post-hoc indicator injection.
- Zero reliance on legacy Phase 4 predictive regression schema.
- Strict fail-closed contracts across data loading, signals, fills, costs, and sealing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer, deep_freeze_value
from acash.data.features.engine import to_decimal18
from acash.data.provenance import calculate_canonical_batch_sha256
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification
from acash.validation.gate import _compute_canonical_series_sha256
from acash.validation.schema import (
    SearchTrialLedger,
    SearchTrialRecord,
    SearchTrialStatus,
    SharpeSpace,
)

# Canonical In-Sample Boundaries
IS_START_DATE: date = date(2017, 1, 1)
IS_END_DATE: date = date(2022, 12, 31)
OOS_SEALED_BOUNDARY_DATE: date = date(2023, 1, 1)

# Canonical Preconditions & Hashes
EXPECTED_HYP_003_SHA256: str = "f59010d14f466e9681325a314fd3e7ef30af43ffd69bc6cecbad1b5e6aab4ee0"
EXPECTED_PREREG_SHA256: str = "3c04f617b9877a85a07043e67b7554034ebd703fe823d3d2de777a7722a3150c"
EXPECTED_R1_MANIFEST_SHA256: str = "27952f476cf96f75dc47ca0eb68a4b74d1f8dc6bf2f0848d1a877740cc32b372"
EXPECTED_CANONICAL_DATASET_SHA256: str = "2a70922156f3d724fffbf7030d791d0da3b0fa1c44f839eea794c2fb2d689ddc"
EXPECTED_QUALIFIED_SESSIONS: int = 1492
EXPECTED_CANONICAL_BARS: int = 581880
REGULAR_SESSION_BAR_COUNT: int = 390

# Frozen Friction Constants (MEC-0013 Sections 6 & 7)
FROZEN_TRANSACTION_COST_PER_SIDE: Decimal = Decimal("0.00008")  # 0.8 bps
FROZEN_SLIPPAGE_PER_SIDE: Decimal = Decimal("0.00005")          # 0.5 bps

# Timezone Authority
NY_TZ: ZoneInfo = ZoneInfo("America/New_York")


def assert_is_boundary(d: date) -> None:
    """Fail-closed assertion enforcing that a date is strictly within IS (2017-01-01..2022-12-31).

    Any date >= 2023-01-01 immediately aborts to preserve the Out-of-Sample seal.
    """
    if d >= OOS_SEALED_BOUNDARY_DATE:
        raise DataContractError(
            f"OOS HARD BOUNDARY VIOLATION: Date {d.isoformat()} lies within the sealed Out-of-Sample "
            f"window (>= {OOS_SEALED_BOUNDARY_DATE.isoformat()}). Access is strictly prohibited."
        )
    if d < IS_START_DATE:
        raise DataContractError(
            f"PRE-IN-SAMPLE BOUNDARY VIOLATION: Date {d.isoformat()} is prior to authorized IS start "
            f"({IS_START_DATE.isoformat()})."
        )


@dataclass(frozen=True)
class OrbCellConfig:
    """Frozen specification of a primary price-only ORB cell."""
    cell_id: str
    window_minutes: int
    direction: str  # "LONG" or "SHORT"
    entry_cost_rate: Decimal = FROZEN_TRANSACTION_COST_PER_SIDE
    exit_cost_rate: Decimal = FROZEN_TRANSACTION_COST_PER_SIDE
    slippage_rate: Decimal = FROZEN_SLIPPAGE_PER_SIDE


# Exact K=4 Frozen Primary Cells
PRIMARY_ORB_CELLS: Tuple[OrbCellConfig, ...] = (
    OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG"),
    OrbCellConfig(cell_id="ORB_5M_SHORT", window_minutes=5, direction="SHORT"),
    OrbCellConfig(cell_id="ORB_15M_LONG", window_minutes=15, direction="LONG"),
    OrbCellConfig(cell_id="ORB_15M_SHORT", window_minutes=15, direction="SHORT"),
)


@dataclass(frozen=True)
class OrbBar:
    """Canonical 1-minute bar representation for simulation."""
    event_start_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class OrbTradeRecord:
    """Deterministic audit record of a single executed ORB trade."""
    session_date: date
    cell_id: str
    direction: str
    signal_bar_index: int
    signal_time_utc: datetime
    entry_bar_index: int
    entry_time_utc: datetime
    observable_entry_price: Decimal
    fill_entry_price: Decimal
    exit_bar_index: int
    exit_time_utc: datetime
    observable_exit_price: Decimal
    fill_exit_price: Decimal
    exit_reason: str  # "STOP_LOSS" or "EOD_FLATTEN"
    gross_return: Decimal
    net_return: Decimal


@dataclass(frozen=True)
class OrbSessionResult:
    """Outcome of simulating an ORB cell on a single regular trading session."""
    session_date: date
    cell_id: str
    had_signal: bool
    had_trade: bool
    trade: Optional[OrbTradeRecord]
    daily_gross_return: Decimal
    daily_net_return: Decimal


@dataclass(frozen=True)
class OrbCellSummary:
    """Aggregated empirical census report for a primary ORB cell."""
    cell_id: str
    window_minutes: int
    direction: str
    eligible_session_count: int
    signal_count: int
    trade_count: int
    no_signal_session_count: int
    stop_exit_count: int
    eod_exit_count: int
    gross_cumulative_return: Decimal
    net_cumulative_return: Decimal
    mean_trade_return: Decimal
    median_trade_return: Decimal
    std_trade_return: Decimal
    min_trade_return: Decimal
    max_trade_return: Decimal
    win_count: int
    loss_count: int
    win_rate: Decimal
    max_drawdown: Decimal
    turnover: int
    annualized_sharpe_daily: Decimal
    canonical_p_value: Decimal
    p_value_input_hash: str
    in_sample_return_series_sha256: str
    config_sha256: str


def validate_r3_preconditions(repo_root: Optional[Path] = None) -> Dict[str, str]:
    """Verify all upstream governance documents, hashes, and lineage before Step R3 execution."""
    root = repo_root or Path(".")

    # 1. Sealed HYP_003
    hyp_path = root / "docs/phase14/hypotheses/HYP_003.json"
    if not hyp_path.exists():
        raise DataContractError(f"Precondition failed: Sealed HYP_003 not found at {hyp_path}")
    with open(hyp_path, "r", encoding="utf-8") as f:
        hyp_data = json.load(f)
    spec = HypothesisSpecification.model_validate(hyp_data)
    computed_hyp_sha = calculate_hypothesis_spec_sha256(spec)
    if computed_hyp_sha != EXPECTED_HYP_003_SHA256:
        raise DataContractError(
            f"Precondition failed: HYP_003 SHA-256 mismatch! Got {computed_hyp_sha}, expected {EXPECTED_HYP_003_SHA256}"
        )

    # 2. Frozen Pre-registration
    prereg_path = root / "docs/phase14/mec_0013_price_only_preregistration.md"
    if not prereg_path.exists():
        raise DataContractError(f"Precondition failed: Preregistration not found at {prereg_path}")
    computed_prereg_sha = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
    if computed_prereg_sha != EXPECTED_PREREG_SHA256:
        raise DataContractError(
            f"Precondition failed: Preregistration SHA-256 mismatch! Got {computed_prereg_sha}, expected {EXPECTED_PREREG_SHA256}"
        )

    # 3. R1 Manifest
    r1_manifest_path = root / "docs/phase14/manifests/manifest_r1_HYP_003.json"
    if not r1_manifest_path.exists():
        raise DataContractError(f"Precondition failed: R1 Manifest not found at {r1_manifest_path}")
    with open(r1_manifest_path, "r", encoding="utf-8") as f:
        r1_man_data = json.load(f)
    manifest_digest = r1_man_data.get("manifest_sha256", "")
    payload_copy = {k: v for k, v in r1_man_data.items() if k != "manifest_sha256"}
    recalculated = hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(payload_copy).encode("utf-8")
    ).hexdigest()
    if manifest_digest != EXPECTED_R1_MANIFEST_SHA256 or recalculated != EXPECTED_R1_MANIFEST_SHA256:
        raise DataContractError(
            f"Precondition failed: R1 manifest SHA-256 mismatch! Got {manifest_digest} (recalc: {recalculated}), expected {EXPECTED_R1_MANIFEST_SHA256}"
        )

    # 4. Semantic Conformance Record
    clarification_path = root / "docs/phase14/phase14_r1_semantic_conformance_record_HYP_003.md"
    if not clarification_path.exists():
        raise DataContractError(f"Precondition failed: Semantic clarification record not found at {clarification_path}")
    clarification_sha = hashlib.sha256(clarification_path.read_bytes()).hexdigest()

    # 5. R2 Manifest
    r2_manifest_path = root / "docs/phase14/manifests/manifest_r2_HYP_003.json"
    if not r2_manifest_path.exists():
        raise DataContractError(f"Precondition failed: R2 Manifest not found at {r2_manifest_path}")
    r2_manifest_sha = hashlib.sha256(r2_manifest_path.read_bytes()).hexdigest()

    # 6. Canonical Parquet Dataset
    parquet_path = root / "data/parquet/research/HYP_003_SPY_1Min_IS_canonical.parquet"
    if not parquet_path.exists():
        raise DataContractError(f"Precondition failed: Canonical dataset not found at {parquet_path}")

    return {
        "hypothesis_sha256": computed_hyp_sha,
        "preregistration_sha256": computed_prereg_sha,
        "r1_manifest_sha256": manifest_digest,
        "clarification_record": str(clarification_path),
        "clarification_sha256": clarification_sha,
        "r2_manifest_path": str(r2_manifest_path),
        "r2_manifest_sha256": r2_manifest_sha,
        "parquet_path": str(parquet_path),
    }


def load_and_validate_canonical_r2_dataset(
    parquet_path: Path,
) -> List[Tuple[date, List[OrbBar]]]:
    """Load canonical R2 In-Sample Parquet dataset and enforce strict validation invariants."""
    if not parquet_path.is_file():
        raise DataContractError(f"Canonical dataset file does not exist: {parquet_path}")

    table = pq.read_table(parquet_path)
    total_bars = table.num_rows

    if total_bars != EXPECTED_CANONICAL_BARS:
        raise DataContractError(
            f"Canonical dataset row count mismatch: expected {EXPECTED_CANONICAL_BARS}, got {total_bars}"
        )

    batch_sha256 = calculate_canonical_batch_sha256(table)
    if batch_sha256 != EXPECTED_CANONICAL_DATASET_SHA256:
        raise DataContractError(
            f"Canonical dataset SHA-256 mismatch! Got '{batch_sha256}', expected '{EXPECTED_CANONICAL_DATASET_SHA256}'"
        )

    # Extract columns
    event_start_utcs = table["event_start_utc"].to_pylist()
    opens = table["open"].to_pylist()
    highs = table["high"].to_pylist()
    lows = table["low"].to_pylist()
    closes = table["close"].to_pylist()
    volumes = table["volume"].to_pylist()

    num_sessions = total_bars // REGULAR_SESSION_BAR_COUNT
    if num_sessions != EXPECTED_QUALIFIED_SESSIONS:
        raise DataContractError(
            f"Session count mismatch: expected {EXPECTED_QUALIFIED_SESSIONS}, got {num_sessions}"
        )

    sessions: List[Tuple[date, List[OrbBar]]] = []

    for i in range(num_sessions):
        idx_start = i * REGULAR_SESSION_BAR_COUNT
        idx_end = (i + 1) * REGULAR_SESSION_BAR_COUNT
        session_ts = event_start_utcs[idx_start:idx_end]

        d_start = session_ts[0].astimezone(NY_TZ).date()
        d_end = session_ts[-1].astimezone(NY_TZ).date()
        if d_start != d_end:
            raise DataContractError(
                f"Session {i} bars cross day boundaries: {d_start.isoformat()} vs {d_end.isoformat()}"
            )

        assert_is_boundary(d_start)

        session_bars: List[OrbBar] = []
        for j in range(idx_start, idx_end):
            ts = event_start_utcs[j]
            o = Decimal(str(opens[j]))
            h = Decimal(str(highs[j]))
            l = Decimal(str(lows[j]))
            c = Decimal(str(closes[j]))
            v = Decimal(str(volumes[j]))
            session_bars.append(OrbBar(event_start_utc=ts, open=o, high=h, low=l, close=c, volume=v))

        sessions.append((d_start, session_bars))

    return sessions


def simulate_orb_session(
    session_date: date,
    bars: Sequence[OrbBar],
    config: OrbCellConfig,
) -> OrbSessionResult:
    """Simulate frozen price-only Opening Range Breakout logic on a single 390-min regular session.

    Execution Invariants:
    1. Opening Range: Computed over first `config.window_minutes` bars [0 .. W-1].
       - OR_high = max(high[:W])
       - OR_low = min(low[:W])
    2. Signal Eligibility: Begins at bar index W (e.g. 09:35 for 5m, 09:45 for 15m) up to 388 (15:58).
    3. Breakout Rule:
       - LONG:  Close_t > OR_high (wick-only does not count)
       - SHORT: Close_t < OR_low  (wick-only does not count)
    4. First-breakout only. Max 1 trade per cell per session. No re-entry.
    5. Entry Fill:
       - If breakout at bar t < 389: entry at bar t+1 at Open_{t+1}.
       - Slippage: +0.5 bps for LONG, -0.5 bps for SHORT.
       - If breakout at bar 389: signal recorded, but NO next bar exists in regular session -> NO TRADE.
    6. Stop Execution:
       - Fixed opposite boundary: stop = OR_low (LONG) or OR_high (SHORT).
       - Evaluated from bar b = t+1 to 389:
         - LONG:  if Low_b <= stop: exit observable = min(stop, Open_b, Low_b), exit fill = observable * (1 - slippage).
         - SHORT: if High_b >= stop: exit observable = max(stop, Open_b, High_b), exit fill = observable * (1 + slippage).
         - Exit reason = STOP_LOSS.
    7. EOD Exit:
       - If stop not triggered, exit at bar 389 (15:59 ET) at Close_{389}.
       - Long exit fill = Close_{389} * (1 - slippage).
       - Short exit fill = Close_{389} * (1 + slippage).
       - Exit reason = EOD_FLATTEN.
    8. Friction / Returns:
       - Transaction cost: 0.8 bps entry, 0.8 bps exit = 1.6 bps round-trip.
       - Slippage applied to observable prices.
    """
    assert_is_boundary(session_date)
    if len(bars) != REGULAR_SESSION_BAR_COUNT:
        raise DataContractError(
            f"Session {session_date.isoformat()} bar count != {REGULAR_SESSION_BAR_COUNT} (got {len(bars)})"
        )

    w = config.window_minutes
    or_high = max(b.high for b in bars[:w])
    or_low = min(b.low for b in bars[:w])

    signal_bar_idx: Optional[int] = None

    # Scan for first breakout close
    for idx in range(w, REGULAR_SESSION_BAR_COUNT):
        b = bars[idx]
        if config.direction == "LONG":
            if b.close > or_high:
                signal_bar_idx = idx
                break
        elif config.direction == "SHORT":
            if b.close < or_low:
                signal_bar_idx = idx
                break
        else:
            raise DataContractError(f"Unsupported direction: '{config.direction}'")

    # If no breakout signal in session
    if signal_bar_idx is None:
        return OrbSessionResult(
            session_date=session_date,
            cell_id=config.cell_id,
            had_signal=False,
            had_trade=False,
            trade=None,
            daily_gross_return=Decimal("0"),
            daily_net_return=Decimal("0"),
        )

    # Breakout occurred on final bar (389): no next minute exists -> no trade
    if signal_bar_idx >= REGULAR_SESSION_BAR_COUNT - 1:
        return OrbSessionResult(
            session_date=session_date,
            cell_id=config.cell_id,
            had_signal=True,
            had_trade=False,
            trade=None,
            daily_gross_return=Decimal("0"),
            daily_net_return=Decimal("0"),
        )

    # Entry at next-bar open (t + 1)
    entry_bar_idx = signal_bar_idx + 1
    entry_bar = bars[entry_bar_idx]
    obs_entry = entry_bar.open

    if config.direction == "LONG":
        fill_entry = obs_entry * (Decimal("1") + config.slippage_rate)
        stop_boundary = or_low
    else:
        fill_entry = obs_entry * (Decimal("1") - config.slippage_rate)
        stop_boundary = or_high

    exit_bar_idx: Optional[int] = None
    obs_exit: Optional[Decimal] = None
    fill_exit: Optional[Decimal] = None
    exit_reason: Optional[str] = None

    # Evaluate bars from entry_bar_idx to 389
    for b_idx in range(entry_bar_idx, REGULAR_SESSION_BAR_COUNT):
        b = bars[b_idx]
        if config.direction == "LONG":
            # Stop condition
            if b.low <= stop_boundary or b.open <= stop_boundary:
                exit_bar_idx = b_idx
                obs_exit = min(stop_boundary, b.open, b.low)
                fill_exit = obs_exit * (Decimal("1") - config.slippage_rate)
                exit_reason = "STOP_LOSS"
                break
        else:
            # Short stop condition
            if b.high >= stop_boundary or b.open >= stop_boundary:
                exit_bar_idx = b_idx
                obs_exit = max(stop_boundary, b.open, b.high)
                fill_exit = obs_exit * (Decimal("1") + config.slippage_rate)
                exit_reason = "STOP_LOSS"
                break

    # EOD flatten at bar 389 close if stop was not triggered
    if exit_bar_idx is None:
        last_bar = bars[REGULAR_SESSION_BAR_COUNT - 1]
        exit_bar_idx = REGULAR_SESSION_BAR_COUNT - 1
        obs_exit = last_bar.close
        if config.direction == "LONG":
            fill_exit = obs_exit * (Decimal("1") - config.slippage_rate)
        else:
            fill_exit = obs_exit * (Decimal("1") + config.slippage_rate)
        exit_reason = "EOD_FLATTEN"

    assert obs_exit is not None and fill_exit is not None and exit_reason is not None

    # Returns calculation
    if config.direction == "LONG":
        gross_ret = (obs_exit - obs_entry) / obs_entry
        # Slipped price return minus transaction costs on entry and exit notional
        slipped_ret = (fill_exit - fill_entry) / fill_entry
        cost_deduction = config.entry_cost_rate + (config.exit_cost_rate * (fill_exit / fill_entry))
        net_ret = slipped_ret - cost_deduction
    else:
        gross_ret = (obs_entry - obs_exit) / obs_entry
        slipped_ret = (fill_entry - fill_exit) / fill_entry
        cost_deduction = config.entry_cost_rate + (config.exit_cost_rate * (fill_exit / fill_entry))
        net_ret = slipped_ret - cost_deduction

    trade_rec = OrbTradeRecord(
        session_date=session_date,
        cell_id=config.cell_id,
        direction=config.direction,
        signal_bar_index=signal_bar_idx,
        signal_time_utc=bars[signal_bar_idx].event_start_utc,
        entry_bar_index=entry_bar_idx,
        entry_time_utc=entry_bar.event_start_utc,
        observable_entry_price=obs_entry,
        fill_entry_price=fill_entry,
        exit_bar_index=exit_bar_idx,
        exit_time_utc=bars[exit_bar_idx].event_start_utc,
        observable_exit_price=obs_exit,
        fill_exit_price=fill_exit,
        exit_reason=exit_reason,
        gross_return=gross_ret,
        net_return=net_ret,
    )

    return OrbSessionResult(
        session_date=session_date,
        cell_id=config.cell_id,
        had_signal=True,
        had_trade=True,
        trade=trade_rec,
        daily_gross_return=gross_ret,
        daily_net_return=net_ret,
    )


def compute_max_drawdown(daily_net_returns: Sequence[Decimal]) -> Decimal:
    """Calculate maximum peak-to-trough drawdown percentage on compounded equity curve."""
    if not daily_net_returns:
        return Decimal("0")

    equity = Decimal("1.0")
    peak = Decimal("1.0")
    max_dd = Decimal("0.0")

    for r in daily_net_returns:
        equity = equity * (Decimal("1.0") + r)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > Decimal("0") else Decimal("0")
        if dd > max_dd:
            max_dd = dd

    return max_dd


def execute_cell_census(
    cell_config: OrbCellConfig,
    sessions: Sequence[Tuple[date, List[OrbBar]]],
) -> Tuple[OrbCellSummary, SearchTrialRecord, List[OrbSessionResult]]:
    """Execute complete deterministic In-Sample census for a single primary ORB cell."""
    session_results: List[OrbSessionResult] = []
    trades: List[OrbTradeRecord] = []
    daily_net_returns: List[Decimal] = []

    for sess_date, bars in sessions:
        res = simulate_orb_session(sess_date, bars, cell_config)
        session_results.append(res)
        daily_net_returns.append(res.daily_net_return)
        if res.had_trade and res.trade is not None:
            trades.append(res.trade)

    eligible_count = len(sessions)
    signal_count = sum(1 for r in session_results if r.had_signal)
    trade_count = len(trades)
    no_signal_count = eligible_count - signal_count
    stop_count = sum(1 for t in trades if t.exit_reason == "STOP_LOSS")
    eod_count = sum(1 for t in trades if t.exit_reason == "EOD_FLATTEN")

    # Cumulative compounded returns
    gross_equity = Decimal("1.0")
    net_equity = Decimal("1.0")
    for r in session_results:
        gross_equity *= (Decimal("1.0") + r.daily_gross_return)
        net_equity *= (Decimal("1.0") + r.daily_net_return)

    gross_cum_ret = gross_equity - Decimal("1.0")
    net_cum_ret = net_equity - Decimal("1.0")

    # Trade-level statistics
    if trade_count > 0:
        net_trade_returns = [t.net_return for t in trades]
        mean_trade_ret = sum(net_trade_returns) / Decimal(trade_count)
        sorted_net = sorted(net_trade_returns)
        if trade_count % 2 == 1:
            median_trade_ret = sorted_net[trade_count // 2]
        else:
            median_trade_ret = (sorted_net[trade_count // 2 - 1] + sorted_net[trade_count // 2]) / Decimal("2")

        diffs_sq = sum((r - mean_trade_ret) ** 2 for r in net_trade_returns)
        std_trade_ret = Decimal(str(math.sqrt(float(diffs_sq / Decimal(max(1, trade_count - 1))))))
        min_trade_ret = min(net_trade_returns)
        max_trade_ret = max(net_trade_returns)
        win_count = sum(1 for r in net_trade_returns if r > Decimal("0"))
        loss_count = sum(1 for r in net_trade_returns if r <= Decimal("0"))
        win_rate = Decimal(win_count) / Decimal(trade_count)
    else:
        mean_trade_ret = Decimal("0")
        median_trade_ret = Decimal("0")
        std_trade_ret = Decimal("0")
        min_trade_ret = Decimal("0")
        max_trade_ret = Decimal("0")
        win_count = 0
        loss_count = 0
        win_rate = Decimal("0")

    max_dd = compute_max_drawdown(daily_net_returns)

    # Daily Return Space Sharpe (Standard 252 annualization factor)
    daily_float = [float(r) for r in daily_net_returns]
    daily_mean = float(np.mean(daily_float))
    daily_std = float(np.std(daily_float, ddof=1))
    period_sharpe = daily_mean / daily_std if daily_std > 1e-12 else 0.0
    annual_sharpe = period_sharpe * math.sqrt(252.0)
    annual_sharpe_dec = to_decimal18(Decimal(f"{annual_sharpe:.18f}")) or Decimal("0")

    # Cryptographic Lineage & Canonical p-value
    daily_net_dec18 = [to_decimal18(r) or Decimal("0") for r in daily_net_returns]
    series_sha256 = _compute_canonical_series_sha256(daily_net_dec18)

    feature_names = ("close", "high", "low", "open", "volume")
    parameters_dict: Dict[str, Any] = {
        "direction": cell_config.direction,
        "entry_rule": "NEXT_BAR_OPEN",
        "eod_exit_time": "15:59",
        "opening_range_window_minutes": cell_config.window_minutes,
        "slippage_bps_per_side": "0.5",
        "stop_rule": "OPPOSITE_OR_BOUNDARY",
        "transaction_cost_bps_round_trip": "1.6",
    }
    config_sha256 = SearchTrialRecord.compute_config_sha256(feature_names, parameters_dict)

    canonical_p = SearchTrialRecord.compute_canonical_p_value(
        daily_net_dec18,
        method="ASYMPTOTIC_TWO_SIDED_ZERO_SHARPE_NORMAL_TEST_V1",
    )

    p_val_input_hash = SearchTrialRecord.compute_p_value_input_hash(
        return_series_sha256=series_sha256,
        config_sha256=config_sha256,
        p_value=canonical_p,
        p_value_method="ASYMPTOTIC_TWO_SIDED_ZERO_SHARPE_NORMAL_TEST_V1",
    )

    summary = OrbCellSummary(
        cell_id=cell_config.cell_id,
        window_minutes=cell_config.window_minutes,
        direction=cell_config.direction,
        eligible_session_count=eligible_count,
        signal_count=signal_count,
        trade_count=trade_count,
        no_signal_session_count=no_signal_count,
        stop_exit_count=stop_count,
        eod_exit_count=eod_count,
        gross_cumulative_return=gross_cum_ret,
        net_cumulative_return=net_cum_ret,
        mean_trade_return=mean_trade_ret,
        median_trade_return=median_trade_ret,
        std_trade_return=std_trade_ret,
        min_trade_return=min_trade_ret,
        max_trade_return=max_trade_ret,
        win_count=win_count,
        loss_count=loss_count,
        win_rate=win_rate,
        max_drawdown=max_dd,
        turnover=trade_count,
        annualized_sharpe_daily=annual_sharpe_dec,
        canonical_p_value=canonical_p,
        p_value_input_hash=p_val_input_hash,
        in_sample_return_series_sha256=series_sha256,
        config_sha256=config_sha256,
    )

    trial_rec = SearchTrialRecord(
        trial_id=cell_config.cell_id,
        strategy_id="HYP_003_ORB_PRICE_ONLY",
        hypothesis_id="HYP_003",
        feature_names=feature_names,
        parameters=dict(parameters_dict),
        trial_status=SearchTrialStatus.EXECUTED_SUCCESSFULLY,
        failure_reason=None,
        in_sample_sharpe=annual_sharpe_dec,
        p_value=canonical_p,
        p_value_method="ASYMPTOTIC_TWO_SIDED_ZERO_SHARPE_NORMAL_TEST_V1",
        p_value_input_hash=p_val_input_hash,
        in_sample_return_series_sha256=series_sha256,
        config_sha256=config_sha256,
        execution_manifest_id="manifest_r3_HYP_003",
    )

    return summary, trial_rec, session_results


@dataclass(frozen=True)
class StepR3CensusResult:
    """Complete Step R3 output bundle containing all K=4 summaries, trial ledger, and manifest."""
    k_declared: int
    k_executed: int
    k_reported: int
    summaries: Tuple[OrbCellSummary, ...]
    ledger: SearchTrialLedger
    manifest_data: Dict[str, Any]
    all_session_results: Mapping[str, List[OrbSessionResult]]


def execute_step_r3_census(repo_root: Optional[Path] = None) -> StepR3CensusResult:
    """Execute complete Step R3 empirical census across all 4 primary ORB cells."""
    root = repo_root or Path(".")

    # 1. Verify Upstream Governance Preconditions
    preconditions = validate_r3_preconditions(root)
    parquet_path = Path(preconditions["parquet_path"])

    # 2. Load and Validate Canonical R2 In-Sample Dataset
    sessions = load_and_validate_canonical_r2_dataset(parquet_path)

    # 3. Execute Exact K=4 Census
    summaries: List[OrbCellSummary] = []
    trials: List[SearchTrialRecord] = []
    all_session_results: Dict[str, List[OrbSessionResult]] = {}

    for cell_cfg in PRIMARY_ORB_CELLS:
        summary, trial_rec, session_res = execute_cell_census(cell_cfg, sessions)
        summaries.append(summary)
        trials.append(trial_rec)
        all_session_results[cell_cfg.cell_id] = session_res

    # 4. Assemble Sealed SearchTrialLedger
    unsealed_ledger = SearchTrialLedger(
        ledger_id="search_trial_ledger_HYP_003",
        strategy_id="HYP_003_ORB_PRICE_ONLY",
        hypothesis_id="HYP_003",
        trials=tuple(trials),
        sharpe_space=SharpeSpace.ANNUAL,
        is_sealed=False,
    )
    ledger_digest = unsealed_ledger.compute_ledger_digest()
    sealed_ledger = SearchTrialLedger(
        ledger_id="search_trial_ledger_HYP_003",
        strategy_id="HYP_003_ORB_PRICE_ONLY",
        hypothesis_id="HYP_003",
        trials=tuple(trials),
        sharpe_space=SharpeSpace.ANNUAL,
        is_sealed=True,
        sealed_at_utc=datetime.now(timezone.utc).isoformat(),
        sealed_by_owner="OPERATOR_HUMAN_AUTHORITY_STEP_R3",
        ledger_digest=ledger_digest,
    )

    # 5. Assemble Durable Manifest
    cells_manifest = []
    for s in summaries:
        cells_manifest.append({
            "cell_id": s.cell_id,
            "window_minutes": s.window_minutes,
            "direction": s.direction,
            "eligible_sessions": s.eligible_session_count,
            "signal_count": s.signal_count,
            "trade_count": s.trade_count,
            "no_signal_sessions": s.no_signal_session_count,
            "stop_exits": s.stop_exit_count,
            "eod_exits": s.eod_exit_count,
            "gross_cumulative_return": str(s.gross_cumulative_return),
            "net_cumulative_return": str(s.net_cumulative_return),
            "mean_trade_return": str(s.mean_trade_return),
            "median_trade_return": str(s.median_trade_return),
            "win_count": s.win_count,
            "loss_count": s.loss_count,
            "win_rate": str(s.win_rate),
            "max_drawdown": str(s.max_drawdown),
            "annualized_sharpe_daily": str(s.annualized_sharpe_daily),
            "canonical_p_value": str(s.canonical_p_value),
            "p_value_input_hash": s.p_value_input_hash,
            "return_series_sha256": s.in_sample_return_series_sha256,
            "config_sha256": s.config_sha256,
        })

    code_path = root / "src/acash/research/step_r3_hyp_003.py"
    execution_code_hash = hashlib.sha256(code_path.read_bytes()).hexdigest() if code_path.exists() else ""

    manifest_data: Dict[str, Any] = {
        "manifest_type": "IN_SAMPLE_CENSUS_MANIFEST",
        "hypothesis_id": "HYP_003",
        "hypothesis_ordinal": 3,
        "mechanism_id": "MEC-0013",
        "hypothesis_sha256": preconditions["hypothesis_sha256"],
        "preregistration_sha256": preconditions["preregistration_sha256"],
        "r1_manifest_sha256": preconditions["r1_manifest_sha256"],
        "semantic_clarification_record_sha256": preconditions["clarification_sha256"],
        "r2_manifest_sha256": preconditions["r2_manifest_sha256"],
        "canonical_dataset_sha256": EXPECTED_CANONICAL_DATASET_SHA256,
        "source_git_sha": "e3b8a900a88dea3d8d28ffb339011cd09796ea0c",
        "execution_code_hash": execution_code_hash,
        "census_intensity": {
            "k_declared": 4,
            "k_executed": 4,
            "k_reported": 4,
        },
        "friction_model": {
            "transaction_cost_round_trip_bps": "1.6",
            "slippage_adverse_per_side_bps": "0.5",
        },
        "temporal_partitions": {
            "in_sample_window_utc": ["2017-01-01T00:00:00Z", "2022-12-31T23:59:59Z"],
            "out_of_sample_state": "SEALED_UNREAD",
            "out_of_sample_boundary": ">= 2023-01-01T00:00:00Z (STRICTLY FORBIDDEN)",
        },
        "primary_cells": cells_manifest,
        "ledger_digest": ledger_digest,
        "results_hash": ledger_digest,
        "status": "STEP_R3_IN_SAMPLE_CENSUS_COMPLETE_PASS",
        "next_required_step": "STEP_R4_VALIDATION_OR_OOS_DECISION_LOCKED",
        "capital_authority_usd": "0.00",
        "paper_authorized": False,
        "live_authorized": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    return StepR3CensusResult(
        k_declared=4,
        k_executed=4,
        k_reported=4,
        summaries=tuple(summaries),
        ledger=sealed_ledger,
        manifest_data=manifest_data,
        all_session_results=all_session_results,
    )
