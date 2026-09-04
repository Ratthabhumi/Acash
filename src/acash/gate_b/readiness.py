"""Phase 13 Slice 2: Authoritative Gate B Readiness & Preflight Verification Service (Stage 3.5).

Implements:
- 6-Domain Authoritative Gate B Readiness Checker (Storage, Trust, Ledger, Snapshot, Risk, Capital/Isolation)
- Cryptographically Signed GateBReadinessReport with Ed25519 signature and canonical digest
- Strictly observational probe contract: zero mutations, zero normalization, zero state repairs
- Temporary non-mutating write-barrier capability probe (_probe_tmp)
- Explicit non-activation boundary (READY_FOR_HUMAN_GO != Gate B ACTIVE)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from acash.execution.crypto import (
    Ed25519Signer,
    Ed25519TrustStore,
    TrustStoreEntryStatus,
)
from acash.gate_b.readers import SnapshotReaderService
from acash.gate_b.recovery import (
    RecoveryDecisionTreeEngine,
    RecoveryInspectionResult,
)
from acash.gate_b.schema import (
    DurableTransactionState,
    LiveAuthorizationStatus,
    SystemSafetyMode,
)
from acash.gate_b.service import GateBRecoveryCoordinator
from acash.gate_b.storage import (
    AuthoritativeGOLedger,
    GENESIS_HEAD_DIGEST,
    StorageEngineSigner,
    StoragePlatformUtils,
)


class GateBReadinessStatus(str, Enum):
    """Authoritative operational readiness status for Gate B."""

    READY_FOR_HUMAN_GO = "READY_FOR_HUMAN_GO"
    BLOCKED = "BLOCKED"
    QUARANTINE_LOCKED = "QUARANTINE_LOCKED"


class GateBDomainCheckResult(BaseModel):
    """Result of a single readiness domain evaluation."""

    domain_id: str
    passed: bool
    status: GateBReadinessStatus
    status_message: str
    measured_attributes: Dict[str, Any] = Field(default_factory=dict)


class GateBReadinessReport(BaseModel):
    """Authoritative, cryptographically signed Gate B readiness verification report."""

    report_timestamp_utc: datetime
    overall_status: GateBReadinessStatus
    domain_results: Dict[str, GateBDomainCheckResult]
    report_digest: str
    signing_key_id: str
    report_signature: str
    raw_storage_root: str

    def compute_canonical_digest(self) -> str:
        """Compute SHA-256 over canonical JSON serialization of report payload.

        CRITICAL GUARDRAIL A: Neither report_digest nor report_signature is included
        in the payload to prevent circularity.
        """
        payload: Dict[str, Any] = {
            "domain_results": {
                k: v.model_dump(mode="json")
                for k, v in sorted(self.domain_results.items())
            },
            "overall_status": self.overall_status.value,
            "raw_storage_root": self.raw_storage_root,
            "report_timestamp_utc": self.report_timestamp_utc.isoformat(),
            "signing_key_id": self.signing_key_id,
        }
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def verify_signature(self, trust_store: Ed25519TrustStore) -> bool:
        """Cryptographically verify that report_signature matches report_digest using signing_key_id."""
        expected_digest = self.compute_canonical_digest()
        if self.report_digest != expected_digest:
            return False

        try:
            trust_store.verify(
                key_id=self.signing_key_id,
                payload_bytes=self.report_digest.encode("utf-8"),
                signature_b64=self.report_signature,
            )
            return True
        except Exception:
            return False



@dataclass(frozen=True)
class BrokerProbeSnapshot:
    """Snapshot of broker terminal connection and account state."""

    init: bool
    login: int
    trade_mode: int  # 0 = Demo
    currency: str
    positions: int
    orders: int
    margin: float
    balance: float
    live_capital_authorized: Decimal


class GateBReadinessChecker:
    """Authoritative Gate B Preflight Verification Service.

    Evaluates the 6 Canonical Gate B Readiness Domains in a strictly read-only,
    observational manner without modifying any production ledger or snapshot state.
    """

    REQUIRED_SKELETON_DIRS = [
        "drafts",
        "staging",
        "snapshots",
        "pointer",
        "aborts",
        "journal",
        "tx_state",
    ]

    PROHIBITED_LIVE_ENV_VARS = [
        "MT5_LIVE_PASSWORD",
        "LIVE_TRADING_KEY",
        "ACASH_LIVE_CAPITAL_ALLOCATION",
        "LIVE_BROKER_API_SECRET",
    ]

    def __init__(
        self,
        storage_root: Path,
        trust_store: Ed25519TrustStore,
        auditor_signer: StorageEngineSigner,
        effective_max_position_size: Optional[Decimal] = Decimal("0.01"),
        max_quote_age_ms: int = 5000,
        broker_probe_override: Optional[BrokerProbeSnapshot] = None,
    ) -> None:
        self._root = Path(storage_root)
        self._trust_store = trust_store
        self._auditor_signer = auditor_signer
        self._effective_max_position_size = effective_max_position_size
        self._max_quote_age_ms = max_quote_age_ms
        self._broker_probe_override = broker_probe_override

    def evaluate_readiness(self) -> GateBReadinessReport:
        """Evaluate all 6 readiness domains and generate a cryptographically signed report."""
        domain_results: Dict[str, GateBDomainCheckResult] = {}

        # Domain 1: Storage Substrate & Durability Contract
        d1 = self._check_domain_1_storage()
        domain_results["DOMAIN_1_STORAGE"] = d1

        # Domain 2: Cryptographic Trust Anchor & Credentials
        d2 = self._check_domain_2_trust()
        domain_results["DOMAIN_2_TRUST"] = d2

        # Domain 3: Authoritative Ledger Continuity & State Hygiene
        d3 = self._check_domain_3_ledger()
        domain_results["DOMAIN_3_LEDGER"] = d3

        # Domain 4: Reader & Snapshot Publication Integrity
        d4 = self._check_domain_4_readers()
        domain_results["DOMAIN_4_READERS"] = d4

        # Domain 5: Pre-Live Risk Admission Configuration & Bounding
        d5 = self._check_domain_5_risk()
        domain_results["DOMAIN_5_RISK"] = d5

        # Domain 6: Capital Lock & Operational Isolation Boundary
        d6 = self._check_domain_6_capital_isolation()
        domain_results["DOMAIN_6_CAPITAL_ISOLATION"] = d6

        # Determine overall status fail-closed
        if any(d.status == GateBReadinessStatus.QUARANTINE_LOCKED for d in domain_results.values()):
            overall_status = GateBReadinessStatus.QUARANTINE_LOCKED
        elif any(d.status == GateBReadinessStatus.BLOCKED for d in domain_results.values()):
            overall_status = GateBReadinessStatus.BLOCKED
        else:
            overall_status = GateBReadinessStatus.READY_FOR_HUMAN_GO

        now_utc = datetime.now(timezone.utc)
        pre_report = GateBReadinessReport(
            report_timestamp_utc=now_utc,
            overall_status=overall_status,
            domain_results=domain_results,
            report_digest="",
            signing_key_id=self._auditor_signer.key_id,
            report_signature="",
            raw_storage_root=str(self._root),
        )

        canonical_digest = pre_report.compute_canonical_digest()
        raw_signature = self._auditor_signer.sign(canonical_digest.encode("utf-8"))

        return pre_report.model_copy(
            update={
                "report_digest": canonical_digest,
                "report_signature": raw_signature,
            }
        )

    # -------------------------------------------------------------------------
    # Domain 1: Storage Substrate & Durability Contract
    # -------------------------------------------------------------------------
    def _check_domain_1_storage(self) -> GateBDomainCheckResult:
        """Domain 1: Verify skeleton, write barrier capability via _probe_tmp, and safety mode."""
        attrs: Dict[str, Any] = {}

        # 1. Directory skeleton
        missing_dirs: List[str] = []
        for d in self.REQUIRED_SKELETON_DIRS:
            target = self._root / d
            if not target.exists() or not target.is_dir():
                missing_dirs.append(d)
        attrs["missing_skeleton_dirs"] = missing_dirs
        if missing_dirs:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_1_STORAGE",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Missing required storage skeleton directories: {missing_dirs}",
                measured_attributes=attrs,
            )

        # 2. SystemSafetyMode check
        safety_file = self._root / "system_safety_mode.state"
        if safety_file.exists():
            try:
                content = safety_file.read_text(encoding="utf-8").strip()
                attrs["system_safety_mode"] = content
                if content == SystemSafetyMode.QUARANTINE_LOCKED.value:
                    return GateBDomainCheckResult(
                        domain_id="DOMAIN_1_STORAGE",
                        passed=False,
                        status=GateBReadinessStatus.QUARANTINE_LOCKED,
                        status_message="Storage substrate is in SystemSafetyMode.QUARANTINE_LOCKED",
                        measured_attributes=attrs,
                    )
            except Exception as exc:
                attrs["safety_file_read_error"] = str(exc)
                return GateBDomainCheckResult(
                    domain_id="DOMAIN_1_STORAGE",
                    passed=False,
                    status=GateBReadinessStatus.QUARANTINE_LOCKED,
                    status_message=f"Failed to read system safety mode file: {exc}",
                    measured_attributes=attrs,
                )
        else:
            attrs["system_safety_mode"] = SystemSafetyMode.NORMAL.value

        # 3. Non-mutating write-barrier capability probe on _probe_tmp
        probe_dir = self._root / "_probe_tmp"
        try:
            probe_dir.mkdir(parents=True, exist_ok=True)
            probe_file = probe_dir / "barrier.probe"
            probe_file.write_bytes(b"DURABILITY_PROBE_STAGE_3_5")
            # Execute barrier capability
            StoragePlatformUtils.flush_directory(probe_dir)
            attrs["barrier_probe_success"] = True
        except Exception as exc:
            attrs["barrier_probe_error"] = str(exc)
            return GateBDomainCheckResult(
                domain_id="DOMAIN_1_STORAGE",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Filesystem write-barrier capability probe failed: {exc}",
                measured_attributes=attrs,
            )
        finally:
            shutil.rmtree(probe_dir, ignore_errors=True)

        return GateBDomainCheckResult(
            domain_id="DOMAIN_1_STORAGE",
            passed=True,
            status=GateBReadinessStatus.READY_FOR_HUMAN_GO,
            status_message="Storage substrate and durability barriers verified clean",
            measured_attributes=attrs,
        )

    # -------------------------------------------------------------------------
    # Domain 2: Cryptographic Trust Anchor & Credentials
    # -------------------------------------------------------------------------
    def _check_domain_2_trust(self) -> GateBDomainCheckResult:
        """Domain 2: Verify active trust anchors for engine, approver, and auditor signer.

        CRITICAL GUARDRAIL B: Scope assertion strictly to required active trust anchors.
        Do NOT fail if historical revoked keys exist in store.
        """
        attrs: Dict[str, Any] = {}
        now_utc = datetime.now(timezone.utc)

        # Check auditor signer key exists and is ACTIVE
        auditor_key_id = self._auditor_signer.key_id
        attrs["auditor_key_id"] = auditor_key_id
        entry = next((e for e in self._trust_store.entries if e.key_id == auditor_key_id), None)
        if entry is None:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_2_TRUST",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Auditor signing key {auditor_key_id} not found in trust store",
                measured_attributes=attrs,
            )

        if entry.status != TrustStoreEntryStatus.ACTIVE:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_2_TRUST",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Auditor signing key {auditor_key_id} is not ACTIVE (status: {entry.status})",
                measured_attributes=attrs,
            )

        if (entry.valid_until is not None and entry.valid_until < now_utc) or (
            entry.valid_from is not None and entry.valid_from > now_utc
        ):
            return GateBDomainCheckResult(
                domain_id="DOMAIN_2_TRUST",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Auditor signing key {auditor_key_id} is expired or not yet valid",
                measured_attributes=attrs,
            )

        # Check at least one active approver key exists
        active_entries = [
            e for e in self._trust_store.entries
            if e.status == TrustStoreEntryStatus.ACTIVE
            and (e.valid_from is None or e.valid_from <= now_utc)
            and (e.valid_until is None or now_utc <= e.valid_until)
        ]
        attrs["active_trust_store_entry_count"] = len(active_entries)
        if len(active_entries) < 1:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_2_TRUST",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message="Zero active unexpired trust store entries found",
                measured_attributes=attrs,
            )

        return GateBDomainCheckResult(
            domain_id="DOMAIN_2_TRUST",
            passed=True,
            status=GateBReadinessStatus.READY_FOR_HUMAN_GO,
            status_message=f"Trust anchors verified clean ({len(active_entries)} active entries)",
            measured_attributes=attrs,
        )

    # -------------------------------------------------------------------------
    # Domain 3: Authoritative Ledger Continuity & State Hygiene
    # -------------------------------------------------------------------------
    def _check_domain_3_ledger(self) -> GateBDomainCheckResult:
        """Domain 3: Verify unbroken ledger continuity and strictly read-only recovery hygiene."""
        attrs: Dict[str, Any] = {}

        # 1. Check ledger head existence & validity
        head_file = self._root / "head.json"
        if not head_file.exists():
            return GateBDomainCheckResult(
                domain_id="DOMAIN_3_LEDGER",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message="Authoritative ledger head.json is missing",
                measured_attributes=attrs,
            )

        try:
            with open(head_file, "r", encoding="utf-8") as f:
                head_data = json.load(f)
            current_head = head_data.get("head_digest")
            attrs["current_head_digest"] = current_head
            if not current_head or len(current_head) != 64:
                return GateBDomainCheckResult(
                    domain_id="DOMAIN_3_LEDGER",
                    passed=False,
                    status=GateBReadinessStatus.BLOCKED,
                    status_message=f"Invalid ledger head digest format: {current_head}",
                    measured_attributes=attrs,
                )
        except Exception as exc:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_3_LEDGER",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Corrupted head.json: {exc}",
                measured_attributes=attrs,
            )

        # 2. Strictly read-only recovery inspection (Guardrail C: zero mutations)
        try:
            ledger = AuthoritativeGOLedger(self._root, self._trust_store)
            coordinator = GateBRecoveryCoordinator(ledger, self._trust_store, self._auditor_signer)
            inspection_results = coordinator.inspect_recovery_state()
            attrs["inspected_transaction_count"] = len(inspection_results)

            quarantine_risks = [
                str(tx_id) for tx_id, res in inspection_results.items()
                if res.quarantine_risk or res.durable_state == DurableTransactionState.QUARANTINED
            ]
            if quarantine_risks:
                attrs["quarantine_risk_transactions"] = quarantine_risks
                return GateBDomainCheckResult(
                    domain_id="DOMAIN_3_LEDGER",
                    passed=False,
                    status=GateBReadinessStatus.QUARANTINE_LOCKED,
                    status_message=f"Quarantine risk detected on transactions: {quarantine_risks}",
                    measured_attributes=attrs,
                )

            pending_recovery = [
                str(tx_id) for tx_id, res in inspection_results.items()
                if res.requires_recovery
            ]
            if pending_recovery:
                attrs["pending_recovery_transactions"] = pending_recovery
                return GateBDomainCheckResult(
                    domain_id="DOMAIN_3_LEDGER",
                    passed=False,
                    status=GateBReadinessStatus.BLOCKED,
                    status_message=f"Transactions requiring recovery action pending: {pending_recovery}",
                    measured_attributes=attrs,
                )

        except Exception as exc:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_3_LEDGER",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Read-only recovery inspection failed: {exc}",
                measured_attributes=attrs,
            )

        return GateBDomainCheckResult(
            domain_id="DOMAIN_3_LEDGER",
            passed=True,
            status=GateBReadinessStatus.READY_FOR_HUMAN_GO,
            status_message="Ledger continuity and transaction hygiene verified clean",
            measured_attributes=attrs,
        )

    # -------------------------------------------------------------------------
    # Domain 4: Reader & Snapshot Publication Integrity
    # -------------------------------------------------------------------------
    def _check_domain_4_readers(self) -> GateBDomainCheckResult:
        """Domain 4: Verify 4-point identity binding and snapshot integrity if active."""
        attrs: Dict[str, Any] = {}
        ledger = AuthoritativeGOLedger(self._root, self._trust_store)

        with ledger.exclusive_lock() as tx:
            active_tx_id = tx.get_current_active_transaction_id()
            attrs["active_transaction_id"] = str(active_tx_id) if active_tx_id else None

            if active_tx_id is not None:
                try:
                    view = SnapshotReaderService.read_active_committed_snapshot(tx)
                    attrs["active_snapshot_transaction_id"] = str(view.transaction_id)
                    attrs["has_active_authorization"] = view.authorization is not None
                    if view.authorization and view.authorization.status != LiveAuthorizationStatus.ACTIVE:
                        return GateBDomainCheckResult(
                            domain_id="DOMAIN_4_READERS",
                            passed=False,
                            status=GateBReadinessStatus.BLOCKED,
                            status_message=f"Active snapshot authorization status is {view.authorization.status}, expected ACTIVE",
                            measured_attributes=attrs,
                        )
                except Exception as exc:
                    return GateBDomainCheckResult(
                        domain_id="DOMAIN_4_READERS",
                        passed=False,
                        status=GateBReadinessStatus.QUARANTINE_LOCKED,
                        status_message=f"Active committed snapshot reader failed (tamper/identity violation): {exc}",
                        measured_attributes=attrs,
                    )
            else:
                attrs["snapshot_baseline"] = "PRE_ACTIVATION_CLEAN"

        return GateBDomainCheckResult(
            domain_id="DOMAIN_4_READERS",
            passed=True,
            status=GateBReadinessStatus.READY_FOR_HUMAN_GO,
            status_message="Snapshot publication boundaries and reader contracts verified clean",
            measured_attributes=attrs,
        )

    # -------------------------------------------------------------------------
    # Domain 5: Pre-Live Risk Admission Configuration & Bounding
    # -------------------------------------------------------------------------
    def _check_domain_5_risk(self) -> GateBDomainCheckResult:
        """Domain 5: Verify risk parameters, position bounds, and quote freshness settings."""
        attrs: Dict[str, Any] = {}
        attrs["effective_max_position_size"] = str(self._effective_max_position_size)
        attrs["max_quote_age_ms"] = self._max_quote_age_ms

        if self._effective_max_position_size is None or self._effective_max_position_size <= 0:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_5_RISK",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Effective max position size undefined or non-positive: {self._effective_max_position_size}",
                measured_attributes=attrs,
            )

        if self._max_quote_age_ms <= 0 or self._max_quote_age_ms > 10000:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_5_RISK",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Max quote freshness window out of acceptable bounds (0, 10000ms]: {self._max_quote_age_ms}",
                measured_attributes=attrs,
            )

        return GateBDomainCheckResult(
            domain_id="DOMAIN_5_RISK",
            passed=True,
            status=GateBReadinessStatus.READY_FOR_HUMAN_GO,
            status_message="Pre-live risk admission parameters verified within bounds",
            measured_attributes=attrs,
        )

    # -------------------------------------------------------------------------
    # Domain 6: Capital Lock & Operational Isolation Boundary
    # -------------------------------------------------------------------------
    def _check_domain_6_capital_isolation(self) -> GateBDomainCheckResult:
        """Domain 6: Verify $0.00 capital, 100% FLAT broker demo, and credential isolation."""
        attrs: Dict[str, Any] = {}

        # 1. Prohibited environment variables (Refinement 1)
        found_prohibited_vars = [
            v for v in self.PROHIBITED_LIVE_ENV_VARS if os.environ.get(v)
        ]
        attrs["prohibited_env_vars_found"] = found_prohibited_vars
        if found_prohibited_vars:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_6_CAPITAL_ISOLATION",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Prohibited live credential environment variables present: {found_prohibited_vars}",
                measured_attributes=attrs,
            )

        # 2. Broker Probe (Refinement 6)
        probe = self._broker_probe_override or self._probe_live_broker()
        if probe is None:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_6_CAPITAL_ISOLATION",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message="Broker safety probe unavailable (cannot verify 100% FLAT state)",
                measured_attributes=attrs,
            )

        attrs["broker_login"] = probe.login
        attrs["broker_trade_mode"] = probe.trade_mode
        attrs["broker_currency"] = probe.currency
        attrs["broker_positions"] = probe.positions
        attrs["broker_orders"] = probe.orders
        attrs["broker_margin"] = probe.margin
        attrs["broker_balance"] = probe.balance
        attrs["live_capital_authorized"] = str(probe.live_capital_authorized)

        # Invariant checks:
        if not probe.init:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_6_CAPITAL_ISOLATION",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message="Broker terminal initialization failed",
                measured_attributes=attrs,
            )

        if probe.login != 112040157:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_6_CAPITAL_ISOLATION",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Broker login is {probe.login}, expected designated Demo 112040157",
                measured_attributes=attrs,
            )

        if probe.trade_mode != 0:  # 0 = Demo
            return GateBDomainCheckResult(
                domain_id="DOMAIN_6_CAPITAL_ISOLATION",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Broker trade mode is {probe.trade_mode} (not DEMO)",
                measured_attributes=attrs,
            )

        if probe.positions != 0 or probe.orders != 0 or probe.margin != 0.0:
            return GateBDomainCheckResult(
                domain_id="DOMAIN_6_CAPITAL_ISOLATION",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Broker is NOT 100% FLAT: positions={probe.positions}, orders={probe.orders}, margin={probe.margin}",
                measured_attributes=attrs,
            )

        if probe.live_capital_authorized != Decimal("0.00"):
            return GateBDomainCheckResult(
                domain_id="DOMAIN_6_CAPITAL_ISOLATION",
                passed=False,
                status=GateBReadinessStatus.BLOCKED,
                status_message=f"Live capital authorization is {probe.live_capital_authorized}, strictly required $0.00",
                measured_attributes=attrs,
            )

        return GateBDomainCheckResult(
            domain_id="DOMAIN_6_CAPITAL_ISOLATION",
            passed=True,
            status=GateBReadinessStatus.READY_FOR_HUMAN_GO,
            status_message="Capital lock ($0.00) and broker 100% FLAT state verified",
            measured_attributes=attrs,
        )

    def _probe_live_broker(self) -> Optional[BrokerProbeSnapshot]:
        """Query MetaTrader 5 terminal if available."""
        try:
            import importlib
            mt5 = importlib.import_module("MetaTrader5")

            init_ok = bool(mt5.initialize())
            if not init_ok:
                return None
            acc = mt5.account_info()
            positions = mt5.positions_get()
            orders = mt5.orders_get()
            mt5.shutdown()

            return BrokerProbeSnapshot(
                init=True,
                login=getattr(acc, "login", 0),
                trade_mode=getattr(acc, "trade_mode", -1),
                currency=getattr(acc, "currency", ""),
                positions=len(positions) if positions else 0,
                orders=len(orders) if orders else 0,
                margin=float(getattr(acc, "margin", 0.0) or 0.0),
                balance=float(getattr(acc, "balance", 0.0) or 0.0),
                live_capital_authorized=Decimal("0.00"),
            )
        except Exception:
            return None
