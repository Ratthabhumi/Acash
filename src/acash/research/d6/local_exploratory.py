"""LOCAL_EXPLORATORY D6 mode: owner-supplied CSV files -> validation -> D6 -> report.

Single-user, noncommercial, retrospective research. Results are never D5-admitted,
never PIT-verified and never feed the Verified Research gates; corporate actions are
whatever the owner supplied and are unverified. Accounting is ``run_d6_portfolio``
unchanged, so causal timing, the negative-cash guard and cash reconstruction apply.

Input files (UTF-8 CSV, header row required):

- bars: ``symbol,session,open,close,adjustment`` with ``adjustment`` = ``raw``.
- distributions (optional): ``symbol,ex_date,payable_date,gross_amount[,distribution_type]``;
  ``gross_amount`` is per share as of the ex-date, not restated for later splits.
- splits (optional): ``symbol,session,ratio`` (new shares per old share).

Sessions come from ``NyseCa1Calendar`` (2013-2026; other years raise). A bar on a
non-session is rejected; every official session in the window is required for every
symbol a portfolio holds. A portfolio with any gap is NOT_RUN and its missing inputs
are listed.
"""

from __future__ import annotations

import csv
import hashlib
import io
import statistics
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.contracts.corporate_action_ledger import parse_distribution_rows
from acash.data.contracts.etf_fx_benchmark import EtfDistributionRecord
from acash.research.d6.accounting import (
    D6_INITIAL_NAV,
    D6_REGISTERED_PORTFOLIOS,
    D6_TIMING_PRIMARY,
    ZERO,
    D6CostModel,
    D6Portfolio,
    D6Result,
    run_d6_portfolio,
)
from acash.research.hyp_009.accounting import max_drawdown

LOCAL_EXPLORATORY_LABEL = "LOCAL_EXPLORATORY"
LOCAL_LIMITATIONS: Tuple[str, ...] = (
    "RETROSPECTIVE_DATA_NOT_PIT_VERIFIED",
    "NOT_D5_ADMITTED",
    "CORPORATE_ACTIONS_UNVERIFIED",
    "ANNUALIZATION_252_SESSION_CONVENTION",
)
_CALENDAR = NyseCa1Calendar()
BAR_COLUMNS = ("symbol", "session", "open", "close", "adjustment")
DISTRIBUTION_COLUMNS = ("symbol", "ex_date", "payable_date", "gross_amount")
SPLIT_COLUMNS = ("symbol", "session", "ratio")
# Close-to-next-open move beyond this factor without a split row is flagged, not corrected.
SPLIT_SUSPECT_FACTOR = Decimal("1.5")


@dataclass(frozen=True)
class LocalInputs:
    sessions: Tuple[date, ...]
    opens: Mapping[str, Mapping[date, Decimal]]
    closes: Mapping[str, Mapping[date, Decimal]]
    dividends: Mapping[str, Sequence[EtfDistributionRecord]]
    splits: Mapping[str, Mapping[date, Decimal]]
    file_sha256: Mapping[str, str]
    imputed_payable: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class LocalOutcome:
    portfolio: str
    status: str
    result: Optional[D6Result]
    metrics: Optional[Mapping[str, Decimal]]
    missing: Tuple[str, ...]


def _read_csv(path: Path, required: Sequence[str]) -> Tuple[List[Dict[str, str]], str]:
    payload = path.read_bytes()
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DataContractError(f"LOCAL_CSV_NOT_UTF8: {path.name}.") from exc
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in required if c not in (reader.fieldnames or ())]
    if missing:
        raise DataContractError(f"LOCAL_CSV_COLUMNS_MISSING: {path.name} {missing}.")
    return list(reader), hashlib.sha256(payload).hexdigest()


def _symbol(row: Mapping[str, str], where: str) -> str:
    sym = row["symbol"].strip().upper()
    if not sym:
        raise DataContractError(f"LOCAL_EMPTY_SYMBOL: {where}.")
    return sym


