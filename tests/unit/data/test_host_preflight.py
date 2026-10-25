"""Offline host preflight: observations only, never a durability certification."""

from __future__ import annotations

from pathlib import Path

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.host_preflight import run_offline_host_preflight


def test_preflight_reports_limitations_without_reading_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APCA_API_SECRET_KEY", "super-secret-value")
    report = run_offline_host_preflight(tmp_path, required_free_bytes=8_388_608)
    assert report["ready_for_real_acquisition"] is False
    assert report["clock_trusted_timestamp"] is False
    assert report["durability"] == {
        "PROCESS_CRASH": "CREATE_ONCE_AND_FSYNC_ATTEMPTED_NOT_TESTED_UNDER_KILL",
        "OS_CRASH": "UNPROVEN",
        "POWER_LOSS": "UNPROVEN",
    }
    assert "APCA_API_SECRET_KEY" in report["credential_env_names_present"]
    assert "super-secret-value" not in repr(report)
    assert list((tmp_path / "preflight_probe").iterdir()) == []


def test_preflight_flags_insufficient_storage(tmp_path: Path) -> None:
    report = run_offline_host_preflight(tmp_path, required_free_bytes=10**18)
    assert report["storage_sufficient"] is False


@pytest.mark.parametrize("required", [0, -1, True])
def test_preflight_rejects_bad_requirement(tmp_path: Path, required: int) -> None:
    with pytest.raises(DataContractError, match="PREFLIGHT_BAD_REQUIRED_BYTES"):
        run_offline_host_preflight(tmp_path, required_free_bytes=required)


def test_preflight_rejects_repository_root() -> None:
    with pytest.raises(DataContractError):
        run_offline_host_preflight(Path(__file__).resolve().parent, required_free_bytes=1)


def test_preflight_rejects_missing_root(tmp_path: Path) -> None:
    with pytest.raises(DataContractError):
        run_offline_host_preflight(tmp_path / "missing", required_free_bytes=1)
