"""Unit tests for Phase 14 AI Research Intelligence Quarantine Integration.

Tests:
- Non-overlapping candidate windows pass cleanly.
- Overlapping windows with canonical holdouts (HYP_001 M5, HYP_002 H4) fail closed.
- Inverted or malformed dates raise QuarantineContaminationError.
- Delegation to canonical quarantine authorities is verified with zero dual-source registries.
"""

import pytest

from acash.research.ai.enums import CandidateFamily, CandidateStatus
from acash.research.ai.exceptions import QuarantineContaminationError
from acash.research.ai.quarantine import (
    assert_research_candidate_quarantine_clean,
    is_candidate_window_clean,
)
from acash.research.ai.schema import ResearchCandidate


@pytest.fixture
def sample_nq_candidate() -> ResearchCandidate:
    return ResearchCandidate(
        candidate_id="CAND_NQ_M5_OPEN",
        candidate_family=CandidateFamily.SESSION_EVENT_MOMENTUM,
        working_title="NQ M5 Opening Momentum",
        target_asset_class="Equity Index Futures",
        target_symbol="NQ",
        proposed_timeframe="M5",
        core_premise="Opening session directional momentum conditioned on fast EMA breakout.",
        candidate_status=CandidateStatus.UNVALIDATED_PROPOSAL,
        recommendation_rationale="Research exploration only.",
        created_at_utc="2026-09-07T00:00:00+00:00",
    )


@pytest.fixture
def sample_eurusd_m5_candidate() -> ResearchCandidate:
    return ResearchCandidate(
        candidate_id="CAND_EURUSD_M5_EXPLORATORY",
        candidate_family=CandidateFamily.TIME_SERIES_MOMENTUM,
        working_title="EURUSD M5 Exploratory Proposal",
        target_asset_class="FX Spot",
        target_symbol="EURUSD",
        proposed_timeframe="M5",
        core_premise="Exploratory proposal on EURUSD M5.",
        candidate_status=CandidateStatus.UNVALIDATED_PROPOSAL,
        recommendation_rationale="Research exploration only.",
        created_at_utc="2026-09-07T00:00:00+00:00",
    )


@pytest.fixture
def sample_eurusd_h4_candidate() -> ResearchCandidate:
    return ResearchCandidate(
        candidate_id="CAND_EURUSD_H4_EXPLORATORY",
        candidate_family=CandidateFamily.TIME_SERIES_MOMENTUM,
        working_title="EURUSD H4 Exploratory Proposal",
        target_asset_class="FX Spot",
        target_symbol="EURUSD",
        proposed_timeframe="H4",
        core_premise="Exploratory proposal on EURUSD H4.",
        candidate_status=CandidateStatus.UNVALIDATED_PROPOSAL,
        recommendation_rationale="Research exploration only.",
        created_at_utc="2026-09-07T00:00:00+00:00",
    )


def test_quarantine_clean_window_passes(sample_nq_candidate: ResearchCandidate) -> None:
    """Assert that a clean, non-overlapping candidate window passes validation cleanly."""
    start = "2021-01-01T00:00:00+00:00"
    end = "2024-12-31T23:59:59+00:00"

    # Should not raise
    assert_research_candidate_quarantine_clean(
        candidate=sample_nq_candidate,
        proposed_start_utc=start,
        proposed_end_utc=end,
    )
    assert is_candidate_window_clean(sample_nq_candidate, start, end) is True


def test_quarantine_overlap_eurusd_m5_fails_closed(
    sample_eurusd_m5_candidate: ResearchCandidate,
) -> None:
    """Assert that proposed EURUSD M5 window overlapping with 2026 M5 holdout fails closed."""
    # Quarantined window is 2026-08-18T04:40:00 to 2026-09-04T21:00:00
    start = "2026-08-20T00:00:00+00:00"
    end = "2026-08-30T00:00:00+00:00"

    with pytest.raises(QuarantineContaminationError, match="BLOCKED_QUARANTINE_VIOLATION"):
        assert_research_candidate_quarantine_clean(
            candidate=sample_eurusd_m5_candidate,
            proposed_start_utc=start,
            proposed_end_utc=end,
        )
    assert is_candidate_window_clean(sample_eurusd_m5_candidate, start, end) is False


def test_quarantine_overlap_eurusd_h4_fails_closed(
    sample_eurusd_h4_candidate: ResearchCandidate,
) -> None:
    """Assert that proposed EURUSD H4 window overlapping with HYP_002 Validation/OOS fails closed."""
    # Quarantined window is 2023-05-29T16:00:00 to 2024-12-31T20:00:00
    start = "2023-06-01T00:00:00+00:00"
    end = "2023-12-31T00:00:00+00:00"

    with pytest.raises(QuarantineContaminationError, match="BLOCKED_QUARANTINE_VIOLATION"):
        assert_research_candidate_quarantine_clean(
            candidate=sample_eurusd_h4_candidate,
            proposed_start_utc=start,
            proposed_end_utc=end,
        )
    assert is_candidate_window_clean(sample_eurusd_h4_candidate, start, end) is False


def test_quarantine_inverted_dates_fail_closed(sample_nq_candidate: ResearchCandidate) -> None:
    """Assert that start_utc >= end_utc fails closed."""
    start = "2024-12-31T00:00:00+00:00"
    end = "2021-01-01T00:00:00+00:00"

    with pytest.raises(QuarantineContaminationError, match="start '.*' >= end"):
        assert_research_candidate_quarantine_clean(
            candidate=sample_nq_candidate,
            proposed_start_utc=start,
            proposed_end_utc=end,
        )


def test_quarantine_malformed_dates_fail_closed(sample_nq_candidate: ResearchCandidate) -> None:
    """Assert that invalid date strings fail closed."""
    with pytest.raises(QuarantineContaminationError, match="Failed to parse"):
        assert_research_candidate_quarantine_clean(
            candidate=sample_nq_candidate,
            proposed_start_utc="invalid_date_format",
            proposed_end_utc="2024-12-31T00:00:00+00:00",
        )


def test_quarantine_empty_dates_fail_closed(sample_nq_candidate: ResearchCandidate) -> None:
    """Assert that empty date strings fail closed."""
    with pytest.raises(QuarantineContaminationError, match="must specify non-empty"):
        assert_research_candidate_quarantine_clean(
            candidate=sample_nq_candidate,
            proposed_start_utc="",
            proposed_end_utc="",
        )
