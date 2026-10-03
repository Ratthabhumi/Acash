"""HYP_011 prospective shadow single-session runner (atomic observation).

Default DRY-RUN (zero network). Live observation requires --execute-network
plus an explicit --authorization identifier whose --ordinal equals
state.observed_session_count + 1. Exactly one expected session per invocation:
no ranges, no catch-up, no backfill. Accounting/benchmark/chain commit happens
only after all price + corporate-action qualification passes.

F15 single-use dispatch: every live invocation consumes one attempt from the
append-only dispatch ledger BEFORE any network call; replay fails closed.
For ordinal >= 2 the live path additionally requires an explicit
--dispatch-authority manifest bound to intent, runtime, CA evidence, expiry,
and trading locks. F16: CA intake is validated pre-network and provenance is
preserved in the sealed observation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.hyp_011_qual_client import HYP011AlpacaClient
from acash.data.qualification.models import MarketDataFeed, PriceAdjustment
from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    EnvAlpacaCredentialProvider,
)
from acash.research.hyp_011.shadow_ca import CADetermination
from acash.research.hyp_011.shadow_ca_bundle import (
    verify_determination_evidence_binding,
    verify_evidence_bundle,
)
from acash.research.hyp_011.shadow_v2_activation import (
    load_segment_activation_authority,
    resolve_v2_activation_session,
    session_one_ca_binding_sha256,
)
from acash.research.hyp_011.shadow_ca_intake import validate_intake_document
from acash.research.hyp_011.shadow_authority import (
    INTENT_REGISTRY_DIRNAME,
    attempt_ledger_key,
    consume_dispatch_attempt,
    resolve_runtime_sha,
    validate_dispatch_authority,
    verify_registered_intent_binding,
)
from acash.research.hyp_011.accounting import BASELINE_SLIPPAGE_BPS
from acash.research.hyp_011.shadow import (
    FAILED_ACTIVATION_SESSION,
    FAILED_DISPATCH_ATTEMPT,
    NEXT_DISPATCH_ATTEMPT,
    STAGE_B_ACTIVATION_SESSION,
    STAGE_C_RECOVERY_BINDING_ID,
    STAGE_C_RECOVERY_BINDING_PATH,
    ShadowState,
    StageCRecoveryAuthority,
    assert_target_session_fresh,
    candidate_schedule_time,
    load_stage_c_recovery_authority,
    observation_eligible_after,
    resolve_operational_activation,
)
from acash.research.hyp_011.shadow_ops import (
    SessionMarket,
    ShadowBenchmark,
    ShadowPortfolio,
    append_observation,
    process_benchmark_session,
    process_strategy_session,
    verify_chain,
)

SYMBOLS = ("ACWI", "AGG", "SPY")
STATE_DIR = Path("data/hyp_011/prospective")
V1_EVIDENCE_STATE_DIR = Path("data/hyp_011/prospective")

EXIT_OK = 0
EXIT_BLOCKED = 2

SEGMENT_ID_V2 = "HYP_011_PROSPECTIVE_V2"


def _check_split_continuity(
    symbol: str,
    market_closes: Dict[str, Decimal],
    market_split_closes: Dict[str, Decimal],
    prior_closes: Dict[str, Any],
) -> str:
    """Fail closed on an implied split without bound official authority.

    Compares today's raw/split close ratio against the prior observed
    session's ratio from persistent state. Session one has no history:
    recorded explicitly, never inferred.
    """
    if not prior_closes:
        return "NO_PRIOR_HISTORY_SINGLE_SESSION"
    prior = prior_closes.get(symbol)
    if not prior:
        raise DataContractError(f"SHADOW_SPLIT_BASELINE_CORRUPT: {symbol}.")
    prior_raw = Decimal(str(prior["raw"]))
    prior_split = Decimal(str(prior["split"]))
    if prior_raw <= Decimal("0") or prior_split <= Decimal("0"):
        raise DataContractError(f"SHADOW_SPLIT_BASELINE_CORRUPT: {symbol}.")
    if market_split_closes[symbol] <= Decimal("0"):
        raise DataContractError(f"SHADOW_SPLIT_NONPOSITIVE: {symbol}.")
    prior_ratio = prior_raw / prior_split
    today_ratio = market_closes[symbol] / market_split_closes[symbol]
    tolerance = abs(prior_ratio) * Decimal("0.000001")
    if abs(today_ratio - prior_ratio) > tolerance:
        raise DataContractError(
            f"BLOCK_PROSPECTIVE_SPLIT_EVENT_CONTRACT: {symbol} ratio "
            f"{prior_ratio} -> {today_ratio} without bound authority."
        )
    return "NO_NEW_SPLIT_EVENT_OBSERVED"


def _expected_next(
    state_sessions: List[str],
    calendar: NyseCa1Calendar,
    activation_session: date,
) -> date:
    if not state_sessions:
        return activation_session
    last = date.fromisoformat(state_sessions[-1])
    cursor = date.fromordinal(last.toordinal() + 1)
    for _ in range(14):
        if calendar.is_trading_session(cursor):
            return cursor
        cursor = date.fromordinal(cursor.toordinal() + 1)
    raise DataContractError("SHADOW_NO_NEXT_SESSION_WITHIN_14_DAYS.")


def main(
    argv: List[str] | None = None,
    _now_utc: datetime | None = None,
    _state_dir: Path | None = None,
    _client: Any | None = None,
    _credential_provider: Any | None = None,
    _stage_c_binding_path: Path | None = None,
    _runtime_sha: str | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="HYP_011 prospective shadow runner.")
    parser.add_argument("--execute-network", action="store_true", default=False)
    parser.add_argument("--authorization", default="")
    parser.add_argument("--ordinal", type=int, default=0)
    parser.add_argument("--dispatch-attempt", type=int, default=0)
    parser.add_argument("--ca-determinations", default="")
    parser.add_argument(
        "--dispatch-authority",
        default="",
        help="Explicit DispatchAuthority manifest (required on live path for ordinal >= 2).",
    )
    parser.add_argument(
        "--ca-evidence-bundle",
        default="",
        help="Per-symbol CA evidence bundle root (required on live path beyond session one).",
    )
    parser.add_argument(
        "--intent-registry",
        default="",
        help="Preregistered-intent registry dir (defaults to <state_dir>/intent_registry).",
    )
    parser.add_argument(
        "--local-preflight",
        action="store_true",
        default=False,
        help="Validate the complete zero-network preflight without consuming "
        "the dispatch attempt and without network.",
    )
    parser.add_argument(
        "--runtime-sha",
        default="",
        help="Explicit runtime commit SHA pin (else resolved from the git checkout).",
    )
    parser.add_argument(
        "--state-dir",
        default="",
        help="Absolute path to mutable state directory (required for V2 production; "
        "defaults to data/hyp_011/prospective for V1 backward compatibility).",
    )
    parser.add_argument(
        "--segment-id",
        default="",
        help="Prospective segment identifier (V2 requires HYP_011_PROSPECTIVE_V2).",
    )
    parser.add_argument(
        "--segment-activation-authority",
        default="",
        help="V2 SegmentActivationAuthority manifest (REQUIRED on the V2 path; "
        "the V2 first target is never derived from V1 Stage-B/Stage-C machinery).",
    )
    args = parser.parse_args(argv)

    # State directory resolution with V2 contract enforcement
    if args.state_dir:
        state_dir = Path(args.state_dir)
        if not state_dir.is_absolute():
            raise DataContractError(
                "SHADOW_STATE_DIR_MUST_BE_ABSOLUTE: --state-dir must be an absolute path."
            )
        # Reject V1 evidence path for V2 production runs
        try:
            state_dir.resolve().relative_to(V1_EVIDENCE_STATE_DIR.resolve())
            raise DataContractError(
                "SHADOW_STATE_DIR_OVERLAPS_V1_EVIDENCE: --state-dir must not overlap "
                f"with V1 evidence path ({V1_EVIDENCE_STATE_DIR})."
            )
        except ValueError:
            # Not a subpath of V1 evidence dir - OK
            pass
    else:
        state_dir = _state_dir if _state_dir is not None else STATE_DIR

    # Segment identity validation for V2. V1 invocations pass neither
    # flag and keep the historical default state dir (backward compatible).
    if args.segment_id:
        if args.segment_id != SEGMENT_ID_V2:
            raise DataContractError(
                f"SHADOW_INVALID_SEGMENT_ID: got {args.segment_id}, "
                f"expected {SEGMENT_ID_V2}."
            )
        # V2 requires explicit state-dir
        if not args.state_dir:
            raise DataContractError(
                "SHADOW_V2_REQUIRES_STATE_DIR: --state-dir is required when --segment-id is set."
            )

    is_v2 = bool(args.segment_id)

    calendar = NyseCa1Calendar()

    # V2 activation authority: the V2 first target comes SOLELY from the
    # human-authorized SegmentActivationAuthority. V1 Stage-B/Stage-C
    # machinery is never consulted on the V2 path (not even when a Stage-C
    # manifest file exists in the checkout).
    segment_activation_sha256: Optional[str] = None
    v2_activation_session: Optional[date] = None
    if is_v2:
        if not args.segment_activation_authority:
            raise DataContractError(
                "SHADOW_V2_ACTIVATION_AUTHORITY_REQUIRED: "
                "--segment-activation-authority is required on the V2 path."
            )
        v2_now = _now_utc if _now_utc is not None else datetime.now(timezone.utc)
        v2_runtime_sha = resolve_runtime_sha(
            _runtime_sha if _runtime_sha is not None else (args.runtime_sha or None)
        )
        v2_authority, segment_activation_sha256 = load_segment_activation_authority(
            Path(args.segment_activation_authority),
            calendar,
            v2_now,
            v2_runtime_sha,
        )
        v2_activation_session = resolve_v2_activation_session(v2_authority)
        print(f"SEGMENT_ACTIVATION_SESSION = {v2_activation_session.isoformat()}")

    attempts = [0]

    def _count() -> None:
        attempts[0] += 1

    print("=== HYP_011 PROSPECTIVE SHADOW (single atomic session) ===")
    print(f"STATE_DIR = {state_dir}")
    if args.segment_id:
        print(f"SEGMENT_ID = {args.segment_id}")
    binding_path = _stage_c_binding_path

    # --local-preflight exercises the complete would-be live local path
    # (authorities, intent, CA, freshness, guards) WITHOUT consuming the
    # attempt and WITHOUT network. Plain dry-run (no flags) stays
    # informational and never requires session authorities.
    if not args.execute_network and not args.local_preflight:
        # PRETEST: full local contract validation, zero network.
        print("PRETEST-DRY-RUN: zero network. Validating local contracts.")
        pretest_state_dir = state_dir
        pretest_now = _now_utc if _now_utc is not None else datetime.now(timezone.utc)
        pretest_state_file = pretest_state_dir / "state.json"
        pretest_committed_count: int = 0
        if pretest_state_file.is_file():
            try:
                st = json.loads(pretest_state_file.read_text(encoding="utf-8"))
                pretest_committed_count = len(st.get("observed_sessions", []))
            except Exception:
                pass

        if is_v2:
            assert v2_activation_session is not None
            assert segment_activation_sha256 is not None
            pretest_activation = v2_activation_session
            pretest_recovery_auth = None
        else:
            pretest_binding_file = binding_path or (
                STAGE_C_RECOVERY_BINDING_PATH if STAGE_C_RECOVERY_BINDING_PATH.is_file() else None
            )
            pretest_recovery_auth = (
                load_stage_c_recovery_authority(calendar, pretest_binding_file)
                if (pretest_binding_file and pretest_binding_file.is_file())
                else None
            )
            pretest_activation = resolve_operational_activation(
                calendar=calendar,
                now_utc=pretest_now,
                stage_c_binding_path=binding_path,
                committed_observations=pretest_committed_count,
            )
        pretest_verified = verify_chain(
            pretest_state_dir,
            expected_activation=pretest_activation,
            expected_recovery_authority=pretest_recovery_auth,
            expected_segment_id=args.segment_id if args.segment_id else None,
            expected_segment_activation_sha256=segment_activation_sha256,
        )
        pretest_observed: List[str] = list(pretest_verified.get("observed_sessions", []))
        pretest_target = _expected_next(pretest_observed, calendar, pretest_activation)
        pretest_session = calendar.get_session(pretest_target)
        pretest_eligible_after = observation_eligible_after(
            pretest_target, calendar
        )
        pretest_eligible = (
            pretest_now.astimezone(timezone.utc) > pretest_eligible_after
        )
        print(f"EXPECTED_SESSION = {pretest_target.isoformat()}")
        print(f"SESSION_OPEN_UTC = {pretest_session.open_utc.isoformat()}")
        print(f"SESSION_CLOSE_UTC = {pretest_session.close_utc.isoformat()}")
        print(f"PROVIDER_ELIGIBLE_AFTER_UTC = {pretest_eligible_after.isoformat()}")
        print(f"OBSERVATION_ELIGIBLE = {str(pretest_eligible).lower()}")
        try:
            pretest_next = assert_target_session_fresh(
                pretest_target, calendar, pretest_now
            )
            print(f"TARGET_FRESH = true")
            print(f"NEXT_SESSION_NOT_YET_OPEN = {pretest_next.isoformat()}")
        except DataContractError as exc:
            print(f"TARGET_FRESH = false")
            print(f"TARGET_STALE_REASON = {exc}")
        print("NETWORK_REQUESTS = 0")
        print("DRY-RUN: no network. Use --execute-network with --authorization.")
        return 0

    now_utc = _now_utc if _now_utc is not None else datetime.now(timezone.utc)
    state_file = state_dir / "state.json"
    committed_count: int = 0
    if state_file.is_file():
        try:
            st = json.loads(state_file.read_text(encoding="utf-8"))
            committed_count = len(st.get("observed_sessions", []))
        except Exception:
            pass

    if is_v2:
        # V2 activation is the validated SegmentActivationAuthority session.
        # V1 Stage-C recovery machinery is never consulted here.
        assert v2_activation_session is not None
        assert segment_activation_sha256 is not None
        activation_session = v2_activation_session
        recovery_auth = None
    else:
        actual_binding_file = binding_path or (
            STAGE_C_RECOVERY_BINDING_PATH if STAGE_C_RECOVERY_BINDING_PATH.is_file() else None
        )
        recovery_auth = (
            load_stage_c_recovery_authority(calendar, actual_binding_file)
            if (actual_binding_file and actual_binding_file.is_file())
            else None
        )

        # Pre-network local validation: resolve operational activation.
        # Fails closed (e.g. SHADOW_RECOVERY_BINDING_REQUIRED) before any network call.
        activation_session = resolve_operational_activation(
            calendar=calendar,
            now_utc=now_utc,
            stage_c_binding_path=binding_path,
            committed_observations=committed_count,
        )

    verified = verify_chain(
        state_dir,
        expected_activation=activation_session,
        expected_recovery_authority=recovery_auth,
        expected_segment_id=args.segment_id if args.segment_id else None,
        expected_segment_activation_sha256=segment_activation_sha256,
    )
    observed: List[str] = list(verified.get("observed_sessions", []))
    expected_ordinal = len(observed) + 1

    # V2 never inherits the V1 Stage-C recovery attempt numbering: a fresh
    # V2 segment always dispatches ordinal 1 attempt 1 under its own
    # SegmentActivationAuthority.
    is_recovery = (
        (not is_v2)
        and len(observed) == 0
        and activation_session > FAILED_ACTIVATION_SESSION
    )
    if is_recovery:
        expected_dispatch_attempt = NEXT_DISPATCH_ATTEMPT
        expected_authorization = (
            f"AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_{expected_ordinal:04d}_ATTEMPT_{expected_dispatch_attempt:04d}"
        )
    else:
        expected_dispatch_attempt = 1
        expected_authorization = (
            f"AUTHORIZE_HYP_011_PROSPECTIVE_OBSERVATION_{expected_ordinal:04d}"
        )

    if not args.authorization:
        raise DataContractError("SHADOW_AUTHORIZATION_REQUIRED.")
    if args.ordinal != expected_ordinal:
        raise DataContractError(
            f"SHADOW_AUTHORIZATION_ORDINAL_MISMATCH: got {args.ordinal}, "
            f"expected {expected_ordinal}."
        )
    if is_recovery and args.dispatch_attempt != expected_dispatch_attempt:
        raise DataContractError(
            f"SHADOW_AUTHORIZATION_ATTEMPT_MISMATCH: got {args.dispatch_attempt}, "
            f"expected {expected_dispatch_attempt}."
        )
    elif not is_recovery and args.dispatch_attempt not in (0, 1):
        raise DataContractError(
            f"SHADOW_AUTHORIZATION_ATTEMPT_MISMATCH: got {args.dispatch_attempt}, "
            f"expected 1."
        )
    if args.authorization != expected_authorization:
        raise DataContractError(
            f"SHADOW_AUTHORIZATION_STRING_MISMATCH: got {args.authorization}, "
            f"expected {expected_authorization}."
        )
    print(
        f"Authorization {args.authorization} ordinal {args.ordinal} "
        f"attempt {expected_dispatch_attempt}: ACCEPTED."
    )

    # DispatchAuthority manifest requirement. V1 compatibility allows a bare
    # token for session one (preserving the sealed Obs #1 lineage semantics).
    # V2 never inherits that exception: V2 ordinal 1 MUST bind a
    # RegisteredIntent + DispatchAuthority from its first session.
    requires_dispatch_authority = is_v2 or len(observed) >= 1
    authority_doc: Dict[str, Any] | None = None
    authority_file_sha: str | None = None
    if requires_dispatch_authority and not args.dispatch_authority:
        raise DataContractError(
            "SHADOW_DISPATCH_AUTHORITY_REQUIRED: live dispatch for "
            f"ordinal {expected_ordinal} requires an explicit "
            "--dispatch-authority manifest."
        )
    if args.dispatch_authority:
        try:
            authority_raw_bytes = Path(args.dispatch_authority).read_bytes()
        except OSError as exc:
            raise DataContractError(f"SHADOW_AUTHORITY_FILE_UNREADABLE: {exc}.") from exc
        try:
            loaded_authority = json.loads(authority_raw_bytes.decode("utf-8"))
        except Exception as exc:
            raise DataContractError(f"SHADOW_AUTHORITY_FILE_CORRUPT: {exc}.") from exc
        if not isinstance(loaded_authority, dict):
            raise DataContractError("SHADOW_AUTHORITY_FILE_MALFORMED.")
        authority_doc = loaded_authority
        authority_file_sha = hashlib.sha256(authority_raw_bytes).hexdigest()

    target = _expected_next(observed, calendar, activation_session)
    print(f"Expected next session: {target.isoformat()}")

    # F15: single-use ledger gate BEFORE any burn or network side effect.
    # The key binds authority (or bare token) + ordinal + attempt + target.
    ledger_key = attempt_ledger_key(
        authority_sha256=authority_file_sha,
        authorization=args.authorization,
        observation_ordinal=expected_ordinal,
        dispatch_attempt=args.dispatch_attempt,
        target_session=target,
    )
    if (state_dir / "dispatch_ledger" / f"{ledger_key}.json").is_file():
        raise DataContractError(
            "BLOCK_DISPATCH_AUTHORITY_REPLAY: this dispatch attempt was "
            "already consumed; a new attempt requires a new explicit "
            "DispatchAuthority."
        )

    obs_path = state_dir / "observations" / f"{target.isoformat()}.json"
    if obs_path.exists():
        print("ALREADY_PROCESSED_NO_ACTION")
        print("NETWORK_REQUESTS_ISSUED = 0")
        return EXIT_OK

    # F18: the attempt ledger is consumed ONLY after every local preflight
    # passes (see below). The read-only replay pre-check above stays early;
    # the destructive consume moved to immediately before network transport.

    # F16: load CA evidence bytes once (prior observations imply CA required).
    ca_file_bytes = b""
    if observed:
        if not args.ca_determinations:
            raise DataContractError(
                "SHADOW_CA_DETERMINATIONS_REQUIRED_BEYOND_SESSION_ONE."
            )
        try:
            ca_file_bytes = Path(args.ca_determinations).read_bytes()
        except OSError as exc:
            raise DataContractError(f"SHADOW_CA_FILE_UNREADABLE: {exc}.") from exc

    # F15: full authority validation (when a manifest was supplied).
    if authority_doc is not None:
        if not ca_file_bytes:
            if is_v2 and expected_ordinal == 1 and not observed:
                # V2 session one holds no prior position, so there is no CA
                # file to bind. The dispatch authority instead binds the
                # deterministic session-one non-event digest: an explicit
                # non-required representation, never an invented event.
                ca_binding_sha256 = session_one_ca_binding_sha256()
            else:
                raise DataContractError(
                    "SHADOW_AUTHORITY_CA_BINDING_UNAVAILABLE: a supplied "
                    "DispatchAuthority requires bound CA evidence bytes."
                )
        else:
            ca_binding_sha256 = hashlib.sha256(ca_file_bytes).hexdigest()
        runtime_sha = resolve_runtime_sha(
            _runtime_sha if _runtime_sha is not None else (args.runtime_sha or None)
        )
        validated_authority = validate_dispatch_authority(
            authority_doc,
            calendar=calendar,
            now_utc=now_utc,
            target_session=target,
            observation_ordinal=expected_ordinal,
            dispatch_attempt=args.dispatch_attempt,
            state_prev_sha256=verified.get("last_observation_sha256"),
            runtime_sha=runtime_sha,
            ca_file_sha256=ca_binding_sha256,
        )
        print(f"DispatchAuthority ACCEPTED: {validated_authority.authority_sha256()[:16]}...")
        # F17: the authority must bind a PHYSICALLY preregistered intent
        # (server-side registry timestamp, O_EXCL create-once). A backdated
        # unregistered JSON can never satisfy this check.
        registry_dir = (
            Path(args.intent_registry)
            if args.intent_registry
            else (state_dir / INTENT_REGISTRY_DIRNAME)
        )
        registered_intent = verify_registered_intent_binding(
            registry_dir=registry_dir,
            bound_intent_sha256=str(authority_doc.get("intent_sha256") or ""),
            target_session=target,
            observation_ordinal=expected_ordinal,
            state_prev_sha256=verified.get("last_observation_sha256"),
        )
        print(
            "RegisteredIntent BOUND: "
            f"{registered_intent.registered_sha256()[:16]}... "
            f"registered_at={registered_intent.registered_at_utc.isoformat()}"
        )

    # F16: corporate-action intake gate BEFORE any market-data network call.
    # The offline intake contract (evidence_ref, source SHA, scope evidence
    # for no-event, exact amount for events) is enforced here so a bad CA
    # package fails with zero requests. Session one records explicit
    # non-required status (no prior holdings, no entitlement possible).
    ca_section: Dict[str, Any] = {}
    dividends: Dict[str, CADetermination] = {}
    if observed:
        # ca_file_bytes was loaded once pre-authority-validation; re-parse here
        # without re-reading (single source of bytes for binding + intake).
        try:
            ca_doc = json.loads(ca_file_bytes.decode("utf-8"))
        except Exception as exc:
            raise DataContractError(f"SHADOW_CA_FILE_CORRUPT: {exc}.") from exc
        if not isinstance(ca_doc, dict):
            raise DataContractError("SHADOW_CA_FILE_MALFORMED.")
        for symbol in SYMBOLS:
            raw = ca_doc.get(symbol)
            if not isinstance(raw, dict):
                raise DataContractError(f"SHADOW_CA_MISSING_{symbol}.")
            determination = validate_intake_document(raw, symbol, target, now_utc)
            dividends[symbol] = determination
            # F16-B: preserve intake provenance in the sealed observation;
            # never silently strip evidence_ref / scope_evidence.
            enriched = determination.to_dict()
            enriched["evidence_ref"] = str(raw["evidence_ref"])
            if raw.get("scope_evidence") is not None:
                enriched["scope_evidence"] = raw["scope_evidence"]
            ca_section[symbol] = enriched
    else:
        for symbol in SYMBOLS:
            ca_section[symbol] = {
                "status": "CA_NOT_ECONOMICALLY_REQUIRED_NO_PRIOR_HOLDINGS"
            }
    print("Corporate-action qualification: PASS.")

    # F19: raw-byte evidence bundle verification per symbol (before any
    # network). Recomputes digests from preserved official bytes, validates
    # sponsor/product identity (239707 is IWB, never ACWI), and binds each
    # sealed determination to its verified bundle digest. Invented digests,
    # missing bytes, and wrong identities fail here with zero requests.
    if observed:
        if not args.ca_evidence_bundle:
            raise DataContractError(
                "SHADOW_CA_BUNDLE_REQUIRED_BEYOND_SESSION_ONE."
            )
        bundle_root = Path(args.ca_evidence_bundle)
        for symbol in SYMBOLS:
            verified_manifest = verify_evidence_bundle(
                bundle_root / symbol, symbol, target, now_utc
            )
            verify_determination_evidence_binding(
                ca_section[symbol], verified_manifest, symbol
            )
        print("Corporate-action evidence bundles: VERIFIED.")

    # Credential presence check (F18 order: after CA/evidence preflight,
    # still before attempt consumption and network).
    cred_prov = _credential_provider or EnvAlpacaCredentialProvider()
    try:
        cred_prov.load()
    except AlpacaCredentialError as exc:
        print(f"BLOCKED_MISSING_CREDENTIALS: {exc}")
        return EXIT_BLOCKED

    # F14 continuation/freshness gate (PROPOSED_PENDING_HUMAN_RATIFICATION):
    # the target may only be processed while the next NYSE session has not
    # opened. A stale target fails here before any network side effect.
    fresh_next = assert_target_session_fresh(target, calendar, now_utc)
    print(f"NEXT_SESSION_NOT_YET_OPEN = {fresh_next.isoformat()}")

    # Full guard validation pre-network (duplicate/order/early/stress/
    # quarantine/completion via close_utc).
    guard_state = ShadowState(activation_session=activation_session)
    guard_state.observed_sessions = list(observed)
    if target < activation_session:
        raise DataContractError(f"SHADOW_BACKFILL_FORBIDDEN: {target}.")
    guard_state.record_session(target, calendar, now_utc)

    # Provider accessibility check pre-network (delayed SIP 15-min boundary)
    provider_eligible_after_utc = observation_eligible_after(target, calendar)
    if now_utc <= provider_eligible_after_utc:
        raise DataContractError(
            f"SHADOW_PROVIDER_DATA_NOT_YET_ACCESSIBLE: session {target.isoformat()} "
            f"eligible strictly after {provider_eligible_after_utc.isoformat()}, "
            f"now is {now_utc.isoformat()}."
        )

    # Complete zero-network local dispatch preflight (H): every local check
    # above passed and NOTHING has been consumed or fetched. This mode proves
    # the full live path is green without touching the attempt ledger.
    if args.local_preflight:
        print("LOCAL_PREFLIGHT = PASS")
        print("ATTEMPT_CONSUMED = false")
        print("NETWORK_REQUESTS = 0")
        return EXIT_OK

    # F18: consume the attempt atomically (one-shot) ONLY after ALL local
    # preflight passed, immediately before market-data transport. Any crash
    # or failure after this point burns the attempt; reuse fails closed.
    # Local preflight failures above leave the ledger UNCHANGED.
    consume_dispatch_attempt(
        state_dir,
        ledger_key,
        {
            "authorization": args.authorization,
            "authority_sha256": authority_file_sha,
            "observation_ordinal": expected_ordinal,
            "dispatch_attempt": args.dispatch_attempt,
            "target_session": target.isoformat(),
        },
    )

    client = _client if _client is not None else HYP011AlpacaClient(http_attempt_listener=_count)
    fetched: Dict[str, Dict[str, Any]] = {}
    for symbol in SYMBOLS:
        fetched[symbol] = {}
        for adjustment in (PriceAdjustment.SPLIT, PriceAdjustment.RAW):
            result = client.fetch_single_session(
                symbol=symbol, session=target, feed=MarketDataFeed.SIP,
                adjustment=adjustment, timeframe="1Day", now_utc=now_utc,
            )
            fetched[symbol][adjustment.value] = {
                "bar": result.bars[0],
                "pages": result.pages_metadata,
                "raw_bytes": result.pages_raw_bytes,
            }
    print(f"NETWORK_REQUESTS_ISSUED = {attempts[0]}")

    # Six-series input qualification.
    market_opens: Dict[str, Decimal] = {}
    market_closes: Dict[str, Decimal] = {}
    provider_section: Dict[str, Any] = {"http_attempts": attempts[0], "series": {}}
    for symbol in SYMBOLS:
        split_bar = fetched[symbol]["split"]["bar"]
        raw_bar = fetched[symbol]["raw"]["bar"]
        if split_bar.timestamp_utc.date() != target or raw_bar.timestamp_utc.date() != target:
            raise DataContractError(f"SHADOW_SERIES_DATE_MISMATCH: {symbol}.")
        market_opens[symbol] = raw_bar.open
        market_closes[symbol] = raw_bar.close
        provider_section["series"][symbol] = {}
        for adj_name in ("split", "raw"):
            entry = fetched[symbol][adj_name]
            provider_section["series"][symbol][adj_name] = {
                "bar": {
                    "t": entry["bar"].timestamp_utc.isoformat(),
                    "o": str(entry["bar"].open), "h": str(entry["bar"].high),
                    "l": str(entry["bar"].low), "c": str(entry["bar"].close),
                    "v": str(entry["bar"].volume),
                },
                "pages": [
                    {"page_index": m.page_index, "byte_length": m.byte_length,
                     "bar_count": m.bar_count,
                     "raw_sha256": hashlib.sha256(b).hexdigest()}
                    for m, b in zip(entry["pages"], entry["raw_bytes"])
                ],
            }

    # Split lineage: ratio continuity vs prior observed closes from state.
    split_section: Dict[str, Any] = {}
    market_split_closes: Dict[str, Decimal] = {
        symbol: fetched[symbol]["split"]["bar"].close for symbol in SYMBOLS
    }
    prior_closes: Dict[str, Any] = {}
    if observed:
        stored_raw = verified.get("last_closes_raw", {})
        stored_split = verified.get("last_closes_split", {})
        for symbol in SYMBOLS:
            if symbol in stored_raw and symbol in stored_split:
                prior_closes[symbol] = {
                    "raw": stored_raw[symbol], "split": stored_split[symbol]
                }
    for symbol in SYMBOLS:
        split_section[symbol] = _check_split_continuity(
            symbol, market_closes, market_split_closes, prior_closes,
        )

    # Restore economic state (fresh on session one).
    if observed:
        portfolio = ShadowPortfolio.from_dict(verified["strategy"])
        benchmark = ShadowBenchmark.from_dict(verified["benchmark"])
        completed_rebalances = int(verified.get("completed_annual_rebalances", 0))
        previous_sha = verified.get("last_observation_sha256")
    else:
        portfolio = ShadowPortfolio()
        benchmark = ShadowBenchmark()
        completed_rebalances = 0
        previous_sha = None

    # Transaction type.
    if not observed:
        transaction_type = "INITIAL_ALLOCATION"
        is_rebalance = True
    elif target.year not in {date.fromisoformat(s).year for s in observed}:
        transaction_type = "SCHEDULED_ANNUAL_REBALANCE"
        is_rebalance = True
    else:
        transaction_type = "HOLD"
        is_rebalance = False

    market = SessionMarket(session=target, opens_raw=market_opens, closes_raw=market_closes)
    pre_strategy = portfolio.to_dict()
    pre_benchmark = benchmark.to_dict()
    strategy_frag = process_strategy_session(
        portfolio, market, dividends, is_rebalance,
        BASELINE_SLIPPAGE_BPS, 1, "SHADOW_BASELINE",
    )
    bench_div = dividends.get("SPY")
    bench_frag = process_benchmark_session(
        benchmark, target, market_opens["SPY"], market_closes["SPY"],
        bench_div, BASELINE_SLIPPAGE_BPS,
    )

    if recovery_auth is not None:
        authority_section: Dict[str, Any] = {
            "activation_binding": recovery_auth.manifest_path,
            "activation_binding_id": recovery_auth.binding_id,
            "activation_binding_sha256": recovery_auth.manifest_sha256,
            "activation_binding_commit_sha": recovery_auth.binding_commit_sha,
            "activation_binding_commit_utc": recovery_auth.binding_commit_utc,
            "operational_activation_session": recovery_auth.activation_session.isoformat(),
            "authorization": args.authorization,
            "ordinal": args.ordinal,
            "dispatch_attempt": expected_dispatch_attempt,
        }
    else:
        authority_section = {
            "activation_binding": (
                str(binding_path)
                if binding_path is not None
                else "docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_ACTIVATION_BINDING.json"
            ),
            "authorization": args.authorization,
            "ordinal": args.ordinal,
            "dispatch_attempt": expected_dispatch_attempt,
        }

    observation: Dict[str, Any] = {
        "schema_version": 1,
        "hypothesis_id": "HYP_011",
        "session": target.isoformat(),
        "processed_at_utc": now_utc.isoformat(),
        "authority": authority_section,
        "provider": provider_section,
        "corporate_actions": ca_section,
        "split_qualification": split_section,
        "transaction_type": transaction_type,
        "pre_state": {
            "strategy": pre_strategy,
            "benchmark": pre_benchmark,
        },
        "strategy": strategy_frag,
        "benchmark": bench_frag,
        "metrics_non_decisive": {
            "strategy_equity": strategy_frag["equity"],
            "strategy_daily_return": strategy_frag["daily_return"],
            "strategy_drawdown": strategy_frag["drawdown"],
            "benchmark_equity": bench_frag["equity"],
            "observed_session_ordinal": len(observed) + 1,
        },
        "scientific_status": "NON_DECISIVE_PROSPECTIVE_SHADOW_MONITORING",
        "paper": False,
        "live": False,
        "capital": "0.00",
        "no_real_orders": True,
    }
    if args.segment_id:
        observation["segment_id"] = args.segment_id
    if segment_activation_sha256 is not None:
        observation["segment_activation_authority_sha256"] = segment_activation_sha256
    digest = append_observation(
        state_dir,
        target,
        observation,
        previous_sha,
        portfolio=portfolio,
        benchmark=benchmark,
        completed_annual_rebalances=(
            completed_rebalances
            + (1 if transaction_type == "SCHEDULED_ANNUAL_REBALANCE" else 0)
        ),
        extra_state={
            "last_closes_raw": {s: str(market_closes[s]) for s in SYMBOLS},
            "last_closes_split": {s: str(market_split_closes[s]) for s in SYMBOLS},
        },
        activation_session=activation_session,
        recovery_authority=recovery_auth,
    )
    print(f"Observation sealed: {digest}")
    print("STATE: observation committed; no further sessions in this invocation.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
