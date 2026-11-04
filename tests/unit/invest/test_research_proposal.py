"""Synthetic end-to-end proof of the research-proposal pipeline (research only, no orders)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import research_proposal as rp

STAMP = datetime(2026, 3, 1, tzinfo=timezone.utc)
DAYS = [datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=i) for i in range(60)]


def _inputs(risky_positive: bool = False) -> rp.ProposalInputs:
    sign = Decimal("1") if risky_positive else Decimal("-1")
    return rp.ProposalInputs(
        returns={
            "AAA": [sign * Decimal("0.001") * ((i % 5) - 2) for i in range(60)],
            "BBB": [sign * Decimal("0.002") * ((i % 7) - 3) for i in range(60)],
            "CCC": [sign * Decimal("0.0005") * ((i % 3) - 1) for i in range(60)],
        },
        timestamps=DAYS,
        current_weights={"AAA": Decimal("0.5"), "BBB": Decimal("0.3"), "CCC": Decimal("0.2")},
    )


def test_proposal_is_deterministic_and_research_only() -> None:
    first = rp.build_proposal(_inputs(), generated_at=STAMP)
    second = rp.build_proposal(_inputs(), generated_at=STAMP)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["recommendation_status"] == rp.RESEARCH_ONLY
    assert first["execution_authority"] == "NONE"
    assert first["governance_status"] == "RANKING_IS_NOT_APPROVAL"
    assert "not an order" in first["disclaimer"].lower()
    for forbidden in ("order_id", "broker_order", "account_id", "submit"):
        assert forbidden not in json.dumps(first).lower()


def test_weights_normalise_and_actions_cover_every_symbol() -> None:
    proposal = rp.build_proposal(_inputs(), generated_at=STAMP)
    total = sum(Decimal(v) for v in proposal["target_weights"].values()) + Decimal(proposal["cash_weight"])
    assert abs(total - Decimal("1")) <= Decimal("0.0001")
    symbols = {a["symbol"] for a in proposal["proposed_actions"]}
    assert symbols == {"AAA", "BBB", "CCC"}
    assert {a["action"] for a in proposal["proposed_actions"]} <= {"ADD", "HOLD", "REDUCE", "EXIT"}


def test_cash_is_chosen_when_risky_candidates_do_not_clear_the_hurdle() -> None:
    proposal = rp.build_proposal(_inputs(risky_positive=False), generated_at=STAMP)
    assert proposal["strategy_id"] == "CASH"
    assert proposal["cash_weight"] == "1.0"


def test_insufficient_history_returns_a_precise_refusal() -> None:
    short = rp.ProposalInputs(returns={"AAA": [Decimal("0.01")]}, timestamps=DAYS[:1],
                              current_weights={"AAA": Decimal("1")})
    result = rp.build_proposal(short)
    assert result["status"] == rp.INSUFFICIENT
    assert result["missing_evidence"] and result["governance_status"] == rp.RESEARCH_ONLY


def test_ragged_history_is_refused() -> None:
    inputs = rp.ProposalInputs(returns={"AAA": [Decimal("0.01")] * 3, "BBB": [Decimal("0.01")] * 2},
                               timestamps=DAYS[:3], current_weights={"AAA": Decimal("1")})
    with pytest.raises(DataContractError, match="RESEARCH_PANEL_RAgged"):
        rp.build_proposal(inputs)


def test_unknown_costs_stay_labelled_as_modeled_estimates() -> None:
    proposal = rp.build_proposal(_inputs(), generated_at=STAMP)
    assert proposal["transaction_cost_status"] == "MODELED_ESTIMATE"
    assert "broker fee schedule" in proposal["missing_evidence"]
    assert Decimal(proposal["modeled_transaction_cost"]) >= 0


def test_risk_limit_forces_cash() -> None:
    proposal = rp.build_proposal(_inputs(risky_positive=True), generated_at=STAMP,
                                 max_drawdown_limit=Decimal("-0.0001"))
    assert proposal["strategy_id"] == "CASH"
