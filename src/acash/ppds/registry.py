"""PPDS multi-account registry, portfolio consolidation, and internal transfer contract.

Pure, deterministic, read-only structures and functions. Fails closed on:
- Duplicate account registration or alias collisions
- Conflicting or legacy DEFAULT account identities in multi-account portfolios
- Mismatched as-of dates
- Evidence reference stealing/collisions across accounts
- Missing or inverted FX rates
- Unmatched or contradictory internal transfers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.ppds.exposure import FXRate, PortfolioValuation


@dataclass(frozen=True)
class AccountRegistration:
    """Explicit synthetic account identity bound to evidence and base currency."""

    portfolio_id: str
    account_id: str
    source_id: str
    as_of: date
    base_currency: str
    evidence_refs: Tuple[str, ...] = ()
    aliases: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        p_id = str(self.portfolio_id or "").strip()
        if not p_id:
            raise DataContractError("PPDS_ACCOUNT_PORTFOLIO_ID_EMPTY: portfolio_id cannot be blank.")

        a_id = str(self.account_id or "").strip()
        if not a_id:
            raise DataContractError("PPDS_ACCOUNT_ID_EMPTY: account_id cannot be blank.")

        s_id = str(self.source_id or "").strip()
        if not s_id:
            raise DataContractError("PPDS_ACCOUNT_SOURCE_ID_EMPTY: source_id cannot be blank.")

        if not isinstance(self.as_of, date):
            raise DataContractError(f"PPDS_ACCOUNT_AS_OF_INVALID: expected date, got {type(self.as_of).__name__}.")

        b_cur = str(self.base_currency or "").strip().upper()
        if len(b_cur) != 3 or not b_cur.isalpha():
            raise DataContractError(f"PPDS_ACCOUNT_BASE_CURRENCY_INVALID: '{self.base_currency}'.")

        # Normalize aliases
        clean_aliases = tuple(sorted({str(a).strip() for a in self.aliases if str(a).strip()}))
        object.__setattr__(self, "portfolio_id", p_id)
        object.__setattr__(self, "account_id", a_id)
        object.__setattr__(self, "source_id", s_id)
        object.__setattr__(self, "base_currency", b_cur)
        object.__setattr__(self, "aliases", clean_aliases)


@dataclass(frozen=True)
class AccountRegistry:
    """Immutable synthetic account registry enforcing isolation, lineage, and uniqueness."""

    portfolio_id: str
    accounts: Tuple[AccountRegistration, ...] = ()

    def __post_init__(self) -> None:
        p_id = str(self.portfolio_id or "").strip()
        if not p_id:
            raise DataContractError("PPDS_REGISTRY_PORTFOLIO_ID_EMPTY.")
        object.__setattr__(self, "portfolio_id", p_id)

    def register(self, account: AccountRegistration) -> AccountRegistry:
        """Register a new account into the portfolio registry with fail-closed invariants."""
        if account.portfolio_id != self.portfolio_id:
            raise DataContractError(
                f"PPDS_REGISTRY_PORTFOLIO_MISMATCH: account portfolio '{account.portfolio_id}' "
                f"!= registry portfolio '{self.portfolio_id}'."
            )

        # Disallow DEFAULT legacy identifier in multi-account portfolios
        if account.account_id.upper() == "DEFAULT" and len(self.accounts) > 0:
            raise DataContractError(
                "PPDS_REGISTRY_DEFAULT_ACCOUNT_FORBIDDEN: legacy 'DEFAULT' account cannot be used "
                "in a multi-account portfolio."
            )
        if any(acc.account_id.upper() == "DEFAULT" for acc in self.accounts):
            raise DataContractError(
                "PPDS_REGISTRY_DEFAULT_ACCOUNT_FORBIDDEN: cannot add additional accounts to a portfolio "
                "containing legacy 'DEFAULT' account."
            )

        # Check for duplicate account_id
        for existing in self.accounts:
            if existing.account_id == account.account_id:
                raise DataContractError(
                    f"PPDS_REGISTRY_DUPLICATE_ACCOUNT: account '{account.account_id}' already registered."
                )
            if account.as_of != existing.as_of:
                raise DataContractError(
                    f"PPDS_REGISTRY_AS_OF_MISMATCH: account '{account.account_id}' as_of {account.as_of.isoformat()} "
                    f"!= existing portfolio as_of {existing.as_of.isoformat()}."
                )

        # Check for alias collision or aliasing to an existing account
        all_existing_identifiers: Set[str] = set()
        for existing in self.accounts:
            all_existing_identifiers.add(existing.account_id)
            all_existing_identifiers.update(existing.aliases)

        new_identifiers = {account.account_id} | set(account.aliases)
        colliding = all_existing_identifiers & new_identifiers
        if colliding:
            raise DataContractError(
                f"PPDS_REGISTRY_ALIAS_COLLISION: identity conflict on {sorted(colliding)}."
            )

        # Check for evidence reference collision (prevent an account from stealing/claiming another's evidence)
        existing_evidence: Set[str] = set()
        for existing in self.accounts:
            existing_evidence.update(existing.evidence_refs)
        colliding_evidence = set(account.evidence_refs) & existing_evidence
        if colliding_evidence:
            raise DataContractError(
                f"PPDS_REGISTRY_EVIDENCE_COLLISION: account '{account.account_id}' claims evidence references "
                f"{sorted(colliding_evidence)} already bound to another account."
            )

        new_accounts = tuple(sorted(list(self.accounts) + [account], key=lambda a: a.account_id))
        return AccountRegistry(portfolio_id=self.portfolio_id, accounts=new_accounts)

    def get_account(self, account_id: str) -> AccountRegistration:
        """Find registered account by primary account_id or alias."""
        clean_id = str(account_id or "").strip()
        for acc in self.accounts:
            if acc.account_id == clean_id or clean_id in acc.aliases:
                return acc
        raise DataContractError(f"PPDS_REGISTRY_ACCOUNT_NOT_FOUND: '{account_id}'.")

    @property
    def account_ids(self) -> Tuple[str, ...]:
        return tuple(acc.account_id for acc in self.accounts)

    @property
    def as_of(self) -> Optional[date]:
        return self.accounts[0].as_of if self.accounts else None

    def __len__(self) -> int:
        return len(self.accounts)


@dataclass(frozen=True)
class CurrencyExposure:
    """Consolidated exposure summary for an individual currency in base currency."""

    currency: str
    net_local_amount: Decimal
    fx_rate_to_base: Decimal
    net_base_amount: Decimal
    weight_of_nav: Decimal


@dataclass(frozen=True)
class ConsolidatedPortfolioValuation:
    """Read-only deterministic multi-account valuation consolidated into explicit reporting currency."""

    portfolio_id: str
    as_of: date
    base_currency: str
    account_valuations: Dict[str, PortfolioValuation]
    per_account_nav: Dict[str, Decimal]
    consolidated_nav: Decimal
    total_cash_base: Decimal
    total_positions_net_base: Decimal
    total_positions_gross_base: Decimal
    currency_exposures: List[CurrencyExposure]
    evidence_refs: Tuple[str, ...]
    unresolved_status: Optional[str] = None


def consolidate_portfolio_valuations(
    registry: AccountRegistry,
    valuations: Mapping[str, PortfolioValuation],
    reporting_currency: str,
    fx_rates: Mapping[Tuple[str, str], FXRate],
) -> ConsolidatedPortfolioValuation:
    """Consolidate multiple per-account valuations into a single portfolio valuation (pure function).

    Fails closed on:
    - Empty registry
    - Missing valuation for any registered account
    - Mismatched as-of dates
    - Inverted, stale, or missing FX rates for account base -> reporting currency conversion
    - Double-counted or unmapped accounts
    """
    if len(registry) == 0:
        raise DataContractError("PPDS_CONSOLIDATION_EMPTY_REGISTRY: at least one account required.")

    clean_reporting = str(reporting_currency or "").strip().upper()
    if len(clean_reporting) != 3 or not clean_reporting.isalpha():
        raise DataContractError(f"PPDS_CONSOLIDATION_REPORTING_CURRENCY_INVALID: '{reporting_currency}'.")

    common_as_of = registry.as_of
    assert common_as_of is not None

    per_account_nav: Dict[str, Decimal] = {}
    total_cash_base = Decimal("0")
    total_positions_net_base = Decimal("0")
    total_positions_gross_base = Decimal("0")

    # Accumulate local net exposures per currency across all accounts
    net_cash_by_currency: Dict[str, Decimal] = {}
    net_pos_by_currency: Dict[str, Decimal] = {}

    evidence_set: Set[str] = set()

    for acc in registry.accounts:
        acc_id = acc.account_id
        if acc_id not in valuations:
            raise DataContractError(
                f"PPDS_CONSOLIDATION_VALUATION_MISSING: missing valuation for account '{acc_id}'."
            )
        val = valuations[acc_id]

        if val.as_of != common_as_of:
            raise DataContractError(
                f"PPDS_CONSOLIDATION_AS_OF_MISMATCH: account '{acc_id}' valuation as_of "
                f"{val.as_of.isoformat()} != registry as_of {common_as_of.isoformat()}."
            )

        if val.account_id != acc_id:
            raise DataContractError(
                f"PPDS_CONSOLIDATION_ACCOUNT_MISMATCH: valuation account '{val.account_id}' "
                f"!= registry account '{acc_id}'."
            )

        # FX multiplier from account valuation base currency to portfolio reporting currency
        acc_base = val.base_currency.upper()
        if acc_base == clean_reporting:
            fx_to_rep = Decimal("1")
        else:
            fx_key = (acc_base, clean_reporting)
            if fx_key not in fx_rates:
                raise DataContractError(
                    f"PPDS_CONSOLIDATION_FX_MISSING: missing rate {acc_base}->{clean_reporting} "
                    f"for account '{acc_id}'."
                )
            fx = fx_rates[fx_key]
            if fx.from_currency.upper() != acc_base or fx.to_currency.upper() != clean_reporting:
                raise DataContractError(
                    f"PPDS_CONSOLIDATION_FX_ORIENTATION_MISMATCH: FXRate internal {fx.from_currency}->{fx.to_currency} "
                    f"!= mapping key {acc_base}->{clean_reporting}."
                )
            if not fx.source_id or not fx.source_id.strip():
                raise DataContractError(
                    f"PPDS_CONSOLIDATION_FX_SOURCE_INVALID: FXRate {acc_base}->{clean_reporting} has blank source_id."
                )
            if fx.as_of != common_as_of:
                raise DataContractError(
                    f"PPDS_CONSOLIDATION_FX_AS_OF_MISMATCH: rate as_of {fx.as_of.isoformat()} != {common_as_of.isoformat()}."
                )
            if not isinstance(fx.rate, Decimal) or not fx.rate.is_finite() or fx.rate <= Decimal("0"):
                raise DataContractError(
                    f"PPDS_CONSOLIDATION_FX_RATE_INVALID: non-positive or non-finite rate for {acc_base}->{clean_reporting}."
                )
            fx_to_rep = fx.rate

        # Converted account NAV
        acc_nav_rep = val.total_portfolio_nav_base * fx_to_rep
        per_account_nav[acc_id] = acc_nav_rep

        total_cash_base += val.total_cash_base * fx_to_rep
        total_positions_net_base += val.total_positions_net_base * fx_to_rep
        total_positions_gross_base += val.total_positions_gross_base * fx_to_rep

        # Currency breakdown aggregation
        for curr, amt in val.cash_local.items():
            net_cash_by_currency[curr] = net_cash_by_currency.get(curr, Decimal("0")) + amt

        for pos in val.positions:
            curr = pos.pricing_currency.upper()
            net_pos_by_currency[curr] = net_pos_by_currency.get(curr, Decimal("0")) + pos.net_market_value_local

        # Evidence references
        evidence_set.update(acc.evidence_refs)

    consolidated_nav = sum(per_account_nav.values(), Decimal("0"))

    # Compute CurrencyExposure lines
    all_currencies = sorted(set(net_cash_by_currency) | set(net_pos_by_currency))
    currency_exposures: List[CurrencyExposure] = []
    for curr in all_currencies:
        net_local = net_cash_by_currency.get(curr, Decimal("0")) + net_pos_by_currency.get(curr, Decimal("0"))
        if curr == clean_reporting:
            curr_fx = Decimal("1")
        else:
            fx_k = (curr, clean_reporting)
            if fx_k not in fx_rates:
                raise DataContractError(
                    f"PPDS_CONSOLIDATION_CURRENCY_FX_MISSING: missing FX conversion {curr}->{clean_reporting}."
                )
            fx_obj = fx_rates[fx_k]
            if fx_obj.from_currency.upper() != curr or fx_obj.to_currency.upper() != clean_reporting:
                raise DataContractError(
                    f"PPDS_CONSOLIDATION_FX_ORIENTATION_MISMATCH: rate internal {fx_obj.from_currency}->{fx_obj.to_currency} "
                    f"!= mapping key {curr}->{clean_reporting}."
                )
            if not fx_obj.source_id or not fx_obj.source_id.strip():
                raise DataContractError(
                    f"PPDS_CONSOLIDATION_FX_SOURCE_INVALID: FXRate {curr}->{clean_reporting} has blank source_id."
                )
            if fx_obj.as_of != common_as_of:
                raise DataContractError(
                    f"PPDS_CONSOLIDATION_FX_AS_OF_MISMATCH: rate {curr}->{clean_reporting} as_of {fx_obj.as_of.isoformat()} "
                    f"!= {common_as_of.isoformat()}."
                )
            if not isinstance(fx_obj.rate, Decimal) or not fx_obj.rate.is_finite() or fx_obj.rate <= Decimal("0"):
                raise DataContractError(
                    f"PPDS_CONSOLIDATION_FX_RATE_INVALID: non-positive or non-finite rate for {curr}->{clean_reporting}."
                )
            curr_fx = fx_obj.rate

        net_base = net_local * curr_fx
        weight = (net_base / consolidated_nav) if consolidated_nav != Decimal("0") else Decimal("0")
        currency_exposures.append(CurrencyExposure(
            currency=curr,
            net_local_amount=net_local,
            fx_rate_to_base=curr_fx,
            net_base_amount=net_base,
            weight_of_nav=weight,
        ))

    return ConsolidatedPortfolioValuation(
        portfolio_id=registry.portfolio_id,
        as_of=common_as_of,
        base_currency=clean_reporting,
        account_valuations=dict(valuations),
        per_account_nav=per_account_nav,
        consolidated_nav=consolidated_nav,
        total_cash_base=total_cash_base,
        total_positions_net_base=total_positions_net_base,
        total_positions_gross_base=total_positions_gross_base,
        currency_exposures=currency_exposures,
        evidence_refs=tuple(sorted(evidence_set)),
        unresolved_status=None,
    )


# ---------------------------------------------------------------------------
# Phase 5: Internal Transfer Contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransferLeg:
    """Documented single side of an internal transfer (withdrawal from source or deposit to destination)."""

    account_id: str
    source_id: str
    transaction_id: str
    effective_date: date
    currency: str
    amount: Decimal
    asset_type: str = "CASH"  # CASH or SECURITY
    symbol: Optional[str] = None
    quantity: Optional[Decimal] = None
    evidence_ref: str = ""
    settled: bool = True

    def __post_init__(self) -> None:
        if not self.account_id or not self.account_id.strip():
            raise DataContractError("PPDS_TRANSFER_LEG_ACCOUNT_EMPTY.")
        if not self.source_id or not self.source_id.strip():
            raise DataContractError("PPDS_TRANSFER_LEG_SOURCE_EMPTY.")
        if not self.transaction_id or not self.transaction_id.strip():
            raise DataContractError("PPDS_TRANSFER_LEG_TX_ID_EMPTY.")
        if not isinstance(self.effective_date, date):
            raise DataContractError("PPDS_TRANSFER_LEG_DATE_INVALID.")
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite():
            raise DataContractError("PPDS_TRANSFER_LEG_AMOUNT_INVALID.")
        if self.asset_type not in {"CASH", "SECURITY"}:
            raise DataContractError(f"PPDS_TRANSFER_LEG_ASSET_TYPE_INVALID: '{self.asset_type}'.")
        if self.asset_type == "SECURITY" and (not self.symbol or not self.symbol.strip()):
            raise DataContractError("PPDS_TRANSFER_LEG_SECURITY_SYMBOL_MISSING.")


@dataclass(frozen=True)
class TransferEnvelope:
    """Complete internal transfer matching envelope between accounts."""

    transfer_id: str
    source_account_id: str
    destination_account_id: str
    asset_type: str
    currency: str
    effective_date: date
    status: str  # MATCHED, UNMATCHED_SOURCE_ONLY, UNMATCHED_DEST_ONLY, CROSS_CURRENCY_PENDING_FX, MISMATCHED_TERMS
    legs: Tuple[TransferLeg, ...]
    fee_amount: Decimal = Decimal("0")
    fx_rate: Optional[Decimal] = None
    evidence_refs: Tuple[str, ...] = ()
    notes: Tuple[str, ...] = ()


def validate_internal_transfer(
    source_leg: Optional[TransferLeg],
    dest_leg: Optional[TransferLeg],
    transfer_id: str,
    *,
    max_fee_allowed: Decimal = Decimal("0"),
    cross_currency_fx_rate: Optional[Decimal] = None,
) -> TransferEnvelope:
    """Validate and match two legs of an internal transfer.

    Guarantees:
    - Same-currency cash transfers require equal and opposite flows (source negative, dest positive)
      subject to explicit fee policy.
    - Security transfers require matching symbol and quantity without inventing tax lots.
    - Single-leg transfers are explicitly flagged as UNMATCHED without fabricating balancing entries.
    - Fails closed on identical source and destination accounts.
    """
    clean_tid = str(transfer_id or "").strip()
    if not clean_tid:
        raise DataContractError("PPDS_TRANSFER_ID_EMPTY.")

    if source_leg is None and dest_leg is None:
        raise DataContractError("PPDS_TRANSFER_EMPTY_LEGS: at least one leg required.")

    # Single-leg: Unmatched source
    if dest_leg is None:
        assert source_leg is not None
        return TransferEnvelope(
            transfer_id=clean_tid,
            source_account_id=source_leg.account_id,
            destination_account_id="",
            asset_type=source_leg.asset_type,
            currency=source_leg.currency,
            effective_date=source_leg.effective_date,
            status="UNMATCHED_SOURCE_ONLY",
            legs=(source_leg,),
            evidence_refs=(source_leg.evidence_ref,) if source_leg.evidence_ref else (),
            notes=("Missing destination counterpart leg; internal transfer incomplete.",),
        )

    # Single-leg: Unmatched dest
    if source_leg is None:
        return TransferEnvelope(
            transfer_id=clean_tid,
            source_account_id="",
            destination_account_id=dest_leg.account_id,
            asset_type=dest_leg.asset_type,
            currency=dest_leg.currency,
            effective_date=dest_leg.effective_date,
            status="UNMATCHED_DEST_ONLY",
            legs=(dest_leg,),
            evidence_refs=(dest_leg.evidence_ref,) if dest_leg.evidence_ref else (),
            notes=("Missing source counterpart leg; internal transfer incomplete.",),
        )

    # Both legs present:
    if source_leg.account_id == dest_leg.account_id:
        raise DataContractError(
            f"PPDS_TRANSFER_SAME_ACCOUNT: source and destination account cannot be identical ('{source_leg.account_id}')."
        )

    if source_leg.asset_type != dest_leg.asset_type:
        return TransferEnvelope(
            transfer_id=clean_tid,
            source_account_id=source_leg.account_id,
            destination_account_id=dest_leg.account_id,
            asset_type="MIXED",
            currency=source_leg.currency,
            effective_date=source_leg.effective_date,
            status="MISMATCHED_TERMS",
            legs=(source_leg, dest_leg),
            notes=(f"Conflicting asset types: source '{source_leg.asset_type}' vs dest '{dest_leg.asset_type}'.",),
        )

    ev_refs = tuple(sorted({ref for ref in (source_leg.evidence_ref, dest_leg.evidence_ref) if ref}))

    if source_leg.asset_type == "CASH":
        # Outflow from source must be negative; inflow to dest must be positive
        if source_leg.amount >= Decimal("0") or dest_leg.amount <= Decimal("0"):
            return TransferEnvelope(
                transfer_id=clean_tid,
                source_account_id=source_leg.account_id,
                destination_account_id=dest_leg.account_id,
                asset_type="CASH",
                currency=source_leg.currency,
                effective_date=source_leg.effective_date,
                status="MISMATCHED_TERMS",
                legs=(source_leg, dest_leg),
                notes=("Source amount must be negative outflow and dest amount must be positive inflow.",),
            )

        # Same currency transfer
        if source_leg.currency.upper() == dest_leg.currency.upper():
            outflow = abs(source_leg.amount)
            inflow = dest_leg.amount
            fee = outflow - inflow
            if fee < Decimal("0"):
                return TransferEnvelope(
                    transfer_id=clean_tid,
                    source_account_id=source_leg.account_id,
                    destination_account_id=dest_leg.account_id,
                    asset_type="CASH",
                    currency=source_leg.currency,
                    effective_date=source_leg.effective_date,
                    status="MISMATCHED_TERMS",
                    legs=(source_leg, dest_leg),
                    notes=("Destination inflow exceeds source outflow (negative fee).",),
                )
            if fee > max_fee_allowed:
                return TransferEnvelope(
                    transfer_id=clean_tid,
                    source_account_id=source_leg.account_id,
                    destination_account_id=dest_leg.account_id,
                    asset_type="CASH",
                    currency=source_leg.currency,
                    effective_date=source_leg.effective_date,
                    status="MISMATCHED_TERMS",
                    fee_amount=fee,
                    legs=(source_leg, dest_leg),
                    notes=(f"Fee {fee} exceeds maximum allowed fee {max_fee_allowed}.",),
                )

            return TransferEnvelope(
                transfer_id=clean_tid,
                source_account_id=source_leg.account_id,
                destination_account_id=dest_leg.account_id,
                asset_type="CASH",
                currency=source_leg.currency,
                effective_date=source_leg.effective_date,
                status="MATCHED",
                fee_amount=fee,
                legs=(source_leg, dest_leg),
                evidence_refs=ev_refs,
                notes=("Matched same-currency internal cash transfer.",),
            )
        else:
            # Cross-currency cash transfer
            if cross_currency_fx_rate is None or cross_currency_fx_rate <= Decimal("0"):
                return TransferEnvelope(
                    transfer_id=clean_tid,
                    source_account_id=source_leg.account_id,
                    destination_account_id=dest_leg.account_id,
                    asset_type="CASH",
                    currency=f"{source_leg.currency}->{dest_leg.currency}",
                    effective_date=source_leg.effective_date,
                    status="CROSS_CURRENCY_PENDING_FX",
                    legs=(source_leg, dest_leg),
                    evidence_refs=ev_refs,
                    notes=("Cross-currency transfer requires explicit conversion rate.",),
                )

            return TransferEnvelope(
                transfer_id=clean_tid,
                source_account_id=source_leg.account_id,
                destination_account_id=dest_leg.account_id,
                asset_type="CASH",
                currency=f"{source_leg.currency}->{dest_leg.currency}",
                effective_date=source_leg.effective_date,
                status="MATCHED_CROSS_CURRENCY",
                fx_rate=cross_currency_fx_rate,
                legs=(source_leg, dest_leg),
                evidence_refs=ev_refs,
                notes=(f"Matched cross-currency transfer with rate {cross_currency_fx_rate}.",),
            )

    else:
        # SECURITY transfer
        if (source_leg.symbol or "").upper() != (dest_leg.symbol or "").upper():
            return TransferEnvelope(
                transfer_id=clean_tid,
                source_account_id=source_leg.account_id,
                destination_account_id=dest_leg.account_id,
                asset_type="SECURITY",
                currency=source_leg.currency,
                effective_date=source_leg.effective_date,
                status="MISMATCHED_TERMS",
                legs=(source_leg, dest_leg),
                notes=(f"Mismatched symbols: source '{source_leg.symbol}' vs dest '{dest_leg.symbol}'.",),
            )

        src_qty = source_leg.quantity or Decimal("0")
        dst_qty = dest_leg.quantity or Decimal("0")
        if src_qty >= Decimal("0") or dst_qty <= Decimal("0"):
            return TransferEnvelope(
                transfer_id=clean_tid,
                source_account_id=source_leg.account_id,
                destination_account_id=dest_leg.account_id,
                asset_type="SECURITY",
                currency=source_leg.currency,
                effective_date=source_leg.effective_date,
                status="MISMATCHED_TERMS",
                legs=(source_leg, dest_leg),
                notes=("Security transfer source quantity must be negative and dest quantity positive.",),
            )

        if abs(src_qty) != dst_qty:
            return TransferEnvelope(
                transfer_id=clean_tid,
                source_account_id=source_leg.account_id,
                destination_account_id=dest_leg.account_id,
                asset_type="SECURITY",
                currency=source_leg.currency,
                effective_date=source_leg.effective_date,
                status="MISMATCHED_TERMS",
                legs=(source_leg, dest_leg),
                notes=(f"Quantity mismatch: outflow {abs(src_qty)} != inflow {dst_qty}.",),
            )

        return TransferEnvelope(
            transfer_id=clean_tid,
            source_account_id=source_leg.account_id,
            destination_account_id=dest_leg.account_id,
            asset_type="SECURITY",
            currency=source_leg.currency,
            effective_date=source_leg.effective_date,
            status="MATCHED",
            legs=(source_leg, dest_leg),
            evidence_refs=ev_refs,
            notes=("Matched security transfer with preserved share count.",),
        )
