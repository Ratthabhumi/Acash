"""Cross-client/identity/root replay attempts must not invoke HTTP again."""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.evidence import content_sha256
from acash.research.ri01.probe import RI01ProbeAuthority
from scripts import ri01_canary_single_use as driver

NOW = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)


def authority(tmp_path: Path) -> RI01ProbeAuthority:
    root = tmp_path / "canary"
    root.mkdir()
    return RI01ProbeAuthority(
        authority_id="AUTHORIZE_RI01_PROBE_R1_CANARY2_TEST",
        runtime_sha=driver.PINNED_RUNTIME,
        session=date(2018, 6, 1),
        capability="bars",
        evidence_root=root,
        max_requests=3,
        valid_from_utc=datetime(2026, 10, 11, 11, tzinfo=timezone.utc),
        valid_until_utc=datetime(2026, 10, 11, 13, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize("replay", ["same", "identity_new_root", "new_identity_same_root"])
def test_cross_client_replay_zero_additional_http(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replay: str
) -> None:
    monkeypatch.setattr(driver, "get_current_runtime_sha", lambda: driver.PINNED_RUNTIME)
    monkeypatch.setenv("ACASH_ALPACA_API_KEY_ID", "synthetic")
    monkeypatch.setenv("ACASH_ALPACA_API_SECRET", "synthetic")
    auth = authority(tmp_path)
    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        assert (auth.evidence_root / "single-operation-start.json").is_file()
        assert len(list((tmp_path / "claims").glob("*.json"))) == 3
        return httpx.Response(403, json={})

    digest = content_sha256(Path(driver.__file__).read_bytes())
    result = driver.execute_once(
        auth, tmp_path / "claims", digest, transport=httpx.MockTransport(handler), now=NOW
    )
    assert result["local_http_invocations"] == count == 1
    replay_auth = auth
    if replay == "identity_new_root":
        other = tmp_path / "other"
        other.mkdir()
        replay_auth = replace(
            auth, evidence_root=other, valid_until_utc=datetime(2026, 10, 11, 14, tzinfo=timezone.utc)
        )
    elif replay == "new_identity_same_root":
        replay_auth = replace(auth, authority_id="AUTHORIZE_RI01_PROBE_R1_CANARY2_OTHER")
    with pytest.raises(DataContractError):
        driver.execute_once(
            replay_auth, tmp_path / "claims", digest, transport=httpx.MockTransport(handler), now=NOW
        )
    assert count == 1


def test_partial_claim_and_wrong_driver_fail_before_http(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(driver, "get_current_runtime_sha", lambda: driver.PINNED_RUNTIME)
    auth = authority(tmp_path)
    digest = content_sha256(Path(driver.__file__).read_bytes())
    claims = tmp_path / "claims"
    claims.mkdir()
    # Simulate crash after the identity claim; no evidence pages exist yet.
    (claims / f"authority-id-{content_sha256(auth.authority_id)}.json").write_text(
        json.dumps({"reserved": True})
    )

    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail("reserved authority reached HTTP")

    with pytest.raises(DataContractError):
        driver.execute_once(
            auth, claims, digest, transport=httpx.MockTransport(forbidden), now=NOW
        )
    with pytest.raises(DataContractError, match="DRIVER_HASH_MISMATCH"):
        driver.execute_once(
            auth, claims, "0" * 64, transport=httpx.MockTransport(forbidden), now=NOW
        )


def _claim_in_process(target: str, index: int) -> bool:
    from acash.evidence import write_immutable_json

    try:
        write_immutable_json(Path(target), {"index": index})
        return True
    except DataContractError:
        return False


def test_atomic_cross_process_race_has_one_winner(tmp_path: Path) -> None:
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context

    target = str(tmp_path / "claim.json")
    with ProcessPoolExecutor(max_workers=4, mp_context=get_context("spawn")) as pool:
        winners = list(pool.map(_claim_in_process, [target] * 4, range(4)))
    assert sum(winners) == 1


def test_driver_http_failure_and_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(driver, "get_current_runtime_sha", lambda *args, **kwargs: driver.PINNED_RUNTIME)
    monkeypatch.setenv("ACASH_ALPACA_API_KEY_ID", "synthetic")
    monkeypatch.setenv("ACASH_ALPACA_API_SECRET", "synthetic")
    auth = authority(tmp_path)
    claims = tmp_path / "claims"
    digest = content_sha256(Path(driver.__file__).read_bytes())

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={})

    result = driver.execute_once(
        auth, claims, digest, transport=httpx.MockTransport(handler), now=NOW
    )
    assert result["local_http_invocations"] == 1
    assert result["failure_type"] == "DataContractError"
    assert result["retrieval_status"] == "ACCESS_FORBIDDEN"
    assert result["qualification_status"] is None

    result_on_disk = json.loads((auth.evidence_root / "single-operation-result.json").read_text())
    assert result_on_disk["failure_type"] == "DataContractError"
    assert result_on_disk["retrieval_status"] == "ACCESS_FORBIDDEN"

    # Verify CLI main exits nonzero
    auth_file = tmp_path / "authority.json"
    auth_file.write_text(json.dumps(auth.to_dict()))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "driver",
            "--authority-file",
            str(auth_file),
            "--claims-dir",
            str(claims),
            "--expected-driver-sha256",
            digest,
            "--execute-approved",
        ],
    )
    import subprocess

    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "")
    monkeypatch.setattr(
        driver,
        "execute_once",
        lambda *args, **kwargs: result,
    )
    with pytest.raises(SystemExit) as exc_info:
        driver.main()
    assert exc_info.value.code == 1


