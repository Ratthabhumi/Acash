"""Owner-declared external cash and broker-displayed observations (synthetic, never Owner data)."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.dashboard_api import private_view_server as srv
from acash.invest import broker_observation as bo
from acash.invest import external_cash as ec
from acash.ppds import private_observation as po

CASH_DOC: Dict[str, Any] = {
    "schema": ec.SCHEMA, "data_class": ec.DATA_CLASS,
    "target": {"amount": "30000.00", "currency": "THB", "evidence_type": "OWNER_EXTERNAL_CASH_TARGET"},
    "accounts": [
        {"account_ref": "EXT_MAKE", "institution": "Make", "owner_label": "Make", "balance": "13000.00",
         "currency": "THB", "precision": "EXACT", "evidence_type": "OWNER_DECLARED",
         "liquidity_status": "WITHDRAWABLE", "reserve_eligible": True, "reserve_designated": True, "inclusion_scope": "WEALTH_ONLY",
         "observed_at": "2026-11-04T00:00:00+07:00", "effective_date": "2026-11-04"},
        {"account_ref": "EXT_LHB", "institution": "LHB", "owner_label": "LHB", "balance": "8000.00",
         "currency": "THB", "precision": "EXACT", "evidence_type": "OWNER_DECLARED",
         "liquidity_status": "WITHDRAWABLE", "reserve_eligible": True, "reserve_designated": True, "inclusion_scope": "WEALTH_ONLY",
         "observed_at": "2026-11-04T00:00:00+07:00", "effective_date": "2026-11-04"},
        {"account_ref": "EXT_KBANK", "institution": "KBank", "owner_label": "KBank", "balance": "2000.00",
         "currency": "THB", "precision": "APPROXIMATE", "evidence_type": "OWNER_ESTIMATE",
         "liquidity_status": "SPENDING", "reserve_eligible": False, "reserve_designated": False, "inclusion_scope": "WEALTH_ONLY",
         "observed_at": "2026-11-04T00:00:00+07:00", "effective_date": "2026-11-04"},
    ],
}

OBS: Dict[str, Any] = {
    "observation_id": "DIME_TEST", "broker": "DIME", "observed_at": "2026-11-04T02:43:00+07:00",
    "currency": "THB",
    "categories": {"us_equities": "175666.08", "cash": "26977.79", "mutual_fund": "103.43",
                   "gold": "79.22", "thai_equities": "0.00"},
    "displayed_total": "202826.52", "source": "SCREENSHOT", "evidence_status": bo.EVIDENCE,
}


def _write(tmp_path: Path, name: str, doc: Dict[str, Any]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _cash(tmp_path: Path) -> ec.ExternalCash:
    return ec.load_external_cash(_write(tmp_path, "cash.json", CASH_DOC))


def test_totals_target_and_gap_are_three_distinct_numbers(tmp_path: Path) -> None:
    cash = _cash(tmp_path)
    summary = ec.summary(cash)
    assert summary["total"] == "23000.00" and summary["target"] == "30000.00" and summary["gap"] == "7000.00"
    assert summary["approximate_component"] == "2000.00"
    assert summary["reserve_eligible_total"] == "21000.00"
    assert summary["designated_reserve_total"] == "21000.00"
    assert "OWNER_TARGET_IS_NOT_THE_EXPENSE_DERIVED_RESERVE_REQUIREMENT" in summary["notes"]
    assert "EXTERNAL_CASH_IS_NOT_BROKER_CASH" in summary["notes"]


def test_external_cash_never_enters_the_broker_scope(tmp_path: Path) -> None:
    cash = _cash(tmp_path)
    merged = ec.consolidated(Decimal("202826.52"), datetime(2026, 11, 4, 2, 43, tzinfo=timezone.utc), cash)
    assert merged["consolidated_total"] == "225826.52"
    assert merged["evidence_quality"] == "MIXED_EVIDENCE_MIXED_TIME"
    assert merged["broker_total"] == "202826.52"          # broker stays separate and unchanged
    assert "never enters broker NAV" in merged["note"]


def test_declared_versus_estimated_precision_is_enforced(tmp_path: Path) -> None:
    doc = json.loads(json.dumps(CASH_DOC))
    doc["accounts"][0]["precision"] = "APPROXIMATE"       # a declaration must stay exact
    with pytest.raises(DataContractError, match="EXTERNAL_CASH_INVALID"):
        ec.load_external_cash(_write(tmp_path, "bad.json", doc))
    doc = json.loads(json.dumps(CASH_DOC))
    doc["accounts"].append(dict(doc["accounts"][0]))      # duplicate account_ref
    with pytest.raises(DataContractError, match="EXTERNAL_CASH_DUPLICATE_ACCOUNT"):
        ec.load_external_cash(_write(tmp_path, "dup.json", doc))


def test_broker_observation_arithmetic_and_append_only(tmp_path: Path) -> None:
    path = tmp_path / "obs.json"
    observation = bo.parse_observation(OBS)
    assert bo.record(path, observation) == "RECORDED"
    assert bo.record(path, observation) == "ALREADY_RECORDED"
    duplicate = bo.BrokerObservation(**{**observation.__dict__, "observation_id": "OTHER"})
    with pytest.raises(DataContractError, match="BROKER_OBSERVATION_DUPLICATE_TIMESTAMP"):
        bo.record(path, duplicate)
    latest = bo.latest(path)
    assert latest is not None and latest.displayed_total == Decimal("202826.52")

    broken = json.loads(json.dumps(OBS))
    broken["displayed_total"] = "202000.00"
    with pytest.raises(DataContractError, match="BROKER_OBSERVATION_ARITHMETIC_MISMATCH"):
        bo.parse_observation(broken)


def test_comparison_requires_aligned_timestamps_not_just_the_same_date() -> None:
    observation = bo.parse_observation(OBS)          # 2026-11-04 02:43 +07:00 == 2026-11-03 19:43Z
    same_time = bo.compare(observation, Decimal("202826.52"), datetime(2026, 11, 3, 19, 45, tzinfo=timezone.utc))
    assert same_time["status"] == "SAME_TIME_COMPARABLE" and same_time["difference"] == "0.00"
    # Same UTC day, eight hours apart: the old date-only rule would have accepted this.
    same_date = bo.compare(observation, Decimal("202826.52"), datetime(2026, 11, 3, 11, 43, tzinfo=timezone.utc))
    assert same_date["status"] == "SAME_DATE_TIME_UNALIGNED"
    assert same_date["alignment_tolerance_minutes"] == 5
    cross = bo.compare(observation, Decimal("208740.01"), datetime(2026, 11, 2, 22, 41, tzinfo=timezone.utc))
    assert cross["status"] == "CROSS_DATE_TIME_MISALIGNED" and cross["difference"] == "-5913.49"
    assert "not proof of a missing transaction" in cross["note"]
    assert bo.compare(observation, Decimal("1"), None)["status"] == "INSUFFICIENT_TIME_EVIDENCE"
    assert bo.compare(observation, None, None)["status"] == "CALCULATED_VALUE_UNAVAILABLE"


def test_wealth_endpoint_labels_mixed_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "data" / "private").mkdir(parents=True)
    (tmp_path / "data" / "private" / "external_accounts.json").write_text(json.dumps(CASH_DOC), encoding="utf-8")
    (tmp_path / "data" / "private" / "broker_observations.json").write_text(
        json.dumps({"schema": bo.SCHEMA, "data_class": bo.DATA_CLASS, "observations": [OBS]}), encoding="utf-8")
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)

    view = {"portfolio_overview": {"computed_nav_ppds": "208740.01"},
            "report_metadata": {"valuation_date": "2026-11-02",
                                "observed_at": "2026-11-02T22:41:00+07:00"}}
    monkeypatch.setattr(srv, "load_view", lambda _p: ("READY", None, view))
    payload = srv._wealth_payload(tmp_path / "unused.json")
    assert payload["external_cash"]["total"] == "23000.00"
    assert payload["comparison"]["status"] == "CROSS_DATE_TIME_MISALIGNED"
    assert payload["consolidated"]["evidence_quality"] == "MIXED_EVIDENCE_MIXED_TIME"
    assert payload["consolidated"]["consolidated_total"] == "225826.52"


def test_missing_private_files_degrade_without_figures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(po, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(srv, "load_view", lambda _p: ("NO_REPORT", None, None))
    payload = srv._wealth_payload(tmp_path / "unused.json")
    assert payload["external_cash"]["status"] == "NO_EXTERNAL_CASH"
    assert "consolidated" not in payload


def test_cash_breakdown_keeps_the_residual_unexplained() -> None:
    """Visible accounts explain the broker cash total only partially; the gap is not a new account."""
    total = Decimal("26977.79")
    components = [
        bo.CashComponent("DIME_FCD", "USD", Decimal("800.04"), Decimal("26945.34")),
        bo.CashComponent("DIME_SAVE", "THB", Decimal("0.44"), Decimal("0.44")),
        bo.CashComponent("DIME_USD", "USD", Decimal("0.00"), Decimal("0.00")),
    ]
    result = bo.cash_breakdown(total, components)
    assert result["status"] == "UNEXPLAINED_RESIDUAL"
    assert result["explained_total"] == "26945.78"
    assert result["residual"] == "32.01"
    assert "not a new cash account" in result["note"]
    assert [c["account_ref"] for c in result["components"]] == ["DIME_FCD", "DIME_SAVE", "DIME_USD"]

    exact = bo.cash_breakdown(Decimal("26945.78"), components[:2])
    assert exact["status"] == "EXPLAINED" and exact["residual"] == "0.00"
    partial = bo.cash_breakdown(total, [bo.CashComponent("DIME_FCD", "USD", Decimal("800.04"))])
    assert partial["status"] == "PARTIAL_COMPONENTS_NOT_VALUED" and partial["components_not_valued"] == ["DIME_FCD"]


def test_residual_is_not_an_asset_unless_same_time_and_complete() -> None:
    """The 23,797.75 gap must be classified, not silently promoted to holdings value."""
    from decimal import Decimal as D

    assert bo.classify_residual(D("23797.75"), same_time=False, components_complete=True)[
        "classification"] == "TIME_OR_SCOPE_MISALIGNED_DIFFERENCE"
    assert bo.classify_residual(D("23797.75"), same_time=True, components_complete=False)[
        "classification"] == "INCOMPLETE_ACCOUNT_COMPONENTS"
    assert bo.classify_residual(D("23797.75"), same_time=True, components_complete=True)[
        "classification"] == "QUALIFIED_UNIDENTIFIED_ASSET"
    assert bo.classify_residual(D("-1"), same_time=True, components_complete=True)[
        "classification"] == "UNEXPLAINED_NEGATIVE_DIFFERENCE"
    assert bo.classify_residual(D("0"), same_time=True, components_complete=True)[
        "classification"] == "NO_RESIDUAL"


def test_classification_registry_requires_evidence_and_reports_partial_coverage(tmp_path: Path) -> None:
    from acash.invest import economic_classification as ec

    doc: Dict[str, Any] = {"schema": ec.SCHEMA, "data_class": ec.DATA_CLASS, "classifications": [
        {"security_id": "VOO", "instrument_type": "ETF", "economic_asset_class": "EQUITY",
         "methodology": "ISSUER_FUND_OBJECTIVE", "evidence_ref": "issuer page",
         "effective_date": "2026-11-04", "verification_status": "ISSUER_EVIDENCE"},
        {"security_id": "NASA", "instrument_type": "ETF", "economic_asset_class": "UNKNOWN",
         "methodology": "NOT_CLASSIFIED", "evidence_ref": "",
         "effective_date": "2026-11-04", "verification_status": "UNKNOWN"}]}
    path = tmp_path / "classification.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    registry = ec.load_registry(path)
    result = ec.coverage(registry, {"VOO": Decimal("100"), "NASA": Decimal("50")})
    assert result["classified_count"] == 1 and result["unknown_count"] == 1
    assert Decimal(result["coverage_by_count"]) == Decimal("0.5")
    assert result["by_class"] == {"EQUITY": "100"}

    doc["classifications"][0]["evidence_ref"] = ""      # an economic class needs evidence
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(DataContractError, match="CLASSIFICATION_EVIDENCE_REQUIRED"):
        ec.load_registry(path)


def test_identity_status_distinguishes_missing_venue_without_fabricating_it() -> None:
    from acash.ppds.private_observation import SecurityClass

    def build(**kw: Any) -> SecurityClass:
        base = {"security_id": "VOO", "classification": "UNKNOWN", "methodology": "NOT_CLASSIFIED",
                "evidence_ref": None, "instrument_type": "ETF", "exchange_mic": None,
                "isin": None, "figi": None, "trading_currency": None}
        return SecurityClass(**{**base, **kw})

    assert build(figi="BBG000BLNNH6").identity_status == "IDENTITY_MAPPED_VENUE_UNVERIFIED"
    assert build(figi="BBG000BLNNH6", exchange_mic="ARCX").identity_status == "IDENTITY_MAPPED_OWNER_SUPPLIED"
    assert build().identity_status == "SECURITY_IDENTITY_UNVERIFIED"
    assert build(instrument_type=None, figi="BBG000BLNNH6").identity_status == "SECURITY_IDENTITY_UNVERIFIED"
