"""Unit, boundary, and adversarial regression tests for Lane B Candidate Evaluator.

Verifies strict compliance with:
- docs/research/LANE_B_SPEC_OFFLINE_QUALIFICATION.md
- AGENTS.md Section 1 (Strict Fail-Closed Contract, Literature & Unit Discipline)
- V13 Primary-Source Integrity Recovery Invariants
"""

from datetime import date
from decimal import Decimal
import dataclasses
import json
from pathlib import Path
from typing import Any, Optional
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_b_candidate_evaluator import (
    LaneBCandidateEvaluator,
    LaneBCandidateEvent,
    LaneBCandidateEvaluationResult,
)


def _sample_valid_event(
    symbol: str = "VOO",
    amount: str = "1.822600",
    ex_date: date = date(2026, 9, 28),
    record_date: Optional[date] = None,
    payable_date: Optional[date] = None,
    authority_class: str = "ISSUER_OFFICIAL_TABLE",
    source_url: Optional[str] = None,
    source_document: str = "Official Distribution Table",
    confirmation_status: str = "SOURCE_CONFIRMED_CANDIDATE",
    event_type: str = "INCOME_DISTRIBUTION",
    fund_legal_identity: Optional[str] = None,
    source_row_ref: str = "issuer_row:test-fixture",
) -> LaneBCandidateEvent:
    rec_d = record_date if record_date is not None else ex_date
    pay_d = payable_date if payable_date is not None else rec_d
    fund_map = {
        "VOO": "Vanguard Index Funds",
        "BND": "Vanguard Bond Index Funds",
        "BIL": "SPDR Series Trust",
        "GLD": "SPDR Gold Trust",
    }
    url_map = {
        "VOO": "https://www.vanguardoffshore.com/en/product/etf/equity/0968/vanguard-sp-500-etf",
        "BND": "https://advisors.vanguard.com/investments/products/bnd/vanguard-total-bond-market-etf",
        "BIL": "https://www.ssga.com/us/en/institutional/resources/documents/etf-dividend-distributions",
    }
    legal_id = fund_legal_identity or fund_map.get(symbol, "Vanguard Index Funds")
    src_url = source_url or url_map.get(symbol, "https://www.vanguard.com")

    return LaneBCandidateEvent(
        symbol=symbol,
        fund_legal_identity=legal_id,
        event_type=event_type,
        amount=Decimal(amount),
        currency="USD",
        ex_date=ex_date,
        record_date=rec_d,
        payable_date=pay_d,
        source_url=src_url,
        source_document=source_document,
        retrieval_status="VERIFIED_PRIMARY_SOURCE",
        authority_class=authority_class,
        confirmation_status=confirmation_status,
        source_row_ref=source_row_ref,
    )


def test_happy_path_candidate_panel_json_evaluates() -> None:
    """Verify that committed 2025-2026 JSON candidate panel parses and verifies cleanly."""
    json_path = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "research"
        / "lane_b_candidate_events_2025_2026.json"
    )
    assert json_path.exists(), f"Candidate JSON file not found at {json_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    events = [
        LaneBCandidateEvent.from_dict(ev)
        for ev in data["cash_distribution_events"]
    ]
    assert len(events) == 30, f"Expected exactly 30 cash events, got {len(events)}"

    evaluator = LaneBCandidateEvaluator()
    result = evaluator.evaluate_panel(events)

    # Every row is now bound to a captured issuer source; this is source verification
    # of event facts, not dataset admission or PIT-vintage qualification.
    assert result.status == "SOURCE_VERIFIED_CANDIDATE"
    assert result.total_events == 30
    assert result.confirmed_events == 30
    assert result.partial_events == 0
    assert set(result.symbols_evaluated) == {"VOO", "BND", "BIL"}
    assert len(result.economic_composite_digest) == 64
    assert len(result.evidence_manifest_digest) == 64
    assert len(result.composite_digest) == 64


