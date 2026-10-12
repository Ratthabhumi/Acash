"""Hermetic Synthetic Golden Benchmark Workflow Tests for Milestone M1.6.

Validates end-to-end investment arithmetic on validated synthetic sessions
(2026-10-05 to 2026-10-09, all canonical NYSE trading sessions — weekends
and holidays are rejected, never represented as observations):
1. Starts with USD 1,000 simulated NAV.
2. Holdings-based 60/40 benchmark (VOO/BND) with drifting weights and a
   2:1 VOO split conserved with zero economic loss.
3. BND cash distribution with explicit gross/net separation (15% is an
   EXAMPLE owner rate, never universal) and ex-date/payable-date separation.
4. Exact Treasury accrual golden numbers (ACT/360 == USD 1,000.50).
5. Explicit IBKR Tiered-inspired per-share friction (no universal rule).
6. Cross-currency THB reporting via fail-closed as-of BOT fixings.
7. Deterministic read-only golden report with evidence digest.

No market data, no network, no broker, no real capital.
"""

from datetime import date
from decimal import Decimal
import hashlib
import json
from typing import Dict, List, Set

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.contracts.etf_fx_benchmark import (
    CashAccrualConventionResult,
    CashAccrualModel,
    DayCountConvention,
    DistributionTaxClassification,
    EtfDistributionRecord,
    EtfSplitRecord,
    FxFixingRecord,
    HoldingsBasedBenchmark,
    HOLDINGS_BENCHMARK_CLASSIFICATION,
    IBKR_COST_MODEL_CLASSIFICATION,
    KNOWN_ETF_REGISTRY,
    PriceBasis,
    SmallOrderFrictionModel,
    build_total_return_panel,
    build_valid_synthetic_session_sequence,
    resolve_fx_fixing_for_date,
    validate_synthetic_trading_session,
)


VALID_SYNTHETIC_WEEK = [
    date(2026, 10, 5),
    date(2026, 10, 6),
    date(2026, 10, 7),
    date(2026, 10, 8),
    date(2026, 10, 9),
]

WEEK_PRICES_VOO = {
    VALID_SYNTHETIC_WEEK[0]: Decimal("100.00"),
    VALID_SYNTHETIC_WEEK[1]: Decimal("50.00"),   # post 2:1 split
    VALID_SYNTHETIC_WEEK[2]: Decimal("51.00"),
    VALID_SYNTHETIC_WEEK[3]: Decimal("51.00"),
    VALID_SYNTHETIC_WEEK[4]: Decimal("49.00"),
}

WEEK_PRICES_BND = {
    VALID_SYNTHETIC_WEEK[0]: Decimal("80.00"),
    VALID_SYNTHETIC_WEEK[1]: Decimal("80.00"),
    VALID_SYNTHETIC_WEEK[2]: Decimal("79.50"),   # $0.50 gross distribution ex-date
    VALID_SYNTHETIC_WEEK[3]: Decimal("80.00"),
    VALID_SYNTHETIC_WEEK[4]: Decimal("80.20"),
}

# Gross $0.50 distribution, ex-date Day 3, payable Day 5.
# Net $0.425 reflects an EXPLICIT 15% example owner rate (owner-specific,
# treaty-dependent — never a universal assumption).
WEEK_BND_DISTRIBUTION = EtfDistributionRecord(
    symbol="BND",
    ex_date=VALID_SYNTHETIC_WEEK[2],
    payable_date=VALID_SYNTHETIC_WEEK[4],
    gross_amount=Decimal("0.50"),
    net_amount=Decimal("0.425"),
    withholding_rate=Decimal("0.15"),
    tax_classification=DistributionTaxClassification.NET_AFTER_WITHHOLDING,
)

WEEK_VOO_SPLIT = EtfSplitRecord(
    symbol="VOO",
    ex_date=VALID_SYNTHETIC_WEEK[1],
    split_from=Decimal("1.0"),
    split_to=Decimal("2.0"),
)


def _friction_model() -> SmallOrderFrictionModel:
    return SmallOrderFrictionModel()


def _init_6040() -> HoldingsBasedBenchmark:
    bench = HoldingsBasedBenchmark(
        target_weights={"VOO": Decimal("0.60"), "BND": Decimal("0.40")},
        rebalance_dates=set(),
        friction_model=_friction_model(),
    )
    bench.initialize(
        nav=Decimal("1000.00"),
        prices={"VOO": WEEK_PRICES_VOO[VALID_SYNTHETIC_WEEK[0]],
                "BND": WEEK_PRICES_BND[VALID_SYNTHETIC_WEEK[0]]},
        trading_date=VALID_SYNTHETIC_WEEK[0],
    )
    return bench


