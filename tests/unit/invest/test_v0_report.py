"""Unit tests for ACASH Invest V0 read-only report (synthetic fixtures only).

No broker, no credentials, no network, no real statements, no statistics.
Every derived number traces to an explicit fixture row; anything unproven
is BLOCKED or NOT_ESTABLISHED, never zeroed or interpolated.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import v0_report as v0_mod
from acash.invest.v0_report import (
    COST_BASIS_MODELLED,
    COST_BASIS_UNKNOWN,
    EVIDENCE_SYNTHETIC_DEMONSTRATION,
    V0CostAssumption,
    build_invest_v0_report,
    render_v0_json,
    render_v0_markdown,
)
from acash.ppds.exposure import FXRate, PriceQuote
from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.lots import CashLot, PositionLot
from acash.ppds.statement_ingest import AccountSnapshot

AS_OF = date(2026, 10, 2)
FICTIONAL_SYMBOLS = ("ETF_A", "ETF_B")


def _prices() -> Dict[str, PriceQuote]:
    return {
        "ETF_A": PriceQuote(
            symbol="ETF_A", price=Decimal("100"), as_of=AS_OF,
            currency="USD", source_id="SYNTHETIC_FIXTURE",
        ),
        "ETF_B": PriceQuote(
            symbol="ETF_B", price=Decimal("50"), as_of=AS_OF,
            currency="USD", source_id="SYNTHETIC_FIXTURE",
        ),
    }


def _ledger() -> NormalizedPortfolioLedger:
    ledger = NormalizedPortfolioLedger(account_id="SYNTHETIC_V0", as_of=AS_OF)
    ledger = ledger.post_cash_lot(
        CashLot(currency="USD", amount=Decimal("150"), acquired_on=AS_OF)
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="ETF_A", quantity=Decimal("4"),
                    cost_basis_per_share=Decimal("100"),
                    acquired_on=AS_OF, currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="ETF_B", quantity=Decimal("9"),
                    cost_basis_per_share=Decimal("50"),
                    acquired_on=AS_OF, currency="USD")
    )
    return ledger


def _statement() -> AccountSnapshot:
    return AccountSnapshot(
        as_of=AS_OF,
        cash_lots=(
            CashLot(currency="USD", amount=Decimal("150"), acquired_on=AS_OF),
        ),
        position_lots=(
            PositionLot(symbol="ETF_A", quantity=Decimal("4"),
                        cost_basis_per_share=Decimal("100"),
                        acquired_on=AS_OF, currency="USD"),
            PositionLot(symbol="ETF_B", quantity=Decimal("9"),
                        cost_basis_per_share=Decimal("50"),
                        acquired_on=AS_OF, currency="USD"),
        ),
        account_id="SYNTHETIC_V0",
    )


def _costs() -> List[V0CostAssumption]:
    return [
        V0CostAssumption(
            name="commission_floor",
            basis=COST_BASIS_MODELLED,
            detail="IBKR Tiered-style per-order minimum assumption; NOT account-verified.",
            amount_base=Decimal("0.35"),
        ),
        V0CostAssumption(
            name="withholding_tax",
            basis=COST_BASIS_UNKNOWN,
            detail="Owner-specific tax treatment unestablished; never assumed zero.",
            amount_base=None,
        ),
    ]


def _report() -> Dict[str, Any]:
    return build_invest_v0_report(
        ledger=_ledger(),
        prices=_prices(),
        fx_rates={},
        base_currency="USD",
        as_of=AS_OF,
        statement=_statement(),
        statement_source_id="SYNTHETIC_STATEMENT",
        ledger_source_id="SYNTHETIC_LEDGER",
        costs=_costs(),
    )


def test_nav_conservation_exact() -> None:
    report = _report()
    # 4*100 + 9*50 + 150 = 1000 exactly.
    assert report["nav_base"] == "1000"
    assert report["total_cash_base"] == "150"
    assert report["total_positions_net_base"] == "850"


def test_cash_inclusive_allocation_weights() -> None:
    report = _report()
    weights = {
        entry["key"]: Decimal(entry["nav_weight"])
        for entry in report["allocation_nav_inclusive"]
    }
    assert weights == {
        "ETF_A": Decimal("0.4"),
        "ETF_B": Decimal("0.45"),
        "CASH:USD": Decimal("0.15"),
    }
    assert sum(weights.values(), Decimal("0")) == Decimal("1")


def test_invested_only_exposure_distinguished_from_nav() -> None:
    report = _report()
    invested = report["invested_only_exposure"]
    assert invested["status"] == "ESTABLISHED"
    lines = {line["key"]: Decimal(line["weight"]) for line in invested["lines"]}
    # 400/850 and 450/850 over INVESTED positions only (cash excluded).
    assert lines["ETF_A"] == Decimal("400") / Decimal("850")
    assert lines["ETF_B"] == Decimal("450") / Decimal("850")
    assert "cash excluded by construction" in invested["basis"].lower()


def test_concentration_reported() -> None:
    report = _report()
    assert report["largest_concentration"] == {
        "key": "ETF_B", "nav_weight": "0.45",
    }


def test_reconciliation_self_consistent_not_independent() -> None:
    report = _report()
    reconciliation = report["reconciliation"]
    # A computed match says exactly that: computed, matched, not independent.
    assert reconciliation["status"] == "COMPUTED_MATCH"
    assert reconciliation["matched"] is True
    # Self-consistency must never be presented as independent attestation.
    assert reconciliation["is_independent"] is False
    assert reconciliation["breaks"] == []


def test_reconciliation_missing_when_no_statement() -> None:
    report = build_invest_v0_report(
        ledger=_ledger(), prices=_prices(), fx_rates={},
        base_currency="USD", as_of=AS_OF, costs=_costs(),
    )
    assert report["reconciliation"]["status"] == "NOT_ESTABLISHED"
    assert report["reconciliation"]["is_independent"] is False


def test_reconciliation_mismatch_reported() -> None:
    snap = _statement()
    tampered = AccountSnapshot(
        as_of=snap.as_of,
        cash_lots=(
            CashLot(currency="USD", amount=Decimal("999"), acquired_on=AS_OF),
        ),
        position_lots=snap.position_lots,
        account_id=snap.account_id,
    )
    report = build_invest_v0_report(
        ledger=_ledger(), prices=_prices(), fx_rates={},
        base_currency="USD", as_of=AS_OF, statement=tampered, costs=_costs(),
    )
    assert report["reconciliation"]["status"] == "COMPUTED_MISMATCH"
    assert report["reconciliation"]["matched"] is False
    assert len(report["reconciliation"]["breaks"]) >= 1


def test_missing_price_fails_closed() -> None:
    prices = _prices()
    del prices["ETF_B"]
    with pytest.raises(DataContractError):
        build_invest_v0_report(
            ledger=_ledger(), prices=prices, fx_rates={},
            base_currency="USD", as_of=AS_OF, costs=_costs(),
        )


def test_stale_price_as_of_fails_closed() -> None:
    prices = _prices()
    prices["ETF_A"] = PriceQuote(
        symbol="ETF_A", price=Decimal("100"), as_of=date(2026, 10, 1),
        currency="USD", source_id="SYNTHETIC_FIXTURE",
    )
    with pytest.raises(DataContractError):
        build_invest_v0_report(
            ledger=_ledger(), prices=prices, fx_rates={},
            base_currency="USD", as_of=AS_OF, costs=_costs(),
        )


def test_missing_fx_fails_closed() -> None:
    ledger = NormalizedPortfolioLedger(account_id="SYNTHETIC_FX", as_of=AS_OF)
    ledger = ledger.post_cash_lot(
        CashLot(currency="USD", amount=Decimal("150"), acquired_on=AS_OF)
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="ETF_A", quantity=Decimal("4"),
                    cost_basis_per_share=Decimal("100"),
                    acquired_on=AS_OF, currency="EUR")
    )
    prices = {
        "ETF_A": PriceQuote(
            symbol="ETF_A", price=Decimal("90"), as_of=AS_OF,
            currency="EUR", source_id="SYNTHETIC_FIXTURE",
        ),
    }
    with pytest.raises(DataContractError):
        build_invest_v0_report(
            ledger=ledger, prices=prices, fx_rates={},
            base_currency="USD", as_of=AS_OF, costs=_costs(),
        )


def test_contradictory_currency_basis_fails_closed() -> None:
    prices = _prices()
    prices["ETF_A"] = PriceQuote(
        symbol="ETF_A", price=Decimal("100"), as_of=AS_OF,
        currency="EUR", source_id="SYNTHETIC_FIXTURE",
    )
    with pytest.raises(DataContractError):
        build_invest_v0_report(
            ledger=_ledger(), prices=prices, fx_rates={},
            base_currency="USD", as_of=AS_OF, costs=_costs(),
        )


def test_unknown_costs_never_total_zero() -> None:
    report = _report()
    assert report["costs"]["total_base"] is None
    assert report["costs"]["total_basis"] == "NOT_ESTABLISHED"


def test_empty_costs_never_total_zero() -> None:
    report = build_invest_v0_report(
        ledger=_ledger(), prices=_prices(), fx_rates={},
        base_currency="USD", as_of=AS_OF, costs=[],
    )
    assert report["costs"]["total_base"] is None
    assert report["costs"]["total_basis"] == "NOT_ESTABLISHED"


def test_invalid_cost_basis_rejected() -> None:
    with pytest.raises(DataContractError):
        build_invest_v0_report(
            ledger=_ledger(), prices=_prices(), fx_rates={},
            base_currency="USD", as_of=AS_OF,
            costs=[V0CostAssumption(name="x", basis="GUARANTEED",
                                    detail="y", amount_base=Decimal("1"))],
        )


def test_nonpositive_nav_fails_closed() -> None:
    ledger = NormalizedPortfolioLedger(account_id="SYNTHETIC_SHORT", as_of=AS_OF)
    ledger = ledger.post_cash_lot(
        CashLot(currency="USD", amount=Decimal("500"), acquired_on=AS_OF)
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="ETF_A", quantity=Decimal("-100"),
                    cost_basis_per_share=Decimal("100"),
                    acquired_on=AS_OF, currency="USD")
    )
    with pytest.raises(DataContractError):
        build_invest_v0_report(
            ledger=ledger, prices=_prices(), fx_rates={},
            base_currency="USD", as_of=AS_OF, costs=_costs(),
        )


def test_invalid_monetary_inputs_fail_closed() -> None:
    with pytest.raises(DataContractError):
        build_invest_v0_report(
            ledger=_ledger(), prices=_prices(), fx_rates={},
            base_currency="US", as_of=AS_OF, costs=_costs(),
        )
    with pytest.raises(DataContractError):
        build_invest_v0_report(
            ledger=_ledger(), prices=_prices(), fx_rates={},
            base_currency="USD", as_of=AS_OF,
            costs=[V0CostAssumption(name="  ", basis=COST_BASIS_MODELLED,
                                    detail="x", amount_base=Decimal("1"))],
        )


def _all_keys(node: Any) -> List[str]:
    keys: List[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            keys.append(str(key))
            keys.extend(_all_keys(value))
    elif isinstance(node, list):
        for value in node:
            keys.extend(_all_keys(value))
    return keys


def test_no_invented_statistics_anywhere() -> None:
    report = _report()
    # No statistic is ever emitted as a report FIELD (disclaimer prose that
    # names what is missing does not count as a fabricated metric).
    forbidden = {
        "sharpe", "sortino", "expected_return", "drawdown", "max_drawdown",
        "alpha", "ranking", "rank_score", "win_rate", "hit_rate",
        "confidence_interval",
    }
    present = {key.lower() for key in _all_keys(report)}
    assert not (present & forbidden)
    # "var"/"cvar" must not appear as fields either (prose may mention them).
    assert "var" not in present and "cvar" not in present
    flat_md = render_v0_markdown(report).lower()
    assert "modelled" in flat_md


def test_no_qualification_escalation() -> None:
    report = _report()
    assert report["evidence_classification"] == EVIDENCE_SYNTHETIC_DEMONSTRATION
    assert report["valuation_basis"].startswith("Point-in-time synthetic")
    assert "NOT_ESTABLISHED" in render_v0_markdown(report)


def test_execution_prohibited() -> None:
    report = _report()
    execution = report["execution"]
    assert execution["order_submission_authorized"] is False
    assert execution["capital_authority_usd"] == "0.00"
    assert "NO_REAL_ORDERS" in execution["recommendation"]


def test_no_broker_network_order_imports_in_invest() -> None:
    """Self-policing: the invest layer must not import trading machinery."""
    import re

    package_dir = Path(v0_mod.__file__).resolve().parent
    import_pattern = re.compile(r"^\s*(import|from)\s+([\w\.]+)", re.MULTILINE)
    for path in sorted(package_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in import_pattern.finditer(text):
            module = match.group(2).lower()
            for banned in ("alpaca", "broker", "order", "socket", "http",
                           "urllib", "requests", "websocket"):
                assert banned not in module.split("."), f"{path.name} imports {module!r}"
        lowered = text.lower()
        for token in ("api_secret", "api_key", "password"):
            assert token not in lowered, f"{path.name} contains {token!r}"


def test_deterministic_output() -> None:
    first = render_v0_json(_report())
    second = render_v0_json(_report())
    assert first == second
    assert render_v0_markdown(_report()) == render_v0_markdown(_report())


def test_committed_example_matches_fresh_generation() -> None:
    """The committed JSON/Markdown examples must equal fresh generation byte-for-byte."""
    repo_root = Path(__file__).resolve().parents[3]
    committed_json = (
        repo_root / "docs" / "invest" / "v0" / "invest_v0_example.json"
    ).read_text(encoding="utf-8")
    committed_md = (
        repo_root / "docs" / "invest" / "v0" / "invest_v0_example.md"
    ).read_text(encoding="utf-8")
    assert committed_json == render_v0_json(_report()) + "\n"
    assert committed_md == render_v0_markdown(_report())
    assert '"nav_base": "1000"' in committed_json


def test_account_verified_cost_rejected_without_provenance() -> None:
    with pytest.raises(DataContractError):
        build_invest_v0_report(
            ledger=_ledger(), prices=_prices(), fx_rates={},
            base_currency="USD", as_of=AS_OF,
            costs=[V0CostAssumption(name="commission", basis="ACCOUNT_VERIFIED",
                                    detail="no attestation attached",
                                    amount_base=Decimal("0.35"))],
        )


def test_negative_cost_rejected() -> None:
    with pytest.raises(DataContractError):
        build_invest_v0_report(
            ledger=_ledger(), prices=_prices(), fx_rates={},
            base_currency="USD", as_of=AS_OF,
            costs=[V0CostAssumption(name="rebate", basis=COST_BASIS_MODELLED,
                                    detail="negative fees need distinct semantics",
                                    amount_base=Decimal("-1.00"))],
        )


def test_short_position_rejected_long_only() -> None:
    ledger = NormalizedPortfolioLedger(account_id="SYNTHETIC_SHORT", as_of=AS_OF)
    ledger = ledger.post_cash_lot(
        CashLot(currency="USD", amount=Decimal("1500"), acquired_on=AS_OF)
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="ETF_A", quantity=Decimal("-5"),
                    cost_basis_per_share=Decimal("100"),
                    acquired_on=AS_OF, currency="USD")
    )
    with pytest.raises(DataContractError):
        build_invest_v0_report(
            ledger=ledger, prices=_prices(), fx_rates={},
            base_currency="USD", as_of=AS_OF, costs=_costs(),
        )


def test_negative_cash_rejected() -> None:
    ledger = NormalizedPortfolioLedger(account_id="SYNTHETIC_OD", as_of=AS_OF)
    ledger = ledger.post_cash_lot(
        CashLot(currency="USD", amount=Decimal("-10"), acquired_on=AS_OF)
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="ETF_A", quantity=Decimal("4"),
                    cost_basis_per_share=Decimal("100"),
                    acquired_on=AS_OF, currency="USD")
    )
    with pytest.raises(DataContractError):
        build_invest_v0_report(
            ledger=ledger, prices=_prices(), fx_rates={},
            base_currency="USD", as_of=AS_OF, costs=_costs(),
        )


def test_multi_currency_blocks_invested_exposure_not_valuation() -> None:
    ledger = NormalizedPortfolioLedger(account_id="SYNTHETIC_FX", as_of=AS_OF)
    ledger = ledger.post_cash_lot(
        CashLot(currency="USD", amount=Decimal("150"), acquired_on=AS_OF)
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="ETF_A", quantity=Decimal("4"),
                    cost_basis_per_share=Decimal("100"),
                    acquired_on=AS_OF, currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="ETF_B", quantity=Decimal("90"),
                    cost_basis_per_share=Decimal("5"),
                    acquired_on=AS_OF, currency="EUR")
    )
    prices = _prices()
    prices["ETF_B"] = PriceQuote(
        symbol="ETF_B", price=Decimal("45"), as_of=AS_OF,
        currency="EUR", source_id="SYNTHETIC_FIXTURE",
    )
    fx_rates = {
        ("EUR", "USD"): FXRate(
            from_currency="EUR", to_currency="USD", rate=Decimal("1.1"),
            as_of=AS_OF, source_id="SYNTHETIC_FIXTURE",
        ),
    }
    report = build_invest_v0_report(
        ledger=ledger, prices=prices, fx_rates=fx_rates,
        base_currency="USD", as_of=AS_OF, costs=[],
    )
    # Valuation works across currencies with explicit FX ...
    assert report["nav_base"] == str(
        Decimal("150") + Decimal("400") + Decimal("90") * Decimal("45") * Decimal("1.1")
    )
    # ... but invested-only exposure refuses multi-currency approximation ...
    assert report["invested_only_exposure"]["status"] == "BLOCKED"
    # ... and so does the embedded PPDS surface (needs exposure lines).
    assert report["ppds_surface"]["status"] == "NOT_ESTABLISHED"
    # Provenance follows the money across the FX boundary.
    eur_entries = [
        entry for entry in report["allocation_nav_inclusive"]
        if entry["key"] == "ETF_B"
    ]
    assert eur_entries[0]["fx_rate_to_base"] == "1.1"
    assert eur_entries[0]["fx_source_id"] == "SYNTHETIC_FIXTURE"


def test_ppds_surface_reused_when_available() -> None:
    report = _report()
    surface_section = report["ppds_surface"]
    assert surface_section["status"] == "ESTABLISHED"
    surface = surface_section["surface"]
    assert surface["order_controls"] is None
    assert surface["reconciliation_matched"] is True
    assert surface["head_sha256"] == report["ledger_head_sha256"]


def test_allocation_carries_valuation_provenance() -> None:
    report = _report()
    positions = {
        entry["key"]: entry
        for entry in report["allocation_nav_inclusive"]
        if entry["kind"] == "POSITION"
    }
    entry = positions["ETF_A"]
    assert entry["price"] == "100"
    assert entry["price_as_of"] == "2026-10-02"
    assert entry["price_source_id"] == "SYNTHETIC_FIXTURE"
    assert entry["pricing_currency"] == "USD"


def test_ledger_tamper_changes_head() -> None:
    assert _ledger().head_sha256 != NormalizedPortfolioLedger(
        account_id="SYNTHETIC_V0", as_of=AS_OF
    ).post_cash_lot(
        CashLot(currency="USD", amount=Decimal("151"), acquired_on=AS_OF)
    ).head_sha256
