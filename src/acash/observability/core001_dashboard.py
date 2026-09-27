"""CORE-001 / HYP_011 read-only dashboard view-model derivation.

Reads canonical prospective artifacts (``state.json`` + sealed
``observations/*.json``) and DERIVES presentation. NEVER writes, mutates,
fetches, or authorizes. Missing pre-first-observation evidence renders as
NOT YET OBSERVED / N/A — never ERROR — unless something that SHOULD exist
is missing or corrupt, which yields EVIDENCE_INVALID_OR_BLOCKED.

Governance mirror (read, not created):
S1 = 20 observed; S2 = 60 observed (Obs 1-60); S2 gates MDD < 25%,
cumret > -20%, every daily > -10% (diagnostic until Obs 60);
PAPER_ELIGIBLE only from canonical qualification evidence (no such
artifact exists in v1, so the dashboard never derives it from counts).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from acash.core.domain.exceptions import DataContractError
from acash.research.hyp_009.accounting import annualized_sharpe, max_drawdown
from acash.research.hyp_011.shadow_ops import verify_chain

CORE_ID = "CORE-001"
HYPOTHESIS_ID = "HYP_011"
STRATEGY_NAME = "Global 80/20 Strategic Allocation Core"
STATE_SCHEMA_VERSION = 1
STARTING_AUM = Decimal("100000.00")

S1_REQUIRED = 20
S2_REQUIRED = 60
S4_CHECKPOINTS = (126, 252)
LONG_HORIZON_REQUIRED = 504
REQUIRED_ANNUAL_REBALANCES = 2

S2_MDD_LIMIT = Decimal("0.25")
S2_CUMRET_FLOOR = Decimal("-0.20")
S2_DAILY_FLOOR = Decimal("-0.10")

NOT_YET = "NOT YET OBSERVED"


def _blocked(reason: str) -> Dict[str, Any]:
    return {"status": "EVIDENCE_INVALID_OR_BLOCKED", "reason": reason}


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DataContractError(f"DASHBOARD_UNREADABLE_ARTIFACT: {path.name}.") from exc
    if not isinstance(doc, dict):
        raise DataContractError(f"DASHBOARD_ARTIFACT_NOT_AN_OBJECT: {path.name}.")
    return doc


def _stdev_ddof1(values: List[Decimal]) -> Decimal:
    mean = sum(values, Decimal("0")) / Decimal(len(values))
    variance = sum((v - mean) ** 2 for v in values) / Decimal(len(values) - 1)
    if variance <= Decimal("0"):
        raise DataContractError("DASHBOARD_ZERO_VARIANCE.")
    return variance.sqrt()


def build_dashboard_state(state_dir: Path | str) -> Dict[str, Any]:
    """Derive the CORE-001 dashboard view model from canonical artifacts."""
    root = Path(state_dir)
    state_path = root / "state.json"
    if not state_path.is_file():
        return _pres1_state("NO_STATE_FILE_YET")

    try:
        state_doc = _read_json(state_path)
        chain_doc = verify_chain(root)
    except (DataContractError, ValueError) as exc:
        # ValueError covers malformed JSON escaping canonical readers;
        # the dashboard boundary still fails closed, never crashes.
        return _base_shell(
            observed_sessions=[],
            evidence={"status": "EVIDENCE_INVALID_OR_BLOCKED", "reason": str(exc)},
        )

    if state_doc.get("schema_version") != STATE_SCHEMA_VERSION:
        return _base_shell(
            observed_sessions=[],
            evidence=_blocked("UNSUPPORTED_STATE_SCHEMA_VERSION."),
        )
    if state_doc.get("hypothesis_id") != HYPOTHESIS_ID:
        return _base_shell(
            observed_sessions=[],
            evidence=_blocked("STATE_HYPOTHESIS_MISMATCH."),
        )

    observed: List[str] = list(state_doc.get("observed_sessions", []))
    obs_dir = root / "observations"
    try:
        records = _load_observations(obs_dir, observed)
    except DataContractError as exc:
        return _base_shell(
            observed_sessions=observed,
            evidence=_blocked(str(exc)),
        )

    evidence = _evidence_section(chain_doc, records)
    if evidence.get("status") == "EVIDENCE_INVALID_OR_BLOCKED":
        return _base_shell(observed_sessions=observed, evidence=evidence)

    return _base_shell(
        observed_sessions=observed,
        evidence=evidence,
        portfolio=_portfolio_section(state_doc, records),
        benchmark=_benchmark_section(state_doc, records),
        performance=_performance_section(records),
        s2=_s2_section(records),
        equity_series=_equity_series(records),
        progress_extra={
            "completed_annual_rebalances": int(
                state_doc.get("completed_annual_rebalances", 0)
            ),
        },
    )


def _base_shell(
    observed_sessions: List[str],
    evidence: Dict[str, Any],
    portfolio: Optional[Dict[str, Any]] = None,
    benchmark: Optional[Dict[str, Any]] = None,
    performance: Optional[Dict[str, Any]] = None,
    s2: Optional[Dict[str, Any]] = None,
    equity_series: Optional[List[Dict[str, Any]]] = None,
    progress_extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    count = len(observed_sessions)
    if count == 0:
        stage = "PRE-S1"
    elif count < S1_REQUIRED:
        stage = "S1_OPERATIONAL_SANITY_IN_PROGRESS"
    elif count < S2_REQUIRED:
        stage = "S1_REVIEW_REQUIRED"
    else:
        stage = "S2_QUALIFICATION_REVIEW_REQUIRED"
    rebalances = int((progress_extra or {}).get("completed_annual_rebalances", 0))
    return {
        "identity": {
            "core_id": CORE_ID,
            "hypothesis_id": HYPOTHESIS_ID,
            "strategy_name": STRATEGY_NAME,
        },
        "governance": {
            "stage": stage,
            "paper_eligible": False,
            "paper_eligible_basis": "NO_QUALIFICATION_EVIDENCE_IN_V1",
            "paper_authorized": False,
            "live_authorized": False,
            "live_locked": True,
            "real_capital_authority_usd": "0.00",
            "no_real_orders": True,
        },
        "progress": {
            "observed_sessions": count,
            "s1_required": S1_REQUIRED,
            "s2_required": S2_REQUIRED,
            "s4_checkpoints": list(S4_CHECKPOINTS),
            "long_horizon_required": LONG_HORIZON_REQUIRED,
            "completed_annual_rebalances": rebalances,
            "required_annual_rebalances": REQUIRED_ANNUAL_REBALANCES,
        },
        "portfolio": portfolio or _empty_portfolio(),
        "benchmark": benchmark or _empty_benchmark(),
        "performance": performance or _empty_performance(),
        "s2": s2 or _empty_s2(),
        "equity_series": equity_series if equity_series is not None else [],
        "evidence": evidence,
        "runtime": {
            "runtime_status": "UNAVAILABLE_FROM_DASHBOARD",
            "timer_status": "UNAVAILABLE_FROM_DASHBOARD",
            "service_status": "UNAVAILABLE_FROM_DASHBOARD",
            "note": "Dashboard v1 performs no remote access.",
        },
        "incident": {"category": "NONE", "basis": "NO_INCIDENCE_EVIDENCE"},
    }


def _pres1_state(reason: str) -> Dict[str, Any]:
    shell = _base_shell(
        observed_sessions=[],
        evidence={
            "status": "AWAITING_OBSERVATION",
            "reason": reason,
            "latest_observation_ordinal": None,
            "latest_observation_session": None,
        },
    )
    return shell


def _empty_portfolio() -> Dict[str, Any]:
    return {
        "total_equity": str(STARTING_AUM),
        "cash": str(STARTING_AUM),
        "receivable": "0",
        "holdings": {"ACWI": 0, "AGG": 0},
        "basis": "CANONICAL_INITIAL_ALL_CASH",
    }


def _empty_benchmark() -> Dict[str, Any]:
    return {"equity": None, "shares": 0, "status": NOT_YET}


def _empty_performance() -> Dict[str, Any]:
    return {
        "latest_daily_return": None,
        "cumulative_return": None,
        "current_drawdown": None,
        "max_drawdown": None,
        "annualized_sharpe": None,
        "annualized_volatility": None,
        "status": "INSUFFICIENT_OBSERVATIONS",
    }


def _empty_s2() -> Dict[str, Any]:
    return {
        "mdd_limit": str(S2_MDD_LIMIT),
        "cumulative_return_floor": str(S2_CUMRET_FLOOR),
        "daily_return_floor": str(S2_DAILY_FLOOR),
        "current_mdd": None,
        "current_cumulative_return": None,
        "worst_daily_return": None,
        "evaluation_state": "INSUFFICIENT_OBSERVATIONS",
        "note": "Diagnostic only until Observation 60.",
    }


def _load_observations(obs_dir: Path, observed: List[str]) -> List[Dict[str, Any]]:
    files = sorted(obs_dir.glob("*.json")) if obs_dir.is_dir() else []
    if len(files) != len(observed):
        raise DataContractError(
            "DASHBOARD_OBSERVATION_COUNT_MISMATCH: files != state ledger."
        )
    records: List[Dict[str, Any]] = []
    seen_sessions: List[str] = []
    seen_ordinals: List[Any] = []
    for path in files:
        doc = _read_json(path)
        session = doc.get("session")
        if not isinstance(session, str):
            raise DataContractError(f"DASHBOARD_OBSERVATION_MISSING_SESSION: {path.name}.")
        if session in seen_sessions:
            raise DataContractError(f"DASHBOARD_DUPLICATE_SESSION: {session}.")
        seen_sessions.append(session)
        raw_auth = doc.get("authority")
        auth_map: Dict[str, Any] = raw_auth if isinstance(raw_auth, dict) else {}
        ordinal = auth_map.get("ordinal")
        if ordinal in seen_ordinals and ordinal is not None:
            raise DataContractError(f"DASHBOARD_DUPLICATE_ORDINAL: {ordinal}.")
        seen_ordinals.append(ordinal)
        strategy = doc.get("strategy")
        bench = doc.get("benchmark")
        if not isinstance(strategy, dict) or "equity" not in strategy:
            raise DataContractError(f"DASHBOARD_OBSERVATION_MISSING_STRATEGY: {path.name}.")
        if not isinstance(bench, dict) or "equity" not in bench:
            raise DataContractError(f"DASHBOARD_OBSERVATION_MISSING_BENCHMARK: {path.name}.")
        for key in ("strategy", "benchmark"):
            equity = Decimal(str(doc[key]["equity"]))
            if not equity.is_finite() or equity <= Decimal("0"):
                raise DataContractError(
                    f"DASHBOARD_NONPOSITIVE_EQUITY: {path.name} {key}."
                )
        records.append(doc)
    if set(seen_sessions) != set(observed):
        raise DataContractError("DASHBOARD_OBSERVATION_SET_MISMATCH.")
    records.sort(key=lambda d: str(d.get("session")))
    return records


def _equity_series(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per-session sealed equity points for charts (no interpolation, no gaps filled)."""
    series: List[Dict[str, Any]] = []
    ordinal = 0
    for doc in records:
        ordinal += 1
        raw_authority = doc.get("authority")
        authority: Dict[str, Any] = raw_authority if isinstance(raw_authority, dict) else {}
        series.append(
            {
                "session": doc.get("session"),
                "ordinal": authority.get("ordinal", ordinal),
                "strategy_equity": str(doc["strategy"]["equity"]),
                "benchmark_equity": str(doc["benchmark"]["equity"]),
                "strategy_drawdown": str(doc["strategy"].get("drawdown", "0")),
            }
        )
    return series


