from __future__ import annotations

import copy
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.invest import market_authority as ma
from acash.invest import market_valuation as mv
from acash.ppds import private_observation as po

FIXTURE = Path("docs/research/evidence/upi_v1_2_synthetic_snapshot.json")
DAY = date(2026, 11, 4)
NOW = datetime(2026, 11, 5, 2, 0, tzinfo=timezone.utc)


def _doc() -> Dict[str, Any]:
    doc: Dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for account in doc["accounts"]:
        account["positions"] = [p for p in account.get("positions") or [] if p.get("quantity") is not None]
    doc["accounts"] = [a for a in doc["accounts"] if a["positions"] or a.get("cash")]
    held = {p["security_id"] for a in doc["accounts"] for p in a["positions"]}
    doc["prices"] = [p for p in doc["prices"] if p["security_id"] in held]
    doc["securities"] = [s for s in doc["securities"] if s["security_id"] in held]
    return doc


def _held(doc: Dict[str, Any]) -> Dict[str, str]:
    return {p["security_id"]: p["currency"] for p in doc["prices"]}


def _obs(sid: str, ccy: str, price: str = "10.00", provider: str = "SYN_A", day: date = DAY,
         price_type: str = "EOD_CLOSE", retrieved: datetime = NOW, stamp: Optional[datetime] = None) -> mv.PriceObservation:
    return mv.PriceObservation(sid, provider, sid, ccy, Decimal(price), price_type, day, retrieved, market_timestamp=stamp)


def _fx(day: date = DAY, kind: str = "REFERENCE_FX", back: str = "0.030303") -> List[mv.FXObservation]:
    return [mv.FXObservation("USD", "THB", Decimal("33.00"), day, kind, "SYN_FX", NOW),
            mv.FXObservation("THB", "USD", Decimal(back), day, kind, "SYN_FX", NOW)]


POLICY = mv.QuotePolicy(as_of=DAY, max_age_days=3, price_types=("EOD_CLOSE",), now=NOW)


@pytest.mark.parametrize("record, capability, state", [
    ("ODR_UPI_MARKET_DATA_004.json", "OWNER_MARKET_DATA_RETRIEVAL_AUTHORIZED", "RATIFIED"),
    ("ODR_UPI_LOCAL_TRANSACTION_AUTHORING_005.json", "OWNER_LOCAL_TRANSACTION_AUTHORING_AUTHORIZED", "RATIFIED"),
])
def test_new_capability_states_and_scope(record: str, capability: str, state: str) -> None:
    path = Path("docs/governance") / record
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert po.odr_state(path, None, capability) == state
    assert {"TRADING_AUTHORIZED", "BROKER_ACCOUNT_CONNECTIVITY", "CAPITAL_TRANSFER"} <= set(doc["independent_of"])
    if capability == "OWNER_MARKET_DATA_RETRIEVAL_AUTHORIZED":
        assert {e["provider_id"] for e in doc["scope_providers"]} == {
            "ALPACA_BASIC", "ALPACA_HISTORICAL", "MARKETDATA_APP_FREE", "FRANKFURTER_ECB_FX"}
        for entry in doc["scope_providers"]:
            for k in ma.ATTESTATIONS:
                assert entry[k] in (False, None), (entry["provider_id"], k)
        lineage = doc["ratification_lineage"]
        assert lineage["decided_by"] == "OWNER" and lineage["scope_changed"] is False  # original history intact
        assert "ODR_UPI_MARKET_DATA_004_AMENDMENT_001" in doc.get("amendments", [])
        assert (Path(".") / lineage["acceptance_evidence"]).is_file()


def test_market_valuation_has_no_network_client() -> None:
    source = Path(mv.__file__).read_text(encoding="utf-8")
    assert not any(f"import {m}" in source for m in ("socket", "urllib", "requests", "httpx", "http.client", "aiohttp"))


def test_candidate_providers_are_disabled_until_verified() -> None:
    matrix = mv.provider_matrix()
    assert {m["provider_id"] for m in matrix} == {"WEBULL_TH_OPENAPI", "ALPACA_BASIC", "MASSIVE_BASIC", "BOT_REFERENCE_FX"}
    assert all(m["status"] == "NOT_ENABLED_UNVERIFIED" for m in matrix)
    with pytest.raises(DataContractError, match="PROVIDER_NOT_ENABLED"):
        mv.CANDIDATE_PROVIDERS[0].latest_prices(["X"], DAY)
    partial = mv.ProviderCapabilities("P", ("EOD_CLOSE",), "UNKNOWN", True, True, None)
    denied = mv.ProviderCapabilities("P", ("EOD_CLOSE",), "UNKNOWN", True, False, True)
    assert (partial.status, denied.status) == ("NOT_ENABLED_UNVERIFIED", "NOT_PERMITTED")