def test_verified_discrepancy_anchors_present_in_json() -> None:
    """Verify the specific primary-source anchors reconciled against Vanguard and SSGA records."""
    json_path = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "research"
        / "lane_b_candidate_events_2025_2026.json"
    )
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    events_by_key = {
        (ev["symbol"], ev["ex_date"]): ev
        for ev in data["cash_distribution_events"]
    }

    # VOO Q4 2025
    voo_q4_25 = events_by_key.get(("VOO", "2025-12-22"))
    assert voo_q4_25 is not None
    assert voo_q4_25["amount"] == "1.771000"
    assert voo_q4_25["payable_date"] == "2025-12-24"
    assert voo_q4_25["confirmation_status"] == "SOURCE_CONFIRMED_CANDIDATE"

    # VOO Q1 2026
    voo_q1_26 = events_by_key.get(("VOO", "2026-03-27"))
    assert voo_q1_26 is not None
    assert voo_q1_26["amount"] == "1.872400"
    assert voo_q1_26["payable_date"] == "2026-03-31"
    assert voo_q1_26["confirmation_status"] == "SOURCE_CONFIRMED_CANDIDATE"

    # VOO Q2 2026
    voo_q2_26 = events_by_key.get(("VOO", "2026-06-26"))
    assert voo_q2_26 is not None
    assert voo_q2_26["amount"] == "1.962200"
    assert voo_q2_26["payable_date"] == "2026-06-30"
    assert voo_q2_26["confirmation_status"] == "SOURCE_CONFIRMED_CANDIDATE"

    # BND 2025-12-18
    bnd_dec_25 = events_by_key.get(("BND", "2025-12-18"))
    assert bnd_dec_25 is not None
    assert bnd_dec_25["amount"] == "0.246638"
    assert bnd_dec_25["payable_date"] == "2025-12-22"
    assert bnd_dec_25["confirmation_status"] == "SOURCE_CONFIRMED_CANDIDATE"

    # BND 2026-07-01
    bnd_jul_26 = events_by_key.get(("BND", "2026-07-01"))
    assert bnd_jul_26 is not None
    assert bnd_jul_26["amount"] == "0.244470"
    assert bnd_jul_26["payable_date"] == "2026-07-06"
    assert bnd_jul_26["confirmation_status"] == "SOURCE_CONFIRMED_CANDIDATE"

    # BND 2026-08-03
    bnd_aug_26 = events_by_key.get(("BND", "2026-08-03"))
    assert bnd_aug_26 is not None
    assert bnd_aug_26["amount"] == "0.251550"
    assert bnd_aug_26["payable_date"] == "2026-08-05"
    assert bnd_aug_26["confirmation_status"] == "SOURCE_CONFIRMED_CANDIDATE"

    # BIL 2026-09-01
    bil_sep_26 = events_by_key.get(("BIL", "2026-09-01"))
    assert bil_sep_26 is not None
    assert bil_sep_26["amount"] == "0.279771"
    assert bil_sep_26["payable_date"] == "2026-09-04"
    assert bil_sep_26["confirmation_status"] == "SOURCE_CONFIRMED_CANDIDATE"


def test_bil_rows_bound_to_official_spdr_workbook() -> None:
    json_path = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "research"
        / "lane_b_candidate_events_2025_2026.json"
    )
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    by_key = {
        (ev["symbol"], ev["ex_date"]): ev for ev in data["cash_distribution_events"]
    }
    expected = {
        "2025-10-01": ("0.310508", "2025-10-06"),
        "2025-11-03": ("0.303301", "2025-11-06"),
        "2025-12-01": ("0.281225", "2025-12-04"),
        "2025-12-18": ("0.365425", "2025-12-23"),
        "2026-02-02": ("0.273931", "2026-02-05"),
        "2026-03-02": ("0.243106", "2026-03-05"),
        "2026-04-01": ("0.263657", "2026-04-06"),
        "2026-05-01": ("0.269910", "2026-05-06"),
        "2026-06-01": ("0.269202", "2026-06-04"),
        "2026-07-01": ("0.267622", "2026-07-07"),
        "2026-08-03": ("0.272951", "2026-08-06"),
    }
    for ex_date, (amount, payable) in expected.items():
        row = by_key[("BIL", ex_date)]
        assert row["amount"] == amount, ex_date
        assert row["payable_date"] == payable, ex_date
        assert row["confirmation_status"] == "SOURCE_CONFIRMED_CANDIDATE", ex_date
        assert row["source_row_ref"].startswith(
            "spdr_historical_distributions_xlsx:"
        ), ex_date
    assert ("BIL", "2025-12-19") not in by_key
    bil_partial = [
        e
        for e in data["cash_distribution_events"]
        if e["symbol"] == "BIL" and e["confirmation_status"] == "SOURCE_PARTIAL"
    ]
    assert bil_partial == []


