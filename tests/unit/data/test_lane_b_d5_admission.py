"""Adversarial tests for D5 real-input admission (no network, no authority)."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import MappingProxyType
from typing import Iterator, Sequence

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification import lane_b_d5_rehearsal
from acash.data.qualification.lane_a_d3_approval import InMemoryTrustRoot
from acash.data.qualification.lane_b_d5_rehearsal import (
    D5_ADMISSION_TRUST_ANCHORS,
    D5AdmissionAuthority,
    D5AdmissionKind,
    D5AdmissionResult,
    D5AdmissionVerdict,
    D5AuthorityProvenance,
    D5AuthorityStatus,
    D5DividendRecord,
    D5EvidenceAuthenticity,
    D5EvidenceEnvelope,
    D5EvidenceLevel,
    D5IndependentAdmissionRecord,
    D5InputOrigin,
    D5RawPage,
    D5RealInputBundle,
    D5RehearsalSpec,
    DatasetOrigin,
    evaluate_d5_offline_rehearsal,
    evaluate_d5_real_admission,
    expected_d5_request_sha256,
    sign_d5_admission_record,
    sign_d5_evidence_envelope,
    verify_sealed_dataset,
)
from acash.data.qualification.manifest import compute_page_sha256
from acash.execution.signing import Ed25519Signer

SESSIONS = tuple(
    date(2026, 9, 28) + timedelta(days=index) for index in range(5)
)
SYMBOLS = ("BIL", "BND", "GLD", "VOO")
NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
KEY_ID = "TEST_D5_EVIDENCE_KEY"
PRIVATE_KEY_B64, PUBLIC_KEY_B64 = Ed25519Signer.generate_key_pair()
PIT_SHA = "a" * 64
ADMIT_KEY_ID = "TEST_D5_ADMISSION_KEY"
ADMIT_PRIVATE_B64, ADMIT_PUBLIC_B64 = Ed25519Signer.generate_key_pair()


def _trust_root(*, revoked: bool = False) -> InMemoryTrustRoot:
    root = InMemoryTrustRoot()
    root.register(KEY_ID, PUBLIC_KEY_B64)
    if revoked:
        root.revoke(KEY_ID)
    return root


class _ProductionFlaggedRoot(InMemoryTrustRoot):
    """Attacker subclass advertising production trust (V24 admission oracle)."""

    @property
    def production_trusted(self) -> bool:
        return True


class _NoOpRoot:
    """Attacker root that accepts every signature and claims production trust."""

    production_trusted = True

    def verify_signature(self, **_: object) -> None:
        return None


@pytest.fixture
def anchored(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Pin the test admitter key, simulating a reviewed anchor provisioning change."""
    monkeypatch.setattr(
        lane_b_d5_rehearsal,
        "D5_ADMISSION_TRUST_ANCHORS",
        MappingProxyType({ADMIT_KEY_ID: ADMIT_PUBLIC_B64}),
    )
    yield


def _admitted(
    bundle: D5RealInputBundle,
    kind: D5AdmissionKind | None = None,
    *,
    private_key_b64: str = ADMIT_PRIVATE_B64,
    admitter_key_id: str = ADMIT_KEY_ID,
    acquisition_key_id: str = KEY_ID,
    acquisition_public_key_b64: str = PUBLIC_KEY_B64,
    admitted_at_utc: str = "2026-10-22T00:00:00+00:00",
) -> D5RealInputBundle:
    if kind is None:
        kind = (
            D5AdmissionKind.PIT_RESEARCH
            if bundle.claimed_level is D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED
            else D5AdmissionKind.RETROSPECTIVE_RESEARCH
        )
    record = D5IndependentAdmissionRecord(
        admission_ref="TEST_D5_ADMISSION_RECORD",
        kind=kind,
        evidence_scope_sha256=bundle.evidence_scope_sha256(),
        acquisition_key_id=acquisition_key_id,
        acquisition_public_key_b64=acquisition_public_key_b64,
        admitter_key_id=admitter_key_id,
        admitted_at_utc=admitted_at_utc,
    )
    return replace(
        bundle, admission_record=sign_d5_admission_record(record, private_key_b64)
    )


def _signed(
    bundle: D5RealInputBundle,
    *,
    private_key_b64: str = PRIVATE_KEY_B64,
    valid_until_utc: str = "2026-12-31T00:00:00+00:00",
    scope_sha256: str | None = None,
) -> D5RealInputBundle:
    authority = bundle.authority
    envelope = D5EvidenceEnvelope(
        key_id=KEY_ID,
        approval_ref=authority.approval_reference,
        authority_sha256=authority.digest(),
        evidence_scope_sha256=scope_sha256 or bundle.evidence_scope_sha256(),
        valid_from_utc="2026-10-20T00:00:00+00:00",
        valid_until_utc=valid_until_utc,
        max_http_requests=authority.max_http_requests,
        max_observed_bytes=authority.max_observed_bytes,
    )
    return replace(
        bundle,
        evidence_envelope=sign_d5_evidence_envelope(envelope, private_key_b64),
    )