def test_selection_falls_back_in_priority_order_and_never_averages() -> None:
    primary = mv.SyntheticProvider("SYN_A", [_obs("AAA", "USD", "10.00")], ("EOD_CLOSE",))
    fallback = mv.SyntheticProvider("SYN_B", [_obs("AAA", "USD", "99.00", "SYN_B"), _obs("BBB", "USD", "20.00", "SYN_B")],
                                    ("EOD_CLOSE",))
    disabled = mv.CANDIDATE_PROVIDERS[0]
    out = mv.select_quotes(["BBB", "AAA", "CCC"], [disabled, primary, fallback], POLICY)
    assert out["selected"]["AAA"].price == Decimal("10.00") and out["selected"]["BBB"].provider_id == "SYN_B"
    assert fallback.calls == [("BBB", "CCC")] and out["unpriced"] == ["CCC"]
    assert out["provider_statuses"] == {"WEBULL_TH_OPENAPI": "NOT_ENABLED_UNVERIFIED", "SYN_A": "QUERIED", "SYN_B": "QUERIED"}


def test_provider_failure_is_reported_not_masked() -> None:
    broken = mv.SyntheticProvider("SYN_A", [], ("EOD_CLOSE",), failure="PROVIDER_RATE_LIMITED")
    backup = mv.SyntheticProvider("SYN_B", [_obs("AAA", "USD", provider="SYN_B")], ("EOD_CLOSE",))
    out = mv.select_quotes(["AAA"], [broken, backup], POLICY)
    assert out["provider_statuses"]["SYN_A"] == "PROVIDER_RATE_LIMITED" and out["selected"]["AAA"].provider_id == "SYN_B"


@pytest.mark.parametrize("obs, reason", [
    (_obs("AAA", "USD", "0"), "PRICE_NONPOSITIVE"),
    (_obs("AAA", "USD", "NaN"), "PRICE_NONPOSITIVE"),
    (_obs("AAA", "usd"), "CURRENCY_INVALID"),
    (_obs("AAA", "USD", price_type="LAST_TRADE"), "PRICE_TYPE_NOT_REQUESTED"),
    (_obs("AAA", "USD", price_type="MIDPOINT"), "OBSERVATION_TYPE_INVALID"),
    (_obs("AAA", "USD", retrieved=NOW.replace(tzinfo=None)), "TIMESTAMP_NOT_TIMEZONE_AWARE"),
    (_obs("AAA", "USD", retrieved=NOW + timedelta(hours=1)), "FUTURE_TIMESTAMP"),
    (_obs("AAA", "USD", stamp=NOW + timedelta(minutes=1)), "FUTURE_TIMESTAMP"),
    (_obs("AAA", "USD", day=DAY + timedelta(days=1), retrieved=NOW), "AFTER_VALUATION_DATE"),
    (_obs("AAA", "USD", day=DAY - timedelta(days=4)), "STALE_PRICE"),
    (_obs("AAA", "USD", provider="SYN_OTHER"), "UNREQUESTED_OR_MISATTRIBUTED"),
])
def test_ineligible_observations_are_rejected_with_a_reason(obs: mv.PriceObservation, reason: str) -> None:
    out = mv.select_quotes(["AAA"], [mv.SyntheticProvider("SYN_A", [obs], ("EOD_CLOSE",))], POLICY)
    assert out["selected"] == {} and out["unpriced"] == ["AAA"]
    assert out["rejected"] == [{"security_id": "AAA", "provider_id": "SYN_A", "reason": reason}]


def test_latest_date_wins_and_same_day_conflicts_fail_closed() -> None:
    older, newer = _obs("AAA", "USD", "9.00", day=DAY - timedelta(days=1)), _obs("AAA", "USD", "10.00")
    out = mv.select_quotes(["AAA"], [mv.SyntheticProvider("SYN_A", [newer, older], ("EOD_CLOSE",))], POLICY)
    assert out["selected"]["AAA"] == newer
    clash = mv.select_quotes(["AAA"], [mv.SyntheticProvider("SYN_A", [newer, _obs("AAA", "USD", "10.50")], ("EOD_CLOSE",))], POLICY)
    assert clash["selected"] == {} and clash["rejected"][0]["reason"] == "CONFLICTING_OBSERVATIONS"
    with pytest.raises(DataContractError, match="QUOTE_POLICY_INVALID"):
        mv.select_quotes(["AAA"], [], mv.QuotePolicy(as_of=DAY, max_age_days=-1))


