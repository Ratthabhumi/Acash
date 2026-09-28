# ACASH Broker Adapter Contract & Interface Specification V1 (Draft)

**Document:** `docs/ppds/BROKER_ADAPTER_CONTRACT_V1_DRAFT.md`
**System Module:** Broker Abstraction & Execution Gateway
**Stage:** R0 Architectural Contract Specification (Draft)
**Runtime Implementation Status:** `PPDS_RUNTIME_IMPLEMENTATION = NOT_AUTHORIZED / NOT_IMPLEMENTED`
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 3, 4, 11

> [!IMPORTANT]
> **ARCHITECTURAL DRAFT ONLY:**
> This document specifies target interface signatures and design invariants. No concrete broker adapter or execution code is implemented or authorized. Zero broker credentials exist or are tested in this task.

---

## 1. Executive Summary & Broker-Neutral Philosophy

To prevent architectural lock-in to any single custodian or execution venue, PPDS decouples all portfolio analytics, risk calculations, and tax ledger records from broker-native API idiosyncrasies.

The candidate **`BrokerAdapter`** interface establishes a standardized protocol for telemetry ingestion and reconciliation across disparate brokers (e.g. Dime! KKP, Webull Securities Thailand, Interactive Brokers, CME FCMs).

### Critical Safety Invariant (Target Design):
All execution-related capability flags (`CAN_SUBMIT_ORDER`, `CAN_REPLACE_ORDER`, `CAN_CANCEL_ORDER`) **default strictly to `false`** across all adapters in PPDS R0. The software interface enforces an immutable read-only firewall at the software layer.

---

## 2. Granular Broker Capability Flags

Every concrete adapter must explicitly declare its supported capabilities via a frozen capability set:

```python
from enum import Enum, auto
from dataclasses import dataclass

class BrokerCapability(Enum):
    # Read / Telemetry Capabilities
    CAN_READ_ACCOUNT = auto()
    CAN_READ_POSITIONS = auto()
    CAN_READ_ORDERS = auto()
    CAN_READ_FILLS = auto()
    CAN_READ_TRANSACTIONS = auto()
    CAN_READ_DIVIDENDS = auto()
    CAN_READ_FEES = auto()
    CAN_READ_FX = auto()
    CAN_READ_REMITTANCES = auto()
    CAN_READ_MARKET_DATA = auto()

    # Order-Writing / Execution Capabilities (LOCKED to False in R0)
    CAN_SUBMIT_ORDER = auto()
    CAN_REPLACE_ORDER = auto()
    CAN_CANCEL_ORDER = auto()

@dataclass(frozen=True)
class AdapterCapabilityManifest:
    adapter_name: str
    broker_code: str
    capabilities: frozenset[BrokerCapability]
    is_read_only: bool = True  # Strict target invariant for PPDS R0
```

---

