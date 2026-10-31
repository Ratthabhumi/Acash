"""Owner-evidence import, reconciliation and decision pack tests (sanitized public inputs only)."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

import pytest

import acash.research.d6.decision_pack as pack_module
import acash.research.d6.owner_evidence as evidence_module
from acash.core.domain.exceptions import DataContractError
from acash.research.d6.broker_profiles import load_candidate_profiles, load_security_eligibility
from acash.research.d6.decision_pack import build_pack, pack_outputs, pack_profiles
from acash.research.d6.owner_evidence import evidence_digest, fx_comparability, parse_observations, reconcile

D = Decimal
REPO = Path(__file__).resolve().parents[3]
OBS = REPO / "docs/research/evidence/v38_owner_observations_public_20261101.json"
MATRIX = REPO / "docs/research/evidence/v38_etf_eligibility_matrix_20261101.csv"
PACK = REPO / "docs/research/evidence/v38_investor_decision_pack_20261101"


def _payload() -> Dict[str, Any]:
    data: Dict[str, Any] = json.loads(OBS.read_text(encoding="utf-8"))
    return data


def _by_id(payload: Dict[str, Any], oid: str) -> Dict[str, Any]:
    obs: Dict[str, Any] = next(o for o in payload["observations"] if o["observation_id"] == oid)
    return obs


def _recon(oid: str, payload: Dict[str, Any] | None = None) -> Any:
    observations = parse_observations(payload or _payload())
    obs = next(o for o in observations if o.observation_id == oid)
    return reconcile(obs, pack_profiles(load_security_eligibility(str(MATRIX))))


def test_public_observations_load_sorted_and_hash_deterministically() -> None:
    first = parse_observations(_payload())
    assert len(first) == 8 and [o.observation_id for o in first] == sorted(o.observation_id for o in first)
    assert evidence_digest(first) == evidence_digest(parse_observations(_payload()))
    assert all(not o.executed for o in first)


def test_dime_order_preview_reconciles_within_display_rounding_and_keeps_cat() -> None:
    r = _recon("DIME_ORDER_PREVIEW_USD100")
    verdicts = {c.item: c.verdict for c in r.checks}
    assert r.status == "FEE_PREVIEW_RECONCILED" and r.execution_status == "NOT_EXECUTED_PREVIEW"
    assert {verdicts[k] for k in ("SECURITY_VALUE_USD", "COMMISSION_USD", "VAT_USD")} == {"CONSISTENT_WITHIN_DISPLAY_ROUNDING"}
    assert verdicts["REGULATORY_USD"] == "NOT_DISPLAYED"
    assert any(m.startswith("CAT_FEE") for m in r.missing_components)


def test_unexplained_preview_difference_is_not_hidden() -> None:
    payload = _payload()
    _by_id(payload, "DIME_ORDER_PREVIEW_USD100")["commission_usd"] = "0.50"
    assert _recon("DIME_ORDER_PREVIEW_USD100", payload).status == "UNEXPLAINED_DIFFERENCE"


def test_rounded_zero_fee_is_not_proof_of_zero() -> None:
    r = _recon("WEBULL_VOO_USD1_FRACTIONAL_PREVIEW")
    total = next(c for c in r.checks if c.item == "DISPLAYED_TOTAL_FEE_USD")
    assert total.verdict == "ROUNDED_ZERO_NOT_PROOF_OF_ZERO" and total.modeled is not None and total.modeled > 0


def test_whole_share_preview_without_value_is_insufficient() -> None:
    r = _recon("WEBULL_AAPL_WHOLE_SHARE_PREVIEW")
    assert r.status == "INSUFFICIENT_DATA" and "ORDER_VALUE" in r.missing_components


def test_indicative_fx_has_no_mid_spread_or_authenticated_expiry() -> None:
    for oid in ("DIME_FX_PREVIEW_20261101", "WEBULL_FX_PREVIEW_20261031"):
        r = _recon(oid)
        assert r.status == "INDICATIVE_PREVIEW_ARITHMETIC_CHECKED"
        assert {"INDEPENDENT_CONTEMPORANEOUS_MID", "FX_SPREAD", "AUTHENTICATED_QUOTE_EXPIRY"} <= set(r.missing_components)
        assert all(c.verdict in ("CONSISTENT_WITHIN_DISPLAY_ROUNDING", "NOT_MODELED") for c in r.checks)
    assert "quote_valid_until" not in evidence_module.OwnerObservation.__dataclass_fields__


def test_non_simultaneous_fx_previews_cannot_be_ranked() -> None:
    observations = parse_observations(_payload())
    assert fx_comparability(observations) == "NON_SIMULTANEOUS_NO_RANKING"
    payload = _payload()
    _by_id(payload, "WEBULL_FX_PREVIEW_20261031")["observed_at"] = "2026-11-01T00:25:00+07:00"
    assert fx_comparability(parse_observations(payload)) == "APPROXIMATELY_SIMULTANEOUS_INDICATIVE_ONLY"


def test_dca_setup_ui_is_not_execution_eligibility() -> None:
    r = _recon("WEBULL_VOO_DCA_SETUP_UI")
    assert r.status == "UI_CAPABILITY_OBSERVED_NOT_EXECUTION_ELIGIBILITY" and "EXECUTION_FILL" in r.missing_components
    voo = next(e for e in load_security_eligibility(str(MATRIX)) if (e.platform_id, e.symbol) == ("WEBULL", "VOO"))
    assert voo.searchable is True and voo.fractional_eligible is None and voo.dca_eligible is None
    assert voo.account_permission == "UNVERIFIED" and voo.evidence_status == "OWNER_UI_OBSERVATION"
    assert voo.ui_capability_observed == ("DCA_SETUP_UI_USD_1", "FRACTIONAL_USD_ORDER_ENTRY_UI")


def test_matrix_cannot_import_verified_account_permission(tmp_path: Path) -> None:
    text = MATRIX.read_text(encoding="utf-8").replace("WEBULL,VOO,ETF,TRUE,UNKNOWN,UNKNOWN,UNKNOWN,UNKNOWN,UNKNOWN,UNKNOWN,UNVERIFIED",
                                                      "WEBULL,VOO,ETF,TRUE,TRUE,TRUE,TRUE,TRUE,UNKNOWN,UNKNOWN,VERIFIED")
    path = tmp_path / "m.csv"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(DataContractError, match="ELIGIBILITY_PERMISSION_NOT_IMPORTABLE"):
        load_security_eligibility(str(path))


def _mutated(oid: str, **changes: Any) -> Dict[str, Any]:
    payload = _payload()
    obs = _by_id(payload, oid)
    for key, value in changes.items():
        if value is None:
            obs.pop(key, None)
        else:
            obs[key] = value
    return payload


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (_mutated("DIME_FX_PREVIEW_20261101", broker_account="x"), "OWNER_EVIDENCE_UNKNOWN_FIELDS"),
        (_mutated("DIME_FX_PREVIEW_20261101", payable_thb=2999.87), "OWNER_EVIDENCE_NUMERIC_NOT_STRING"),
        (_mutated("DIME_FX_PREVIEW_20261101", executed=True), "OWNER_EVIDENCE_EXECUTION_CONTRADICTION"),
        (_mutated("DIME_FX_PREVIEW_20261101", evidence_type="EXECUTED_TRANSACTION"), "OWNER_EVIDENCE_EXECUTION_CONTRADICTION"),
        (_mutated("DIME_FX_PREVIEW_20261101", time_precision="UNKNOWN"), "OWNER_EVIDENCE_TIMESTAMP_PRECISION_CONTRADICTION"),
        (_mutated("DIME_FX_PREVIEW_20261101", observed_at="2026-11-01T00:27:00"), "DECISION_TIMESTAMP_WITHOUT_ZONE"),
        (_mutated("DIME_FX_PREVIEW_20261101", target_amount_usd=None), "OWNER_EVIDENCE_MISSING_FIELDS"),
        (_mutated("DIME_FX_PREVIEW_20261101", payable_thb="-1"), "DECISION_INVALID_MONEY"),
        (_mutated("DIME_FX_PREVIEW_20261101", platform_id="ROBINHOOD"), "OWNER_EVIDENCE_UNKNOWN_PLATFORM"),
        (_mutated("DIME_FX_PREVIEW_20261101", notes="account owner@example.com"), "OWNER_EVIDENCE_PRIVATE_IDENTIFIER"),
        (_mutated("DIME_FX_PREVIEW_20261101", notes="IBKR U1234567"), "OWNER_EVIDENCE_PRIVATE_IDENTIFIER"),
        (_mutated("DIME_FX_PREVIEW_20261101", notes="bank 0123456789"), "OWNER_EVIDENCE_PRIVATE_IDENTIFIER"),
        (_mutated("DIME_FX_PREVIEW_20261101", notes="acct 123-4-56789-0"), "OWNER_EVIDENCE_PRIVATE_IDENTIFIER"),
        ({"schema": "OTHER", "observations": []}, "OWNER_EVIDENCE_BAD_SCHEMA"),
    ],
)
def test_malformed_or_private_observations_are_rejected(payload: Dict[str, Any], code: str) -> None:
    with pytest.raises(DataContractError, match=code):
        parse_observations(payload)


def test_duplicate_ids_and_duplicate_observations_are_rejected() -> None:
    payload = _payload()
    payload["observations"].append(copy.deepcopy(payload["observations"][0]))
    with pytest.raises(DataContractError, match="OWNER_EVIDENCE_DUPLICATE_ID"):
        parse_observations(payload)
    payload["observations"][-1]["observation_id"] = "COPY_OF_FIRST"
    with pytest.raises(DataContractError, match="OWNER_EVIDENCE_DUPLICATE_OBSERVATION"):
        parse_observations(payload)


def test_financially_relevant_changes_change_evidence_and_pack_digests() -> None:
    eligibility = load_security_eligibility(str(MATRIX))
    base = parse_observations(_payload())
    changed = parse_observations(_mutated("DIME_ORDER_PREVIEW_USD100", vat_usd="0.02"))
    assert evidence_digest(base) != evidence_digest(changed)
    assert build_pack(base, eligibility)["pack_sha256"] != build_pack(changed, eligibility)["pack_sha256"]
    assert build_pack(base, eligibility)["pack_sha256"] != build_pack(base, eligibility[1:])["pack_sha256"]


def test_decision_pack_matches_committed_artifacts_and_claims_nothing_unverified() -> None:
    json_text, md_text = pack_outputs(str(OBS), str(MATRIX))
    assert (json_text, md_text) == pack_outputs(str(OBS), str(MATRIX))
    assert Path(str(PACK) + ".json").read_bytes() == json_text.encode("utf-8")
    assert Path(str(PACK) + ".md").read_bytes() == md_text.encode("utf-8")
    pack = json.loads(json_text)
    statuses = {a["cost_status"] for s in pack["scenarios"].values() for a in s["assessments"]}
    assert not statuses & {"ALL_IN_DOCUMENTED", "QUOTE_OBSERVED"}
    assert pack["governance"]["NO_REAL_ORDERS"] is True and pack["governance"]["EXECUTION_AUTHORITY_FROM_EVIDENCE"] == "NONE"
    assert pack["fx_comparability"] == "NON_SIMULTANEOUS_NO_RANKING"
    assert any(item.startswith("OWNER: investment horizon") for item in pack["next_evidence"])
    assert "rank" not in md_text.lower().replace("no ranking", "").replace("_no_ranking", "")


def test_pack_profiles_keep_three_kbank_bearers_on_one_platform() -> None:
    profiles = pack_profiles(())
    ibkr = [p for p in profiles if p.platform_id == "IBKR"]
    assert [p.funding_terms.route_id for p in ibkr if p.funding_terms] == [
        "KBANK_KPLUS_SWIFT_SHAR", "KBANK_KPLUS_SWIFT_DEBT", "KBANK_KPLUS_SWIFT_CRED"]
    assert len(profiles) == len(load_candidate_profiles()) + 2


def test_evidence_and_pack_modules_have_no_network_trading_or_historical_data_access() -> None:
    for module in (evidence_module, pack_module):
        source = Path(str(module.__file__)).read_text(encoding="utf-8")
        for token in ("import requests", "urllib", "socket", "http.client", "httpx", "bars_raw", "distributions.csv",
                      "splits.csv", "place_order", "submit_order"):
            assert token not in source