def test_source_partial_cannot_become_source_verified() -> None:
    """SOURCE_PARTIAL status must result in CANDIDATE_STRUCTURE_VALIDATED, never SOURCE_VERIFIED."""
    evaluator = LaneBCandidateEvaluator()

    ev_confirmed = _sample_valid_event(
        symbol="VOO", confirmation_status="SOURCE_CONFIRMED_CANDIDATE"
    )
    res_confirmed = evaluator.evaluate_panel([ev_confirmed])
    assert res_confirmed.status == "SOURCE_VERIFIED_CANDIDATE"
    assert res_confirmed.confirmed_events == 1
    assert res_confirmed.partial_events == 0

    ev_partial = _sample_valid_event(
        symbol="VOO", confirmation_status="SOURCE_PARTIAL"
    )
    res_partial = evaluator.evaluate_panel([ev_partial])
    assert res_partial.status == "CANDIDATE_STRUCTURE_VALIDATED"
    assert res_partial.confirmed_events == 0
    assert res_partial.partial_events == 1


def test_unauthorized_source_domain_rejected() -> None:
    """Source URL must originate from an authorized issuer domain."""
    evaluator = LaneBCandidateEvaluator()
    unauthorized_event = _sample_valid_event(
        source_url="https://random-aggregator.com/dividends/voo"
    )
    with pytest.raises(DataContractError, match="authorized issuer domain"):
        evaluator.evaluate_panel([unauthorized_event])


def test_identical_duplicate_rejected() -> None:
    """Identical duplicate rows must be rejected to prevent silent count/digest inflation."""
    evaluator = LaneBCandidateEvaluator()
    ev1 = _sample_valid_event(symbol="VOO", ex_date=date(2026, 9, 28))
    ev2 = _sample_valid_event(symbol="VOO", ex_date=date(2026, 9, 28))

    with pytest.raises(DataContractError, match="Duplicate identical event"):
        evaluator.evaluate_panel([ev1, ev2])


def test_contradictory_duplicate_rejected() -> None:
    """Duplicate ex_dates with conflicting dollar amounts must be quarantined and rejected."""
    evaluator = LaneBCandidateEvaluator()
    ev1 = _sample_valid_event(symbol="VOO", amount="1.822600")
    ev2 = _sample_valid_event(symbol="VOO", amount="1.950000")

    with pytest.raises(DataContractError, match="Contradictory duplicate event"):
        evaluator.evaluate_panel([ev1, ev2])


def test_disallowed_event_type_rejected() -> None:
    """Non-income distribution events (e.g. Return of Capital) are disallowed."""
    evaluator = LaneBCandidateEvaluator()
    ev = _sample_valid_event(event_type="RETURN_OF_CAPITAL")

    with pytest.raises(DataContractError, match="Disallowed event type"):
        evaluator.evaluate_panel([ev])


def test_mismatched_fund_legal_identity_rejected() -> None:
    """Mismatch between symbol and expected fund legal identity is rejected."""
    evaluator = LaneBCandidateEvaluator()
    ev = _sample_valid_event(symbol="VOO", fund_legal_identity="SPDR Series Trust")

    with pytest.raises(DataContractError, match="Fund legal identity mismatch"):
        evaluator.evaluate_panel([ev])


