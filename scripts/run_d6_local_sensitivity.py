"""LOCAL_EXPLORATORY sensitivity: payable-date policy, counterfactual event reading, cost grid.

Runs the registered D6 portfolios on the same saved bars for each scenario and prints
markdown tables. Scenarios are labelled assumptions, not verified broker fees or tax
treatment. No network.

Modes:
  scenarios  payable-lag policies, the counterfactual "BND capital gains were
             corrections" reading, and single-assumption cost changes
  grid       the V34 cost grid (fixed before execution; no tuning): commission
             structure x share granularity x spread
"""

from __future__ import annotations

import argparse
import csv
import tempfile
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.accounting import D6_REGISTERED_PORTFOLIOS, D6_TIMING_PRIMARY, D6CostModel
from acash.research.d6.local_exploratory import LocalOutcome, load_local_inputs, run_local_exploratory

BASE_COST = D6CostModel(label="LOCAL_COST_SCENARIO", slippage_bps=Decimal("2"), regulatory_fees=True)
COSTS: Dict[str, D6CostModel] = {
    "base_2bps_regfees": BASE_COST,
    "zero_cost_upper_bound": D6CostModel(label="ZERO_COST_UPPER_BOUND"),
    "slippage_10bps": D6CostModel(label="SLIPPAGE_10BPS", slippage_bps=Decimal("10"), regulatory_fees=True),
    "commission_0.005_min1": D6CostModel(
        label="COMMISSION_SCENARIO", slippage_bps=Decimal("2"), regulatory_fees=True,
        commission_per_share=Decimal("0.005"), commission_minimum=Decimal("1"),
    ),
    "withholding_15pct": D6CostModel(
        label="WITHHOLDING_15PCT_SCENARIO", slippage_bps=Decimal("2"), regulatory_fees=True,
        withholding_rate=Decimal("0.15"),
    ),
}
# V34 grid, fixed before execution. Commission structures are HYPOTHETICAL shapes, not
# verified current fees of any broker.
_PER_SHARE = {"commission_per_share": Decimal("0.005"), "commission_minimum": Decimal("1")}
_PER_TICKET = {"commission_minimum": Decimal("1")}
GRID: Tuple[Tuple[str, D6CostModel, bool], ...] = (
    ("G0 zero cost, fractional (upper bound)", D6CostModel(label="G0"), False),
    ("G1 0 comm, 2 bps, fractional", D6CostModel(label="G1", slippage_bps=Decimal("2"), regulatory_fees=True), False),
    ("G2 0 comm, 2 bps, whole shares", D6CostModel(label="G2", slippage_bps=Decimal("2"), regulatory_fees=True), True),
    ("G3 0 comm, 10 bps, whole shares", D6CostModel(label="G3", slippage_bps=Decimal("10"), regulatory_fees=True), True),
    ("G4 0.005/sh min 1, 2 bps, fractional",
     D6CostModel(label="G4", slippage_bps=Decimal("2"), regulatory_fees=True, **_PER_SHARE), False),
    ("G5 0.005/sh min 1, 2 bps, whole shares",
     D6CostModel(label="G5", slippage_bps=Decimal("2"), regulatory_fees=True, **_PER_SHARE), True),
    ("G6 1.00 per order, 2 bps, whole shares",
     D6CostModel(label="G6", slippage_bps=Decimal("2"), regulatory_fees=True, **_PER_TICKET), True),
)
RECLASSIFIED = {"OCC_MEMO_CORROBORATED", "SECONDARY_INDICATION_ONLY", "ISSUER_DOCUMENT"}


@dataclass(frozen=True)
class Row:
    scenario: str
    portfolio: str
    terminal_nav: Decimal
    max_drawdown: Decimal
    execution_cost: Decimal
    trades: int
    skipped: int
    turnover: Decimal
    mean_cash_share: Decimal
    receivables_at_rebalance: Decimal


def counterfactual_drop(src: Path, dst: Path) -> int:
    """Counterfactual: the cited BND capital-gain events were provider corrections, not cash.

    Reconciled input: drop rows whose evidence class marks them as reclassified gains.
    Provider-format input: drop the smaller event of each same-symbol same-ex-date pair.
    """
    with src.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = list(reader.fieldnames or ())
    if "evidence_class" in columns:
        keep = [r for r in rows if r["evidence_class"] not in RECLASSIFIED]
    else:
        groups: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
        for row in rows:
            groups.setdefault((row["symbol"], row["ex_date"]), []).append(row)
        keep = [max(g, key=lambda r: Decimal(r["gross_amount"])) if len(g) > 1 else g[0] for g in groups.values()]
    with dst.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(keep, key=lambda r: (r["symbol"], r["ex_date"], r["event_id"])))
    return len(rows) - len(keep)


