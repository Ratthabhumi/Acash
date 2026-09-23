"""HYP_007 Step R4 Post-Hoc Descriptive Failure Decomposition (M1 vs M2).

Authority:
- AUTHORIZE_HYP_007_POST_R4_CLOSURE_AND_CONDITIONAL_HYP_008_RESEARCH_INCEPTION
- Classification: POST_HOC_DESCRIPTIVE_FAILURE_ANALYSIS (NOT confirmatory hypothesis testing)
- Canonical Head: 653b007e4d5ce73c5022086f40737a4525410a55

Strictly Enforces:
- Reads ONLY sealed exposed evidence (M1 / M2 ledgers, quotes, bars). NEVER reads M3 or the
  quarantine gap [2026-08-15, 2026-09-23).
- Every statistic is a pure, deterministic function of sealed inputs (no hidden optimization,
  no random seeds, no M2-aware threshold selection).
- Volatility-state cutoffs are fixed quantiles derived from the DECLARED exposed reference
  sample (M1 registered replication), then applied identically to M1 and M2.
- No confirmatory claim is possible from this module: it reports descriptive differences only.

All amounts are Decimal; all output dicts are JSON-serializable deterministic structures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Sequence, Tuple, cast

import pyarrow.parquet as pq

from acash.core.domain.exceptions import DataContractError

# ---------------------------------------------------------------------------
# Exposed Sample Authority
# ---------------------------------------------------------------------------

M1_FIRST_SESSION: date = date(2021, 7, 1)
M1_LAST_SESSION: date = date(2024, 4, 30)
M2_FIRST_SESSION: date = date(2024, 5, 1)
M2_LAST_SESSION: date = date(2026, 8, 14)

EXPOSED_REFERENCE_SAMPLE: str = "M1_REGISTERED_REPLICATION"
VOLATILITY_STATE_QUANTILES: Tuple[float, float] = (1.0 / 3.0, 2.0 / 3.0)
VOLATILITY_STATE_LABELS: Tuple[str, str, str] = ("LOW", "MEDIUM", "HIGH")

DECISION_EPOCHS_ET: Tuple[str, ...] = (
    "10:00:00",
    "10:30:00",
    "11:00:00",
    "11:30:00",
    "12:00:00",
    "12:30:00",
    "13:00:00",
    "13:30:00",
    "14:00:00",
    "14:30:00",
    "15:00:00",
    "15:30:00",
)

FRICTION_COMPONENTS: Tuple[str, ...] = (
    "commission",
    "sec31_fee",
    "finra_taf",
    "standalone_slippage",
    "stress_half_spread",
    "stress_borrow_fee",
)


@dataclass(frozen=True)
class EdgeComparison:
    """Gross vs net edge and per-trade expectancy for one sample."""

    sample: str
    trades_count: int
    gross_pnl: Decimal
    total_friction: Decimal
    net_pnl: Decimal
    gross_expectancy_per_trade: Decimal
    net_expectancy_per_trade: Decimal
    friction_per_trade: Decimal
    friction_gross_ratio: Decimal
    gross_made_net_negative_trades: int
    trades_profitable_net: int
    win_rate_net: Decimal


def _dec(value: Any) -> Decimal:
    return Decimal(str(value))


def _statistic_aggregate(records: Sequence[Dict[str, Any]], numeric_fields: Sequence[str]) -> Dict[str, Decimal]:
    totals = {name: Decimal("0") for name in numeric_fields}
    for rec in records:
        for name in numeric_fields:
            totals[name] += _dec(rec[name])
    return totals


def compute_edge_comparison(
    sample: str,
    trades_records: Sequence[Dict[str, Any]],
) -> EdgeComparison:
    """Compute gross/net edge and per-trade expectancy from a sealed trade ledger."""
    if not trades_records:
        return EdgeComparison(
            sample=sample,
            trades_count=0,
            gross_pnl=Decimal("0"),
            total_friction=Decimal("0"),
            net_pnl=Decimal("0"),
            gross_expectancy_per_trade=Decimal("0"),
            net_expectancy_per_trade=Decimal("0"),
            friction_per_trade=Decimal("0"),
            friction_gross_ratio=Decimal("0"),
            gross_made_net_negative_trades=0,
            trades_profitable_net=0,
            win_rate_net=Decimal("0"),
        )

    gross = Decimal("0")
    friction = Decimal("0")
    net = Decimal("0")
    flipped_negative = 0
    net_positive = 0
    for rec in trades_records:
        g = _dec(rec["gross_pnl"])
        f = _dec(rec["total_friction"])
        n_i = _dec(rec["net_pnl"])
        gross += g
        friction += f
        net += n_i
        if g > Decimal("0") and n_i <= Decimal("0"):
            flipped_negative += 1
        if n_i > Decimal("0"):
            net_positive += 1

    n = len(trades_records)
    gross_exp = gross / Decimal(n)
    net_exp = net / Decimal(n)
    frict_per_trade = friction / Decimal(n)
    ratio = (friction / gross) if gross != Decimal("0") else Decimal("0")
    win_rate = (Decimal(net_positive) / Decimal(n)).quantize(Decimal("0.000001"))

    return EdgeComparison(
        sample=sample,
        trades_count=n,
        gross_pnl=gross,
        total_friction=friction,
        net_pnl=net,
        gross_expectancy_per_trade=gross_exp,
        net_expectancy_per_trade=net_exp,
        friction_per_trade=frict_per_trade,
        friction_gross_ratio=ratio,
        gross_made_net_negative_trades=flipped_negative,
        trades_profitable_net=net_positive,
        win_rate_net=win_rate,
    )


def friction_burden_profile(
    sample: str,
    exec_legs: Sequence[Dict[str, Any]],
    trades_count: int,
    gross_pnl: Decimal,
    executed_notional: Decimal,
    starting_aum: Decimal,
    path_prefix: str,
) -> Dict[str, Any]:
    """Sum each friction component for a given execution path (BASELINE or STRESS)."""
    totals = {name: Decimal("0") for name in FRICTION_COMPONENTS}
    tot_friction = Decimal("0")
    for leg in exec_legs:
        if leg.get("path") != path_prefix:
            continue
        for name in FRICTION_COMPONENTS:
            totals[name] += _dec(leg.get(name, Decimal("0")))
        tot_friction += _dec(leg["total_friction"])

    profile: Dict[str, Any] = {
        "sample": sample,
        "path": path_prefix,
        "legs_count": sum(1 for leg in exec_legs if leg.get("path") == path_prefix),
        "total_friction": str(tot_friction),
    }
    for name in FRICTION_COMPONENTS:
        profile[name] = str(totals[name])
        profile[f"{name}_pct_of_total"] = (
            str(totals[name] / tot_friction) if tot_friction != Decimal("0") else "0"
        )

    profile["friction_per_trade"] = str(tot_friction / Decimal(trades_count)) if trades_count else "0"
    profile["friction_gross_pnl_ratio"] = str(tot_friction / gross_pnl) if gross_pnl != Decimal("0") else "0"
    profile["friction_pct_of_aum"] = str(tot_friction / starting_aum) if starting_aum != Decimal("0") else "0"
    profile["friction_bps_of_notional"] = (
        str((tot_friction / executed_notional) * Decimal("10000")) if executed_notional != Decimal("0") else "0"
    )
    return profile


def long_short_asymmetry(trades_records: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Per-direction gross/net expectancy, counts, and P&L contribution."""
    sides: Dict[str, List[Dict[str, Any]]] = {"LONG": [], "SHORT": []}
    for rec in trades_records:
        d = str(rec["direction"])
        if d in sides:
            sides[d].append(rec)

    out: Dict[str, Dict[str, str]] = {}
    for side, recs in sides.items():
        if not recs:
            out[side] = {
                "count": "0",
                "gross_pnl": "0",
                "net_pnl": "0",
                "gross_expectancy": "0",
                "net_expectancy": "0",
                "friction": "0",
                "win_rate_net": "0",
            }
            continue
        gross = sum((_dec(r["gross_pnl"]) for r in recs), Decimal("0"))
        friction = sum((_dec(r["total_friction"]) for r in recs), Decimal("0"))
        net = sum((_dec(r["net_pnl"]) for r in recs), Decimal("0"))
        positive = sum(1 for r in recs if _dec(r["net_pnl"]) > Decimal("0"))
        out[side] = {
            "count": str(len(recs)),
            "gross_pnl": str(gross),
            "net_pnl": str(net),
            "gross_expectancy": str(gross / Decimal(len(recs))),
            "net_expectancy": str(net / Decimal(len(recs))),
            "friction": str(friction),
            "win_rate_net": str((Decimal(positive) / Decimal(len(recs))).quantize(Decimal("0.000001"))),
        }
    return out


