"""LOCAL_EXPLORATORY D6 mode: loading, validation, engine reuse and labelling."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.accounting import D6_REGISTERED_PORTFOLIOS, D6CostModel, run_d6_portfolio
from acash.research.d6.local_exploratory import (
    LOCAL_EXPLORATORY_LABEL,
    compute_metrics,
    coverage,
    load_local_inputs,
    render_report,
    run_local_exploratory,
)

SESSIONS = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
PRICES = {
    "VOO": [("100", "100"), ("99", "101"), ("101", "102"), ("102", "103"), ("103", "104")],
    "BND": [("70", "70"), ("70", "70.1"), ("70.1", "70.2"), ("70.2", "70.2"), ("70.2", "70.3")],
    "GLD": [("190", "190"), ("189", "191"), ("191", "192"), ("192", "191"), ("191", "193")],
    "BIL": [("91.5", "91.5"), ("91.5", "91.51"), ("91.51", "91.52"), ("91.52", "91.53"), ("91.53", "91.54")],
}
ZERO_COST = D6CostModel(label="ZERO_COST_UPPER_BOUND")
START, END = date(2024, 1, 1), date(2024, 1, 8)


def _bars(path: Path, skip: tuple[str, str] | None = None, adjustment: str = "raw") -> Path:
    rows = ["symbol,session,open,close,adjustment"]
    for sym, prices in PRICES.items():
        for session, (open_, close) in zip(SESSIONS, prices):
            if (sym, session) != skip:
                rows.append(f"{sym},{session},{open_},{close},{adjustment}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_all_five_comparators_run_and_are_labelled_local(tmp_path: Path) -> None:
    dist = _write(
        tmp_path / "d.csv",
        "symbol,ex_date,payable_date,gross_amount\nVOO,2024-01-04,2024-01-08,0.5\nBND,2024-01-04,2024-01-05,0.2\n",
    )
    inputs = load_local_inputs(_bars(tmp_path / "b.csv"), dist)
    outcomes = run_local_exploratory(inputs, start=START, end=END, cost=ZERO_COST)
    assert [o.portfolio for o in outcomes] == [p.name for p in D6_REGISTERED_PORTFOLIOS]
    assert all(o.status == "RUN" and o.result is not None for o in outcomes)
    assert all(o.result.label == LOCAL_EXPLORATORY_LABEL for o in outcomes if o.result)
    cash = outcomes[0].metrics
    assert cash is not None and cash["terminal_nav"] == Decimal("1000.00") and cash["total_return"] == 0
    report = render_report(inputs, outcomes, start=START, end=END, cost=ZERO_COST)
    assert "Not D5-admitted, not PIT-verified" in report
    assert "D5_REAL_DATA_ADMITTED" not in report
    assert "Imputed payable dates (labelled in the distributions file): none" in report


def test_imputed_payable_dates_are_counted_in_report(tmp_path: Path) -> None:
    dist = _write(
        tmp_path / "d.csv",
        "symbol,ex_date,payable_date,gross_amount,distribution_type,payable_date_source\n"
        "BND,2024-01-03,2024-01-09,0.2,DIVIDEND_CASH,IMPUTED_EX_PLUS_6D\n"
        "BND,2024-01-04,2024-01-05,0.2,DIVIDEND_CASH,PROVIDER\n",
    )
    inputs = load_local_inputs(_bars(tmp_path / "b.csv"), dist)
    assert inputs.imputed_payable == {"BND": 1}
    outcomes = run_local_exploratory(inputs, start=START, end=END, cost=ZERO_COST)
    assert "Imputed payable dates (labelled in the distributions file): BND=1" in render_report(
        inputs, outcomes, start=START, end=END, cost=ZERO_COST
    )


def test_voo_matches_hand_computed_causal_reference(tmp_path: Path) -> None:
    inputs = load_local_inputs(_bars(tmp_path / "b.csv"))
    voo = run_local_exploratory(inputs, start=START, end=END, cost=ZERO_COST)[2]
    assert voo.result is not None and voo.metrics is not None
    # Decide at 01-02 close 100 -> 10 shares; buy at 01-03 open 99; cash 10; final close 104.
    assert voo.result.trades[0].session == date(2024, 1, 3)
    assert voo.metrics["terminal_nav"] == Decimal("1050")
    direct = run_d6_portfolio(
        D6_REGISTERED_PORTFOLIOS[2],
        sessions=inputs.sessions,
        opens=inputs.opens,
        closes=inputs.closes,
        dividends={},
        cost=ZERO_COST,
    )
    assert direct.terminal_nav == voo.result.terminal_nav


def test_missing_session_marks_only_affected_portfolio_not_run(tmp_path: Path) -> None:
    inputs = load_local_inputs(_bars(tmp_path / "b.csv", skip=("GLD", "2024-01-05")))
    status = {o.portfolio: o for o in run_local_exploratory(inputs, start=START, end=END, cost=ZERO_COST)}
    four = status["VOO_BND_GLD_BIL_50_30_10_10"]
    assert four.status == "NOT_RUN" and four.result is None
    assert four.missing == ("GLD: 1 of 5 sessions missing (first 2024-01-05)",)
    assert status["VOO_BND_60_40"].status == "RUN"
    assert coverage(inputs, START, END)["GLD"]["missing"] == (date(2024, 1, 5),)


@pytest.mark.parametrize(
    "row, code",
    [
        ("VOO,2024-01-02,100,100,split", "LOCAL_ADJUSTED_BARS_REJECTED"),
        ("VOO,2024-01-02,0,100,raw", "LOCAL_NONPOSITIVE_OR_NONFINITE"),
        ("VOO,2024-01-02,NaN,100,raw", "LOCAL_NONPOSITIVE_OR_NONFINITE"),
        ("VOO,2024-01-02,Infinity,100,raw", "LOCAL_NONPOSITIVE_OR_NONFINITE"),
        ("VOO,2024-01-02,abc,100,raw", "LOCAL_UNPARSEABLE_NUMBER"),
        ("VOO,2024/01/02,100,100,raw", "LOCAL_BAD_DATE"),
        (",2024-01-02,100,100,raw", "LOCAL_EMPTY_SYMBOL"),
        ("VOO,2024-01-06,100,100,raw", "LOCAL_BAR_ON_NON_SESSION"),
        ("VOO,2024-01-15,100,100,raw", "LOCAL_BAR_ON_NON_SESSION"),
        ("VOO,2030-01-02,100,100,raw", "outside ratified CA-1"),
    ],
)
def test_malformed_bar_rows_fail_closed(tmp_path: Path, row: str, code: str) -> None:
    path = _write(tmp_path / "b.csv", f"symbol,session,open,close,adjustment\n{row}\n")
    with pytest.raises(DataContractError, match=code):
        load_local_inputs(path)


def test_session_missing_for_every_symbol_is_still_detected(tmp_path: Path) -> None:
    rows = ["symbol,session,open,close,adjustment"]
    rows += [f"VOO,{s},{o},{c},raw" for s, (o, c) in zip(SESSIONS, PRICES["VOO"]) if s != "2024-01-05"]
    inputs = load_local_inputs(_write(tmp_path / "b.csv", "\n".join(rows) + "\n"))
    voo = run_local_exploratory(inputs, start=START, end=END, cost=ZERO_COST)[2]
    assert voo.status == "NOT_RUN"
    assert voo.missing == ("VOO: 1 of 5 sessions missing (first 2024-01-05)",)


def test_duplicate_bar_and_missing_columns_rejected(tmp_path: Path) -> None:
    dup = "symbol,session,open,close,adjustment\nVOO,2024-01-02,1,1,raw\nvoo,2024-01-02,1,1,raw\n"
    with pytest.raises(DataContractError, match="LOCAL_DUPLICATE_BAR"):
        load_local_inputs(_write(tmp_path / "dup.csv", dup))
    with pytest.raises(DataContractError, match="LOCAL_CSV_COLUMNS_MISSING"):
        load_local_inputs(_write(tmp_path / "cols.csv", "symbol,session,open,close\nVOO,2024-01-02,1,1\n"))


def test_ex_date_off_session_is_rejected_not_silently_dropped(tmp_path: Path) -> None:
    dist = _write(tmp_path / "d.csv", "symbol,ex_date,payable_date,gross_amount\nVOO,2024-01-06,2024-01-08,0.5\n")
    with pytest.raises(DataContractError, match="LOCAL_EX_DATE_NOT_A_BAR_SESSION"):
        load_local_inputs(_bars(tmp_path / "b.csv"), dist)


def test_split_validation_and_unrecorded_split_flag(tmp_path: Path) -> None:
    off = _write(tmp_path / "s.csv", "symbol,session,ratio\nVOO,2024-01-06,2\n")
    with pytest.raises(DataContractError, match="LOCAL_SPLIT_NOT_ON_A_BAR_SESSION"):
        load_local_inputs(_bars(tmp_path / "b.csv"), splits_csv=off)
    jump = "symbol,session,open,close,adjustment\n" + "\n".join(
        f"VOO,{s},{p},{p},raw" for s, p in zip(SESSIONS, ["100", "100", "50", "50", "50"])
    )
    inputs = load_local_inputs(_write(tmp_path / "j.csv", jump + "\n"))
    assert coverage(inputs, START, END)["VOO"]["possible_unrecorded_splits"] == (date(2024, 1, 4),)


def test_gld_cash_distribution_rejected_by_engine(tmp_path: Path) -> None:
    dist = _write(tmp_path / "d.csv", "symbol,ex_date,payable_date,gross_amount\nGLD,2024-01-04,2024-01-05,0.1\n")
    inputs = load_local_inputs(_bars(tmp_path / "b.csv"), dist)
    with pytest.raises(DataContractError, match="D6_NO_CASH_DISTRIBUTION_ENTITLEMENT"):
        run_local_exploratory(inputs, start=START, end=END, cost=ZERO_COST)


def test_window_and_metric_boundaries(tmp_path: Path) -> None:
    inputs = load_local_inputs(_bars(tmp_path / "b.csv"))
    with pytest.raises(DataContractError, match="LOCAL_BAD_WINDOW"):
        run_local_exploratory(inputs, start=END, end=START, cost=ZERO_COST)
    with pytest.raises(DataContractError, match="LOCAL_EMPTY_WINDOW"):
        run_local_exploratory(inputs, start=date(2025, 1, 1), end=date(2025, 2, 1), cost=ZERO_COST)
    with pytest.raises(DataContractError, match="LOCAL_TOO_FEW_SESSIONS_FOR_METRICS"):
        run_local_exploratory(inputs, start=START, end=date(2024, 1, 3), cost=ZERO_COST)


def test_unrelated_symbol_order_does_not_change_results(tmp_path: Path) -> None:
    forward = load_local_inputs(_bars(tmp_path / "b.csv"))
    lines = (tmp_path / "b.csv").read_text(encoding="utf-8").splitlines()
    reversed_path = _write(tmp_path / "r.csv", "\n".join([lines[0], *reversed(lines[1:])]) + "\n")
    backward = load_local_inputs(reversed_path)
    a = run_local_exploratory(forward, start=START, end=END, cost=ZERO_COST)
    b = run_local_exploratory(backward, start=START, end=END, cost=ZERO_COST)
    assert [o.metrics for o in a] == [o.metrics for o in b]


def test_metrics_reject_short_curve() -> None:
    from acash.research.d6.accounting import D6NavRecord, D6Result

    result = D6Result(portfolio="X", cost_label="Z")
    result.nav_curve = [D6NavRecord(date(2024, 1, 2), Decimal(1), Decimal(0), Decimal(0), Decimal(1))]
    with pytest.raises(DataContractError, match="LOCAL_TOO_FEW_SESSIONS"):
        compute_metrics(result, Decimal(1))