def _positive(raw: str, where: str) -> Decimal:
    try:
        value = Decimal(raw.strip())
    except InvalidOperation as exc:
        raise DataContractError(f"LOCAL_UNPARSEABLE_NUMBER: {where} {raw!r}.") from exc
    if not value.is_finite() or value <= ZERO:
        raise DataContractError(f"LOCAL_NONPOSITIVE_OR_NONFINITE: {where} {raw!r}.")
    return value


def _session(raw: str, where: str) -> date:
    try:
        return date.fromisoformat(raw.strip())
    except ValueError as exc:
        raise DataContractError(f"LOCAL_BAD_DATE: {where} {raw!r}.") from exc


def load_local_inputs(
    bars_csv: Path, distributions_csv: Optional[Path] = None, splits_csv: Optional[Path] = None
) -> LocalInputs:
    rows, digest = _read_csv(bars_csv, BAR_COLUMNS)
    digests = {bars_csv.name: digest}
    opens: Dict[str, Dict[date, Decimal]] = {}
    closes: Dict[str, Dict[date, Decimal]] = {}
    for index, row in enumerate(rows, start=2):
        where = f"{bars_csv.name}:{index}"
        if row["adjustment"].strip().lower() != "raw":
            raise DataContractError(f"LOCAL_ADJUSTED_BARS_REJECTED: {where}; D6 requires raw prices.")
        sym = _symbol(row, where)
        session = _session(row["session"], where)
        if not _CALENDAR.is_trading_session(session):
            raise DataContractError(f"LOCAL_BAR_ON_NON_SESSION: {sym} {session}.")
        if session in opens.setdefault(sym, {}):
            raise DataContractError(f"LOCAL_DUPLICATE_BAR: {sym} {session}.")
        opens[sym][session] = _positive(row["open"], where)
        closes.setdefault(sym, {})[session] = _positive(row["close"], where)
    if not opens:
        raise DataContractError(f"LOCAL_NO_BARS: {bars_csv.name}.")
    sessions = tuple(sorted({s for by_session in opens.values() for s in by_session}))

    splits: Dict[str, Dict[date, Decimal]] = {}
    if splits_csv is not None:
        split_rows, digests[splits_csv.name] = _read_csv(splits_csv, SPLIT_COLUMNS)
        for index, row in enumerate(split_rows, start=2):
            where = f"{splits_csv.name}:{index}"
            sym = _symbol(row, where)
            session = _session(row["session"], where)
            if session in splits.setdefault(sym, {}):
                raise DataContractError(f"LOCAL_DUPLICATE_SPLIT: {sym} {session}.")
            if session not in opens.get(sym, {}):
                raise DataContractError(f"LOCAL_SPLIT_NOT_ON_A_BAR_SESSION: {sym} {session}.")
            splits[sym][session] = _positive(row["ratio"], where)

    dividends: Dict[str, List[EtfDistributionRecord]] = {}
    imputed: Dict[str, int] = {}
    if distributions_csv is not None:
        dist_rows, digests[distributions_csv.name] = _read_csv(distributions_csv, DISTRIBUTION_COLUMNS)
        grouped: Dict[str, List[Dict[str, str]]] = {}
        for index, row in enumerate(dist_rows, start=2):
            sym = _symbol(row, f"{distributions_csv.name}:{index}")
            grouped.setdefault(sym, []).append(row)
            if (row.get("payable_date_source") or "").startswith("IMPUTED"):
                imputed[sym] = imputed.get(sym, 0) + 1
        for sym, sym_rows in sorted(grouped.items()):
            records = parse_distribution_rows(sym_rows, symbol=sym, source_ref=distributions_csv.name)
            # An ex-date that is not a bar session would be silently skipped by the engine.
            have = opens.get(sym, {})
            for record in records:
                if have and min(have) <= record.ex_date <= max(have) and record.ex_date not in have:
                    raise DataContractError(f"LOCAL_EX_DATE_NOT_A_BAR_SESSION: {sym} {record.ex_date}.")
            dividends[sym] = records

    return LocalInputs(sessions, opens, closes, dividends, splits, digests, imputed)