def time_of_day_decomposition(
    sample: str,
    trades_records: Sequence[Dict[str, Any]],
    signal_records: Sequence[Dict[str, Any]],
) -> Dict[str, Dict[str, str]]:
    """Per-epoch contribution split by frozen 12 decision epochs."""
    epoch_rows: Dict[str, List[Dict[str, Any]]] = {ep: [] for ep in DECISION_EPOCHS_ET}
    for rec in trades_records:
        ep = str(rec["entry_epoch_et"])
        if ep in epoch_rows:
            epoch_rows[ep].append(rec)

    out: Dict[str, Dict[str, str]] = {}
    total_trades = len(trades_records)
    for ep in DECISION_EPOCHS_ET:
        recs = epoch_rows[ep]
        if not recs:
            out[ep] = {
                "signal_count": "0",
                "trade_count": "0",
                "gross_pnl": "0",
                "net_pnl": "0",
                "avg_trade_return": "0",
                "win_rate_net": "0",
                "share_of_total_trades": "0",
            }
            continue
        gross = sum((_dec(r["gross_pnl"]) for r in recs), Decimal("0"))
        net = sum((_dec(r["net_pnl"]) for r in recs), Decimal("0"))
        avg_ret = (net / Decimal(total_trades)) if total_trades else Decimal("0")
        positive = sum(1 for r in recs if _dec(r["net_pnl"]) > Decimal("0"))
        signals = sum(1 for s in signal_records if str(s["decision_epoch_et"]) == ep)
        out[ep] = {
            "signal_count": str(signals),
            "trade_count": str(len(recs)),
            "gross_pnl": str(gross),
            "net_pnl": str(net),
            "avg_trade_return": str(avg_ret),
            "win_rate_net": str((Decimal(positive) / Decimal(len(recs))).quantize(Decimal("0.000001"))),
            "share_of_total_trades": str((Decimal(len(recs)) / Decimal(total_trades)).quantize(Decimal("0.000001"))),
        }
    return out