def test_synthetic_calendar_rejects_weekends_and_holidays() -> None:
    # 2026-10-03 is a Saturday, 2026-10-04 a Sunday: never ETF sessions.
    with pytest.raises(DataContractError, match="INVALID_SESSION_DATE"):
        validate_synthetic_trading_session(date(2026, 10, 3))
    with pytest.raises(DataContractError, match="INVALID_SESSION_DATE"):
        validate_synthetic_trading_session(date(2026, 10, 4))
    # Thanksgiving 2026 is an official NYSE holiday.
    with pytest.raises(DataContractError, match="INVALID_SESSION_DATE"):
        validate_synthetic_trading_session(date(2026, 11, 26))
    # The golden week is all valid canonical sessions.
    assert list(build_valid_synthetic_session_sequence(VALID_SYNTHETIC_WEEK)) == VALID_SYNTHETIC_WEEK
    # Non-monotonic and empty sequences fail closed.
    with pytest.raises(DataContractError, match="Non-monotonic"):
        build_valid_synthetic_session_sequence([VALID_SYNTHETIC_WEEK[1], VALID_SYNTHETIC_WEEK[0]])
    with pytest.raises(DataContractError, match="cannot be empty"):
        build_valid_synthetic_session_sequence([])


def test_fx_fixing_asof_resolution_fail_closed() -> None:
    fixings = {
        VALID_SYNTHETIC_WEEK[0]: FxFixingRecord(
            fixing_date=VALID_SYNTHETIC_WEEK[0], base_currency="USD",
            quote_currency="THB", rate=Decimal("36.50"), source="BOT",
        ),
    }
    assert resolve_fx_fixing_for_date(fixings, VALID_SYNTHETIC_WEEK[0]).rate == Decimal("36.50")
    # A missing fixing is a genuine omission: no silent same-day fallback.
    with pytest.raises(DataContractError, match="MISSING_FX_FIXING"):
        resolve_fx_fixing_for_date(fixings, VALID_SYNTHETIC_WEEK[1])


def test_cash_accrual_golden_act360_exact() -> None:
    result = CashAccrualConventionResult(
        principal=Decimal("1000"), annual_rate=Decimal("0.045"), days=4
    )
    # 1000 * 0.045 * 4/360 = 0.50 exactly; ending NAV = 1000.50 exactly.
    assert result.act_360_interest == Decimal("0.50")
    assert result.act_360_ending_nav == Decimal("1000.50")


def test_cash_accrual_act365_distinct_not_equivalent() -> None:
    result = CashAccrualConventionResult(
        principal=Decimal("1000"), annual_rate=Decimal("0.045"), days=4
    )
    # 1000 * 0.045 * 4/365 = 180/365 = 36/73 ≈ 0.4931506849 (non-terminating).
    assert abs(result.act_365_interest - (Decimal("36") / Decimal("73"))) < Decimal("1e-12")
    assert result.act_365_ending_nav.quantize(Decimal("0.0000000001")) == Decimal("1000.4931506849")
    # The conventions are NOT interchangeable.
    assert result.act_360_interest != result.act_365_interest
    assert result.act_360_ending_nav != result.act_365_ending_nav


def test_holdings_initial_cash_and_share_quantities_exact() -> None:
    bench = _init_6040()
    # Targets were VOO 6 @ $100 ($600) + BND 5 @ $80 ($400) = $1000 stock,
    # plus $1.40 friction > $1000 cash, so the largest position (VOO) trimmed
    # by exactly one whole share: VOO 5, BND 5.
    # VOO buy friction: max(5*0.0035, 0.35) + 500*0.0007 = 0.35 + 0.35 = 0.70.
    # BND buy friction: max(5*0.0035, 0.35) + 400*0.0007 = 0.35 + 0.28 = 0.63.
    assert bench._shares == {"VOO": Decimal("5"), "BND": Decimal("5")}
    assert bench._cash == Decimal("98.67")
    assert bench.nav_history[-1] == Decimal("998.67")
    assert len(bench.transactions) == 2
    assert all(t.reason == "INITIAL_ALLOCATION" for t in bench.transactions)
    assert bench.model_classification == HOLDINGS_BENCHMARK_CLASSIFICATION


