"""Seal tests for HYP_011 R2 provider + sponsor qualification outcome.

Provider PASS + all three sponsors PASS from sealed/official authorities.
Prospective derived calendar-only. No network.
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, cast

from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.hyp_010_sponsor_authority import (
    parse_sponsor_records,
    qualify_sponsor_authority,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_provider_manifest_pass() -> None:
    m = _load(REPO_ROOT / "docs/phase14/manifests/HYP_011_R2_PROVIDER_QUALIFICATION.json")
    assert m["classification"] == "PROVIDER_PROBE_PASS"
    assert m["http_attempts"] == 6
    for symbol in ("ACWI", "AGG", "SPY"):
        assert m["results"][symbol]["split_rows"] == 4
        assert m["results"][symbol]["raw_rows"] == 4
        assert m["results"][symbol]["alignment"] == "PASS"


def test_sealed_sponsor_qualifications() -> None:
    mec15 = _load(REPO_ROOT / "docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json")
    supp = _load(REPO_ROOT / "docs/research/manifests/HYP_009_SPY_2024_DIVIDEND_AUTHORITY_SUPPLEMENT.json")
    spy = parse_sponsor_records(
        "SPY",
        [{"ex_date": d["ex_date"], "cash_distribution": d["cash_distribution"],
          "payable_date": d["payable_date"]} for d in mec15["distributions"]]
        + [{"ex_date": d["ex_date"], "cash_distribution": d["cash_distribution"],
            "payable_date": d["payable_date"]} for d in supp["distributions"]],
        "SEALED_COMPOSITE", "STATE_STREET_SPDR_OFFICIAL",
    )
    assert qualify_sponsor_authority("SPY", "STATE_STREET_SPDR_OFFICIAL", spy).classification == (
        "SPY_DIVIDEND_AUTHORITY_QUALIFIED"
    )
    agg = _load(REPO_ROOT / "docs/research/manifests/HYP_010_AGG_ISHARES_DIVIDEND_AUTHORITY.json")
    ag = parse_sponsor_records(
        "AGG",
        [{"ex_date": d["ex_date"], "cash_distribution": d["cash_distribution"],
          "payable_date": d["payable_date"]} for d in agg["distributions"]],
        "SEALED", "BLACKROCK_ISHARES_OFFICIAL",
    )
    assert qualify_sponsor_authority("AGG", "BLACKROCK_ISHARES_OFFICIAL", ag).classification == (
        "AGG_DIVIDEND_AUTHORITY_QUALIFIED"
    )
    acwi = _load(REPO_ROOT / "docs/research/manifests/HYP_011_ACWI_ISHARES_DIVIDEND_AUTHORITY.json")
    assert acwi["record_count"] == 20
    ac = parse_sponsor_records(
        "ACWI",
        [{"ex_date": d["ex_date"], "cash_distribution": d["cash_distribution"],
          "payable_date": d["payable_date"]} for d in acwi["distributions"]],
        "ISHARES_OFFICIAL_PAGE", "BLACKROCK_ISHARES_OFFICIAL",
    )
    qual = qualify_sponsor_authority("ACWI", "BLACKROCK_ISHARES_OFFICIAL", ac)
    assert qual.classification == "ACWI_DIVIDEND_AUTHORITY_QUALIFIED"


def test_sponsor_manifest_overall_pass() -> None:
    m = _load(REPO_ROOT / "docs/phase14/manifests/HYP_011_R2_SPONSOR_AUTHORITY_QUALIFICATION.json")
    assert m["symbols"]["SPY"]["classification"] == "SPY_DIVIDEND_AUTHORITY_QUALIFIED"
    assert m["symbols"]["AGG"]["classification"] == "AGG_DIVIDEND_AUTHORITY_QUALIFIED"
    assert m["symbols"]["ACWI"]["classification"] == "ACWI_DIVIDEND_AUTHORITY_QUALIFIED"
    assert m["unofficial_sources_used"] is False
    assert m["d_zero_inferred_anywhere"] is False
    assert m["overall_r2_classification"] == (
        "R2_PROVIDER_AND_SPONSOR_AUTHORITIES_QUALIFIED_HISTORICAL_BUILD_NOT_EXECUTED"
    )


def test_prospective_calendar_only_from_actual_r1_ts() -> None:
    cal = NyseCa1Calendar()
    commit_ts = datetime(2026, 9, 24, 22, 34, 44, tzinfo=timezone.utc)
    session = cal.get_session(date(2026, 9, 25))
    assert session.open_utc == datetime(2026, 9, 25, 13, 30, tzinfo=timezone.utc)
    assert session.open_utc > commit_ts
    assert str(session.session_type) == "SessionType.REGULAR"
    summary = _load(REPO_ROOT / "docs/phase14/manifests/HYP_011_R2_QUALIFICATION_SUMMARY.json")
    assert summary["prospective_start_session"] == "2026-09-25"
    assert summary["prospective_price_access"] == 0
    assert summary["overall_classification"] == (
        "R2_PROVIDER_AND_SPONSOR_AUTHORITIES_QUALIFIED_HISTORICAL_BUILD_NOT_EXECUTED"
    )