def official_sessions(start: date, end: date) -> Tuple[date, ...]:
    days = (start + timedelta(days=n) for n in range((end - start).days + 1))
    return tuple(d for d in days if _CALENDAR.is_trading_session(d))


def coverage(inputs: LocalInputs, start: date, end: date) -> Dict[str, Dict[str, object]]:
    window = official_sessions(start, end)
    report: Dict[str, Dict[str, object]] = {}
    for sym in sorted(inputs.opens):
        have = inputs.opens[sym]
        present = [s for s in window if s in have]
        suspects = [
            s
            for prev, s in zip(present, present[1:])
            if s not in inputs.splits.get(sym, {})
            and not (
                1 / SPLIT_SUSPECT_FACTOR
                < inputs.opens[sym][s] / inputs.closes[sym][prev]
                < SPLIT_SUSPECT_FACTOR
            )
        ]
        report[sym] = {
            "first": present[0] if present else None,
            "last": present[-1] if present else None,
            "sessions": len(present),
            "missing": tuple(s for s in window if s not in have),
            "distributions": sum(1 for r in inputs.dividends.get(sym, ()) if start <= r.ex_date <= end),
            "splits": sum(1 for s in inputs.splits.get(sym, {}) if start <= s <= end),
            "possible_unrecorded_splits": tuple(suspects),
        }
    return report


def compute_metrics(result: D6Result, initial_nav: Decimal) -> Dict[str, Decimal]:
    navs = [record.nav for record in result.nav_curve]
    if len(navs) < 3:
        raise DataContractError("LOCAL_TOO_FEW_SESSIONS_FOR_METRICS: need at least 3.")
    returns = [b / a - 1 for a, b in zip(navs, navs[1:])]
    growth = navs[-1] / initial_nav
    periods = Decimal(len(returns))
    return {
        "terminal_nav": navs[-1],
        "total_return": growth - 1,
        "annualized_return_252": growth ** (Decimal(252) / periods) - 1,
        "annualized_volatility_252": statistics.stdev(returns) * Decimal(252).sqrt(),
        "max_drawdown": max_drawdown(navs),
        "commissions": result.commissions,
        "regulatory_fees": result.regulatory_fees,
        "distributions_net": result.dividends_gross - result.withholding,
        "trades": Decimal(len(result.trades)),
        "skipped_orders": Decimal(len(result.skipped_orders)),
    }


def run_local_exploratory(
    inputs: LocalInputs,
    *,
    start: date,
    end: date,
    cost: D6CostModel,
    whole_shares: bool = False,
    execution_timing: str = D6_TIMING_PRIMARY,
    initial_nav: Decimal = D6_INITIAL_NAV,
    portfolios: Sequence[D6Portfolio] = D6_REGISTERED_PORTFOLIOS,
) -> List[LocalOutcome]:
    if start > end:
        raise DataContractError(f"LOCAL_BAD_WINDOW: {start} > {end}.")
    if not any(start <= s <= end for s in inputs.sessions):
        raise DataContractError(f"LOCAL_EMPTY_WINDOW: no bar sessions in {start}..{end}.")
    window = list(official_sessions(start, end))
    outcomes: List[LocalOutcome] = []
    for portfolio in portfolios:
        missing = []
        for sym in sorted(portfolio.weights):
            have = inputs.opens.get(sym, {})
            gaps = [s for s in window if s not in have]
            if gaps:
                missing.append(f"{sym}: {len(gaps)} of {len(window)} sessions missing (first {gaps[0]})")
        if missing:
            outcomes.append(LocalOutcome(portfolio.name, "NOT_RUN", None, None, tuple(missing)))
            continue
        result = run_d6_portfolio(
            portfolio,
            sessions=window,
            opens=inputs.opens,
            closes=inputs.closes,
            dividends={sym: inputs.dividends.get(sym, ()) for sym in portfolio.weights},
            splits=inputs.splits,
            cost=cost,
            whole_shares=whole_shares,
            initial_nav=initial_nav,
            execution_timing=execution_timing,
        )
        result = replace(result, label=LOCAL_EXPLORATORY_LABEL)
        outcomes.append(LocalOutcome(portfolio.name, "RUN", result, compute_metrics(result, initial_nav), ()))
    return outcomes


