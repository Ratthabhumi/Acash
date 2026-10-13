"""Adversarial + boundary tests for the offline Lane A authority, dispatch-reserve
request ledger, plan/query binding, and zero-network dry run.

Attack order: happy path -> boundary -> malformed -> contradictory -> adversarial ->
permutation -> fail-closed. NETWORK_REQUESTS = 0 by construction: this module
imports nothing that opens a socket; the dry-run test asserts the result carries
network_requests_issued == 0. All ledger scenarios are SYNTHETIC (fake dispatch
records only) — no HTTP, no provider API, no real transport.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from typing import Dict

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_authority import (
    LANE_A_CURRENCY,
    LANE_A_ENDPOINT_PATH,
    LANE_A_MAX_HTTP_OPERATIONS,
    LANE_A_MAX_TOTAL_PAYLOAD_BYTES,
    LANE_A_PAGE_LIMIT,
    LANE_A_SORT,
    LANE_A_SYMBOLS,
    LaneAAuthority,
    LaneAAuthorityError,
    LaneAAuthorityStatus,
    LaneAOperationState,
    LaneARequestLedger,
    LaneAScope,
    build_lane_a_scope,
    canonical_query_parameters,
    describe_approval_provenance,
    dry_run_validate,
    plan_lane_a_requests,
    redact_secrets,
    validate_authority,
    validate_planned_request,
)

NOW = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
APPROVED_AT = datetime(2026, 10, 13, 0, 0, 0, tzinfo=timezone.utc)
ISSUED_AT = datetime(2026, 10, 13, 0, 30, 0, tzinfo=timezone.utc)
EXPIRES_AT = datetime(2026, 10, 14, 0, 0, 0, tzinfo=timezone.utc)


def _authority(
    status: LaneAAuthorityStatus = LaneAAuthorityStatus.ISSUED,
    issued: datetime | None = ISSUED_AT,
    expires: datetime | None = EXPIRES_AT,
    approved: datetime | None = APPROVED_AT,
    max_ops: int = 12,
    max_bytes: int = LANE_A_MAX_TOTAL_PAYLOAD_BYTES,
    reference: str = "OP-APPROVAL-TEST-001",
    feed: str = "iex",
) -> LaneAAuthority:
    return LaneAAuthority(
        status=status,
        scope=build_lane_a_scope(feed),
        max_http_operations=max_ops,
        max_total_payload_bytes=max_bytes,
        issued_at_utc=issued,
        expires_at_utc=expires,
        approval_reference=reference,
        approved_at_utc=approved,
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

    def test_naive_issued_timestamp_rejected_at_construction(self) -> None:
        with pytest.raises(DataContractError, match="timezone-aware"):
            _authority(issued=datetime(2026, 10, 13, 0, 30, 0))

    def test_naive_expires_timestamp_rejected_at_construction(self) -> None:
        with pytest.raises(DataContractError, match="timezone-aware"):
            _authority(expires=datetime(2026, 10, 14, 0, 0, 0))

    def test_naive_approved_timestamp_rejected_at_construction(self) -> None:
        with pytest.raises(DataContractError, match="timezone-aware"):
            _authority(approved=datetime(2026, 10, 13, 0, 0, 0))

    def test_issued_without_approved_timestamp_rejected(self) -> None:
        with pytest.raises(DataContractError, match="approved_at_utc"):
            _authority(approved=None)

    def test_validity_start_backdated_before_approval_rejected(self) -> None:
        with pytest.raises(LaneAAuthorityError, match="precedes approved_at_utc"):
            validate_authority(_authority(issued=APPROVED_AT - timedelta(hours=1)), NOW)

    def test_empty_approval_reference_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="approval_reference"):
            _authority(reference="   ")

    def test_ops_above_lane_cap_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="exceeds the Lane A cap"):
            _authority(max_ops=LANE_A_MAX_HTTP_OPERATIONS + 1)

    def test_bytes_above_lane_cap_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="exceeds the Lane A cap"):
            _authority(max_bytes=LANE_A_MAX_TOTAL_PAYLOAD_BYTES + 1)


class TestApprovalProvenance:
    """Structural validation must never be misrepresented as human approval."""

    def test_provenance_is_structural_and_unverified(self) -> None:
        prov = describe_approval_provenance(_authority())
        assert prov.verification_level == "STRUCTURAL_FIELD_CHECKS_ONLY"
        assert prov.externally_verified is False
        assert prov.approval_reference == "OP-APPROVAL-TEST-001"
        assert prov.approved_at_utc == APPROVED_AT

    def test_provenance_for_missing_authority(self) -> None:
        prov = describe_approval_provenance(None)
        assert prov.externally_verified is False
        assert prov.approval_reference == ""
        assert prov.approved_at_utc is None

    def test_dry_run_result_carries_unverified_provenance(self) -> None:
        result = dry_run_validate(_authority(), NOW)
        assert result.network_requests_issued == 0
        assert result.approval_provenance.externally_verified is False
        assert result.approval_provenance.verification_level == "STRUCTURAL_FIELD_CHECKS_ONLY"


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
            "feed": "iex",
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

    def test_scope_with_unknown_feed_fails_closed(self) -> None:
        # boats/otc are in the official Alpaca enum but outside Lane A scope;
        # feed is never defaulted or silently widened.
        with pytest.raises(DataContractError, match="feed"):
            self._scope(feed="boats")

    def test_scope_with_sip_feed_allowed(self) -> None:
        assert self._scope(feed="sip").feed == "sip"


class TestRequestLedger:
    def test_dispatch_and_complete_within_budget(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=1000)
        rid1 = ledger.begin_dispatch("VOO,BND,GLD,BIL", "raw")
        ledger.complete_dispatch(rid1, 400)
        rid2 = ledger.begin_dispatch("VOO,BND,GLD,BIL", "all")
        ledger.complete_dispatch(rid2, 400)
        assert ledger.dispatched_attempts == 2
        assert ledger.bytes_received == 800
        assert ledger.remaining_operations() == 10
        assert ledger.remaining_bytes() == 200
        assert all(r.state is LaneAOperationState.COMPLETED for r in ledger.request_log)

    def test_request_count_exhaustion_fails_closed(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=2, max_total_payload_bytes=10_000)
        ledger.complete_dispatch(ledger.begin_dispatch("A", "raw"), 10)
        ledger.complete_dispatch(ledger.begin_dispatch("B", "raw"), 10)
        with pytest.raises(DataContractError, match="budget exhausted"):
            ledger.begin_dispatch("C", "raw")

    def test_repeated_failed_dispatches_cannot_bypass_cap(self) -> None:
        """P1 regression: failed/timed-out attempts must consume the cap too."""
        ledger = LaneARequestLedger(
            max_http_operations=LANE_A_MAX_HTTP_OPERATIONS,
            max_total_payload_bytes=100_000,
        )
        for _ in range(LANE_A_MAX_HTTP_OPERATIONS):
            rid = ledger.begin_dispatch("VOO,BND,GLD,BIL", "raw")
            ledger.fail_dispatch(rid, observed_bytes=64)
        assert ledger.dispatched_attempts == LANE_A_MAX_HTTP_OPERATIONS
        assert ledger.remaining_operations() == 0
        with pytest.raises(DataContractError, match="budget exhausted"):
            ledger.begin_dispatch("VOO,BND,GLD,BIL", "raw")

    def test_failed_dispatch_counts_attempt_and_observed_bytes(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=100)
        rid = ledger.begin_dispatch("VOO", "raw")
        ledger.fail_dispatch(rid, observed_bytes=60)
        assert ledger.dispatched_attempts == 1
        assert ledger.bytes_received == 60
        assert ledger.request_log[0].state is LaneAOperationState.FAILED
        assert ledger.request_log[0].bytes_observed == 60

    def test_timeout_without_bytes_still_consumes_operation(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=1, max_total_payload_bytes=100)
        rid = ledger.begin_dispatch("VOO", "raw")
        ledger.fail_dispatch(rid)  # timeout, zero bytes observed
        assert ledger.dispatched_attempts == 1
        with pytest.raises(DataContractError, match="budget exhausted"):
            ledger.begin_dispatch("BND", "raw")

    def test_duplicate_completion_is_rejected_without_double_counting(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=100)
        rid = ledger.begin_dispatch("VOO", "raw")
        ledger.complete_dispatch(rid, 10)
        with pytest.raises(DataContractError, match="single-use"):
            ledger.complete_dispatch(rid, 10)
        assert ledger.dispatched_attempts == 1
        assert ledger.bytes_received == 10

    def test_settle_after_settle_fail_is_rejected(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=100)
        rid = ledger.begin_dispatch("VOO", "raw")
        ledger.fail_dispatch(rid, observed_bytes=5)
        with pytest.raises(DataContractError, match="single-use"):
            ledger.complete_dispatch(rid, 5)

    def test_unknown_reservation_rejected(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=100)
        with pytest.raises(DataContractError, match="Unknown Lane A dispatch reservation"):
            ledger.complete_dispatch(999, 10)
        with pytest.raises(DataContractError, match="Unknown Lane A dispatch reservation"):
            ledger.fail_dispatch(999, 10)

    def test_byte_overrun_records_failure_terminates_ledger(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=100)
        rid = ledger.begin_dispatch("VOO", "raw")
        with pytest.raises(DataContractError, match="byte budget"):
            ledger.complete_dispatch(rid, 500)
        assert ledger.terminated is True
        assert ledger.dispatched_attempts == 1
        assert ledger.bytes_received == 0  # overrun bytes are evidence, not admitted budget
        record = ledger.request_log[0]
        assert record.state is LaneAOperationState.FAILED
        assert record.bytes_observed == 500
        with pytest.raises(DataContractError, match="TERMINATED"):
            ledger.begin_dispatch("BND", "raw")

    def test_exact_byte_budget_boundary_admits_then_exhausts(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=100)
        ledger.complete_dispatch(ledger.begin_dispatch("VOO", "raw"), 100)
        assert ledger.remaining_bytes() == 0
        rid = ledger.begin_dispatch("BND", "raw")
        with pytest.raises(DataContractError, match="byte budget"):
            ledger.complete_dispatch(rid, 1)
        assert ledger.terminated is True

    def test_negative_payload_rejected_and_reservation_survives(self) -> None:
        ledger = LaneARequestLedger(max_http_operations=12, max_total_payload_bytes=100)
        rid = ledger.begin_dispatch("VOO", "raw")
        with pytest.raises(DataContractError, match="non-negative"):
            ledger.complete_dispatch(rid, -1)
        # rejected settlement does not consume the single-use reservation
        ledger.complete_dispatch(rid, 10)
        assert ledger.bytes_received == 10
        assert ledger.dispatched_attempts == 1

    def test_ledger_is_not_crash_durable_by_contract(self) -> None:
        # Documented non-guarantee: state is in-process memory only. The public
        # API must stay pure in-memory (no persistence hooks that would imply
        # durability the contract does not provide).
        ledger = LaneARequestLedger(max_http_operations=1, max_total_payload_bytes=100)
        assert not hasattr(ledger, "persist")
        assert not hasattr(ledger, "load")
        ledger.begin_dispatch("VOO", "raw")
        assert "NOT persisted" in (LaneARequestLedger.__doc__ or "")


class TestPlanAndScopeBinding:
    def test_plan_is_two_multisymbol_operations(self) -> None:
        plan = plan_lane_a_requests(_authority())
        assert len(plan) == 2  # one multi-symbol request per adjustment
        adjustments = [r.adjustment for r in plan]
        assert adjustments == sorted(adjustments)
        for request in plan:
            assert request.symbols == ("BIL", "BND", "GLD", "VOO")
            assert request.endpoint_path == LANE_A_ENDPOINT_PATH
            assert request.feed == "iex"
            assert request.sort == LANE_A_SORT
            assert request.limit == LANE_A_PAGE_LIMIT
            assert request.currency == LANE_A_CURRENCY

    def test_plan_is_permutation_invariant(self) -> None:
        assert plan_lane_a_requests(_authority()) == plan_lane_a_requests(_authority())

    def test_plan_over_budget_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="refusing to expand scope"):
            plan_lane_a_requests(_authority(max_ops=1))

    def test_canonical_query_parameters_exact(self) -> None:
        request = plan_lane_a_requests(_authority())[0]
        params = dict(canonical_query_parameters(request))
        assert params == {
            "symbols": "BIL,BND,GLD,VOO",
            "timeframe": "1Day",
            "start": "2026-09-28",
            "end": "2026-10-02",
            "adjustment": request.adjustment,
            "feed": "iex",
            "sort": "asc",
            "limit": "1000",
            "currency": "USD",
        }

    def test_first_page_query_has_no_page_token(self) -> None:
        # Pagination is bound to echo this exact query + response next_page_token;
        # the first page never carries a cursor (no cursorless re-query either way).
        request = plan_lane_a_requests(_authority())[0]
        keys = [k for k, _ in canonical_query_parameters(request)]
        assert "page_token" not in keys
        assert len(keys) == 9

    def test_valid_plan_passes(self) -> None:
        authority = _authority()
        for request in plan_lane_a_requests(authority):
            validate_planned_request(authority, request)

    def test_off_scope_symbol_rejected(self) -> None:
        authority = _authority()
        drifted = replace(plan_lane_a_requests(authority)[0], symbols=("SPY",))
        with pytest.raises(DataContractError, match="canonical sorted order"):
            validate_planned_request(authority, drifted)

    def test_symbol_subset_rejected(self) -> None:
        authority = _authority()
        drifted = replace(plan_lane_a_requests(authority)[0], symbols=("VOO",))
        with pytest.raises(DataContractError, match="canonical sorted order"):
            validate_planned_request(authority, drifted)

    def test_unsorted_symbol_order_rejected(self) -> None:
        authority = _authority()
        drifted = replace(
            plan_lane_a_requests(authority)[0], symbols=("VOO", "GLD", "BND", "BIL")
        )
        with pytest.raises(DataContractError, match="canonical sorted order"):
            validate_planned_request(authority, drifted)

    def test_off_scope_adjustment_rejected(self) -> None:
        authority = _authority()
        drifted = replace(plan_lane_a_requests(authority)[0], adjustment="dividend")
        with pytest.raises(DataContractError, match="adjustment"):
            validate_planned_request(authority, drifted)

    def test_off_scope_window_rejected(self) -> None:
        authority = _authority()
        drifted = replace(
            plan_lane_a_requests(authority)[0], start_date=date(2026, 1, 1)
        )
        with pytest.raises(DataContractError, match="differs from authority scope"):
            validate_planned_request(authority, drifted)

    def test_wrong_endpoint_rejected(self) -> None:
        authority = _authority()
        drifted = replace(
            plan_lane_a_requests(authority)[0], endpoint_path="/v2/stocks/quotes"
        )
        with pytest.raises(DataContractError, match="endpoint"):
            validate_planned_request(authority, drifted)

    def test_wrong_feed_rejected_no_silent_fallback(self) -> None:
        authority = _authority()
        drifted = replace(plan_lane_a_requests(authority)[0], feed="sip")
        with pytest.raises(DataContractError, match="no silent feed fallback"):
            validate_planned_request(authority, drifted)

    def test_wrong_sort_rejected(self) -> None:
        authority = _authority()
        drifted = replace(plan_lane_a_requests(authority)[0], sort="desc")
        with pytest.raises(DataContractError, match="sort"):
            validate_planned_request(authority, drifted)

    def test_wrong_limit_rejected(self) -> None:
        authority = _authority()
        drifted = replace(plan_lane_a_requests(authority)[0], limit=10_000)
        with pytest.raises(DataContractError, match="limit"):
            validate_planned_request(authority, drifted)

    def test_wrong_currency_rejected(self) -> None:
        authority = _authority()
        drifted = replace(plan_lane_a_requests(authority)[0], currency="EUR")
        with pytest.raises(DataContractError, match="currency"):
            validate_planned_request(authority, drifted)


class TestDryRun:
    def test_dry_run_issues_zero_network_requests(self) -> None:
        result = dry_run_validate(_authority(), NOW)
        assert result.network_requests_issued == 0
        assert result.planned_operations == 2

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

    def test_redacts_json_quoted_header_values(self) -> None:
        # P2 regression: JSON-quoted header dicts previously escaped redaction.
        text = '{"apca-api-key-id": "AKIAJSONSECRET", "apca-api-secret-key": "jsonsecretvalue123"}'
        out = redact_secrets(text)
        assert "AKIAJSONSECRET" not in out
        assert "jsonsecretvalue123" not in out
        assert out.count("[REDACTED]") == 2

    def test_redacts_bearer_tokens(self) -> None:
        out = redact_secrets("Authorization: Bearer abcdef1234567890")
        assert "abcdef1234567890" not in out

    def test_redacts_bearer_in_json_quoted_authorization(self) -> None:
        text = '{"Authorization": "Bearer zzztopsecrettoken99"}'
        out = redact_secrets(text)
        assert "zzztopsecrettoken99" not in out

    def test_plain_text_unchanged(self) -> None:
        assert redact_secrets("no secrets here") == "no secrets here"






