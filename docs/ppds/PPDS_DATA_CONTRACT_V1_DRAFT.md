# ACASH PPDS Data Contract & Entity Specification V1 (Draft)

**Document:** `docs/ppds/PPDS_DATA_CONTRACT_V1_DRAFT.md`
**System Module:** Data Modeling & Domain Schemas
**Stage:** R0 Technical Contract Draft
**Date Context:** 2026-09-28
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 4, 7, 13

---

## 1. Executive Summary & Modeling Principles

The **PPDS Data Contract** defines the canonical data transfer objects (DTOs) and persistent domain schemas governing the Personal Portfolio Decision Support system.

### Core Data Integrity Invariants:
1. **Preserve Broker-Native Identifiers:** Never discard or overwrite custodian order IDs, execution IDs, or transaction numbers. Every domain record must retain a direct pointer to its raw broker source payload.
2. **Double-Entry Financial Discipline:** Every cash movement, trade execution, dividend payment, and fee deduction must balance across asset and cash accounts.
3. **Multi-Currency Purity:** Balances and transactions are stored in their native currency (`USD`, `THB`, `EUR`) alongside an authoritative exchange rate lineage (e.g. Bank of Thailand or Commercial Bank Daily Rate under Section 9 of the Thai Revenue Code). Never store single un-attributed converted values.

---

## 2. Canonical Domain Entity Schemas

