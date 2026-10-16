"""D3-00 approval-envelope tests (OFFLINE ONLY — ephemeral test keys).

No production keys, no trust ceremony, no network. Proves the offline
verification LOGIC with generated throwaway key material.
"""

from __future__ import annotations

from typing import Any

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_d3_approval import (
    ApprovalEnvelope,
    EnvelopeApprovalCheck,
    InMemoryTrustRoot,
    admit_byte_population,
    sign_envelope,
)
from acash.execution.signing import Ed25519Signer

_NOW = "2026-10-16T12:00:00+00:00"


def _envelope(**overrides: object) -> ApprovalEnvelope:
    params = {
        "key_id": "test-key-001",
        "approval_ref": "OP-2026-10-16-001",
        "scope_digest": "a" * 64,
        "runtime_sha": "b" * 40,
        "valid_from_utc": "2026-10-16T00:00:00+00:00",
        "valid_until_utc": "2026-10-17T00:00:00+00:00",
        "max_operations": 12,
        "max_bytes": 524288,
        "paid_budget_usd": "0.00",
    }
    params.update(overrides)
    return ApprovalEnvelope(**params)  # type: ignore[arg-type]


def _trusted_pair() -> tuple[InMemoryTrustRoot, str]:
    private_b64, public_b64 = Ed25519Signer.generate_key_pair()
    trust = InMemoryTrustRoot()
    trust.register("test-key-001", public_b64)
    return trust, private_b64


def test_envelope_roundtrip_verifies() -> None:
    trust, private_b64 = _trusted_pair()
    signed = sign_envelope(_envelope(), private_b64)
    assert signed.signature_b64 != ""
    trust.verify_envelope(signed, _NOW)


def test_envelope_wrong_signature_rejected() -> None:
    trust, _ = _trusted_pair()
    other_private, _ = Ed25519Signer.generate_key_pair()
    signed = sign_envelope(_envelope(), other_private)
    try:
        trust.verify_envelope(signed, _NOW)
        assert False, "wrong-key signature must fail"
    except DataContractError:
        pass


def test_envelope_wrong_scope_rejected() -> None:
    trust, private_b64 = _trusted_pair()
    signed = sign_envelope(_envelope(), private_b64)
    import dataclasses

    tampered = dataclasses.replace(signed, scope_digest="c" * 64)
    try:
        trust.verify_envelope(tampered, _NOW)
        assert False, "altered scope must fail"
    except DataContractError:
        pass


def test_envelope_wrong_runtime_rejected() -> None:
    trust, private_b64 = _trusted_pair()
    signed = sign_envelope(_envelope(), private_b64)
    import dataclasses

    tampered = dataclasses.replace(signed, runtime_sha="c" * 40)
    try:
        trust.verify_envelope(tampered, _NOW)
        assert False, "altered runtime must fail"
    except DataContractError:
        pass


def test_envelope_expired_rejected() -> None:
    trust, private_b64 = _trusted_pair()
    signed = sign_envelope(_envelope(), private_b64)
    try:
        trust.verify_envelope(signed, "2026-10-18T00:00:00+00:00")
        assert False, "expired approval must fail"
    except DataContractError:
        pass


def test_envelope_revoked_key_rejected() -> None:
    trust, private_b64 = _trusted_pair()
    signed = sign_envelope(_envelope(), private_b64)
    trust.revoke("test-key-001")
    try:
        trust.verify_envelope(signed, _NOW)
        assert False, "revoked key must fail"
    except DataContractError:
        pass


def test_envelope_malformed_rejected() -> None:
    trust, _ = _trusted_pair()
    for bad in (
        _envelope().__class__(**{**_envelope_kwargs(), "signature_b64": "!!!not-b64!!!"}),
    ):
        try:
            trust.verify_envelope(bad, _NOW)
            assert False, "malformed envelope must fail"
        except DataContractError:
            pass
    try:
        trust.verify_envelope(_envelope(), _NOW)
        assert False, "unsigned envelope must fail"
    except DataContractError:
        pass


def _envelope_kwargs() -> dict[str, Any]:
    return {
        "key_id": "test-key-001",
        "approval_ref": "OP-2026-10-16-001",
        "scope_digest": "a" * 64,
        "runtime_sha": "b" * 40,
        "valid_from_utc": "2026-10-16T00:00:00+00:00",
        "valid_until_utc": "2026-10-17T00:00:00+00:00",
        "max_operations": 12,
        "max_bytes": 524288,
        "paid_budget_usd": "0.00",
        "signature_b64": "",
    }


def test_envelope_untrusted_key_rejected() -> None:
    trust, private_b64 = _trusted_pair()
    signed = sign_envelope(_envelope(), private_b64)
    import dataclasses

    foreign = dataclasses.replace(signed, key_id="unknown-key")
    try:
        trust.verify_envelope(foreign, _NOW)
        assert False, "untrusted key must fail"
    except DataContractError:
        pass


def test_envelope_altered_serialization_rejected() -> None:
    trust, private_b64 = _trusted_pair()
    signed = sign_envelope(_envelope(), private_b64)
    import dataclasses

    altered = dataclasses.replace(signed, max_operations=11)
    try:
        trust.verify_envelope(altered, _NOW)
        assert False, "altered bytes must fail"
    except DataContractError:
        pass


def test_envelope_duplicate_conflicting_identity_rejected() -> None:
    trust, private_b64 = _trusted_pair()
    first = sign_envelope(_envelope(), private_b64)
    second = sign_envelope(_envelope(max_operations=12), private_b64)
    assert first.signature_b64 == second.signature_b64
    other_private, _ = Ed25519Signer.generate_key_pair()
    other_signed = sign_envelope(_envelope(), other_private)
    assert other_signed.signature_b64 != first.signature_b64
    try:
        trust.verify_envelope(other_signed, _NOW)
        assert False, "conflicting signer must fail"
    except DataContractError:
        pass


def test_adapter_binds_envelope_to_approval() -> None:
    trust, private_b64 = _trusted_pair()
    signed = sign_envelope(_envelope(), private_b64)
    check = EnvelopeApprovalCheck(signed, trust, _NOW)

    class _Approval:
        approval_ref = "OP-2026-10-16-001"
        scope_digest = "a" * 64
        runtime_sha = "b" * 40

    assert check.check(_Approval()) is True

    class _WrongApproval:
        approval_ref = "OP-OTHER"
        scope_digest = "a" * 64
        runtime_sha = "b" * 40

    assert check.check(_WrongApproval()) is False


def test_byte_population_contract() -> None:
    assert admit_byte_population("", 100, 100) == "IDENTITY_SINGLE_POPULATION"
    assert admit_byte_population("identity", 0, 0) == "IDENTITY_SINGLE_POPULATION"
    assert admit_byte_population("gzip", 80, 100) == "DUAL_POPULATION_REQUIRED"
    try:
        admit_byte_population("", 100, 90)
        assert False, "identity contradiction must fail"
    except DataContractError:
        pass
    try:
        admit_byte_population("gzip", -1, 10)
        assert False, "negative length must fail"
    except DataContractError:
        pass


def test_no_production_trust_material_in_module() -> None:
    from pathlib import Path

    import acash.data.qualification.lane_a_d3_approval as module

    source = Path(str(module.__file__)).read_text(encoding="utf-8")
    for banned in ("os.environ", "getenv", "private_key_b64 =", "PROD_", "PRODUCTION_KEY"):
        assert banned not in source, f"production surface {banned!r} present"
    assert "TEST-ONLY" in source
