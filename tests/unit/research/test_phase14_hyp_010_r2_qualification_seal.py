"""Seal tests for HYP_010 R2 provider + sponsor qualification outcome.

SPY/BIL/AGG PASS from sealed authorities; VEU blocked (structure only — the
block itself is the absence of authority). Prospective derived calendar-only.
No network.
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


def test_sealed_spy_composite_36() -> None:
    mec15 = _load(REPO_ROOT / "docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json")
    supp = _load(REPO_ROOT / "docs/research/manifests/HYP_009_SPY_2024_DIVIDEND_AUTHORITY_SUPPLEMENT.json")
    recs = parse_sponsor_records(
        "SPY",
        [{"ex_date": d["ex_date"], "cash_distribution": d["cash_distribution"],
          "payable_date": d["payable_date"]} for d in mec15["distributions"]]
        + [{"ex_date": d["ex_date"], "cash_distribution": d["cash_distribution"],
            "payable_date": d["payable_date"]} for d in supp["distributions"]],
        "SEALED_COMPOSITE",
        "STATE_STREET_SPDR_OFFICIAL",
    )
    qual = qualify_sponsor_authority("SPY", "STATE_STREET_SPDR_OFFICIAL", recs)
    assert qual.classification == "SPY_DIVIDEND_AUTHORITY_QUALIFIED"
    assert qual.records_count == 36


def test_sealed_bil_108_affirmed_zeros() -> None:
    manifest = _load(
        REPO_ROOT / "docs/research/manifests/HYP_010_BIL_SSGA_DIVIDEND_AUTHORITY.json"
    )
    assert manifest["record_count"] == 108
    recs = parse_sponsor_records(
        "BIL",
        [{"ex_date": d["ex_date"], "cash_distribution": d["cash_distribution"],
          "payable_date": d["payable_date"]} for d in manifest["distributions"]],
        "SSGA_OFFICIAL_WORKBOOK",
        "STATE_STREET_SPDR_OFFICIAL",
    )
    qual = qualify_sponsor_authority("BIL", "STATE_STREET_SPDR_OFFICIAL", recs)
    assert qual.classification == "BIL_DIVIDEND_AUTHORITY_QUALIFIED"
    assert sum(1 for r in recs if r.affirmed_zero) == 33


def test_sealed_agg_108_feb_dec_schedule() -> None:
    manifest = _load(
        REPO_ROOT / "docs/research/manifests/HYP_010_AGG_ISHARES_DIVIDEND_AUTHORITY.json"
    )
    assert manifest["record_count"] == 108
    recs = parse_sponsor_records(
        "AGG",
        [{"ex_date": d["ex_date"], "cash_distribution": d["cash_distribution"],
          "payable_date": d["payable_date"]} for d in manifest["distributions"]],
        "ISHARES_OFFICIAL_PAGE",
        "BLACKROCK_ISHARES_OFFICIAL",
    )
    qual = qualify_sponsor_authority("AGG", "BLACKROCK_ISHARES_OFFICIAL", recs)
    assert qual.classification == "AGG_DIVIDEND_AUTHORITY_QUALIFIED"


def test_veu_block_structure() -> None:
    qual = qualify_sponsor_authority("VEU", "VANGUARD_OFFICIAL", [])
    assert qual.classification == "BLOCKED_VEU_DIVIDEND_AUTHORITY_NO_RECORDS"
    summary = _load(
        REPO_ROOT / "docs/phase14/manifests/HYP_010_R2_QUALIFICATION_SUMMARY.json"
    )
    assert summary["overall_classification"] == (
        "R2_PROVIDER_QUALIFIED_SPONSOR_AUTHORITY_BLOCKED"
    )


def test_prospective_calendar_only_derivation() -> None:
    cal = NyseCa1Calendar()
    commit_ts = datetime(2026, 9, 24, 20, 0, 10, tzinfo=timezone.utc)
    assert cal.is_trading_session(date(2026, 9, 24)) is True
    session = cal.get_session(date(2026, 9, 25))
    assert session.open_utc == datetime(2026, 9, 25, 13, 30, tzinfo=timezone.utc)
    assert session.open_utc > commit_ts
    assert str(session.session_type) == "SessionType.REGULAR"
    summary = _load(
        REPO_ROOT / "docs/phase14/manifests/HYP_010_R2_QUALIFICATION_SUMMARY.json"
    )
    assert summary["prospective_start_session"] == "2026-09-25"
    assert summary["prospective_price_access"] == 0


def test_qualification_manifests_present_and_locked() -> None:
    prov = _load(REPO_ROOT / "docs/phase14/manifests/HYP_010_R2_PROVIDER_QUALIFICATION.json")
    assert prov["classification"] == "PROVIDER_PROBE_PASS"
    assert prov["http_attempts"] == 8
    spon = _load(REPO_ROOT / "docs/phase14/manifests/HYP_010_R2_SPONSOR_AUTHORITY_QUALIFICATION.json")
    assert spon["symbols"]["VEU"]["classification"].startswith("BLOCKED_VEU")
    assert spon["unofficial_sources_used"] is False
    assert spon["d_zero_inferred_anywhere"] is False
    assert spon["overall_r2_classification"] == "R2_PROVIDER_QUALIFIED_SPONSOR_AUTHORITY_BLOCKED"
