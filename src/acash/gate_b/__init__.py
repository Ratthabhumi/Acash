"""Phase 13 Slice 2: Gate B Dual-Layer Mandatory Authorization Module.

Exposes canonical schemas, DTOs, exceptions, storage engines, and cryptographic
validation primitives for Gate B preflight verification and activation transactions.
"""

from acash.gate_b.exceptions import (
    CryptographicVerificationError,
    DataContractError,
    GateBError,
    PreLiveRiskAdmissionError,
    QuarantineError,
    StorageDurabilityError,
)
from acash.gate_b.schema import (
    AuthoritativeAbortRecordBlock,
    AuthoritativeCommitRecordBlock,
    AuthoritativeLedgerProtocol,
    DurablePointerTransitionRecord,
    DurableTransactionState,
    HumanGORecord,
    JournalState,
    LiveAuthorization,
    LiveAuthorizationStatus,
    MT5QuoteSnapshot,
    SystemSafetyMode,
    assert_activation_preconditions,
    calculate_worst_case_notional,
    verify_human_go_record_integrity,
)
from acash.gate_b.readiness import (
    BrokerProbeSnapshot,
    GateBDomainCheckResult,
    GateBReadinessChecker,
    GateBReadinessReport,
    GateBReadinessStatus,
)
from acash.gate_b.storage import (
    AuthoritativeGOLedger,
    LedgerStorageTransaction,
    StorageCommitContract,
    StorageEngineSignerProtocol,
    StoragePlatformUtils,
    WALJournal,
)

__all__ = [
    "AuthoritativeAbortRecordBlock",
    "AuthoritativeCommitRecordBlock",
    "AuthoritativeGOLedger",
    "AuthoritativeLedgerProtocol",
    "BrokerProbeSnapshot",
    "CryptographicVerificationError",
    "DataContractError",
    "DurablePointerTransitionRecord",
    "DurableTransactionState",
    "GateBDomainCheckResult",
    "GateBError",
    "GateBReadinessChecker",
    "GateBReadinessReport",
    "GateBReadinessStatus",
    "HumanGORecord",
    "JournalState",
    "LedgerStorageTransaction",
    "LiveAuthorization",
    "LiveAuthorizationStatus",
    "MT5QuoteSnapshot",
    "PreLiveRiskAdmissionError",
    "QuarantineError",
    "StorageCommitContract",
    "StorageDurabilityError",
    "StorageEngineSignerProtocol",
    "StoragePlatformUtils",
    "SystemSafetyMode",
    "WALJournal",
    "assert_activation_preconditions",
    "calculate_worst_case_notional",
    "verify_human_go_record_integrity",
]