def test_driver_transport_failure_and_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(driver, "get_current_runtime_sha", lambda *args, **kwargs: driver.PINNED_RUNTIME)
    monkeypatch.setenv("ACASH_ALPACA_API_KEY_ID", "synthetic")
    monkeypatch.setenv("ACASH_ALPACA_API_SECRET", "synthetic")
    auth = authority(tmp_path)
    claims = tmp_path / "claims"
    digest = content_sha256(Path(driver.__file__).read_bytes())

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    result = driver.execute_once(
        auth, claims, digest, transport=httpx.MockTransport(handler), now=NOW
    )
    assert result["local_http_invocations"] == 1
    assert result["failure_type"] == "DataContractError"
    assert result["retrieval_status"] == "TRANSPORT_FAILED"
    assert result["qualification_status"] is None

    auth_file = tmp_path / "authority.json"
    auth_file.write_text(json.dumps(auth.to_dict()))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "driver",
            "--authority-file",
            str(auth_file),
            "--claims-dir",
            str(claims),
            "--expected-driver-sha256",
            digest,
            "--execute-approved",
        ],
    )
    import subprocess

    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "")
    monkeypatch.setattr(driver, "execute_once", lambda *args, **kwargs: result)
    with pytest.raises(SystemExit) as exc_info:
        driver.main()
    assert exc_info.value.code == 1


def test_driver_incomplete_grid_contract_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(driver, "get_current_runtime_sha", lambda *args, **kwargs: driver.PINNED_RUNTIME)
    monkeypatch.setenv("ACASH_ALPACA_API_KEY_ID", "synthetic")
    monkeypatch.setenv("ACASH_ALPACA_API_SECRET", "synthetic")
    auth = authority(tmp_path)
    claims = tmp_path / "claims"
    digest = content_sha256(Path(driver.__file__).read_bytes())

    # Return only 5 bars instead of expected 390
    partial_bars = [
        {"t": f"2018-06-01T13:3{i}:00Z", "o": 270.0, "h": 271.0, "l": 269.0, "c": 270.5, "v": 1000}
        for i in range(5)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"bars": {"SPY": partial_bars}, "next_page_token": None})

    result = driver.execute_once(
        auth, claims, digest, transport=httpx.MockTransport(handler), now=NOW
    )
    assert result["local_http_invocations"] == 1
    assert result["failure_type"] == "DataContractError"
    assert result["retrieval_status"] == "RETRIEVED"
    assert result["qualification_status"] == "CONTRACT_FAILED"

    # Disk evidence preserves both manifest and qualification
    qual_path = auth.evidence_root / "2018-06-01" / "bars" / "qualification.json"
    assert qual_path.is_file()
    qual_data = json.loads(qual_path.read_text())
    assert qual_data["status"] == "CONTRACT_FAILED"

    auth_file = tmp_path / "authority.json"
    auth_file.write_text(json.dumps(auth.to_dict()))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "driver",
            "--authority-file",
            str(auth_file),
            "--claims-dir",
            str(claims),
            "--expected-driver-sha256",
            digest,
            "--execute-approved",
        ],
    )
    import subprocess

    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "")
    monkeypatch.setattr(driver, "execute_once", lambda *args, **kwargs: result)
    with pytest.raises(SystemExit) as exc_info:
        driver.main()
    assert exc_info.value.code == 1