def test_dual_digest_divergence_on_provenance_tampering() -> None:
    """Economic digest remains unchanged while evidence digest updates on provenance alteration."""
    evaluator = LaneBCandidateEvaluator()
    ev1 = _sample_valid_event(
        symbol="VOO",
        source_document="Vanguard Official S&P 500 ETF Distributions",
        confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
    )
    ev2 = _sample_valid_event(
        symbol="VOO",
        source_document="Vanguard Revised 2026 Distribution Release",
        confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
    )

    res1 = evaluator.evaluate_panel([ev1])
    res2 = evaluator.evaluate_panel([ev2])

    # Economic digest depends solely on economic attributes: must match
    assert res1.economic_composite_digest == res2.economic_composite_digest
    # Evidence manifest digest includes provenance/source documents: must diverge
    assert res1.evidence_manifest_digest != res2.evidence_manifest_digest


def test_gld_cash_dividend_strictly_rejected() -> None:
    """GLD is a physical grantor trust; cash dividend events must be rejected fail-closed."""
    evaluator = LaneBCandidateEvaluator()
    gld_event = _sample_valid_event(symbol="GLD", amount="0.00")

    with pytest.raises(DataContractError, match="NO_CASH_DISTRIBUTION_ENTITLEMENT"):
        evaluator.evaluate_panel([gld_event])


def test_unknown_basis_authority_rejected() -> None:
    """Records without authorized issuer authority must be rejected fail-closed."""
    evaluator = LaneBCandidateEvaluator()
    event = _sample_valid_event(authority_class="UNKNOWN_BASIS")

    with pytest.raises(DataContractError, match="invalid authority class 'UNKNOWN_BASIS'"):
        evaluator.evaluate_panel([event])


def test_negative_or_zero_amount_rejected() -> None:
    """Zero or negative dividend amounts are invalid for declared distribution events."""
    evaluator = LaneBCandidateEvaluator()

    with pytest.raises(DataContractError, match="must be positive"):
        event_neg = _sample_valid_event(amount="-1.50")
        evaluator.evaluate_panel([event_neg])

    with pytest.raises(DataContractError, match="must be positive"):
        event_zero = _sample_valid_event(amount="0.00")
        evaluator.evaluate_panel([event_zero])


def test_non_usd_currency_rejected() -> None:
    """Only USD distributions are supported in Lane A/B universe."""
    evaluator = LaneBCandidateEvaluator()
    event_eur = _sample_valid_event(symbol="VOO")
    # Manually bypass _sample_valid_event default
    event_eur = LaneBCandidateEvent(
        symbol="VOO",
        fund_legal_identity="Vanguard Index Funds",
        event_type="INCOME_DISTRIBUTION",
        amount=Decimal("1.80"),
        currency="EUR",
        ex_date=date(2026, 9, 28),
        record_date=date(2026, 9, 28),
        payable_date=date(2026, 9, 30),
        source_url="https://www.vanguard.com",
        source_document="Vanguard Distributions",
        retrieval_status="VERIFIED_PRIMARY_SOURCE",
        authority_class="ISSUER_OFFICIAL_TABLE",
        confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
    )
    with pytest.raises(DataContractError, match="Unsupported distribution currency 'EUR'"):
        evaluator.evaluate_panel([event_eur])


def test_date_inversion_rejected() -> None:
    """Date ordering invariant ex_date <= record_date <= payable_date must hold."""
    evaluator = LaneBCandidateEvaluator()

    # Record date before ex date
    event_rec_before_ex = _sample_valid_event(
        ex_date=date(2026, 9, 28),
        record_date=date(2026, 9, 27),
        payable_date=date(2026, 9, 30),
    )
    with pytest.raises(DataContractError, match="record_date 2026-09-27 precedes ex_date"):
        evaluator.evaluate_panel([event_rec_before_ex])

    # Payable date before record date
    event_pay_before_rec = _sample_valid_event(
        ex_date=date(2026, 9, 28),
        record_date=date(2026, 9, 28),
        payable_date=date(2026, 9, 25),
    )
    with pytest.raises(DataContractError, match="payable_date 2026-09-25 precedes record_date"):
        evaluator.evaluate_panel([event_pay_before_rec])


