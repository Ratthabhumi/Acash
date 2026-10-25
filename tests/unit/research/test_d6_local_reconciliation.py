"""Issuer and cited-evidence reconciliation of LOCAL_EXPLORATORY distributions (offline)."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.contracts.corporate_action_ledger import parse_distribution_rows
from acash.research.d6.accounting import D6_REGISTERED_PORTFOLIOS, D6CostModel, run_d6_portfolio
from acash.research.d6.local_alpaca import corporate_action_rows
from acash.research.d6.local_reconciliation import (
    apply_issuer_records,
    apply_reclassification,
    parse_ssga_distribution_xlsx,
)

WINDOW = (date(2016, 1, 1), date(2025, 12, 31))
EVIDENCE = Path(__file__).resolve().parents[3] / "docs/research/evidence/bnd_capital_gain_reclassification_v34.csv"
HEADER = ["FUND NAME", "TICKER", "CUSIP", "EX-DATE", "RECORD DATE", "PAYABLE DATE", "DIVIDEND ($)",
          "SHORT TERM CAPITAL GAIN ($)", "LONG TERM CAPITAL GAIN ($)", "FREQUENCY"]


def _xlsx(rows: list[list[str]]) -> bytes:
    strings: list[str] = []
    cells = []
    for r, values in enumerate([HEADER, *rows], start=1):
        parts = []
        for value in values:
            strings.append(value)
            parts.append(f'<c t="s"><v>{len(strings) - 1}</v></c>')
        cells.append(f'<row r="{r}">{"".join(parts)}</row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as book:
        book.writestr("xl/sharedStrings.xml", f"<sst {ns}>" + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>")
        book.writestr("xl/worksheets/sheet1.xml", f"<worksheet {ns}><sheetData>{''.join(cells)}</sheetData></worksheet>")
    return buffer.getvalue()


def _issuer_row(ex: str, pay: str, amount: str, cusip: str = "78468R663", st: str = "", lt: str = "") -> list[str]:
    return ["BIL fund", "BIL", cusip, ex, ex, pay, f" {amount} ", st, lt, "Monthly"]


def _row(sym: str, ex: str, pay: str, amount: str, source: str, event_id: str) -> dict[str, str]:
    return {"symbol": sym, "ex_date": ex, "payable_date": pay, "gross_amount": amount, "distribution_type": "DIVIDEND_CASH",
            "payable_date_source": source, "event_id": event_id, "process_date": ex}


def _issuer(*rows: list[str]) -> Any:
    return parse_ssga_distribution_xlsx(_xlsx(list(rows)), ["BIL"])


def test_issuer_file_replaces_imputed_payable_and_confirms_provider_payable() -> None:
    issuer = _issuer(
        _issuer_row("03/01/2017", "03/07/2017", "0.017"),
        _issuer_row("04/03/2017", "04/07/2017", "0.02"),
        _issuer_row("05/01/2017", "05/05/2017", "0.000000"),
        _issuer_row("12/29/2009", "12/31/2009", "0", lt="0.001"),
    )
    rows = [
        _row("BIL", "2017-03-01", "2017-03-08", "0.017", "IMPUTED_EX_PLUS_7D_MAX_OBSERVED_LAG", "a"),
        _row("BIL", "2017-04-03", "2017-04-07", "0.02", "PROVIDER", "b"),
        _row("VOO", "2017-03-24", "2017-03-30", "1.0", "IMPUTED_EX_PLUS_6D_MAX_OBSERVED_LAG", "c"),
    ]
    result = apply_issuer_records(rows, issuer, symbol="BIL", cusip="78468R663", window=WINDOW, source_ref="ssga")
    assert (result.matched, result.payable_replaced, result.payable_confirmed) == (2, 1, 1)
    assert result.rows[0]["payable_date"] == "2017-03-07" and result.rows[0]["payable_date_source"] == "ISSUER_FILE"
    assert result.rows[0]["evidence_class"] == "ISSUER_FILE_MATCHED" and result.rows[0]["event_id"] == "a"
    assert result.rows[2]["evidence_class"] == "PROVIDER_ONLY"
    assert result.rows[2]["payable_date_source"].startswith("IMPUTED")
    assert result.issuer_events_missing_from_provider == ()
    assert result.issuer_zero_amount_rows_without_provider_event == 1


@pytest.mark.parametrize(
    "issuer_rows, row, code",
    [
        ([_issuer_row("03/01/2017", "03/07/2017", "0.018")],
         _row("BIL", "2017-03-01", "", "0.017", "", "a"), "ISSUER_AMOUNT_MISMATCH"),
        ([_issuer_row("03/01/2017", "03/07/2017", "0.017")],
         _row("BIL", "2017-03-01", "2017-03-06", "0.017", "PROVIDER", "a"), "ISSUER_PROVIDER_PAYABLE_CONFLICT"),
        ([_issuer_row("03/01/2017", "03/07/2017", "0.017", cusip="X")],
         _row("BIL", "2017-03-01", "", "0.017", "", "a"), "ISSUER_CUSIP_MISMATCH"),
        ([], _row("BIL", "2017-03-01", "", "0.017", "", "a"), "ISSUER_EVENT_NOT_FOUND"),
        ([_issuer_row("03/01/2017", "03/07/2017", "0.017", lt="0.01")],
         _row("BIL", "2017-03-01", "", "0.017", "", "a"), "ISSUER_CAPITAL_GAIN_NEEDS_RECLASSIFICATION"),
    ],
)
def test_issuer_reconciliation_fails_closed(issuer_rows: list[list[str]], row: dict[str, str], code: str) -> None:
    with pytest.raises(DataContractError, match=code):
        apply_issuer_records([row], _issuer(*issuer_rows), symbol="BIL", cusip="78468R663", window=WINDOW,
                             source_ref="ssga")


def test_nonzero_issuer_event_missing_from_provider_is_reported() -> None:
    issuer = _issuer(_issuer_row("03/01/2017", "03/07/2017", "0.017"), _issuer_row("04/03/2017", "04/07/2017", "0.02"))
    rows = [_row("BIL", "2017-03-01", "2017-03-07", "0.017", "PROVIDER", "a")]
    result = apply_issuer_records(rows, issuer, symbol="BIL", cusip="78468R663", window=WINDOW, source_ref="s")
    assert result.issuer_events_missing_from_provider == ("2017-04-03",)


def _bnd_rows() -> list[dict[str, str]]:
    return [
        _row("BND", "2020-12-23", "2020-12-29", "0.1471819", "PROVIDER", "3b63faa9"),
        _row("BND", "2020-12-23", "2020-12-29", "0.1436", "PROVIDER", "eb13dcb4"),
    ]


def _evidence() -> list[dict[str, str]]:
    with EVIDENCE.open(encoding="utf-8", newline="") as handle:
        return [r for r in csv.DictReader(handle) if r["ex_date"] == "2020-12-23"]


def test_bnd_capital_gain_split_preserves_cash_once_and_identity() -> None:
    rows = apply_reclassification(_bnd_rows(), _evidence())
    assert [(r["distribution_type"], r["gross_amount"], r["event_id"], r["evidence_class"]) for r in rows] == [
        ("DIVIDEND_CASH", "0.1471819", "3b63faa9", "PROVIDER_ONLY"),
        ("CAPITAL_GAIN_LONG_TERM", "0.1064", "eb13dcb4#long_term", "OCC_MEMO_CORROBORATED"),
        ("CAPITAL_GAIN_SHORT_TERM", "0.0372", "eb13dcb4#short_term", "OCC_MEMO_CORROBORATED"),
    ]
    assert sum(Decimal(r["gross_amount"]) for r in rows) == Decimal("0.1471819") + Decimal("0.1436")

    sessions = [date(2020, 12, 21), date(2020, 12, 22), date(2020, 12, 23), date(2020, 12, 28), date(2020, 12, 29)]
    prices = {"VOO": {s: Decimal("100") for s in sessions}, "BND": {s: Decimal("88") for s in sessions}}
    portfolio = next(p for p in D6_REGISTERED_PORTFOLIOS if p.name == "VOO_BND_60_40")
    cost = D6CostModel(label="ZERO_COST_UPPER_BOUND")

    def gross(dist_rows: list[dict[str, str]]) -> Decimal:
        records = parse_distribution_rows(dist_rows, symbol="BND", source_ref="d.csv")
        result = run_d6_portfolio(portfolio, sessions=sessions, opens=prices, closes=prices,
                                  dividends={"BND": records}, cost=cost)
        assert len(result.entitlements) == len(dist_rows)
        return result.dividends_gross

    assert gross(rows) == gross(_bnd_rows())


@pytest.mark.parametrize(
    "mutate, code",
    [
        (lambda e: [dict(e[0], amount="0.1065"), e[1]], "RECLASS_COMPONENTS_DO_NOT_SUM"),
        (lambda e: [dict(x, provider_gross_amount="0.2") for x in e], "RECLASS_PROVIDER_EVENT_MATCHES_0"),
        (lambda e: [dict(e[0], evidence_class="BLOG"), e[1]], "RECLASS_UNKNOWN_EVIDENCE_CLASS"),
        (lambda e: [dict(e[0], evidence_ref=" "), e[1]], "RECLASS_EVIDENCE_REF_MISSING"),
        (lambda e: [dict(x, payable_date="2020-12-30") for x in e], "RECLASS_PAYABLE_CONFLICT"),
        (lambda e: [e[0], dict(e[1], component_type="CAPITAL_GAIN_LONG_TERM", amount="0.0372")],
         "RECLASS_DUPLICATE_COMPONENT"),
    ],
)
def test_reclassification_fails_closed(mutate: Any, code: str) -> None:
    with pytest.raises(DataContractError, match=code):
        apply_reclassification(_bnd_rows(), mutate(_evidence()))


def test_reclassifying_twice_is_rejected() -> None:
    once = apply_reclassification(_bnd_rows(), _evidence())
    with pytest.raises(DataContractError, match="RECLASS_PROVIDER_EVENT_MATCHES_0"):
        apply_reclassification(once, _evidence())


def test_committed_evidence_components_sum_to_provider_amounts() -> None:
    with EVIDENCE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for r in rows:
        groups.setdefault((r["ex_date"], r["provider_gross_amount"]), []).append(r)
    assert sorted(groups) == [("2020-12-23", "0.1436"), ("2021-04-01", "0.0534"),
                              ("2021-12-23", "0.13"), ("2022-04-01", "0.0593")]
    for (_, gross), members in groups.items():
        assert sum(Decimal(m["amount"]) for m in members) == Decimal(gross)
        assert all(m["evidence_ref"].startswith("https://") for m in members)
    assert {m["evidence_class"] for m in groups[("2020-12-23", "0.1436")]} == {"OCC_MEMO_CORROBORATED"}


def test_provider_cross_type_duplicate_is_rejected() -> None:
    cash = {"symbol": "BND", "ex_date": "2020-12-23", "payable_date": "2020-12-29", "process_date": "2020-12-29",
            "rate": 0.1436, "id": "c1"}
    gain = {"symbol": "BND", "ex_date": "2020-12-23", "payable_date": "2020-12-29", "process_date": "2020-12-29",
            "id": "g1", "cusip": "921937835", "long_term_rate": 0.1064, "short_term_rate": 0.0372}
    page = {"corporate_actions": {"cash_dividends": [cash], "capital_gains_distributions": [gain]}}
    with pytest.raises(DataContractError, match="ALPACA_POSSIBLE_CROSS_TYPE_DUPLICATE"):
        corporate_action_rows([page], ["BND"], window=WINDOW)
