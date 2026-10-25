"""LOCAL_EXPLORATORY sensitivity: payable-date policy, same-day pair reading, cost scenarios.

Runs the registered D6 portfolios on the same saved bars for each scenario and prints
a markdown table (terminal NAV, turnover, mean cash share, rank, receivables
outstanding at rebalance executions). Scenarios are labelled assumptions, not broker
costs or tax treatment. No network.

Inputs: converted directories from ``fetch_alpaca_d6_local_data.py convert`` with
--payable-lag-policy min / median / max.
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

from acash.research.d6.accounting import D6_TIMING_PRIMARY, D6CostModel
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


@dataclass(frozen=True)
class Row:
    scenario: str
    portfolio: str
    terminal_nav: Decimal
    turnover: Decimal
    mean_cash_share: Decimal
    receivables_at_rebalance: Decimal


def drop_smaller_same_day_pair(src: Path, dst: Path) -> int:
    """Scenario: read each same-symbol same-ex-date pair as a correction; keep the larger rate."""
    with src.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = list(reader.fieldnames or ())
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
        result = outcome.result
        if result is None:
            continue
        navs = result.nav_curve
        mean_nav = sum((r.nav for r in navs), Decimal(0)) / len(navs)
        executions = {t.session for t in result.trades}
        rows.append(
            Row(
                scenario,
                outcome.portfolio,
                result.terminal_nav,
                sum((t.notional for t in result.trades), Decimal(0)) / mean_nav,
                sum((r.cash / r.nav for r in navs), Decimal(0)) / len(navs),
                sum((r.receivable for r in navs if r.session in executions), Decimal(0)),
            )
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--policy-dir", action="append", required=True, help="NAME=DIR (converted dataset)")
    parser.add_argument("--primary", required=True, help="NAME of the policy dir used for pair and cost scenarios")
    parser.add_argument("--start", type=date.fromisoformat, default=date(2016, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    args = parser.parse_args()
    dirs = {item.split("=", 1)[0]: Path(item.split("=", 1)[1]) for item in args.policy_dir}

    def run(name: str, d: Path, cost: D6CostModel, distributions: Path | None = None) -> List[Row]:
        inputs = load_local_inputs(d / "bars_raw.csv", distributions or d / "distributions.csv", d / "splits.csv")
        outcomes = run_local_exploratory(
            inputs, start=args.start, end=args.end, cost=cost, execution_timing=D6_TIMING_PRIMARY
        )
        return summarize(name, outcomes)

    rows: List[Row] = []
    for name, d in dirs.items():
        rows += run(f"payable_{name}", d, BASE_COST)
    primary = dirs[args.primary]
    with tempfile.TemporaryDirectory() as tmp:
        pair_csv = Path(tmp) / "distributions.csv"
        dropped = drop_smaller_same_day_pair(primary / "distributions.csv", pair_csv)
        rows += run(f"pairs_as_corrections_{args.primary}(-{dropped})", primary, BASE_COST, pair_csv)
    for name, cost in COSTS.items():
        if cost is not BASE_COST:
            rows += run(f"cost_{name}_{args.primary}", primary, cost)

    print("| Scenario | Portfolio | Terminal NAV | Turnover (x mean NAV) | Mean cash share "
          "| Receivables at executions | Rank |")
    print("|---|---|---|---|---|---|---|")
    for scenario in dict.fromkeys(r.scenario for r in rows):
        group = [r for r in rows if r.scenario == scenario]
        ranked = sorted(group, key=lambda r: r.terminal_nav, reverse=True)
        for r in group:
            print(
                f"| {r.scenario} | {r.portfolio} | {r.terminal_nav:.2f} | {r.turnover:.4f} | "
                f"{r.mean_cash_share * 100:.4f}% | {r.receivables_at_rebalance:.2f} | {ranked.index(r) + 1} |"
            )


if __name__ == "__main__":
    main()
