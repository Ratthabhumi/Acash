"""Unit tests for append-only decision ledger contract and correlation query."""

from datetime import datetime, timezone
import pytest

from acash.core.domain.audit import DecisionRecord
from acash.core.domain.exceptions import LedgerTamperError
from acash.storage.mock import InMemoryDecisionLedger


def test_append_only_decision_ledger(sample_time: datetime) -> None:
    ledger = InMemoryDecisionLedger()

    rec1 = DecisionRecord(
        decision_id="DEC_001",
        timestamp_utc=sample_time,
        inputs_snapshot_ref="snap_001",
        signal_ref="sig_001",
        target_allocation=None,
        risk_assessment=None,
        correlation_id="CORR_CYCLE_1",
        schema_version="1.0.0",
    )

    # 1. Append record
    did = ledger.append_decision(rec1)
    assert did == "DEC_001"
    assert ledger.get_decision("DEC_001") == rec1

    # 2. Tamper attempt: Overwriting existing decision_id raises LedgerTamperError
    rec_tamper = DecisionRecord(
        decision_id="DEC_001",
        timestamp_utc=sample_time,
        inputs_snapshot_ref="snap_tampered",
        signal_ref=None,
        target_allocation=None,
        risk_assessment=None,
        correlation_id="CORR_CYCLE_1",
        schema_version="1.0.0",
    )
    with pytest.raises(LedgerTamperError):
        ledger.append_decision(rec_tamper)

    # 3. Append multiple records with same correlation_id and reconstruct lifecycle
    rec2 = DecisionRecord(
        decision_id="DEC_002",
        timestamp_utc=sample_time,
        inputs_snapshot_ref="snap_002",
        signal_ref="sig_002",
        target_allocation=None,
        risk_assessment=None,
        correlation_id="CORR_CYCLE_1",
        schema_version="1.0.0",
    )
    ledger.append_decision(rec2)

    cycle_records = ledger.query_by_correlation_id("CORR_CYCLE_1")
    assert len(cycle_records) == 2
    assert cycle_records[0].decision_id == "DEC_001"
    assert cycle_records[1].decision_id == "DEC_002"
