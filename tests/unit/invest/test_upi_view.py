"""Dashboard view model projection and the loopback private view server (synthetic and isolated ODR fixtures)."""

from __future__ import annotations

import copy
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterator

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.dashboard_api import private_view_server as srv
from acash.invest import upi_view as uv
from acash.invest.capacity_plan import load_capacity
from acash.invest.wealth_pack import build_wealth_pack
from acash.ppds import private_observation as po

PORT = srv.DEFAULT_PORT
TOKEN = "t" * 43
ORIGIN = srv.ALLOWED_ORIGINS[0]


def _pack(path: str = uv.SYNTHETIC_PACK) -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return doc


def _leaves(node: Any) -> Iterator[Any]:
    if isinstance(node, dict):
        for value in node.values():
            yield from _leaves(value)
    elif isinstance(node, list):
        for value in node:
            yield from _leaves(value)
    else:
        yield node


def test_synthetic_view_golden_values_copied_not_recomputed() -> None:
    view = uv.build_view(_pack())
    assert (view["view_schema"], view["data_mode"]) == ("ACASH_UPI_VIEW_V1", "SYNTHETIC_DEMO")
    overview = view["portfolio_overview"]
    assert (overview["computed_nav_ppds"], overview["observed_position_value"], overview["unclassified_holdings_value"],
            overview["total_best_evidence"]) == ("77220.00", "8250.00", "10280.00", "85470.00")
    assert overview["computed_nav_is_total_best_evidence"] is False
    assert view["concentration"]["status"] == "COMPLETE"
    amounts = {r["monthly_contribution_thb"] for r in view["financial_capacity"]["scenarios"]}
    assert {"5000.00", "7500.00", "10000.00"} <= amounts
    assert view["decision_status"]["orders_generated"] == 0
    assert "PRIVATE_OBSERVATION_AUTHORIZATION_NOT_REQUIRED" in view["data_quality"]["reason_codes"]
    assert view["governance"]["observation_authority"]["trading_authority"] == "NONE"
    assert not any(isinstance(v, float) for v in _leaves(view))


def test_evidence_only_view_keeps_unknown_as_null() -> None:
    view = uv.build_view(_pack(uv.SYNTHETIC_EVIDENCE_ONLY_PACK))
    assert view["report_metadata"]["report_type"] == "EVIDENCE_ONLY_REPORT"
    assert view["allocation"]["computed_by_classification"] is None
    assert view["allocation"]["computed_status"] == "NOT_COMPUTED_EVIDENCE_ONLY_REPORT"
    assert "EVIDENCE_ONLY_REPORT" in view["data_quality"]["reason_codes"]


def test_committed_dashboard_fixtures_match_regeneration(tmp_path: Path) -> None:
    for pack_path, fixture in uv.DASHBOARD_FIXTURES.items():
        out = uv.write_view(uv.build_view(_pack(pack_path)), tmp_path / Path(fixture).name)
        assert out.read_bytes() == Path(fixture).read_bytes()


@pytest.mark.parametrize("snapshot, pack_path, report_type", [
    ("docs/research/evidence/upi_v1_2_synthetic_snapshot.json", uv.SYNTHETIC_PACK, "FULL_REPORT"),
    ("docs/research/evidence/upi_v1_2_synthetic_totals_only.json", uv.SYNTHETIC_EVIDENCE_ONLY_PACK, "EVIDENCE_ONLY_REPORT"),
])
def test_synthetic_end_to_end_snapshot_to_dashboard_fixture(tmp_path: Path, snapshot: str, pack_path: str,
                                                            report_type: str) -> None:
    from acash.invest import preflight as pf
    from acash.invest import wealth_pack as wp

    report = pf.preflight(Path(snapshot), Path(wp.PUBLIC_CAPACITY))
    assert report["preflight"] == "READY_WITH_WARNINGS"
    targets = json.dumps({"CORE_DIVERSIFIED": "0.7", "CASH": "0.3"})
    wp.main(["--snapshot", snapshot, "--target-weights", targets, "--output", str(tmp_path / "pack")])
    pack = json.loads((tmp_path / "pack" / "upi_v1_pack.json").read_text(encoding="utf-8"))
    view_path = uv.write_view(uv.build_view(pack), tmp_path / "view.json")
    assert view_path.read_bytes() == Path(uv.DASHBOARD_FIXTURES[pack_path]).read_bytes()
    assert json.loads(view_path.read_text(encoding="utf-8"))["report_metadata"]["report_type"] == report_type


