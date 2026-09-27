"""Generate a CORE-001 dashboard snapshot (derived presentation, read-only source).

Reads canonical HYP_011 prospective artifacts and writes ONE derived JSON
document to --out. The source state directory is NEVER modified; --out may
not lie inside the state directory. Zero network. Zero authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from acash.observability.core001_dashboard import build_dashboard_state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CORE-001 dashboard snapshot.")
    parser.add_argument("--state-dir", default="data/hyp_011/prospective")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    state_dir = Path(args.state_dir).resolve()
    out_path = Path(args.out).resolve()
    if out_path == state_dir or state_dir in out_path.parents:
        print("REFUSED: --out must not lie inside the state directory.")
        return 2

    view = build_dashboard_state(state_dir)
    payload = {
        "document": "CORE_001_DASHBOARD_SNAPSHOT_V1",
        "read_only_derivation": True,
        "network_requests_issued": 0,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_state_dir": str(state_dir),
        "view": view,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True))
        handle.write("\n")
    print(f"Snapshot written: {out_path}")
    print("NETWORK_REQUESTS_ISSUED = 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
