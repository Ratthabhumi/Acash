"""Read-only preflight for the UPI private snapshot pilot.

Never writes or alters inputs. The result carries statuses, error codes and opaque
references only, never amounts. Paths outside the repository or under ``data/private/`` are
presumed owner-private and are not read at all unless ODR-001 is RATIFIED; after reading,
the schema scope, data class and storage location are checked before the contract is parsed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.invest.capacity_plan import load_capacity
from acash.invest.market_calendar import load_calendar, price_session_status
from acash.ppds.private_observation import (
    AUTHORIZATION_RECORD,
    DATA_CLASSES,
    SCHEMAS,
    PortfolioSnapshot,
    assert_private_location,
    book_summary,
    build_book,
    odr_state,
    parse_snapshot,
    presumed_private,
    read_gated_json,
)

_RECONCILED = ("RECONCILED", "CONSISTENT_WITH_DISPLAY_ROUNDING")


def _code(exc: Exception) -> str:
    return str(exc).split(":")[0].rstrip(".")


def _duplicate_cash(snapshot: PortfolioSnapshot) -> List[str]:
    """Heuristic only: equal non-zero settled cash in the same currency at two accounts of one broker."""
    seen: Dict[Tuple[str, str, str], List[str]] = {}
    for account in snapshot.accounts:
        for line in account.cash:
            if line.kind == "SETTLED" and line.amount != 0:
                seen.setdefault((account.broker, line.currency, str(line.amount)), []).append(account.account_ref)
    return sorted(",".join(sorted(set(refs))) for refs in seen.values() if len(set(refs)) > 1)


def preflight(snapshot_path: Path, capacity_path: Optional[Path] = None, output_dir: Optional[Path] = None,
              report_date: Optional[date] = None) -> Dict[str, Any]:
    checks: List[Dict[str, str]] = []

    def add(name: str, status: str, detail: str = "") -> None:
        checks.append({"check": name, "status": status, "detail": detail})

    def result() -> Dict[str, Any]:
        statuses = {c["status"] for c in checks}
        overall = ("BLOCKED" if "BLOCKED" in statuses else "INVALID" if "FAIL" in statuses else
                   "READY_WITH_WARNINGS" if "WARN" in statuses else "READY")
        return {"preflight": overall, "checks": checks, "inputs_modified": False,
                "note": "Statuses and codes only; amounts are never printed."}

    if presumed_private(snapshot_path):
        state = odr_state(None, None)
        if state != "RATIFIED":
            add("odr_authorization", "BLOCKED",
                f"{AUTHORIZATION_RECORD.as_posix()} {state}; presumed owner-private path, file not read")
            return result()
    try:
        doc = read_gated_json(snapshot_path, "PRIVATE_SNAPSHOT")
    except DataContractError as exc:
        add("snapshot_readable", "FAIL", _code(exc))
        return result()
    if not isinstance(doc, dict):
        add("snapshot_readable", "FAIL", "PRIVATE_NOT_A_MAPPING")
        return result()
    schema, data_class = doc.get("schema"), doc.get("data_class")
    add("schema", "PASS" if schema in SCHEMAS else "FAIL", str(schema) if schema in SCHEMAS else "PRIVATE_SCHEMA_MISMATCH")
    add("data_class", "PASS" if data_class in DATA_CLASSES else "FAIL",
        str(data_class) if data_class in DATA_CLASSES else "PRIVATE_DATA_CLASS_INVALID")
    if schema not in SCHEMAS or data_class not in DATA_CLASSES:
        return result()

    private = data_class == "OWNER_PRIVATE_OBSERVATION"
    if private:
        try:
            assert_private_location(snapshot_path)
            add("snapshot_location", "PASS")
        except DataContractError as exc:
            add("snapshot_location", "FAIL", _code(exc))
        state = odr_state(None, str(schema))
        if state != "RATIFIED":
            add("odr_authorization", "BLOCKED",
                f"{AUTHORIZATION_RECORD.as_posix()} {state} for {schema}; snapshot contract not parsed")
            return result()
        add("odr_authorization", "PASS", f"{AUTHORIZATION_RECORD.as_posix()} RATIFIED for {schema}")
    else:
        add("odr_authorization", "NOT_REQUIRED", "synthetic fixture")

    try:
        snapshot = parse_snapshot(doc)
        add("snapshot_contract", "PASS", f"{len(snapshot.accounts)} accounts")
        summary = book_summary(build_book(snapshot), report_date)
    except DataContractError as exc:
        add("snapshot_contract_or_valuation", "FAIL", _code(exc))
        return result()
    add("report_type", "PASS", summary.get("report_type", "FULL_REPORT"))
    add("freshness", "WARN" if summary["valuation_stale"] else "PASS",
        f"valuation_age_days={summary['valuation_age_days']} observation_lag_days="
        f"{summary['time_alignment']['observation_lag_days']}")
    for group in _duplicate_cash(snapshot):
        add("cash_overlap", "WARN", f"POSSIBLE_DUPLICATE_CASH_ACROSS_ACCOUNTS: {group}")
    evidence = summary.get("evidence")
    if evidence:
        block = evidence[snapshot.reporting_currency]
        for acct in block["accounts"]:
            total = acct["account_total"]
            status = total["status"] if isinstance(total, dict) else str(total)
            level = "PASS" if status in _RECONCILED else "INFO" if status == "NOT_REPORTED" else "WARN"
            add(f"account_total:{acct['account_ref']}", level,
                " ".join([status, acct["evidence_level"], *acct["flags"]]))
        unverified = [s["security_id"] for s in block["security_identity"]
                      if s["identity_status"] == "SECURITY_IDENTITY_UNVERIFIED"]
        add("security_identity", "WARN" if unverified else "PASS",
            f"SECURITY_IDENTITY_UNVERIFIED: {','.join(unverified)}" if unverified else "all mapped")
        add("market_session", "INFO", block["market_session_status"])
        calendar = load_calendar()
        mics = {s.security_id: s.exchange_mic for s in snapshot.securities}
        for sid, stamp in snapshot.published_at:
            status = price_session_status(calendar, mics.get(sid), datetime.fromisoformat(stamp))
            level = ("PASS" if status == "WITHIN_REGULAR_SESSION" else
                     "INFO" if status.startswith("MARKET_SESSION_NOT_VERIFIED") else "WARN")
            add(f"market_session:{sid}", level, f"{status} ({calendar.calendar_id})")

    if capacity_path is not None:
        try:
            capacity = load_capacity(capacity_path)
            add("capacity", "PASS" if capacity.data_class == data_class else "FAIL",
                "" if capacity.data_class == data_class else "PACK_DATA_CLASS_MISMATCH")
        except DataContractError as exc:
            add("capacity", "BLOCKED" if _code(exc) == "PRIVATE_OBSERVATION_NOT_AUTHORIZED" else "FAIL", _code(exc))
    if output_dir is not None and private:
        try:
            assert_private_location(output_dir)
            add("output_location", "PASS")
        except DataContractError as exc:
            add("output_location", "FAIL", _code(exc))
    return result()


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="ACASH UPI pilot preflight (read-only; prints statuses, never amounts).")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--capacity", default=None)
    parser.add_argument("--output", default=None, help="Planned report directory (checked, not created).")
    parser.add_argument("--report-date", default=None)
    args = parser.parse_args(argv)
    report = preflight(Path(args.snapshot), Path(args.capacity) if args.capacity else None,
                       Path(args.output) if args.output else None,
                       date.fromisoformat(args.report_date) if args.report_date else None)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["preflight"] in ("READY", "READY_WITH_WARNINGS") else 2)


if __name__ == "__main__":
    main()