@pytest.mark.parametrize("mutate, code", [
    (lambda p: p.update(pack_version="X"), "VIEW_PACK_VERSION_UNSUPPORTED"),
    (lambda p: p.update(data_class="PUBLIC"), "VIEW_DATA_CLASS_INVALID"),
    (lambda p: p.update(data_class="OWNER_PRIVATE_OBSERVATION"), "PACK_AUTHORITY_INCONSISTENT"),
    (lambda p: p["A_total_wealth"].pop("evidence"), "VIEW_SNAPSHOT_SCHEMA_UNSUPPORTED"),
])
def test_malformed_or_contradictory_packs_fail_closed(mutate: Any, code: str) -> None:
    pack = copy.deepcopy(_pack())
    mutate(pack)
    with pytest.raises(DataContractError, match=code):
        uv.build_view(pack)


def test_v1_1_pack_is_unsupported() -> None:
    with pytest.raises(DataContractError, match="VIEW_SNAPSHOT_SCHEMA_UNSUPPORTED"):
        uv.build_view(_pack("docs/research/evidence/upi_v1_synthetic_pack/upi_v1_pack.json"))


def _private_view() -> Dict[str, Any]:
    view = uv.build_view(_pack())
    view["data_mode"] = "OWNER_PRIVATE_READ_ONLY"
    return view


def _ratify(root: Path, status: str = "RATIFIED") -> None:
    record = root / po.AUTHORIZATION_RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"capability": po.AUTHORIZED_CAPABILITY, "status": status, "ratified_by": "OWNER",
                                  "ratified_on": "2026-11-02", "scope_schemas": [po.SCHEMA_V1_2]}), encoding="utf-8")


def test_private_view_write_requires_odr_and_private_location(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    target = tmp_path / "data" / "private" / "out" / "upi_view.json"
    with pytest.raises(DataContractError, match="PRIVATE_OBSERVATION_NOT_AUTHORIZED"):
        uv.write_view(_private_view(), target)
    _ratify(tmp_path)
    with pytest.raises(DataContractError, match="PRIVATE_LOCATION_NOT_IGNORED"):
        uv.write_view(_private_view(), tmp_path / "dashboard" / "src" / "fixtures" / "leak.json")
    assert uv.write_view(_private_view(), target).is_file()


def _headers(**extra: str) -> Dict[str, str]:
    return {"Host": f"127.0.0.1:{PORT}", "Origin": ORIGIN, srv.TOKEN_HEADER: TOKEN, **extra}


def _call(view_path: Path, method: str = "GET", target: str = srv.ROUTE, **headers: Any) -> Any:
    status, out_headers, body = srv.respond(method, target, headers if headers else _headers(), TOKEN, view_path, PORT)
    return status, out_headers, json.loads(body) if body else None


@pytest.mark.parametrize("method, target, headers, status, code", [
    ("GET", srv.ROUTE, {"Host": "evil.example", "Origin": ORIGIN, srv.TOKEN_HEADER: TOKEN}, 421, "HOST_NOT_ALLOWED"),
    ("GET", srv.ROUTE, {"Host": f"127.0.0.1:{PORT}", srv.TOKEN_HEADER: TOKEN}, 403, "ORIGIN_NOT_ALLOWED"),
    ("GET", srv.ROUTE, {"Host": f"127.0.0.1:{PORT}", "Origin": "http://evil.example", srv.TOKEN_HEADER: TOKEN}, 403,
     "ORIGIN_NOT_ALLOWED"),
    ("GET", srv.ROUTE + "?path=C:/x.json", None, 404, "NOT_FOUND"),
    ("GET", "/api/upi/order", None, 404, "NOT_FOUND"),
    ("POST", srv.ROUTE, None, 405, "METHOD_NOT_ALLOWED"),
    ("DELETE", srv.ROUTE, None, 405, "METHOD_NOT_ALLOWED"),
    ("GET", srv.ROUTE, {"Host": f"127.0.0.1:{PORT}", "Origin": ORIGIN}, 401, "SESSION_TOKEN_REQUIRED"),
    ("GET", srv.ROUTE, {"Host": f"127.0.0.1:{PORT}", "Origin": ORIGIN, srv.TOKEN_HEADER: "wrong"}, 401,
     "SESSION_TOKEN_REQUIRED"),
])
def test_server_rejects_before_reading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method: str, target: str,
                                       headers: Any, status: int, code: str) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    _ratify(tmp_path)

    def never(*_: Any) -> None:
        raise AssertionError("view read before request checks")
    monkeypatch.setattr(po, "read_bounded_json", never)
    got_status, out_headers, body = srv.respond(method, target, headers or _headers(), TOKEN, tmp_path / "v.json", PORT)
    assert (got_status, json.loads(body)["status"]) == (status, code)
    assert out_headers["Cache-Control"] == "no-store"


