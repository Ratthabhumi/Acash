"""Authorized OpenFIGI batch over held tickers: ticker-only disclosure, reviewable candidates.

The Owner authorized sending the *ticker list* to OpenFIGI for identity discovery. This module sends
nothing else — no quantities, cost basis, account numbers, values or screenshots — and writes the
results to a git-ignored private file whose entries stay `PENDING_OWNER_REVIEW` until the Owner
confirms a FIGI. It never changes a valuation.

Usage: ``python -m acash.market_data.identity_batch [--dry-run]``
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from acash.invest import market_authority as ma
from acash.market_data import openfigi as of

SNAPSHOT = Path("data/private/snapshot.json")
OUTPUT = Path("data/private/security_identities.json")
EXCLUDED = frozenset({"SCBSET50", "MTS-GOLD"})
SCHEMA = "ACASH_SECURITY_IDENTITIES_V1"


def held_tickers(snapshot: Path = SNAPSHOT) -> List[str]:
    """Unique held identifiers, excluding instruments that are not ordinary US listings."""
    doc = json.loads(snapshot.read_text(encoding="utf-8"))
    securities = doc.get("securities")
    if not isinstance(securities, list):
        raise ValueError("snapshot securities missing")
    return sorted({str(row["security_id"]) for row in securities
                   if isinstance(row, dict) and row.get("security_id")} - EXCLUDED)


def rows_for(results: Sequence[of.MappingResult]) -> List[Dict[str, Any]]:
    return [{"ticker": r.job.get("idValue"), "status": r.status, "code": r.code,
             "candidates": [{"figi": c.figi, "composite_figi": c.composite_figi, "name": c.name,
                             "ticker": c.ticker, "exch_code": c.exch_code,
                             "security_type": c.security_type, "market_sector": c.market_sector}
                            for c in r.candidates],
             "owner_confirmation": "PENDING_OWNER_REVIEW" if r.candidates else "NONE"}
            for r in results]


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dry = "--dry-run" in args
    tickers = held_tickers()
    print(f"tickers_authorized={len(tickers)}")
    if dry:
        return 0
    key = ma.identity_credential()
    if key is None:
        print("REFUSED_NO_CREDENTIAL")
        return 2
    provider = of.OpenFIGIIdentityProvider(key, of.urllib_post, lambda: True,
                                           lambda: datetime.now(timezone.utc))
    try:
        results = provider.map_identifiers("TICKER", tickers, exchCode="US")
    except Exception as exc:  # one diagnostic retry without the venue hint
        print("first_attempt=" + str(exc).split(":")[0])
        results = provider.map_identifiers("TICKER", tickers)
    rows = rows_for(results)
    counts: Dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    OUTPUT.write_text(json.dumps({"schema": SCHEMA, "data_class": "OWNER_PRIVATE_OBSERVATION",
                                  "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                  "evidence": "OPENFIGI_V3_MAPPING_TICKER_ONLY", "rows": rows},
                                 indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("counts=" + json.dumps(counts, sort_keys=True))
    print("written=" + str(OUTPUT.is_file()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
