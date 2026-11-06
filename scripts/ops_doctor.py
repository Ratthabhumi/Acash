"""Read-only operational acceptance report (no network, no service changes).

    uv run python scripts/ops_doctor.py

It reads only local artifacts and never restarts or reconfigures anything. SCHEDULED_SYNC_ACCEPTED is
true only when a scheduled execution record exists; a registered task is not evidence of a run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acash.ops.ops_report import build_report

PRIVATE = Path(__import__("os").environ["ACASH_PRIVATE_DIR"]) if __import__("os").environ.get("ACASH_PRIVATE_DIR") else ROOT / "data" / "private"


def main() -> int:
    print(json.dumps(build_report(PRIVATE), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