def summarize(scenario: str, outcomes: Sequence[LocalOutcome]) -> List[Row]:
    rows = []
    for outcome in outcomes:
        result, metrics = outcome.result, outcome.metrics
        if result is None or metrics is None:
            continue
        navs = result.nav_curve
        mean_nav = sum((r.nav for r in navs), Decimal(0)) / len(navs)
        executions = {t.session for t in result.trades}
        slippage = sum((abs(t.fill_price - t.open_price) * t.quantity for t in result.trades), Decimal(0))
        rows.append(
            Row(
                scenario,
                outcome.portfolio,
                result.terminal_nav,
                metrics["max_drawdown"],
                result.commissions + result.regulatory_fees + slippage,
                len(result.trades),
                len(result.skipped_orders),
                sum((t.notional for t in result.trades), Decimal(0)) / mean_nav,
                sum((r.cash / r.nav for r in navs), Decimal(0)) / len(navs),
                sum((r.receivable for r in navs if r.session in executions), Decimal(0)),
            )
        )
    return rows


def _print(rows: Sequence[Row]) -> None:
    print("| Scenario | Portfolio | Terminal NAV | Max DD | Exec. cost | Trades | Skipped | Turnover "
          "| Mean cash share | Receivables at executions | Rank |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for scenario in dict.fromkeys(r.scenario for r in rows):
        group = [r for r in rows if r.scenario == scenario]
        ranked = sorted(group, key=lambda r: r.terminal_nav, reverse=True)
        for r in group:
            print(
                f"| {r.scenario} | {r.portfolio} | {r.terminal_nav:.2f} | {r.max_drawdown * 100:.2f}% | "
                f"{r.execution_cost:.2f} | {r.trades} | {r.skipped} | {r.turnover:.4f} | "
                f"{r.mean_cash_share * 100:.4f}% | {r.receivables_at_rebalance:.2f} | {ranked.index(r) + 1} |"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("scenarios", "grid"))
    parser.add_argument("--policy-dir", action="append", required=True, help="NAME=DIR (converted dataset)")
    parser.add_argument("--primary", required=True, help="NAME of the dataset used for non-policy scenarios")
    parser.add_argument("--start", type=date.fromisoformat, default=date(2016, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    args = parser.parse_args()
    dirs = {item.split("=", 1)[0]: Path(item.split("=", 1)[1]) for item in args.policy_dir}
    primary = dirs[args.primary]

    def run(name: str, d: Path, cost: D6CostModel, distributions: Path | None = None, whole: bool = False) -> List[Row]:
        inputs = load_local_inputs(d / "bars_raw.csv", distributions or d / "distributions.csv", d / "splits.csv")
        outcomes = run_local_exploratory(
            inputs, start=args.start, end=args.end, cost=cost, whole_shares=whole, execution_timing=D6_TIMING_PRIMARY
        )
        return summarize(name, outcomes)

    rows: List[Row] = []
    if args.mode == "grid":
        inputs = load_local_inputs(primary / "bars_raw.csv", primary / "distributions.csv", primary / "splits.csv")
        not_run: List[str] = []
        for name, cost, whole in GRID:
            for portfolio in D6_REGISTERED_PORTFOLIOS:
                try:
                    outcomes = run_local_exploratory(
                        inputs, start=args.start, end=args.end, cost=cost, whole_shares=whole,
                        execution_timing=D6_TIMING_PRIMARY, portfolios=[portfolio],
                    )
                except DataContractError as exc:
                    not_run.append(f"- {name} / {portfolio.name}: NOT_RUN ({exc})")
                    continue
                rows += summarize(name, outcomes)
        _print(rows)
        print("\n" + "\n".join(not_run) if not_run else "")
        return
    for name, d in dirs.items():
        rows += run(f"payable_{name}", d, BASE_COST)
    with tempfile.TemporaryDirectory() as tmp:
        cf_csv = Path(tmp) / "distributions.csv"
        dropped = counterfactual_drop(primary / "distributions.csv", cf_csv)
        rows += run(f"COUNTERFACTUAL_gains_as_corrections_{args.primary}(-{dropped})", primary, BASE_COST, cf_csv)
    for name, cost in COSTS.items():
        if cost is not BASE_COST:
            rows += run(f"cost_{name}_{args.primary}", primary, cost)
    _print(rows)


if __name__ == "__main__":
    main()
