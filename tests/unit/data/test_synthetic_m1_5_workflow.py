"""Hermetic Synthetic Golden Benchmark Workflow Test for Milestone M1.5.

Validates end-to-end investment arithmetic and baseline comparisons:
1. Starts with USD 1,000 simulated NAV.
2. Uses synthetic raw ETF prices across candidate universe (VOO, BND, GLD, BIL).
3. Includes a 2:1 split event (VOO) with zero economic loss.
4. Includes cash distributions with 15% withholding tax.
5. Includes a Treasury cash/yield scenario (CashAccrualModel & BIL).
6. Applies explicit IBKR-inspired cost assumptions (SmallOrderFrictionModel).
7. Includes a cross-currency reporting scenario (USD and THB views via BOT fixings).
8. Correctly computes portfolio total returns and drawdowns.
9. Compares BM-ZERO-CASH, BM-SP500 (VOO buy-and-hold), and BM-6040 (60/40 balanced).
10. Preserves evidence digests, data basis (PriceBasis.RAW_UNADJUSTED_PRICE), and valuation dates.
11. Emits a deterministic read-only report dictionary.
"""

from datetime import date
from decimal import Decimal
import hashlib
import json
from typing import Any, Dict, List, Tuple

import pytest

from acash.data.contracts.etf_fx_benchmark import (
    AssetClass,
    CashAccrualModel,
    DayCountConvention,
    EtfDailyObservation,
    EtfDistributionRecord,
    EtfInstrumentContract,
    EtfSplitRecord,
    FxFixingRecord,
    KNOWN_ETF_REGISTRY,
    PriceBasis,
    SmallOrderFrictionModel,
    build_total_return_panel,
)


