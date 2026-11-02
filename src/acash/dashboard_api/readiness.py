"""Launcher readiness: governance flags, ODR states and private-view availability.

Prints statuses only; never amounts, file contents or session tokens. The private view is
opened only when ODR-001 is RATIFIED, and then only through the server's contract check.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from acash.dashboard_api.private_view_server import DEFAULT_VIEW, load_view
from acash.ppds import private_observation as po
from acash.ppds import transactions
from acash.research.d6.decision_pack import GOVERNANCE


def readiness(view_path: Optional[Path] = None) -> Dict[str, Any]:
    path = view_path or (po._repo_root() / DEFAULT_VIEW)
    odr1 = po.odr_state(None, po.SCHEMA_V1_2)
    odr2 = po.odr_state(po._repo_root() / transactions.AUTHORIZATION_RECORD, transactions.SCHEMA,
                        transactions.AUTHORIZED_CAPABILITY)
    if not path.is_file():
        view = "NO_REPORT"
    elif odr1 != "RATIFIED":
        view = "PRESENT_NOT_OPENED"
    else:
        status, code, _ = load_view(path)
        view = status if code is None else f"{status} ({code})"
    blockers: List[str] = []
    if odr1 != "RATIFIED":
        blockers.append(f"ODR-001 {odr1}")
    if view != "READY":
        blockers.append(f"private view {view}")
    return {"governance": dict(GOVERNANCE), "odr_001": odr1, "odr_002": odr2, "private_view": view,
            "private_mode": "BLOCKED" if blockers else "READY", "blockers": blockers}


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="ACASH dashboard launcher readiness (statuses only).")
    parser.add_argument("--require-private", action="store_true", help="Exit 3 unless private mode is READY.")
    args = parser.parse_args(argv)
    state = readiness()
    g = state["governance"]
    print(f"  Governance : NO_REAL_ORDERS={str(g['NO_REAL_ORDERS']).lower()} | real capital USD "
          f"{g['REAL_CAPITAL_AUTHORITY_USD']} | D5 {g['D5_REAL_ADMISSION']} | Lane A/B {g['LANE_A_B']}"
          f" | HYP_003 {g['HYP_003']}")
    print(f"  ODR-001    : {state['odr_001']} (owner-private observation)")
    print(f"  ODR-002    : {state['odr_002']} (owner-private transactions)")
    print(f"  Private view report : {state['private_view']}")
    blockers = f" - {'; '.join(state['blockers'])}" if state["blockers"] else ""
    print(f"  Private mode : {state['private_mode']}{blockers}")
    sys.stdout.flush()
    if args.require_private and state["private_mode"] != "READY":
        sys.exit(3)


if __name__ == "__main__":
    main()