def test_server_odr_states_and_view_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    view_path = tmp_path / "data" / "private" / "out" / "upi_view.json"
    status, _, body = _call(view_path)
    assert (status, body) == (403, {"status": "AUTHORIZATION_REQUIRED", "odr_state": "RECORD_UNREADABLE"})
    _ratify(tmp_path)
    assert _call(view_path)[2] == {"status": "NO_REPORT"}
    assert _call(view_path, "OPTIONS")[0] == 204
    uv.write_view(_private_view(), view_path)
    status, headers, body = _call(view_path)
    assert status == 200 and body["data_mode"] == "OWNER_PRIVATE_READ_ONLY"
    assert (headers["Cache-Control"], headers["Access-Control-Allow-Origin"]) == ("no-store", ORIGIN)
    view_path.write_text(json.dumps(uv.build_view(_pack())), encoding="utf-8")
    assert _call(view_path)[2] == {"status": "INVALID_REPORT", "code": "VIEW_CONTRACT_MISMATCH"}
    view_path.write_text("{bad", encoding="utf-8")
    assert _call(view_path)[2]["code"] == "UPI_VIEW_MALFORMED_JSON"
    _ratify(tmp_path, "REVOKED")
    assert _call(view_path)[2] == {"status": "AUTHORIZATION_REQUIRED", "odr_state": "REVOKED"}


def test_launcher_readiness_never_opens_view_without_odr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                         capsys: pytest.CaptureFixture[str]) -> None:
    from acash.dashboard_api import readiness as rd

    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    view_path = tmp_path / "data" / "private" / "out" / "upi_view.json"
    state = rd.readiness(view_path)
    assert (state["odr_001"], state["private_view"], state["private_mode"]) == (
        "RECORD_UNREADABLE", "NO_REPORT", "BLOCKED")
    assert state["governance"]["NO_REAL_ORDERS"] is True
    _ratify(tmp_path, "PROPOSED_NOT_RATIFIED")
    view_path.parent.mkdir(parents=True)
    view_path.write_text("{}", encoding="utf-8")

    real_read = po.read_bounded_json

    def never(*_: Any) -> None:
        raise AssertionError("view read while ODR-001 is not ratified")
    monkeypatch.setattr(po, "read_bounded_json", never)
    assert rd.readiness(view_path)["private_view"] == "PRESENT_NOT_OPENED"
    monkeypatch.setattr(po, "read_bounded_json", real_read)
    _ratify(tmp_path)
    assert rd.readiness(view_path)["private_view"] == "INVALID_REPORT (VIEW_CONTRACT_MISMATCH)"
    uv.write_view(_private_view(), view_path)
    assert rd.readiness(view_path) | {"governance": None} == {
        "governance": None, "odr_001": "RATIFIED", "odr_002": "RECORD_UNREADABLE", "odr_003": "RECORD_UNREADABLE",
        "private_view": "READY",
        "private_mode": "READY", "blockers": []}

    _ratify(tmp_path, "REVOKED")
    monkeypatch.setattr(rd, "DEFAULT_VIEW", view_path.relative_to(tmp_path))
    with pytest.raises(SystemExit) as exit_info:
        rd.main(["--require-private"])
    assert exit_info.value.code == 3
    out = capsys.readouterr().out
    assert "Private mode : BLOCKED - ODR-001 REVOKED; private view PRESENT_NOT_OPENED" in out
    assert "NO_REAL_ORDERS=true" in out and '"' not in out
    rd.main([])