```python
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum, auto

# ==============================================================================
# 1. Accounts & Capabilities
# ==============================================================================

class BrokerType(Enum):
    DIME_KKP = "DIME_KKP"
    WEBULL_TH = "WEBULL_TH"
    INTERACTIVE_BROKERS = "INTERACTIVE_BROKERS"
    NINJATRADER = "NINJATRADER"
    CME_FCM_GENERIC = "CME_FCM_GENERIC"

@dataclass(frozen=True)
class BrokerAccount:
    account_id: str                   # System canonical account ID (e.g. DIME-ACC-01)
    broker_native_account_id: str     # Masked custodian account number
    broker_type: BrokerType
    currency_primary: str             # e.g. "USD" or "THB"
    opened_date: Optional[date]
    is_active: bool
    source_lineage_digest: str

@dataclass(frozen=True)
class CashBalance:
    account_id: str
    currency: str                     # USD, THB, etc.
    settled_cash: Decimal
    unsettled_cash: Decimal
    accrued_cash: Decimal
    total_cash: Decimal
    as_of_timestamp_utc: datetime

# ==============================================================================
# 2. Positions & Tax Lots
# ==============================================================================

@dataclass(frozen=True)
class PositionLot:
    lot_id: str
    account_id: str
    symbol: str
    acquired_timestamp: datetime
    quantity: Decimal
    cost_basis_per_unit_native: Decimal
    cost_basis_native_currency: str
    tax_fx_method: str                 # BOT_REFERENCE or COMMERCIAL_BANK_DAILY
    tax_fx_rate: Decimal
    tax_fx_source: str                 # e.g. "BOT", "SCB"
    source_fill_id: str

@dataclass(frozen=True)
class Position:
    account_id: str
    book_id: str                      # CORE, SATELLITE, SPECULATIVE, TACTICAL, FUTURES
    symbol: str
    quantity: Decimal
    market_price_native: Decimal
    market_value_native: Decimal
    native_currency: str
    unrealized_pnl_native: Decimal
    as_of_timestamp_utc: datetime
    lots: List[PositionLot]

# ==============================================================================
# 3. Orders, Fills & Transactions
# ==============================================================================

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderState(Enum):
    PROPOSED = "PROPOSED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

@dataclass(frozen=True)
class Order:
    order_id: str                     # System canonical order ID
    broker_native_order_id: Optional[str]
    account_id: str
    book_id: str
    symbol: str
    side: OrderSide
    order_type: str                   # MARKET, LIMIT, STOP_LIMIT
    specified_quantity: Optional[Decimal]
    specified_amount_native: Optional[Decimal] # Amount-based orders (Dime)
    limit_price_native: Optional[Decimal]
    state: OrderState
    created_at_utc: datetime
    updated_at_utc: datetime

@dataclass(frozen=True)
class Fill:
    fill_id: str
    order_id: str
    broker_native_fill_id: str
    account_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    price_native: Decimal
    gross_consideration: Decimal
    commission_native: Decimal
    regulatory_fees_native: Decimal
    net_consideration: Decimal
    native_currency: str
    executed_at_utc: datetime
    source_document_sha256: str

# ==============================================================================
# 4. Corporate Actions & Dividends
# ==============================================================================

@dataclass(frozen=True)
class Dividend:
    dividend_id: str
    account_id: str
    symbol: str
    ex_date: date
    record_date: date
    payable_date: date
    gross_amount_usd: Decimal
    withholding_tax_usd: Decimal
    net_amount_usd: Decimal
    withholding_tax_rate: Decimal      # e.g. 0.1500 (15% per DTA Art. 10 via W-8BEN)
    tax_fx_method: str                 # BOT_REFERENCE or COMMERCIAL_BANK_DAILY
    tax_fx_rate: Decimal
    tax_fx_source: str                 # e.g. "BOT", "SCB"
    net_amount_thb: Decimal
    official_sponsor_source: str       # BLACKROCK_ISHARES_OFFICIAL, etc.

# ==============================================================================
# 5. Multi-Book & Capital Allocation
# ==============================================================================

class BookCategory(Enum):
    INVESTMENT_CORE = "INVESTMENT_CORE"
    INVESTMENT_SATELLITE = "INVESTMENT_SATELLITE"
    INVESTMENT_SPECULATIVE = "INVESTMENT_SPECULATIVE"
    TRADING_EQUITY_TACTICAL = "TRADING_EQUITY_TACTICAL"
    TRADING_FUTURES_MACRO = "TRADING_FUTURES_MACRO"

@dataclass(frozen=True)
class PortfolioBook:
    book_id: str
    category: BookCategory
    target_capital_ceiling_usd: Optional[Decimal]
    target_capital_floor_usd: Optional[Decimal]
    max_drawdown_limit: Decimal
    max_position_concentration: Decimal
    benchmark_symbol: str
    is_active: bool

@dataclass(frozen=True)
class CapitalTransfer:
    transfer_id: str
    from_book_id: str
    to_book_id: str
    amount_usd: Decimal
    authorized_by: str                 # OPERATOR_EXPLICIT_SIGNATURE
    authorization_token_id: str
    executed_at_utc: datetime
    transfer_rationale: str

# ==============================================================================
# 6. Decision Support Output (Decoupled Investment vs Trading)
# ==============================================================================

class RecommendationState(Enum):
    BUY_CANDIDATE = "BUY_CANDIDATE"
    HOLD = "HOLD"
    REDUCE_REVIEW = "REDUCE_REVIEW"
    NO_ACTION = "NO_ACTION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

@dataclass(frozen=True)
class InvestmentRecommendationDTO:
    """
    Long-term investment recommendation envelope.
    Does NOT use short-term price stops. Governed by fundamental review and thesis criteria.
    """
    recommendation_id: str
    book_id: str
    symbol: str
    state: RecommendationState
    evaluation_timestamp_utc: datetime
    thesis_statement: str
    thesis_review_conditions: List[str]
    target_allocation_envelope_pct: Decimal
    valuation_evidence_digest: str
    portfolio_concentration_impact: Decimal
    target_custodian: str
    is_reviewed_by_human: bool = False

@dataclass(frozen=True)
class TradingRecommendationDTO:
    """
    Tactical trading recommendation envelope.
    Governed by explicit structural price invalidation and dollar risk limits.
    """
    recommendation_id: str
    book_id: str
    symbol: str
    state: RecommendationState
    evaluation_timestamp_utc: datetime
    entry_level: Decimal
    price_invalidation_stop: Decimal
    stop_distance: Decimal
    recommended_dollar_risk: Decimal
    target_time_horizon: str
    target_broker_code: str
    evidence_reference_digest: str
    is_reviewed_by_human: bool = False
```

---

## 3. Storage & Cryptographic Lineage (Target Design Invariants)

> **STATUS NOTICE:**
> ```text
> PPDS_RUNTIME_IMPLEMENTATION = NOT_AUTHORIZED / NOT_IMPLEMENTED
> ```
> All data contracts in this document represent **DRAFT ARCHITECTURAL SPECIFICATIONS** and target invariants. No runtime database, serialization engine, or active background process is currently authorized or implemented.

- **Target Invariant:** All domain DTOs will serialize deterministically via byte-exact JSON schemas.
- **Target Invariant:** In production implementation, records will be indexed by their SHA-256 state hashes, ensuring that external modifications break cryptographic lineage.
- **Target Invariant:** Execution capabilities remain strictly fail-closed at the interface layer.

---

## 4. Verification Ledger

- Domain Model Scope: DRAFT SPECIFICATION (21 Canonical Entities Defined)
- Multi-Currency Support: PRESERVED (Section 9 Flexible Tax FX Schema)
- Recommendation Schemas: DECOUPLED (Investment Thesis vs Trading Invalidation)
- Runtime Implementation Status: `NOT_AUTHORIZED / NOT_IMPLEMENTED`
- Execution Gating: STRICT FAIL-CLOSED DESIGN ($0.00 / NO REAL ORDERS)
