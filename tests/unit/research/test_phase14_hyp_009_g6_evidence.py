"""Tests for evidence-derived G6 (no literal-True flags).

Builds ContractQualificationEvidence from measured values and proves each
independent corruption forces exactly its flag false (and G6 false).
"""

from datetime import date
from typing import Any, Dict, Tuple, cast
import dataclasses
import json
from pathlib import Path

import pytest

from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.hyp_009 import gates as GATES
from acash.research.hyp_009 import partitions as PART

REPO_ROOT = Path(__file__).resolve().parents[3]


def _m1_evidence() -> GATES.ContractQualificationEvidence:
    sessions = tuple(
        PART.expected_sessions(
            NyseCa1Calendar(), PART.AUTHORIZED_MIN_DATE, PART.AUTHORIZED_MAX_DATE
        )
    )
    assert len(sessions) == 1259
    return GATES.ContractQualificationEvidence(
        provider_contract_hash_recomputed=GATES.FROZEN_PROVIDER_CONTRACT_HASH,
        provider_contract_hash_authority=GATES.FROZEN_PROVIDER_CONTRACT_HASH,
        request_symbol="SPY",
        request_feed="sip",
        request_timeframe="1Day",
        request_start=PART.AUTHORIZED_MIN_DATE,
        request_end=PART.AUTHORIZED_MAX_DATE,
        partition="M1",
        expected_sessions=sessions,
        split_sessions=sessions,
        raw_sessions=sessions,
        dividend_validated_count=20,
        dividend_missing_payable_count=0,
        split_determination="NO_SPLIT_EVENTS_IN_AUTHORIZED_WINDOW",
        page_shas_recorded=("00fb4009a4c19f39f969a485a733b156eabf719cc44bc980de1282eb39be168c",),
        page_shas_recomputed=("00fb4009a4c19f39f969a485a733b156eabf719cc44bc980de1282eb39be168c",),
        sealed_hash_pairs=(("abc123", "abc123"),),
        forbidden_access_counts=(0, 0, 0, 0),
    )


def test_frozen_pins_match_r1_manifest() -> None:
    manifest = cast(
        Dict[str, Any],
        json.loads(
            (REPO_ROOT / "docs" / "phase14" / "manifests" / "manifest_r1_HYP_009.json").read_text(
                encoding="utf-8"
            )
        ),
    )
    assert GATES.FROZEN_PROVIDER_CONTRACT_HASH == (
        manifest["contract_hashes"]["provider_contract_hash"]
    )
    assert PART.M1_START == date(2016, 11, 1)
    assert PART.M1_END == date(2020, 12, 31)
    assert PART.M2_START == date(2021, 1, 1)
    assert PART.M2_END == date(2024, 12, 31)


def test_valid_evidence_derives_all_true() -> None:
    qual = GATES.derive_contract_qualification(_m1_evidence())
    assert qual.no_material_failure is True


def test_unknown_partition_rejected() -> None:
    import dataclasses as dc

    with pytest.raises(ValueError, match="UNKNOWN_PARTITION"):
        GATES.derive_contract_qualification(
            dc.replace(_m1_evidence(), partition="M9")
        )


def _corruptions() -> Dict[str, Dict[str, Any]]:
    sessions = _m1_evidence().expected_sessions
    shifted = sessions[1:] + (sessions[0],)
    return {
        "provider_contract_pass": {
            "provider_contract_hash_recomputed": "0" * 64,
        },
        "calendar_coverage_pass": {
            "split_sessions": shifted,
            "raw_sessions": shifted,
            "expected_sessions": sessions,
        },
        "split_raw_alignment_pass": {
            "raw_sessions": shifted,
        },
        "dividend_contract_pass": {
            "dividend_validated_count": 0,
        },
        "payable_date_contract_pass": {
            "dividend_missing_payable_count": 2,
        },
        "split_contract_pass": {
            "split_determination": "SOMETHING_ELSE",
        },
        "response_scope_pass": {
            "split_sessions": sessions + (date(2021, 1, 4),),
            "raw_sessions": sessions + (date(2021, 1, 4),),
            "expected_sessions": sessions + (date(2021, 1, 4),),
        },
        "provenance_hash_pass": {
            "page_shas_recomputed": ("ff" * 32,),
        },
        "serialization_integrity_pass": {
            "sealed_hash_pairs": (("pinned", "different"),),
        },
        "forbidden_partition_access_zero": {
            "forbidden_access_counts": (1, 0, 0, 0),
        },
    }


def test_each_corruption_forces_exactly_its_flag() -> None:
    base = _m1_evidence()
    flag_fields = [f.name for f in dataclasses.fields(GATES.ContractQualification)]
    assert len(flag_fields) == 10
    for flag, overrides in _corruptions().items():
        qual = GATES.derive_contract_qualification(
            dataclasses.replace(base, **cast(Any, overrides))
        )
        assert getattr(qual, flag) is False, flag
        assert qual.no_material_failure is False, flag