def test_buy_and_hold_weight_drift_and_zero_trades() -> None:
    bench = _init_6040()
    initial_weights = bench.weight_history[-1]
    for day in VALID_SYNTHETIC_WEEK[1:]:
        prices = {"VOO": WEEK_PRICES_VOO[day], "BND": WEEK_PRICES_BND[day]}
        if day == VALID_SYNTHETIC_WEEK[1]:
            bench.apply_split("VOO", Decimal("2.0"))
        bench.step(day, prices)
    # Prices moved: weights must have drifted away from the Day-1 snapshot.
    assert bench.weight_history[-1] != initial_weights
    # No scheduled rebalances: exactly the 2 initial transactions, shares static.
    assert len(bench.transactions) == 2
    assert bench._shares == {"VOO": Decimal("10"), "BND": Decimal("5")}


def test_monthly_vs_quarterly_rebalance_semantics() -> None:
    month_ends = [date(2026, 9, 30), date(2026, 10, 30), date(2026, 11, 30), date(2026, 12, 31)]
    assert list(build_valid_synthetic_session_sequence(month_ends)) == month_ends
    voo = {month_ends[0]: Decimal("100"), month_ends[1]: Decimal("102"),
           month_ends[2]: Decimal("101"), month_ends[3]: Decimal("110")}
    bnd = {month_ends[0]: Decimal("80"), month_ends[1]: Decimal("80"),
           month_ends[2]: Decimal("81"), month_ends[3]: Decimal("81")}

    def run(rebalance_dates: Set[date]) -> HoldingsBasedBenchmark:
        bench = HoldingsBasedBenchmark(
            target_weights={"VOO": Decimal("0.60"), "BND": Decimal("0.40")},
            rebalance_dates=rebalance_dates,
            friction_model=_friction_model(),
        )
        bench.initialize(
            nav=Decimal("10000.00"),
            prices={"VOO": voo[month_ends[0]], "BND": bnd[month_ends[0]]},
            trading_date=month_ends[0],
        )
        for day in month_ends[1:]:
            bench.step(day, {"VOO": voo[day], "BND": bnd[day]})
        return bench

    monthly = run({month_ends[1], month_ends[2], month_ends[3]})
    quarterly = run({month_ends[3]})
    monthly_rebalances = [t for t in monthly.transactions if t.reason == "SCHEDULED_REBALANCE"]
    quarterly_rebalances = [t for t in quarterly.transactions if t.reason == "SCHEDULED_REBALANCE"]
    # Oct 30 drift is sub-share (whole-share quantization): scheduled date
    # with zero trades. Nov 30 and Dec 31 execute; quarterly only Dec 31.
    assert {t.trading_date for t in monthly_rebalances} == {month_ends[2], month_ends[3]}
    assert {t.trading_date for t in quarterly_rebalances} == {month_ends[3]}
    assert len(monthly.transactions) == 6
    assert len(quarterly.transactions) == 4
    # Different trading implies different terminal NAVs (friction + timing).
    assert monthly.nav_history[-1] == Decimal("10639.5185")
    assert quarterly.nav_history[-1] == Decimal("10631.4026")


def test_friction_only_when_trading() -> None:
    # Step through a flat week with no rebalances and no distributions:
    # NAV moves only with prices; friction is recorded exactly once (init).
    bench = HoldingsBasedBenchmark(
        target_weights={"VOO": Decimal("0.60"), "BND": Decimal("0.40")},
        rebalance_dates=set(),
        friction_model=_friction_model(),
    )
    bench.initialize(
        nav=Decimal("1000.00"),
        prices={"VOO": Decimal("100.00"), "BND": Decimal("80.00")},
        trading_date=VALID_SYNTHETIC_WEEK[0],
    )
    for day in VALID_SYNTHETIC_WEEK[1:]:
        bench.step(day, {"VOO": Decimal("100.00"), "BND": Decimal("80.00")})
    assert len(bench.transactions) == 2
    # 0.70 VOO + 0.63 BND initial friction only; stepping adds nothing.
    assert sum((t.friction_cost for t in bench.transactions), Decimal("0")) == Decimal("1.33")


