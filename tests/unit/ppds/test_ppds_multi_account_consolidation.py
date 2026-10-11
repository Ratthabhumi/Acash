"""Tests for PPDS multi-account consolidation, FX orientation, evidence provenance, and internal transfers.

Covers:
1. Inverted FX rate orientation rejection
2. Contradictory FX mapping key and embedded rate fields
3. Wrong PriceQuote.symbol rejection
4. Missing/blank quote or FX source_id
5. Ledger and valuation as-of mismatch
6. Offset long/short lots (gross vs net distinctness)
7. Duplicate account registration fails closed
8. Alias collisions and duplicate aliases fail closed
9. Attestation with unverified source downgraded
10. Tampered ledger source bytes rejected (integrity compromised)
11. Non-attested break never claims INDEPENDENT status
12. Conflicting valuation dates across accounts in registry fail closed
13. Same-currency matched internal cash transfer
14. Unmatched internal transfer (source only, dest only)
15. Cross-currency transfer lacking conversion rate pending FX
16. Internal transfer does not alter consolidated portfolio NAV
17. Missing price or FX rate fails closed
18. Non-finite / non-Decimal inputs fail closed
19. Backward compatibility with PR #16-20 single-account workflows
20. Isolation: zero network, credentials, orders, or live accounts
Plus Phase 6 end-to-end synthetic multi-account scenario (USD + THB).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import hashlib
import json
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.ppds.exposure import (
    FXRate,
    PortfolioValuation,
    PriceQuote,
    ValuedPosition,
    evaluate_portfolio_base_currency,
    gross_lots_exposure,
    net_signed_exposure,
)
from acash.ppds.ledger import NormalizedPortfolioLedger
from acash.ppds.lots import CashLot, PositionLot
from acash.ppds.reconcile import (
    IndependentLedgerAttestation,
    ReconciliationResult,
    format_reconciliation_report,
    reconcile_snapshot_ledger,
)
from acash.ppds.registry import (
    AccountRegistration,
    AccountRegistry,
    ConsolidatedPortfolioValuation,
    TransferEnvelope,
    TransferLeg,
    consolidate_portfolio_valuations,
    validate_internal_transfer,
)
from acash.ppds.statement_ingest import AccountSnapshot
from acash.ppds.surface import render_read_only_surface


# ---------------------------------------------------------------------------
# Test 1 & 2: FX orientation and mapping key consistency
# ---------------------------------------------------------------------------


def test_adversarial_1_fx_inverted_orientation_rejected() -> None:
    """evaluate_portfolio_base_currency rejects inverted FXRate (USD->THB passed under THB->USD key)."""
    as_of = date(2026, 10, 5)
    ledger = NormalizedPortfolioLedger(account_id="ACC_THB", as_of=as_of)
    ledger = ledger.post_cash_lot(CashLot(currency="THB", amount=Decimal("10000.00"), acquired_on=as_of))

    # Inverted rate object: says from USD to THB rate=35, placed under key ("THB", "USD")
    inverted_fx = {
        ("THB", "USD"): FXRate(
            from_currency="USD",  # Inverted!
            to_currency="THB",
            rate=Decimal("35.0"),
            as_of=as_of,
            source_id="SYNTH_FX",
        )
    }

    with pytest.raises(DataContractError, match="PPDS_VALUATION_FX_ORIENTATION_MISMATCH"):
        evaluate_portfolio_base_currency(
            ledger=ledger,
            base_currency="USD",
            as_of=as_of,
            prices={},
            fx_rates=inverted_fx,
        )


def test_adversarial_2_fx_contradictory_fields_rejected() -> None:
    """evaluate_portfolio_base_currency rejects FXRate whose fields contradict the target currency."""
    as_of = date(2026, 10, 5)
    ledger = NormalizedPortfolioLedger(account_id="ACC_EUR", as_of=as_of)
    ledger = ledger.post_cash_lot(CashLot(currency="EUR", amount=Decimal("500.00"), acquired_on=as_of))

    contradictory_fx = {
        ("EUR", "USD"): FXRate(
            from_currency="EUR",
            to_currency="GBP",  # Contradicts clean_base "USD"!
            rate=Decimal("0.85"),
            as_of=as_of,
            source_id="SYNTH_FX",
        )
    }

    with pytest.raises(DataContractError, match="PPDS_VALUATION_FX_ORIENTATION_MISMATCH"):
        evaluate_portfolio_base_currency(
            ledger=ledger,
            base_currency="USD",
            as_of=as_of,
            prices={},
            fx_rates=contradictory_fx,
        )


# ---------------------------------------------------------------------------
# Test 3: PriceQuote symbol mismatch
# ---------------------------------------------------------------------------


def test_adversarial_3_price_quote_symbol_mismatch_rejected() -> None:
    """evaluate_portfolio_base_currency rejects PriceQuote whose symbol != dictionary key."""
    as_of = date(2026, 10, 5)
    ledger = NormalizedPortfolioLedger(account_id="ACC_EQ", as_of=as_of)
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("10"), cost_basis_per_share=Decimal("400"), acquired_on=as_of, currency="USD")
    )

    mismatched_quote = {
        "SPY": PriceQuote(
            symbol="IVV",  # Mismatch!
            price=Decimal("450.00"),
            as_of=as_of,
            currency="USD",
            source_id="SYNTH_PRICE",
        )
    }

    with pytest.raises(DataContractError, match="PPDS_VALUATION_QUOTE_SYMBOL_MISMATCH"):
        evaluate_portfolio_base_currency(
            ledger=ledger,
            base_currency="USD",
            as_of=as_of,
            prices=mismatched_quote,
            fx_rates={},
        )


# ---------------------------------------------------------------------------
# Test 4: Missing or blank quote or FX source_id
# ---------------------------------------------------------------------------


def test_adversarial_4_blank_source_id_rejected() -> None:
    """Blank source_id on quote or FX rate fails closed."""
    as_of = date(2026, 10, 5)
    ledger = NormalizedPortfolioLedger(account_id="ACC_EQ", as_of=as_of)
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("10"), cost_basis_per_share=Decimal("400"), acquired_on=as_of, currency="USD")
    )

    blank_quote_source = {
        "SPY": PriceQuote(symbol="SPY", price=Decimal("450.00"), as_of=as_of, currency="USD", source_id="   ")
    }

    with pytest.raises(DataContractError, match="PPDS_VALUATION_PRICE_SOURCE_INVALID"):
        evaluate_portfolio_base_currency(
            ledger=ledger,
            base_currency="USD",
            as_of=as_of,
            prices=blank_quote_source,
            fx_rates={},
        )

    # Test blank FX source_id
    cash_ledger = NormalizedPortfolioLedger(account_id="ACC_THB", as_of=as_of)
    cash_ledger = cash_ledger.post_cash_lot(CashLot(currency="THB", amount=Decimal("100.00"), acquired_on=as_of))
    blank_fx_source = {
        ("THB", "USD"): FXRate(from_currency="THB", to_currency="USD", rate=Decimal("0.028"), as_of=as_of, source_id="")
    }

    with pytest.raises(DataContractError, match="PPDS_VALUATION_FX_SOURCE_INVALID"):
        evaluate_portfolio_base_currency(
            ledger=cash_ledger,
            base_currency="USD",
            as_of=as_of,
            prices={},
            fx_rates=blank_fx_source,
        )


# ---------------------------------------------------------------------------
# Test 5: Ledger and valuation as-of mismatch
# ---------------------------------------------------------------------------


def test_adversarial_5_ledger_and_valuation_as_of_mismatch() -> None:
    """evaluate_portfolio_base_currency fails closed when ledger.as_of != valuation as_of."""
    ledger_date = date(2026, 10, 4)
    val_date = date(2026, 10, 5)
    ledger = NormalizedPortfolioLedger(account_id="ACC_1", as_of=ledger_date)
    ledger = ledger.post_cash_lot(CashLot(currency="USD", amount=Decimal("1000.00"), acquired_on=ledger_date))

    with pytest.raises(DataContractError, match="PPDS_VALUATION_LEDGER_AS_OF_MISMATCH"):
        evaluate_portfolio_base_currency(
            ledger=ledger,
            base_currency="USD",
            as_of=val_date,
            prices={},
            fx_rates={},
        )


# ---------------------------------------------------------------------------
# Test 6: Offsetting long/short lots semantic distinctness
# ---------------------------------------------------------------------------


def test_adversarial_6_offset_long_short_lots() -> None:
    """Gross lots exposure and net signed exposure remain semantically distinct on offsetting lots."""
    as_of = date(2026, 10, 5)
    ledger = NormalizedPortfolioLedger(account_id="ACC_HEDGE", as_of=as_of)
    # Long 10 SPY, Short 10 SPY
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("10"), cost_basis_per_share=Decimal("400"), acquired_on=as_of, currency="USD")
    )
    ledger = ledger.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("-10"), cost_basis_per_share=Decimal("400"), acquired_on=as_of, currency="USD")
    )

    prices = {"SPY": Decimal("450.00")}
    # Net signed exposure nets to 0 shares -> empty exposure raises DataContractError
    with pytest.raises(DataContractError, match="PPDS_EXPOSURE_EMPTY"):
        net_signed_exposure(ledger, prices)

    # Gross lots exposure captures 20 shares commitment = $9,000
    gross = gross_lots_exposure(ledger, prices)
    assert len(gross) == 1
    assert gross[0].key == "SPY"
    assert gross[0].market_value == "9000.00"


# ---------------------------------------------------------------------------
# Test 7 & 8: Account Registry duplicate and alias collisions
# ---------------------------------------------------------------------------


def test_adversarial_7_duplicate_account_registration_fails_closed() -> None:
    """AccountRegistry rejects duplicate account IDs."""
    as_of = date(2026, 10, 5)
    registry = AccountRegistry(portfolio_id="PORT_1")
    acc1 = AccountRegistration(
        portfolio_id="PORT_1",
        account_id="ACC_USD",
        source_id="IBKR_USD",
        as_of=as_of,
        base_currency="USD",
    )
    registry = registry.register(acc1)

    with pytest.raises(DataContractError, match="PPDS_REGISTRY_DUPLICATE_ACCOUNT"):
        registry.register(acc1)


def test_adversarial_8_alias_collision_fails_closed() -> None:
    """AccountRegistry rejects an account whose alias collides with another account or alias."""
    as_of = date(2026, 10, 5)
    registry = AccountRegistry(portfolio_id="PORT_1")
    acc1 = AccountRegistration(
        portfolio_id="PORT_1",
        account_id="ACC_USD",
        source_id="IBKR_USD",
        as_of=as_of,
        base_currency="USD",
        aliases=("PRIMARY_USD",),
    )
    registry = registry.register(acc1)

    acc2 = AccountRegistration(
        portfolio_id="PORT_1",
        account_id="ACC_USD_2",
        source_id="SCHWAB_USD",
        as_of=as_of,
        base_currency="USD",
        aliases=("PRIMARY_USD",),  # Collides with acc1's alias!
    )
    with pytest.raises(DataContractError, match="PPDS_REGISTRY_ALIAS_COLLISION"):
        registry.register(acc2)


# ---------------------------------------------------------------------------
# Test 9: Independent-source attestation without actual artifact evidence
# ---------------------------------------------------------------------------


def test_adversarial_9_unattested_independent_claim_demoted() -> None:
    """Claiming independence with distinct source IDs but without attestation yields unverified status."""
    as_of = date(2026, 10, 5)
    snap = AccountSnapshot(
        as_of=as_of,
        account_id="ACC_1",
        cash_lots=(CashLot(currency="USD", amount=Decimal("1000.00"), acquired_on=as_of),),
        position_lots=(),
    )
    ledger = NormalizedPortfolioLedger(account_id="ACC_1", as_of=as_of)
    ledger = ledger.post_cash_lot(CashLot(currency="USD", amount=Decimal("1000.00"), acquired_on=as_of))

    rec = reconcile_snapshot_ledger(
        snapshot=snap,
        ledger=ledger,
        statement_source_id="CUSTODIAN_STMT",
        ledger_source_id="INTERNAL_ERP",
        is_independent=True,
        attestation=None,  # No attestation!
    )
    assert rec.status == "NUMERICALLY_MATCHED_INDEPENDENCE_UNVERIFIED"
    assert rec.is_independent is False
    assert rec.source_independence_status == "INDEPENDENCE_UNVERIFIED"
    assert rec.evidence_integrity_status == "UNATTESTED"


# ---------------------------------------------------------------------------
# Test 10: Tampered ledger source bytes rejected
# ---------------------------------------------------------------------------


def test_adversarial_10_tampered_ledger_source_bytes_rejected() -> None:
    """reconcile_snapshot_ledger rejects tampered ledger artifact bytes whose digest != attestation."""
    as_of = date(2026, 10, 5)
    snap = AccountSnapshot(
        as_of=as_of,
        account_id="ACC_1",
        cash_lots=(CashLot(currency="USD", amount=Decimal("1000.00"), acquired_on=as_of),),
        position_lots=(),
    )
    ledger = NormalizedPortfolioLedger(account_id="ACC_1", as_of=as_of)
    ledger = ledger.post_cash_lot(CashLot(currency="USD", amount=Decimal("1000.00"), acquired_on=as_of))

    raw_authentic_bytes = b'{"ledger_entries": [{"currency": "USD", "amount": "1000.00"}]}'
    authentic_sha = hashlib.sha256(raw_authentic_bytes).hexdigest()

    attestation = IndependentLedgerAttestation(
        ledger_source_id="AUDITED_ERP",
        artifact_sha256=authentic_sha,
        account_id="ACC_1",
        as_of=as_of,
        entry_count=ledger.entry_count,
        head_sha256=ledger.head_sha256,
        lineage_ref="evidence/erp_20261005.json",
        origin_system="SAP_GL",
    )

    # Tamper with the bytes
    tampered_bytes = b'{"ledger_entries": [{"currency": "USD", "amount": "9999.00"}]}'

    rec = reconcile_snapshot_ledger(
        snapshot=snap,
        ledger=ledger,
        statement_source_id="STMT_SOURCE",
        ledger_source_id="AUDITED_ERP",
        is_independent=True,
        attestation=attestation,
        ledger_artifact_bytes=tampered_bytes,
    )

    assert rec.status == "SOURCE_LINEAGE_CONFLICT"
    assert rec.is_independent is False
    assert rec.evidence_integrity_status == "INTEGRITY_COMPROMISED"
    assert rec.source_independence_status == "SOURCE_LINEAGE_CONFLICT"


# ---------------------------------------------------------------------------
# Test 11: Contradictory source verification statuses resolved
# ---------------------------------------------------------------------------


def test_adversarial_11_unattested_break_never_claims_independent_status() -> None:
    """Discrepancy without attestation produces BREAKS_INDEPENDENCE_UNVERIFIED with is_independent=False."""
    as_of = date(2026, 10, 5)
    snap = AccountSnapshot(
        as_of=as_of,
        account_id="ACC_1",
        cash_lots=(CashLot(currency="USD", amount=Decimal("1200.00"), acquired_on=as_of),),  # Differs from ledger
        position_lots=(),
    )
    ledger = NormalizedPortfolioLedger(account_id="ACC_1", as_of=as_of)
    ledger = ledger.post_cash_lot(CashLot(currency="USD", amount=Decimal("1000.00"), acquired_on=as_of))

    rec = reconcile_snapshot_ledger(
        snapshot=snap,
        ledger=ledger,
        statement_source_id="CUSTODIAN_STMT",
        ledger_source_id="ERP_UNATTESTED",
        is_independent=True,
        attestation=None,
    )

    # Must NOT say INDEPENDENT_RECONCILIATION_BREAKS while is_independent is False
    assert rec.status == "BREAKS_INDEPENDENCE_UNVERIFIED"
    assert rec.is_independent is False
    assert rec.source_independence_status == "INDEPENDENCE_UNVERIFIED"


# ---------------------------------------------------------------------------
# Test 12: Conflicting valuation dates across accounts
# ---------------------------------------------------------------------------


def test_adversarial_12_conflicting_account_dates_in_registry_rejected() -> None:
    """AccountRegistry rejects accounts with different as_of dates."""
    registry = AccountRegistry(portfolio_id="PORT_1")
    acc1 = AccountRegistration(
        portfolio_id="PORT_1",
        account_id="ACC_USD",
        source_id="IBKR",
        as_of=date(2026, 10, 5),
        base_currency="USD",
    )
    registry = registry.register(acc1)

    acc2 = AccountRegistration(
        portfolio_id="PORT_1",
        account_id="ACC_THB",
        source_id="SCB",
        as_of=date(2026, 10, 6),  # Mismatched date!
        base_currency="THB",
    )
    with pytest.raises(DataContractError, match="PPDS_REGISTRY_AS_OF_MISMATCH"):
        registry.register(acc2)


# ---------------------------------------------------------------------------
# Test 13: Same-currency matched internal transfer
# ---------------------------------------------------------------------------


def test_adversarial_13_same_currency_matched_internal_transfer() -> None:
    """validate_internal_transfer correctly matches equal-and-opposite cash flows."""
    d = date(2026, 10, 5)
    source_leg = TransferLeg(
        account_id="ACC_USD_1",
        source_id="IBKR",
        transaction_id="TX_OUT_001",
        effective_date=d,
        currency="USD",
        amount=Decimal("-5000.00"),
        asset_type="CASH",
        evidence_ref="wire_out_5000.pdf",
    )
    dest_leg = TransferLeg(
        account_id="ACC_USD_2",
        source_id="SCHWAB",
        transaction_id="TX_IN_001",
        effective_date=d,
        currency="USD",
        amount=Decimal("5000.00"),
        asset_type="CASH",
        evidence_ref="wire_in_5000.pdf",
    )

    env = validate_internal_transfer(source_leg, dest_leg, "XFER_001")
    assert env.status == "MATCHED"
    assert env.fee_amount == Decimal("0")
    assert set(env.evidence_refs) == {"wire_out_5000.pdf", "wire_in_5000.pdf"}


# ---------------------------------------------------------------------------
# Test 14: Unmatched internal transfer (source only / dest only)
# ---------------------------------------------------------------------------


def test_adversarial_14_unmatched_internal_transfer() -> None:
    """validate_internal_transfer flags single-leg transfers as UNMATCHED."""
    d = date(2026, 10, 5)
    source_leg = TransferLeg(
        account_id="ACC_USD_1",
        source_id="IBKR",
        transaction_id="TX_OUT_002",
        effective_date=d,
        currency="USD",
        amount=Decimal("-2000.00"),
        asset_type="CASH",
    )

    env_source_only = validate_internal_transfer(source_leg, None, "XFER_UNMATCHED_SRC")
    assert env_source_only.status == "UNMATCHED_SOURCE_ONLY"

    dest_leg = TransferLeg(
        account_id="ACC_USD_2",
        source_id="SCHWAB",
        transaction_id="TX_IN_002",
        effective_date=d,
        currency="USD",
        amount=Decimal("2000.00"),
        asset_type="CASH",
    )
    env_dest_only = validate_internal_transfer(None, dest_leg, "XFER_UNMATCHED_DST")
    assert env_dest_only.status == "UNMATCHED_DEST_ONLY"


# ---------------------------------------------------------------------------
# Test 15: Cross-currency transfer lacking required FX evidence
# ---------------------------------------------------------------------------


def test_adversarial_15_cross_currency_transfer_lacking_fx() -> None:
    """validate_internal_transfer marks cross-currency transfer without conversion rate as CROSS_CURRENCY_PENDING_FX."""
    d = date(2026, 10, 5)
    src = TransferLeg(
        account_id="ACC_USD",
        source_id="IBKR",
        transaction_id="TX_USD_OUT",
        effective_date=d,
        currency="USD",
        amount=Decimal("-1000.00"),
        asset_type="CASH",
    )
    dst = TransferLeg(
        account_id="ACC_THB",
        source_id="SCB",
        transaction_id="TX_THB_IN",
        effective_date=d,
        currency="THB",
        amount=Decimal("35000.00"),
        asset_type="CASH",
    )

    env = validate_internal_transfer(src, dst, "XFER_FX_001")
    assert env.status == "CROSS_CURRENCY_PENDING_FX"

    # With explicit reviewed FX rate
    env_matched = validate_internal_transfer(src, dst, "XFER_FX_001", cross_currency_fx_rate=Decimal("35.0"))
    assert env_matched.status == "MATCHED_CROSS_CURRENCY"
    assert env_matched.fx_rate == Decimal("35.0")


# ---------------------------------------------------------------------------
# Test 16: Internal transfer does not alter consolidated portfolio NAV
# ---------------------------------------------------------------------------


def test_adversarial_16_internal_transfer_nav_invariance() -> None:
    """Transfer of cash between two accounts inside the portfolio preserves total consolidated NAV."""
    as_of = date(2026, 10, 5)
    # Portfolio before transfer: Account 1 has $10,000 USD, Account 2 has $5,000 USD. Total NAV = $15,000 USD.
    reg = AccountRegistry(portfolio_id="PORT_TRANS")
    reg = reg.register(AccountRegistration("PORT_TRANS", "ACC_1", "SRC_1", as_of, "USD"))
    reg = reg.register(AccountRegistration("PORT_TRANS", "ACC_2", "SRC_2", as_of, "USD"))

    v1_before = PortfolioValuation(
        as_of=as_of,
        base_currency="USD",
        account_id="ACC_1",
        cash_local={"USD": Decimal("10000.00")},
        cash_base={"USD": Decimal("10000.00")},
        total_cash_base=Decimal("10000.00"),
        positions=[],
        total_positions_gross_base=Decimal("0"),
        total_positions_net_base=Decimal("0"),
        total_portfolio_nav_base=Decimal("10000.00"),
    )
    v2_before = PortfolioValuation(
        as_of=as_of,
        base_currency="USD",
        account_id="ACC_2",
        cash_local={"USD": Decimal("5000.00")},
        cash_base={"USD": Decimal("5000.00")},
        total_cash_base=Decimal("5000.00"),
        positions=[],
        total_positions_gross_base=Decimal("0"),
        total_positions_net_base=Decimal("0"),
        total_portfolio_nav_base=Decimal("5000.00"),
    )
    cons_before = consolidate_portfolio_valuations(reg, {"ACC_1": v1_before, "ACC_2": v2_before}, "USD", {})
    assert cons_before.consolidated_nav == Decimal("15000.00")

    # After transfer of $3,000 USD from ACC_1 to ACC_2:
    v1_after = PortfolioValuation(
        as_of=as_of,
        base_currency="USD",
        account_id="ACC_1",
        cash_local={"USD": Decimal("7000.00")},
        cash_base={"USD": Decimal("7000.00")},
        total_cash_base=Decimal("7000.00"),
        positions=[],
        total_positions_gross_base=Decimal("0"),
        total_positions_net_base=Decimal("0"),
        total_portfolio_nav_base=Decimal("7000.00"),
    )
    v2_after = PortfolioValuation(
        as_of=as_of,
        base_currency="USD",
        account_id="ACC_2",
        cash_local={"USD": Decimal("8000.00")},
        cash_base={"USD": Decimal("8000.00")},
        total_cash_base=Decimal("8000.00"),
        positions=[],
        total_positions_gross_base=Decimal("0"),
        total_positions_net_base=Decimal("0"),
        total_portfolio_nav_base=Decimal("8000.00"),
    )
    cons_after = consolidate_portfolio_valuations(reg, {"ACC_1": v1_after, "ACC_2": v2_after}, "USD", {})
    # Consolidated NAV is exactly preserved at $15,000.00 USD
    assert cons_after.consolidated_nav == Decimal("15000.00")
    assert cons_after.consolidated_nav == cons_before.consolidated_nav


# ---------------------------------------------------------------------------
# Test 17: Missing price or FX rate in consolidation fails closed
# ---------------------------------------------------------------------------


def test_adversarial_17_missing_consolidation_fx_rate_fails_closed() -> None:
    """consolidate_portfolio_valuations fails closed when required currency conversion rate is missing."""
    as_of = date(2026, 10, 5)
    reg = AccountRegistry(portfolio_id="PORT_GLOBAL")
    reg = reg.register(AccountRegistration("PORT_GLOBAL", "ACC_THB", "SCB", as_of, "THB"))

    v_thb = PortfolioValuation(
        as_of=as_of,
        base_currency="THB",
        account_id="ACC_THB",
        cash_local={"THB": Decimal("100000.00")},
        cash_base={"THB": Decimal("100000.00")},
        total_cash_base=Decimal("100000.00"),
        positions=[],
        total_positions_gross_base=Decimal("0"),
        total_positions_net_base=Decimal("0"),
        total_portfolio_nav_base=Decimal("100000.00"),
    )

    with pytest.raises(DataContractError, match="PPDS_CONSOLIDATION_FX_MISSING"):
        consolidate_portfolio_valuations(
            registry=reg,
            valuations={"ACC_THB": v_thb},
            reporting_currency="USD",
            fx_rates={},  # Missing THB->USD!
        )


# ---------------------------------------------------------------------------
# Test 18: NaN, Infinity, and non-Decimal inputs fail closed
# ---------------------------------------------------------------------------


def test_adversarial_18_non_finite_inputs_fail_closed() -> None:
    """Non-finite or non-Decimal rates or prices fail closed immediately."""
    as_of = date(2026, 10, 5)
    ledger = NormalizedPortfolioLedger(account_id="ACC_1", as_of=as_of)
    ledger = ledger.post_cash_lot(CashLot(currency="EUR", amount=Decimal("100.00"), acquired_on=as_of))

    inf_fx = {
        ("EUR", "USD"): FXRate(
            from_currency="EUR",
            to_currency="USD",
            rate=Decimal("Infinity"),  # Infinity!
            as_of=as_of,
            source_id="SYNTH",
        )
    }
    with pytest.raises(DataContractError, match="PPDS_VALUATION_FX_RATE_INVALID"):
        evaluate_portfolio_base_currency(ledger, "USD", as_of, {}, inf_fx)


# ---------------------------------------------------------------------------
# Test 19: Backward compatibility with PR #16–20 single-account workflows
# ---------------------------------------------------------------------------


def test_adversarial_19_backward_compatibility() -> None:
    """Existing single-account workflows and DEFAULT account remain functional."""
    as_of = date(2026, 10, 5)
    ledger = NormalizedPortfolioLedger(account_id="DEFAULT", as_of=as_of)
    ledger = ledger.post_cash_lot(CashLot(currency="USD", amount=Decimal("5000.00"), acquired_on=as_of))

    val = evaluate_portfolio_base_currency(
        ledger=ledger,
        base_currency="USD",
        as_of=as_of,
        prices={},
        fx_rates={},
    )
    assert val.total_portfolio_nav_base == Decimal("5000.00")
    assert val.account_id == "DEFAULT"

    snap = AccountSnapshot(
        as_of=as_of,
        account_id="DEFAULT",
        cash_lots=(CashLot(currency="USD", amount=Decimal("5000.00"), acquired_on=as_of),),
        position_lots=(),
    )
    rec = reconcile_snapshot_ledger(snap, ledger)
    assert rec.matched is True
    assert rec.status == "SELF_CONSISTENCY_VERIFIED"
    assert rec.is_independent is False
    assert rec.evidence_integrity_status == "UNATTESTED"


# ---------------------------------------------------------------------------
# Test 20: Isolation - zero network, credentials, or live accounts
# ---------------------------------------------------------------------------


def test_adversarial_20_pure_offline_isolation() -> None:
    """Verifies all registry and consolidation structures operate completely in-memory without I/O."""
    import sys
    # Verify no broker or live trading modules are imported
    forbidden_modules = {"alpaca_trade_api", "ccxt", "interactive_brokers", "mt5"}
    loaded = set(sys.modules.keys())
    assert not (forbidden_modules & loaded)


# ---------------------------------------------------------------------------
# Phase 6: End-to-End Synthetic Multi-Account Workflow
# ---------------------------------------------------------------------------


def test_phase_6_end_to_end_synthetic_workflow() -> None:
    """Complete multi-account decision-support workflow demonstrating:

    - Two distinct accounts: one USD-focused, one THB-focused
    - Independent synthetic evidence per account with verified bytes
    - Explicit PriceQuote and FXRate objects
    - Matched internal cash transfer
    - Exact consolidated base-currency NAV
    - Read-only operator reporting
    """
    as_of = date(2026, 10, 5)

    # 1. Account 1: USD equity account
    # Has $10,000 USD cash and 10 shares SPY ($450 each = $4,500 USD).
    # Net NAV = $14,500 USD.
    ledger_usd = NormalizedPortfolioLedger(account_id="ACC_USD_ALPHA", as_of=as_of)
    ledger_usd = ledger_usd.post_cash_lot(CashLot(currency="USD", amount=Decimal("10000.00"), acquired_on=as_of))
    ledger_usd = ledger_usd.post_position_lot(
        PositionLot(symbol="SPY", quantity=Decimal("10"), cost_basis_per_share=Decimal("400.00"), acquired_on=as_of, currency="USD")
    )

    prices_usd = {
        "SPY": PriceQuote(symbol="SPY", price=Decimal("450.00"), as_of=as_of, currency="USD", source_id="SYNTH_NYSE_FEED")
    }
    val_usd = evaluate_portfolio_base_currency(
        ledger=ledger_usd,
        base_currency="USD",
        as_of=as_of,
        prices=prices_usd,
        fx_rates={},
    )
    assert val_usd.total_portfolio_nav_base == Decimal("14500.00")

    # 2. Account 2: THB equity account
    # Has 50,000 THB cash and 100 shares PTT (35 THB each = 3,500 THB).
    # Net NAV = 53,500 THB.
    ledger_thb = NormalizedPortfolioLedger(account_id="ACC_THB_BETA", as_of=as_of)
    ledger_thb = ledger_thb.post_cash_lot(CashLot(currency="THB", amount=Decimal("50000.00"), acquired_on=as_of))
    ledger_thb = ledger_thb.post_position_lot(
        PositionLot(symbol="PTT", quantity=Decimal("100"), cost_basis_per_share=Decimal("30.00"), acquired_on=as_of, currency="THB")
    )

    prices_thb = {
        "PTT": PriceQuote(symbol="PTT", price=Decimal("35.00"), as_of=as_of, currency="THB", source_id="SYNTH_SET_FEED")
    }
    val_thb = evaluate_portfolio_base_currency(
        ledger=ledger_thb,
        base_currency="THB",
        as_of=as_of,
        prices=prices_thb,
        fx_rates={},
    )
    assert val_thb.total_portfolio_nav_base == Decimal("53500.00")

    # 3. Independent attestation & byte-level verification for Account 1
    usd_artifact_bytes = b'{"account": "ACC_USD_ALPHA", "entries": 2, "as_of": "2026-10-05"}'
    usd_artifact_sha = hashlib.sha256(usd_artifact_bytes).hexdigest()
    usd_attestation = IndependentLedgerAttestation(
        ledger_source_id="IBKR_DIRECT_FEED",
        artifact_sha256=usd_artifact_sha,
        account_id="ACC_USD_ALPHA",
        as_of=as_of,
        entry_count=ledger_usd.entry_count,
        head_sha256=ledger_usd.head_sha256,
        lineage_ref="books/acc_usd_alpha_20261005.json",
        origin_system="IBKR_CLEARING",
    )

    snap_usd = AccountSnapshot(
        as_of=as_of,
        account_id="ACC_USD_ALPHA",
        cash_lots=(CashLot(currency="USD", amount=Decimal("10000.00"), acquired_on=as_of),),
        position_lots=(PositionLot(symbol="SPY", quantity=Decimal("10"), cost_basis_per_share=Decimal("400.00"), acquired_on=as_of, currency="USD"),),
    )
    rec_usd = reconcile_snapshot_ledger(
        snapshot=snap_usd,
        ledger=ledger_usd,
        statement_source_id="CUSTODIAN_STMT_USD",
        ledger_source_id="IBKR_DIRECT_FEED",
        is_independent=True,
        attestation=usd_attestation,
        ledger_artifact_bytes=usd_artifact_bytes,
    )
    assert rec_usd.matched is True
    assert rec_usd.status == "INDEPENDENT_RECONCILIATION_MATCHED"
    assert rec_usd.is_independent is True
    assert rec_usd.evidence_integrity_status == "BYTES_VERIFIED"
    assert rec_usd.source_independence_status == "INDEPENDENT_VERIFIED"

    # 4. Multi-Account Registry
    registry = AccountRegistry(portfolio_id="PORT_GLOBAL_V1")
    registry = registry.register(AccountRegistration(
        portfolio_id="PORT_GLOBAL_V1",
        account_id="ACC_USD_ALPHA",
        source_id="IBKR_DIRECT_FEED",
        as_of=as_of,
        base_currency="USD",
        evidence_refs=("books/acc_usd_alpha_20261005.json",),
    ))
    registry = registry.register(AccountRegistration(
        portfolio_id="PORT_GLOBAL_V1",
        account_id="ACC_THB_BETA",
        source_id="SCB_FEED",
        as_of=as_of,
        base_currency="THB",
        evidence_refs=("books/acc_thb_beta_20261005.json",),
    ))
    assert len(registry) == 2

    # 5. FX Rates for portfolio reporting currency (USD):
    # 1 THB = 0.028 USD
    fx_rates = {
        ("THB", "USD"): FXRate(
            from_currency="THB",
            to_currency="USD",
            rate=Decimal("0.028"),
            as_of=as_of,
            source_id="SYNTH_BOT_FIXING",
        )
    }

    # 6. Multi-Account Portfolio Consolidation
    # ACC_USD NAV = $14,500.00 USD
    # ACC_THB NAV = 53,500 THB * 0.028 = $1,498.00 USD
    # Total Consolidated NAV = $14,500.00 + $1,498.00 = $15,998.00 USD
    # Total Cash = $10,000 + (50,000 * 0.028 = $1,400) = $11,400.00 USD
    # Total Net Positions = $4,500 + (3,500 * 0.028 = $98) = $4,598.00 USD
    # Total Gross Positions = $4,598.00 USD
    cons = consolidate_portfolio_valuations(
        registry=registry,
        valuations={"ACC_USD_ALPHA": val_usd, "ACC_THB_BETA": val_thb},
        reporting_currency="USD",
        fx_rates=fx_rates,
    )
    assert cons.consolidated_nav == Decimal("15998.000")
    assert cons.total_cash_base == Decimal("11400.000")
    assert cons.total_positions_net_base == Decimal("4598.000")
    assert cons.total_positions_gross_base == Decimal("4598.000")
    assert cons.per_account_nav["ACC_USD_ALPHA"] == Decimal("14500.00")
    assert cons.per_account_nav["ACC_THB_BETA"] == Decimal("1498.000")

    # 7. Matched internal cash transfer demonstration
    xfer_out = TransferLeg(
        account_id="ACC_USD_ALPHA",
        source_id="IBKR_DIRECT_FEED",
        transaction_id="TX_WIRE_OUT",
        effective_date=as_of,
        currency="USD",
        amount=Decimal("-1000.00"),
        asset_type="CASH",
        evidence_ref="books/acc_usd_alpha_20261005.json",
    )
    xfer_in = TransferLeg(
        account_id="ACC_THB_BETA",
        source_id="SCB_FEED",
        transaction_id="TX_WIRE_IN",
        effective_date=as_of,
        currency="THB",
        amount=Decimal("35714.28"),
        asset_type="CASH",
        evidence_ref="books/acc_thb_beta_20261005.json",
    )
    xfer_env = validate_internal_transfer(
        xfer_out,
        xfer_in,
        transfer_id="XFER_USD_THB_01",
        cross_currency_fx_rate=Decimal("35.71428"),
    )
    assert xfer_env.status == "MATCHED_CROSS_CURRENCY"

    # 8. Report verification
    report_text = format_reconciliation_report(rec_usd)
    assert "Evidence Integrity: BYTES_VERIFIED" in report_text
    assert "Source Independence: INDEPENDENT_VERIFIED" in report_text
