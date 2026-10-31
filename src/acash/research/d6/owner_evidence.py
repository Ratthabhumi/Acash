"""Read-only import and reconciliation of sanitized owner observations (ACASH V38).

An observation records what a broker UI displayed. It is never proof that a quote was
executable, an order was filled, or that the owner holds execution permission.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.d6.investor_decision import (
    QUOTE_DISPLAY_TOLERANCE_USD,
    QUOTE_REFERENCE_MAX_GAP,
    THAI_VAT_RATE,
    ZERO,
    BrokerProfile,
    _money,
    _plain,
    _timestamp,
    solve_final_notional,
)

PUBLIC_SCHEMA = "ACASH_OWNER_OBSERVATIONS_PUBLIC_V1"
EVIDENCE_TYPES = (
    "PUBLISHED_PROVIDER_TARIFF",
    "BROKER_UI_OBSERVATION",
    "INDICATIVE_AMOUNT_PREVIEW",
    "FEE_ESTIMATE",
    "EXECUTED_TRANSACTION",
    "SYNTHETIC_FIXTURE",
    "INDEPENDENT_MARKET_REFERENCE",
)
OBSERVATION_KINDS = ("FX_AMOUNT_PREVIEW", "ORDER_PREVIEW", "ORDER_ENTRY_UI", "DCA_SETUP_UI")
TIME_PRECISIONS = ("EXACT", "MINUTE_APPROXIMATE", "DATE_ONLY", "UNKNOWN")
PLATFORM_IDS = ("DIME", "WEBULL", "IBKR")
SHARE_MODES = ("WHOLE", "FRACTIONAL_USD")
DISPLAY_TOLERANCE_THB = Decimal("0.005")
MONEY_FIELDS = (
    "source_amount_thb", "payable_thb", "target_amount_usd", "displayed_rate_thb_per_usd", "order_total_usd",
    "security_value_usd", "commission_usd", "vat_usd", "regulatory_usd", "displayed_fee_usd", "estimated_quantity",
)
_PRIVATE_PATTERNS = (
    re.compile(r"\d{9,}"),
    re.compile(r"\b\d{3}-\d-\d{5}-\d\b"),
    re.compile(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", re.IGNORECASE),
    re.compile(r"\bU\d{6,}\b"),
    re.compile(r"\b0\d{2}-?\d{3}-?\d{4}\b"),
)


@dataclass(frozen=True)
class OwnerObservation:
    observation_id: str
    platform_id: str
    kind: str
    evidence_type: str
    time_precision: str
    observed_at: Optional[str] = None
    observed_on: Optional[str] = None
    symbol: Optional[str] = None
    order_type: Optional[str] = None
    share_mode: Optional[str] = None
    source_amount_thb: Optional[Decimal] = None
    payable_thb: Optional[Decimal] = None
    target_amount_usd: Optional[Decimal] = None
    displayed_rate_thb_per_usd: Optional[Decimal] = None
    countdown_seconds: Optional[int] = None
    order_total_usd: Optional[Decimal] = None
    security_value_usd: Optional[Decimal] = None
    commission_usd: Optional[Decimal] = None
    vat_usd: Optional[Decimal] = None
    regulatory_usd: Optional[Decimal] = None
    displayed_fee_usd: Optional[Decimal] = None
    estimated_quantity: Optional[Decimal] = None
    ui_claims: Tuple[str, ...] = ()
    executed: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        oid = self.observation_id
        if not oid.strip():
            raise DataContractError("OWNER_EVIDENCE_EMPTY_ID.")
        for value, allowed, code in (
            (self.platform_id, PLATFORM_IDS, "PLATFORM"),
            (self.kind, OBSERVATION_KINDS, "KIND"),
            (self.evidence_type, EVIDENCE_TYPES, "EVIDENCE_TYPE"),
            (self.time_precision, TIME_PRECISIONS, "TIME_PRECISION"),
        ):
            if value not in allowed:
                raise DataContractError(f"OWNER_EVIDENCE_UNKNOWN_{code}: {oid} {value!r}.")
        if self.order_type not in (None, "MANUAL", "DCA") or self.share_mode not in (None, *SHARE_MODES):
            raise DataContractError(f"OWNER_EVIDENCE_BAD_ORDER_FIELDS: {oid}.")
        if self.time_precision in ("EXACT", "MINUTE_APPROXIMATE"):
            if self.observed_at is None:
                raise DataContractError(f"OWNER_EVIDENCE_MISSING_TIMESTAMP: {oid}.")
            _timestamp(self.observed_at, f"{oid} observed_at")
        elif self.observed_at is not None:
            raise DataContractError(f"OWNER_EVIDENCE_TIMESTAMP_PRECISION_CONTRADICTION: {oid}.")
        if self.time_precision == "DATE_ONLY" and self.observed_on is None:
            raise DataContractError(f"OWNER_EVIDENCE_MISSING_DATE: {oid}.")
        if self.time_precision == "UNKNOWN" and self.observed_on is not None:
            raise DataContractError(f"OWNER_EVIDENCE_TIMESTAMP_PRECISION_CONTRADICTION: {oid}.")
        if self.observed_on is not None:
            date.fromisoformat(self.observed_on)
        for name in MONEY_FIELDS:
            _money(getattr(self, name), f"{oid} {name}")
        if self.countdown_seconds is not None and self.countdown_seconds < 0:
            raise DataContractError(f"OWNER_EVIDENCE_BAD_COUNTDOWN: {oid}.")
        if self.executed != (self.evidence_type == "EXECUTED_TRANSACTION"):
            raise DataContractError(f"OWNER_EVIDENCE_EXECUTION_CONTRADICTION: {oid}.")
        required = {
            "FX_AMOUNT_PREVIEW": ("source_amount_thb", "target_amount_usd", "displayed_rate_thb_per_usd"),
            "DCA_SETUP_UI": ("symbol",),
            "ORDER_ENTRY_UI": ("symbol",),
        }.get(self.kind, ())
        missing = [name for name in required if getattr(self, name) is None]
        if missing:
            raise DataContractError(f"OWNER_EVIDENCE_MISSING_FIELDS: {oid} {missing}.")
        if self.kind == "ORDER_PREVIEW" and self.order_total_usd is None and self.displayed_fee_usd is None:
            raise DataContractError(f"OWNER_EVIDENCE_MISSING_FIELDS: {oid} order_total_usd or displayed_fee_usd.")
        for text in (oid, self.notes, self.symbol or "", *self.ui_claims):
            if any(p.search(text) for p in _PRIVATE_PATTERNS):
                raise DataContractError(f"OWNER_EVIDENCE_PRIVATE_IDENTIFIER: {oid}.")

    @property
    def sha256(self) -> str:
        return CanonicalConfigSerializer.compute_sha256(_plain(_strings(asdict(self))))


def _strings(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _strings(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_strings(v) for v in value]
    return value


_FIELDS = set(OwnerObservation.__dataclass_fields__)


def parse_observations(payload: Dict[str, Any]) -> Tuple[OwnerObservation, ...]:
    if set(payload) - {"schema", "classification", "notice", "observations"} or payload.get("schema") != PUBLIC_SCHEMA:
        raise DataContractError(f"OWNER_EVIDENCE_BAD_SCHEMA: {payload.get('schema')!r}.")
    observations: List[OwnerObservation] = []
    for raw in payload.get("observations", []):
        unknown = set(raw) - _FIELDS
        if unknown:
            raise DataContractError(f"OWNER_EVIDENCE_UNKNOWN_FIELDS: {sorted(unknown)}.")
        fields = dict(raw)
        for name in MONEY_FIELDS:
            value = fields.get(name)
            if value is not None and not isinstance(value, str):
                raise DataContractError(f"OWNER_EVIDENCE_NUMERIC_NOT_STRING: {name}.")
            if value is not None:
                fields[name] = Decimal(value)
        fields["ui_claims"] = tuple(fields.get("ui_claims", ()))
        observations.append(OwnerObservation(**fields))
    ids = [o.observation_id for o in observations]
    if len(set(ids)) != len(ids):
        raise DataContractError("OWNER_EVIDENCE_DUPLICATE_ID.")
    content = [o.sha256 for o in (_without_id(o) for o in observations)]
    if len(set(content)) != len(content):
        raise DataContractError("OWNER_EVIDENCE_DUPLICATE_OBSERVATION.")
    return tuple(sorted(observations, key=lambda o: o.observation_id))


def _without_id(obs: OwnerObservation) -> OwnerObservation:
    return replace(obs, observation_id="-")


def load_observations(path: str) -> Tuple[OwnerObservation, ...]:
    with open(path, encoding="utf-8") as handle:
        return parse_observations(json.load(handle))


def evidence_digest(observations: Sequence[OwnerObservation]) -> str:
    return CanonicalConfigSerializer.compute_sha256(sorted(o.sha256 for o in observations))


@dataclass(frozen=True)
class ReconciliationCheck:
    item: str
    observed: Optional[Decimal]
    modeled: Optional[Decimal]
    residual: Optional[Decimal]
    verdict: str


@dataclass(frozen=True)
class Reconciliation:
    observation_id: str
    observation_sha256: str
    platform_id: str
    kind: str
    evidence_type: str
    execution_status: str
    status: str
    checks: Tuple[ReconciliationCheck, ...]
    missing_components: Tuple[str, ...]
    notes: Tuple[str, ...]


def _check(item: str, observed: Optional[Decimal], modeled: Optional[Decimal], tolerance: Decimal) -> ReconciliationCheck:
    if observed is None or modeled is None:
        return ReconciliationCheck(item, observed, modeled, None, "NOT_DISPLAYED" if observed is None else "NOT_MODELED")
    residual = observed - modeled
    if abs(residual) > tolerance:
        verdict = "UNEXPLAINED_DIFFERENCE"
    elif observed == ZERO and modeled > ZERO:
        verdict = "ROUNDED_ZERO_NOT_PROOF_OF_ZERO"
    else:
        verdict = "CONSISTENT_WITHIN_DISPLAY_ROUNDING"
    return ReconciliationCheck(item, observed, modeled, residual, verdict)


def _profile_for(obs: OwnerObservation, profiles: Sequence[BrokerProfile]) -> Optional[BrokerProfile]:
    order_type = obs.order_type or "MANUAL"
    for profile in profiles:
        if profile.platform_id == obs.platform_id and profile.commission_policy.applicable_order_type in ("ALL", order_type):
            return profile
    return None


def reconcile(obs: OwnerObservation, profiles: Sequence[BrokerProfile]) -> Reconciliation:
    checks: List[ReconciliationCheck] = []
    missing: List[str] = []
    notes: List[str] = []
    status = "UI_CAPABILITY_OBSERVED_NOT_EXECUTION_ELIGIBILITY"
    if obs.kind == "FX_AMOUNT_PREVIEW":
        assert obs.source_amount_thb is not None and obs.target_amount_usd is not None and obs.displayed_rate_thb_per_usd is not None
        rate = obs.displayed_rate_thb_per_usd
        if obs.payable_thb is not None:
            checks.append(_check("PAYABLE_THB_VS_TARGET_X_RATE", obs.payable_thb, obs.target_amount_usd * rate, DISPLAY_TOLERANCE_THB))
            checks.append(_check("UNSPENT_INPUT_THB", obs.source_amount_thb - obs.payable_thb, None, DISPLAY_TOLERANCE_THB))
        else:
            checks.append(_check("TARGET_USD_VS_SOURCE_DIV_RATE", obs.target_amount_usd, obs.source_amount_thb / rate, QUOTE_DISPLAY_TOLERANCE_USD))
        missing += ["INDEPENDENT_CONTEMPORANEOUS_MID", "FX_SPREAD"]
        if obs.countdown_seconds is not None:
            notes.append("Countdown recorded as displayed; no absolute expiry is derived from a minute-precision clock.")
        missing.append("AUTHENTICATED_QUOTE_EXPIRY")
        status = "INDICATIVE_PREVIEW_ARITHMETIC_CHECKED"
    elif obs.kind == "ORDER_PREVIEW":
        profile = _profile_for(obs, profiles)
        policy = profile.commission_policy if profile is not None else None
        status = "FEE_PREVIEW_RECONCILED"
        if policy is None or obs.order_total_usd is None:
            status = "INSUFFICIENT_DATA"
            missing.append("ORDER_VALUE" if obs.order_total_usd is None else "BROKER_PROFILE")
        else:
            rate = policy.rate or ZERO
            if policy.policy_type == "FREE_MONTHLY_TIERED" and obs.commission_usd == ZERO:
                rate = ZERO
            if policy.policy_type == "FIXED_PER_SHARE":
                status = "INSUFFICIENT_DATA"
                missing.append("SHARE_PRICE")
            else:
                vat_rate = THAI_VAT_RATE if policy.vat_applicable else ZERO
                notional, commission = solve_final_notional(obs.order_total_usd, rate, ZERO, vat_rate, ZERO)
                vat = commission * vat_rate
                regulatory: Optional[Decimal] = None
                if policy.cat_fee_per_share_usd is not None and obs.estimated_quantity is not None:
                    regulatory = obs.estimated_quantity * policy.cat_fee_per_share_usd
                elif policy.cat_fee_per_share_usd is not None:
                    missing.append("CAT_FEE (documented rule; share count not displayed)")
                tol = QUOTE_DISPLAY_TOLERANCE_USD
                checks.append(_check("SECURITY_VALUE_USD", obs.security_value_usd, notional, tol))
                checks.append(_check("COMMISSION_USD", obs.commission_usd, commission, tol))
                checks.append(_check("VAT_USD", obs.vat_usd, vat, tol))
                checks.append(_check("REGULATORY_USD", obs.regulatory_usd, regulatory, tol))
                if obs.displayed_fee_usd is not None:
                    checks.append(_check("DISPLAYED_TOTAL_FEE_USD", obs.displayed_fee_usd, commission + vat + (regulatory or ZERO), tol))
                notes.append(f"Modeled with profile {profile.broker_id if profile else '-'}; fees solved on final notional.")
        if any(c.verdict == "UNEXPLAINED_DIFFERENCE" for c in checks):
            status = "UNEXPLAINED_DIFFERENCE"
    else:
        notes.append("UI capability is not account execution permission; nothing was activated or executed.")
    if not obs.executed:
        missing.append("EXECUTION_FILL")
    return Reconciliation(
        observation_id=obs.observation_id,
        observation_sha256=obs.sha256,
        platform_id=obs.platform_id,
        kind=obs.kind,
        evidence_type=obs.evidence_type,
        execution_status="EXECUTED" if obs.executed else "NOT_EXECUTED_PREVIEW",
        status=status,
        checks=tuple(checks),
        missing_components=tuple(missing),
        notes=tuple(notes),
    )


def fx_comparability(observations: Sequence[OwnerObservation]) -> str:
    """Cross-platform FX previews are comparable only when timestamped within the reference gap."""
    fx = [o for o in observations if o.kind == "FX_AMOUNT_PREVIEW"]
    if len({o.platform_id for o in fx}) < 2:
        return "SINGLE_PLATFORM_ONLY"
    if any(o.observed_at is None for o in fx):
        return "TIMING_UNKNOWN_NO_RANKING"
    times = [_timestamp(o.observed_at or "", "observed_at") for o in fx]
    return "NON_SIMULTANEOUS_NO_RANKING" if max(times) - min(times) > QUOTE_REFERENCE_MAX_GAP else "APPROXIMATELY_SIMULTANEOUS_INDICATIVE_ONLY"
