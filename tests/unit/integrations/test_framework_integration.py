"""Framework adapters: contract, fail-closed behaviour and no execution authority."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.integrations import framework_integration as fi


def test_matrix_separates_code_from_native_and_qualification() -> None:
    matrix = fi.acceptance_matrix()
    ids = {row["framework_id"] for row in matrix["frameworks"]}
    assert ids == {"NAUTILUS_TRADER", "OPENBB", "TRADINGAGENTS", "FREQTRADE", "QUANTDINGER"}
    for row in matrix["frameworks"]:
        assert row["execution_authority"] == fi.NO_EXECUTION
        assert row["production_enabled"] is False
        assert row["input_rights_qualified"] is False
        assert row["pit_validated"] is False
        assert row["result_reconciled"] is False
        # Installed never implies executed or qualified.
        assert row["native_smoke_verified"] is False


def test_openbb_requires_pit_timestamps_and_source() -> None:
    adapter = fi.OpenBBAdapter()
    blocked = adapter.normalise_issuer_fact({"symbol": "VOO"})
    assert blocked.integration_status == "BLOCKED" and "OPENBB_EVIDENCE_INCOMPLETE" in str(blocked.blocked_reason)
    fact = {"symbol": "VOO", "concept": "net_assets", "value": "1000", "unit": "USD",
            "source_url": "https://example.invalid/filing", "published_at": "2026-01-02T00:00:00+00:00",
            "available_at": "2026-01-03T00:00:00+00:00", "provider": "SEC"}
    ok = adapter.normalise_issuer_fact(fact)
    assert ok.result_type == "FUNDAMENTAL_EVIDENCE" and ok.pit_qualified is True
    assert ok.rights == "READ_ONLY_DOCUMENTED_SOURCE" and ok.execution_authority == fi.NO_EXECUTION
    with pytest.raises(DataContractError, match="OPENBB_PIT_INVALID"):
        adapter.normalise_issuer_fact({**fact, "available_at": "2026-01-01T00:00:00+00:00"})


def test_tradingagents_packet_is_opinion_not_evidence() -> None:
    adapter = fi.TradingAgentsAdapter()
    packet = {"issuer": "VOO", "as_of": "2026-01-01T00:00:00+00:00", "thesis": "cost advantage",
              "citations": ["https://example.invalid/a"], "available_at": "2026-01-02T00:00:00+00:00"}
    result = adapter.validate_packet(packet)
    assert result.result_type == "EXTERNAL_RESEARCH_OPINION"
    assert result.pit_qualified is True and result.execution_authority == fi.NO_EXECUTION
    assert result.diagnostics["autonomous_research"] == "DISABLED"
    with pytest.raises(DataContractError, match="RESEARCH_PACKET_CITATIONS_REQUIRED"):
        adapter.validate_packet({**packet, "citations": []})
    blocked = adapter.validate_packet({"issuer": "VOO"})
    assert blocked.integration_status == "BLOCKED"


def test_freqtrade_artifact_is_synthetic_and_not_orders() -> None:
    adapter = fi.FreqtradeAdapter()
    assert str(adapter.import_backtest({}).blocked_reason).startswith("FREQTRADE_ARTIFACT_INCOMPLETE")
    artifact = {"strategy": "ExampleStrategy", "pairs": ["BTC/USDT"], "timerange": "20260101-20260201",
                "total_trades": 4, "profit_total": "0.02", "backtest_start": "2026-01-01"}
    result = adapter.import_backtest(artifact)
    assert result.rights == "SYNTHETIC_ONLY" and result.result_type == "EXTERNAL_ENGINE_RESULT"
    assert result.native_runtime == "SUBPROCESS_REQUIRED"
    assert "crypto-only" in result.limitations


def test_quantdinger_refuses_order_scope_and_reports_disconnected() -> None:
    adapter = fi.QuantDingerAdapter()
    assert adapter.read_result("/api/agent/v1/backtests/1").integration_status == "BLOCKED"
    assert adapter.read_result("/api/agent/v1/backtests/1").blocked_reason == "NATIVE_RUNTIME_NOT_CONNECTED"
    for path in ("/api/orders", "/api/runtime", "/api/agent/v1/orders", "/api/backtests/1"):
        with pytest.raises(DataContractError, match="QUANTDINGER_SCOPE_REFUSED"):
            adapter.read_result(path)
    payload = {"experiment_id": "exp-1", "metric": "sharpe", "value": "1.2"}
    connected = fi.QuantDingerAdapter(lambda path: payload).read_result("/api/agent/v1/experiments/exp-1")
    assert connected.result_type == "EXTERNAL_ENGINE_RESULT" and connected.native_runtime == "REMOTE_READ_ONLY"


def test_nautilus_adapter_never_claims_a_native_run() -> None:
    result = fi.NautilusAdapter().status()
    assert result.framework_id == "NAUTILUS_TRADER"
    assert result.execution_authority == fi.NO_EXECUTION
    if result.native_runtime == "NOT_INSTALLED":
        assert result.blocked_reason == "NAUTILUS_RUNTIME_NOT_INSTALLED"


def test_doctor_script_emits_the_same_matrix(tmp_path: Path) -> None:
    from subprocess import run, PIPE
    completed = run(["uv", "run", "python", "scripts/framework_doctor.py"], capture_output=True, text=True)
    assert completed.returncode == 0
    doc = json.loads(completed.stdout)
    assert doc["schema"] == fi.MATRIX_SCHEMA and len(doc["frameworks"]) == 5
    assert all(row["native_smoke_verified"] is False for row in doc["frameworks"])
