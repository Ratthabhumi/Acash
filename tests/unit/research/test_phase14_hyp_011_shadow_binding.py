"""Tests for HYP_011 prospective shadow Stage-B binding (calendar only)."""

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, cast

from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011.shadow import (
    derive_activation_session,
    missed_unobserved_sessions,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
BINDING = (
    REPO_ROOT
    / "docs"
    / "phase14"
    / "manifests"
    / "HYP_011_PROSPECTIVE_SHADOW_ACTIVATION_BINDING.json"
)


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_binding_matches_derivation() -> None:
    cal = NyseCa1Calendar()
    commit_ts = datetime(2026, 9, 26, 17, 39, 1, tzinfo=timezone.utc)
    assert derive_activation_session(cal, commit_ts).isoformat() == "2026-09-28"
    assert [d.isoformat() for d in missed_unobserved_sessions(cal, date(2026, 9, 28))] == [
        "2026-09-25"
    ]
    m = _load(BINDING)
    assert m["stage_a_commit_sha"] == "8ca629b44417749be345f762a624b73b880be2fc"
    assert m["stage_a_commit_timestamp_utc"] == "2026-09-26T17:39:01Z"
    assert m["scientific_prospective_boundary"] == "2026-09-25"
    assert m["missed_unobserved_sessions"] == ["2026-09-25"]
    assert m["missed_unobserved_session_count"] == 1
    assert m["missed_counted_toward_evaluation"] is False
    assert m["operational_activation_session"] == "2026-09-28"
    assert m["operational_activation_open_utc"] == "2026-09-28T13:30:00+00:00"
    assert m["prospective_price_access_at_seal"] == 0
