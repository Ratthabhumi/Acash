"""RI-01 provider probe R1 harness tests (mock transport ONLY).

No live network, no credentials, no Homelab, no outcomes. Proves scope
gating (allowlist/holdout/capability/authorization), envelope integrity,
pagination to exhaustion, trade provenance preservation, entitlement
fail-closed, and stability comparison — all against synthetic payloads.
"""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider
from acash.research.ri01.probe import (
    ALLOWLISTED_SESSIONS,
    HOLDOUT_START,
    PROBE_SYMBOL,
    RI01ProbeClient,
    compare_stability,
    main,
    write_envelope,
)

CREDS = EnvAlpacaCredentialProvider(
    environ={
        "ACASH_ALPACA_API_KEY_ID": "mock_id",
        "ACASH_ALPACA_API_SECRET": "mock_secret",
    }
)


def _synthetic_bars(session: date, count: int) -> List[Dict[str, Any]]:
    calendar = NyseCa1Calendar()
    open_utc = calendar.get_session(session).open_utc
    assert open_utc is not None
    return [
        {
            "t": (open_utc + timedelta(minutes=k)).isoformat(),
            "o": 100,
            "h": 101,
            "l": 99,
            "c": 100.5,
            "v": 1000,
        }
        for k in range(count)
    ]