def _admit(bundle: D5RealInputBundle, root: object | None = None) -> D5AdmissionResult:
    return evaluate_d5_real_admission(
        bundle,
        now_utc=NOW,
        trust_root=root if root is not None else _trust_root(),  # type: ignore[arg-type]
    )


def _authority(**overrides: object) -> D5AdmissionAuthority:
    base: dict[str, object] = {
        "status": D5AuthorityStatus.ISSUED,
        "provenance": D5AuthorityProvenance.OPERATOR_ISSUED,
        "authority_ref": "TEST_D5_REAL_INPUT_AUTHORITY",
        "provider": "ALPACA",
        "feed": "sip",
        "timeframe": "1Day",
        "symbols": SYMBOLS,
        "start_date": SESSIONS[0],
        "end_date": SESSIONS[-1],
        "adjustments": ("raw", "split"),
        "max_http_requests": 4,
        "max_observed_bytes": 100_000,
        "issued_at_utc": datetime(2026, 10, 20, tzinfo=timezone.utc),
        "expires_at_utc": datetime(2026, 12, 31, tzinfo=timezone.utc),
        "approval_reference": "TEST_APPROVAL_REFERENCE",
    }
    base.update(overrides)
    return D5AdmissionAuthority(**base)  # type: ignore[arg-type]


def _dividends(*, pit: bool) -> tuple[D5DividendRecord, ...]:
    return (
        D5DividendRecord(
            symbol="BIL",
            ex_date=date(2026, 10, 1),
            record_date=date(2026, 10, 1),
            payable_date=date(2026, 10, 5),
            amount_per_share=Decimal("0.228000"),
            confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
            source_row_ref="synthetic:bli:2026-10-01",
            pit_vintage_known=pit,
        ),
        D5DividendRecord(
            symbol="BND",
            ex_date=date(2026, 10, 1),
            record_date=date(2026, 10, 1),
            payable_date=date(2026, 10, 5),
            amount_per_share=Decimal("0.237328"),
            confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
            source_row_ref="synthetic:bnd:2026-10-01",
            pit_vintage_known=pit,
        ),
        D5DividendRecord(
            symbol="VOO",
            ex_date=date(2026, 9, 30),
            record_date=date(2026, 9, 30),
            payable_date=date(2026, 10, 2),
            amount_per_share=Decimal("1.740000"),
            confirmation_status="SOURCE_CONFIRMED_CANDIDATE",
            source_row_ref="synthetic:voo:2026-09-30",
            pit_vintage_known=pit,
        ),
    )


def _page(
    authority: D5AdmissionAuthority,
    adjustment: str,
    *,
    token: str | None = None,
    next_token: str | None = None,
    sessions: Sequence[date] = SESSIONS,
    symbols: Sequence[str] = SYMBOLS,
    close: str = "100",
    hour: int = 13,
    minute: int = 30,
) -> D5RawPage:
    bars = {
        symbol: [
            {
                "t": datetime(
                    day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc
                ).isoformat(),
                "o": close,
                "h": close,
                "l": close,
                "c": close,
                "v": 1000,
            }
            for day in sessions
        ]
        for symbol in symbols
    }
    raw = json.dumps(
        {"bars": bars, "next_page_token": next_token}, separators=(",", ":")
    ).encode("utf-8")
    return D5RawPage(
        adjustment=adjustment,
        page_index=0 if token is None else 1,
        page_token=token,
        next_page_token=next_token,
        request_sha256=expected_d5_request_sha256(authority, adjustment, token),
        content_sha256=compute_page_sha256(raw),
        raw_bytes=raw,
    )


def _pages(authority: D5AdmissionAuthority) -> tuple[D5RawPage, ...]:
    return (
        _page(authority, "raw"),
        _page(authority, "split"),
    )


def _bundle(
    *,
    claimed: D5EvidenceLevel = D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED,
    origin: D5InputOrigin = D5InputOrigin.OPERATOR_ACQUISITION,
    authority: D5AdmissionAuthority | None = None,
    pages: tuple[D5RawPage, ...] | None = None,
    dividends: tuple[D5DividendRecord, ...] | None = None,
    pit_vintage_known: bool = False,
    pit_evidence_ref: str = "",
    expected_dividends: tuple[D5DividendRecord, ...] | None = None,
) -> D5RealInputBundle:
    active_authority = authority or _authority()
    active_dividends = dividends if dividends is not None else _dividends(pit=False)
    return D5RealInputBundle(
        authority=active_authority,
        origin=origin,
        pages=pages if pages is not None else _pages(active_authority),
        dividends=active_dividends,
        expected_ex_dates={
            "BND": (date(2026, 10, 1),),
            "BIL": (date(2026, 10, 1),),
            "VOO": (date(2026, 9, 30),),
        },
        claimed_level=claimed,
        pit_vintage_known=pit_vintage_known,
        pit_evidence_ref=pit_evidence_ref,
        expected_dividends=expected_dividends,
    )


