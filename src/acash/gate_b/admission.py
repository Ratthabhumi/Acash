"""Phase 13 Slice 2: Pre-Live Risk Admission & Deep Verification Engine (Stage 3.3).

Implements the 9-stage sequential pre-live risk admission decision pipeline:
1. Safety Mode Guard: Checks SystemSafetyMode under consistent lock boundary.
2. Snapshot Reader Boundary: Reads active committed snapshot under same lock.
3. LiveAuthorization & Currency Basis Assertion: Status, symbol, strategy, account, expiry, and USD basis.
4. Deterministic Position Size Bounding: Strict min(auth, gov) precedence; fails closed if undefined.
5. HumanGO Cryptographic Re-Verification: Self-digest, active trust store key, Ed25519 signature, lineage digests.
6. Ledger-Head Continuity Assertion: Asserts snapshot head and current ledger head match active record.
7. MT5 Quote Freshness & Spread Invariants: Symbol match, age >= 0, age <= max_quote_age_ms, ask >= bid.
8. max_slippage_points & Worst-Case Notional Bounding:
   - slippage_price_delta = points * point_size [quote price units]
   - monetary_slippage_allowance = quantity * contract_size * slippage_price_delta [USD]
   - worst_case_price = quote.ask + delta (BUY) or quote.bid - delta (SELL) > 0
   - bounded_notional = quantity * contract_size * worst_case_price <= max_notional_usd
9. Pre-Live Risk Admission Decision: Emits frozen, immutable decision with canonical digest.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import logging
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.enums import OrderSide
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.crypto import Ed25519TrustStore, TrustStoreEntryStatus
from acash.gate_b.exceptions import (
    CryptographicVerificationError,
    DataContractError,
    PreLiveRiskAdmissionError,
)
from acash.gate_b.readers import SnapshotReaderService, _resolve_transaction_context
from acash.gate_b.schema import (
    LiveAuthorizationStatus,
    MT5QuoteSnapshot,
    SystemSafetyMode,
)
from acash.gate_b.storage import (
    AuthoritativeGOLedger,
    LedgerStorageTransaction,
)

logger = logging.getLogger(__name__)

__all__ = [
    "GateBOrderAdmissionRequest",
    "PreLiveRiskAdmissionDecision",
    "PreLiveRiskAdmissionService",
]


class GateBOrderAdmissionRequest(BaseModel):
    """Immutable client request to evaluate pre-live risk admission."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(description="Unique client/strategy admission request identifier.")
    strategy_id: str = Field(description="Originating strategy identifier.")
    symbol: str = Field(description="Normalized tradeable asset symbol.")
    side: OrderSide = Field(description="Trade direction ('BUY' or 'SELL').")
    quantity: Decimal = Field(gt=Decimal("0"), description="Requested order volume in lots.")
    quote: MT5QuoteSnapshot = Field(description="Authoritative MT5 broker quote observation.")
    account_id: Optional[str] = Field(default=None, description="Target broker account ID.")
    account_currency: str = Field(
        default="USD",
        description="Broker account base currency; MUST be USD for Phase 13.",
    )


