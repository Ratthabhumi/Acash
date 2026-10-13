"""Adversarial + boundary tests for the offline Lane A authority, budget ledger, and dry run.

Attack order: happy path → boundary → malformed → contradictory → adversarial →
permutation → fail-closed. NETWORK_REQUESTS = 0 by construction: this module
imports nothing that opens a socket; the dry-run test asserts the result carries
network_requests_issued == 0.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Dict

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_authority import (
    LANE_A_MAX_HTTP_OPERATIONS,
    LANE_A_MAX_TOTAL_PAYLOAD_BYTES,
    LANE_A_SYMBOLS,
    LaneAAuthority,
    LaneAAuthorityError,
    LaneAAuthorityStatus,
    LaneARequestLedger,
    build_lane_a_scope,
    dry_run_validate,
    plan_lane_a_requests,
    redact_secrets,
    validate_authority,
    validate_planned_request,
    LaneAScope,
)

NOW = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
ISSUED_AT = datetime(2026, 10, 13, 0, 0, 0, tzinfo=timezone.utc)
EXPIRES_AT = datetime(2026, 10, 14, 0, 0, 0, tzinfo=timezone.utc)


def _authority(
    status: LaneAAuthorityStatus = LaneAAuthorityStatus.ISSUED,
    issued: datetime | None = ISSUED_AT,
    expires: datetime | None = EXPIRES_AT,
    max_ops: int = 12,
    max_bytes: int = LANE_A_MAX_TOTAL_PAYLOAD_BYTES,
    reference: str = "OP-APPROVAL-TEST-001",
) -> LaneAAuthority:
    return LaneAAuthority(
        status=status,
        scope=build_lane_a_scope(),
        max_http_operations=max_ops,
        max_total_payload_bytes=max_bytes,
        issued_at_utc=issued,
        expires_at_utc=expires,
        approval_reference=reference,
    )


class TestAuthorityValidation:
    def test_valid_authority_passes(self) -> None:
        assert validate_authority(_authority(), NOW) is not None

    def test_none_authority_fails_closed(self) -> None:
        with pytest.raises(LaneAAuthorityError):
            validate_authority(None, NOW)

    @pytest.mark.parametrize(
        "status",
        [LaneAAuthorityStatus.UNISSUED, LaneAAuthorityStatus.EXPIRED, LaneAAuthorityStatus.REVOKED],
    )
    def test_non_issued_status_fails_closed(self, status: LaneAAuthorityStatus) -> None:
        with pytest.raises(LaneAAuthorityError):
            validate_authority(_authority(status=status), NOW)

    def test_expired_authority_fails_closed(self) -> None:
        with pytest.raises(LaneAAuthorityError, match="expired"):
            validate_authority(_authority(expires=NOW - timedelta(seconds=1)), NOW)

    def test_not_yet_valid_authority_fails_closed(self) -> None:
        with pytest.raises(LaneAAuthorityError, match="not yet valid"):
            validate_authority(_authority(issued=NOW + timedelta(seconds=1)), NOW)

    def test_boundary_now_equals_expiry_is_expired(self) -> None:
        with pytest.raises(LaneAAuthorityError):
            validate_authority(_authority(expires=NOW), NOW)

    def test_boundary_now_equals_issue_is_valid(self) -> None:
        validate_authority(_authority(issued=NOW, expires=NOW + timedelta(hours=1)), NOW)

    def test_issued_after_expires_contradictory(self) -> None:
        with pytest.raises(LaneAAuthorityError, match="after expires_at_utc"):
            validate_authority(_authority(issued=EXPIRES_AT, expires=ISSUED_AT), NOW)

    def test_naive_now_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="timezone-aware"):
            validate_authority(_authority(), datetime(2026, 10, 13, 12, 0, 0))

    def test_empty_approval_reference_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="approval_reference"):
            _authority(reference="   ")

    def test_ops_above_lane_cap_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="exceeds the Lane A cap"):
            _authority(max_ops=LANE_A_MAX_HTTP_OPERATIONS + 1)

    def test_bytes_above_lane_cap_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="exceeds the Lane A cap"):
            _authority(max_bytes=LANE_A_MAX_TOTAL_PAYLOAD_BYTES + 1)


class TestScopeValidation:
    def test_universe_is_exact(self) -> None:
        assert LANE_A_SYMBOLS == frozenset({"VOO", "BND", "GLD", "BIL"})

    def _scope(self, **overrides: object) -> LaneAScope:
        base: Dict[str, object] = {
            "symbols": LANE_A_SYMBOLS,
            "timeframe": "1Day",
            "start_date": date(2026, 9, 28),
            "end_date": date(2026, 10, 2),
            "adjustments": frozenset({"raw", "all"}),
            "provider": "ALPACA",
            "paid_budget_usd": 0,
        }
        base.update(overrides)
        return LaneAScope(**base)  # type: ignore[arg-type]

    def test_scope_with_unknown_symbol_fails(self) -> None:
        with pytest.raises(DataContractError, match="outside the Lane A canary universe"):
            self._scope(symbols=frozenset({"SPY"}))

    def test_scope_with_wrong_window_fails(self) -> None:
        with pytest.raises(DataContractError, match="window must be exactly"):
            self._scope(end_date=date(2026, 10, 5))

    def test_scope_with_paid_budget_fails(self) -> None:
        with pytest.raises(DataContractError, match="paid_budget_usd"):
            self._scope(paid_budget_usd=99)

    def test_scope_with_empty_symbols_fails(self) -> None:
        with pytest.raises(DataContractError, match="non-empty"):
            self._scope(symbols=frozenset())


class TestRequestLedger:
    def test_record_within_budget(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=1000)
        ledger.record_operation("VOO", "raw", 400)
        ledger.record_operation("VOO", "all", 400)
        assert ledger.requests_issued == 2
        assert ledger.bytes_received == 800
        assert ledger.remaining_operations() == 10
        assert ledger.remaining_bytes() == 200

    def test_request_count_exhaustion_fails_closed(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=2, max_total_payload_bytes=10_000)
        ledger.record_operation("VOO", "raw", 10)
        ledger.record_operation("BND", "raw", 10)
        with pytest.raises(DataContractError, match="request-count budget exhausted"):
            ledger.record_operation("GLD", "raw", 10)

    def test_byte_budget_exhaustion_fails_closed(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=100)
        ledger.record_operation("VOO", "raw", 90)
        with pytest.raises(DataContractError, match="byte budget would be exceeded"):
            ledger.record_operation("BND", "raw", 20)
        assert ledger.requests_issued == 1
        assert ledger.bytes_received == 90

    def test_exact_byte_budget_boundary_admits_then_exhausts(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=100)
        ledger.record_operation("VOO", "raw", 100)
        assert ledger.remaining_bytes() == 0
        with pytest.raises(DataContractError):
            ledger.record_operation("BND", "raw", 1)

    def test_negative_payload_fails_closed(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=100)
        with pytest.raises(DataContractError, match="non-negative"):
            ledger.record_operation("VOO", "raw", -1)

    def test_rejected_record_does_not_consume_budget(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=100)
        with pytest.raises(DataContractError):
            ledger.record_operation("VOO", "raw", 500)
        assert ledger.requests_issued == 0
        assert ledger.bytes_received == 0


class TestPlanAndScopeBinding:
    def test_plan_is_deterministic_eight_operations(self) -> None:
        plan = plan_lane_a_requests(_authority())
        assert len(plan) == 8  # 4 symbols x 2 adjustments
        symbols = [r.symbol for r in plan]
        assert symbols == sorted(symbols)

    def test_plan_is_permutation_invariant(self) -> None:
        assert plan_lane_a_requests(_authority()) == plan_lane_a_requests(_authority())

    def test_plan_over_budget_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="refusing to expand scope"):
            plan_lane_a_requests(_authority(max_ops=4))

    def test_off_scope_symbol_rejected(self) -> None:
        authority = _authority()
        plan = plan_lane_a_requests(authority)
        drifted = plan[0].__class__(
            symbol="SPY",
            adjustment=plan[0].adjustment,
            timeframe=plan[0].timeframe,
            start_date=plan[0].start_date,
            end_date=plan[0].end_date,
            provider=plan[0].provider,
        )
        with pytest.raises(DataContractError, match="not in the authority scope"):
            validate_planned_request(authority, drifted)

    def test_off_scope_adjustment_rejected(self) -> None:
        authority = _authority()
        plan = plan_lane_a_requests(authority)
        drifted = plan[0].__class__(
            symbol=plan[0].symbol,
            adjustment="dividend",
            timeframe=plan[0].timeframe,
            start_date=plan[0].start_date,
            end_date=plan[0].end_date,
            provider=plan[0].provider,
        )
        with pytest.raises(DataContractError, match="adjustment"):
            validate_planned_request(authority, drifted)

    def test_off_scope_window_rejected(self) -> None:
        authority = _authority()
        plan = plan_lane_a_requests(authority)
        drifted = plan[0].__class__(
            symbol=plan[0].symbol,
            adjustment=plan[0].adjustment,
            timeframe=plan[0].timeframe,
            start_date=date(2026, 1, 1),
            end_date=plan[0].end_date,
            provider=plan[0].provider,
        )
        with pytest.raises(DataContractError, match="differs from authority scope"):
            validate_planned_request(authority, drifted)


class TestDryRun:
    def test_dry_run_issues_zero_network_requests(self) -> None:
        result = dry_run_validate(_authority(), NOW)
        assert result.network_requests_issued == 0
        assert result.planned_operations == 8

    def test_dry_run_rejects_unissued_authority(self) -> None:
        with pytest.raises(LaneAAuthorityError):
            dry_run_validate(_authority(status=LaneAAuthorityStatus.UNISSUED), NOW)

    def test_dry_run_rejects_none_authority(self) -> None:
        with pytest.raises(LaneAAuthorityError):
            dry_run_validate(None, NOW)


class TestRedaction:
    def test_redacts_alpaca_key_headers(self) -> None:
        text = "request failed: apca-api-key-id=AKIA123SECRET456 apca-api-secret-key=supersecretvalue"
        out = redact_secrets(text)
        assert "AKIA123SECRET456" not in out
        assert "supersecretvalue" not in out
        assert "[REDACTED]" in out

    def test_redacts_bearer_tokens(self) -> None:
        out = redact_secrets("Authorization: Bearer abcdef1234567890")
        assert "abcdef1234567890" not in out

    def test_plain_text_unchanged(self) -> None:
        assert redact_secrets("no secrets here") == "no secrets here"
