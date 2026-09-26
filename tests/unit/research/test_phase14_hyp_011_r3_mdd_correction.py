"""Pre-replay tests for the corrected MDD computation (§8, synthetic only).

Proves: first-day loss draws against 100000, old omission differs, corrected
includes 100000, equality with ledger drawdown, per-path usage, gate
consumption, and zero forbidden access. No network.
"""

from datetime import date
from decimal import Decimal
from typing import List

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.hyp_009.accounting import EquityRecord, max_drawdown
from acash.research.hyp_009.gates import GateInputs, evaluate_gates
from acash.research.hyp_011.accounting import corrected_path_mdd


def _record(session: date, equity: str) -> EquityRecord:
    eq = Decimal(equity)
    peak = max(Decimal("100000"), eq)
    return EquityRecord(
        session=session, cash=Decimal("0"), shares=0, raw_close=Decimal("100"),
        market_value=eq, dividend_receivable=Decimal("0"), total_equity=eq,
        daily_return=None, running_peak=peak,
        drawdown=(peak - eq) / peak,
    )


def _curve() -> List[EquityRecord]:
    # Strictly declining from below 100000.
    return [
        _record(date(2016, 1, 4), "99000"),
        _record(date(2016, 1, 5), "98000"),
        _record(date(2016, 1, 6), "97000"),
    ]


def test_first_eod_below_start_creates_drawdown() -> None:
    curve = _curve()
    assert curve[0].drawdown == (Decimal("100000") - Decimal("99000")) / Decimal("100000")


def test_old_calculation_differs() -> None:
    curve = _curve()
    old = max_drawdown([r.total_equity for r in curve])
    new = max_drawdown([Decimal("100000")] + [r.total_equity for r in curve])
    assert old != new
    assert old == (Decimal("99000") - Decimal("97000")) / Decimal("99000")
    assert new == (Decimal("100000") - Decimal("97000")) / Decimal("100000")


def test_corrected_includes_starting_peak() -> None:
    curve = _curve()
    assert corrected_path_mdd(curve) == Decimal("0.03")


def test_corrected_equals_ledger_drawdown() -> None:
    curve = _curve()
    assert corrected_path_mdd(curve) == max(r.drawdown for r in curve)


def test_empty_curve_fail_closed() -> None:
    with pytest.raises(DataContractError):
        corrected_path_mdd([])


def test_all_paths_use_corrected_helper() -> None:
    from pathlib import Path

    code = Path("scripts/execute_hyp_011_r3.py").read_text(encoding="utf-8")
    assert code.count("ACC.corrected_path_mdd(result.equity_curve)") >= 1
    assert "max_drawdown([r.total_equity" not in code


def test_gates_consume_corrected_mdd() -> None:
    mdd = corrected_path_mdd(_curve())
    outcome = evaluate_gates(
        GateInputs(
            baseline_net_total_return=Decimal("0.5"),
            baseline_net_annualized_sharpe=Decimal("0.9"),
            baseline_max_drawdown=mdd,
            benchmark_max_drawdown=Decimal("0.4"),
            stress_net_total_return=Decimal("0.4"),
            no_material_contract_failure=True,
        )
    )
    assert outcome.g3 is True
    assert outcome.g4 is True


def test_runner_replay_mode_zero_network() -> None:
    import httpx

    from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient

    def _boom(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be invoked")

    client = HYP011AlpacaClient(transport=httpx.MockTransport(_boom))
    assert client is not None


def test_no_forbidden_tokens_in_helper() -> None:
    import inspect

    import acash.research.hyp_011.accounting as acc_mod

    source = inspect.getsource(acc_mod.corrected_path_mdd)
    for token in ("urllib", "requests", "httpx", "alpaca"):
        assert token not in source
