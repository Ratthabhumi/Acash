"""Phase 13 Slice 2: Gate B Readiness Checker Unit Tests (Stage 3.5).

Verifies:
1. Complete 6-domain readiness evaluation on physical filesystem directories.
2. Cryptographic signature and digest authentication on GateBReadinessReport.
3. Separation of hash integrity vs signature rejection on report tampering.
4. Strictly read-only recovery inspection (zero writes, zero renames, zero state alterations).
5. Fail-closed behavior on broken skeletons, quarantine locks, missing keys, and capital breaches.
6. Explicit non-activation boundary (READY_FOR_HUMAN_GO != Gate B ACTIVE).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
from typing import Generator, Tuple
from uuid import uuid4

import pytest

from acash.execution.crypto import (
    Ed25519Signer,
    Ed25519TrustStore,
    Ed25519TrustStoreEntry,
    TrustStoreEntryStatus,
)
from acash.gate_b.readiness import (
    BrokerProbeSnapshot,
    GateBReadinessChecker,
    GateBReadinessReport,
    GateBReadinessStatus,
)
from acash.gate_b.recovery import RecoveryDecisionTreeEngine
from acash.gate_b.schema import (
    AuthoritativeCommitRecordBlock,
    DurableTransactionState,
    HumanGORecord,
    LiveAuthorization,
    LiveAuthorizationStatus,
    SystemSafetyMode,
)
from acash.gate_b.service import GateBRecoveryCoordinator
from acash.gate_b.storage import (
    AuthoritativeGOLedger,
    GENESIS_HEAD_DIGEST,
    StorageCommitContract,
    StorageEngineSigner,
    StoragePlatformUtils,
)

ReadinessEnvType = Tuple[Path, Ed25519TrustStore, StorageEngineSigner, StorageEngineSigner, BrokerProbeSnapshot]


@pytest.fixture
def readiness_env(tmp_path: Path) -> Generator[ReadinessEnvType, None, None]:
    """Provide isolated physical storage directory, trust credentials, and flat broker probe."""
    root = tmp_path / "readiness_isolated_root"
    root.mkdir(parents=True, exist_ok=True)


    now_utc = datetime.now(timezone.utc)

    # Engine key
    eng_priv, eng_pub = Ed25519Signer.generate_key_pair()
    eng_key_id = "KEY_ENGINE_STAGE_3_5"
    eng_entry = Ed25519TrustStoreEntry(
        key_id=eng_key_id,
        issuer_id="ACASH_STORAGE_ENGINE_ROOT",
        public_key_b64=eng_pub,
        valid_from=now_utc - timedelta(days=1),
        valid_until=now_utc + timedelta(days=365),
        status=TrustStoreEntryStatus.ACTIVE,
    )

    # Approver key
    app_priv, app_pub = Ed25519Signer.generate_key_pair()
    app_key_id = "KEY_GOVERNANCE_STAGE_3_5"
    app_entry = Ed25519TrustStoreEntry(
        key_id=app_key_id,
        issuer_id="ACASH_GOVERNANCE_ROOT",
        public_key_b64=app_pub,
        valid_from=now_utc - timedelta(days=1),
        valid_until=now_utc + timedelta(days=365),
        status=TrustStoreEntryStatus.ACTIVE,
    )

    # Auditor key (for report signing)
    aud_priv, aud_pub = Ed25519Signer.generate_key_pair()
    aud_key_id = "KEY_AUDITOR_STAGE_3_5"
    aud_entry = Ed25519TrustStoreEntry(
        key_id=aud_key_id,
        issuer_id="ACASH_AUDIT_ROOT",
        public_key_b64=aud_pub,
        valid_from=now_utc - timedelta(days=1),
        valid_until=now_utc + timedelta(days=365),
        status=TrustStoreEntryStatus.ACTIVE,
    )

    trust_store = Ed25519TrustStore(entries=(eng_entry, app_entry, aud_entry))
    eng_signer = StorageEngineSigner(eng_key_id, eng_priv)
    aud_signer = StorageEngineSigner(aud_key_id, aud_priv)

    # Initialize authoritative skeleton & genesis head
    ledger = AuthoritativeGOLedger(root, trust_store)
    with ledger.exclusive_lock() as tx:
        tx.set_head_digest_durable(GENESIS_HEAD_DIGEST)
        (root / "drafts").mkdir(parents=True, exist_ok=True)

    probe = BrokerProbeSnapshot(
        init=True,
        login=112040157,
        trade_mode=0,
        currency="USD",
        positions=0,
        orders=0,
        margin=0.0,
        balance=2999.65,
        live_capital_authorized=Decimal("0.00"),
    )

    yield root, trust_store, eng_signer, aud_signer, probe

    StoragePlatformUtils.mark_directory_writable(root)



def test_readiness_clean_baseline_succeeds(readiness_env: ReadinessEnvType) -> None:
    """Verify that a clean initialized Gate B storage environment passes all 6 domains."""
    root, trust_store, _, aud_signer, probe = readiness_env

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )

    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.READY_FOR_HUMAN_GO
    assert len(report.domain_results) == 6
    for domain_id, result in report.domain_results.items():
        assert result.passed is True, f"Domain {domain_id} failed: {result.status_message}"
        assert result.status == GateBReadinessStatus.READY_FOR_HUMAN_GO

    # Verify cryptographic signature
    assert report.verify_signature(trust_store) is True


def test_readiness_report_digest_mutates_on_tamper(readiness_env: ReadinessEnvType) -> None:
    """Proves hash integrity: mutating report payload changes canonical digest."""
    root, trust_store, _, aud_signer, probe = readiness_env

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )
    report = checker.evaluate_readiness()
    original_digest = report.report_digest

    # Tamper with a domain check message
    tampered_results = dict(report.domain_results)
    d1 = tampered_results["DOMAIN_1_STORAGE"]
    tampered_results["DOMAIN_1_STORAGE"] = d1.model_copy(
        update={"status_message": "TAMPERED_MODIFIED_MESSAGE"}
    )
    tampered_report = report.model_copy(update={"domain_results": tampered_results})

    new_digest = tampered_report.compute_canonical_digest()
    assert new_digest != original_digest


def test_readiness_report_signature_fails_on_tamper(readiness_env: ReadinessEnvType) -> None:
    """Proves cryptographic rejection: signature verification fails when report payload is mutated."""
    root, trust_store, _, aud_signer, probe = readiness_env

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )
    report = checker.evaluate_readiness()
    assert report.verify_signature(trust_store) is True

    # Mutate overall status from READY_FOR_HUMAN_GO to BLOCKED
    tampered_report = report.model_copy(update={"overall_status": GateBReadinessStatus.BLOCKED})
    assert tampered_report.verify_signature(trust_store) is False


def test_readiness_report_signature_succeeds_for_original(readiness_env: ReadinessEnvType) -> None:
    """Proves that an unmodified report authenticates successfully against the trust store."""
    root, trust_store, _, aud_signer, probe = readiness_env

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )
    report = checker.evaluate_readiness()
    assert report.verify_signature(trust_store) is True


def test_readiness_inspect_recovery_state_is_strictly_read_only(readiness_env: ReadinessEnvType) -> None:
    """Proves that inspect_recovery_state() performs zero writes or renames on disk."""
    root, trust_store, eng_signer, aud_signer, _ = readiness_env
    ledger = AuthoritativeGOLedger(root, trust_store)

    # Take snapshot of directory state (file paths and sizes)
    files_before = {p.relative_to(root): p.stat().st_size for p in root.glob("**/*") if p.is_file()}

    coordinator = GateBRecoveryCoordinator(ledger, trust_store, eng_signer)
    results = coordinator.inspect_recovery_state()

    assert isinstance(results, dict)

    files_after = {p.relative_to(root): p.stat().st_size for p in root.glob("**/*") if p.is_file()}
    assert files_before == files_after, "inspect_recovery_state modified files on disk!"


def test_readiness_missing_directory_skeleton_fails_closed(readiness_env: ReadinessEnvType) -> None:
    """Removing a required skeleton directory causes Domain 1 to fail closed (BLOCKED)."""
    root, trust_store, _, aud_signer, probe = readiness_env

    # Remove snapshots directory
    shutil.rmtree(root / "snapshots")

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )
    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.BLOCKED
    assert report.domain_results["DOMAIN_1_STORAGE"].passed is False
    assert report.domain_results["DOMAIN_1_STORAGE"].status == GateBReadinessStatus.BLOCKED
    assert "snapshots" in report.domain_results["DOMAIN_1_STORAGE"].status_message


def test_readiness_quarantine_locked_fails_closed(readiness_env: ReadinessEnvType) -> None:
    """Substrate in QUARANTINE_LOCKED causes Domain 1 to fail to QUARANTINE_LOCKED."""
    root, trust_store, _, aud_signer, probe = readiness_env

    # Write QUARANTINE_LOCKED safety file
    (root / "system_safety_mode.state").write_text("QUARANTINE_LOCKED", encoding="utf-8")

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )
    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.QUARANTINE_LOCKED
    assert report.domain_results["DOMAIN_1_STORAGE"].passed is False
    assert report.domain_results["DOMAIN_1_STORAGE"].status == GateBReadinessStatus.QUARANTINE_LOCKED


def test_readiness_revoked_auditor_key_fails_closed(readiness_env: ReadinessEnvType) -> None:
    """Revoked auditor signing key causes Domain 2 to fail closed (BLOCKED)."""
    root, trust_store, _, aud_signer, probe = readiness_env

    # Revoke auditor key entry
    now_utc = datetime.now(timezone.utc)
    revoked_entry = Ed25519TrustStoreEntry(
        key_id=aud_signer.key_id,
        issuer_id="ACASH_AUDIT_ROOT",
        public_key_b64="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        valid_from=now_utc - timedelta(days=1),
        valid_until=now_utc + timedelta(days=365),
        status=TrustStoreEntryStatus.REVOKED,
    )
    bad_trust_store = Ed25519TrustStore(entries=(revoked_entry,))

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=bad_trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )
    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.BLOCKED
    assert report.domain_results["DOMAIN_2_TRUST"].passed is False
    assert "not ACTIVE" in report.domain_results["DOMAIN_2_TRUST"].status_message


def test_readiness_broken_ledger_head_continuity_fails_closed(readiness_env: ReadinessEnvType) -> None:
    """Missing or corrupted head.json causes Domain 3 to fail closed (BLOCKED)."""
    root, trust_store, _, aud_signer, probe = readiness_env

    # Corrupt head.json
    (root / "head.json").write_text("INVALID_NON_JSON_CORRUPTION", encoding="utf-8")

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )
    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.BLOCKED
    assert report.domain_results["DOMAIN_3_LEDGER"].passed is False


def test_readiness_quarantine_risk_fails_closed(readiness_env: ReadinessEnvType) -> None:
    """Transaction in QUARANTINED state causes Domain 3 to report QUARANTINE_LOCKED."""
    root, trust_store, _, aud_signer, probe = readiness_env

    # Inject a quarantined transaction state file
    bad_tx_id = uuid4()
    (root / "tx_state" / f"{bad_tx_id}.state").write_text("QUARANTINED", encoding="utf-8")

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )
    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.QUARANTINE_LOCKED
    assert report.domain_results["DOMAIN_3_LEDGER"].passed is False
    assert report.domain_results["DOMAIN_3_LEDGER"].status == GateBReadinessStatus.QUARANTINE_LOCKED


def test_readiness_pending_recovery_fails_closed(readiness_env: ReadinessEnvType) -> None:
    """Transaction in COMMITTING state causes Domain 3 to report BLOCKED (unrecovered)."""
    root, trust_store, _, aud_signer, probe = readiness_env

    # Inject an unrecovered COMMITTING transaction
    unrecovered_tx_id = uuid4()
    (root / "tx_state" / f"{unrecovered_tx_id}.state").write_text("COMMITTING", encoding="utf-8")

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )
    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.QUARANTINE_LOCKED or report.overall_status == GateBReadinessStatus.BLOCKED
    assert report.domain_results["DOMAIN_3_LEDGER"].passed is False


def test_readiness_undefined_position_limit_fails_closed(readiness_env: ReadinessEnvType) -> None:
    """Non-positive or undefined effective position limit fails Domain 5 (BLOCKED)."""
    root, trust_store, _, aud_signer, probe = readiness_env

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        effective_max_position_size=Decimal("0.00"),
        broker_probe_override=probe,
    )
    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.BLOCKED
    assert report.domain_results["DOMAIN_5_RISK"].passed is False


def test_readiness_prohibited_env_vars_fails_closed(readiness_env: ReadinessEnvType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Presence of live password environment variable fails Domain 6 (BLOCKED)."""
    root, trust_store, _, aud_signer, probe = readiness_env

    monkeypatch.setenv("MT5_LIVE_PASSWORD", "SECRET_LIVE_PASSWORD_DO_NOT_LEAK")

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )
    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.BLOCKED
    assert report.domain_results["DOMAIN_6_CAPITAL_ISOLATION"].passed is False
    assert "MT5_LIVE_PASSWORD" in report.domain_results["DOMAIN_6_CAPITAL_ISOLATION"].status_message


