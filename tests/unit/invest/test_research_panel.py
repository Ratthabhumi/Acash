"""Panel weights come from qualified position rows; a missing weight is an exclusion, not a zero."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import research_panel as rp

ROWS = [
    {"security_id": "AAA", "price_currency": "USD", "value_local": "60.00"},
    {"security_id": "HOOD", "price_currency": "USD", "value_local": "40.00"},
    {"security_id": "THB1", "price_currency": "THB", "value_local": "9999.00"},
]
DAYS = [date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7)]


def _series(step: str = "1") -> Dict[str, Dict[date, Decimal]]:
    return {"AAA": {d: Decimal("100") + i for i, d in enumerate(DAYS)},
            "HOOD": {d: Decimal("50") + Decimal(step) * i for i, d in enumerate(DAYS)}}


def test_weights_are_global_and_ignore_other_currencies() -> None:
    weights = rp.qualified_weights(ROWS, ["AAA", "HOOD", "THB1"])
    assert weights == {"AAA": Decimal("0.6"), "HOOD": Decimal("0.4")}
    assert sum(weights.values()) == Decimal(1)


def test_a_symbol_without_a_value_is_excluded_never_zeroed() -> None:
    panel = rp.build_panel(_series(), {"AAA": Decimal("1")}, ["AAA", "HOOD"], min_sessions=1)
    assert panel["eligible"] == ["AAA"]
    assert panel["excluded"]["HOOD"]["reason"] == "NO_QUALIFIED_POSITION_VALUE"
    assert "HOOD" not in panel["inputs"].current_weights


def test_short_history_is_excluded_for_a_different_reason() -> None:
    panel = rp.build_panel(_series(), {"AAA": Decimal("0.5"), "HOOD": Decimal("0.5")},
                           ["AAA", "HOOD"], min_sessions=10)
    assert panel["excluded"]["AAA"]["reason"] == "SESSION_COVERAGE_BELOW_MINIMUM"
    assert panel["excluded"]["HOOD"]["reason"] == "SESSION_COVERAGE_BELOW_MINIMUM"


def test_panel_weights_are_renormalised_and_the_fact_is_reported() -> None:
    panel = rp.build_panel(_series(), {"AAA": Decimal("0.6"), "HOOD": Decimal("0.4")},
                           ["AAA", "HOOD"], min_sessions=1)
    assert panel["weights_renormalised_to_panel"] is False
    partial = rp.build_panel(_series(), {"AAA": Decimal("0.6")}, ["AAA", "HOOD"], min_sessions=1)
    assert partial["weights"] == {"AAA": "1"}


def test_unqualified_value_is_refused_not_treated_as_zero() -> None:
    rows: List[Dict[str, Any]] = [{"security_id": "AAA", "price_currency": "USD", "value_local": None}]
    with pytest.raises(DataContractError, match="PANEL_WEIGHT_UNQUALIFIED"):
        rp.qualified_weights(rows, ["AAA"])


def test_labels_separate_hypothetical_from_realized() -> None:
    panel = rp.build_panel(_series(), {"AAA": Decimal("0.5"), "HOOD": Decimal("0.5")},
                           ["AAA", "HOOD"], min_sessions=1)
    labels = rp.real_vs_hypothetical(panel)
    assert labels["realized_performance"] is False and labels["transaction_reconstructed"] is False
    assert "NOT_REALIZED_PORTFOLIO_PERFORMANCE" in labels["labels"]
    assert labels["weight_basis"] == rp.WEIGHT_BASIS