class PreLiveRiskAdmissionDecision(BaseModel):
    """Immutable, cryptographically bound pre-live risk admission verdict."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str = Field(description="Deterministic admission decision identifier.")
    is_admitted: bool = Field(description="Strict boolean admission verdict.")
    decision_timestamp_utc: datetime = Field(description="Strict UTC timestamp of evaluation.")
    authorization_id: str = Field(description="Bound LiveAuthorization ID.")
    activation_transaction_id: UUID = Field(description="Bound storage transaction ID.")
    strategy_id: str = Field(description="Admitted strategy identifier.")
    symbol: str = Field(description="Admitted instrument symbol.")
    side: OrderSide = Field(description="Admitted order side.")
    quantity: Decimal = Field(description="Admitted volume in lots.")
    effective_max_position_size: Decimal = Field(
        description="Enforced strictest position size ceiling in lots."
    )
    currency_basis: str = Field(description="Monetary currency basis (strictly USD).")
    reference_price: Decimal = Field(
        description="Market price evaluated (ask for BUY, bid for SELL)."
    )
    slippage_price_delta: Decimal = Field(
        description="Maximum price slippage allowance in quote price units."
    )
    monetary_slippage_allowance: Decimal = Field(
        description="Total monetary slippage allowance in account currency (USD)."
    )
    worst_case_price: Decimal = Field(
        description="Execution price including maximum authorized slippage delta."
    )
    bounded_executable_notional: Decimal = Field(
        description="Total worst-case exposure in account currency (USD)."
    )
    max_notional_usd: Decimal = Field(description="Authorized notional threshold in USD.")
    quote_age_ms: float = Field(description="Measured quote age at evaluation in milliseconds.")
    head_digest: str = Field(description="Verified ledger head digest.")
    decision_digest: str = Field(
        description="SHA-256 digest over canonical decision payload."
    )


class PreLiveRiskAdmissionService:
    """Authoritative Pre-Live Risk Admission Engine for Gate B (§4, B12–B45)."""

    @staticmethod
    def evaluate_admission(
        storage: Union[LedgerStorageTransaction, AuthoritativeGOLedger],
        request: GateBOrderAdmissionRequest,
        trust_store: Ed25519TrustStore,
        ledger: Optional[AuthoritativeGOLedger] = None,
        *,
        max_position_size: Optional[Decimal] = None,
        now_utc: Optional[datetime] = None,
    ) -> PreLiveRiskAdmissionDecision:
        """Evaluate order admission against full cryptographic, risk, and bounding contracts.

        All state reads (safety mode, active snapshot, ledger head) execute under
        the EXACT SAME consistent lock boundary (Invariant 1).
        Fails closed with PreLiveRiskAdmissionError on any contract breach.
        """
        current_time = now_utc or datetime.now(timezone.utc)
        if current_time.tzinfo is None or current_time.utcoffset() != timezone.utc.utcoffset(None):
            raise DataContractError(f"Current time {current_time} must be explicit UTC-aware")

        with _resolve_transaction_context(storage) as tx:
            # =================================================================
            # STAGE 1: Safety Mode Guard
            # =================================================================
            safety_mode = tx.get_system_safety_mode()
            if safety_mode == SystemSafetyMode.QUARANTINE_LOCKED:
                raise PreLiveRiskAdmissionError(
                    "SYSTEM_QUARANTINED_PENDING_FORENSIC_AUDIT"
                )

            # =================================================================
            # STAGE 2: Snapshot Reader Boundary (under same lock)
            # =================================================================
            try:
                active_view = SnapshotReaderService.read_active_committed_snapshot(tx)
            except Exception as snap_exc:
                raise PreLiveRiskAdmissionError(
                    f"ACTIVE_COMMITTED_SNAPSHOT_UNAVAILABLE: {snap_exc}"
                ) from snap_exc

            auth = active_view.authorization
            if auth is None:
                raise PreLiveRiskAdmissionError(
                    "AUTHORIZATION_DESYNC: Active authorization missing from snapshot"
                )

            # =================================================================
            # STAGE 3: LiveAuthorization & Currency Basis Assertion
            # =================================================================
            if auth.status != LiveAuthorizationStatus.ACTIVE:
                raise PreLiveRiskAdmissionError(
                    f"AUTHORIZATION_INACTIVE: Current status is {auth.status}"
                )

            if request.strategy_id != auth.strategy_id:
                raise PreLiveRiskAdmissionError(
                    f"STRATEGY_MISMATCH: Request strategy '{request.strategy_id}' "
                    f"!= Authorized '{auth.strategy_id}'"
                )

            if request.symbol != auth.symbol:
                raise PreLiveRiskAdmissionError(
                    f"SYMBOL_MISMATCH: Request symbol '{request.symbol}' "
                    f"!= Authorized '{auth.symbol}'"
                )

            if request.account_id is not None and request.account_id != auth.account_id:
                raise PreLiveRiskAdmissionError(
                    f"ACCOUNT_MISMATCH: Request account '{request.account_id}' "
                    f"!= Authorized '{auth.account_id}'"
                )

            if current_time >= auth.expires_at:
                raise PreLiveRiskAdmissionError(
                    f"AUTHORIZATION_EXPIRED: Current time {current_time.isoformat()} "
                    f">= Expiry {auth.expires_at.isoformat()}"
                )

            # Explicit Currency Basis Alignment Invariant:
            # account_currency ("USD") == quote_currency_basis ("USD") == max_notional_usd basis ("USD")
            if request.account_currency != "USD":
                raise PreLiveRiskAdmissionError(
                    f"CURRENCY_BASIS_MISMATCH: Account currency '{request.account_currency}' "
                    f"must be 'USD' for Phase 13"
                )

            if not request.symbol.endswith("USD"):
                raise PreLiveRiskAdmissionError(
                    f"CURRENCY_BASIS_MISMATCH: Symbol '{request.symbol}' quote currency "
                    f"is not 'USD'; direct USD notional calculation invalid"
                )

            # =================================================================
            # STAGE 4: Deterministic Position Size Bounding
            # =================================================================
            raw_auth_limit = getattr(auth, "max_position_size", None)
            raw_gov_limit = max_position_size

            auth_limit: Optional[Decimal] = None
            if raw_auth_limit is not None:
                if not isinstance(raw_auth_limit, Decimal):
                    try:
                        auth_limit = Decimal(str(raw_auth_limit))
                    except Exception as exc:
                        raise PreLiveRiskAdmissionError(
                            f"INVALID_AUTHORIZATION_POSITION_LIMIT: auth.max_position_size invalid: {exc}"
                        ) from exc
                else:
                    auth_limit = raw_auth_limit

                if auth_limit <= Decimal("0"):
                    raise PreLiveRiskAdmissionError(
                        f"INVALID_AUTHORIZATION_POSITION_LIMIT: auth.max_position_size ({auth_limit}) must be positive"
                    )

            gov_limit: Optional[Decimal] = None
            if raw_gov_limit is not None:
                if not isinstance(raw_gov_limit, Decimal):
                    try:
                        gov_limit = Decimal(str(raw_gov_limit))
                    except Exception as exc:
                        raise PreLiveRiskAdmissionError(
                            f"INVALID_GOVERNANCE_POSITION_LIMIT: governance max_position_size invalid: {exc}"
                        ) from exc
                else:
                    gov_limit = raw_gov_limit

                if gov_limit <= Decimal("0"):
                    raise PreLiveRiskAdmissionError(
                        f"INVALID_GOVERNANCE_POSITION_LIMIT: governance max_position_size ({gov_limit}) must be positive"
                    )

            if auth_limit is not None and gov_limit is not None:
                effective_limit = min(auth_limit, gov_limit)
            elif auth_limit is not None:
                effective_limit = auth_limit
            elif gov_limit is not None:
                effective_limit = gov_limit
            else:
                raise PreLiveRiskAdmissionError(
                    "MAX_POSITION_SIZE_UNDEFINED: No valid position size ceiling defined in authorization or governance parameters"
                )

            if request.quantity <= Decimal("0"):
                raise PreLiveRiskAdmissionError(
                    f"INVALID_ORDER_QUANTITY: Requested quantity ({request.quantity}) must be positive"
                )

            if request.quantity > effective_limit:
                raise PreLiveRiskAdmissionError(
                    f"MAX_POSITION_SIZE_BREACH: Requested quantity ({request.quantity}) "
                    f"exceeds effective position size ceiling ({effective_limit})"
                )

            # =================================================================
            # STAGE 5: HumanGO Cryptographic Re-Verification
            # =================================================================
            bound_record = active_view.record
            if bound_record is None:
                raise PreLiveRiskAdmissionError(
                    "AUTHORIZATION_DESYNC: Active HumanGORecord missing from snapshot"
                )

            # 5.1 Self-digest validation
            calc_digest = bound_record.compute_canonical_digest()
            if calc_digest != bound_record.record_digest:
                raise CryptographicVerificationError(
                    f"GO_RECORD_DIGEST_CORRUPTED: Calculated {calc_digest} != Recorded {bound_record.record_digest}"
                )

            # 5.2 Approver key trust store resolution and status
            try:
                entry = trust_store.resolve(
                    bound_record.approver_public_key_id,
                    at_time=bound_record.record_timestamp_utc,
                )
            except Exception as res_exc:
                raise CryptographicVerificationError(
                    f"APPROVER_KEY_REVOKED_OR_UNRESOLVED: Key ID '{bound_record.approver_public_key_id}': {res_exc}"
                ) from res_exc

            if entry is None or entry.status != TrustStoreEntryStatus.ACTIVE:
                raise CryptographicVerificationError(
                    f"APPROVER_KEY_REVOKED_OR_UNRESOLVED: Key ID '{bound_record.approver_public_key_id}'"
                )

            # 5.3 Signature re-verification
            try:
                bound_record.verify_signature(trust_store)
            except Exception as sig_exc:
                raise CryptographicVerificationError(
                    f"HUMAN_GO_SIGNATURE_INVALID: {sig_exc}"
                ) from sig_exc

            # 5.4 Lineage and digest bindings
            if bound_record.record_digest != auth.active_go_record_digest:
                raise PreLiveRiskAdmissionError(
                    f"AUTHORIZATION_DESYNC: Ledger record digest {bound_record.record_digest} "
                    f"!= auth.active_go_record_digest {auth.active_go_record_digest}"
                )

            if bound_record.authorization_id != auth.authorization_id:
                raise PreLiveRiskAdmissionError(
                    f"AUTHORIZATION_DESYNC: Ledger record authorization_id {bound_record.authorization_id} "
                    f"!= auth.authorization_id {auth.authorization_id}"
                )

            if bound_record.approved_authorization_digest != auth.approved_authorization_digest:
                raise PreLiveRiskAdmissionError(
                    f"AUTHORIZATION_DESYNC: Ledger record approved_authorization_digest "
                    f"{bound_record.approved_authorization_digest} != auth.approved_authorization_digest {auth.approved_authorization_digest}"
                )

            if auth.source_approved_digest != bound_record.approved_authorization_digest:
                raise PreLiveRiskAdmissionError(
                    f"AUTHORIZATION_DESYNC: Active authorization source_approved_digest "
                    f"{auth.source_approved_digest} != bound_record.approved_authorization_digest {bound_record.approved_authorization_digest}"
                )

            # =================================================================
            # STAGE 6: Ledger-Head Continuity Assertion
            # =================================================================
            if active_view.head_digest != bound_record.record_digest:
                raise PreLiveRiskAdmissionError(
                    f"AUTHORIZATION_DESYNC: Snapshot head digest {active_view.head_digest} "
                    f"!= bound record digest {bound_record.record_digest}"
                )

            current_head = tx.current_head_digest
            if current_head != bound_record.record_digest:
                raise PreLiveRiskAdmissionError(
                    f"AUTHORIZATION_DESYNC: Authoritative ledger head {current_head} "
                    f"has advanced beyond active record {bound_record.record_digest}"
                )

            if ledger is not None and ledger.current_head_digest != bound_record.record_digest:
                raise PreLiveRiskAdmissionError(
                    f"AUTHORIZATION_DESYNC: Ledger instance head {ledger.current_head_digest} "
                    f"has advanced beyond active record {bound_record.record_digest}"
                )

            # =================================================================
            # STAGE 7: MT5 Quote Freshness & Spread Invariants
            # =================================================================
            quote = request.quote
            if quote.symbol != auth.symbol:
                raise PreLiveRiskAdmissionError(
                    f"QUOTE_SYMBOL_MISMATCH: Quote symbol '{quote.symbol}' "
                    f"!= Authorized '{auth.symbol}'"
                )

            if auth.max_quote_age_ms is None or auth.max_quote_age_ms <= 0:
                raise PreLiveRiskAdmissionError(
                    "MANDATORY_PARAMETER_MISSING: auth.max_quote_age_ms undefined or non-positive"
                )
            if auth.max_slippage_points is None or auth.max_slippage_points <= 0:
                raise PreLiveRiskAdmissionError(
                    "MANDATORY_PARAMETER_MISSING: auth.max_slippage_points undefined or non-positive"
                )

            quote.assert_valid_and_fresh(max_quote_age_ms=auth.max_quote_age_ms)
            quote_age_ms = (current_time - quote.timestamp_utc).total_seconds() * 1000.0

            # =================================================================
            # STAGE 8: max_slippage_points & Worst-Case Notional Bounding
            # =================================================================
            # Invariant: slippage_price_delta is in quote price units
            slippage_price_delta = Decimal(str(auth.max_slippage_points)) * quote.point_size
            monetary_slippage_allowance = (
                request.quantity * quote.contract_size * slippage_price_delta
            )

            if request.side == OrderSide.BUY:
                reference_price = quote.ask
                worst_case_price = quote.ask + slippage_price_delta
            elif request.side == OrderSide.SELL:
                reference_price = quote.bid
                worst_case_price = quote.bid - slippage_price_delta
            else:
                raise PreLiveRiskAdmissionError(f"UNSUPPORTED_ORDER_SIDE: {request.side}")

            if worst_case_price <= Decimal("0"):
                raise PreLiveRiskAdmissionError(
                    f"INVALID_WORST_CASE_EXECUTION_PRICE: Computed worst-case price "
                    f"{worst_case_price} is non-positive (Reference: {reference_price}, "
                    f"Slippage Delta: {slippage_price_delta})"
                )

            order_units = request.quantity * quote.contract_size
            bounded_executable_notional = order_units * worst_case_price

            if bounded_executable_notional > auth.max_notional_usd:
                raise PreLiveRiskAdmissionError(
                    f"WORST_CASE_NOTIONAL_BREACH: Bounded executable notional {bounded_executable_notional} "
                    f"exceeds limit {auth.max_notional_usd} (Nominal: {order_units * reference_price})"
                )

            # =================================================================
            # STAGE 9: Pre-Live Risk Admission Decision
            # =================================================================
            decision_payload = {
                "request_id": request.request_id,
                "authorization_id": auth.authorization_id,
                "activation_transaction_id": str(active_view.transaction_id),
                "strategy_id": request.strategy_id,
                "symbol": request.symbol,
                "side": request.side.value,
                "quantity": str(request.quantity),
                "effective_max_position_size": str(effective_limit),
                "currency_basis": "USD",
                "reference_price": str(reference_price),
                "slippage_price_delta": str(slippage_price_delta),
                "monetary_slippage_allowance": str(monetary_slippage_allowance),
                "worst_case_price": str(worst_case_price),
                "bounded_executable_notional": str(bounded_executable_notional),
                "max_notional_usd": str(auth.max_notional_usd),
                "quote_age_ms": f"{quote_age_ms:.1f}",
                "head_digest": current_head,
                "decision_timestamp_utc": current_time.isoformat(),
            }
            canonical_bytes = CanonicalConfigSerializer.to_canonical_json(decision_payload).encode(
                "utf-8"
            )
            decision_digest = hashlib.sha256(canonical_bytes).hexdigest()
            decision_id = f"ADM_{decision_digest[:16].upper()}"

            return PreLiveRiskAdmissionDecision(
                decision_id=decision_id,
                is_admitted=True,
                decision_timestamp_utc=current_time,
                authorization_id=auth.authorization_id,
                activation_transaction_id=active_view.transaction_id,
                strategy_id=request.strategy_id,
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                effective_max_position_size=effective_limit,
                currency_basis="USD",
                reference_price=reference_price,
                slippage_price_delta=slippage_price_delta,
                monetary_slippage_allowance=monetary_slippage_allowance,
                worst_case_price=worst_case_price,
                bounded_executable_notional=bounded_executable_notional,
                max_notional_usd=auth.max_notional_usd,
                quote_age_ms=quote_age_ms,
                head_digest=current_head,
                decision_digest=decision_digest,
            )