def _selected(doc: Dict[str, Any], scale: str = "1") -> Dict[str, mv.PriceObservation]:
    return {s: _obs(s, c, str(Decimal("10.00") * Decimal(scale))) for s, c in _held(doc).items()}


def _computed(doc: Dict[str, Any]) -> Decimal:
    ev = po.evidence_report(po.build_book(po.parse_snapshot(doc)))
    return sum((Decimal(a["computed_value"]) for a in ev["accounts"]), Decimal(0))


def test_revaluation_keeps_quantities_and_cash_and_is_linear_in_price() -> None:
    doc = _doc()
    before = copy.deepcopy(doc)
    one, meta = mv.revalue_snapshot(doc, _selected(doc), _fx(), "SYN_REVALUED")
    assert doc == before
    assert [a["positions"] for a in one["accounts"]] == [
        [{k: v for k, v in p.items() if not k.startswith("observed_market_value")} for p in a["positions"]] for a in before["accounts"]]
    assert [a["cash"] for a in one["accounts"]] == [a["cash"] for a in before["accounts"]]
    assert all("reported_total" not in a and "sub_portfolio_totals" not in a for a in one["accounts"])
    assert (one["valuation_date"], {p["as_of"] for p in one["prices"]}) == (DAY.isoformat(), {DAY.isoformat()})
    assert meta["valuation_mode"] == "SAME_DATE_EOD" and meta["broker_total_comparison"] == "TIME_MISALIGNED_COMPARISON"
    assert "REFERENCE_FX_NOT_EXECUTABLE" in meta["flags"] and meta["cash_basis"] == "CASH_AS_OF_HOLDINGS_OBSERVATION"
    two = mv.revalue_snapshot(doc, _selected(doc, "2"), _fx(), "SYN_REVALUED")[0]
    three = mv.revalue_snapshot(doc, _selected(doc, "3"), _fx(), "SYN_REVALUED")[0]
    step1, step2 = _computed(two) - _computed(one), _computed(three) - _computed(two)
    assert step1 > 0 and abs(step1 - step2) <= Decimal("0.05")


def test_revaluation_refuses_unknown_value_mixed_dates_and_bad_fx() -> None:
    doc = _doc()
    picked = _selected(doc)
    gap = dict(picked)
    gap.pop(sorted(gap)[0])
    with pytest.raises(DataContractError, match="REVALUATION_PRICE_UNAVAILABLE"):
        mv.revalue_snapshot(doc, gap, _fx(), "SYN_R")
    skew = dict(picked)
    first = sorted(skew)[0]
    skew[first] = _obs(first, skew[first].currency, day=DAY - timedelta(days=1))
    with pytest.raises(DataContractError, match="REVALUATION_TIME_MISALIGNED"):
        mv.revalue_snapshot(doc, skew, _fx(), "SYN_R")
    with pytest.raises(DataContractError, match="REVALUATION_TIME_MISALIGNED"):
        mv.revalue_snapshot(doc, picked, _fx(DAY - timedelta(days=1)), "SYN_R")
    with pytest.raises(DataContractError, match="REVALUATION_FX_KIND_INVALID"):
        mv.revalue_snapshot(doc, picked, _fx(kind="GUESSED"), "SYN_R")
    with pytest.raises(DataContractError, match="PRIVATE_FX_RECIPROCAL_INCONSISTENT"):
        mv.revalue_snapshot(doc, picked, _fx(back="33.00"), "SYN_R")
    full = json.loads(FIXTURE.read_text(encoding="utf-8"))
    with pytest.raises(DataContractError, match="REVALUATION_VALUE_ONLY_PRESENT"):
        mv.revalue_snapshot(full, picked, _fx(), "SYN_R")
    total_only = [a for a in full["accounts"] if not a.get("positions") and not a.get("cash")]
    assert total_only
    with_total_only = _doc()
    with_total_only["accounts"].append(total_only[0])
    with pytest.raises(DataContractError, match="REVALUATION_TOTAL_ONLY_ACCOUNT"):
        mv.revalue_snapshot(with_total_only, picked, _fx(), "SYN_R")