def _bars_transport(pages: Dict[str, List[List[Dict[str, Any]]]]) -> httpx.MockTransport:
    """Serve canned bar pages per session; record nothing, touch no network."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/stocks/bars"
        start = str(request.url.params["start"])
        session = start[:10]
        token = request.url.params.get("page_token")
        session_pages = pages[session]
        index = 0 if token is None else int(token)
        body = {
            "bars": {PROBE_SYMBOL: session_pages[index]},
            "next_page_token": (
                str(index + 1) if index + 1 < len(session_pages) else None
            ),
        }
        raw = json.dumps(body).encode("utf-8")
        return httpx.Response(
            200,
            content=raw,
            headers={
                "ratelimit_limit": "200",
                "ratelimit_remaining": "199",
                "ratelimit_reset": "1700000000",
            },
        )

    return httpx.MockTransport(handler)


def _trades_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/stocks/trades"
        body = {
            "trades": {
                PROBE_SYMBOL: [
                    {
                        "t": "2021-06-01T13:30:00.123456789Z",
                        "x": "P",
                        "p": 100.1,
                        "s": 50,
                        "c": ["O"],
                    },
                    {
                        "t": "2021-06-01T13:30:00.234567890Z",
                        "x": "N",
                        "p": 100.2,
                        "s": 10,
                        "c": ["Q"],
                    },
                    {
                        "t": "2021-06-01T19:59:59.999999999Z",
                        "x": "N",
                        "p": 101.3,
                        "s": 200,
                        "c": ["6"],
                    },
                ]
            },
            "next_page_token": None,
        }
        return httpx.Response(200, content=json.dumps(body).encode("utf-8"))

    return httpx.MockTransport(handler)


def _denied_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, content=b"{}")

    return httpx.MockTransport(handler)


def _raising_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be issued")

    return httpx.MockTransport(handler)


def test_dry_run_validates_scope_zero_network(tmp_path: Path, capsys: Any) -> None:
    assert (
        main(
            ["--session", "2018-06-01", "--capability", "bars"],
            _transport=_raising_transport(),
            _out_dir=tmp_path,
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "SESSION = 2018-06-01" in out
    assert "NETWORK_REQUESTS = 0" in out
    assert list(tmp_path.iterdir()) == []


def test_holdout_session_rejected_zero_network(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        main(
            [
                "--execute-network",
                "--authorization",
                "AUTHORIZE_RI01_PROBE_R1_X",
                "--session",
                "2024-03-01",
            ],
            _transport=_raising_transport(),
            _out_dir=tmp_path,
        )


def test_non_allowlisted_session_rejected_zero_network(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        main(
            [
                "--execute-network",
                "--authorization",
                "AUTHORIZE_RI01_PROBE_R1_X",
                "--session",
                "2020-01-02",
            ],
            _transport=_raising_transport(),
            _out_dir=tmp_path,
        )


def test_unknown_capability_rejected_zero_network(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        main(
            ["--session", "2018-06-01", "--capability", "quotes"],
            _transport=_raising_transport(),
            _out_dir=tmp_path,
        )


def test_missing_authorization_rejected_zero_network(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        main(
            ["--execute-network", "--session", "2018-06-01"],
            _transport=_raising_transport(),
            _out_dir=tmp_path,
        )


def test_holdout_boundary_constant() -> None:
    assert HOLDOUT_START == date(2023, 1, 1)
    assert PROBE_SYMBOL == "SPY"
    assert set(ALLOWLISTED_SESSIONS) == {
        date(2018, 6, 1),
        date(2021, 6, 1),
        date(2021, 11, 26),
    }
    assert all(session < HOLDOUT_START for session in ALLOWLISTED_SESSIONS)


@pytest.mark.parametrize(
    "session,count",
    [(date(2018, 6, 1), 390), (date(2021, 11, 26), 210)],
)
def test_bars_capability_envelope_and_grid(
    tmp_path: Path, capsys: Any, session: date, count: int
) -> None:
    bars = _synthetic_bars(session, count)
    pages = {session.isoformat(): [bars[:200], bars[200:]]}
    assert (
        main(
            [
                "--execute-network",
                "--authorization",
                "AUTHORIZE_RI01_PROBE_R1_X",
                "--session",
                session.isoformat(),
                "--capability",
                "bars",
            ],
            _transport=_bars_transport(pages),
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
            _out_dir=tmp_path,
            _credential_provider=CREDS,
        )
        == 0
    )
    out = capsys.readouterr().out
    assert f"BARS {session.isoformat()}: {count} bars" in out
    assert "NETWORK_REQUESTS_ISSUED = 2" in out
    session_dir = tmp_path / session.isoformat()
    payload = session_dir / "bars_1min_sip_raw.bin"
    envelope = session_dir / "bars_1min_sip_raw.envelope.json"
    assert payload.is_file() and envelope.is_file()
    # Digest binds the exact concatenated raw page bytes.
    assert hashlib.sha256(payload.read_bytes()).hexdigest() in out
    doc = json.loads(envelope.read_text(encoding="utf-8"))
    assert doc["content_sha256"] == hashlib.sha256(payload.read_bytes()).hexdigest()
    assert doc["rate_limits"]["ratelimit_limit"] == "200"
    assert doc["retrieved_at_utc"] == "2026-10-04T12:00:00+00:00"


def test_trades_window_preserves_venue_and_conditions(tmp_path: Path) -> None:
    assert (
        main(
            [
                "--execute-network",
                "--authorization",
                "AUTHORIZE_RI01_PROBE_R1_X",
                "--session",
                "2021-06-01",
                "--capability",
                "trades",
            ],
            _transport=_trades_transport(),
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
            _out_dir=tmp_path,
            _credential_provider=CREDS,
        )
        == 0
    )
    session_dir = tmp_path / "2021-06-01"
    assert (session_dir / "trades_sip_window_open.bin").is_file()
    assert (session_dir / "trades_sip_window_close.bin").is_file()
    envelope = json.loads(
        (session_dir / "trades_sip_window_open.envelope.json").read_text(
            encoding="utf-8"
        )
    )
    assert envelope["trade_count"] == 3
    assert envelope["window"] == "open"


def test_entitlement_denied_records_nothing(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        main(
            [
                "--execute-network",
                "--authorization",
                "AUTHORIZE_RI01_PROBE_R1_X",
                "--session",
                "2018-06-01",
                "--capability",
                "bars",
            ],
            _transport=_denied_transport(),
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
            _out_dir=tmp_path,
            _credential_provider=CREDS,
        )
    assert list(tmp_path.iterdir()) == []


def test_stability_comparison() -> None:
    assert compare_stability("a" * 64, "a" * 64) == "STABLE"
    assert compare_stability("a" * 64, "b" * 64) == "DIFFERENT"
    with pytest.raises(DataContractError):
        compare_stability("", "b" * 64)


def test_envelope_names_cannot_escape(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        write_envelope(
            tmp_path,
            "../escape",
            b"{}",
            {},
            datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
        )


def test_fetched_bars_carry_schema_only_no_metrics(tmp_path: Path) -> None:
    bars = _synthetic_bars(date(2018, 6, 1), 390)
    pages = {"2018-06-01": [bars]}
    client = RI01ProbeClient(
        credential_provider=CREDS, transport=_bars_transport(pages)
    )
    _, validated, _ = client.fetch_bars(date(2018, 6, 1), NyseCa1Calendar())
    assert len(validated) == 390
    assert all(set(bar.keys()) == {"timestamp", "open", "high", "low", "close", "volume"} for bar in validated)
