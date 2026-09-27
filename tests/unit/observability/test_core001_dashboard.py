"""Unit tests for the CORE-001 read-only dashboard adapter.

All fixtures are synthetic and sealed into tmp dirs only — never the real
HYP_011 data directory. Zero network. Zero market data.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import pytest

from acash.observability import core001_dashboard as dash
from acash.research.hyp_011.shadow_ops import ShadowBenchmark, ShadowPortfolio, append_observation

REAL_STATE_DIR = Path(__file__).resolve().parents[3] / "data" / "hyp_011" / "prospective"


def _seal(
    state_dir: Path,
    session: date,
    ordinal: int,
    equity: str,
    prev_sha: str | None,
    spy_equity: str = "100100.00",
) -> str:
    observation: Dict[str, Any] = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "session": session.isoformat(),
        "processed_at_utc": "2026-09-28T21:00:00+00:00",
        "authority": {"ordinal": ordinal},
        "provider": {"http_attempts": 6},
        "corporate_actions": {
            "ACWI": {"status": "CA_NOT_ECONOMICALLY_REQUIRED_NO_PRIOR_HOLDINGS"}
        },
        "scientific_status": "NON_DECISIVE_PROSPECTIVE_SHADOW_MONITORING",
        "strategy": {
            "holdings": {"ACWI": 100, "AGG": 50},
            "cash": "1000.00",
            "market_value": "99000.00",
            "receivable": "0",
            "equity": equity,
            "daily_return": "0.001",
            "drawdown": "0.0",
        },
        "benchmark": {
            "shares": 190,
            "cash": "100.00",
            "equity": spy_equity,
            "daily_return": "0.001",
            "drawdown": "0.0",
        },
    }
    return append_observation(
        state_dir, session, observation, prev_sha,
        portfolio=ShadowPortfolio(), benchmark=ShadowBenchmark(),
    )


def _seal_n(state_dir: Path, n: int) -> List[str]:
    prev: str | None = None
    shas: List[str] = []
    for i in range(n):
        session = date(2026, 9, 28) + timedelta(days=i)
        prev = _seal(state_dir, session, i + 1, str(100000 + (i + 1) * 100), prev)
        shas.append(prev)
    return shas


def _dir_bytes(root: Path) -> Dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


def test_zero_observation_pres1(tmp_path: Path) -> None:
    view = dash.build_dashboard_state(tmp_path)
    assert view["identity"]["hypothesis_id"] == "HYP_011"
    assert view["governance"]["stage"] == "PRE-S1"
    assert view["progress"]["observed_sessions"] == 0
    assert view["portfolio"]["holdings"] == {"ACWI": 0, "AGG": 0}
    assert view["portfolio"]["cash"] == "100000.00"
    assert view["performance"]["status"] == "INSUFFICIENT_OBSERVATIONS"
    assert view["s2"]["evaluation_state"] == "INSUFFICIENT_OBSERVATIONS"
    assert view["s2"]["mdd_limit"] == "0.25"
    assert view["governance"]["paper_authorized"] is False
    assert view["governance"]["live_locked"] is True
    assert view["governance"]["real_capital_authority_usd"] == "0.00"
    assert view["governance"]["no_real_orders"] is True
    assert view["runtime"]["timer_status"] == "UNAVAILABLE_FROM_DASHBOARD"


def test_one_valid_observation(tmp_path: Path) -> None:
    _seal_n(tmp_path, 1)
    view = dash.build_dashboard_state(tmp_path)
    assert view["progress"]["observed_sessions"] == 1
    assert view["governance"]["stage"] == "S1_OPERATIONAL_SANITY_IN_PROGRESS"
    assert view["evidence"]["latest_observation_ordinal"] == 1
    assert view["evidence"]["latest_observation_session"] == "2026-09-28"
    assert view["portfolio"]["total_equity"] == "100100"
    assert view["s2"]["evaluation_state"] == "INSUFFICIENT_OBSERVATIONS"
    assert view["governance"]["paper_eligible"] is False


def test_nineteen_in_progress(tmp_path: Path) -> None:
    _seal_n(tmp_path, 19)
    view = dash.build_dashboard_state(tmp_path)
    assert view["progress"]["observed_sessions"] == 19
    assert view["governance"]["stage"] == "S1_OPERATIONAL_SANITY_IN_PROGRESS"


def test_twenty_without_qualification_requires_review(tmp_path: Path) -> None:
    _seal_n(tmp_path, 20)
    view = dash.build_dashboard_state(tmp_path)
    assert view["governance"]["stage"] == "S1_REVIEW_REQUIRED"
    assert "OPERATIONALLY_SANE" not in view["governance"]["stage"]


def test_missed_sessions_never_counted(tmp_path: Path) -> None:
    # Two observed sessions with a calendar gap: count stays 2, no error.
    prev = _seal(tmp_path, date(2026, 9, 28), 1, "100100", None)
    _seal(tmp_path, date(2026, 9, 30), 2, "100200", prev)
    view = dash.build_dashboard_state(tmp_path)
    assert view["progress"]["observed_sessions"] == 2
    assert view["evidence"]["status"] != "EVIDENCE_INVALID_OR_BLOCKED"


def test_sixty_without_qualification_not_paper_eligible(tmp_path: Path) -> None:
    _seal_n(tmp_path, 60)
    view = dash.build_dashboard_state(tmp_path)
    assert view["progress"]["observed_sessions"] == 60
    assert view["governance"]["stage"] == "S2_QUALIFICATION_REVIEW_REQUIRED"
    assert view["governance"]["paper_eligible"] is False
    assert view["s2"]["evaluation_state"] == "S2_QUALIFICATION_REVIEW_REQUIRED"
    assert view["s2"]["current_mdd"] is not None
    assert view["s2"]["current_cumulative_return"] is not None
    assert view["s2"]["worst_daily_return"] is not None
    assert view["performance"]["status"] == "DIAGNOSTIC_ONLY_UNTIL_OBSERVATION_60"


def test_corrupted_evidence_blocked(tmp_path: Path) -> None:
    _seal_n(tmp_path, 2)
    (tmp_path / "observations" / "2026-09-28.json").write_text("{broken", encoding="utf-8")
    view = dash.build_dashboard_state(tmp_path)
    assert view["evidence"]["status"] == "EVIDENCE_INVALID_OR_BLOCKED"


def test_duplicate_session_blocked(tmp_path: Path) -> None:
    _seal_n(tmp_path, 1)
    src = tmp_path / "observations" / "2026-09-28.json"
    (tmp_path / "observations" / "2026-09-28-dup.json").write_bytes(src.read_bytes())
    view = dash.build_dashboard_state(tmp_path)
    assert view["evidence"]["status"] == "EVIDENCE_INVALID_OR_BLOCKED"


def test_orphan_file_count_mismatch_blocked(tmp_path: Path) -> None:
    _seal_n(tmp_path, 1)
    (tmp_path / "observations" / "2026-09-29.json").write_text("{}", encoding="utf-8")
    view = dash.build_dashboard_state(tmp_path)
    assert view["evidence"]["status"] == "EVIDENCE_INVALID_OR_BLOCKED"


def test_negative_equity_blocked(tmp_path: Path) -> None:
    _seal(tmp_path, date(2026, 9, 28), 1, "-5", None)
    view = dash.build_dashboard_state(tmp_path)
    assert view["evidence"]["status"] == "EVIDENCE_INVALID_OR_BLOCKED"


def test_unsupported_schema_blocked(tmp_path: Path) -> None:
    (tmp_path / "state.json").write_text(
        json.dumps({"schema_version": 99, "hypothesis_id": "HYP_011",
                    "observed_sessions": []}), encoding="utf-8")
    view = dash.build_dashboard_state(tmp_path)
    assert view["evidence"]["status"] == "EVIDENCE_INVALID_OR_BLOCKED"


def test_adapter_never_mutates_state_dir(tmp_path: Path) -> None:
    _seal_n(tmp_path, 3)
    before = _dir_bytes(tmp_path)
    dash.build_dashboard_state(tmp_path)
    dash.build_dashboard_state(tmp_path)
    assert _dir_bytes(tmp_path) == before


def test_observability_package_has_no_write_capability() -> None:
    module_path = Path(dash.__file__)
    assert module_path.parent.name == "observability"
    content = module_path.read_text(encoding="utf-8")
    forbidden = ["write_text", "write_bytes", "mkdir", "rename", "unlink",
                 "rmdir", "chmod", "subprocess", "socket", "urllib", "requests",
                 "httpx", "urlopen", "fetch(", "Alpaca", "credential",
                 "systemctl", "commit", "push"]
    for token in forbidden:
        assert token not in content, f"write/network capability token: {token}"
    assert "read_text" in content


def test_benchmark_return_uses_starting_aum(tmp_path: Path) -> None:
    # Frozen semantics: benchmark prev_equity starts at $100,000, so the
    # Observation #1 sealed equity already embeds entry friction. Cumulative
    # return must be latest/100000 - 1, NOT latest/first - 1.
    _seal(tmp_path, date(2026, 9, 28), 1, "100100", None, spy_equity="99900.00")
    view = dash.build_dashboard_state(tmp_path)
    assert view["benchmark"]["return_since_entry"] == str(
        Decimal("99900.00") / Decimal("100000") - Decimal("1")
    )


def test_benchmark_return_multi_observation(tmp_path: Path) -> None:
    prev = _seal(tmp_path, date(2026, 9, 28), 1, "100100", None, spy_equity="99900.00")
    _seal(tmp_path, date(2026, 9, 29), 2, "100200", prev, spy_equity="101000.00")
    view = dash.build_dashboard_state(tmp_path)
    assert view["benchmark"]["return_since_entry"] == str(
        Decimal("101000.00") / Decimal("100000") - Decimal("1")
    )
    assert view["benchmark"]["return_since_entry"] != str(
        Decimal("101000.00") / Decimal("99900.00") - Decimal("1")
    )


def test_real_prospective_dir_never_mutated_by_adapter() -> None:
    # Durable past Observation #0001: the canonical directory MAY contain
    # sealed observations. The invariant is non-mutation, never emptiness.
    if not REAL_STATE_DIR.is_dir():
        pytest.skip("no canonical prospective directory in this checkout")
    before = _dir_bytes(REAL_STATE_DIR)
    view = dash.build_dashboard_state(REAL_STATE_DIR)
    after = _dir_bytes(REAL_STATE_DIR)
    assert before == after
    assert view["identity"]["hypothesis_id"] == "HYP_011"
    assert view["governance"]["paper_authorized"] is False
    assert view["governance"]["live_locked"] is True