def test_deterministic_digest_permutation_invariance() -> None:
    """Panel ordering must not alter the resulting framed composite digest."""
    evaluator = LaneBCandidateEvaluator()
    ev1 = _sample_valid_event(symbol="VOO", ex_date=date(2026, 9, 28))
    ev2 = _sample_valid_event(
        symbol="BND",
        ex_date=date(2026, 9, 1),
        payable_date=date(2026, 9, 3),
        source_url="https://advisors.vanguard.com/investments/products/bnd/vanguard-total-bond-market-etf",
    )

    res_1 = evaluator.evaluate_panel([ev1, ev2])
    res_2 = evaluator.evaluate_panel([ev2, ev1])

    assert res_1.economic_composite_digest == res_2.economic_composite_digest
    assert res_1.evidence_manifest_digest == res_2.evidence_manifest_digest
    assert res_1.composite_digest == res_2.composite_digest


def test_empty_panel_raises() -> None:
    """Empty candidate panel is rejected fail-closed."""
    evaluator = LaneBCandidateEvaluator()
    with pytest.raises(DataContractError, match="must not be empty"):
        evaluator.evaluate_panel([])


def _event_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "symbol": "VOO",
        "fund_legal_identity": "Vanguard Index Funds",
        "cusip": "922908363",
        "event_type": "INCOME_DISTRIBUTION",
        "amount": "1.822600",
        "currency": "USD",
        "ex_date": "2026-09-28",
        "record_date": "2026-09-28",
        "payable_date": "2026-09-30",
        "source_url": (
            "https://advisors.vanguard.com/investments/products/voo/"
            "vanguard-sp-500-etf"
        ),
        "source_document": "Vanguard Official Distribution History",
        "retrieval_status": "UNVERIFIED_CAPTURE_TIME",
        "authority_class": "ISSUER_OFFICIAL_TABLE",
    }
    base.update(overrides)
    return base


def test_from_dict_missing_confirmation_is_partial_not_confirmed() -> None:
    """Omitting confirmation_status must NEVER yield a confirmed outcome."""
    ev = LaneBCandidateEvent.from_dict(_event_dict())
    assert ev.confirmation_status == "SOURCE_PARTIAL"
    res = LaneBCandidateEvaluator().evaluate_panel([ev])
    assert res.confirmed_events == 0
    assert res.partial_events == 1
    assert res.status == "CANDIDATE_STRUCTURE_VALIDATED"


def test_from_dict_unknown_confirmation_rejected() -> None:
    """An undefined confirmation value is malformed and fails closed."""
    with pytest.raises(DataContractError, match="Malformed confirmation_status"):
        LaneBCandidateEvent.from_dict(
            _event_dict(confirmation_status="TRUST_ME_BRO")
        )


def test_confirmed_without_row_binding_downgraded_to_partial() -> None:
    """A valid issuer domain is not evidence; confirmed needs a row reference."""
    evaluator = LaneBCandidateEvaluator()
    ev = _sample_valid_event(source_row_ref="")
    res = evaluator.evaluate_panel([ev])
    assert res.confirmed_events == 0
    assert res.partial_events == 1
    assert res.status == "CANDIDATE_STRUCTURE_VALIDATED"


@pytest.mark.parametrize(
    "url",
    [
        "http://advisors.vanguard.com/investments/products/voo",
        "https://user:pass@advisors.vanguard.com/investments/products/voo",
        "https://advisors.vanguard.com:8443/investments/products/voo",
        "https://vanguard.com.evil.example/voo",
        "https://notvanguard.com/voo",
    ],
)
def test_invalid_source_url_forms_rejected(url: str) -> None:
    """Scheme, userinfo, explicit port and lookalike hosts all fail closed."""
    evaluator = LaneBCandidateEvaluator()
    ev = _sample_valid_event(source_url=url)
    with pytest.raises(DataContractError):
        evaluator.evaluate_panel([ev])


