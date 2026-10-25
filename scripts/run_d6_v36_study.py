"""LOCAL_EXPLORATORY V36 study: IBKR cost audit, Thai funding cadence, withholding
scenarios, accounting attribution and subperiods (frozen grid; no network).

Spec: docs/research/D6_V36_FUNDING_COST_AUDIT_SPEC_20261026.md. Run from the
repository root as ``uv run python -m scripts.run_d6_v36_study ...``. Writes CSVs
to --out (git-ignored, must be empty) and prints markdown tables. Fees are
current published schedules applied retrospectively; spreads, intermediary fees
and withholding rows are labelled scenarios, not account or tax facts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.accounting import (
    D6_INITIAL_NAV,
    D6_REGISTERED_PORTFOLIOS,
    D6CostModel,
    D6Portfolio,
    D6Result,
    run_d6_portfolio,
)
from acash.research.d6.attribution import broker_attribution, household_attribution
from acash.research.d6.contributions import h10_rate, monthly_contribution_schedule, parse_h10_rates, xirr
from acash.research.d6.funding import FundingPlan, FundingScenario, plan_funding
from acash.research.d6.local_exploratory import LocalInputs, load_local_inputs, official_sessions
from scripts.run_d6_contribution_study import COST_ROWS, CONTRIBUTIONS, NOT_RUN_REASON, _fmt, _metrics, _sha

D = Decimal
V35 = {row: (cost, whole) for row, cost, whole in COST_ROWS}
R2_COST = V35["R2"][0]
_TIER = {
    "commission_per_share": D("0.0035"),
    "commission_minimum": D("0.35"),
    "commission_floor": D("0.01"),
    "clearing_per_share": D("0.0002"),
    "clearing_max_rate": D("0.005"),
    "passthrough_rate": D("0.000175") + D("0.00056"),
}


def _tiered(label: str, cap: Decimal, venue: Decimal = D("0")) -> D6CostModel:
    return D6CostModel(
        label,
        slippage_bps=D("2"),
        regulatory_fees=True,
        commission_max_rate=cap,
        exchange_per_share=venue,
        commission_per_share=_TIER["commission_per_share"],
        commission_minimum=_TIER["commission_minimum"],
        commission_floor=_TIER["commission_floor"],
        clearing_per_share=_TIER["clearing_per_share"],
        clearing_max_rate=_TIER["clearing_max_rate"],
        passthrough_rate=_TIER["passthrough_rate"],
    )


AUDIT_ROWS: Tuple[Tuple[str, D6CostModel, bool], ...] = (
    ("R2", V35["R2"][0], False),
    (
        "R2F",
        D6CostModel(
            "IBKR_PRO_FIXED_FRAC_LITERAL_1PCT",
            slippage_bps=D("2"),
            regulatory_fees=True,
            commission_per_share=D("0.005"),
            commission_minimum=D("1.00"),
            commission_max_rate=D("0.01"),
            commission_floor=D("0.01"),
            fractional_rate=D("0.01"),
        ),
        False,
    ),
    ("R3", V35["R3"][0], False),
    ("R3H", _tiered("IBKR_PRO_TIERED_CAP_0_5PCT_EX_VENUE_FRAC", D("0.005")), False),
    ("R3L", _tiered("IBKR_PRO_TIERED_ARCA_OPEN_AUCTION_LIMIT_FRAC", D("0.01"), D("0.0006")), False),
    ("R3M", _tiered("IBKR_PRO_TIERED_ARCA_AT_THE_OPEN_FRAC", D("0.01"), D("0.0015")), False),
    ("R3R", _tiered("IBKR_PRO_TIERED_ARCA_REMOVE_LIQUIDITY_FRAC", D("0.01"), D("0.0030")), False),
    ("R4", V35["R4"][0], True),
    ("R5", V35["R5"][0], True),
)
REGRESSION_ROWS = ("R2", "R3", "R4", "R5")


def _funding_rows() -> List[FundingScenario]:
    rows = [FundingScenario("F0")]
    for name, cadence in (("F1", 1), ("F2", 3), ("F3", 12)):
        if cadence == 1:
            rows.append(FundingScenario("F1_CTRL", cadence=1))
        for fee in ("0", "250", "400", "550"):
            rows.append(FundingScenario(f"{name}_fee{fee}_s0.5", cadence, D(fee), D("0.005")))
        rows.append(FundingScenario(f"{name}_fee400_s0", cadence, D("400"), D("0")))
        rows.append(FundingScenario(f"{name}_fee400_s1.0", cadence, D("400"), D("0.01")))
        rows.append(FundingScenario(f"{name}_fee400_s0.5_d1", cadence, D("400"), D("0.005"), delay_sessions=1))
        rows.append(FundingScenario(f"{name}_fee400_s0.5_d3", cadence, D("400"), D("0.005"), delay_sessions=3))
        rows.append(FundingScenario(f"{name}_fee400_s0.5_int15", cadence, D("400"), D("0.005"), D("15")))
    return rows


def _w(label: str, voo: str, ordinary: str, gains: str) -> D6CostModel:
    overrides = (
        ("VOO", "*", D(voo)),
        ("BND", "DIVIDEND_CASH", D(ordinary)),
        ("BIL", "*", D(ordinary)),
        ("BND", "CAPITAL_GAIN_LONG_TERM", D(gains)),
        ("BND", "CAPITAL_GAIN_SHORT_TERM", D(gains)),
    )
    return D6CostModel(
        label,
        slippage_bps=R2_COST.slippage_bps,
        regulatory_fees=True,
        commission_per_share=R2_COST.commission_per_share,
        commission_minimum=R2_COST.commission_minimum,
        commission_max_rate=R2_COST.commission_max_rate,
        commission_floor=R2_COST.commission_floor,
        withholding_overrides=overrides,
    )


TAX_ROWS = (
    ("W0", _w("W0", "0", "0", "0")),
    ("W15", _w("W15", "0.15", "0.15", "0.15")),
    ("W30", _w("W30", "0.30", "0.30", "0.30")),
    ("WT_LOW", _w("WT_LOW", "0.15", "0", "0")),
    ("WT_MID", _w("WT_MID", "0.15", "0.15", "0")),
    ("WT_NOTREATY", _w("WT_NOTREATY", "0.30", "0.30", "0")),
)
WINDOWS = (
    ("2016-2019", date(2016, 1, 1), date(2019, 12, 31)),
    ("2020-2022", date(2020, 1, 1), date(2022, 12, 31)),
    ("2023-2025", date(2023, 1, 1), date(2025, 12, 31)),
    ("2016-2025", date(2016, 1, 1), date(2025, 12, 31)),
)
NON_CASH = [p for p in D6_REGISTERED_PORTFOLIOS if p.weights]


def _run(
    inputs: LocalInputs,
    window: Sequence[date],
    portfolio: D6Portfolio,
    cost: D6CostModel,
    whole: bool,
    contributions: Dict[date, Decimal],
) -> Optional[D6Result]:
    try:
        return run_d6_portfolio(
            portfolio,
            sessions=window,
            opens=inputs.opens,
            closes=inputs.closes,
            dividends={s: inputs.dividends.get(s, ()) for s in portfolio.weights},
            splits=inputs.splits,
            cost=cost,
            whole_shares=whole,
            contributions=contributions,
        )
    except DataContractError as exc:
        if NOT_RUN_REASON not in str(exc):
            raise
        return None


def _write(path: Path, rows: List[Dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _pct(value: object) -> str:
    return _fmt(value, "pct")


def cost_audit(inputs: LocalInputs, window: Sequence[date], v35_grid: Path, out: Path) -> None:
    rows: List[Dict[str, object]] = []
    for scenario, amount in CONTRIBUTIONS:
        schedule = monthly_contribution_schedule(window, amount)
        for row, cost, whole in AUDIT_ROWS:
            for portfolio in D6_REGISTERED_PORTFOLIOS:
                result = _run(inputs, window, portfolio, cost, whole, schedule)
                base = {"scenario": scenario, "row": row, "cost_label": cost.label, "portfolio": portfolio.name}
                rows.append({**base, "status": "RUN" if result else "NOT_RUN", **(_metrics(result) if result else {})})
    _write(out / "v36_cost_audit.csv", [r for r in rows if r["status"] == "RUN"])

    with v35_grid.open(encoding="utf-8") as handle:
        snapshot = {(r["scenario"], r["row"], r["portfolio"]): r for r in csv.DictReader(handle) if r["dataset"] == "max"}
    checked, diffs = 0, []
    for r in rows:
        if r["row"] not in REGRESSION_ROWS:
            continue
        old = snapshot[(str(r["scenario"]), str(r["row"]), str(r["portfolio"]))]
        if (old["status"] == "RUN") != (r["status"] == "RUN"):
            diffs.append(f"{r['scenario']}/{r['row']}/{r['portfolio']}: status")
            continue
        checked += 1
        for key, value in r.items():
            if key in old and key not in ("status", "row", "scenario", "portfolio") and old[key] != str(value):
                diffs.append(f"{r['scenario']}/{r['row']}/{r['portfolio']}: {key}")
    print("\n## P0 regression vs V35 snapshot (R2/R3/R4/R5, every metric)")
    print(f"- cells compared: {checked}; differing fields: {len(diffs)} {diffs[:5]}")

    print("\n## P0 IBKR interpretation rows: TWR annualized (terminal NAV)")
    for scenario, _ in CONTRIBUTIONS:
        print(f"\n### {scenario}")
        print("| Portfolio | " + " | ".join(r for r, _, _ in AUDIT_ROWS) + " |")
        print("|---|" + "---|" * len(AUDIT_ROWS))
        for portfolio in NON_CASH:
            cells = []
            for row, _, _ in AUDIT_ROWS:
                hit = next(x for x in rows if x["scenario"] == scenario and x["row"] == row and x["portfolio"] == portfolio.name)
                cells.append(
                    "NOT_RUN" if hit["status"] != "RUN" else f"{_pct(hit['twr_ann_252'])} ({_fmt(hit['terminal_nav'])})"
                )
            print(f"| {portfolio.name} | " + " | ".join(cells) + " |")


def _household(
    plan: FundingPlan, result: D6Result, rates: Dict[date, Decimal], window: Sequence[date]
) -> Dict[str, object]:
    rate_t, _ = h10_rate(rates, window[-1])
    rate_0, _ = h10_rate(rates, window[0])
    usd = result.terminal_nav + plan.in_transit_usd + plan.unremitted_thb / rate_t
    thb = (result.terminal_nav + plan.in_transit_usd) * rate_t + plan.unremitted_thb
    thb_flows = [(window[0], -D6_INITIAL_NAV * rate_0)] + [(d, -t) for d, t, _ in plan.savings] + [(window[-1], thb)]
    usd_flows = [(window[0], -D6_INITIAL_NAV)] + [(d, -t / r) for d, t, r in plan.savings] + [(window[-1], usd)]
    rem = plan.remittances
    return {
        "household_usd": usd,
        "household_thb": thb,
        "household_xirr_thb": xirr(thb_flows),
        "household_xirr_usd": xirr(usd_flows),
        "remittances": len(rem),
        "sender_fees_thb": sum((r.sender_fee_usd_ref * r.rate for r in rem), D("0")),
        "frictions_usd": sum(
            (r.sender_fee_usd_ref + r.spread_cost_usd + r.intermediary_fee_usd + r.rounding_usd for r in rem), D("0")
        ),
        "unremitted_thb": plan.unremitted_thb,
        "in_transit_usd": plan.in_transit_usd,
        "mean_unremitted_thb": plan.mean_unremitted_thb,
        "prior_h10_uses": plan.prior_rate_uses,
    }


def funding_study(inputs: LocalInputs, window: Sequence[date], rates: Dict[date, Decimal], out: Path) -> None:
    rows: List[Dict[str, object]] = []
    for scenario, amount in CONTRIBUTIONS[1:]:
        for fs in _funding_rows():
            plan = plan_funding(window, amount, rates, fs)
            for portfolio in D6_REGISTERED_PORTFOLIOS:
                result = _run(inputs, window, portfolio, R2_COST, False, plan.contributions)
                if result is None:
                    raise DataContractError(f"V36_UNEXPECTED_NOT_RUN: {scenario} {fs.label} {portfolio.name}.")
                m = _metrics(result)
                rows.append(
                    {
                        "scenario": scenario,
                        "funding": fs.label,
                        "portfolio": portfolio.name,
                        "broker_nav": result.terminal_nav,
                        "broker_twr_ann_252": m["twr_ann_252"],
                        "broker_commissions": result.commissions,
                        **_household(plan, result, rates, window),
                    }
                )
    _write(out / "v36_funding.csv", rows)
    for r in rows:
        if r["funding"] == "F1_CTRL":
            f0 = next(x for x in rows if x["funding"] == "F0" and x["scenario"] == r["scenario"] and x["portfolio"] == r["portfolio"])
            if f0["broker_nav"] != r["broker_nav"]:
                raise DataContractError(f"V36_F1_CTRL_DIVERGES_FROM_F0: {r['scenario']} {r['portfolio']}.")
    print("\n## P1 Funding cadence (R2; household = broker + in-transit + unremitted THB at terminal H.10)")
    print("- F1_CTRL reproduced F0 broker NAV to the cent in every cell.")
    for scenario, _ in CONTRIBUTIONS[1:]:
        print(f"\n### {scenario}: household THB XIRR by portfolio; 60/40 household USD and frictions")
        names = [p.name for p in NON_CASH]
        print("| Funding | " + " | ".join(names) + " | 60/40 household USD | 60/40 frictions USD | mean unremitted THB |")
        print("|---|" + "---|" * (len(names) + 3))
        for fs in _funding_rows():
            cell = {r["portfolio"]: r for r in rows if r["scenario"] == scenario and r["funding"] == fs.label}
            sixty = cell["VOO_BND_60_40"]
            print(
                f"| {fs.label} | "
                + " | ".join(_pct(cell[n]["household_xirr_thb"]) for n in names)
                + f" | {_fmt(sixty['household_usd'])} | {_fmt(sixty['frictions_usd'])} | {_fmt(sixty['mean_unremitted_thb'])} |"
            )


def tax_study(inputs: LocalInputs, window: Sequence[date], out: Path) -> None:
    rows: List[Dict[str, object]] = []
    for scenario, amount in CONTRIBUTIONS[:2]:
        schedule = monthly_contribution_schedule(window, amount)
        for row, cost in TAX_ROWS:
            for portfolio in NON_CASH:
                result = _run(inputs, window, portfolio, cost, False, schedule)
                if result is None:
                    raise DataContractError(f"V36_UNEXPECTED_NOT_RUN: {row} {portfolio.name}.")
                m = _metrics(result)
                rows.append(
                    {
                        "scenario": scenario,
                        "row": row,
                        "portfolio": portfolio.name,
                        "terminal_nav": result.terminal_nav,
                        "twr_ann_252": m["twr_ann_252"],
                        "xirr_act365": m["xirr_act365"],
                        "dividends_gross": result.dividends_gross,
                        "withholding": result.withholding,
                    }
                )
    _write(out / "v36_tax.csv", rows)
    print("\n## P1 Withholding scenarios (R2, F0): TWR annualized (withholding USD)")
    for scenario, _ in CONTRIBUTIONS[:2]:
        print(f"\n### {scenario}")
        print("| Portfolio | " + " | ".join(r for r, _ in TAX_ROWS) + " |")
        print("|---|" + "---|" * len(TAX_ROWS))
        for portfolio in NON_CASH:
            cells = [
                next(x for x in rows if x["scenario"] == scenario and x["row"] == r and x["portfolio"] == portfolio.name)
                for r, _ in TAX_ROWS
            ]
            print(
                f"| {portfolio.name} | "
                + " | ".join(f"{_pct(c['twr_ann_252'])} ({_fmt(c['withholding'])})" for c in cells)
                + " |"
            )


def attribution_study(inputs: LocalInputs, window: Sequence[date], rates: Dict[date, Decimal], out: Path) -> None:
    selected = {fs.label: fs for fs in _funding_rows() if fs.label in ("F0", "F1_fee400_s0.5", "F2_fee400_s0.5", "F3_fee400_s0.5")}
    rows: List[Dict[str, object]] = []
    last_closes = {s: inputs.closes[s][window[-1]] for s in ("VOO", "BND", "GLD", "BIL")}
    rate_t, _ = h10_rate(rates, window[-1])
    for scenario, amount in CONTRIBUTIONS[:2]:
        for label, fs in selected.items():
            if scenario == "C0" and label != "F0":
                continue
            plan = plan_funding(window, amount, rates, fs)
            for portfolio in NON_CASH:
                result = _run(inputs, window, portfolio, R2_COST, False, plan.contributions)
                if result is None:
                    raise DataContractError(f"V36_UNEXPECTED_NOT_RUN: {portfolio.name}.")
                broker = broker_attribution(result, D6_INITIAL_NAV, last_closes)
                household = household_attribution(plan, broker, result.terminal_nav, rate_t)
                rows.append({"scenario": scenario, "funding": label, "portfolio": portfolio.name, **broker, **{f"hh_{k}": v for k, v in household.items()}})
    keys: List[str] = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    _write(out / "v36_attribution.csv", [{k: r.get(k, "") for k in keys} for r in rows])
    print("\n## P2 Accounting attribution (R2; USD; identities verified every row)")
    print("| C/Funding | Portfolio | Price VOO | Price BND | Price GLD | Price BIL | Distributions | Slippage | Comm+Reg | Bank fees+spread | FX translation | Household |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        dist = sum((D(str(v)) for k, v in r.items() if k.startswith("distributions_")), D("0"))
        fric = sum((D(str(r[f"hh_{k}"])) for k in ("sender_fees", "fx_spread", "intermediary", "cent_rounding")), D("0"))
        print(
            f"| {r['scenario']}/{r['funding']} | {r['portfolio']} | "
            + " | ".join(_fmt(r.get(f"price_{s}", "")) for s in ("VOO", "BND", "GLD", "BIL"))
            + f" | {_fmt(dist)} | {_fmt(r['slippage'])} | {_fmt(D(str(r['commissions'])) + D(str(r['regulatory_fees'])))} | "
            f"{_fmt(fric)} | {_fmt(r['hh_fx_translation'])} | {_fmt(r['hh_household_usd'])} |"
        )


def subperiod_study(inputs: LocalInputs, out: Path) -> None:
    rows: List[Dict[str, object]] = []
    for name, start, end in WINDOWS:
        window = list(official_sessions(start, end))
        for scenario, amount in CONTRIBUTIONS[:2]:
            schedule = monthly_contribution_schedule(window, amount)
            for portfolio in D6_REGISTERED_PORTFOLIOS:
                result = _run(inputs, window, portfolio, R2_COST, False, schedule)
                if result is None:
                    raise DataContractError(f"V36_UNEXPECTED_NOT_RUN: {portfolio.name}.")
                m = _metrics(result)
                mean_nav = sum((r.nav for r in result.nav_curve), D("0")) / D(len(result.nav_curve))
                rows.append(
                    {
                        "window": name,
                        "sessions": len(window),
                        "scenario": scenario,
                        "portfolio": portfolio.name,
                        **m,
                        "turnover": sum((t.notional for t in result.trades), D("0")) / mean_nav,
                    }
                )
    _write(out / "v36_subperiods.csv", rows)
    print("\n## P2 Subperiods (fresh USD 1,000 per window; R2; C0 metrics, C1 XIRR)")
    for name, _, _ in WINDOWS:
        cell = [r for r in rows if r["window"] == name and r["scenario"] == "C0"]
        c1 = {r["portfolio"]: r for r in rows if r["window"] == name and r["scenario"] == "C1"}
        print(f"\n### {name} ({cell[0]['sessions']} sessions)")
        print("| Portfolio | Cum TWR | Ann TWR | Vol | MaxDD | Turnover | Comm+Reg | C1 XIRR |")
        print("|---|---|---|---|---|---|---|---|")
        for r in cell:
            fees = D(str(r["commissions"])) + D(str(r["regulatory_fees"]))
            print(
                f"| {r['portfolio']} | {_pct(r['twr_total'])} | {_pct(r['twr_ann_252'])} | {_pct(r['twr_vol_252'])} | "
                f"{_pct(r['twr_max_drawdown'])} | {D(str(r['turnover'])):.2f}x | {_fmt(fees)} | {_pct(c1[r['portfolio']]['xirr_act365'])} |"
            )
        order = sorted(cell, key=lambda r: (-D(str(r["twr_ann_252"])), str(r["portfolio"])))
        print("- ranking: " + " > ".join(str(r["portfolio"]) for r in order))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--h10", type=Path, required=True)
    parser.add_argument("--v35-grid", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if any(args.out.iterdir()):
        raise SystemExit(f"refusing non-empty output dir {args.out}")
    files = {n: args.data / n for n in ("bars_raw.csv", "distributions.csv", "splits.csv")}
    print("## Inputs")
    for name, path in files.items():
        print(f"- `{name}` sha256 `{_sha(path)}`")
    print(f"- H.10 page sha256 `{hashlib.sha256(args.h10.read_bytes()).hexdigest()}`")
    print(f"- V35 grid snapshot sha256 `{_sha(args.v35_grid)}`")
    inputs = load_local_inputs(files["bars_raw.csv"], files["distributions.csv"], files["splits.csv"])
    rates = parse_h10_rates(args.h10.read_text(encoding="utf-8"))
    window = list(official_sessions(date(2016, 1, 1), date(2025, 12, 31)))
    cost_audit(inputs, window, args.v35_grid, args.out)
    funding_study(inputs, window, rates, args.out)
    tax_study(inputs, window, args.out)
    attribution_study(inputs, window, rates, args.out)
    subperiod_study(inputs, args.out)


if __name__ == "__main__":
    main()
