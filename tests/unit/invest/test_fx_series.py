"""BOT reference FX series orientation, alignment and the exact THB decomposition (synthetic)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, List, Sequence, Tuple

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import fx_series as fx

D1, D2, D3 = date(2026, 11, 2), date(2026, 11, 3), date(2026, 11, 4)


class FakeFx:
    provider_id = "BOT_REFERENCE_FX"

    def __init__(self, rates: Sequence[Tuple[date, str]]) -> None:
        self.rates = list(rates)
        self.calls: List[Tuple[date, int]] = []

    def reference_rates(self, end: date, lookback_days: int = 7) -> List[Any]:
        self.calls.append((end, lookback_days))
        start = end - timedelta(days=lookback_days)
        out = []
        for day, rate in self.rates:
            if start <= day <= end:
                stamp = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
                out.append(_Obs("USD", "THB", Decimal(rate), day, stamp))
                out.append(_Obs("THB", "USD", Decimal(f"{Decimal(1) / Decimal(rate):.10g}"), day, stamp))
        return out


class _Obs:
    def __init__(self, src: str, dst: str, rate: Decimal, day: date, stamp: datetime) -> None:
        self.from_currency, self.to_currency, self.rate, self.market_date = src, dst, rate, day
        self.kind, self.provider_id, self.retrieved_at = "REFERENCE_FX", "BOT_REFERENCE_FX", stamp


def test_series_keeps_only_the_usd_to_thb_direction() -> None:
    series = fx.collect_series(FakeFx([(D1, "33.50"), (D2, "33.73")]), D1, D3)
    assert list(series.rates().items()) == [(D1, Decimal("33.50")), (D2, Decimal("33.73"))]
    summary = series.summary()
    assert summary["orientation"] == "THB_PER_USD" and summary["executable"] is False
    assert summary["points"] == 2 and summary["latest"]["usd_thb"] == "33.73"


def test_conflicting_rate_for_one_date_is_refused() -> None:
    provider = FakeFx([(D1, "33.50")])
    provider.rates.append((D1, "33.90"))
    with pytest.raises(DataContractError, match="FX_CONFLICTING_RATE"):
        fx.collect_series(provider, D1, D3)


def test_chunking_issues_one_request_per_window() -> None:
    provider = FakeFx([(date(2026, 1, 2), "34.10")])
    fx.collect_series(provider, date(2026, 1, 1), date(2026, 12, 31), chunk_days=180)
    assert len(provider.calls) == 3  # 01-01..06-29, 06-29..12-25, 12-26..12-31 → three bounded windows


def test_empty_response_is_an_error_not_an_empty_series() -> None:
    with pytest.raises(DataContractError, match="FX_SERIES_EMPTY"):
        fx.collect_series(FakeFx([]), D1, D3)


def _closes(prices: Sequence[str], days: Sequence[date]) -> dict[str, dict[date, Decimal]]:
    return {"AAA": {day: Decimal(price) for day, price in zip(days, prices)},
            "BBB": {day: Decimal(price) for day, price in zip(days, prices)}}


def test_decomposition_is_exact_for_each_period() -> None:
    rates = {D1: Decimal("33.00"), D2: Decimal("33.33"), D3: Decimal("34.00")}
    closes = _closes(["100", "110", "105"], [D1, D2, D3])
    result = fx.decompose(closes, rates, [D1, D2, D3])
    r_usd, r_fx = result.usd["AAA"][0], result.fx[0]
    assert result.thb["AAA"][0] == (1 + r_usd) * (1 + r_fx) - 1
    assert result.cross["AAA"][0] == r_usd * r_fx
    summary = result.summary()
    instrument = summary["instruments"]["AAA"]
    # Decimal division rounds each period to 28 digits, so the compounded identity is exact to that
    # precision and no further; the residual is reported rather than hidden.
    assert abs(Decimal(instrument["identity_residual"])) < Decimal("1e-24")
    # THB = USD + FX + cross to the same precision.
    assert abs((Decimal(instrument["usd_price_return"]) + Decimal(instrument["fx_translation"])
                + Decimal(instrument["cross_term"])) - Decimal(instrument["thb_return"])) < Decimal("1e-24")


def test_missing_fx_session_is_excluded_not_filled() -> None:
    rates = {D1: Decimal("33.00"), D2: Decimal("33.33"), D3: Decimal("34.00")}
    closes = _closes(["100", "110", "105"], [D1, D2, D3])
    result = fx.decompose(closes, rates, [D1, D2, D3, date(2026, 11, 5)])
    assert result.sessions == (D1, D2, D3) and len(result.fx) == 2


def test_price_session_without_a_bar_is_refused() -> None:
    rates = {D1: Decimal("33.00"), D2: Decimal("33.33")}
    closes = {"AAA": {D1: Decimal("100")}}
    with pytest.raises(DataContractError, match="FX_PRICE_SESSION_MISSING"):
        fx.decompose(closes, rates, [D1, D2])


def test_portfolio_weights_must_cover_the_universe() -> None:
    rates = {D1: Decimal("33.00"), D2: Decimal("33.33")}
    closes = _closes(["100", "101"], [D1, D2])
    result = fx.decompose(closes, rates, [D1, D2])
    assert result.summary({"AAA": Decimal("0.5"), "BBB": Decimal("0.5")})["portfolio"]["weight_basis"] == \
        "CONSTANT_WEIGHTS_DAILY_REBALANCED"
    with pytest.raises(DataContractError, match="FX_PORTFOLIO_WEIGHTS_INCOMPLETE"):
        result.summary({"AAA": Decimal("1")})


def test_series_round_trips_through_the_private_store(tmp_path: Any) -> None:
    series = fx.collect_series(FakeFx([(D1, "33.50"), (D2, "33.73")]), D1, D3)
    rates = {D1: Decimal("33.50"), D2: Decimal("33.73")}
    report = fx.decompose(_closes(["100", "101"], [D1, D2]), rates, [D1, D2]).summary()
    path = fx.write_series(series, report, tmp_path)
    assert path.is_file()
    loaded = fx.load_series(tmp_path)
    assert loaded is not None and loaded["points"][0]["orientation"] == "THB_PER_USD"
    decomposition = fx.load_decomposition(tmp_path)
    assert decomposition is not None and decomposition["sessions"] == 2
    assert fx.load_series(tmp_path / "absent") is None


def test_decomposition_is_labelled_as_a_hypothetical_basket() -> None:
    rates = {D1: Decimal("33.00"), D2: Decimal("33.33")}
    closes = _closes(["100", "101"], [D1, D2])
    summary = fx.decompose(closes, rates, [D1, D2]).summary({"AAA": Decimal("0.5"), "BBB": Decimal("0.5")})
    assert summary["performance_basis"] == "HYPOTHETICAL_HISTORICAL_BASKET"
    assert summary["realized_performance"] is False
    for label in ("CURRENT_WEIGHTS_APPLIED_HISTORICALLY", "NOT_REALIZED_PORTFOLIO_PERFORMANCE",
                  "BOT_REFERENCE_FX_NOT_EXECUTABLE", "PRICE_RETURN_ONLY"):
        assert label in summary["labels"]
    assert summary["portfolio"]["weights_are_current_not_historical"] is True
