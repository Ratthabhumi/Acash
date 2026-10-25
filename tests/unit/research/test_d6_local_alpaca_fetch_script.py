"""fetch_alpaca_d6_local_data.convert: verified raw pages only, never the network."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.local_alpaca import page_record
from scripts import fetch_alpaca_d6_local_data as script


def _write_raw(raw: Path, tag: str, pages: list[dict[str, Any]]) -> None:
    raw.mkdir(parents=True, exist_ok=True)
    records, token = [], None
    for index, page in enumerate(pages, start=1):
        payload = json.dumps(page).encode()
        record = page_record(tag, index, token, payload)
        (raw / record["file"]).write_bytes(payload)
        records.append(record)
        token = record["next_page_token"]
    manifest = {"schema": script.SCHEMA, "requests": {tag: {"asof_status": "PINNED:2026-10-25"}}, "pages": records}
    (raw / script.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")


@pytest.fixture
def raw_dirs(tmp_path: Path) -> tuple[Path, Path]:
    bar = {"t": "2024-01-02T05:00:00Z", "o": 1, "c": 1}
    _write_raw(tmp_path / "bars", "bars", [{"bars": {"VOO": [bar]}, "next_page_token": "p2"},
                                           {"bars": {"BND": [bar]}, "next_page_token": None}])
    div = {"symbol": "VOO", "ex_date": "2024-03-22", "payable_date": "2024-03-27", "process_date": "2024-03-27",
           "rate": 1.5, "id": "d1"}
    _write_raw(tmp_path / "ca", "corporate_actions",
               [{"corporate_actions": {"cash_dividends": [div]}, "next_page_token": None}])
    return tmp_path / "bars", tmp_path / "ca"


def _convert(raw_dirs: tuple[Path, Path], out: Path) -> dict[str, Any]:
    bars, ca = raw_dirs
    return script.convert(bars, [(ca, "corporate_actions")], out, date(2016, 1, 1), date(2025, 12, 31), None)


def test_convert_is_offline_and_binds_sources(
    raw_dirs: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _no_network(*_: object, **__: object) -> None:
        raise AssertionError("network used")

    monkeypatch.setattr(httpx, "Client", _no_network)
    manifest = _convert(raw_dirs, tmp_path / "out")
    assert manifest["network"] == "NONE"
    assert manifest["counts"]["bars"] == 2 and manifest["counts"]["distributions"] == 1
    assert len(manifest["sources"]["bars"]["pages"]) == 2
    assert (tmp_path / "out" / "distributions.csv").read_text(encoding="utf-8").splitlines()[1].endswith(",d1,2024-03-27")
    with pytest.raises(DataContractError, match="OUTPUT_DIR_NOT_EMPTY"):
        _convert(raw_dirs, tmp_path / "out")


def test_convert_rejects_tampered_missing_or_extra_pages(raw_dirs: tuple[Path, Path], tmp_path: Path) -> None:
    bars, _ = raw_dirs
    page = bars / "bars_page_02.json"
    original = page.read_bytes()
    page.write_bytes(original.replace(b"BND", b"BIL"))
    with pytest.raises(DataContractError, match="RAW_PAGE_DIGEST_MISMATCH"):
        _convert(raw_dirs, tmp_path / "o1")
    page.unlink()
    with pytest.raises(DataContractError, match="RAW_PAGE_SET_MISMATCH"):
        _convert(raw_dirs, tmp_path / "o2")
    page.write_bytes(original)
    (bars / "bars_page_03.json").write_bytes(b"{}")
    with pytest.raises(DataContractError, match="RAW_PAGE_SET_MISMATCH"):
        _convert(raw_dirs, tmp_path / "o3")
    assert not (tmp_path / "o1").exists() and not (tmp_path / "o3").exists()