def test_driver_qualified_success_exit_code_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(driver, "get_current_runtime_sha", lambda *args, **kwargs: driver.PINNED_RUNTIME)
    monkeypatch.setenv("ACASH_ALPACA_API_KEY_ID", "synthetic")
    monkeypatch.setenv("ACASH_ALPACA_API_SECRET", "synthetic")
    auth = authority(tmp_path)
    claims = tmp_path / "claims"
    digest = content_sha256(Path(driver.__file__).read_bytes())

    cal = NyseCa1Calendar()
    grid = cal.expected_minute_grid(date(2018, 6, 1))
    full_bars = [
        {"t": ts.isoformat(), "o": 270.0, "h": 271.0, "l": 269.0, "c": 270.5, "v": 1000}
        for ts in grid
    ]
    # Add inclusive-close bar
    full_bars.append(
        {"t": "2018-06-01T20:00:00Z", "o": 270.0, "h": 271.0, "l": 269.0, "c": 270.5, "v": 1000}
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"bars": {"SPY": full_bars}, "next_page_token": None})

    result = driver.execute_once(
        auth, claims, digest, transport=httpx.MockTransport(handler), now=NOW
    )
    assert result["local_http_invocations"] == 1
    assert result["failure_type"] is None
    assert result["retrieval_status"] == "RETRIEVED"
    assert result["qualification_status"] == "QUALIFIED"

    auth_file = tmp_path / "authority.json"
    auth_file.write_text(json.dumps(auth.to_dict()))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "driver",
            "--authority-file",
            str(auth_file),
            "--claims-dir",
            str(claims),
            "--expected-driver-sha256",
            digest,
            "--execute-approved",
        ],
    )
    import subprocess

    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "")
    monkeypatch.setattr(driver, "execute_once", lambda *args, **kwargs: result)
    # Should not raise SystemExit (or exit code 0)
    driver.main()


def test_validity_window_expiry_before_first_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(driver, "get_current_runtime_sha", lambda *args, **kwargs: driver.PINNED_RUNTIME)
    auth = authority(tmp_path)
    claims = tmp_path / "claims"
    digest = content_sha256(Path(driver.__file__).read_bytes())

    expired_clock = auth.valid_until_utc + timedelta(seconds=1)

    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail("expired authority reached HTTP")

    with pytest.raises(DataContractError, match="AUTHORITY_EXPIRED"):
        driver.execute_once(
            auth, claims, digest, transport=httpx.MockTransport(forbidden), now=expired_clock
        )
    # No reservations or HTTP calls were made
    assert not claims.exists()


def test_validity_window_expiry_between_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(driver, "get_current_runtime_sha", lambda *args, **kwargs: driver.PINNED_RUNTIME)
    monkeypatch.setenv("ACASH_ALPACA_API_KEY_ID", "synthetic")
    monkeypatch.setenv("ACASH_ALPACA_API_SECRET", "synthetic")
    auth = authority(tmp_path)
    claims = tmp_path / "claims"
    digest = content_sha256(Path(driver.__file__).read_bytes())

    # Stepped clock: valid for pre-checks and page 1 dispatch, expired right before page 2 dispatch
    valid_time = auth.valid_from_utc + timedelta(minutes=10)
    expired_time = auth.valid_until_utc + timedelta(seconds=10)
    times = [valid_time, valid_time, valid_time, valid_time, expired_time]
    clock_idx = 0

    def stepped_clock() -> datetime:
        nonlocal clock_idx
        idx = min(clock_idx, len(times) - 1)
        clock_idx += 1
        return times[idx]

    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            # Return first page with next_page_token
            bars = [
                {"t": "2018-06-01T13:30:00Z", "o": 270.0, "h": 271.0, "l": 269.0, "c": 270.5, "v": 1000}
            ]
            return httpx.Response(200, json={"bars": {"SPY": bars}, "next_page_token": "TOKEN2"})
        pytest.fail("second page should have been blocked by dispatch window check")

    result = driver.execute_once(
        auth, claims, digest, transport=httpx.MockTransport(handler), now=stepped_clock
    )
    assert calls == 1
    assert result["failure_type"] == "DataContractError"
    # Result receipt is preserved
    assert (auth.evidence_root / "single-operation-result.json").is_file()