@pytest.mark.parametrize(
    "field,value",
    [
        ("publication_date", "2026-09-29"),
        ("revision_status", "REVISED_2026_10_01"),
        ("retrieval_status", "UNVERIFIED_CAPTURE_TIME"),
        ("cusip", "000000000"),
        ("source_row_ref", "issuer_row:other"),
    ],
)
def test_evidence_digest_binds_provenance_fields(field: str, value: str) -> None:
    """Material provenance changes the evidence digest, never the economic one."""
    evaluator = LaneBCandidateEvaluator()
    base = _sample_valid_event()
    replace_kwargs: dict[str, Any] = {field: value}
    variant = dataclasses.replace(base, **replace_kwargs)
    res_base = evaluator.evaluate_panel([base])
    res_variant = evaluator.evaluate_panel([variant])
    assert res_base.economic_composite_digest == res_variant.economic_composite_digest
    assert res_base.evidence_manifest_digest != res_variant.evidence_manifest_digest


def test_evidence_digest_delimiter_collision_impossible() -> None:
    """Naive '|' joins collide; canonical JSON keeps distinct rows distinct."""
    evaluator = LaneBCandidateEvaluator()
    ev_a = _sample_valid_event(source_document="A|B", source_row_ref="C")
    ev_b = _sample_valid_event(source_document="A", source_row_ref="B|C")
    res_a = evaluator.evaluate_panel([ev_a])
    res_b = evaluator.evaluate_panel([ev_b])
    assert res_a.economic_composite_digest == res_b.economic_composite_digest
    assert res_a.evidence_manifest_digest != res_b.evidence_manifest_digest


def test_bnd_rows_bound_to_issuer_distribution_table() -> None:
    """All BND candidates bind to the captured issuer table by record-date row."""
    json_path = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "research"
        / "lane_b_candidate_events_2025_2026.json"
    )
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    by_key = {(e["symbol"], e["ex_date"]): e for e in data["cash_distribution_events"]}
    expected = {
        "2025-10-01": ("0.237328", "2025-10-03"),
        "2025-11-03": ("0.243631", "2025-11-05"),
        "2025-12-01": ("0.238572", "2025-12-03"),
        "2026-02-02": ("0.245470", "2026-02-04"),
        "2026-03-02": ("0.227824", "2026-03-04"),
        "2026-04-01": ("0.250016", "2026-04-06"),
        "2026-05-01": ("0.241713", "2026-05-05"),
        "2026-06-01": ("0.247259", "2026-06-03"),
    }
    for ex_date, (amount, payable) in expected.items():
        row = by_key[("BND", ex_date)]
        assert row["amount"] == amount
        assert row["payable_date"] == payable
        assert row["record_date"] == ex_date
        assert row["confirmation_status"] == "SOURCE_CONFIRMED_CANDIDATE"
        assert row["retrieval_status"] == "CAPTURED_LIVE_ISSUER_TABLE_2026-10-22"
        assert row["source_row_ref"].startswith(
            "vanguard_bnd_distribution_history:recordDate="
        )
        assert row["source_url"] == (
            "https://investor.vanguard.com/investment-products/etfs/profile/bnd"
        )

    artifact = data["metadata"]["bnd_source_artifact"]
    assert artifact["sha256"] == (
        "d09560f58834be2b1297f782969410aba07adab08f1a537a366f3dcd916d3abd"
    )
    assert artifact["bytes"] == 226062
    assert artifact["publication_vintage"] == "UNKNOWN"
    assert artifact["revision_status"] == "REVISION_POLICY_UNVERIFIED"


def test_confirmed_rows_carry_source_row_binding() -> None:
    """Every SOURCE_CONFIRMED_CANDIDATE row in the panel has a row reference."""
    json_path = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "research"
        / "lane_b_candidate_events_2025_2026.json"
    )
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    confirmed = [
        e
        for e in data["cash_distribution_events"]
        if e["confirmation_status"] == "SOURCE_CONFIRMED_CANDIDATE"
    ]
    assert confirmed, "expected at least one confirmed candidate"
    for row in confirmed:
        assert row.get("source_row_ref", "").strip(), row