def _evidence_section(
    chain_doc: Dict[str, Any], records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    if not records:
        return {
            "status": "AWAITING_OBSERVATION",
            "reason": "OBSERVED_COUNT_ZERO",
            "latest_observation_ordinal": None,
            "latest_observation_session": None,
        }
    latest = records[-1]
    raw_authority = latest.get("authority")
    raw_provider = latest.get("provider")
    raw_ca = latest.get("corporate_actions")
    authority: Dict[str, Any] = raw_authority if isinstance(raw_authority, dict) else {}
    provider: Dict[str, Any] = raw_provider if isinstance(raw_provider, dict) else {}
    ca_doc: Dict[str, Any] = raw_ca if isinstance(raw_ca, dict) else {}
    ca_status = "N/A"
    if ca_doc:
        first = next(iter(ca_doc.values()))
        if isinstance(first, dict) and "status" in first:
            ca_status = str(first["status"])
        else:
            ca_status = "DETERMINATIONS_PRESENT"
    return {
        "status": str(latest.get("scientific_status", "SEALED")),
        "reason": "LATEST_SEALED_OBSERVATION",
        "latest_observation_ordinal": authority.get("ordinal"),
        "latest_observation_session": latest.get("session"),
        "latest_artifact_sha256": chain_doc.get("last_observation_sha256"),
        "previous_artifact_sha256": latest.get("previous_observation_sha256"),
        "provider_attempts": provider.get("http_attempts"),
        "corporate_action_status": ca_status,
        "state_chain_health": "READY",
        "observation_count": len(records),
    }


def _portfolio_section(
    state_doc: Dict[str, Any], records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    if records:
        frag = records[-1]["strategy"]
        return {
            "total_equity": str(frag.get("equity")),
            "cash": str(frag.get("cash")),
            "receivable": str(frag.get("receivable", "0")),
            "holdings": dict(frag.get("holdings", {})),
            "market_value": str(frag.get("market_value", "0")),
            "basis": "LATEST_SEALED_OBSERVATION",
        }
    strategy = state_doc.get("strategy")
    if isinstance(strategy, dict) and "cash" in strategy:
        return {
            "total_equity": str(STARTING_AUM),
            "cash": str(strategy.get("cash")),
            "receivable": "0",
            "holdings": dict(strategy.get("holdings", {"ACWI": 0, "AGG": 0})),
            "basis": "CANONICAL_INITIAL_ALL_CASH",
        }
    return _empty_portfolio()


def _benchmark_section(
    state_doc: Dict[str, Any], records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    if records:
        frag = records[-1]["benchmark"]
        last_eq = Decimal(str(frag["equity"]))
        # Frozen semantics: benchmark starts from simulated starting AUM
        # ($100,000 prev_equity/peak); Observation #1 daily return already
        # includes entry friction against that base. Cumulative return must
        # therefore use STARTING_AUM, not the first sealed equity.
        bench_return = last_eq / STARTING_AUM - Decimal("1")
        return {
            "equity": str(frag.get("equity")),
            "shares": frag.get("shares", 0),
            "return_since_entry": str(bench_return),
            "status": "SEALED",
        }
    return _empty_benchmark()


def _performance_section(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return _empty_performance()
    equities = [Decimal(str(r["strategy"]["equity"])) for r in records]
    rets = [Decimal(str(r["strategy"].get("daily_return", "0"))) for r in records]
    start = STARTING_AUM
    cumret = equities[-1] / start - Decimal("1")
    mdd = max_drawdown([start] + equities)
    if len(records) >= 2:
        try:
            sharpe = annualized_sharpe(rets)
            vol = _stdev_ddof1(rets) * Decimal(252).sqrt()
        except DataContractError:
            sharpe, vol = None, None
    else:
        sharpe, vol = None, None
    return {
        "latest_daily_return": str(rets[-1]),
        "cumulative_return": str(cumret),
        "current_drawdown": str(records[-1]["strategy"].get("drawdown", "0")),
        "max_drawdown": str(mdd),
        "annualized_sharpe": str(sharpe) if sharpe is not None else None,
        "annualized_volatility": str(vol) if vol is not None else None,
        "status": "DIAGNOSTIC_ONLY_UNTIL_OBSERVATION_60",
    }


def _s2_section(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    base = _empty_s2()
    if not records:
        return base
    window = records[:S2_REQUIRED]
    equities = [Decimal(str(r["strategy"]["equity"])) for r in window]
    rets = [Decimal(str(r["strategy"].get("daily_return", "0"))) for r in window]
    base["current_mdd"] = str(max_drawdown([STARTING_AUM] + equities))
    base["current_cumulative_return"] = str(equities[-1] / STARTING_AUM - Decimal("1"))
    base["worst_daily_return"] = str(min(rets))
    if len(records) < S2_REQUIRED:
        base["evaluation_state"] = "INSUFFICIENT_OBSERVATIONS"
    else:
        base["evaluation_state"] = "S2_QUALIFICATION_REVIEW_REQUIRED"
    return base
