"""RI-01 provider probe R1 harness tests (mock transport ONLY).

No live network, no credentials, no Homelab, no outcomes. Proves scope
gating (allowlist/holdout/capability/authorization), envelope integrity,
pagination to exhaustion, trade provenance preservation, entitlement
fail-closed, qualification separation, strict decoding, and stability comparison
— all against synthetic payloads.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.evidence import (
    content_sha256,
    ordered_page_chain_digest,
)
from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider
from acash.research.ri01.feasibility import parse_utc_timestamp
from acash.research.ri01.probe import (
    ALLOWLISTED_SESSIONS,
    HOLDOUT_START,
    PROBE_SYMBOL,
    RI01ProbeAuthority,
    RI01ProbeClient,
    _extract_rate_limit_headers,
    compare_stability,
    main,
)

CREDS = EnvAlpacaCredentialProvider(
    environ={
        "ACASH_ALPACA_API_KEY_ID": "mock_id",
        "ACASH_ALPACA_API_SECRET": "mock_secret",
    }
)
MOCK_RUNTIME_SHA = "a" * 40


def _build_authority(
    tmp_path: Path,
    session: date = date(2021, 6, 1),
    capability: str = "bars",
    max_requests: int = 10,
    valid_from: Optional[datetime] = None,
    valid_until: Optional[datetime] = None,
    read_only: bool = True,
    no_outcomes: bool = True,
    no_paper: bool = True,
    no_live: bool = True,
    capital_usd: Decimal = Decimal("0.00"),
    no_real_orders: bool = True,
    runtime_sha: str = MOCK_RUNTIME_SHA,
    authority_id: str = "AUTHORIZE_RI01_PROBE_R1_TEST",
) -> RI01ProbeAuthority:
    root = tmp_path / "external_evidence"
    root.mkdir(parents=True, exist_ok=True)
    v_from = valid_from or datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    v_until = valid_until or datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc)
    return RI01ProbeAuthority(
        authority_id=authority_id,
        runtime_sha=runtime_sha,
        session=session,
        capability=capability,
        evidence_root=root,
        max_requests=max_requests,
        valid_from_utc=v_from,
        valid_until_utc=v_until,
        read_only=read_only,
        no_outcomes=no_outcomes,
        no_paper=no_paper,
        no_live=no_live,
        capital_usd=capital_usd,
        no_real_orders=no_real_orders,
    )


def _synthetic_bars(session: date, count: int) -> List[Dict[str, Any]]:
    calendar = NyseCa1Calendar()
    open_utc = calendar.get_session(session).open_utc
    assert open_utc is not None
    return [
        {
            "t": (open_utc + timedelta(minutes=k)).isoformat(),
            "o": 100,
            "h": 101,
            "l": 99,
            "c": 100.5,
            "v": 1000,
        }
        for k in range(count)
    ]


def _bars_transport(pages: List[List[Dict[str, Any]]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/stocks/bars"
        token = request.url.params.get("page_token")
        index = 0 if token is None else int(token)
        next_tok = str(index + 1) if index + 1 < len(pages) else None
        body = {
            "bars": {PROBE_SYMBOL: pages[index]},
            "next_page_token": next_tok,
        }
        return httpx.Response(
            200,
            content=json.dumps(body).encode("utf-8"),
            headers={
                "x-ratelimit-limit": "200",
                "x-ratelimit-remaining": str(199 - index),
                "x-ratelimit-reset": "1700000000",
            },
        )

    return httpx.MockTransport(handler)


def _trades_transport(pages: Optional[List[List[Dict[str, Any]]]] = None) -> httpx.MockTransport:
    default_trades = [
        {
            "t": "2021-06-01T13:30:00.123456789Z",
            "x": "P",
            "p": 100.1,
            "s": 50,
            "c": ["O"],
        },
        {
            "t": "2021-06-01T13:30:00.234567890Z",
            "x": "N",
            "p": 100.2,
            "s": 10,
            "c": ["Q"],
        },
    ]
    trade_pages = pages or [default_trades]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/stocks/trades"
        token = request.url.params.get("page_token")
        index = 0 if token is None else int(token)
        next_tok = str(index + 1) if index + 1 < len(trade_pages) else None
        body = {
            "trades": {PROBE_SYMBOL: trade_pages[index]},
            "next_page_token": next_tok,
        }
        return httpx.Response(
            200,
            content=json.dumps(body).encode("utf-8"),
            headers={
                "x-ratelimit-limit": "200",
                "x-ratelimit-remaining": str(199 - index),
            },
        )

    return httpx.MockTransport(handler)


def _raising_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be issued")

    return httpx.MockTransport(handler)


# --- 1. Dry run & Scope Gating ---


def test_dry_run_validates_scope_zero_network(tmp_path: Path, capsys: Any) -> None:
    assert (
        main(
            ["--session", "2018-06-01", "--capability", "bars"],
            _transport=_raising_transport(),
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "SESSION = 2018-06-01" in out
    assert "NETWORK_REQUESTS = 0" in out


def test_holdout_session_rejected_zero_network() -> None:
    with pytest.raises(DataContractError, match="RI01_PROBE_HOLDOUT_FORBIDDEN"):
        main(["--session", "2024-03-01"], _transport=_raising_transport())


def test_non_allowlisted_session_rejected_zero_network() -> None:
    with pytest.raises(DataContractError, match="RI01_PROBE_SESSION_NOT_ALLOWLISTED"):
        main(["--session", "2020-01-02"], _transport=_raising_transport())


def test_unknown_capability_rejected_zero_network() -> None:
    with pytest.raises(DataContractError, match="RI01_PROBE_UNKNOWN_CAPABILITY"):
        main(["--session", "2018-06-01", "--capability", "quotes"], _transport=_raising_transport())


# --- 2. Authority Gating, Locks, and Strict Decoding ---


def test_bad_authority_pre_network_failure(tmp_path: Path) -> None:
    auth = _build_authority(tmp_path, authority_id="INVALID_PREFIX")
    with pytest.raises(DataContractError, match="RI01_PROBE_BAD_AUTHORITY_ID"):
        main(
            ["--execute-network"],
            _authority=auth,
            _transport=_raising_transport(),
            _runtime_sha=MOCK_RUNTIME_SHA,
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
        )


def test_runtime_mismatch_failure(tmp_path: Path) -> None:
    auth = _build_authority(tmp_path, runtime_sha="b" * 40)
    with pytest.raises(DataContractError, match="RI01_PROBE_RUNTIME_MISMATCH"):
        main(
            ["--execute-network"],
            _authority=auth,
            _transport=_raising_transport(),
            _runtime_sha=MOCK_RUNTIME_SHA,
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
        )


def test_authority_expiry_and_future_validity(tmp_path: Path) -> None:
    auth_expired = _build_authority(
        tmp_path,
        valid_from=datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc),
        valid_until=datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHORITY_EXPIRED"):
        main(
            ["--execute-network"],
            _authority=auth_expired,
            _transport=_raising_transport(),
            _runtime_sha=MOCK_RUNTIME_SHA,
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
        )

    auth_future = _build_authority(
        tmp_path,
        valid_from=datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc),
        valid_until=datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHORITY_FUTURE"):
        main(
            ["--execute-network"],
            _authority=auth_future,
            _transport=_raising_transport(),
            _runtime_sha=MOCK_RUNTIME_SHA,
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize(
    "lock_kwarg,val",
    [
        ({"read_only": False}, "read_only"),
        ({"no_outcomes": False}, "no_outcomes"),
        ({"no_paper": False}, "no_paper"),
        ({"no_live": False}, "no_live"),
        ({"capital_usd": Decimal("100.00")}, "capital_usd"),
        ({"no_real_orders": False}, "no_real_orders"),
    ],
)
def test_security_and_capital_locks_enforced(tmp_path: Path, lock_kwarg: Dict[str, Any], val: str) -> None:
    auth = _build_authority(tmp_path, **lock_kwarg)
    with pytest.raises(DataContractError, match="RI01_PROBE_LOCK_VIOLATION"):
        main(
            ["--execute-network"],
            _authority=auth,
            _transport=_raising_transport(),
            _runtime_sha=MOCK_RUNTIME_SHA,
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
        )


def test_evidence_root_rejections(tmp_path: Path) -> None:
    # Relative path
    auth_relative = _build_authority(tmp_path)
    object.__setattr__(auth_relative, "evidence_root", Path("relative/path"))
    with pytest.raises(DataContractError, match="EVIDENCE_ROOT_NOT_ABSOLUTE"):
        auth_relative.validate(
            datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
            MOCK_RUNTIME_SHA,
            NyseCa1Calendar(),
        )

    # HYP011 collision
    auth_hyp011 = _build_authority(tmp_path)
    object.__setattr__(auth_hyp011, "evidence_root", Path("/var/lib/acash/hyp011/v2"))
    with pytest.raises(DataContractError, match="EVIDENCE_ROOT_HYP011_COLLISION"):
        auth_hyp011.validate(
            datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
            MOCK_RUNTIME_SHA,
            NyseCa1Calendar(),
        )


def test_authority_strict_decoding_adversarial(tmp_path: Path) -> None:
    auth = _build_authority(tmp_path)
    base_dict = auth.to_dict()

    # 1. String booleans fail closed
    d_str_false = copy.deepcopy(base_dict)
    d_str_false["no_live"] = "false"
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHORITY_BAD_TYPE"):
        RI01ProbeAuthority.from_dict(d_str_false)

    d_str_true = copy.deepcopy(base_dict)
    d_str_true["read_only"] = "true"
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHORITY_BAD_TYPE"):
        RI01ProbeAuthority.from_dict(d_str_true)

    # 2. Integer booleans fail closed (0, 1)
    d_int_zero = copy.deepcopy(base_dict)
    d_int_zero["no_paper"] = 0
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHORITY_BAD_TYPE"):
        RI01ProbeAuthority.from_dict(d_int_zero)

    d_int_one = copy.deepcopy(base_dict)
    d_int_one["read_only"] = 1
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHORITY_BAD_TYPE"):
        RI01ProbeAuthority.from_dict(d_int_one)

    # 3. String max_requests fails closed
    d_str_req = copy.deepcopy(base_dict)
    d_str_req["max_requests"] = "10"
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHORITY_BAD_TYPE"):
        RI01ProbeAuthority.from_dict(d_str_req)

    # 4. Bool max_requests fails closed (bool is subclass of int)
    d_bool_req = copy.deepcopy(base_dict)
    d_bool_req["max_requests"] = True
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHORITY_BAD_TYPE"):
        RI01ProbeAuthority.from_dict(d_bool_req)

    # 5. Unknown fields fail closed
    d_unknown = copy.deepcopy(base_dict)
    d_unknown["malicious_extra_field"] = "payload"
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHORITY_UNKNOWN_FIELDS"):
        RI01ProbeAuthority.from_dict(d_unknown)

    # 6. Missing mandatory fields fail closed
    d_missing = copy.deepcopy(base_dict)
    del d_missing["runtime_sha"]
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHORITY_MISSING_FIELD"):
        RI01ProbeAuthority.from_dict(d_missing)

    # 7. Naive timestamp fails closed
    d_naive = copy.deepcopy(base_dict)
    d_naive["valid_from_utc"] = "2026-10-01T00:00:00"  # no tz
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHORITY_NAIVE_TIME"):
        RI01ProbeAuthority.from_dict(d_naive)

    # 8. Bad runtime SHA fails closed
    d_bad_sha = copy.deepcopy(base_dict)
    d_bad_sha["runtime_sha"] = "not_a_valid_sha"
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHORITY_BAD_TYPE"):
        RI01ProbeAuthority.from_dict(d_bad_sha)


def test_authority_sha256_sensitivity(tmp_path: Path) -> None:
    auth1 = _build_authority(tmp_path, max_requests=10)
    auth2 = _build_authority(tmp_path, max_requests=11)
    assert auth1.authority_sha256 != auth2.authority_sha256
    assert len(auth1.authority_sha256) == 64


# --- 3. Pagination, Request Budget, Rate Limits, and Evidence Immutability ---


def test_bars_multi_page_and_x_ratelimit_evidence(tmp_path: Path, capsys: Any) -> None:
    session = date(2021, 6, 1)
    bars = _synthetic_bars(session, 390)
    pages = [bars[:200], bars[200:]]
    auth = _build_authority(tmp_path, session=session, capability="bars", max_requests=5)

    assert (
        main(
            ["--execute-network"],
            _authority=auth,
            _transport=_bars_transport(pages),
            _runtime_sha=MOCK_RUNTIME_SHA,
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
            _credential_provider=CREDS,
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "BARS 2021-06-01: 390 bars, pages=2" in out
    assert "NETWORK_REQUESTS_ISSUED = 2" in out

    bars_dir = auth.evidence_root / "2021-06-01" / "bars"
    p0 = bars_dir / "page_0000.bin"
    p1 = bars_dir / "page_0001.bin"
    manifest_path = bars_dir / "manifest.json"
    qual_path = bars_dir / "qualification.json"
    assert p0.is_file() and p1.is_file() and manifest_path.is_file() and qual_path.is_file()

    manifest_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_doc["item_count"] == 390
    assert manifest_doc["status"] == "RETRIEVED"
    assert manifest_doc["authority_sha256"] == auth.authority_sha256
    assert len(manifest_doc["page_records"]) == 2
    assert manifest_doc["page_records"][0]["rate_limit_headers"]["x-ratelimit-remaining"] == "199"
    assert manifest_doc["page_records"][1]["rate_limit_headers"]["x-ratelimit-remaining"] == "198"

    # Qualification record proves consumer validation passed
    qual_doc = json.loads(qual_path.read_text(encoding="utf-8"))
    assert qual_doc["status"] == "QUALIFIED"
    assert qual_doc["qualified_item_count"] == 390
    assert qual_doc["expected_item_count"] == 390
    assert qual_doc["authority_sha256"] == auth.authority_sha256

    # Immutable create-once: re-running or overwriting must fail
    with pytest.raises(DataContractError, match="EVIDENCE_FILE_EXISTS_IMMUTABLE"):
        main(
            ["--execute-network"],
            _authority=auth,
            _transport=_bars_transport(pages),
            _runtime_sha=MOCK_RUNTIME_SHA,
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
            _credential_provider=CREDS,
        )


def test_trades_multi_page_and_provenance(tmp_path: Path, capsys: Any) -> None:
    session = date(2021, 6, 1)
    page1 = [
        {"t": "2021-06-01T13:30:00.100Z", "x": "P", "p": 100.1, "s": 50, "c": ["O"]},
    ]
    page2 = [
        {"t": "2021-06-01T13:30:00.200Z", "x": "N", "p": 100.2, "s": 10, "c": ["Q"]},
    ]
    auth = _build_authority(tmp_path, session=session, capability="trades", max_requests=10)

    assert (
        main(
            ["--execute-network"],
            _authority=auth,
            _transport=_trades_transport([page1, page2]),
            _runtime_sha=MOCK_RUNTIME_SHA,
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
            _credential_provider=CREDS,
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "TRADES 2021-06-01/open: 2 trades, pages=2" in out

    open_dir = auth.evidence_root / "2021-06-01" / "trades_open"
    assert (open_dir / "page_0000.bin").is_file()
    assert (open_dir / "page_0001.bin").is_file()
    assert (open_dir / "manifest.json").is_file()
    assert (open_dir / "qualification.json").is_file()


def test_repeated_token_detection_fails_closed(tmp_path: Path) -> None:
    session = date(2021, 6, 1)
    bars = _synthetic_bars(session, 10)

    def looping_handler(request: httpx.Request) -> httpx.Response:
        body = {
            "bars": {PROBE_SYMBOL: bars},
            "next_page_token": "static_infinite_loop_token",
        }
        return httpx.Response(200, content=json.dumps(body).encode("utf-8"))

    auth = _build_authority(tmp_path, session=session, capability="bars", max_requests=10)
    with pytest.raises(DataContractError, match="RI01_PROBE_REPEATED_PAGE_TOKEN"):
        main(
            ["--execute-network"],
            _authority=auth,
            _transport=httpx.MockTransport(looping_handler),
            _runtime_sha=MOCK_RUNTIME_SHA,
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
            _credential_provider=CREDS,
        )

    # Proves terminal failure manifest written
    manifest_path = auth.evidence_root / "2021-06-01" / "bars" / "manifest.json"
    assert manifest_path.is_file()
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert doc["status"] == "MALFORMED_RESPONSE"


def test_request_budget_exhaustion_fails_closed(tmp_path: Path) -> None:
    session = date(2021, 6, 1)
    bars = _synthetic_bars(session, 390)
    pages = [bars[:100], bars[100:200], bars[200:300], bars[300:]]
    # Allow only 2 requests, but 4 are required
    auth = _build_authority(tmp_path, session=session, capability="bars", max_requests=2)
    with pytest.raises(DataContractError, match="RI01_PROBE_REQUEST_BUDGET_EXHAUSTED"):
        main(
            ["--execute-network"],
            _authority=auth,
            _transport=_bars_transport(pages),
            _runtime_sha=MOCK_RUNTIME_SHA,
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
            _credential_provider=CREDS,
        )

    # Proves partial run recorded
    manifest_path = auth.evidence_root / "2021-06-01" / "bars" / "manifest.json"
    assert manifest_path.is_file()
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert doc["status"] == "PARTIAL"


# --- 4. RTH Grid Qualification vs Provider Response Bounds ---


def test_close_edge_provider_bar_excluded_from_grid(tmp_path: Path) -> None:
    session = date(2018, 6, 1)
    calendar = NyseCa1Calendar()
    close_utc = calendar.get_session(session).close_utc
    assert close_utc is not None

    # Alpaca start/end inclusive: provider returns 390 RTH bars PLUS 1 bar at close_utc (20:00:00)
    bars_391 = _synthetic_bars(session, 390)
    bars_391.append(
        {
            "t": close_utc.isoformat(),
            "o": 100,
            "h": 101,
            "l": 99,
            "c": 100.5,
            "v": 1000,
        }
    )
    auth = _build_authority(tmp_path, session=session, capability="bars")

    client = RI01ProbeClient(
        credential_provider=CREDS, transport=_bars_transport([bars_391])
    )
    now_utc = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
    manifest, qualified = client.fetch_bars(auth, calendar, now_utc)

    # Raw manifest preserves all 391 items retrieved from provider with status RETRIEVED
    assert manifest.item_count == 391
    assert manifest.status == "RETRIEVED"
    # Qualified RTH bars exclude the close-edge bar and match exact 390 regular-session count [open, close)
    assert len(qualified) == 390
    assert parse_utc_timestamp(qualified[-1]["timestamp"], "bar") < close_utc.astimezone(timezone.utc)


def test_half_day_grid_success(tmp_path: Path) -> None:
    session = date(2021, 11, 26)  # half day, 210 minutes
    bars = _synthetic_bars(session, 210)
    auth = _build_authority(tmp_path, session=session, capability="bars")

    client = RI01ProbeClient(
        credential_provider=CREDS, transport=_bars_transport([bars])
    )
    now_utc = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
    manifest, qualified = client.fetch_bars(auth, NyseCa1Calendar(), now_utc)
    assert len(qualified) == 210
    assert manifest.item_count == 210
    assert manifest.status == "RETRIEVED"


def test_missing_minute_fails_closed(tmp_path: Path) -> None:
    session = date(2018, 6, 1)
    # 389 bars instead of 390
    bars_missing = _synthetic_bars(session, 389)
    auth = _build_authority(tmp_path, session=session, capability="bars")
    client = RI01ProbeClient(
        credential_provider=CREDS, transport=_bars_transport([bars_missing])
    )
    now_utc = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(DataContractError, match="RI01_INCOMPLETE_SESSION_GRID"):
        client.fetch_bars(auth, NyseCa1Calendar(), now_utc)

    # CRITICAL INVARIANT: Incomplete grid writes manifest RETRIEVED + qualification CONTRACT_FAILED
    bars_dir = auth.evidence_root / "2018-06-01" / "bars"
    manifest_doc = json.loads((bars_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_doc["status"] == "RETRIEVED"
    assert manifest_doc["item_count"] == 389

    qual_doc = json.loads((bars_dir / "qualification.json").read_text(encoding="utf-8"))
    assert qual_doc["status"] == "CONTRACT_FAILED"
    assert qual_doc["qualified_item_count"] == 389
    assert qual_doc["expected_item_count"] == 390
    assert "RI01_INCOMPLETE_SESSION_GRID" in str(qual_doc["error_message"])


def test_generic_forbidden_never_covered(tmp_path: Path) -> None:
    auth = _build_authority(tmp_path, capability="bars")
    client = RI01ProbeClient(
        credential_provider=CREDS,
        transport=httpx.MockTransport(lambda req: httpx.Response(403, content=b"{}")),
    )
    with pytest.raises(DataContractError, match="RI01_PROBE_ACCESS_FORBIDDEN"):
        client.fetch_bars(auth, NyseCa1Calendar(), datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc))

    bars_dir = auth.evidence_root / auth.session.isoformat() / "bars"
    manifest_doc = json.loads((bars_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_doc["status"] == "ACCESS_FORBIDDEN"
    assert not (bars_dir / "qualification.json").exists()


def test_401_is_authentication_failure_not_entitlement_bars(tmp_path: Path) -> None:
    auth = _build_authority(tmp_path, capability="bars")
    client = RI01ProbeClient(
        credential_provider=CREDS,
        transport=httpx.MockTransport(lambda req: httpx.Response(401, content=b"{}")),
    )
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHENTICATION_FAILED") as excinfo:
        client.fetch_bars(auth, NyseCa1Calendar(), datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc))
    assert "ENTITLEMENT" not in str(excinfo.value)

    bars_dir = auth.evidence_root / auth.session.isoformat() / "bars"
    manifest_doc = json.loads((bars_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_doc["status"] == "AUTHENTICATION_FAILED"
    assert manifest_doc["status"] != "ENTITLEMENT_DENIED"
    assert not (bars_dir / "qualification.json").exists()


def test_403_reason_unconfirmed_trades(tmp_path: Path) -> None:
    auth = _build_authority(tmp_path, session=date(2021, 6, 1), capability="trades")
    with pytest.raises(DataContractError, match="RI01_PROBE_ACCESS_FORBIDDEN") as excinfo:
        main(
            ["--execute-network"],
            _authority=auth,
            _transport=httpx.MockTransport(lambda req: httpx.Response(403, content=b"{}")),
            _runtime_sha=MOCK_RUNTIME_SHA,
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
            _credential_provider=CREDS,
        )
    assert "AUTHENTICATION" not in str(excinfo.value)

    trades_dir = auth.evidence_root / "2021-06-01" / "trades_open"
    manifest_doc = json.loads((trades_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_doc["status"] == "ACCESS_FORBIDDEN"


def test_401_is_authentication_failure_not_entitlement_trades(tmp_path: Path) -> None:
    auth = _build_authority(tmp_path, session=date(2021, 6, 1), capability="trades")
    with pytest.raises(DataContractError, match="RI01_PROBE_AUTHENTICATION_FAILED") as excinfo:
        main(
            ["--execute-network"],
            _authority=auth,
            _transport=httpx.MockTransport(lambda req: httpx.Response(401, content=b"{}")),
            _runtime_sha=MOCK_RUNTIME_SHA,
            _now_utc=datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc),
            _credential_provider=CREDS,
        )
    assert "ENTITLEMENT" not in str(excinfo.value)

    trades_dir = auth.evidence_root / "2021-06-01" / "trades_open"
    manifest_doc = json.loads((trades_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_doc["status"] == "AUTHENTICATION_FAILED"
    assert not (trades_dir / "qualification.json").exists()


def test_http_error_never_covered(tmp_path: Path) -> None:
    auth = _build_authority(tmp_path, capability="bars")
    client = RI01ProbeClient(
        credential_provider=CREDS,
        transport=httpx.MockTransport(lambda req: httpx.Response(500, content=b"Internal Server Error")),
    )
    with pytest.raises(DataContractError, match="RI01_PROBE_BARS_HTTP_500"):
        client.fetch_bars(auth, NyseCa1Calendar(), datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc))

    bars_dir = auth.evidence_root / auth.session.isoformat() / "bars"
    manifest_doc = json.loads((bars_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_doc["status"] == "HTTP_FAILED"


def test_malformed_page_fails_closed(tmp_path: Path) -> None:
    auth = _build_authority(tmp_path, capability="bars")
    client = RI01ProbeClient(
        credential_provider=CREDS,
        transport=httpx.MockTransport(lambda req: httpx.Response(200, content=b"not-json")),
    )
    with pytest.raises(DataContractError, match="RI01_PROBE_BARS_CORRUPT"):
        client.fetch_bars(auth, NyseCa1Calendar(), datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc))

    bars_dir = auth.evidence_root / auth.session.isoformat() / "bars"
    manifest_doc = json.loads((bars_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_doc["status"] == "MALFORMED_RESPONSE"


def test_extract_rate_limit_headers_exact_prefix_only() -> None:
    headers = httpx.Headers(
        {
            "X-RateLimit-Limit": "200",
            "x-ratelimit-remaining": "199",
            "X-RATELIMIT-RESET": "1700000000",
            "Content-Type": "application/json",
            "custom-ratelimit-other": "ignored",
            "some-other-header": "val",
        }
    )
    extracted = _extract_rate_limit_headers(headers)
    assert set(extracted.keys()) == {
        "x-ratelimit-limit",
        "x-ratelimit-remaining",
        "x-ratelimit-reset",
    }
    assert "custom-ratelimit-other" not in extracted


def test_stability_comparison() -> None:
    assert compare_stability("a" * 64, "a" * 64) == "STABLE"
    assert compare_stability("a" * 64, "b" * 64) == "DIFFERENT"
    with pytest.raises(DataContractError, match="RI01_STABILITY_EMPTY_DIGEST"):
        compare_stability("", "b" * 64)


@pytest.mark.parametrize("capability", ["bars", "trades"])
@pytest.mark.parametrize("status,body,expected", [
    (401, {"code": 42210000, "message": "subscription does not permit querying recent SIP data"}, "AUTHENTICATION_FAILED"),
    (403, {"message": "secret mock_secret"}, "ACCESS_FORBIDDEN"),
    (422, {"code": 42210000, "message": "market orders must not have trail_price"}, "HTTP_FAILED"),
    (422, {"code": "42210000", "message": "subscription does not permit querying recent SIP data"}, "HTTP_FAILED"),
    (403, {"code": True, "message": "subscription does not permit querying recent SIP data"}, "ACCESS_FORBIDDEN"),
    (422, {"code": 42210000, "message": "subscription does not permit querying recent SIP data"}, "ENTITLEMENT_DENIED"),
    (403, {"code": 40010001, "message": "subscription does not permit querying recent SIP data"}, "ENTITLEMENT_DENIED"),
    (403, [42210000], "ACCESS_FORBIDDEN"),
    (403, {"code": 42210000, "message": "subscription does not permit querying recent SIP data", "extra": "x" * 4096}, "ACCESS_FORBIDDEN"),
])
def test_http_failure_evidence_requires_positive_entitlement(
    tmp_path: Path, capability: str, status: int, body: Any, expected: str,
) -> None:
    auth = _build_authority(tmp_path, capability=capability)
    client = RI01ProbeClient(CREDS, httpx.MockTransport(lambda request: httpx.Response(status, json=body)))
    now = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
    with pytest.raises(DataContractError):
        if capability == "bars":
            client.fetch_bars(auth, NyseCa1Calendar(), now)
        else:
            client.fetch_trades_window(
                datetime(2021, 6, 1, 13, 25, tzinfo=timezone.utc),
                datetime(2021, 6, 1, 13, 35, tzinfo=timezone.utc), "open", auth, now,
            )
    folder = auth.evidence_root / "2021-06-01" / ("bars" if capability == "bars" else "trades_open")
    raw = (folder / "manifest.json").read_text()
    doc = json.loads(raw)
    assert doc["status"] == expected
    assert doc["subject_metadata"]["http_status"] == status
    assert doc["subject_metadata"]["http_response_observed"] is True
    assert "mock_secret" not in raw and "trail_price" not in raw
    assert not (folder / "qualification.json").exists()
    assert client.requests_issued == 1


@pytest.mark.parametrize("capability", ["bars", "trades"])
@pytest.mark.parametrize("error_type", [httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError, httpx.ReadError])
@pytest.mark.parametrize("partial", [False, True])
def test_transport_failure_preserves_partial_pages_without_retry(
    tmp_path: Path, capability: str, error_type: type[httpx.RequestError], partial: bool,
) -> None:
    auth = _build_authority(tmp_path, capability=capability)
    calls = 0
    first_bytes = json.dumps({capability: {"SPY": []}, "next_page_token": "next"}).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if partial and calls == 1:
            return httpx.Response(200, content=first_bytes)
        raise error_type("mock_secret https://user:password@private.invalid", request=request)

    client = RI01ProbeClient(CREDS, httpx.MockTransport(handler))
    now = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
    with pytest.raises(DataContractError, match="RI01_PROBE_TRANSPORT_FAILED") as excinfo:
        if capability == "bars":
            client.fetch_bars(auth, NyseCa1Calendar(), now)
        else:
            client.fetch_trades_window(
                datetime(2021, 6, 1, 13, 25, tzinfo=timezone.utc),
                datetime(2021, 6, 1, 13, 35, tzinfo=timezone.utc), "open", auth, now,
            )
    folder = auth.evidence_root / "2021-06-01" / ("bars" if capability == "bars" else "trades_open")
    raw = (folder / "manifest.json").read_text()
    doc = json.loads(raw)
    assert doc["status"] == "TRANSPORT_FAILED"
    assert doc["operation_count"] == calls == (2 if partial else 1)
    assert len(doc["page_records"]) == int(partial)
    metadata = doc["subject_metadata"]
    assert metadata["provider_acceptance"] == "UNKNOWN"
    assert metadata["invocation_initiated"] is True
    assert metadata["http_response_observed"] is False
    assert metadata["retrieval_completed"] is False
    assert "http_status" not in metadata
    assert "mock_secret" not in raw + str(excinfo.value)
    assert "password" not in raw + str(excinfo.value)
    assert not (folder / "qualification.json").exists()
    if partial:
        assert (folder / "page_0000.bin").read_bytes() == first_bytes
        assert doc["page_records"][0]["raw_bytes_sha256"] == content_sha256(first_bytes)
