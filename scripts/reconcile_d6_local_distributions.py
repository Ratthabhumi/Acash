"""Build a reconciled LOCAL_EXPLORATORY distributions dataset (offline, new directory).

Inputs: a converted directory (``fetch_alpaca_d6_local_data.py convert``), the
committed BND capital-gain evidence CSV, and optionally a locally saved State Street
historical-distributions workbook for BIL. Bars and splits are copied byte-for-byte;
only distributions change. The original converted directory is never modified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from acash.core.domain.exceptions import DataContractError
from acash.research.d6.local_reconciliation import (
    RECONCILED_COLUMNS,
    apply_issuer_records,
    apply_reclassification,
    parse_ssga_distribution_xlsx,
)

BIL_CUSIP = "78468R663"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconcile(src: Path, out: Path, evidence_csv: Path, ssga_xlsx: Optional[Path], window: tuple[date, date]) -> Dict[str, Any]:
    if out.exists() and any(out.iterdir()):
        raise DataContractError(f"OUTPUT_DIR_NOT_EMPTY: {out}; use a new versioned path.")
    with (src / "distributions.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    with evidence_csv.open(encoding="utf-8", newline="") as handle:
        evidence = list(csv.DictReader(handle))
    issuer_report: Dict[str, Any] = {"status": "NOT_SUPPLIED"}
    if ssga_xlsx is not None:
        issuer = parse_ssga_distribution_xlsx(ssga_xlsx.read_bytes(), ["BIL"])
        result = apply_issuer_records(
            rows, issuer, symbol="BIL", cusip=BIL_CUSIP, window=window,
            source_ref=f"ssga-historical-distributions.xlsx sha256:{_sha(ssga_xlsx)}",
        )
        rows = result.rows
        issuer_report = {
            "symbol": "BIL",
            "matched": result.matched,
            "payable_confirmed": result.payable_confirmed,
            "payable_replaced_from_issuer": result.payable_replaced,
            "issuer_events_missing_from_provider": list(result.issuer_events_missing_from_provider),
            "issuer_zero_amount_rows_without_provider_event": result.issuer_zero_amount_rows_without_provider_event,
        }
    reconciled = apply_reclassification(rows, evidence)
    out.mkdir(parents=True, exist_ok=True)
    for name in ("bars_raw.csv", "splits.csv"):
        shutil.copyfile(src / name, out / name)
    with (out / "distributions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(RECONCILED_COLUMNS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(reconciled)
    sources = [r["payable_date_source"] for r in reconciled]
    manifest = {
        "reconciled_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "network": "NONE",
        "inputs_sha256": {
            "source_distributions.csv": _sha(src / "distributions.csv"),
            evidence_csv.name: _sha(evidence_csv),
            **({ssga_xlsx.name: _sha(ssga_xlsx)} if ssga_xlsx else {}),
        },
        "issuer_reconciliation": issuer_report,
        "counts": {
            "rows": len(reconciled),
            "by_type": {t: sum(r["distribution_type"] == t for r in reconciled)
                        for t in sorted({r["distribution_type"] for r in reconciled})},
            "by_evidence_class": {c: sum(r["evidence_class"] == c for r in reconciled)
                                  for c in sorted({r["evidence_class"] for r in reconciled})},
            "payable_provider": sources.count("PROVIDER"),
            "payable_issuer_file": sources.count("ISSUER_FILE"),
            "payable_imputed": sum(s.startswith("IMPUTED") for s in sources),
        },
        "files_sha256": {n: _sha(out / n) for n in ("bars_raw.csv", "distributions.csv", "splits.csv")},
    }
    (out / "reconciliation_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="src", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--evidence", type=Path,
                        default=Path("docs/research/evidence/bnd_capital_gain_reclassification_v34.csv"))
    parser.add_argument("--ssga-xlsx", type=Path)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2016, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    args = parser.parse_args()
    manifest = reconcile(args.src, args.out, args.evidence, args.ssga_xlsx, (args.start, args.end))
    print(json.dumps({k: manifest[k] for k in ("issuer_reconciliation", "counts", "files_sha256")}, indent=2))


if __name__ == "__main__":
    main()