def test_readiness_non_zero_live_capital_fails_closed(readiness_env: ReadinessEnvType) -> None:
    """Attempted live capital authorization > $0.00 fails Domain 6 (BLOCKED)."""
    root, trust_store, _, aud_signer, probe = readiness_env

    bad_probe = BrokerProbeSnapshot(
        init=probe.init,
        login=probe.login,
        trade_mode=probe.trade_mode,
        currency=probe.currency,
        positions=probe.positions,
        orders=probe.orders,
        margin=probe.margin,
        balance=probe.balance,
        live_capital_authorized=Decimal("100.00"),  # VIOLATION
    )

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=bad_probe,
    )
    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.BLOCKED
    assert report.domain_results["DOMAIN_6_CAPITAL_ISOLATION"].passed is False


def test_readiness_non_flat_broker_fails_closed(readiness_env: ReadinessEnvType) -> None:
    """Non-flat broker demo (open positions) fails Domain 6 (BLOCKED)."""
    root, trust_store, _, aud_signer, probe = readiness_env

    bad_probe = BrokerProbeSnapshot(
        init=probe.init,
        login=probe.login,
        trade_mode=probe.trade_mode,
        currency=probe.currency,
        positions=1,  # VIOLATION: open position
        orders=0,
        margin=10.50,
        balance=probe.balance,
        live_capital_authorized=Decimal("0.00"),
    )

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=bad_probe,
    )
    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.BLOCKED
    assert report.domain_results["DOMAIN_6_CAPITAL_ISOLATION"].passed is False


