"""Canary 2 proposed scope and unissued authority: mock HTTP only."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider
from acash.research.ri01.probe import RI01ProbeAuthority, RI01ProbeClient, main

ROOT = Path(__file__).resolve().parents[3]


def candidate() -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads(
        (ROOT / "docs/research/ri01/RI01_CANARY2_UNISSUED_AUTHORITY.json").read_text()
    )
    return doc


def test_canary2_unissued_candidate_cannot_execute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("unissued candidate reached HTTP")

    monkeypatch.setattr(httpx.Client, "request", forbidden)
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(candidate()))
    with pytest.raises(DataContractError, match="AUTHORITY_LOAD_FAILED"):
        main(["--execute-network", "--authority-file", str(path)], _runtime_sha=candidate()["runtime_sha"])


def test_canary2_scope_only_dry_run_zero_http(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("dry run reached HTTP")

    monkeypatch.setattr(httpx.Client, "request", forbidden)
    assert main(["--session", "2018-06-01", "--capability", "bars"]) == 0
    assert "NETWORK_REQUESTS = 0" in capsys.readouterr().out


@pytest.mark.parametrize("field", [
    "feed", "timeframe", "adjustment", "start", "end", "expected_grid",
    "proposed_validity",
])
def test_review_metadata_is_not_executable_authority(field: str) -> None:
    doc = candidate()
    doc[field] = "review-only"
    with pytest.raises(DataContractError, match="AUTHORITY_UNKNOWN_FIELDS"):
        RI01ProbeAuthority.from_dict(doc)


def test_unissued_identity_stays_invalid_after_resolving_other_fields(tmp_path: Path) -> None:
    doc = candidate()
    doc.update({
        "evidence_root": str(tmp_path / "outside_canary2"),
        "valid_from_utc": "2026-10-09T00:00:00+00:00",
        "valid_until_utc": "2026-10-09T02:00:00+00:00",
    })
    auth = RI01ProbeAuthority.from_dict(doc)
    with pytest.raises(DataContractError, match="BAD_AUTHORITY_ID"):
        auth.validate(
            datetime(2026, 10, 9, 0, 30, tzinfo=timezone.utc),
            str(doc["runtime_sha"]), NyseCa1Calendar(),
        )


@pytest.mark.parametrize("page_size,expected_requests,complete", [(200, 2, True), (100, 3, False)])
def test_canary2_budget_and_exact_grid_mock_only(
    tmp_path: Path, page_size: int, expected_requests: int, complete: bool,
) -> None:
    doc = candidate()
    doc.update({
        "authority_id": "AUTHORIZE_RI01_PROBE_R1_CANARY2_SYNTHETIC_TEST",
        "evidence_root": str(tmp_path / "outside_canary2"),
        "valid_from_utc": "2026-10-09T00:00:00+00:00",
        "valid_until_utc": "2026-10-09T02:00:00+00:00",
    })
    auth = RI01ProbeAuthority.from_dict(doc)
    now = datetime(2026, 10, 9, 0, 30, tzinfo=timezone.utc)
    calendar = NyseCa1Calendar()
    auth.validate(now, str(doc["runtime_sha"]), calendar)
    opened = datetime(2018, 6, 1, 13, 30, tzinfo=timezone.utc)
    # 391 raw bars including the 20:00 UTC inclusive boundary bar
    bars = [
        {
            "t": (opened + timedelta(minutes=k)).isoformat(),
            "o": 270.0 + k * 0.01,
            "h": 270.5 + k * 0.01,
            "l": 269.5 + k * 0.01,
            "c": 270.2 + k * 0.01,
            "v": 5000,
        }
        for k in range(391)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "data.alpaca.markets"
        assert request.url.params["feed"] == "sip"
        assert request.url.params["adjustment"] == "raw"
        assert request.url.params["start"] == "2018-06-01T13:30:00+00:00"
        assert request.url.params["end"] == "2018-06-01T20:00:00+00:00"
        offset = int(request.url.params.get("page_token", "0"))
        end = min(offset + page_size, 391)
        return httpx.Response(200, json={
            "bars": {"SPY": bars[offset:end]},
            "next_page_token": str(end) if end < 391 else None,
        })

    creds = EnvAlpacaCredentialProvider(environ={
        "ACASH_ALPACA_API_KEY_ID": "synthetic", "ACASH_ALPACA_API_SECRET": "synthetic",
    })
    client = RI01ProbeClient(creds, httpx.MockTransport(handler))
    if complete:
        manifest, qualified = client.fetch_bars(auth, calendar, now)
        assert manifest.status == "RETRIEVED"
        assert manifest.item_count == 391
        assert len(qualified) == 390
        assert client.last_qualification_record is not None
        assert client.last_qualification_record.status == "QUALIFIED"
        assert client.last_qualification_record.qualified_item_count == 390
    else:
        with pytest.raises(DataContractError, match="REQUEST_BUDGET_EXHAUSTED"):
            client.fetch_bars(auth, calendar, now)
        folder = auth.evidence_root / "2018-06-01" / "bars"
        terminal = json.loads((folder / "manifest.json").read_text())
        assert terminal["status"] == "PARTIAL" and terminal["item_count"] == 300
        assert not (folder / "qualification.json").exists()
    assert client.requests_issued == expected_requests <= 3