def subperiod_stability(
    sample: str,
    daily_perf_records: Sequence[Dict[str, Any]],
    trades_records: Sequence[Dict[str, Any]],
) -> Dict[str, Dict[str, str]]:
    """Calendar-year fixed partitions for descriptive stability diagnosis."""
    from collections import defaultdict

    year_trades: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for rec in trades_records:
        year_trades[date.fromisoformat(str(rec["session_date"])).year].append(rec)

    year_perf: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for rec in daily_perf_records:
        if not rec.get("strategy_eligible", True):
            continue
        year_perf[date.fromisoformat(str(rec["session_date"])).year].append(rec)

    out: Dict[str, Dict[str, str]] = {}
    all_years = sorted(set(year_trades.keys()) | set(year_perf.keys()))
    for year in all_years:
        perf_recs = year_perf.get(year, [])
        t_recs = year_trades.get(year, [])
        returns = [_dec(r["baseline_daily_return"]) for r in perf_recs if r.get("baseline_daily_return") is not None]
        gross = sum((_dec(r["gross_pnl"]) for r in t_recs), Decimal("0"))
        net = sum((_dec(r["net_pnl"]) for r in t_recs), Decimal("0"))
        out[str(year)] = {
            "trades_count": str(len(t_recs)),
            "gross_pnl": str(gross),
            "net_pnl": str(net),
            "net_expectancy": str(net / Decimal(len(t_recs))) if t_recs else "0",
            "total_return_summary": _subperiod_return(returns),
        }
    return out


def _subperiod_return(returns: Sequence[Decimal]) -> str:
    if not returns:
        return "0"
    product = Decimal("1")
    for r in returns:
        product *= (Decimal("1") + r)
    return str(product - Decimal("1"))