def _pit_bundle(**overrides: object) -> D5RealInputBundle:
    bundle = _bundle(
        claimed=D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED,
        dividends=_dividends(pit=True),
        pit_vintage_known=True,
        pit_evidence_ref="PIT_VINTAGE_ARCHIVE:test",
    )
    return replace(bundle, pit_evidence_sha256=PIT_SHA, **overrides)  # type: ignore[arg-type]


def test_signed_retrospective_bundle_seals_but_is_not_admitted() -> None:
    result = _admit(_signed(_bundle()))
    assert result.verdict is D5AdmissionVerdict.RETROSPECTIVE_ONLY
    assert result.admitted_level is D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED
    admission = result.manifest["admission"]
    assert admission["real_data_admitted"] is False
    assert admission["caller_verifier_accepted"] is True
    assert (
        admission["evidence_authenticity"]
        == D5EvidenceAuthenticity.CALLER_VERIFIER_ACCEPTED.value
    )
    assert admission["admission_kind"] is None
    assert "INDEPENDENT_ADMISSION_REQUIRED" in admission["limitations"]
    assert "NO_ANCHORED_ADMISSION_RECORD" in admission["limitations"]
    assert result.manifest["origin"] == DatasetOrigin.REAL_CANDIDATE.value
    assert result.dataset_bytes is not None
    verify_sealed_dataset(
        result.dataset_bytes,
        result.dataset_sha256 or "",
        result.composite_sha256 or "",
    )


