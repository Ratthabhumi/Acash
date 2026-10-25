"""LOCAL_EXPLORATORY V35 contribution study (frozen grid; no tuning, no network).

Spec: docs/research/D6_V35_CONTRIBUTION_STUDY_SPEC_20261025.md. Runs the five
registered D6 portfolios for contribution scenarios C0..C3 x cost rows R0..R7,
writes a per-run CSV and the contribution ledger to --out (git-ignored) and
prints markdown tables. Broker costs are a present-day IBKR Pro scenario applied
to history, not account-verified fees; THB spreads are hypothetical.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.accounting import (
    D6_INITIAL_NAV,
    D6_REGISTERED_PORTFOLIOS,
    D6CostModel,
    D6Result,
    run_d6_portfolio,
)
from acash.research.d6.contributions import (
    cash_drag,
    investor_flows,
    monthly_contribution_schedule,
    parse_h10_rates,
    reconcile_cash,
    thb_view,
    twr_index,
    xirr,
)
from acash.research.d6.local_exploratory import LocalInputs, curve_metrics, load_local_inputs, official_sessions

D = Decimal
CONTRIBUTIONS: Tuple[Tuple[str, Decimal], ...] = (("C0", D("0")), ("C1", D("50")), ("C2", D("100")), ("C3", D("250")))
def _ibkr_fixed(label: str, slippage_bps: Decimal = D("2")) -> D6CostModel:
    return D6CostModel(
        label,
        slippage_bps=slippage_bps,
        regulatory_fees=True,
        commission_per_share=D("0.005"),
        commission_minimum=D("1.00"),
        commission_max_rate=D("0.01"),
        commission_floor=D("0.01"),
    )


def _ibkr_tiered_ex_venue(label: str) -> D6CostModel:
    return D6CostModel(
        label,
        slippage_bps=D("2"),
        regulatory_fees=True,
        commission_per_share=D("0.0035"),
        commission_minimum=D("0.35"),
        commission_max_rate=D("0.01"),
        commission_floor=D("0.01"),
        clearing_per_share=D("0.0002"),
        clearing_max_rate=D("0.005"),
        passthrough_rate=D("0.000175") + D("0.00056"),
    )


COST_ROWS: Tuple[Tuple[str, D6CostModel, bool], ...] = (
    ("R0", D6CostModel("V34_PRIMARY", slippage_bps=D("2"), regulatory_fees=True), False),
    ("R1", D6CostModel("ZERO_COST_UPPER_BOUND"), False),
    ("R2", _ibkr_fixed("IBKR_PRO_FIXED_FRAC"), False),
    ("R3", _ibkr_tiered_ex_venue("IBKR_PRO_TIERED_EX_VENUE_FRAC"), False),
    ("R4", _ibkr_fixed("IBKR_PRO_FIXED_WHOLE"), True),
    ("R5", _ibkr_tiered_ex_venue("IBKR_PRO_TIERED_EX_VENUE_WHOLE"), True),
    ("R6", _ibkr_fixed("IBKR_PRO_FIXED_FRAC_SLIP10", D("10")), False),
    (
        "R7",
        D6CostModel(
            "ZERO_COMM_MIN_NOTIONAL_1USD_FRAC", slippage_bps=D("2"), regulatory_fees=True, min_order_notional=D("1.00")
        ),
        False,
    ),
)
SPREADS = (D("0"), D("0.005"), D("0.01"))
NOT_RUN_REASON = "D6_SPLIT_CASH_IN_LIEU_UNSUPPORTED"


@dataclass(frozen=True)
class Run:
    dataset: str
    scenario: str
    row: str
    portfolio: str
    status: str
    result: Optional[D6Result]
    metrics: Dict[str, object]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _metrics(result: D6Result) -> Dict[str, object]:
    index = twr_index(result, D6_INITIAL_NAV)
    curve = curve_metrics(index, D6_INITIAL_NAV)
    mean_cash, end_cash = cash_drag(result)
    ledger = reconcile_cash(result, D6_INITIAL_NAV)
    skipped: Dict[str, int] = {}
    for order in result.skipped_orders:
        skipped[order.reason] = skipped.get(order.reason, 0) + 1
    terminal = result.terminal_nav
    return {
        "terminal_nav": terminal,
        "contributed": result.contributed,
        "net_gain": terminal - D6_INITIAL_NAV - result.contributed,
        "twr_total": curve["total_return"],
        "twr_ann_252": curve["annualized_return_252"],
        "twr_vol_252": curve["annualized_volatility_252"],
        "twr_max_drawdown": curve["max_drawdown"],
        "xirr_act365": xirr(investor_flows(result, D6_INITIAL_NAV)),
        "mean_cash_share": mean_cash,
        "terminal_cash": end_cash,
        "commissions": result.commissions,
        "regulatory_fees": result.regulatory_fees,
        "slippage_cost": sum((abs(t.fill_price - t.open_price) * t.quantity for t in result.trades), D("0")),
        "trades": len(result.trades),
        "skipped": ";".join(f"{k}={v}" for k, v in sorted(skipped.items())),
        "reconciled_ending_cash": ledger["ending_cash"],
    }


def run_grid(inputs: LocalInputs, dataset: str, start: date, end: date, rows: Sequence[str]) -> List[Run]:
    window = list(official_sessions(start, end))
    runs: List[Run] = []
    for scenario, amount in CONTRIBUTIONS:
        schedule = monthly_contribution_schedule(window, amount)
        for row, cost, whole in COST_ROWS:
            if row not in rows:
                continue
            for portfolio in D6_REGISTERED_PORTFOLIOS:
                try:
                    result = run_d6_portfolio(
                        portfolio,
                        sessions=window,
                        opens=inputs.opens,
                        closes=inputs.closes,
                        dividends={s: inputs.dividends.get(s, ()) for s in portfolio.weights},
                        splits=inputs.splits,
                        cost=cost,
                        whole_shares=whole,
                        contributions=schedule,
                    )
                except DataContractError as exc:
                    if NOT_RUN_REASON not in str(exc):
                        raise
                    runs.append(Run(dataset, scenario, row, portfolio.name, f"NOT_RUN ({exc})", None, {}))
                    continue
                runs.append(Run(dataset, scenario, row, portfolio.name, "RUN", result, _metrics(result)))
    return runs


def _fmt(value: object, kind: str = "money") -> str:
    if value is None or value == "":
        return "—"
    if kind == "pct":
        return f"{float(value) * 100:.2f}%"  # type: ignore[arg-type]
    return f"{Decimal(str(value)):.2f}"


def _ranking(runs: Sequence[Run], scenario: str, row: str) -> List[str]:
    cell = [r for r in runs if r.scenario == scenario and r.row == row and r.status == "RUN"]
    cell.sort(key=lambda r: (-Decimal(str(r.metrics["twr_ann_252"])), r.portfolio))
    return [r.portfolio for r in cell]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, required=True, help="primary converted dataset dir")
    parser.add_argument("--boundary-data", type=Path, required=True, help="min-lag dataset dir (R2 only)")
    parser.add_argument("--h10", type=Path, required=True, help="stored H.10 Thailand historical page")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2016, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if any(args.out.iterdir()):
        raise SystemExit(f"refusing non-empty output dir {args.out}")

    files = {n: args.data / n for n in ("bars_raw.csv", "distributions.csv", "splits.csv")}
    print("## Inputs")
    for name, path in [*files.items(), ("boundary distributions.csv", args.boundary_data / "distributions.csv")]:
        print(f"- `{name}` sha256 `{_sha(path)}`")
    print(f"- H.10 page sha256 `{hashlib.sha256(args.h10.read_bytes()).hexdigest()}`")

    primary = load_local_inputs(files["bars_raw.csv"], files["distributions.csv"], files["splits.csv"])
    boundary = load_local_inputs(
        args.boundary_data / "bars_raw.csv", args.boundary_data / "distributions.csv", args.boundary_data / "splits.csv"
    )
    runs = run_grid(primary, "max", args.start, args.end, [r for r, _, _ in COST_ROWS])
    runs += run_grid(boundary, "min", args.start, args.end, ["R2"])
    rates = parse_h10_rates(args.h10.read_text(encoding="utf-8"))

    fields = ["dataset", "scenario", "row", "cost_label", "portfolio", "status"]
    metric_keys = list(next(r.metrics for r in runs if r.status == "RUN"))
    labels = {row: cost.label for row, cost, _ in COST_ROWS}
    with (args.out / "v35_grid.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fields + metric_keys)
        for r in runs:
            writer.writerow(
                [r.dataset, r.scenario, r.row, labels[r.row], r.portfolio, r.status]
                + [r.metrics.get(k, "") for k in metric_keys]
            )
    sample = next(r for r in runs if r.scenario == "C1" and r.row == "R2" and r.result is not None)
    with (args.out / "v35_contribution_ledger_C1.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["session", "amount_usd"])
        for day, amount in sample.result.contributions if sample.result else ():
            writer.writerow([day.isoformat(), str(amount)])

    main_runs = [r for r in runs if r.dataset == "max"]
    print("\n## C0 baseline (R0) — must equal V34 primary")
    for r in main_runs:
        if r.scenario == "C0" and r.row == "R0":
            print(f"- {r.portfolio}: {_fmt(r.metrics.get('terminal_nav'))}")

    for scenario, _ in CONTRIBUTIONS:
        print(f"\n## {scenario} x R2 IBKR Pro Fixed, fractional")
        print("| Portfolio | Terminal | Contributed | Net gain | TWR ann | Vol | MaxDD (TWR) | XIRR | Mean cash | End cash | Comm | Trades | Skipped |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in main_runs:
            if r.scenario == scenario and r.row == "R2":
                m = r.metrics
                print(
                    f"| {r.portfolio} | {_fmt(m.get('terminal_nav'))} | {_fmt(m.get('contributed'))} | "
                    f"{_fmt(m.get('net_gain'))} | {_fmt(m.get('twr_ann_252'), 'pct')} | {_fmt(m.get('twr_vol_252'), 'pct')} | "
                    f"{_fmt(m.get('twr_max_drawdown'), 'pct')} | {_fmt(m.get('xirr_act365'), 'pct')} | "
                    f"{_fmt(m.get('mean_cash_share'), 'pct')} | {_fmt(m.get('terminal_cash'))} | "
                    f"{_fmt(m.get('commissions'))} | {m.get('trades', '—')} | {m.get('skipped') or '—'} |"
                )

    print("\n## Cost sensitivity: terminal NAV (TWR ann) per row")
    for scenario, _ in CONTRIBUTIONS:
        print(f"\n### {scenario}")
        print("| Portfolio | " + " | ".join(r for r, _, _ in COST_ROWS) + " |")
        print("|---|" + "---|" * len(COST_ROWS))
        for portfolio in D6_REGISTERED_PORTFOLIOS:
            cells = []
            for row, _, _ in COST_ROWS:
                hit = next(r for r in main_runs if r.scenario == scenario and r.row == row and r.portfolio == portfolio.name)
                cells.append(
                    "NOT_RUN" if hit.status != "RUN"
                    else f"{_fmt(hit.metrics['terminal_nav'])} ({_fmt(hit.metrics['twr_ann_252'], 'pct')})"
                )
            print(f"| {portfolio.name} | " + " | ".join(cells) + " |")

    print("\n## Ranking by TWR (ties by name); reference C0/R0")
    reference = _ranking(main_runs, "C0", "R0")
    print(f"- reference: {' > '.join(reference)}")
    for scenario, _ in CONTRIBUTIONS:
        for row, _, _ in COST_ROWS:
            order = _ranking(main_runs, scenario, row)
            common = [p for p in reference if p in order]
            same = [p for p in order if p in common] == common
            print(f"- {scenario}/{row}: {' > '.join(order)}{'' if same else '  **REVERSAL**'}")

    print("\n## Payable-lag boundary (R2): max-lag minus min-lag terminal NAV")
    for r in main_runs:
        if r.row != "R2" or r.status != "RUN":
            continue
        twin = next(b for b in runs if b.dataset == "min" and b.scenario == r.scenario and b.portfolio == r.portfolio)
        delta = Decimal(str(r.metrics["terminal_nav"])) - Decimal(str(twin.metrics["terminal_nav"]))
        print(f"- {r.scenario} {r.portfolio}: {delta:.2f}")

    print("\n## THB view (R2; H.10 noon rates; spreads hypothetical, bank fees/taxes not modelled)")
    print("| Scenario | Portfolio | Spread in/out | THB contributed | THB terminal | THB XIRR | USD XIRR | prior-H.10 uses |")
    print("|---|---|---|---|---|---|---|---|")
    for r in main_runs:
        if r.row != "R2" or r.result is None or r.portfolio == "CASH_NO_TRADE":
            continue
        flows = investor_flows(r.result, D6_INITIAL_NAV)
        for spread in SPREADS:
            view = thb_view(flows, rates, funding_spread=spread, liquidation_spread=spread)
            print(
                f"| {r.scenario} | {r.portfolio} | {spread * 100:.1f}% | {_fmt(view['thb_contributed'])} | "
                f"{_fmt(view['thb_terminal'])} | {_fmt(view['thb_xirr'], 'pct')} | "
                f"{_fmt(r.metrics['xirr_act365'], 'pct')} | {view['prior_h10_rate_uses']} |"
            )


if __name__ == "__main__":
    main()
