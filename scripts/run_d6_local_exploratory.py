"""Run the five D6 portfolios in LOCAL_EXPLORATORY mode on owner-supplied CSV files.

Example:
    uv run python scripts/run_d6_local_exploratory.py \
        --bars data/local_research/bars_raw.csv \
        --distributions data/local_research/distributions.csv \
        --splits data/local_research/splits.csv \
        --start 2016-01-01 --end 2025-12-31 --slippage-bps 2 --regulatory-fees

No network access. Outputs go to --out (default under the git-ignored data/ tree).
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from acash.research.d6.accounting import D6_TIMING_OPEN_SENSITIVITY, D6_TIMING_PRIMARY, D6CostModel
from acash.research.d6.local_exploratory import load_local_inputs, render_report, run_local_exploratory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bars", type=Path, required=True)
    parser.add_argument("--distributions", type=Path)
    parser.add_argument("--splits", type=Path)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--out", type=Path, default=Path("data/local_research/out"))
    parser.add_argument("--cost-label", default=None)
    parser.add_argument("--slippage-bps", type=Decimal, default=Decimal("0"))
    parser.add_argument("--commission-per-share", type=Decimal, default=Decimal("0"))
    parser.add_argument("--commission-minimum", type=Decimal, default=Decimal("0"))
    parser.add_argument("--regulatory-fees", action="store_true")
    parser.add_argument("--withholding-rate", type=Decimal, default=Decimal("0"))
    parser.add_argument("--whole-shares", action="store_true")
    parser.add_argument("--timing", choices=("primary", "sensitivity"), default="primary")
    args = parser.parse_args()

    zero_cost = not (args.slippage_bps or args.commission_per_share or args.commission_minimum or args.regulatory_fees)
    cost = D6CostModel(
        label=args.cost_label or ("ZERO_COST_UPPER_BOUND" if zero_cost else "LOCAL_COST_SCENARIO"),
        slippage_bps=args.slippage_bps,
        commission_per_share=args.commission_per_share,
        commission_minimum=args.commission_minimum,
        regulatory_fees=args.regulatory_fees,
        withholding_rate=args.withholding_rate,
    )
    timing = D6_TIMING_PRIMARY if args.timing == "primary" else D6_TIMING_OPEN_SENSITIVITY
    inputs = load_local_inputs(args.bars, args.distributions, args.splits)
    outcomes = run_local_exploratory(
        inputs, start=args.start, end=args.end, cost=cost, whole_shares=args.whole_shares, execution_timing=timing
    )

    args.out.mkdir(parents=True, exist_ok=True)
    report = render_report(inputs, outcomes, start=args.start, end=args.end, cost=cost, execution_timing=timing)
    (args.out / "report.md").write_text(report, encoding="utf-8")
    for outcome in outcomes:
        if outcome.result is None:
            continue
        with (args.out / f"nav_{outcome.portfolio}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["session", "cash", "market_value", "receivable", "nav"])
            for rec in outcome.result.nav_curve:
                writer.writerow([rec.session.isoformat(), rec.cash, rec.market_value, rec.receivable, rec.nav])
    print(report)


if __name__ == "__main__":
    main()
