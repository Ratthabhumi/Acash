"""Owner-run purge of the private market warehouse (retention obligation, never data recovery).

Deleting stored market observations is an obligation when the provider terms or the plan end. This
command removes every partition, the manifest, the session index and the job state, and writes an
audit record that contains counts and a reason — never the data itself.

    uv run python scripts/purge_market_data.py                          # dry run, deletes nothing
    uv run python scripts/purge_market_data.py --confirm DELETE_PRIVATE_MARKET_DATA \
        --reason "PROVIDER_TERMS_ENDED_2026_12_01"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acash.invest import market_authority as ma  # noqa: E402
from acash.market_data import warehouse as wh  # noqa: E402

CONFIRM = "DELETE_PRIVATE_MARKET_DATA"


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge the private market-data warehouse.")
    parser.add_argument("--confirm", default=None, help=f"required value: {CONFIRM}")
    parser.add_argument("--reason", default="OWNER_RETENTION_TERMINATION")
    parser.add_argument("--root", default=str(ROOT / "data" / "private" / "market_warehouse"))
    args = parser.parse_args()
    store = wh.BarWarehouse(Path(args.root), record=ROOT / ma.RECORD)
    partitions = sorted((Path(args.root) / "bars").glob("*.parquet"))
    summary = {"root": str(Path(args.root)), "partitions_present": len(partitions),
               "reason": args.reason, "confirmed": args.confirm == CONFIRM}
    if args.confirm != CONFIRM:
        summary["status"] = "DRY_RUN_NOTHING_DELETED"
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    result = store.purge(args.reason)
    summary.update({"status": "PURGED", **result})
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