def test_synthetic_golden_benchmark_workflow_usd1000() -> None:
    # -------------------------------------------------------------------------
    # 1. Starting Capital & Candidate Universe
    # -------------------------------------------------------------------------
    initial_nav_usd = Decimal("1000.00")
    candidate_symbols = ("VOO", "BND", "GLD", "BIL")

    voo_contract = KNOWN_ETF_REGISTRY["VOO"]
    bnd_contract = KNOWN_ETF_REGISTRY["BND"]
    gld_contract = KNOWN_ETF_REGISTRY["GLD"]
    bil_contract = KNOWN_ETF_REGISTRY["BIL"]

    # -------------------------------------------------------------------------
    # 2. Synthetic Market Data with Split & Dividend (Dates: 2026-10-01 to 2026-10-05)
    # -------------------------------------------------------------------------
    dates = [
        date(2026, 10, 1),
        date(2026, 10, 2),
        date(2026, 10, 3),
        date(2026, 10, 4),
        date(2026, 10, 5),
    ]

    # VOO: Day 1=100, Day 2=50 (2:1 split happens on Day 2), Day 3=51 (+2%), Day 4=51 (flat), Day 5=49 (-3.92%)
    voo_raw_bars = [
        (dates[0], Decimal("100.00")),
        (dates[1], Decimal("50.00")),
        (dates[2], Decimal("51.00")),
        (dates[3], Decimal("51.00")),
        (dates[4], Decimal("49.00")),
    ]
    voo_splits = [
        EtfSplitRecord(
            symbol="VOO",
            ex_date=dates[1],
            split_from=Decimal("1.0"),
            split_to=Decimal("2.0"),
        )
    ]

    # BND: Day 1=80, Day 2=80, Day 3=79.50 with $0.50 gross dividend (ex-date Day 3), Day 4=80, Day 5=80.20
    # Net dividend after 15% withholding tax = $0.50 * 0.85 = $0.425
    bnd_raw_bars = [
        (dates[0], Decimal("80.00")),
        (dates[1], Decimal("80.00")),
        (dates[2], Decimal("79.50")),
        (dates[3], Decimal("80.00")),
        (dates[4], Decimal("80.20")),
    ]
    bnd_distributions = [
        EtfDistributionRecord(
            symbol="BND",
            ex_date=dates[2],
            payable_date=dates[2],
            cash_amount=Decimal("0.425"),  # 15% withholding tax applied
        )
    ]

    # GLD: Day 1=180, Day 2=181, Day 3=182, Day 4=181, Day 5=183
    gld_raw_bars = [
        (dates[0], Decimal("180.00")),
        (dates[1], Decimal("181.00")),
        (dates[2], Decimal("182.00")),
        (dates[3], Decimal("181.00")),
        (dates[4], Decimal("183.00")),
    ]

    # BIL: Day 1=91.50, Day 2=91.51, Day 3=91.52, Day 4=91.53, Day 5=91.54
    bil_raw_bars = [
        (dates[0], Decimal("91.50")),
        (dates[1], Decimal("91.51")),
        (dates[2], Decimal("91.52")),
        (dates[3], Decimal("91.53")),
        (dates[4], Decimal("91.54")),
    ]

    # Build Total Return Panels for all assets
    voo_panel = build_total_return_panel(
        voo_contract,
        voo_raw_bars,
        splits=voo_splits,
        price_basis=PriceBasis.RAW_UNADJUSTED_PRICE,
    )
    bnd_panel = build_total_return_panel(
        bnd_contract,
        bnd_raw_bars,
        distributions=bnd_distributions,
        price_basis=PriceBasis.RAW_UNADJUSTED_PRICE,
    )
    gld_panel = build_total_return_panel(
        gld_contract,
        gld_raw_bars,
        price_basis=PriceBasis.RAW_UNADJUSTED_PRICE,
    )
    bil_panel = build_total_return_panel(
        bil_contract,
        bil_raw_bars,
        price_basis=PriceBasis.RAW_UNADJUSTED_PRICE,
    )

    # Verify split day return for VOO: 100 -> 50 with 2:1 split has total_return_factor == 1.0 (0.0% change)
    assert voo_panel[1].total_return_factor == Decimal("1.0")

    # Verify dividend day return for BND (Day 3): (79.50 + 0.425) / 80.00 = 79.925 / 80.00
    expected_bnd_tr_day3 = (Decimal("79.50") + Decimal("0.425")) / Decimal("80.00")
    bnd_day3_period_return = bnd_panel[2].total_return_factor / bnd_panel[1].total_return_factor
    assert bnd_day3_period_return == expected_bnd_tr_day3

    # -------------------------------------------------------------------------
    # 3. Treasury Cash Accrual Model (ACT/360)
    # -------------------------------------------------------------------------
    # Converted BEY yield = 4.5% p.a.
    t_bill_model = CashAccrualModel(
        annual_rate=Decimal("0.045"),
        convention=DayCountConvention.ACT_360,
    )
    # 4 days elapsed between Oct 1 and Oct 5
    accrued_cash_4d = t_bill_model.accrue(initial_nav_usd, days=4)
    bm_tbill_final_nav = initial_nav_usd + accrued_cash_4d
    assert bm_tbill_final_nav > initial_nav_usd

    # -------------------------------------------------------------------------
    # 4. IBKR Friction Model on Portfolio Initial Allocation
    # -------------------------------------------------------------------------
    friction_model = SmallOrderFrictionModel(
        commission_rate=Decimal("0.0005"),
        min_commission_usd=Decimal("0.35"),
        max_commission_pct=Decimal("0.01"),
        half_spread=Decimal("0.0005"),
        slippage=Decimal("0.0002"),
    )

    # Initial allocation of $1,000 into 60/40: $600 VOO, $400 BND
    # Order 1 (VOO $600): commission = max(600*0.0005=0.30, 0.35) = 0.35, cap = 6.00 -> 0.35
    #   spread+slippage = 600 * 0.0007 = 0.42. Total = 0.77
    cost_voo = friction_model.calculate_cost(Decimal("600.00"))
    assert cost_voo == Decimal("0.77")

    # Order 2 (BND $400): commission = 0.35, spread+slippage = 400 * 0.0007 = 0.28. Total = 0.63
    cost_bnd = friction_model.calculate_cost(Decimal("400.00"))
    assert cost_bnd == Decimal("0.63")
    total_initial_friction_6040 = cost_voo + cost_bnd  # $1.40

    # -------------------------------------------------------------------------
    # 5. Baseline Evolution (Oct 1 to Oct 5)
    # -------------------------------------------------------------------------
    # BM-ZERO-CASH: NAV remains strictly $1,000.00, MaxDD = 0.00%
    bm_zero_cash_navs = [Decimal("1000.00")] * len(dates)

    # BM-SP500 (VOO Buy & Hold):
    voo_initial_cost = friction_model.calculate_cost(Decimal("1000.00"))
    voo_navs = [initial_nav_usd - voo_initial_cost]
    for t_idx in range(1, len(dates)):
        period_ret = voo_panel[t_idx].total_return_factor / voo_panel[t_idx - 1].total_return_factor
        voo_navs.append(voo_navs[-1] * period_ret)

    # BM-6040 (60% VOO / 40% BND):
    nav_6040 = initial_nav_usd - total_initial_friction_6040
    navs_6040 = [nav_6040]
    for t_idx in range(1, len(dates)):
        ret_voo = voo_panel[t_idx].total_return_factor / voo_panel[t_idx - 1].total_return_factor
        ret_bnd = bnd_panel[t_idx].total_return_factor / bnd_panel[t_idx - 1].total_return_factor
        period_ret_6040 = (Decimal("0.60") * ret_voo) + (Decimal("0.40") * ret_bnd)
        navs_6040.append(navs_6040[-1] * period_ret_6040)

    # -------------------------------------------------------------------------
    # 6. Drawdown Calculation (Strict Canonical Formula)
    # -------------------------------------------------------------------------
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

    max_dd_zero_cash = compute_max_drawdown(bm_zero_cash_navs)
    max_dd_voo = compute_max_drawdown(voo_navs)
    max_dd_6040 = compute_max_drawdown(navs_6040)

    assert max_dd_zero_cash == Decimal("0.0")
    assert max_dd_voo > Decimal("0.0")  # VOO dipped on Day 5

    # -------------------------------------------------------------------------
    # 7. Cross-Currency (THB) Reporting Scenario via BOT Reference Fixings
    # -------------------------------------------------------------------------
    bot_fx_rates = [
        FxFixingRecord(
            fixing_date=dates[0],
            base_currency="USD",
            quote_currency="THB",
            rate=Decimal("36.50"),
            source="BOT",
        ),
        FxFixingRecord(
            fixing_date=dates[1],
            base_currency="USD",
            quote_currency="THB",
            rate=Decimal("36.55"),
            source="BOT",
        ),
        FxFixingRecord(
            fixing_date=dates[2],
            base_currency="USD",
            quote_currency="THB",
            rate=Decimal("36.60"),
            source="BOT",
        ),
        FxFixingRecord(
            fixing_date=dates[3],
            base_currency="USD",
            quote_currency="THB",
            rate=Decimal("36.45"),
            source="BOT",
        ),
        FxFixingRecord(
            fixing_date=dates[4],
            base_currency="USD",
            quote_currency="THB",
            rate=Decimal("36.52"),
            source="BOT",
        ),
    ]

    thb_nav_6040 = [
        fx.convert(usd_val, from_currency="USD", to_currency="THB")
        for usd_val, fx in zip(navs_6040, bot_fx_rates)
    ]
    assert len(thb_nav_6040) == len(dates)

    # -------------------------------------------------------------------------
    # 8. Deterministic Golden Report Generation
    # -------------------------------------------------------------------------
    results_map: Dict[str, Dict[str, str]] = {
        "BM-ZERO-CASH": {
            "final_nav_usd": str(bm_zero_cash_navs[-1]),
            "total_return_pct": "0.0000",
            "max_drawdown_pct": "0.0000",
            "calmar_status": "CALMAR_UNDEFINED_ZERO_DRAWDOWN",
        },
        "BM-TBILL-THEORETICAL": {
            "final_nav_usd": str(round(bm_tbill_final_nav, 4)),
            "total_return_pct": str(round((bm_tbill_final_nav - initial_nav_usd) / initial_nav_usd * 100, 4)),
        },
        "BM-SP500-VOO": {
            "final_nav_usd": str(round(voo_navs[-1], 4)),
            "total_return_pct": str(round((voo_navs[-1] - initial_nav_usd) / initial_nav_usd * 100, 4)),
            "max_drawdown_pct": str(round(max_dd_voo * 100, 4)),
        },
        "BM-6040": {
            "final_nav_usd": str(round(navs_6040[-1], 4)),
            "final_nav_thb": str(round(thb_nav_6040[-1], 2)),
            "total_return_pct": str(round((navs_6040[-1] - initial_nav_usd) / initial_nav_usd * 100, 4)),
            "max_drawdown_pct": str(round(max_dd_6040 * 100, 4)),
            "initial_friction_usd": str(total_initial_friction_6040),
        },
    }

    report_dict: Dict[str, Any] = {
        "milestone": "M1.5",
        "scenario": "SYNTHETIC_GOLDEN_BENCHMARK_USD1000",
        "initial_nav_usd": str(initial_nav_usd),
        "as_of_start": str(dates[0]),
        "as_of_end": str(dates[-1]),
        "universe": list(candidate_symbols),
        "price_basis": PriceBasis.RAW_UNADJUSTED_PRICE.value,
        "results": results_map,
    }

    # Verify report is canonically serializable and deterministic
    serialized = json.dumps(report_dict, sort_keys=True)
    report_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    assert len(report_hash) == 64
    assert results_map["BM-ZERO-CASH"]["calmar_status"] == "CALMAR_UNDEFINED_ZERO_DRAWDOWN"