def _pct(value: Decimal) -> str:
    return f"{value * 100:.2f}%"


def render_report(
    inputs: LocalInputs,
    outcomes: Sequence[LocalOutcome],
    *,
    start: date,
    end: date,
    cost: D6CostModel,
    execution_timing: str = D6_TIMING_PRIMARY,
) -> str:
    cov = coverage(inputs, start, end)
    lines = [
        f"# D6 {LOCAL_EXPLORATORY_LABEL} report",
        "",
        "Label: LOCAL_EXPLORATORY. Not D5-admitted, not PIT-verified, retrospective, "
        "not a performance claim and not trading authority.",
        "",
        f"- Window: {start} .. {end} ({len(official_sessions(start, end))} NYSE sessions)",
        f"- Execution timing: {execution_timing}",
        f"- Cost scenario: {cost.label} (slippage {cost.slippage_bps} bps, "
        f"commission/share {cost.commission_per_share}, regulatory fees {cost.regulatory_fees}, "
        f"withholding {cost.withholding_rate})",
        f"- Limitations: {', '.join(LOCAL_LIMITATIONS)}",
        f"- Imputed payable dates (labelled in the distributions file): "
        f"{', '.join(f'{s}={n}' for s, n in sorted(inputs.imputed_payable.items())) or 'none'}",
        "- Same-ex-date multiple distributions kept as separate provider events: "
        + (
            ", ".join(
                f"{s}={n}"
                for s, n in sorted(
                    (s, sum(":" in r.distribution_type for r in recs)) for s, recs in inputs.dividends.items()
                )
                if n
            )
            or "none"
        ),
        "",
        "## Input files (SHA-256)",
        "",
        *[f"- `{name}`: `{digest}`" for name, digest in sorted(inputs.file_sha256.items())],
        "",
        "## Coverage",
        "",
        "| Symbol | First | Last | Sessions | Missing | Distributions | Splits | Possible unrecorded splits |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for sym, row in cov.items():
        missing = row["missing"]
        suspects = row["possible_unrecorded_splits"]
        assert isinstance(missing, tuple) and isinstance(suspects, tuple)
        lines.append(
            f"| {sym} | {row['first']} | {row['last']} | {row['sessions']} | {len(missing)} | "
            f"{row['distributions']} | {row['splits']} | {', '.join(map(str, suspects)) or '-'} |"
        )
    lines += [
        "",
        "## Results",
        "",
        "| Portfolio | Status | Terminal NAV | Total return | Ann. return (252) | Ann. vol (252) "
        "| Max drawdown | Commissions | Reg. fees | Net distributions | Trades | Skipped |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for outcome in outcomes:
        m = outcome.metrics
        if m is None:
            lines.append(f"| {outcome.portfolio} | NOT_RUN | " + " | ".join(["-"] * 10) + " |")
            continue
        lines.append(
            f"| {outcome.portfolio} | RUN | {m['terminal_nav']:.2f} | {_pct(m['total_return'])} | "
            f"{_pct(m['annualized_return_252'])} | {_pct(m['annualized_volatility_252'])} | "
            f"{_pct(m['max_drawdown'])} | {m['commissions']:.2f} | {m['regulatory_fees']:.2f} | "
            f"{m['distributions_net']:.2f} | {m['trades']} | {m['skipped_orders']} |"
        )
    not_run = [o for o in outcomes if o.status == "NOT_RUN"]
    if not_run:
        lines += ["", "## Missing inputs (portfolios not run; nothing was filled in)", ""]
        lines += [f"- {o.portfolio}: {'; '.join(o.missing)}" for o in not_run]
    return "\n".join(lines) + "\n"