def test_dashboard_api_has_no_trading_or_outbound_network_imports() -> None:
    import re

    package_dir = Path(srv.__file__).resolve().parent
    import_pattern = re.compile(r"^\s*(import|from)\s+([\w\.]+)", re.MULTILINE)
    for path in sorted(package_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in import_pattern.finditer(text):
            parts = match.group(2).lower().split(".")
            for banned in ("alpaca", "broker", "order", "socket", "urllib", "requests", "websocket", "execution", "paper"):
                assert banned not in parts, f"{path.name} imports {match.group(2)!r}"
        for token in ("api_secret", "api_key", "password"):
            assert token not in text.lower()


def test_server_binds_loopback_and_refuses_tracked_view_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    with pytest.raises(DataContractError, match="PRIVATE_LOCATION_NOT_IGNORED"):
        srv.serve(0, tmp_path / "dashboard" / "public" / "view.json")
    server = srv.serve(0, tmp_path / "data" / "private" / "out" / "upi_view.json")
    try:
        assert server.server_address[0] == "127.0.0.1"
    finally:
        server.server_close()


def _synthetic_pack_with_fund(tmp_path: Path, with_fund: bool) -> Dict[str, Any]:
    snapshot = json.loads((Path("docs/research/evidence/upi_v1_2_synthetic_snapshot.json")).read_text(encoding="utf-8"))
    snapshot["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    capacity = json.loads((Path("docs/research/evidence/upi_v1_synthetic_capacity.json")).read_text(encoding="utf-8"))
    capacity["data_class"] = snapshot["data_class"]
    cap_path = tmp_path / "capacity.json"
    cap_path.write_text(json.dumps(capacity), encoding="utf-8")
    if with_fund:
        snapshot["securities"].append({"security_id": "SCBSET50", "instrument_type": "OTHER",
                                       "classification": "UNKNOWN", "methodology": "NOT_CLASSIFIED"})
        snapshot["prices"].append({"security_id": "SCBSET50", "price": "24.0440", "currency": "THB",
                                   "as_of": snapshot["valuation_date"], "source_id": "DIME_APP_DISPLAY"})
        main = next(a for a in snapshot["accounts"] if a["account_ref"] == "BROKER_D_MAIN")
        main["positions"].append({"security_id": "SCBSET50", "quantity": "4.3422",
                                  "cost_basis_total": "100.00", "cost_basis_currency": "THB"})
    pack = build_wealth_pack(po.build_book(po.parse_snapshot(snapshot)), load_capacity(cap_path), None,
                             date.fromisoformat(snapshot["valuation_date"]))
    return uv.build_view(json.loads(json.dumps(pack)))


def test_thb_fund_inside_a_usd_account_is_not_multiplied_by_fx(tmp_path: Path) -> None:
    """Regression (Owner SCBSET50): a THB NAV per unit must stay THB, never take an FX multiplier."""
    before = _synthetic_pack_with_fund(tmp_path, with_fund=False)
    after = _synthetic_pack_with_fund(tmp_path, with_fund=True)

    def account_value(view: Dict[str, Any], ref: str) -> Decimal:
        return Decimal(str(next(a for a in view["accounts"] if a["account_ref"] == ref)["computed_value"]))

    delta = account_value(after, "BROKER_D_MAIN") - account_value(before, "BROKER_D_MAIN")
    expected = Decimal("4.3422") * Decimal("24.0440")
    assert abs(delta - expected) < Decimal("0.01")          # units x THB NAV, no x33 and no /0.03
    assert delta < Decimal("200")                            # a double FX conversion would exceed 3,500
    nav_delta = Decimal(str(after["portfolio_overview"]["computed_nav_ppds"])) - \
        Decimal(str(before["portfolio_overview"]["computed_nav_ppds"]))
    assert abs(nav_delta - expected) < Decimal("0.01")


def test_stale_view_is_reported_stale_instead_of_as_current(tmp_path: Path,
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    """A report generated before an input correction must never be served as current figures."""
    from acash.dashboard_api import private_input as pi

    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    path = tmp_path / "upi_view.json"
    path.write_text(json.dumps(_private_view()), encoding="utf-8")
    monkeypatch.setattr(pi, "report_consistency",
                        lambda: {"status": "CONSISTENT", "generation_id": "g", "generated_at": "t",
                                 "inputs_changed_since": False})
    assert srv.load_view(path)[0] == "READY"
    monkeypatch.setattr(pi, "report_consistency",
                        lambda: {"status": "CONSISTENT", "generation_id": "g", "generated_at": "t",
                                 "inputs_changed_since": True})
    status, code, doc = srv.load_view(path)
    assert (status, code) == ("STALE_REPORT", "REPORT_INPUT_STALE") and doc is not None


def test_allocations_exclude_the_unqualified_residual() -> None:
    """The broker residual is diagnostics; it must not appear in any allocation or weight."""
    view = uv.build_view(_pack())
    assert "UNCLASSIFIED_RESIDUAL" not in view["allocation"]["currency_exposure_best_evidence"]
    assert view["concentration"]["unclassified_share"] == "0.0000"
    assert view["concentration"]["status"] == "COMPLETE"
    residual = view["portfolio_overview"]["unclassified_holdings_value"]
    assert residual != "0.00"                      # still reported as diagnostics
    assert view["portfolio_overview"]["total_best_evidence"] == "85470.00"


def test_position_rows_are_conserved_and_never_include_the_broker_residual() -> None:
    """Rows describe held lines only; cash and an unqualified broker residual stay out of them."""
    view = uv.build_view(_pack())
    block = view["positions"]
    rows = block["rows"]
    assert block["schema"] == "ACASH_POSITION_ROWS_V1" and block["status"] == "AVAILABLE"
    assert rows and all(Decimal(r["value_reporting"]) > 0 for r in rows)
    total_rows = sum(Decimal(r["value_reporting"]) for r in rows)
    assert total_rows == Decimal(block["position_value_total"])
    total = Decimal(view["portfolio_overview"]["total_best_evidence"])
    residual = Decimal(view["portfolio_overview"]["unclassified_holdings_value"])
    # Held lines + the reconciliation residual cannot reach the total, because cash is neither.
    assert total_rows + residual <= total
    assert all(r["source"] in ("PPDS_QUANTITY_X_PRICE", "BROKER_OBSERVED_MARKET_VALUE") for r in rows)
    assert sum(Decimal(r["weight"]) for r in rows) < Decimal(1)
    assert all(r["weight_basis"] == "SHARE_OF_TOTAL_BEST_EVIDENCE" for r in rows)


def test_position_rows_never_invent_a_cost_basis_or_a_quantity() -> None:
    rows = uv.build_view(_pack())["positions"]["rows"]
    for row in rows:
        established = row["cost_basis_status"] == "ESTABLISHED"
        assert (row["unrealized_pnl_local"] is not None) is established
        assert row["unrealized_status"] == ("COMPUTED" if established else "COST_BASIS_NOT_ESTABLISHED")
        if row["source"] == "BROKER_OBSERVED_MARKET_VALUE":
            assert row["quantity"] is None and row["price"] is None
        else:
            assert row["quantity"] is not None and row["price"] is not None


def test_position_rows_are_identical_after_regeneration(tmp_path: Path) -> None:
    first = uv.build_view(_pack())
    written = uv.write_view(first, tmp_path / "view.json")
    again = json.loads(written.read_text(encoding="utf-8"))
    assert again["positions"] == first["positions"]
    assert len(again["positions"]["rows"]) == len(first["positions"]["rows"])
