"""ACASH Paper Trading — E3.5 Operational CLI tests.

Covers:
- Arg parsing for run/status/integrity subcommands
- `status` output against a real journal
- `integrity` PASS/FAIL against real and corrupted journals

GOVERNANCE (E3.5):
==================
- Real-feed bars are EXECUTION/PAPER INFRA ONLY, never research evidence.
- CLI has no LIVE mode; all runs are PAPER_ONLY by construction.
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from acash.paper.cli import (
    _status_session,
    _integrity_session,
    _review_session,
    main,
)
from acash.paper.runner import PaperSessionConfig, PaperSessionRunner, SyntheticBar
from acash.paper.strategy import InfrastructureTestStrategy


@pytest.fixture
def session_id() -> str:
    return f"TEST-CLI-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "paper_storage"


def write_runner_journal(storage_root: Path, session_id: str) -> None:
    journal_path = storage_root / f"{session_id}.journal.jsonl"
    config = PaperSessionConfig(
        session_id=session_id,
        strategy_id=InfrastructureTestStrategy.STRATEGY_ID,
        strategy_version=InfrastructureTestStrategy.STRATEGY_VERSION,
        instrument="SYNTH-USD",
        initial_cash=Decimal("100000"),
        max_position_units=Decimal("10"),
        max_notional=Decimal("500000"),
        max_daily_loss=Decimal("5000"),
        fill_slippage_bps=Decimal("0.5"),
        fill_commission_per_unit=Decimal("7.0"),
        prng_seed=42,
        git_commit="test-commit-abc123",
        component_version="0.1.0-test",
        journal_path=journal_path,
        snapshot_path=storage_root / f"{session_id}.snapshots.jsonl",
    )
    runner = PaperSessionRunner(config)
    runner.start()
    base = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
    for i in range(4):
        close = Decimal("100") + Decimal(i)
        runner.process_bar(
            SyntheticBar(
                timestamp_utc=base,
                symbol="SYNTH-USD",
                open=close - Decimal("1"),
                high=close + Decimal("1"),
                low=close - Decimal("2"),
                close=close,
                volume=Decimal("1000"),
            )
        )
    runner.stop()


class TestArgParsing:
    def test_run_requires_provider(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            main(["run", "--symbol", "BTCUSDT"])
        assert "provider" in capsys.readouterr().err

    def test_provider_choices(self) -> None:
        with pytest.raises(SystemExit):
            main(["run", "--provider", "fake", "--symbol", "X"])

    def test_help_is_zero(self) -> None:
        with pytest.raises(SystemExit) as excinfo:
            main(["--help"])
        assert excinfo.value.code == 0


class TestStatus:
    def test_status_against_real_journal(
        self, storage_root: Path, session_id: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        write_runner_journal(storage_root, session_id)
        ns = argparse.Namespace(session_id=session_id, storage=str(storage_root))
        _status_session(ns)
        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["session_id"] == session_id
        assert result["event_count"] > 0
        assert result["journal_integrity"] == "PASS"
        assert result["reconciliation_status"] in ("PASS", "CONSISTENT", "VIOLATIONS")


class TestIntegrity:
    def test_integrity_passes_clean_journal(
        self, storage_root: Path, session_id: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        write_runner_journal(storage_root, session_id)
        ns = argparse.Namespace(session_id=session_id, storage=str(storage_root))
        _integrity_session(ns)
        result = json.loads(capsys.readouterr().out)
        assert result["status"] == "PASS"
        assert result["violations"] == []

    def test_integrity_missing_journal_raises(
        self, storage_root: Path, session_id: str
    ) -> None:
        ns = argparse.Namespace(session_id=session_id, storage=str(storage_root))
        with pytest.raises(FileNotFoundError):
            _integrity_session(ns)

    def test_unknown_session_status_raises(
        self, storage_root: Path, session_id: str
    ) -> None:
        ns = argparse.Namespace(session_id="UNKNOWN", storage=str(storage_root))
        with pytest.raises(FileNotFoundError):
            _status_session(ns)


class TestReview:
    def test_review_builds_session_package(
        self, storage_root: Path, session_id: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        write_runner_journal(storage_root, session_id)
        ns = argparse.Namespace(session_id=session_id, storage=str(storage_root))
        _review_session(ns)
        result = json.loads(capsys.readouterr().out)
        assert result["session_id"] == session_id
        assert result["item_count"] >= 22
        assert "JOURNAL" in result["sections"]
        assert "FEED" in result["sections"]
        assert "PORTFOLIO" in result["sections"]
        assert "SESSION" in result["sections"]
        # Every item must carry a provenance label in OBSERVED/MODEL/DERIVED.
        for section, items in result["sections"].items():
            for item in items:
                assert item["provenance"] in ("OBSERVED", "MODEL", "DERIVED")

    def test_review_missing_manifest_raises(
        self, storage_root: Path, session_id: str
    ) -> None:
        journal_path = storage_root / f"{session_id}.journal.jsonl"
        config = PaperSessionConfig(
            session_id=session_id,
            strategy_id=InfrastructureTestStrategy.STRATEGY_ID,
            strategy_version=InfrastructureTestStrategy.STRATEGY_VERSION,
            instrument="SYNTH-USD",
            initial_cash=Decimal("100000"),
            max_position_units=Decimal("10"),
            max_notional=Decimal("500000"),
            max_daily_loss=Decimal("5000"),
            fill_slippage_bps=Decimal("0.5"),
            fill_commission_per_unit=Decimal("7.0"),
            prng_seed=42,
            git_commit="test-commit-abc123",
            component_version="0.1.0-test",
            journal_path=journal_path,
            snapshot_path=storage_root / f"{session_id}.snapshots.jsonl",
        )
        runner = PaperSessionRunner(config)
        runner.start()
        # No snapshot file exists yet -> review must fail-closed.
        ns = argparse.Namespace(session_id=session_id, storage=str(storage_root))
        with pytest.raises(FileNotFoundError):
            _review_session(ns)