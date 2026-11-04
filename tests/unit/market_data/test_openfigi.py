"""OpenFIGI identity connector: candidates only, header auth, bounded batching, no price semantics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Tuple

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.market_data import openfigi as of

KEY = "SYNTHETIC_OPENFIGI_KEY_NEVER_REAL"


def _provider(responses: List[Tuple[int, Any]], allow: Callable[[], bool] = lambda: True) -> Tuple[of.OpenFIGIIdentityProvider, List[Tuple[str, Mapping[str, str], bytes]]]:
    calls: List[Tuple[str, Mapping[str, str], bytes]] = []

    def post(url: str, headers: Mapping[str, str], body: bytes) -> Tuple[int, bytes]:
        calls.append((url, headers, body))
        status, payload = responses[min(len(calls) - 1, len(responses) - 1)]
        return status, payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")

    provider = of.OpenFIGIIdentityProvider((of.__name__, KEY), post, allow,
                                           lambda: datetime.now(timezone.utc))
    return provider, calls


def _ok(*items: Dict[str, Any]) -> Dict[str, Any]:
    return {"data": list(items)}


IBM = {"figi": "BBG000BLNNH6", "ticker": "IBM", "name": "INTL BUSINESS MACHINES CORP",
       "exchCode": "US", "securityType": "Common Stock", "marketSector": "Equity"}


def test_mapping_sends_the_key_in_the_header_and_never_in_the_url() -> None:
    provider, calls = _provider([(200, [_ok(IBM)])])
    result = provider.map_identifiers("TICKER", ["IBM"])
    assert result[0].status == of.SINGLE_CANDIDATE
    url, headers, body = calls[0]
    assert url == "https://api.openfigi.com/v3/mapping"
    assert KEY not in url and KEY not in body.decode()
    assert headers[of.X_OPENFIGI_APIKEY] == KEY
    assert json.loads(body) == [{"idType": "TICKER", "idValue": "IBM"}]


def test_batches_at_the_documented_maximum_and_dedupes() -> None:
    provider, calls = _provider([(200, [_ok(IBM)] * 100), (200, [_ok(IBM)] * 50)])
    values = [f"SYN{i}" for i in range(150)] + ["SYN0"]
    results = provider.map_identifiers("TICKER", values)
    assert len(calls) == 2 and len(results) == 150
    assert len(json.loads(calls[0][2])) == 100 and len(json.loads(calls[1][2])) == 50


def test_error_statuses_are_classified() -> None:
    for status, code in ((401, "IDENTITY_ACCESS_DENIED"), (429, "IDENTITY_RATE_LIMITED"),
                         (400, "IDENTITY_REQUEST_INVALID"), (503, "IDENTITY_UNAVAILABLE")):
        provider, _ = _provider([(status, b"")])
        with pytest.raises(DataContractError, match=code):
            provider.map_identifiers("TICKER", ["IBM"])


def test_no_match_and_multiple_candidates_stay_distinct() -> None:
    provider, _ = _provider([(200, [{"error": "No identifier found."}, _ok()])])
    results = provider.map_identifiers("TICKER", ["ZZZZ", "ZZZY"])
    assert results[0].status == of.NO_CANDIDATE and results[0].code
    assert results[1].status == of.NO_CANDIDATE

    second = {"figi": "BBG000BLNNH7", "ticker": "IBM", "exchCode": "GR"}
    provider, _ = _provider([(200, [_ok(IBM, second)])])
    ambiguous = provider.map_identifiers("TICKER", ["IBM"])[0]
    assert ambiguous.status == of.MULTIPLE_CANDIDATES and len(ambiguous.candidates) == 2


def test_malformed_envelope_and_unsupported_identifier_are_refused() -> None:
    provider, _ = _provider([(200, {"data": []})])
    with pytest.raises(DataContractError, match="IDENTITY_RESPONSE_INVALID"):
        provider.map_identifiers("TICKER", ["IBM"])
    provider, calls = _provider([(200, [_ok(IBM)])])
    with pytest.raises(DataContractError, match="IDENTITY_ID_TYPE_UNSUPPORTED"):
        provider.map_identifiers("LEI", ["5493000"])
    with pytest.raises(DataContractError, match="IDENTITY_ID_VALUE_INVALID"):
        provider.map_identifiers("TICKER", ["IBM;DROP"])
    assert calls == []


def test_local_limiter_blocks_before_any_request() -> None:
    provider, calls = _provider([(200, [_ok(IBM)])], allow=lambda: False)
    with pytest.raises(DataContractError, match="IDENTITY_RATE_LIMITED"):
        provider.map_identifiers("TICKER", ["IBM"])
    assert calls == []


def test_post_transport_refuses_other_hosts_and_extra_headers() -> None:
    with pytest.raises(DataContractError, match="IDENTITY_ENDPOINT_NOT_ALLOWED"):
        of.urllib_post("https://evil.example/v3/mapping", {}, b"[]")
    with pytest.raises(DataContractError, match="IDENTITY_HEADER_NOT_ALLOWED"):
        of.urllib_post("https://api.openfigi.com/v3/mapping", {"Authorization": "x"}, b"[]")


def test_owner_confirmation_is_never_inferred_from_a_single_hit() -> None:
    provider, _ = _provider([(200, [_ok(IBM)])])
    result = provider.map_identifiers("TICKER", ["IBM"])[0]
    assert of.confirm_candidate(result, "BBG000BLNNH6", owner_confirmed=False) == of.CANDIDATE_REVIEW_REQUIRED
    assert of.confirm_candidate(result, "BBG000BLNNH6", owner_confirmed=True) == of.OWNER_CONFIRMED
    assert of.confirm_candidate(result, "BBG000000000", owner_confirmed=True) == of.UNVERIFIED
    assert result.owner_confirmation_required is True


def test_module_declares_no_price_or_trading_surface() -> None:
    source = of.__file__ and open(of.__file__, encoding="utf-8").read()
    for banned in ("/v2/orders", "/v2/accounts", "paper-api", "AlpacaIEX", "PriceObservation"):
        assert banned not in source


def test_identity_batch_discloses_only_tickers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from acash.market_data import identity_batch as ib

    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({"securities": [
        {"security_id": "AAPL"}, {"security_id": "VOO"}, {"security_id": "SCBSET50"},
        {"security_id": "MTS-GOLD"}, {"security_id": "AAPL"}]}), encoding="utf-8")
    assert ib.held_tickers(snapshot) == ["AAPL", "VOO"]

    provider, calls = _provider([(200, [_ok(IBM), _ok(IBM)])])
    results = provider.map_identifiers("TICKER", ib.held_tickers(snapshot), exchCode="US")
    body = json.loads(calls[0][2])
    assert [job["idValue"] for job in body] == ["AAPL", "VOO"]
    for job in body:
        assert set(job) == {"idType", "idValue", "exchCode"}      # no quantity, value or account
    rows = ib.rows_for(results)
    assert rows[0]["owner_confirmation"] == "PENDING_OWNER_REVIEW"
    assert "figi" in rows[0]["candidates"][0]


def _batch(tmp_path: Path, rows: Any) -> Path:
    path = tmp_path / "identities.json"
    path.write_text(json.dumps({"schema": "ACASH_SECURITY_IDENTITIES_V1",
                                "data_class": "OWNER_PRIVATE_OBSERVATION", "rows": rows}), encoding="utf-8")
    return path


def _row(ticker: str, figi: str = "BBG000BLNNH6", **candidate: Any) -> Dict[str, Any]:
    return {"ticker": ticker, "status": "SINGLE_CANDIDATE",
            "candidates": [{"figi": figi, "ticker": ticker, "exch_code": "US",
                            "security_type": "Common Stock", **candidate}]}


def test_identity_review_validates_deterministically(tmp_path: Path) -> None:
    from acash.market_data import identity_review as ir

    rows = [_row("AAPL"), _row("VOO", figi="BBG000BLNNH7"),
            _row("BAD", figi="NOT_A_FIGI"),
            {"ticker": "MISMATCH", "status": "SINGLE_CANDIDATE",
             "candidates": [{"figi": "BBG000BLNNH8", "ticker": "OTHER", "exch_code": "US",
                            "security_type": "Common Stock"}]},
            _row("NOVENUE", figi="BBG000BLNNH9", exch_code=""),
            {"ticker": "MULTI", "status": "MULTIPLE_CANDIDATES",
             "candidates": [{"figi": "BBG000BLNNHA", "ticker": "MULTI", "exch_code": "US"},
                            {"figi": "BBG000BLNNHB", "ticker": "MULTI", "exch_code": "US"}]}]
    validated = {r["ticker"]: r["validation"] for r in ir.validate_rows(rows)}
    assert validated["AAPL"] == ir.AUTO and validated["VOO"] == ir.AUTO
    assert validated["BAD"] == ir.BLOCKED and "FIGI_FORMAT_INVALID" in str(
        next(r for r in ir.validate_rows(rows) if r["ticker"] == "BAD")["reasons"])
    assert validated["MISMATCH"] == ir.BLOCKED and validated["NOVENUE"] == ir.REVIEW
    assert validated["MULTI"] == ir.REVIEW


def test_identity_review_blocks_duplicate_figis(tmp_path: Path) -> None:
    from acash.market_data import identity_review as ir

    rows = [_row("AAPL"), _row("MSFT", figi="BBG000BLNNH6")]
    validated = {r["ticker"]: r["validation"] for r in ir.validate_rows(rows)}
    assert validated["AAPL"] == ir.AUTO and validated["MSFT"] == ir.BLOCKED


def test_bulk_confirmation_applies_only_validated_rows_and_checks_the_revision(tmp_path: Path) -> None:
    from acash.market_data import identity_review as ir

    path = _batch(tmp_path, [_row("AAPL"), _row("BAD", figi="NOT_A_FIGI"), _row("MULTI", figi="BBG000BLNNHC")])
    # make MULTI ambiguous so it must stay out of the bulk action
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["rows"][2] = {"ticker": "MULTI", "status": "MULTIPLE_CANDIDATES",
                      "candidates": [{"figi": "BBG000BLNNHC", "ticker": "MULTI", "exch_code": "US"},
                                     {"figi": "BBG000BLNNHD", "ticker": "MULTI", "exch_code": "US"}]}
    path.write_text(json.dumps(doc), encoding="utf-8")
    revision = ir.load_batch(path)["revision"]

    with pytest.raises(DataContractError, match="IDENTITY_REVIEW_REVISION_CONFLICT"):
        ir.confirm_bulk(path, "stale-revision", confirm=True)
    with pytest.raises(DataContractError, match="IDENTITY_CONFIRMATION_REQUIRED"):
        ir.confirm_bulk(path, revision, confirm=False)

    result = ir.confirm_bulk(path, revision, confirm=True)
    assert result["status"] == "CONFIRMED" and result["confirmed"] == 1
    assert result["excluded"] == ["BAD", "MULTI"]
    after = {row["ticker"]: row for row in ir.load_batch(path)["doc"]["rows"]}
    assert after["AAPL"]["owner_confirmation"] == ir.CONFIRMED
    assert after["BAD"].get("owner_confirmation") != ir.CONFIRMED
    assert after["MULTI"].get("owner_confirmation") != ir.CONFIRMED
    assert ir.load_batch(path)["doc"]["confirmation_revision"]["previous_revision"] == revision
