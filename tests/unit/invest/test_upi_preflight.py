"""Read-only pilot preflight: gate before parse, no amounts in output, actionable statuses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from acash.invest import preflight as pf
from acash.ppds import private_observation as po

FULL = Path("docs/research/evidence/upi_v1_2_synthetic_snapshot.json")
TOTALS_ONLY = Path("docs/research/evidence/upi_v1_2_synthetic_totals_only.json")
CAPACITY = Path("docs/research/evidence/upi_v1_synthetic_capacity.json")


def _status(report: Dict[str, Any], name: str) -> str:
    status: str = next(c["status"] for c in report["checks"] if c["check"] == name)
    return status


def test_synthetic_full_snapshot_is_ready_with_warnings_and_prints_no_amounts() -> None:
    report = pf.preflight(FULL, CAPACITY)
    assert report["preflight"] == "READY_WITH_WARNINGS"
    assert _status(report, "account_total:BROKER_D_MAIN") == "WARN"
    assert _status(report, "account_total:BANK_FCD") == "PASS"
    assert _status(report, "capacity") == "PASS"
    text = json.dumps(report)
    for amount in ("2250", "77220", "160.00", "95750", "500.00"):
        assert amount not in text


def test_totals_only_snapshot_reports_evidence_only() -> None:
    report = pf.preflight(TOTALS_ONLY)
    check = next(c for c in report["checks"] if c["check"] == "report_type")
    assert check["detail"] == "EVIDENCE_ONLY_REPORT"


def _private(tmp_path: Path, source: Path) -> Path:
    doc = json.loads(source.read_text(encoding="utf-8"))
    doc["data_class"] = "OWNER_PRIVATE_OBSERVATION"
    path = tmp_path / "data" / "private" / "snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_closed_odr_blocks_before_parsing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    path = _private(tmp_path, FULL)
    before = path.read_bytes()

    def never(*_: Any) -> None:
        raise AssertionError("private content parsed while unauthorized")
    monkeypatch.setattr(pf, "parse_snapshot", never)
    report = pf.preflight(path, output_dir=tmp_path / "data" / "private" / "out")
    assert report["preflight"] == "BLOCKED"
    assert _status(report, "odr_authorization") == "BLOCKED"
    assert path.read_bytes() == before


def test_ratified_fixture_passes_and_rejects_unsafe_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    record = tmp_path / po.AUTHORIZATION_RECORD
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({"capability": po.AUTHORIZED_CAPABILITY, "status": "RATIFIED", "ratified_by": "OWNER",
                                  "ratified_on": "2026-11-02", "scope_schemas": [po.SCHEMA_V1_2]}), encoding="utf-8")
    path = _private(tmp_path, FULL)
    assert pf.preflight(path, output_dir=tmp_path / "data" / "private" / "out")["preflight"] == "READY_WITH_WARNINGS"
    unsafe = pf.preflight(path, output_dir=tmp_path / "docs")
    assert (unsafe["preflight"], _status(unsafe, "output_location")) == ("INVALID", "FAIL")
    blocked_capacity = pf.preflight(path, capacity_path=CAPACITY)
    assert _status(blocked_capacity, "capacity") == "FAIL"


def test_malformed_snapshot_is_invalid_with_code(tmp_path: Path) -> None:
    doc = json.loads(FULL.read_text(encoding="utf-8"))
    doc["accounts"][0]["reported_total"]["amount"] = "-2250.00"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    report = pf.preflight(path)
    assert report["preflight"] == "INVALID"
    detail = next(c["detail"] for c in report["checks"] if c["status"] == "FAIL")
    assert detail == "PRIVATE_NEGATIVE_VALUE" and "2250" not in json.dumps(report)


def test_possible_duplicate_cash_across_accounts_is_warned(tmp_path: Path) -> None:
    doc = json.loads(FULL.read_text(encoding="utf-8"))
    doc["accounts"].append({"account_ref": "BANK_FCD_COPY", "broker": "BANK_A", "role": "CASH_RESERVE", "base_currency": "USD",
                            "cash": [{"currency": "USD", "amount": "500.00", "kind": "SETTLED"}]})
    path = tmp_path / "dup.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    report = pf.preflight(path)
    assert {"check": "cash_overlap", "status": "WARN",
            "detail": "POSSIBLE_DUPLICATE_CASH_ACROSS_ACCOUNTS: BANK_FCD,BANK_FCD_COPY"} in report["checks"]


def test_cli_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as ok:
        pf.main(["--snapshot", str(FULL)])
    assert ok.value.code == 0
    missing = tmp_path / "missing.json"
    with pytest.raises(SystemExit) as bad:
        pf.main(["--snapshot", str(missing)])
    assert bad.value.code == 2
    assert "PRIVATE_SNAPSHOT_UNREADABLE" in capsys.readouterr().out