def test_split_value_conservation_holdings() -> None:
    bench = HoldingsBasedBenchmark(
        target_weights={"VOO": Decimal("1.0")},
        rebalance_dates=set(),
        friction_model=_friction_model(),
    )
    bench.initialize(
        nav=Decimal("1000.00"),
        prices={"VOO": Decimal("100.00")},
        trading_date=VALID_SYNTHETIC_WEEK[0],
    )
    # 10 shares @ $100 = $1000 stock; friction max(10*0.0035,0.35)+1000*0.0007
    # = 0.35 + 0.70 = 1.05 > $0 residual -> trim to 9 shares.
    assert bench._shares == {"VOO": Decimal("9")}
    nav_before_split = bench.nav_history[-1]
    bench.apply_split("VOO", Decimal("2.0"))
    assert bench._shares == {"VOO": Decimal("18")}
    # Post-split $50 price on the doubled share count preserves position value.
    nav_after = bench.step(VALID_SYNTHETIC_WEEK[1], {"VOO": Decimal("50.00")})
    assert nav_after == nav_before_split


def test_distribution_ex_payable_separation() -> None:
    bench = _init_6040()
    bench.apply_split("VOO", WEEK_VOO_SPLIT.split_ratio)
    bench.step(
        VALID_SYNTHETIC_WEEK[1],
        {"VOO": WEEK_PRICES_VOO[VALID_SYNTHETIC_WEEK[1]],
         "BND": WEEK_PRICES_BND[VALID_SYNTHETIC_WEEK[1]]},
    )
    cash_after_init = bench._cash
    # Day 3 (ex-date): entitlement booked as receivable, NOT cash.
    bench.step(
        VALID_SYNTHETIC_WEEK[2],
        {"VOO": WEEK_PRICES_VOO[VALID_SYNTHETIC_WEEK[2]],
         "BND": WEEK_PRICES_BND[VALID_SYNTHETIC_WEEK[2]]},
        distributions=[WEEK_BND_DISTRIBUTION],
    )
    # 5 BND shares x $0.425 net = $2.125 receivable; cash untouched by dividend.
    assert bench.outstanding_receivables() == {("BND", VALID_SYNTHETIC_WEEK[4]): Decimal("2.125")}
    assert bench._cash == cash_after_init
    # NAV includes the receivable: 10*51 + 5*79.50 + 98.67 + 2.125 = 1008.295.
    assert bench.nav_history[-1] == Decimal("1008.295")
    # Day 5 (payable date): receivable settles into cash, none outstanding.
    bench.step(
        VALID_SYNTHETIC_WEEK[4],
        {"VOO": WEEK_PRICES_VOO[VALID_SYNTHETIC_WEEK[4]],
         "BND": WEEK_PRICES_BND[VALID_SYNTHETIC_WEEK[4]]},
        distributions=[WEEK_BND_DISTRIBUTION],
    )
    assert bench.outstanding_receivables() == {}
    assert bench._cash == cash_after_init + Decimal("2.125")
    # 10*49 + 5*80.20 + 100.795 = 991.795.
    assert bench.nav_history[-1] == Decimal("991.795")


def test_missing_price_fail_closed() -> None:
    bench = _init_6040()
    with pytest.raises(DataContractError, match="MISSING_PRICE"):
        bench.step(VALID_SYNTHETIC_WEEK[1], {"VOO": Decimal("50.00")})
    with pytest.raises(DataContractError, match="MISSING_PRICE"):
        bench.step(VALID_SYNTHETIC_WEEK[1], {"VOO": Decimal("0"), "BND": Decimal("80.00")})


def test_infeasible_rebalance_no_borrowing() -> None:
    # $10 cannot fund even one whole share at $100 plus friction.
    bench = HoldingsBasedBenchmark(
        target_weights={"VOO": Decimal("1.0")},
        rebalance_dates=set(),
        friction_model=_friction_model(),
    )
    with pytest.raises(DataContractError, match="INSUFFICIENT_CASH"):
        bench.initialize(
            nav=Decimal("10.00"),
            prices={"VOO": Decimal("100.00")},
            trading_date=VALID_SYNTHETIC_WEEK[0],
        )
    # Scheduled rebalance demanding net buys beyond cash fails closed.
    # Init $901.33 @ VOO 100/BND 80 sizes VOO 5 + BND 4 ($80.056 residual).
    # Rebalance day at VOO 80/BND 80 sizes a 6-share VOO target: the 1-share
    # buy ($80.406 with friction) exceeds $80.056 cash with no sales to fund it.
    bench2 = HoldingsBasedBenchmark(
        target_weights={"VOO": Decimal("0.60"), "BND": Decimal("0.40")},
        rebalance_dates={VALID_SYNTHETIC_WEEK[1]},
        friction_model=_friction_model(),
    )
    bench2.initialize(
        nav=Decimal("901.33"),
        prices={"VOO": Decimal("100.00"), "BND": Decimal("80.00")},
        trading_date=VALID_SYNTHETIC_WEEK[0],
    )
    assert bench2._cash == Decimal("80.056")
    with pytest.raises(DataContractError, match="INSUFFICIENT_CASH"):
        bench2.step(
            VALID_SYNTHETIC_WEEK[1],
            {"VOO": Decimal("80.00"), "BND": Decimal("80.00")},
        )