def test_readiness_wrong_broker_login_fails_closed(readiness_env: ReadinessEnvType) -> None:
    """Wrong broker account login fails Domain 6 (BLOCKED)."""
    root, trust_store, _, aud_signer, probe = readiness_env

    bad_probe = BrokerProbeSnapshot(
        init=probe.init,
        login=999999999,  # VIOLATION
        trade_mode=probe.trade_mode,
        currency=probe.currency,
        positions=0,
        orders=0,
        margin=0.0,
        balance=probe.balance,
        live_capital_authorized=Decimal("0.00"),
    )

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=bad_probe,
    )
    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.BLOCKED
    assert report.domain_results["DOMAIN_6_CAPITAL_ISOLATION"].passed is False


def test_ready_report_cannot_activate_gate_b(readiness_env: ReadinessEnvType) -> None:
    """Enforces that a READY_FOR_HUMAN_GO report has zero ability to activate Gate B."""
    root, trust_store, _, aud_signer, probe = readiness_env

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )
    report = checker.evaluate_readiness()

    assert report.overall_status == GateBReadinessStatus.READY_FOR_HUMAN_GO

    # Confirm that no active snapshot pointer was created
    pointer_file = root / "pointer" / "committed_pointer"
    assert not pointer_file.exists()


def test_readiness_checker_has_no_live_activation_capability() -> None:
    """Verifies that GateBReadinessChecker exposes zero activation or execution methods."""
    prohibited_methods = [
        "activate_gate_b",
        "activate_authorization",
        "send_order",
        "execute_live_order",
        "unlock_gate_b",
    ]
    for method in prohibited_methods:
        assert not hasattr(GateBReadinessChecker, method), f"Prohibited method {method} found on GateBReadinessChecker!"


def test_readiness_temporary_barrier_probe_leaves_no_artifacts(readiness_env: ReadinessEnvType) -> None:
    """Verifies that Domain 1 capability probe cleans up _probe_tmp completely."""
    root, trust_store, _, aud_signer, probe = readiness_env

    checker = GateBReadinessChecker(
        storage_root=root,
        trust_store=trust_store,
        auditor_signer=aud_signer,
        broker_probe_override=probe,
    )
    checker.evaluate_readiness()

    probe_dir = root / "_probe_tmp"
    assert not probe_dir.exists(), "_probe_tmp was not cleaned up!"
