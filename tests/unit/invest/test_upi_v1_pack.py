"""Capacity planner and unified portfolio intelligence pack (synthetic fixtures only)."""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import capacity_plan as cp
from acash.invest import wealth_pack as wp
from acash.ppds import private_observation as po

CAPACITY = Path(wp.PUBLIC_CAPACITY)
SNAPSHOT = Path(wp.PUBLIC_SNAPSHOT)
PUBLIC_PACK_DIR = Path("docs/research/evidence/upi_v1_synthetic_pack")


def _capacity_doc() -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads(CAPACITY.read_text(encoding="utf-8"))
    return doc


def _pack() -> Dict[str, Any]:
    return wp.build_wealth_pack(po.build_book(po.load_snapshot(SNAPSHOT)), cp.load_capacity(CAPACITY))


def test_capacity_golden_values() -> None:
    result = cp.assess_capacity(cp.parse_capacity(_capacity_doc()))
    assert result["monthly_surplus_thb"] == "15000.00"
    assert result["reserve"]["target_thb"] == "30000.00"
    assert result["reserve"]["shortfall_thb"] == "10000.00"
    rows = {r["monthly_contribution_thb"]: r for r in result["scenarios"]}
    assert rows["5000.00"]["months_to_reserve_target_from_residual"] == 1
    assert rows["10000.00"]["months_to_reserve_target_from_residual"] == 2
    assert {r["status"] for r in result["scenarios"]} == {"RESERVE_SHORTFALL_PRIORITY"}
    assert result["quant_budget"]["authorization"] == "NOT_AUTHORIZED"
    assert result["quant_budget"]["fundable_from_reserve_excess"] is False


def test_contribution_exceeding_surplus_and_reserve_met() -> None:
    doc = _capacity_doc()
    doc.update(monthly_income_thb="12000", emergency_reserve_thb="40000")
    rows = {r["monthly_contribution_thb"]: r["status"] for r in cp.assess_capacity(cp.parse_capacity(doc))["scenarios"]}
    assert rows["5000.00"] == "CONTRIBUTION_EXCEEDS_SURPLUS"
    doc.update(monthly_income_thb="30000")
    result = cp.assess_capacity(cp.parse_capacity(doc))
    assert {r["status"] for r in result["scenarios"]} == {"WITHIN_SURPLUS_RESERVE_MET"}
    assert result["quant_budget"]["fundable_from_reserve_excess"] is True


def test_exceptional_expense_reduces_reserve_and_no_progress_is_none() -> None:
    doc = _capacity_doc()
    doc.update(exceptional_expenses_12m_thb="5000", monthly_income_thb="10000")
    result = cp.assess_capacity(cp.parse_capacity(doc))
    assert result["reserve"]["effective_thb"] == "15000.00"
    assert result["capacity_status"] == "CAPACITY_NOT_POSITIVE"
    assert all(r["months_to_reserve_target_from_residual"] is None for r in result["scenarios"])


@pytest.mark.parametrize("field, value, code", [
    ("monthly_income_thb", 25000.0, "CAPACITY_NUMBER_MUST_BE_STRING"),
    ("monthly_income_thb", "-1", "CAPACITY_INVALID_AMOUNT"),
    ("horizon_years", True, "CAPACITY_HORIZON_INVALID"),
    ("horizon_years", 0, "CAPACITY_HORIZON_INVALID"),
    ("surprise", "1", "CAPACITY_UNKNOWN_FIELDS"),
    ("data_class", "REAL", "CAPACITY_SCHEMA_OR_DATA_CLASS_INVALID"),
])
def test_capacity_malformed(field: str, value: Any, code: str) -> None:
    doc = _capacity_doc()
    doc[field] = value
    with pytest.raises(DataContractError, match=code):
        cp.parse_capacity(doc)


def test_capacity_zero_need_fails_closed() -> None:
    doc = _capacity_doc()
    doc.update(essential_expenses_thb="0", obligations_thb="0")
    with pytest.raises(DataContractError, match="CAPACITY_MONTHLY_NEED_ZERO"):
        cp.parse_capacity(doc)


def test_contribution_first_never_sells_and_conserves() -> None:
    current = {"CORE_DIVERSIFIED": Decimal("500"), "THEMATIC": Decimal("400"), "CASH": Decimal("100")}
    targets = {"CORE_DIVERSIFIED": Decimal("0.8"), "CASH": Decimal("0.2")}
    result = cp.contribution_first_allocation(current, targets, Decimal("300"))
    alloc = {k: Decimal(v) for k, v in result["allocation"].items()}
    assert alloc["THEMATIC"] == Decimal("0.00")
    assert sum(alloc.values()) == Decimal("300.00")
    assert result["sells"] == "NONE" and result["label"] == "ILLUSTRATIVE_ALLOCATION_NOT_AN_ORDER"
    with pytest.raises(DataContractError, match="SUM_TO_ONE"):
        cp.contribution_first_allocation(current, {"CASH": Decimal("0.5")}, Decimal("1"))
    with pytest.raises(DataContractError, match="CONTRIBUTION_NONPOSITIVE"):
        cp.contribution_first_allocation(current, targets, Decimal("0"))


def test_pack_concludes_no_action_and_generates_no_orders() -> None:
    pack = _pack()
    assert pack["E_decision"]["conclusion"] == "NO_ACTION_PENDING_EVIDENCE"
    assert pack["E_decision"]["orders_generated"] == 0
    assert pack["governance"]["NO_REAL_ORDERS"] is True
    assert pack["C_quant_workspace"]["status"] == "RESEARCH_ONLY_NOT_AUTHORIZED"
    assert sorted(pack["D_financial_capacity"]["v38_route_costs_per_contribution"]) == ["10000", "5000", "7500"]


def test_pack_is_deterministic_and_references_v38_pack() -> None:
    first, second = _pack(), _pack()
    assert first["pack_sha256"] == second["pack_sha256"]
    v38 = json.loads(Path(wp.V38_PACK_JSON).read_text(encoding="utf-8"))
    assert first["E_decision"]["v38_decision_pack"]["pack_sha256"] == v38["pack_sha256"]


def test_pack_rejects_mixed_data_classes() -> None:
    book = po.build_book(po.load_snapshot(SNAPSHOT))
    owner_capacity = replace(cp.load_capacity(CAPACITY), data_class="OWNER_PRIVATE_OBSERVATION")
    with pytest.raises(DataContractError, match="PACK_DATA_CLASS_MISMATCH"):
        wp.build_wealth_pack(book, owner_capacity)


def test_owner_private_pack_cannot_be_written_to_tracked_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    pack = dict(_pack(), data_class="OWNER_PRIVATE_OBSERVATION")
    with pytest.raises(DataContractError, match="PRIVATE_LOCATION_NOT_IGNORED"):
        wp.write_pack(pack, tmp_path / "docs")
    written = wp.write_pack(pack, tmp_path / "data" / "private" / "out")
    assert [p.name for p in written] == ["upi_v1_pack.json", "upi_v1_pack.md"]


def test_committed_public_pack_matches_regeneration(tmp_path: Path) -> None:
    targets = '{"CORE_DIVERSIFIED": "0.7", "CASH": "0.3"}'
    wp.main(["--target-weights", targets, "--output", str(tmp_path)])
    for name in ("upi_v1_pack.json", "upi_v1_pack.md"):
        assert (tmp_path / name).read_bytes() == (PUBLIC_PACK_DIR / name).read_bytes()
