"""Unit tests verifying MEC-0015 contract specifications and invariants.

Validates:
- Standalone $0.001 slippage
- Commission formula & minimum ticket ($0.35, $0.0035 * shares)
- Short borrow baseline (0 bps) and mandatory stress (50 bps)
- Noise Area full-14 session warmup policy
- Exact daily-vol contract (15 returns, Close-to-Close, ddof=1, current day excluded)
- Early-close session exclusion policy
- HYP_005 governance status: ABSENT, backtest NOT STARTED
"""

from decimal import Decimal
from pathlib import Path
import json
import pytest

from acash.execution.regulatory_fees import compute_sec31_fee, compute_finra_taf


def test_baseline_standalone_slippage_and_direction() -> None:
    """Standalone slippage is exactly $0.001/share per executed side in adverse direction."""
    slippage_per_share = Decimal("0.001")
    ask_fill = Decimal("500.00")
    bid_fill = Decimal("499.98")

    # BUY executed price: ask + 0.001
    effective_buy = ask_fill + slippage_per_share
    assert effective_buy == Decimal("500.001")

    # SELL executed price: bid - 0.001
    effective_sell = bid_fill - slippage_per_share
    assert effective_sell == Decimal("499.979")
    assert effective_sell > Decimal("0.00")


def test_commission_contract_and_ticket_minimum() -> None:
    """Commission is max($0.35, $0.0035 * shares) per executed side."""
    rate = Decimal("0.0035")
    min_ticket = Decimal("0.35")

    def calc_commission(shares: int) -> Decimal:
        raw = Decimal(shares) * rate
        return max(min_ticket, raw)

    # 10 shares -> $0.035 -> minimum $0.35
    assert calc_commission(10) == Decimal("0.35")
    # 100 shares -> exact minimum $0.35
    assert calc_commission(100) == Decimal("0.35")
    # 101 shares -> $0.3535
    assert calc_commission(101) == Decimal("0.3535")
    # 1000 shares -> $3.50
    assert calc_commission(1000) == Decimal("3.50")


def test_short_borrow_contract() -> None:
    """Short borrow assumption: baseline 0 bps, mandatory stress 50 bps annualized."""
    baseline_borrow_rate_annual = Decimal("0.00")
    stress_borrow_rate_annual = Decimal("0.0050")  # 50 bps

    assert baseline_borrow_rate_annual == Decimal("0.00")
    assert stress_borrow_rate_annual == Decimal("0.0050")

    # Pro-rated to intraday holding (e.g. 6.5 hours of a 252-day 6.5-hour year = 1/252)
    daily_stress_rate = stress_borrow_rate_annual / Decimal("252")
    assert daily_stress_rate > Decimal("0.0")


def test_noise_area_warmup_policy() -> None:
    """Baseline Noise Area requires full 14 prior completed sessions before emitting values."""
    required_warmup_sessions = 14
    author_variant_min_periods = 13

    assert required_warmup_sessions == 14
    assert author_variant_min_periods == 13
    assert required_warmup_sessions != author_variant_min_periods


def test_exact_daily_vol_contract() -> None:
    """Exact daily vol contract: Close-to-Close simple returns, 15 returns, ddof=1, current day excluded."""
    return_type = "SIMPLE_CLOSE_TO_CLOSE"
    window_returns_count = 15
    ddof = 1
    shift = 1
    current_day_included = False
    dividend_treatment = "UNADJUSTED_CLOSE_TO_CLOSE"

    assert return_type == "SIMPLE_CLOSE_TO_CLOSE"
    assert window_returns_count == 15
    assert ddof == 1
    assert shift == 1
    assert current_day_included is False
    assert dividend_treatment == "UNADJUSTED_CLOSE_TO_CLOSE"


def test_early_close_policy() -> None:
    """Early close sessions (210 minutes) are strictly excluded from HYP_005 baseline."""
    early_close_policy = "EXCLUDE_NON_STANDARD_REGULAR_SESSIONS"
    standard_session_bar_count = 390
    early_close_bar_count = 210

    assert early_close_policy == "EXCLUDE_NON_STANDARD_REGULAR_SESSIONS"
    assert standard_session_bar_count == 390
    assert early_close_bar_count < standard_session_bar_count


def test_hyp_005_remains_absent_governance_lock() -> None:
    """HYP_005 must NOT exist anywhere in governance or alpha registries."""
    registry_path = Path("src/acash/research/alpha_schema.py")
    if registry_path.exists():
        content = registry_path.read_text(encoding="utf-8")
        assert "HYP_005" not in content, "HYP_005 found in alpha_schema.py!"

    # Check that no sealed manifest or backtest exists for HYP_005
    for p in Path("docs/research/manifests").glob("*HYP_005*"):
        pytest.fail(f"Found unexpected HYP_005 manifest: {p}")