def test_pit_claim_without_pit_evidence_blocks() -> None:
    result = evaluate_d5_real_admission(
        _bundle(claimed=D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PIT_EVIDENCE_QUALIFIED_REQUIRES_PIT_VINTAGE" in result.blockers[0]


def test_unsigned_issued_authority_cannot_seal_operator_data() -> None:
    """Fail-first 1/2: ISSUED + OPERATOR_ISSUED structural fields are not authority."""
    for bundle in (_bundle(), _pit_bundle()):
        result = evaluate_d5_real_admission(bundle, now_utc=NOW)
        assert result.verdict is D5AdmissionVerdict.BLOCKED
        assert "D5_EXTERNAL_EVIDENCE_PENDING" in result.blockers[0]
        assert result.dataset_bytes is None


def test_signed_envelope_without_trust_root_blocks() -> None:
    result = evaluate_d5_real_admission(_signed(_bundle()), now_utc=NOW)
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "no trust root supplied" in result.blockers[0]


def test_caller_pit_flags_do_not_produce_real_admission() -> None:
    """Fail-first 5/6: verified test-key PIT evidence is still not admission."""
    result = _admit(_signed(_pit_bundle()))
    assert result.verdict is D5AdmissionVerdict.INDEPENDENT_ADMISSION_REQUIRED
    assert result.admitted_level is D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED
    assert result.manifest["admission"]["real_data_admitted"] is False
    assert result.manifest["real_data_admitted"] is False
    assert result.manifest["origin"] == DatasetOrigin.REAL_CANDIDATE.value


def test_pit_claim_requires_bound_evidence_digest() -> None:
    bundle = replace(_pit_bundle(), pit_evidence_sha256="")
    result = _admit(_signed(bundle))
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PIT_EVIDENCE_QUALIFIED_REQUIRES_EVIDENCE_SHA256" in result.blockers[0]


def _assert_not_admitted(result: D5AdmissionResult) -> None:
    assert result.verdict is not D5AdmissionVerdict.ADMITTED
    assert result.verdict is not D5AdmissionVerdict.RETROSPECTIVE_ADMITTED
    assert result.manifest.get("real_data_admitted") is not True
    assert result.manifest.get("origin") != DatasetOrigin.REAL_ADMITTED.value


def test_caller_trust_root_objects_never_confer_admission() -> None:
    """V25-S01: fake, subclassed, or no-op roots cannot produce real admission."""
    subclassed = _ProductionFlaggedRoot()
    subclassed.register(KEY_ID, PUBLIC_KEY_B64)
    attacker_private, _ = Ed25519Signer.generate_key_pair()
    cases = (
        _admit(_signed(_pit_bundle()), subclassed),
        _admit(_signed(_pit_bundle()), _NoOpRoot()),
        _admit(_signed(_pit_bundle(), private_key_b64=attacker_private), _NoOpRoot()),
        _admit(_signed(_bundle()), _NoOpRoot()),
    )
    for result in cases:
        _assert_not_admitted(result)
        assert result.manifest["admission"]["admission_kind"] is None


def test_no_op_verifier_is_never_classified_independent() -> None:
    """V26-S02: caller acceptance is reported as caller acceptance only."""
    attacker_private, _ = Ed25519Signer.generate_key_pair()
    result = _admit(
        _signed(_bundle(), private_key_b64=attacker_private), _NoOpRoot()
    )
    admission = result.manifest["admission"]
    assert admission["caller_verifier_accepted"] is True
    assert (
        admission["evidence_authenticity"]
        == D5EvidenceAuthenticity.CALLER_VERIFIER_ACCEPTED.value
    )
    assert "independent_envelope_signature" not in result.checks
    synthetic = evaluate_d5_real_admission(
        _bundle(
            claimed=D5EvidenceLevel.SYNTHETIC_PIPELINE_PROOF,
            origin=D5InputOrigin.SYNTHETIC_FIXTURE,
            authority=_authority(provenance=D5AuthorityProvenance.TEST_FIXTURE),
            dividends=_dividends(pit=True),
            pit_vintage_known=True,
        ),
        now_utc=NOW,
    )
    assert (
        synthetic.manifest["admission"]["evidence_authenticity"]
        == D5EvidenceAuthenticity.NOT_APPLICABLE.value
    )


@pytest.mark.usefixtures("anchored")
def test_forged_envelope_under_no_op_verifier_cannot_use_anchored_record() -> None:
    """V26-S02 fail-first: V25 admitted a forged envelope when the caller verifier was a no-op."""
    attacker_private, _ = Ed25519Signer.generate_key_pair()
    forged = _admitted(_signed(_pit_bundle(), private_key_b64=attacker_private))
    result = _admit(forged, _NoOpRoot())
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D3_VERIFY_BAD_SIGNATURE" in result.blockers[0]


@pytest.mark.usefixtures("anchored")
def test_no_op_verifier_cannot_bypass_envelope_expiry() -> None:
    expired = _admitted(
        _signed(_pit_bundle(), valid_until_utc="2026-10-21T00:00:00+00:00"),
        admitted_at_utc="2026-10-20T12:00:00+00:00",
    )
    result = _admit(expired, _NoOpRoot())
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_ADMISSION_ENVELOPE_OUTSIDE_VALIDITY_AT_REVIEW" in result.blockers[0]


def test_trust_anchors_are_empty_by_default() -> None:
    """No production admission root is fabricated in the repository."""
    assert dict(D5_ADMISSION_TRUST_ANCHORS) == {}
    result = _admit(_admitted(_signed(_pit_bundle())), _NoOpRoot())
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_ADMISSION_UNANCHORED_KEY" in result.blockers[0]


@pytest.mark.usefixtures("anchored")
def test_anchored_pit_record_is_the_only_pit_admission_path() -> None:
    result = _admit(_admitted(_signed(_pit_bundle())))
    assert result.verdict is D5AdmissionVerdict.ADMITTED
    assert result.admitted_level is D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED
    admission = result.manifest["admission"]
    assert admission["real_data_admitted"] is True
    assert admission["admission_kind"] == D5AdmissionKind.PIT_RESEARCH.value
    assert (
        admission["evidence_authenticity"]
        == D5EvidenceAuthenticity.INDEPENDENTLY_VERIFIED.value
    )
    assert result.manifest["origin"] == DatasetOrigin.REAL_ADMITTED.value
    assert result.dataset_bytes is not None
    verify_sealed_dataset(
        result.dataset_bytes,
        result.dataset_sha256 or "",
        result.composite_sha256 or "",
    )


@pytest.mark.usefixtures("anchored")
def test_anchored_retrospective_record_stays_non_pit() -> None:
    """P1: retrospective admission is real but never PIT-labelled."""
    result = _admit(_admitted(_signed(_bundle())))
    assert result.verdict is D5AdmissionVerdict.RETROSPECTIVE_ADMITTED
    assert result.admitted_level is D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED
    admission = result.manifest["admission"]
    assert admission["real_data_admitted"] is True
    assert admission["admission_kind"] == D5AdmissionKind.RETROSPECTIVE_RESEARCH.value
    assert "NOT_POINT_IN_TIME" in admission["limitations"]


@pytest.mark.usefixtures("anchored")
def test_admission_kind_cannot_be_upgraded() -> None:
    cases = (
        _admit(_admitted(_signed(_pit_bundle()), D5AdmissionKind.RETROSPECTIVE_RESEARCH)),
        _admit(_admitted(_signed(_bundle()), D5AdmissionKind.PIT_RESEARCH)),
    )
    for result in cases:
        assert result.verdict is D5AdmissionVerdict.BLOCKED
        assert "D5_ADMISSION_KIND_MISMATCH" in result.blockers[0]
    retro = _admitted(_signed(_bundle()))
    upgraded = _signed(
        replace(
            retro,
            claimed_level=D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED,
            dividends=_dividends(pit=True),
            pit_vintage_known=True,
            pit_evidence_ref="PIT_VINTAGE_ARCHIVE:test",
            pit_evidence_sha256=PIT_SHA,
        )
    )
    result = _admit(upgraded)
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_ADMISSION_KIND_MISMATCH" in result.blockers[0]


@pytest.mark.usefixtures("anchored")
def test_attacker_keys_cannot_issue_admission() -> None:
    attacker_private, _ = Ed25519Signer.generate_key_pair()
    forged = _admit(_admitted(_signed(_pit_bundle()), private_key_b64=attacker_private))
    assert forged.verdict is D5AdmissionVerdict.BLOCKED
    assert "D3_VERIFY_BAD_SIGNATURE" in forged.blockers[0]
    self_signed = _admit(
        _admitted(
            _signed(_pit_bundle()),
            private_key_b64=attacker_private,
            admitter_key_id="ATTACKER_KEY",
        )
    )
    assert self_signed.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_ADMISSION_UNANCHORED_KEY" in self_signed.blockers[0]


@pytest.mark.usefixtures("anchored")
def test_resigned_envelope_cannot_reuse_admission_record() -> None:
    """Colluding acquisition re-signs a changed bundle; the record scope still binds."""
    admitted = _admitted(_signed(_pit_bundle()))
    authority = admitted.authority
    budget_authority = _authority(max_http_requests=8)
    variants: tuple[D5RealInputBundle, ...] = (
        replace(admitted, authority=budget_authority, pages=_pages(budget_authority)),
        replace(
            admitted,
            pages=(
                _page(authority, "raw", close="250"),
                _page(authority, "split", close="250"),
            ),
        ),
        replace(admitted, pit_evidence_sha256="c" * 64),
        replace(
            admitted,
            dividends=tuple(r for r in admitted.dividends if r.symbol != "VOO"),
            expected_ex_dates={
                k: v for k, v in admitted.expected_ex_dates.items() if k != "VOO"
            },
        ),
    )
    for variant in variants:
        result = _admit(_signed(variant))
        assert result.verdict is D5AdmissionVerdict.BLOCKED, result.blockers
        assert "D5_ADMISSION_RECORD_SCOPE_MISMATCH" in result.blockers[0]


@pytest.mark.usefixtures("anchored")
def test_replayed_admission_record_from_other_bundle_blocks() -> None:
    other_bundle = _bundle(
        claimed=D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED,
        authority=_authority(authority_ref="OTHER_RUN_AUTHORITY"),
        dividends=_dividends(pit=True),
        pit_vintage_known=True,
        pit_evidence_ref="PIT_VINTAGE_ARCHIVE:test",
    )
    other = _admitted(_signed(replace(other_bundle, pit_evidence_sha256=PIT_SHA)))
    assert _admit(other).verdict is D5AdmissionVerdict.ADMITTED
    target = replace(_signed(_pit_bundle()), admission_record=other.admission_record)
    result = _admit(target)
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_ADMISSION_RECORD_SCOPE_MISMATCH" in result.blockers[0]


def test_revoked_admitter_key_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Revocation is removal from the anchors; previously valid records stop admitting."""
    bundle = _admitted(_signed(_pit_bundle()))
    monkeypatch.setattr(
        lane_b_d5_rehearsal,
        "D5_ADMISSION_TRUST_ANCHORS",
        MappingProxyType({ADMIT_KEY_ID: ADMIT_PUBLIC_B64}),
    )
    assert _admit(bundle).verdict is D5AdmissionVerdict.ADMITTED
    monkeypatch.setattr(
        lane_b_d5_rehearsal, "D5_ADMISSION_TRUST_ANCHORS", MappingProxyType({})
    )
    result = _admit(bundle)
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_ADMISSION_UNANCHORED_KEY" in result.blockers[0]


@pytest.mark.usefixtures("anchored")
def test_acquisition_operator_cannot_admit_own_evidence() -> None:
    with pytest.raises(DataContractError, match="D5_ADMISSION_NOT_INDEPENDENT"):
        _admitted(_signed(_pit_bundle()), admitter_key_id=KEY_ID)
    bundle = _admitted(_signed(_pit_bundle()))
    assert bundle.admission_record is not None
    object.__setattr__(bundle.admission_record, "admitter_key_id", KEY_ID)
    result = _admit(bundle)
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_ADMISSION_NOT_INDEPENDENT" in result.blockers[0]
    mismatched = _admit(
        _admitted(_signed(_pit_bundle()), acquisition_key_id="OTHER_ACQUISITION_KEY")
    )
    assert mismatched.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_ADMISSION_RECORD_ACQUISITION_KEY_MISMATCH" in mismatched.blockers[0]


@pytest.mark.usefixtures("anchored")
def test_admission_record_temporal_policy() -> None:
    cases = (
        ("2026-10-24T00:00:00+00:00", "D5_ADMISSION_RECORD_FUTURE_DATED"),
        ("2026-10-19T00:00:00+00:00", "D5_ADMISSION_RECORD_PREDATES_EVIDENCE"),
    )
    for admitted_at, code in cases:
        result = _admit(_admitted(_signed(_pit_bundle()), admitted_at_utc=admitted_at))
        assert result.verdict is D5AdmissionVerdict.BLOCKED
        assert code in result.blockers[0]
    expired = _admitted(
        _signed(_pit_bundle(), valid_until_utc="2026-10-21T00:00:00+00:00"),
        admitted_at_utc="2026-10-20T12:00:00+00:00",
    )
    result = _admit(expired)
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D3_VERIFY_EXPIRED" in result.blockers[0]


def test_synthetic_pages_relabeled_as_operator_data_block() -> None:
    """Fail-first 3: relabeling origin after signing invalidates the scope."""
    synthetic = _bundle(
        origin=D5InputOrigin.SYNTHETIC_FIXTURE,
        claimed=D5EvidenceLevel.SYNTHETIC_PIPELINE_PROOF,
        authority=_authority(provenance=D5AuthorityProvenance.TEST_FIXTURE),
    )
    signed = _signed(synthetic)
    relabeled = replace(
        signed,
        origin=D5InputOrigin.OPERATOR_ACQUISITION,
        claimed_level=D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED,
        authority=_authority(),
    )
    result = _admit(relabeled)
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert result.dataset_bytes is None
    unsigned_relabel = replace(relabeled, evidence_envelope=None)
    unsigned_relabel = replace(
        unsigned_relabel, pages=_pages(unsigned_relabel.authority)
    )
    result = _admit(unsigned_relabel)
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_EXTERNAL_EVIDENCE_PENDING" in result.blockers[0]


def test_self_consistent_rehashed_fabricated_pages_block() -> None:
    """Fail-first 4: recomputed page hashes still change the signed scope."""
    authority = _authority()
    signed = _signed(_bundle(authority=authority))
    fabricated = (
        _page(authority, "raw", close="250"),
        _page(authority, "split", close="250"),
    )
    result = _admit(replace(signed, pages=fabricated))
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_EVIDENCE_ENVELOPE_SCOPE_MISMATCH" in result.blockers[0]


def test_post_signing_pit_upgrade_blocks() -> None:
    """Fail-first 6: flipping PIT flags after signing invalidates the scope."""
    signed = _signed(replace(_pit_bundle(), pit_vintage_known=False,
                             claimed_level=D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED))
    upgraded = replace(
        signed,
        pit_vintage_known=True,
        claimed_level=D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED,
    )
    result = _admit(upgraded)
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_EVIDENCE_ENVELOPE_SCOPE_MISMATCH" in result.blockers[0]


def test_post_signing_dividend_census_omission_blocks() -> None:
    """Fail-first 7: dropping an event from both lists after signing is detected."""
    signed = _signed(_bundle())
    omitted = replace(
        signed,
        dividends=tuple(r for r in signed.dividends if r.symbol != "VOO"),
        expected_ex_dates={
            key: value
            for key, value in signed.expected_ex_dates.items()
            if key != "VOO"
        },
    )
    result = _admit(omitted)
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_EVIDENCE_ENVELOPE_SCOPE_MISMATCH" in result.blockers[0]


def test_invalid_revoked_expired_or_mismatched_envelope_blocks() -> None:
    """Fail-first 8: bad signer, revoked key, expired window, wrong scope."""
    other_private, _ = Ed25519Signer.generate_key_pair()
    cases: list[tuple[D5AdmissionResult, str]] = [
        (_admit(_signed(_bundle(), private_key_b64=other_private)), "D3_VERIFY_BAD_SIGNATURE"),
        (_admit(_signed(_bundle()), _trust_root(revoked=True)), "D3_VERIFY_REVOKED_KEY"),
        (
            _admit(_signed(_bundle(), valid_until_utc="2026-10-21T00:00:00+00:00")),
            "D3_VERIFY_EXPIRED",
        ),
        (_admit(_signed(_bundle(), scope_sha256="b" * 64)), "D5_EVIDENCE_ENVELOPE_SCOPE_MISMATCH"),
    ]
    for result, code in cases:
        assert result.verdict is D5AdmissionVerdict.BLOCKED
        assert code in result.blockers[0]


def test_dataset_from_other_acquisition_run_blocks() -> None:
    """Fail-first 9: a valid envelope for another run cannot cover this bundle."""
    other = _authority(authority_ref="OTHER_RUN_AUTHORITY")
    other_signed = _signed(_bundle(authority=other))
    assert other_signed.evidence_envelope is not None
    target = replace(_bundle(), evidence_envelope=other_signed.evidence_envelope)
    result = _admit(target)
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_EVIDENCE_ENVELOPE_AUTHORITY_MISMATCH" in result.blockers[0]


@pytest.mark.usefixtures("anchored")
def test_no_path_upgrades_to_full_dataset_admitted() -> None:
    """Fail-first 10: even an anchored record cannot self-issue FULL_DATASET_ADMITTED."""
    bundle = _admitted(
        _signed(replace(_pit_bundle(), claimed_level=D5EvidenceLevel.FULL_DATASET_ADMITTED))
    )
    result = _admit(bundle, _NoOpRoot())
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_FULL_DATASET_ADMITTED_REQUIRES_SEPARATE_ADMISSION_RECORD" in result.blockers[0]
    for verdict_bundle in (_signed(_bundle()), _signed(_pit_bundle())):
        assert _admit(verdict_bundle).admitted_level is not D5EvidenceLevel.FULL_DATASET_ADMITTED


def test_synthetic_bundle_cannot_claim_real_evidence() -> None:
    authority = _authority(provenance=D5AuthorityProvenance.TEST_FIXTURE)
    result = evaluate_d5_real_admission(
        _bundle(
            claimed=D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED,
            origin=D5InputOrigin.SYNTHETIC_FIXTURE,
            authority=authority,
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_SYNTHETIC_INPUT_CANNOT_CLAIM_REAL_EVIDENCE" in result.blockers[0]


def test_synthetic_bundle_can_only_seal_pipeline_proof() -> None:
    authority = _authority(provenance=D5AuthorityProvenance.TEST_FIXTURE)
    records = _dividends(pit=True)
    result = evaluate_d5_real_admission(
        _bundle(
            claimed=D5EvidenceLevel.SYNTHETIC_PIPELINE_PROOF,
            origin=D5InputOrigin.SYNTHETIC_FIXTURE,
            authority=authority,
            dividends=records,
            pit_vintage_known=True,
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.SYNTHETIC_ONLY
    assert result.admitted_level is D5EvidenceLevel.SYNTHETIC_PIPELINE_PROOF
    assert result.manifest["admission"]["real_data_admitted"] is False


def test_synthetic_bundle_cannot_claim_retrospective_real_evidence() -> None:
    authority = _authority(provenance=D5AuthorityProvenance.TEST_FIXTURE)
    result = evaluate_d5_real_admission(
        _bundle(
            claimed=D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED,
            origin=D5InputOrigin.SYNTHETIC_FIXTURE,
            authority=authority,
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_SYNTHETIC_INPUT_CANNOT_CLAIM_REAL_EVIDENCE" in result.blockers[0]


def test_full_dataset_claim_requires_separate_record() -> None:
    result = evaluate_d5_real_admission(
        _bundle(claimed=D5EvidenceLevel.FULL_DATASET_ADMITTED),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_FULL_DATASET_ADMITTED_REQUIRES_SEPARATE_ADMISSION_RECORD" in (
        result.blockers[0]
    )


def test_source_verified_claim_is_not_d5_sealable() -> None:
    result = evaluate_d5_real_admission(
        _bundle(claimed=D5EvidenceLevel.SOURCE_VERIFIED_CANDIDATE),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_CLAIMED_LEVEL_NOT_SEALABLE" in result.blockers[0]


def test_unissued_or_expired_authority_blocks() -> None:
    for authority in (
        _authority(status=D5AuthorityStatus.UNISSUED),
        _authority(status=D5AuthorityStatus.REVOKED),
        _authority(
            issued_at_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
            expires_at_utc=datetime(2026, 2, 1, tzinfo=timezone.utc),
        ),
    ):
        result = evaluate_d5_real_admission(
            _bundle(authority=authority), now_utc=NOW
        )
        assert result.verdict is D5AdmissionVerdict.BLOCKED


def test_request_digest_tamper_blocks() -> None:
    authority = _authority()
    pages = list(_pages(authority))
    pages[0] = replace(pages[0], request_sha256="0" * 64)
    result = evaluate_d5_real_admission(
        _bundle(authority=authority, pages=tuple(pages)), now_utc=NOW
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PAGE_REQUEST_SHA_MISMATCH" in result.blockers[0]


def test_pages_cannot_be_reused_across_authorities() -> None:
    first = _authority()
    second = _authority(authority_ref="OTHER_D5_REAL_INPUT_AUTHORITY")
    result = evaluate_d5_real_admission(
        _bundle(authority=second, pages=_pages(first)), now_utc=NOW
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PAGE_REQUEST_SHA_MISMATCH" in result.blockers[0]


def test_content_digest_tamper_blocks() -> None:
    authority = _authority()
    pages = list(_pages(authority))
    pages[0] = replace(pages[0], raw_bytes=pages[0].raw_bytes + b" ")
    result = evaluate_d5_real_admission(
        _bundle(authority=authority, pages=tuple(pages)), now_utc=NOW
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PAGE_CONTENT_SHA_MISMATCH" in result.blockers[0]


def test_pagination_chain_and_replay_are_blocked() -> None:
    authority = _authority()
    first = _page(authority, "raw", sessions=SESSIONS[:2])
    second = _page(
        authority,
        "raw",
        token="next-1",
        sessions=SESSIONS[2:],
    )
    broken_first = replace(first, next_page_token="next-2")
    result = evaluate_d5_real_admission(
        _bundle(
            authority=authority,
            pages=(broken_first, second, _page(authority, "split")),
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PAGE" in result.blockers[0]


def test_missing_session_blocks() -> None:
    authority = _authority()
    result = evaluate_d5_real_admission(
        _bundle(
            authority=authority,
            pages=(
                _page(authority, "raw", sessions=SESSIONS[:-1]),
                _page(authority, "split", sessions=SESSIONS[:-1]),
            ),
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED


def test_mixed_symbol_page_blocks() -> None:
    authority = _authority()
    result = evaluate_d5_real_admission(
        _bundle(
            authority=authority,
            pages=(
                _page(authority, "raw", symbols=SYMBOLS + ("MSFT",)),
                _page(authority, "split"),
            ),
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "UNEXPECTED_SYMBOL" in result.blockers[0]


def test_out_of_scope_bar_blocks() -> None:
    authority = _authority()
    result = evaluate_d5_real_admission(
        _bundle(
            authority=authority,
            pages=(
                _page(
                    authority,
                    "raw",
                    sessions=SESSIONS + (date(2026, 10, 5),),
                ),
                _page(authority, "split"),
            ),
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PAGE_BAR_OUTSIDE_SCOPE" in result.blockers[0]


def test_utc_and_new_york_session_dates_must_agree() -> None:
    authority = _authority()
    result = evaluate_d5_real_admission(
        _bundle(
            authority=authority,
            pages=(
                _page(
                    authority,
                    "raw",
                    sessions=(SESSIONS[1],),
                    hour=0,
                    minute=30,
                ),
                _page(authority, "split"),
            ),
        ),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_BAR_UTC_NY_DATE_MISMATCH" in result.blockers[0]


def test_byte_and_page_budgets_block() -> None:
    authority = _authority(max_observed_bytes=10)
    result = evaluate_d5_real_admission(
        _bundle(authority=authority), now_utc=NOW
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_BYTE_BUDGET_EXCEEDED" in result.blockers[0]

    authority = _authority(max_http_requests=1)
    result = evaluate_d5_real_admission(
        _bundle(authority=authority), now_utc=NOW
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_PAGE_BUDGET_EXCEEDED" in result.blockers[0]


def test_dividend_input_must_match_expected() -> None:
    result = evaluate_d5_real_admission(
        _bundle(expected_dividends=()), now_utc=NOW
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_DIVIDEND_INPUT_DOES_NOT_MATCH_EXPECTED" in result.blockers[0]


def test_missing_adjustment_pages_block() -> None:
    authority = _authority()
    result = evaluate_d5_real_admission(
        _bundle(authority=authority, pages=(_page(authority, "raw"),)),
        now_utc=NOW,
    )
    assert result.verdict is D5AdmissionVerdict.BLOCKED
    assert "D5_MISSING_ADJUSTMENT_PAGES" in result.blockers[0]


def test_offline_rehearsal_refuses_real_admitted_origin() -> None:
    authority = _authority()
    result = evaluate_d5_offline_rehearsal(
        D5RehearsalSpec(
            origin=DatasetOrigin.REAL_ADMITTED,
            universe=authority.symbols,
            scope_start=authority.start_date,
            scope_end=authority.end_date,
            feed=authority.feed,
            timeframe=authority.timeframe,
            adjustment="raw",
            authority_ref=authority.authority_ref,
            expected_sessions=SESSIONS,
            split_bars={},
            raw_bars={},
        )
    )
    assert result.verdict.name == "BLOCKED"
    assert "REAL_ADMITTED_REQUIRES_D5_REAL_ADMISSION_BRIDGE" in result.blockers[0]
