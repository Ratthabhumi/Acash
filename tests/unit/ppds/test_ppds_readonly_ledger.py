"""Unit tests for the PPDS read-only runtime skeleton (synthetic fixtures only).

No broker imports, no credentials, no network, no real statements. Every
derived number traces to a fixture row. Order controls must never exist here.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.ppds import exposure as exposure_mod
from acash.ppds import ledger as ledger_mod
from acash.ppds import lots as lots_mod
from acash.ppds import reconcile as reconcile_mod
from acash.ppds import statement_ingest as ingest_mod
from acash.ppds import surface as surface_mod
from acash.ppds.exposure import etf_overlap_exposure, fx_exposure, position_exposure
from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.lots import CashLot, PositionLot
from acash.ppds.reconcile import reconcile_snapshot_ledger
from acash.ppds.statement_ingest import ingest_account_snapshot, parse_statement_csv
from acash.ppds.surface import render_read_only_surface

STATEMENT_CSV = """record_type,symbol,currency,quantity,amount,cost_basis_per_share,acquired_on
CASH,,USD,,100000.00,,2026-09-30
CASH,,THB,,50000.00,,2026-09-30
POSITION,ACWI,USD,500,,100.00,2026-09-30
POSITION,AGG,USD,300,,95.00,2026-09-30
"""


def _snapshot() -> ingest_mod.AccountSnapshot:
    rows = parse_statement_csv(STATEMENT_CSV)
    return ingest_account_snapshot(rows, date(2026, 9, 30))


def _ledger() -> NormalizedPortfolioLedger:
    snap = _snapshot()
    ledger = NormalizedPortfolioLedger()
    for cash_lot in snap.cash_lots:
        ledger = ledger.post_cash_lot(cash_lot)
    for position_lot in snap.position_lots:
        ledger = ledger.post_position_lot(position_lot)
    return ledger


def test_ingest_valid_statement() -> None:
    snap = _snapshot()
    assert snap.as_of == date(2026, 9, 30)
    assert snap.cash_by_currency() == {"USD": Decimal("100000.00"), "THB": Decimal("50000.00")}
    assert snap.quantity_by_symbol() == {"ACWI": Decimal("500"), "AGG": Decimal("300")}


def test_ingest_malformed_rows_fail_closed() -> None:
    with pytest.raises(DataContractError):
        parse_statement_csv("")
    with pytest.raises(DataContractError):
        parse_statement_csv("record_type,symbol\nCASH,USD\n")
    rows = parse_statement_csv(STATEMENT_CSV)
    bad: Dict[str, Any] = dict(rows[0])
    bad["amount"] = "not-a-number"
    with pytest.raises(DataContractError):
        ingest_account_snapshot([bad], date(2026, 9, 30))
    bad_float: Dict[str, Any] = dict(rows[2])
    bad_float["quantity"] = 500.0
    with pytest.raises(DataContractError):
        ingest_account_snapshot([bad_float], date(2026, 9, 30))
    unknown: Dict[str, Any] = dict(rows[0])
    unknown["record_type"] = "OPTION"
    with pytest.raises(DataContractError):
        ingest_account_snapshot([unknown], date(2026, 9, 30))


def test_lots_reject_invalid() -> None:
    with pytest.raises(DataContractError):
        CashLot.from_mapping({"currency": "US", "amount": "1", "acquired_on": "2026-09-30"})
    with pytest.raises(DataContractError):
        CashLot.from_mapping({"currency": "USD", "amount": "nan", "acquired_on": "2026-09-30"})
    with pytest.raises(DataContractError):
        PositionLot.from_mapping({"symbol": "ACWI", "quantity": "0", "cost_basis_per_share": "1",
                                   "acquired_on": "2026-09-30", "currency": "USD"})


def test_ledger_append_only_hash_chained() -> None:
    empty = NormalizedPortfolioLedger()
    assert empty.head_sha256 == "0" * 64
    assert empty.entry_count == 0
    one = empty.post_cash_lot(CashLot(currency="USD", amount=Decimal("1"), acquired_on=date(2026, 9, 30)))
    assert empty.entry_count == 0  # original untouched (immutable)
    assert one.entry_count == 1
    assert one.head_sha256 != empty.head_sha256
    assert len(one.head_sha256) == 64
    two = one.post_position_lot(PositionLot(symbol="ACWI", quantity=Decimal("1"),
                                             cost_basis_per_share=Decimal("100"),
                                             acquired_on=date(2026, 9, 30), currency="USD"))
    assert two.entry_count == 2
    assert two.head_sha256 != one.head_sha256


def test_reconcile_match() -> None:
    result = reconcile_snapshot_ledger(_snapshot(), _ledger())
    assert result.matched is True
    assert result.breaks == []


def test_reconcile_mismatch_reports_breaks() -> None:
    snap = _snapshot()
    ledger = _ledger()
    tampered = NormalizedPortfolioLedger(
        cash_lots=ledger.cash_lots,
        position_lots=ledger.position_lots + (
            PositionLot(symbol="ACWI", quantity=Decimal("1"),
                        cost_basis_per_share=Decimal("100"),
                        acquired_on=date(2026, 9, 30), currency="USD"),
        ),
        head_sha256=ledger.head_sha256,
        entry_count=ledger.entry_count + 1,
    )
    result = reconcile_snapshot_ledger(snap, tampered)
    assert result.matched is False
    assert any(item.scope == "POSITION" and item.key == "ACWI" for item in result.breaks)


def test_position_exposure_math() -> None:
    lines = position_exposure(
        _ledger(), {"ACWI": Decimal("100"), "AGG": Decimal("95")}
    )
    by_key = {line.key: line for line in lines}
    # ACWI 500×100=50000, AGG 300×95=28500, total 78500.
    assert by_key["ACWI"].market_value == "50000"
    assert by_key["AGG"].market_value == "28500"
    total_weight = sum(Decimal(line.weight) for line in lines)
    assert total_weight == Decimal("1")
    with pytest.raises(DataContractError):
        position_exposure(_ledger(), {"ACWI": Decimal("100")})


def test_etf_overlap_decomposition() -> None:
    lines = etf_overlap_exposure(
        _ledger(),
        {"ACWI": Decimal("100"), "AGG": Decimal("95")},
        {"ACWI": {"US": Decimal("0.6"), "EXUS": Decimal("0.4")},
         "AGG": {"BONDS": Decimal("1")}},
    )
    by_key = {line.key: line for line in lines}
    # ACWI leg 50000 -> US 30000, EXUS 20000; AGG leg 28500 -> BONDS 28500.
    assert by_key["US"].market_value == "30000.0"
    assert by_key["EXUS"].market_value == "20000.0"
    assert by_key["BONDS"].market_value == "28500"
    with pytest.raises(DataContractError):
        etf_overlap_exposure(
            _ledger(), {"ACWI": Decimal("100"), "AGG": Decimal("95")},
            {"ACWI": {"US": Decimal("0.5"), "EXUS": Decimal("0.4")}},
        )


def test_fx_exposure_math() -> None:
    lines = fx_exposure(_ledger(), {"USD": Decimal("1"), "THB": Decimal("0.03")})
    by_key = {line.key: line for line in lines}
    # USD 100000×1=100000; THB 50000×0.03=1500.00; total 101500.
    assert by_key["USD"].market_value == "100000.00"
    assert by_key["THB"].market_value == "1500.0000"
    with pytest.raises(DataContractError):
        fx_exposure(_ledger(), {"USD": Decimal("1")})


def test_surface_read_only_no_order_controls() -> None:
    ledger = _ledger()
    result = reconcile_snapshot_ledger(_snapshot(), ledger)
    exposures = position_exposure(ledger, {"ACWI": Decimal("100"), "AGG": Decimal("95")})
    surface = render_read_only_surface(ledger, result, exposures)
    assert surface["order_controls"] is None
    assert surface["reconciliation_matched"] is True
    assert surface["entry_count"] == 4
    assert surface["head_sha256"] == ledger.head_sha256
    flat = str(surface).lower()
    assert "endpoint" not in flat
    assert "credential" not in flat


def test_no_broker_or_secret_imports_in_ppds() -> None:
    """Self-policing: the PPDS skeleton must not import broker/secret machinery."""
    import re

    package_dir = Path(lots_mod.__file__).resolve().parent
    import_pattern = re.compile(r"^\s*(import|from)\s+([\w\.]+)", re.MULTILINE)
    for path in sorted(package_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in import_pattern.finditer(text):
            module = match.group(2).lower()
            assert "alpaca" not in module, f"{path.name} imports {module!r}"
            assert "broker" not in module, f"{path.name} imports {module!r}"
        lowered = text.lower()
        for token in ("api_secret", "api_key", "password", "secret_ref"):
            assert token not in lowered, f"{path.name} contains {token!r}"


def test_package_modules_import_cleanly() -> None:
    for module in (lots_mod, ledger_mod, ingest_mod, reconcile_mod, exposure_mod, surface_mod):
        assert module.__name__.startswith("acash.ppds.")
