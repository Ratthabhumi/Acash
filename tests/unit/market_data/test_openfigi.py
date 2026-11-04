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
