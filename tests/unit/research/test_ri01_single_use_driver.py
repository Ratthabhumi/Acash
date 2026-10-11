"""Cross-client/identity/root replay attempts must not invoke HTTP again."""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.evidence import content_sha256
from acash.research.ri01.probe import RI01ProbeAuthority
from scripts import ri01_canary_single_use as driver

NOW = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)


def authority(tmp_path: Path) -> RI01ProbeAuthority:
    root = tmp_path / "canary"
    root.mkdir()
    return RI01ProbeAuthority(
        authority_id="AUTHORIZE_RI01_PROBE_R1_CANARY2_TEST", runtime_sha=driver.PINNED_RUNTIME,
        session=date(2018, 6, 1), capability="bars", evidence_root=root, max_requests=3,
        valid_from_utc=datetime(2026, 10, 11, 11, tzinfo=timezone.utc),
        valid_until_utc=datetime(2026, 10, 11, 13, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize("replay", ["same", "identity_new_root", "new_identity_same_root"])
def test_cross_client_replay_zero_additional_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replay: str) -> None:
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
    result = driver.execute_once(auth, tmp_path / "claims", digest, transport=httpx.MockTransport(handler), now=NOW)
    assert result["local_http_invocations"] == count == 1
    replay_auth = auth
    if replay == "identity_new_root":
        other = tmp_path / "other"
        other.mkdir()
        replay_auth = replace(auth, evidence_root=other, valid_until_utc=datetime(2026, 10, 11, 14, tzinfo=timezone.utc))
    elif replay == "new_identity_same_root":
        replay_auth = replace(auth, authority_id="AUTHORIZE_RI01_PROBE_R1_CANARY2_OTHER")
    with pytest.raises(DataContractError):
        driver.execute_once(replay_auth, tmp_path / "claims", digest, transport=httpx.MockTransport(handler), now=NOW)
    assert count == 1


def test_partial_claim_and_wrong_driver_fail_before_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(driver, "get_current_runtime_sha", lambda: driver.PINNED_RUNTIME)
    auth = authority(tmp_path)
    digest = content_sha256(Path(driver.__file__).read_bytes())
    claims = tmp_path / "claims"
    claims.mkdir()
    # Simulate crash after the identity claim; no evidence pages exist yet.
    (claims / f"authority-id-{content_sha256(auth.authority_id)}.json").write_text(json.dumps({"reserved": True}))

    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail("reserved authority reached HTTP")

    with pytest.raises(DataContractError):
        driver.execute_once(auth, claims, digest, transport=httpx.MockTransport(forbidden), now=NOW)
    with pytest.raises(DataContractError, match="DRIVER_HASH_MISMATCH"):
        driver.execute_once(auth, claims, "0" * 64, transport=httpx.MockTransport(forbidden), now=NOW)


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