## 3. Abstract `BrokerAdapter` Interface Definition

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class BrokerAdapter(ABC):
    """
    Standardized sovereign broker adapter contract (Target Architecture).
    Decouples custodian communication from ACASH portfolio logic.
    """

    @abstractmethod
    def get_capabilities(self) -> AdapterCapabilityManifest:
        """Return declared read and execution capabilities."""
        pass

    @abstractmethod
    def get_accounts(self) -> List["BrokerAccountDTO"]:
        """Retrieve all accounts under the authenticated credentials."""
        pass

    @abstractmethod
    def get_cash_balances(self, account_id: str) -> List["CashBalanceDTO"]:
        """Retrieve multi-currency cash balances (e.g. THB, USD, FCD)."""
        pass

    @abstractmethod
    def get_positions(self, account_id: str) -> List["PositionDTO"]:
        """Retrieve active security holdings and lot details."""
        pass

    @abstractmethod
    def get_transactions(
        self,
        account_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List["TransactionDTO"]:
        """Retrieve historical financial ledger transactions."""
        pass

    @abstractmethod
    def get_orders(
        self,
        account_id: str,
        start_time: Optional[datetime] = None
    ) -> List["OrderDTO"]:
        """Retrieve open, cancelled, and filled order records."""
        pass

    @abstractmethod
    def get_fills(
        self,
        account_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List["FillDTO"]:
        """Retrieve execution fill records with exact fee decompositions."""
        pass

    @abstractmethod
    def get_dividends(
        self,
        account_id: str,
        tax_year: int
    ) -> List["DividendDTO"]:
        """Retrieve dividend payments, foreign withholding taxes, and ex-dates."""
        pass

    @abstractmethod
    def get_fx_activity(
        self,
        account_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List["FXConversionDTO"]:
        """Retrieve currency conversions (THB <-> USD), rates, and spreads."""
        pass

    @abstractmethod
    def get_market_data_entitlements(self, account_id: str) -> List[str]:
        """Retrieve active real-time and delayed market data subscriptions."""
        pass

    # Execution Boundary (Fail-Closed Default in R0 Target Architecture)
    def submit_order(self, order_intent: "OrderIntentDTO") -> "OrderResultDTO":
        raise PermissionError("ORDER_WRITING_DISABLED: PPDS R0 is strictly read-only.")

    def cancel_order(self, order_id: str) -> bool:
        raise PermissionError("ORDER_WRITING_DISABLED: PPDS R0 is strictly read-only.")
```

---

## 4. Planned Candidate Adapters

### 4.1 `DimeAdapter` (File / Statement Ingestion)
- **Primary Transport:** Secure local parser ingesting official PDF statements, CSV trade confirmations, and exported ledger tables.
- **Capabilities:**
  - `CAN_READ_ACCOUNT`, `CAN_READ_POSITIONS`, `CAN_READ_TRANSACTIONS`, `CAN_READ_DIVIDENDS`, `CAN_READ_FX`.
  - Execution capabilities: `NONE` (Zero API order entry).
- **Function:** Reconciles US equity holdings and cash/FCD deposit accounts.

### 4.2 `WebullAdapter` (Open API Telemetry)
- **Primary Transport:**
  - REST HTTPS: Account inquiry, order inquiry, historical executions.
  - Server-streaming gRPC: Real-time trade event streaming (`TradeEvent` notifications).
  - WebSocket: Market data streaming (independent entitlement required).
- **Security & Authorization Status:**
  - `WEBULL_BROKER_SIDE_READ_ONLY_KEY = NOT_PRIMARY_SOURCE_CONFIRMED`.
  - `WEBULL_READ_ONLY_INTEGRATION = BLOCKED_PENDING_SECURITY_DESIGN`.
  - `WEBULL_UAT = DOCUMENTED_NOT_AUTHORIZED_FOR_USE`.
- **Capabilities (Proposed Target):**
  - Read telemetry only (`CAN_READ_ACCOUNT`, `CAN_READ_POSITIONS`, `CAN_READ_ORDERS`, `CAN_READ_FILLS`).
  - Order writing strictly disabled.

### 4.3 `FuturesBrokerAdapter` (FCM Integration)
- **Primary Transport:** FIX / Web API / Gateway socket to regulated CME clearing broker (IBKR candidate).
- **Capabilities (Proposed Target):**
  - `CAN_READ_POSITIONS`, `CAN_READ_FILLS`, `CAN_READ_CASH`, `CAN_READ_FEES`.
- **Function:** Micro futures position tracking, mark-to-market reconciliation, and margin utilization telemetry.

---

## 5. Security & Fail-Closed Invariants (Target Architecture)

1. **Zero Hardcoded Credentials:** Adapters must ingest credentials via OS-level secure credential stores (e.g. Windows DPAPI, system environment variables), never from source files or git history.
2. **Read-Only Verification Handshake:** Prior to initializing an API adapter, a self-test handshake must verify that the provided credential lacks order-placement permissions. If order submission is technically permitted by the API key and no broker-side constraint exists, the adapter raises `SecurityContractError` and halts.

---

## 6. Verification Ledger

- Contract Specification: COMPLETE (Draft Signatures)
- Implementation Truth: `PPDS_RUNTIME_IMPLEMENTATION = NOT_AUTHORIZED / NOT_IMPLEMENTED`
- Adapter Decoupling: BROKER-NEUTRAL
- Execution Gating: STRICT FAIL-CLOSED (Order placement hard-disabled in design)
- Security Boundary: Integration blocked pending broker-side read-only key confirmation