def volatility_state_diagnosis(
    m1_daily_perf: Sequence[Dict[str, Any]],
    m2_daily_perf: Sequence[Dict[str, Any]],
    m1_trades: Sequence[Dict[str, Any]],
    m2_trades: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Ex-ante volatility state (prior-15-day realized vol) terciles from M1 reference sample.

    Cutoffs are fixed quantiles of the M1 registered replication (declared exposed reference).
    The identical cutoffs are then applied to M1 and M2 for descriptive comparison.
    """
    m1_vols = sorted(_dec(r["realized_vol_15d"]) for r in m1_daily_perf if r.get("realized_vol_15d") is not None)
    if len(m1_vols) < 3:
        raise DataContractError("M1 reference sample too small for volatility terciles.")

    def quantile(sorted_vals: Sequence[Decimal], q: float) -> Decimal:
        idx = q * (len(sorted_vals) - 1)
        lo = int(idx)
        hi = min(lo + 1, len(sorted_vals) - 1)
        frac = idx - lo
        return sorted_vals[lo] * (Decimal("1") - Decimal(str(frac))) + sorted_vals[hi] * Decimal(str(frac))

    low_cut = quantile(m1_vols, VOLATILITY_STATE_QUANTILES[0])
    high_cut = quantile(m1_vols, VOLATILITY_STATE_QUANTILES[1])

    def classify(
        sample: str,
        perf_recs: Sequence[Dict[str, Any]],
        trades: Sequence[Dict[str, Any]],
    ) -> Dict[str, Dict[str, str]]:
        state_rows: Dict[str, List[Dict[str, Any]]] = {"LOW": [], "MEDIUM": [], "HIGH": []}
        by_session = {str(r["session_date"]): _dec(r["realized_vol_15d"]) for r in perf_recs}
        for t in trades:
            sd = str(t["session_date"])
            vol = by_session.get(sd)
            if vol is None:
                continue
            if vol <= low_cut:
                state = "LOW"
            elif vol >= high_cut:
                state = "HIGH"
            else:
                state = "MEDIUM"
            state_rows[state].append(t)

        out = {}
        for st, recs in state_rows.items():
            if not recs:
                out[st] = {"count": "0", "gross_pnl": "0", "net_pnl": "0", "net_expectancy": "0",
                           "friction": "0", "win_rate_net": "0"}
                continue
            gross = sum((_dec(r["gross_pnl"]) for r in recs), Decimal("0"))
            friction = sum((_dec(r["total_friction"]) for r in recs), Decimal("0"))
            net = sum((_dec(r["net_pnl"]) for r in recs), Decimal("0"))
            positive = sum(1 for r in recs if _dec(r["net_pnl"]) > Decimal("0"))
            out[st] = {
                "count": str(len(recs)),
                "gross_pnl": str(gross),
                "net_pnl": str(net),
                "net_expectancy": str(net / Decimal(len(recs))),
                "friction": str(friction),
                "win_rate_net": str((Decimal(positive) / Decimal(len(recs))).quantize(Decimal("0.000001"))),
            }
        return out

    return {
        "reference_sample": EXPOSED_REFERENCE_SAMPLE,
        "cutoffs_source": "fixed_quantiles_over_M1",
        "low_cutoff_realized_vol_15d": str(low_cut),
        "high_cutoff_realized_vol_15d": str(high_cut),
        "M1": classify("M1", m1_daily_perf, m1_trades),
        "M2": classify("M2", m2_daily_perf, m2_trades),
    }


def liquidity_spread_diagnosis(
    m1_quotes: Sequence[Dict[str, Any]],
    m2_quotes: Sequence[Dict[str, Any]],
) -> Dict[str, Dict[str, str]]:
    """Descriptive observed NBBO spread and quote-quality comparison at decision boundaries."""
    out: Dict[str, Dict[str, str]] = {}
    for label, quotes in (("M1", m1_quotes), ("M2", m2_quotes)):
        if not quotes:
            out[label] = {"count": "0"}
            continue
        half_spreads = []
        quoted_sizes = []
        locked_count = 0
        crossed_count = 0
        for q in quotes:
            bid = _dec(q["bid_price"])
            ask = _dec(q["ask_price"])
            if ask > bid:
                half_spreads.append((ask - bid) / Decimal("2"))
            quoted_sizes.append(_dec(q.get("bid_size", 0)) + _dec(q.get("ask_size", 0)))
            if q.get("is_locked"):
                locked_count += 1
            if q.get("is_crossed"):
                crossed_count += 1

        spread_sum = sum((s for s in half_spreads), Decimal("0"))
        avg_half = spread_sum / Decimal(len(half_spreads)) if half_spreads else Decimal("0")
        size_sum = sum((s for s in quoted_sizes), Decimal("0"))
        out[label] = {
            "count": str(len(quotes)),
            "avg_half_spread_usd": str(avg_half),
            "pct_locked": str((Decimal(locked_count) / Decimal(len(quotes))).quantize(Decimal("0.000001"))),
            "pct_crossed": str((Decimal(crossed_count) / Decimal(len(quotes))).quantize(Decimal("0.000001"))),
            "avg_quoted_size": str((size_sum / Decimal(len(quotes))).quantize(Decimal("0.000001"))),
        }
    return out


def volume_regime_diagnosis(
    m1_bars: Sequence[Dict[str, Any]],
    m2_bars: Sequence[Dict[str, Any]],
) -> Dict[str, Dict[str, str]]:
    """Prior-day (ex-ante) volume distribution per 1-min sip bar for M1 vs M2."""
    out: Dict[str, Dict[str, str]] = {}
    for label, bars in (("M1", m1_bars), ("M2", m2_bars)):
        if not bars:
            out[label] = {"count": "0"}
            continue
        vols = sorted(_dec(r["volume"]) for r in bars if r.get("volume") is not None)
        n = len(vols)
        median = vols[n // 2] if n % 2 == 1 else (vols[n // 2 - 1] + vols[n // 2]) / Decimal("2")
        mean = sum(vols) / Decimal(n)
        out[label] = {
            "bar_count": str(n),
            "median_volume_per_bar": str(median),
            "mean_volume_per_bar": str(mean),
            "p90_volume": str(vols[min(n - 1, int(0.9 * (n - 1)))]),
            "p10_volume": str(vols[int(0.1 * (n - 1))]),
        }
    return out


def _read_pylist(path: str) -> List[Dict[str, Any]]:
    """Read a sealed parquet ledger into a deterministic list of plain dicts."""
    return cast(List[Dict[str, Any]], pq.read_table(path).to_pylist())


def load_trades(repo_root: str, sample: str) -> List[Dict[str, Any]]:
    if sample == "M1":
        path = f"{repo_root}/data/hyp_007/m1_trade_ledger.parquet"
    elif sample == "M2":
        path = f"{repo_root}/data/hyp_007/m2/m2_trade_ledger.parquet"
    else:
        raise DataContractError(f"Unknown sample {sample}")
    return _read_pylist(path)


def load_execution_legs(repo_root: str, sample: str) -> List[Dict[str, Any]]:
    if sample == "M1":
        base = f"{repo_root}/data/hyp_007/m1_baseline_execution_ledger.parquet"
        stress = f"{repo_root}/data/hyp_007/m1_stress_execution_ledger.parquet"
    elif sample == "M2":
        base = f"{repo_root}/data/hyp_007/m2/m2_baseline_execution_ledger.parquet"
        stress = f"{repo_root}/data/hyp_007/m2/m2_stress_execution_ledger.parquet"
    else:
        raise DataContractError(f"Unknown sample {sample}")
    return _read_pylist(base) + _read_pylist(stress)


def load_daily_performance(repo_root: str, sample: str) -> List[Dict[str, Any]]:
    if sample == "M1":
        path = f"{repo_root}/data/hyp_007/m1_daily_performance.parquet"
    elif sample == "M2":
        path = f"{repo_root}/data/hyp_007/m2/m2_daily_performance.parquet"
    else:
        raise DataContractError(f"Unknown sample {sample}")
    return _read_pylist(path)


def load_signals(repo_root: str, sample: str) -> List[Dict[str, Any]]:
    if sample == "M1":
        path = f"{repo_root}/data/hyp_007/m1_signal_ledger.parquet"
    elif sample == "M2":
        path = f"{repo_root}/data/hyp_007/m2/m2_signal_ledger.parquet"
    else:
        raise DataContractError(f"Unknown sample {sample}")
    return _read_pylist(path)


def load_quotes(repo_root: str, sample: str) -> List[Dict[str, Any]]:
    if sample == "M1":
        path = f"{repo_root}/data/hyp_007/m1_execution_quotes_qualified.parquet"
    elif sample == "M2":
        path = f"{repo_root}/data/hyp_007/m2/m2_execution_quotes_qualified.parquet"
    else:
        raise DataContractError(f"Unknown sample {sample}")
    return _read_pylist(path)


def load_bars(repo_root: str, sample: str) -> List[Dict[str, Any]]:
    if sample == "M1":
        path = f"{repo_root}/data/hyp_007/m1_bars_qualified.parquet"
    elif sample == "M2":
        path = f"{repo_root}/data/hyp_007/m2/m2_bars_qualified.parquet"
    else:
        raise DataContractError(f"Unknown sample {sample}")
    return _read_pylist(path)


def executed_notional(exec_legs: Sequence[Dict[str, Any]], path_prefix: str) -> Decimal:
    total = Decimal("0")
    for leg in exec_legs:
        if leg.get("path") != path_prefix:
            continue
        total += _dec(leg["fill_price"]) * _dec(leg["shares"])
    return total


def run_failure_decomposition(repo_root: str) -> Dict[str, Any]:
    """Deterministic descriptive decomposition over sealed M1 and M2 evidence."""
    m1_trades = load_trades(repo_root, "M1")
    m2_trades = load_trades(repo_root, "M2")
    m1_legs = load_execution_legs(repo_root, "M1")
    m2_legs = load_execution_legs(repo_root, "M2")
    m1_daily = load_daily_performance(repo_root, "M1")
    m2_daily = load_daily_performance(repo_root, "M2")
    m1_signals = load_signals(repo_root, "M1")
    m2_signals = load_signals(repo_root, "M2")
    m1_quotes = load_quotes(repo_root, "M1")
    m2_quotes = load_quotes(repo_root, "M2")
    m1_bars = load_bars(repo_root, "M1")
    m2_bars = load_bars(repo_root, "M2")

    base_aum = Decimal("100000.00")

    edge_m1 = compute_edge_comparison("M1", m1_trades)
    edge_m2 = compute_edge_comparison("M2", m2_trades)

    notional_m1_base = executed_notional(m1_legs, "BASELINE")
    notional_m2_base = executed_notional(m2_legs, "BASELINE")
    notional_m1_stress = executed_notional(m1_legs, "STRESS")
    notional_m2_stress = executed_notional(m2_legs, "STRESS")

    friction_m1_base = friction_burden_profile("M1", m1_legs, edge_m1.trades_count, edge_m1.gross_pnl, notional_m1_base, base_aum, "BASELINE")
    friction_m2_base = friction_burden_profile("M2", m2_legs, edge_m2.trades_count, edge_m2.gross_pnl, notional_m2_base, base_aum, "BASELINE")
    friction_m1_stress = friction_burden_profile("M1", m1_legs, edge_m1.trades_count, edge_m1.gross_pnl, notional_m1_stress, base_aum, "STRESS")
    friction_m2_stress = friction_burden_profile("M2", m2_legs, edge_m2.trades_count, edge_m2.gross_pnl, notional_m2_stress, base_aum, "STRESS")

    gross_edge_degradation: Decimal
    if edge_m1.gross_expectancy_per_trade != Decimal("0"):
        gross_edge_degradation = (
            (edge_m1.gross_expectancy_per_trade - edge_m2.gross_expectancy_per_trade)
            / abs(edge_m1.gross_expectancy_per_trade)
        ).quantize(Decimal("0.0001"))
    else:
        gross_edge_degradation = Decimal("0")

    def _stringify_decimals(mapping: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, v in mapping.items():
            out[k] = str(v) if isinstance(v, Decimal) else v
        return out

    return {
        "decomposition_classification": "POST_HOC_DESCRIPTIVE_FAILURE_ANALYSIS",
        "authorization": "AUTHORIZE_HYP_007_POST_R4_CLOSURE_AND_CONDITIONAL_HYP_008_RESEARCH_INCEPTION",
        "canonical_head": "653b007e4d5ce73c5022086f40737a4525410a55",
        "m3_accessed": False,
        "quarantine_gap_accessed": False,
        "samples": {
            "M1": {
                "sessions": len([r for r in m1_daily if r.get("strategy_eligible", True)]),
                "starting_aum_usd": str(base_aum),
                **_stringify_decimals(edge_m1.__dict__),
            },
            "M2": {
                "sessions": len([r for r in m2_daily if r.get("strategy_eligible", True)]),
                "starting_aum_usd": str(base_aum),
                **_stringify_decimals(edge_m2.__dict__),
            },
        },
        "gross_edge_degradation_fraction_baseline_norm": str(gross_edge_degradation),
        "friction": {
            "M1_BASELINE": friction_m1_base,
            "M2_BASELINE": friction_m2_base,
            "M1_STRESS": friction_m1_stress,
            "M2_STRESS": friction_m2_stress,
        },
        "long_short": {
            "M1": long_short_asymmetry(m1_trades),
            "M2": long_short_asymmetry(m2_trades),
        },
        "time_of_day": {
            "M1": time_of_day_decomposition("M1", m1_trades, m1_signals),
            "M2": time_of_day_decomposition("M2", m2_trades, m2_signals),
        },
        "subperiod": {
            "M1": subperiod_stability("M1", m1_daily, m1_trades),
            "M2": subperiod_stability("M2", m2_daily, m2_trades),
        },
        "volatility_state": volatility_state_diagnosis(m1_daily, m2_daily, m1_trades, m2_trades),
        "liquidity": liquidity_spread_diagnosis(m1_quotes, m2_quotes),
        "volume": volume_regime_diagnosis(m1_bars, m2_bars),
    }