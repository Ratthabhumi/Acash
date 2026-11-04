"""Stage the owner-supplied Dime! tax evidence (private, not a journal write).

    uv run python scripts/tax_evidence.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acash.invest import tax_intelligence as tax  # noqa: E402

BASELINE = date(2026, 11, 2)  # frozen snapshot valuation date

SUMMARY = {
    "tax_year": 2026,
    "covered_from": "2026-01-01",
    "covered_to": "2026-09-30",
    "funds_in_usd": "3475.59",
    "funds_out_usd": "6015.01",
    "gross_dividends_usd": "123.74",
    "withheld_usd": "12.05",
    "net_dividends_usd": "111.69",
    "source": "DIME_OFFSHORE_ANNUAL_SUMMARY_SCREENSHOT",
    "observed_at": "2026-11-05T00:15:00+07:00",
    "publication_lag_days": 6,
}

TRADES = [
    {"date": "2026-11-02", "security_id": "HOOD", "amount": "100.00", "amount_currency": "USD",
     "shares": "1.1619192", "price_per_share": "86.0645", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "META", "amount": "180.00", "amount_currency": "USD",
     "shares": "0.2896287", "price_per_share": "620.4840", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "ACHR", "amount": "100.00", "amount_currency": "USD",
     "shares": "24.0615199", "price_per_share": "4.1450", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "GEV", "amount": "100.00", "amount_currency": "USD",
     "shares": "0.1160463", "price_per_share": "860.3460", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "GE", "amount": "100.00", "amount_currency": "USD",
     "shares": "0.3269861", "price_per_share": "305.3340", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "VOO", "amount": "3000.00", "amount_currency": "THB",
     "shares": "0.1271353", "price_per_share": "695.7940", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "SPCX", "amount": "50.00", "amount_currency": "USD",
     "shares": "0.3615452", "price_per_share": "138.0740", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "CRWV", "amount": "44.32", "amount_currency": "USD",
     "shares": "0.8078060", "price_per_share": "54.7780", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "IREN", "amount": "2499.88", "amount_currency": "THB",
     "shares": "3.0674157", "price_per_share": "24.03", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "ONDS", "amount": "100.00", "amount_currency": "USD",
     "shares": "15.6473354", "price_per_share": "6.38", "price_currency": "USD"},
    {"date": "2026-10-30", "security_id": "CRWV", "amount": "1500.68", "amount_currency": "THB",
     "shares": "27.4028", "price_per_share": "54.7780", "price_currency": "USD", "status": "CANCELLED",
     "note": "cancelled order; must never create a holding"},
]

CASH = [
    {"date": "2026-10-30", "description": "Dime! USD +180.00", "kind": "deposit", "amount": "180.00",
     "currency": "USD"},
    {"date": "2026-10-30", "description": "META -180.00", "kind": "buy", "amount": "-180.00",
     "currency": "USD"},
    {"date": "2026-10-30", "description": "Dime! FCD -> Dime! USD internal transfer", "kind": "internal",
     "amount": "180.00", "currency": "USD"},
]


def main() -> int:
    doc = tax.build_evidence(SUMMARY, TRADES, CASH, BASELINE)
    path = tax.write_evidence(doc)
    staged = doc["staged_trades"]
    print(json.dumps({
        "path": str(path),
        "accepted": len(staged["accepted_for_journal"]),
        "pre_baseline": len(staged["pre_baseline_candidates"]),
        "rejected": [(r["security_id"], r["reason"]) for r in staged["rejected"]],
        "withholding_ratio": doc["annual_summary"]["checks"]["effective_withholding_ratio"],
        "next_update": doc["annual_summary"]["checks"]["next_expected_update"],
        "tax_liability": doc["tax_liability"]["status"],
        "readiness": doc["readiness"]["historical_performance"],
        "flows": [(f["description"], f["classification"]) for f in doc["cash_flows"]],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