def test_deterministic_lineage() -> None:
    def run_once() -> HoldingsBasedBenchmark:
        bench = _init_6040()
        for day in VALID_SYNTHETIC_WEEK[1:]:
            prices = {"VOO": WEEK_PRICES_VOO[day], "BND": WEEK_PRICES_BND[day]}
            if day == VALID_SYNTHETIC_WEEK[1]:
                bench.apply_split("VOO", Decimal("2.0"))
            dists = [WEEK_BND_DISTRIBUTION] if day in (
                VALID_SYNTHETIC_WEEK[2], VALID_SYNTHETIC_WEEK[4]) else None
            bench.step(day, prices, distributions=dists)
        return bench

    first, second = run_once(), run_once()
    assert first.nav_history == second.nav_history
    assert first.date_history == second.date_history
    assert len(first.transactions) == len(second.transactions)
    assert [(t.symbol, t.shares_delta, t.price) for t in first.transactions] == [
        (t.symbol, t.shares_delta, t.price) for t in second.transactions
    ]


def test_synthetic_golden_benchmark_workflow_usd1000() -> None:
    initial_nav_usd = Decimal("1000.00")

    # Build Total Return Panels (ex-date-based TR convention) for reference.
    voo_panel = build_total_return_panel(
        KNOWN_ETF_REGISTRY["VOO"],
        [(d, WEEK_PRICES_VOO[d]) for d in VALID_SYNTHETIC_WEEK],
        splits=[WEEK_VOO_SPLIT],
        price_basis=PriceBasis.RAW_UNADJUSTED_PRICE,
    )
    assert voo_panel[1].total_return_factor == Decimal("1.0")  # split conserved

    # Holdings-based BM-6040 golden path (hand-verified day by day).
    bench = _init_6040()
    bench.apply_split("VOO", WEEK_VOO_SPLIT.split_ratio)
    for day in VALID_SYNTHETIC_WEEK[1:]:
        prices = {"VOO": WEEK_PRICES_VOO[day], "BND": WEEK_PRICES_BND[day]}
        dists = [WEEK_BND_DISTRIBUTION] if day in (
            VALID_SYNTHETIC_WEEK[2], VALID_SYNTHETIC_WEEK[4]) else None
        bench.step(day, prices, distributions=dists)

    # Day-by-day NAV (shares VOO 10 / BND 5 after split; cash 98.67):
    # Oct 6: 10*50 + 5*80 + 98.67 = 998.67
    # Oct 7: 10*51 + 5*79.50 + 98.67 + 2.125 receivable = 1008.295
    # Oct 8: 10*51 + 5*80 + 98.67 + 2.125 = 1010.795
    # Oct 9: 10*49 + 5*80.20 + (98.67 + 2.125 settled) = 991.795
    expected_navs = [
        Decimal("998.67"),
        Decimal("998.67"),
        Decimal("1008.295"),
        Decimal("1010.795"),
        Decimal("991.795"),
    ]
    assert bench.nav_history == expected_navs
    assert bench.outstanding_receivables() == {}
    assert bench._shares == {"VOO": Decimal("10"), "BND": Decimal("5")}

    # VOO buy-and-hold via the same engine: 9 shares @ $100 (trimmed from 10),
    # cash 99.02, split to 18 shares on Oct 6.
    voo_bh = HoldingsBasedBenchmark(
        target_weights={"VOO": Decimal("1.0")},
        rebalance_dates=set(),
        friction_model=_friction_model(),
    )
    voo_bh.initialize(
        nav=initial_nav_usd, prices={"VOO": Decimal("100.00")},
        trading_date=VALID_SYNTHETIC_WEEK[0],
    )
    assert voo_bh._shares == {"VOO": Decimal("9")}
    voo_bh.apply_split("VOO", Decimal("2.0"))
    for day in VALID_SYNTHETIC_WEEK[1:]:
        voo_bh.step(day, {"VOO": WEEK_PRICES_VOO[day]})
    # 18*49 + 99.02 = 882 + 99.02 = 981.02.
    assert voo_bh.nav_history[-1] == Decimal("981.02")

    # Treasury golden: exact ACT/360 ending NAV.
    tbill = CashAccrualModel(annual_rate=Decimal("0.045"), convention=DayCountConvention.ACT_360)
    bm_tbill_final_nav = initial_nav_usd + tbill.accrue(initial_nav_usd, days=4)
    assert bm_tbill_final_nav == Decimal("1000.50")

    # Drawdowns (strict canonical formula, local helper).
    def compute_max_drawdown(nav_series: List[Decimal]) -> Decimal:
        peak = nav_series[0]
        max_dd = Decimal("0.0")
        for val in nav_series:
            if val > peak:
                peak = val
            if peak > Decimal("0"):
                dd = (peak - val) / peak
                if dd > max_dd:
                    max_dd = dd
        return max_dd

    assert compute_max_drawdown([initial_nav_usd] * 5) == Decimal("0.0")
    assert compute_max_drawdown(voo_bh.nav_history) > Decimal("0.0")
    assert compute_max_drawdown(bench.nav_history) > Decimal("0.0")

    # THB reporting via fail-closed as-of fixings.
    thb_fixings = {
        day: FxFixingRecord(
            fixing_date=day, base_currency="USD", quote_currency="THB",
            rate=rate, source="BOT",
        )
        for day, rate in zip(
            VALID_SYNTHETIC_WEEK,
            [Decimal("36.50"), Decimal("36.55"), Decimal("36.60"),
             Decimal("36.45"), Decimal("36.52")],
        )
    }
    thb_nav_6040 = [
        resolve_fx_fixing_for_date(thb_fixings, day).convert(usd_val, "USD", "THB")
        for day, usd_val in zip(VALID_SYNTHETIC_WEEK, bench.nav_history)
    ]
    # 991.795 * 36.52 = 36220.35340 -> 36220.35.
    assert thb_nav_6040[-1].quantize(Decimal("0.01")) == Decimal("36220.35")

    # Deterministic golden report.
    results_map: Dict[str, Dict[str, str]] = {
        "BM-ZERO-CASH": {
            "final_nav_usd": "1000.00",
            "total_return_pct": "0.0000",
            "max_drawdown_pct": "0.0000",
            "calmar_status": "CALMAR_UNDEFINED_ZERO_DRAWDOWN",
        },
        "BM-TBILL-THEORETICAL": {
            "final_nav_usd": str(bm_tbill_final_nav),
            "total_return_pct": str((bm_tbill_final_nav - initial_nav_usd) / initial_nav_usd * 100),
        },
        "BM-SP500-VOO-HOLDINGS": {
            "final_nav_usd": str(voo_bh.nav_history[-1]),
            "max_drawdown_pct": str(compute_max_drawdown(voo_bh.nav_history) * 100),
        },
        "BM-6040-HOLDINGS": {
            "final_nav_usd": str(bench.nav_history[-1]),
            "final_nav_thb": str(thb_nav_6040[-1].quantize(Decimal("0.01"))),
            "total_return_pct": str((bench.nav_history[-1] - initial_nav_usd) / initial_nav_usd * 100),
            "max_drawdown_pct": str(compute_max_drawdown(bench.nav_history) * 100),
            "initial_friction_usd": "1.33",
            "price_basis": PriceBasis.RAW_UNADJUSTED_PRICE.value,
        },
    }
    report_dict: Dict[str, object] = {
        "milestone": "M1.6",
        "scenario": "SYNTHETIC_GOLDEN_BENCHMARK_USD1000",
        "initial_nav_usd": str(initial_nav_usd),
        "as_of_start": str(VALID_SYNTHETIC_WEEK[0]),
        "as_of_end": str(VALID_SYNTHETIC_WEEK[-1]),
        "universe": ["VOO", "BND"],
        "price_basis": PriceBasis.RAW_UNADJUSTED_PRICE.value,
        "sessions": [str(d) for d in build_valid_synthetic_session_sequence(VALID_SYNTHETIC_WEEK)],
        "results": results_map,
    }
    serialized = json.dumps(report_dict, sort_keys=True)
    report_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    assert len(report_hash) == 64
    assert results_map["BM-ZERO-CASH"]["calmar_status"] == "CALMAR_UNDEFINED_ZERO_DRAWDOWN"
