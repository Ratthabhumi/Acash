"""Tests for prospective shadow ops: single-session accounting, chain, runner guards.

Synthetic/mocked only. No network. No live observation.
"""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_011.shadow_ca import CADetermination
from acash.research.hyp_011.shadow_ops import (
    SessionMarket,
    ShadowBenchmark,
    ShadowPortfolio,
    append_observation,
    build_initial_state,
    process_benchmark_session,
    process_strategy_session,
    validate_initial_state,
)


def _load_runner_module() -> Any:
    import importlib.util

    script_path = Path(__file__).resolve().parents[3] / "scripts" / "process_hyp_011_prospective_shadow.py"
    spec = importlib.util.spec_from_file_location("process_hyp_011_prospective_shadow", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _market(session: date, level: str = "100") -> SessionMarket:
    px = Decimal(level)
    return SessionMarket(
        session=session,
        opens_raw={"ACWI": px, "AGG": px},
        closes_raw={"ACWI": px, "AGG": px},
    )


def test_fresh_state_and_initial_80_20_allocation() -> None:
    portfolio = ShadowPortfolio()
    assert portfolio.cash == Decimal("100000.00")
    assert portfolio.holdings == {"ACWI": 0, "AGG": 0}
    frag = process_strategy_session(
        portfolio, _market(date(2026, 9, 28)), {}, True,
        Decimal("2"), 1, "SHADOW_BASELINE",
    )
    assert portfolio.holdings["ACWI"] > 0
    assert portfolio.holdings["AGG"] > 0
    w_acwi = Decimal(portfolio.holdings["ACWI"]) * Decimal("100") / Decimal(frag["equity"])
    assert abs(w_acwi - Decimal("0.80")) < Decimal("0.05")


def test_initial_allocation_not_annual_rebalance() -> None:
    # Rebalance counting lives in ShadowState.completed_annual_rebalances,
    # which process_strategy_session never touches.
    from acash.research.hyp_011.shadow import ShadowState

    state = ShadowState(activation_session=date(2026, 9, 28))
    assert state.completed_annual_rebalances == 0


def test_prior_close_entitlement_and_payable_ordering() -> None:
    portfolio = ShadowPortfolio()
    process_strategy_session(
        portfolio, _market(date(2026, 9, 28)), {}, True, Decimal("2"), 1, "P"
    )
    shares = portfolio.holdings["ACWI"]
    event = CADetermination(
        symbol="ACWI", session=date(2026, 9, 29), has_event=True,
        ex_date=date(2026, 9, 29), amount_per_share=Decimal("1"),
        payable_date=date(2026, 10, 5),
        authority_source="BLACKROCK_ISHARES_OFFICIAL",
        retrieved_at_utc="2026-09-29T21:00:00+00:00", source_sha256="a" * 64,
    )
    frag = process_strategy_session(
        portfolio, _market(date(2026, 9, 29)), {"ACWI": event}, False,
        Decimal("2"), 1, "P",
    )
    assert frag["entitlements"] == [{
        "symbol": "ACWI", "ex_date": "2026-09-29", "amount": str(Decimal(shares)),
        "authority_source": "BLACKROCK_ISHARES_OFFICIAL",
        "authority_sha256": "a" * 64,
    }]
    # Receivable in equity but not yet spendable (payable Oct-05).
    assert Decimal(frag["receivable"]) == Decimal(shares)


def test_ex_date_activation_buy_not_entitled() -> None:
    portfolio = ShadowPortfolio()
    event = CADetermination(
        symbol="ACWI", session=date(2026, 9, 28), has_event=True,
        ex_date=date(2026, 9, 28), amount_per_share=Decimal("1"),
        payable_date=date(2026, 10, 5),
        authority_source="BLACKROCK_ISHARES_OFFICIAL",
        retrieved_at_utc="2026-09-28T21:00:00+00:00", source_sha256="b" * 64,
    )
    frag = process_strategy_session(
        portfolio, _market(date(2026, 9, 28)), {"ACWI": event}, True,
        Decimal("2"), 1, "P",
    )
    assert frag["entitlements"] == []


def test_split_fail_close_contract() -> None:
    # Split-event authority must be bound before holdings update; the ops layer
    # performs no silent ratio inference. Non-positive prices fail closed here
    # as the accounting-level guard.
    portfolio = ShadowPortfolio()
    bad = SessionMarket(
        session=date(2026, 9, 28),
        opens_raw={"ACWI": Decimal("0"), "AGG": Decimal("100")},
        closes_raw={"ACWI": Decimal("100"), "AGG": Decimal("100")},
    )
    with pytest.raises(DataContractError):
        process_strategy_session(
            portfolio, bad, {}, True, Decimal("2"), 1, "P"
        )


def test_single_row_provider_contract_shape() -> None:
    from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient
    from acash.data.qualification.models import MarketDataFeed, PriceAdjustment

    import httpx

    calls = []

    def _boom(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise AssertionError("network must not be invoked")

    client = HYP011AlpacaClient(transport=httpx.MockTransport(_boom))
    # Sunday is not a trading session: rejected pre-network with zero calls.
    with pytest.raises(DataContractError):
        client.fetch_single_session(
            symbol="ACWI", session=date(2026, 9, 27),
            feed=MarketDataFeed.SIP, adjustment=PriceAdjustment.RAW,
            timeframe="1Day",
        )
    assert calls == []


def test_append_only_chain_and_tamper() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp)
        sha1 = append_observation(
            state_dir, date(2026, 9, 28), {"equity": "100979.02"}, None
        )
        assert (state_dir / "observations" / "2026-09-28.json").is_file()
        state = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
        assert state["last_observation_sha256"] == sha1
        assert state["observed_session_count"] == 1
        # Duplicate write rejected (immutability).
        with pytest.raises(DataContractError):
            append_observation(state_dir, date(2026, 9, 28), {"equity": "1"}, sha1)
        # Tamper detection: altered bytes no longer match the chained pin.
        target = state_dir / "observations" / "2026-09-28.json"
        target.write_text('{"tampered": true}', encoding="utf-8")
        import hashlib

        assert hashlib.sha256(target.read_bytes()).hexdigest() != sha1


def test_benchmark_independent_and_first_day_anchor() -> None:
    bench = ShadowBenchmark()
    frag = process_benchmark_session(
        bench, date(2026, 9, 28), Decimal("500"), Decimal("501"), None, Decimal("2")
    )
    assert frag["entry"]["side"] == "BUY"
    assert bench.shares > 0
    # First-day return anchored at 100000.
    first_equity = Decimal(frag["equity"])
    assert Decimal(frag["daily_return"]) == first_equity / Decimal("100000") - Decimal("1")
    # Second session with same prices: return ~ fee-free drift only.
    frag2 = process_benchmark_session(
        bench, date(2026, 9, 29), Decimal("501"), Decimal("501"), None, Decimal("2")
    )
    assert Decimal(frag2["daily_return"]) == Decimal(frag2["equity"]) / first_equity - Decimal("1")


def test_runner_dry_run_zero_network(
    capsys: Any, stage_c_b_absent: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner_module()
    monkeypatch.setattr(runner, "STAGE_C_RECOVERY_BINDING_PATH", stage_c_b_absent)

    assert (
        runner.main(
            [],
            _now_utc=datetime(2026, 9, 28, 15, 0, 0, tzinfo=timezone.utc),
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "PRETEST" in out
    assert "EXPECTED_SESSION = 2026-09-28" in out
    assert "SESSION_OPEN_UTC = 2026-09-28T13:30:00+00:00" in out
    assert "SESSION_CLOSE_UTC = 2026-09-28T20:00:00+00:00" in out
    assert "NETWORK_REQUESTS = 0" in out


def test_state_serde_round_trip() -> None:
    from acash.research.hyp_011.shadow_ops import (
        ShadowBenchmark,
        ShadowPortfolio,
        verify_chain,
    )

    portfolio = ShadowPortfolio()
    process_strategy_session(
        portfolio, _market(date(2026, 9, 28)), {}, True, Decimal("2"), 1, "P"
    )
    restored = ShadowPortfolio.from_dict(portfolio.to_dict())
    assert restored == portfolio
    bench = ShadowBenchmark()
    process_benchmark_session(
        bench, date(2026, 9, 28), Decimal("500"), Decimal("501"), None, Decimal("2")
    )
    assert ShadowBenchmark.from_dict(bench.to_dict()) == bench
    with pytest.raises(DataContractError):
        ShadowPortfolio.from_dict({"cash": "x"})


def test_verify_chain_blocks_tamper_and_orphan() -> None:
    import tempfile

    from acash.research.hyp_011.shadow_ops import append_observation, verify_chain

    with tempfile.TemporaryDirectory() as tmp:
        state_dir = Path(tmp)
        # Empty dir verifies as the complete canonical initial state.
        fresh = verify_chain(state_dir)
        validate_initial_state(fresh)
        assert fresh["observed_sessions"] == []
        assert fresh["observed_session_count"] == 0
        # Mutated identity field -> blocked.
        tampered = dict(fresh)
        tampered["starting_aum"] = "99999.99"
        (state_dir / "state.json").write_text(json.dumps(tampered), encoding="utf-8")
        with pytest.raises(DataContractError):
            verify_chain(state_dir)
        # Orphan file with no state sessions -> blocked.
        (state_dir / "observations").mkdir(parents=True, exist_ok=True)
        (state_dir / "observations" / "2026-09-28.json").write_text("{}", encoding="utf-8")
        (state_dir / "state.json").write_text(
            json.dumps(dict(fresh, observed_sessions=["2026-09-28"])),
            encoding="utf-8",
        )
        with pytest.raises(DataContractError):
            verify_chain(state_dir)


def test_runner_ordinal_and_chain_guards() -> None:
    runner = _load_runner_module()

    # Wrong ordinal rejected pre-network (no --execute-network needed for arg parse,
    # but ordinal check happens after chain verify which needs no network).
    with pytest.raises(DataContractError):
        runner.main(["--execute-network", "--authorization", "AUTH_X", "--ordinal", "99"])


class _MockBars:
    bars: List[Any]
    pages_metadata: List[Any]
    pages_raw_bytes: List[Any]

    def __init__(self, session: date, level: str = "100"):
        from acash.data.qualification.daily_models import DailyBar

        self.bars = [
            DailyBar(
                timestamp_utc=datetime.combine(
                    session, datetime.min.time(), tzinfo=timezone.utc
                ).replace(hour=5),
                open=Decimal(level),
                high=Decimal(level),
                low=Decimal(level),
                close=Decimal(level),
                volume=Decimal("1000"),
            )
        ]
        self.pages_metadata = []
        self.pages_raw_bytes = []


class _MockClient:
    def __init__(self, calls: List[Any], level: str = "100"):
        self._calls = calls
        self._level = level

    def fetch_single_session(self, symbol: str, session: date, **kwargs: Any) -> Any:
        self._calls.append((symbol, session.isoformat()))
        return _MockBars(session, self._level)


def _make_test_stage_c_binding(tmp_path: Path) -> Path:
    binding_path = tmp_path / "stage_c_test_binding.json"
    doc = {
        "binding_id": "HYP_011_PROSPECTIVE_SHADOW_RECOVERY_STAGE_C",
        "binding_commit_sha": "d9608c0a2353bd5ed41943e5fb893ef9648089d2",
        "binding_commit_utc": "2026-09-29T12:00:00Z",
        "activation_session": "2026-09-29",
        "scientific_prospective_boundary": "2026-09-25",
        "failed_dispatch_session": "2026-09-28",
        "failed_dispatch_attempt": 1,
        "next_observation_ordinal": 1,
        "next_dispatch_attempt": 2,
        "backfill_allowed": False,
        "retry_failed_session_allowed": False,
        "locks": {
            "paper_trading": False,
            "live_trading": False,
            "real_capital_authority_usd": "0.00",
            "no_real_orders": True,
        },
    }
    binding_path.write_text(json.dumps(doc), encoding="utf-8")
    return binding_path


def _run_observation(
    tmp_path: Path,
    session: str,
    ordinal: int,
    now_utc: datetime,
    calls: List[Any],
    level: str = "100",
    ca_file: str = "",
    stage_c_binding: Optional[Path] = None,
    dispatch_attempt: int = 1,
    authority_path: str = "",
    runtime_sha: Optional[str] = None,
    bundle_path: str = "",
) -> int:
    runner = _load_runner_module()

    if dispatch_attempt > 1:
        auth = f"AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_{ordinal:04d}_ATTEMPT_{dispatch_attempt:04d}"
    else:
        auth = f"AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_{ordinal:04d}"

    argv = [
        "--execute-network",
        "--authorization",
        auth,
        "--ordinal",
        str(ordinal),
        "--dispatch-attempt",
        str(dispatch_attempt),
    ]
    if ca_file:
        argv += ["--ca-determinations", ca_file]
    if authority_path:
        argv += ["--dispatch-authority", authority_path]
    if bundle_path:
        argv += ["--ca-evidence-bundle", bundle_path]
    from acash.execution.alpaca.credentials import EnvAlpacaCredentialProvider

    dummy_prov = EnvAlpacaCredentialProvider(
        environ={"ACASH_ALPACA_API_KEY_ID": "mock_id", "ACASH_ALPACA_API_SECRET": "mock_secret"}
    )
    return int(
        runner.main(
            argv,
            _now_utc=now_utc,
            _state_dir=tmp_path,
            _client=_MockClient(calls, level),
            _credential_provider=dummy_prov,
            _stage_c_binding_path=stage_c_binding,
            _runtime_sha=runtime_sha,
        )
    )


def test_mocked_observation_0001_end_to_end(tmp_path: Path) -> None:
    binding = _make_test_stage_c_binding(tmp_path)
    calls: List[Any] = []
    rc = _run_observation(
        tmp_path, "2026-09-29", 1,
        datetime(2026, 9, 29, 21, 0, 0, tzinfo=timezone.utc), calls,
        stage_c_binding=binding, dispatch_attempt=2,
    )
    assert rc == 0
    assert len(calls) == 6  # 3 symbols x 2 adjustments, no retry
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["activation_session"] == "2026-09-29"
    assert state["observed_sessions"] == ["2026-09-29"]
    assert state["observed_session_count"] == 1
    assert state["last_processed_session"] == "2026-09-29"
    assert state["completed_annual_rebalances"] == 0
    assert state["strategy"]["holdings"]["ACWI"] > 0
    assert state["strategy"]["holdings"]["AGG"] > 0
    assert state["benchmark"]["SPY_shares"] > 0
    obs = json.loads(
        (tmp_path / "observations" / "2026-09-29.json").read_text(encoding="utf-8")
    )
    assert obs["previous_observation_sha256"] is None
    # Session one makes no existence claim: explicit non-required status.
    for symbol in ("ACWI", "AGG", "SPY"):
        assert obs["corporate_actions"][symbol] == {
            "status": "CA_NOT_ECONOMICALLY_REQUIRED_NO_PRIOR_HOLDINGS"
        }
    assert state["last_observation_sha256"] == hashlib.sha256(
        (tmp_path / "observations" / "2026-09-29.json").read_bytes()
    ).hexdigest()


def test_second_mocked_observation_continuity(tmp_path: Path) -> None:
    binding = _make_test_stage_c_binding(tmp_path)
    calls: List[Any] = []
    assert _run_observation(
        tmp_path, "2026-09-29", 1,
        datetime(2026, 9, 29, 21, 0, 0, tzinfo=timezone.utc), calls,
        stage_c_binding=binding, dispatch_attempt=2,
    ) == 0
    state1 = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    cash1 = state1["strategy"]["cash"]
    # Second session: needs canonical CA determinations (has prior holdings now).
    # F16 intake contract: no-event docs carry scope evidence + evidence refs.
    # F19: digests are recomputed bundle-evidence digests over fixture bytes.
    sponsors = {"ACWI": "BLACKROCK_ISHARES_OFFICIAL", "AGG": "BLACKROCK_ISHARES_OFFICIAL", "SPY": "STATE_STREET_SPDR_OFFICIAL"}
    urls = {
        "ACWI": "https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf",
        "AGG": "https://www.ishares.com/us/products/239458/ishares-core-us-aggregate-bond-etf",
        "SPY": "https://www.ssga.com/us/en/institutional/etfs/spdr-sp-500-etf-trust-spy",
    }
    identities = {
        "ACWI": {"product_id": "239600", "ticker": "ACWI",
                 "sponsor": "BLACKROCK_ISHARES_OFFICIAL"},
        "AGG": {"product_id": "239458", "ticker": "AGG",
                "sponsor": "BLACKROCK_ISHARES_OFFICIAL"},
        "SPY": {"schedule": "SSGA_OFFICIAL_2026_DISTRIBUTIONS", "ticker": "SPY",
                "sponsor": "STATE_STREET_SPDR_OFFICIAL"},
    }
    bundle_root = tmp_path / "ca_bundle_2026-09-30"
    bundle_digests = {}
    for symbol in ("ACWI", "AGG", "SPY"):
        sdir = bundle_root / symbol
        edir = sdir / "evidence"
        edir.mkdir(parents=True)
        ev_bytes = f"OFFICIAL-FIXTURE-EVIDENCE::{symbol}::2026-09-30\n".encode()
        sched_bytes = f"OFFICIAL-FIXTURE-SCHEDULE::{symbol}::2026-09-30\n".encode()
        ev_name = f"{symbol.lower()}-scope-fixture.pdf"
        sched_name = f"{symbol.lower()}-schedule-fixture.pdf"
        (edir / ev_name).write_bytes(ev_bytes)
        (edir / sched_name).write_bytes(sched_bytes)
        ev_sha = hashlib.sha256(ev_bytes).hexdigest()
        sched_sha = hashlib.sha256(sched_bytes).hexdigest()
        manifest = {
            "schema_version": 1, "symbol": symbol, "target_session": "2026-09-30",
            "authority_source": sponsors[symbol], "official_url": urls[symbol],
            "product_identity": identities[symbol], "evidence_file": ev_name,
            "evidence_sha256": ev_sha,
            "retrieved_at_utc": "2026-09-30T21:00:00+00:00",
            "scope_type": "NO_EVENT_SCOPE",
            "schedule_evidence": {"file": sched_name, "sha256": sched_sha},
            "note": "Fixture bundle.",
        }
        (sdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        bundle_digests[symbol] = {"sha": ev_sha, "ref": ev_name, "sched_sha": sched_sha}
    ca_doc = {
        symbol: {
            "symbol": symbol,
            "session": "2026-09-30",
            "has_event": False,
            "authority_source": sponsors[symbol],
            "retrieved_at_utc": "2026-09-30T21:00:00+00:00",
            "source_sha256": bundle_digests[symbol]["sha"],
            "evidence_ref": bundle_digests[symbol]["ref"],
            "scope_evidence": {
                "schedule_id": "FIXTURE_OFFICIAL_SCOPE_2026_09_30",
                "schedule_sha256": bundle_digests[symbol]["sched_sha"],
                "scope_note": "Fixture official-scope coverage for 2026-09-30.",
                "retrieved_at_utc": "2026-09-30T21:00:00+00:00",
            },
        }
        for symbol in ("ACWI", "AGG", "SPY")
    }
    ca_path = tmp_path / "ca_2026-09-30.json"
    ca_path.write_text(json.dumps(ca_doc), encoding="utf-8")
    # F15 ceremony: mint a DispatchAuthority bound to intent + runtime + CA bytes.
    # F17: the authority binds the PHYSICALLY preregistered intent digest.
    from acash.research.hyp_011.shadow_authority import (
        ObservationIntent,
        register_observation_intent,
        validate_observation_intent,
    )

    fixture_runtime_sha = "e" * 40
    reg_path = register_observation_intent(
        registry_dir=tmp_path / "intent_registry",
        calendar=NyseCa1Calendar(),
        target_session=date(2026, 9, 30),
        observation_ordinal=2,
        previous_observation_sha256=state1["last_observation_sha256"],
        scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
        authority_identity="TEST_FIXTURE",
        now_utc=datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc),
    )
    registered_sha = str(json.loads(reg_path.read_text(encoding="utf-8"))["intent_sha256"])
    intent = ObservationIntent(
        hypothesis_id="HYP_011",
        target_session=date(2026, 9, 30),
        observation_ordinal=2,
        scientific_inclusion_intent="INCLUDE_PROSPECTIVE",
        previous_observation_sha256=state1["last_observation_sha256"],
        backfill_allowed=False,
        automatic_skip_allowed=False,
        created_at_utc=datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc),
        authority_identity="TEST_FIXTURE",
    )
    cal = NyseCa1Calendar()
    validated_intent = validate_observation_intent(
        intent.canonical_doc(), cal, datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    )
    ca_bytes = ca_path.read_bytes()
    authority_doc = {
        "schema_version": 1,
        "intent_sha256": registered_sha,
        "intent": intent.canonical_doc(),
        "runtime_commit_sha": fixture_runtime_sha,
        "target_session": "2026-09-30",
        "observation_ordinal": 2,
        "dispatch_attempt": 1,
        "valid_after_utc": "2026-09-30T00:00:00+00:00",
        "expires_at_utc": "2026-10-01T00:00:00+00:00",
        "ca_manifest_sha256": hashlib.sha256(ca_bytes).hexdigest(),
        "paper_trading": False,
        "live_trading": False,
        "real_capital_authority_usd": "0.00",
        "no_real_orders": True,
        "authority_identity": "TEST_FIXTURE",
    }
    authority_path = tmp_path / "dispatch_authority_0002.json"
    authority_path.write_text(json.dumps(authority_doc, indent=2), encoding="utf-8")
    assert _run_observation(
        tmp_path, "2026-09-30", 2,
        datetime(2026, 9, 30, 21, 0, 0, tzinfo=timezone.utc), calls,
        level="101", ca_file=str(ca_path),
        stage_c_binding=binding, dispatch_attempt=1,
        authority_path=str(authority_path), runtime_sha=fixture_runtime_sha,
        bundle_path=str(bundle_root),
    ) == 0
    state2 = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state2["observed_sessions"] == ["2026-09-29", "2026-09-30"]
    assert state2["observed_session_count"] == 2
    # No fresh reset: holdings/cash continue, benchmark does not re-enter.
    assert state2["strategy"]["holdings"] == state1["strategy"]["holdings"]
    assert state2["benchmark"]["SPY_shares"] == state1["benchmark"]["SPY_shares"]
    obs2 = json.loads(
        (tmp_path / "observations" / "2026-09-30.json").read_text(encoding="utf-8")
    )
    assert obs2["previous_observation_sha256"] == state1["last_observation_sha256"]
    assert state2["last_observation_sha256"] == hashlib.sha256(
        (tmp_path / "observations" / "2026-09-30.json").read_bytes()
    ).hexdigest()
    # F16-B: intake provenance survives into the sealed observation.
    # F19: sealed digests are recomputed bundle-evidence digests.
    for symbol, sponsor in (
        ("ACWI", "BLACKROCK_ISHARES_OFFICIAL"),
        ("AGG", "BLACKROCK_ISHARES_OFFICIAL"),
        ("SPY", "STATE_STREET_SPDR_OFFICIAL"),
    ):
        section = obs2["corporate_actions"][symbol]
        assert section["authority_source"] == sponsor
        assert section["source_sha256"] == bundle_digests[symbol]["sha"]
        assert section["evidence_ref"] == bundle_digests[symbol]["ref"]
        assert section["scope_evidence"]["schedule_sha256"] == bundle_digests[symbol]["sched_sha"]
        assert section["has_event"] is False
    # F15: each live dispatch consumed exactly one ledger entry (bare ordinal-1
    # attempt + authority-bound ordinal-2 attempt).
    assert len(list((tmp_path / "dispatch_ledger").glob("*.json"))) == 2


def _ca_doc(
    symbol: str, session: str, sponsor: str, has_event: bool = False,
) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "session": session,
        "has_event": has_event,
        "authority_source": sponsor,
        "retrieved_at_utc": f"{session}T21:00:00+00:00",
        "source_sha256": "d" * 64,
    }


def test_ca_from_dict_round_trip_no_event() -> None:
    from acash.research.hyp_011.shadow_ca import CADetermination

    now = datetime(2026, 9, 29, 21, 30, 0, tzinfo=timezone.utc)
    det = CADetermination.from_dict(
        _ca_doc("ACWI", "2026-09-29", "BLACKROCK_ISHARES_OFFICIAL"),
        "ACWI", date(2026, 9, 29), now,
    )
    assert det.has_event is False
    assert det.source_sha256 == "d" * 64


def test_ca_from_dict_event_requires_canonical_amount() -> None:
    from acash.research.hyp_011.shadow_ca import CADetermination

    now = datetime(2026, 9, 29, 21, 30, 0, tzinfo=timezone.utc)
    base = _ca_doc("AGG", "2026-09-29", "BLACKROCK_ISHARES_OFFICIAL", True)
    base.update({
        "ex_date": "2026-09-29",
        "amount_per_share": "0.5",
        "payable_date": "2026-10-05",
    })
    det = CADetermination.from_dict(base, "AGG", date(2026, 9, 29), now)
    assert det.amount_per_share == Decimal("0.5")
    # Legacy "amount" key alone is NOT accepted.
    legacy = dict(base)
    del legacy["amount_per_share"]
    legacy["amount"] = "0.5"
    with pytest.raises(DataContractError):
        CADetermination.from_dict(legacy, "AGG", date(2026, 9, 29), now)


def test_ca_from_dict_rejects_spoof_and_future() -> None:
    from acash.research.hyp_011.shadow_ca import CADetermination

    now = datetime(2026, 9, 29, 21, 30, 0, tzinfo=timezone.utc)
    good = _ca_doc("SPY", "2026-09-29", "STATE_STREET_SPDR_OFFICIAL")
    # Wrong sponsor for symbol.
    bad = dict(good, authority_source="BLACKROCK_ISHARES_OFFICIAL")
    with pytest.raises(DataContractError):
        CADetermination.from_dict(bad, "SPY", date(2026, 9, 29), now)
    # Wrong session.
    bad = dict(good, session="2026-09-30")
    with pytest.raises(DataContractError):
        CADetermination.from_dict(bad, "SPY", date(2026, 9, 29), now)
    # Malformed SHA.
    bad = dict(good, source_sha256="xyz")
    with pytest.raises(DataContractError):
        CADetermination.from_dict(bad, "SPY", date(2026, 9, 29), now)
    # Retrieval timestamp in the future relative to processing.
    bad = dict(good, retrieved_at_utc="2026-09-29T22:00:00+00:00")
    with pytest.raises(DataContractError):
        CADetermination.from_dict(bad, "SPY", date(2026, 9, 29), now)
    # Naive timestamp.
    bad = dict(good, retrieved_at_utc="2026-09-29T21:00:00")
    with pytest.raises(DataContractError):
        CADetermination.from_dict(bad, "SPY", date(2026, 9, 29), now)


def test_initial_state_rejects_nonpristine() -> None:
    state = build_initial_state()
    bad = dict(state, observed_session_count=1)
    with pytest.raises(DataContractError):
        validate_initial_state(bad)
    bad = dict(state, hypothesis_id="HYP_009")
    with pytest.raises(DataContractError):
        validate_initial_state(bad)
    tampered = dict(state["strategy"], cash="99999.99")
    bad = dict(state, strategy=tampered)
    with pytest.raises(DataContractError):
        validate_initial_state(bad)
    bad = dict(state, locks=dict(state["locks"], no_real_orders=False))
    with pytest.raises(DataContractError):
        validate_initial_state(bad)
