#!/usr/bin/env python
"""Execute MEC-0015 Alpaca Corporate Actions (Cash Dividend) Qualification Probe.

Zero Credentials printed or leaked.
Zero Market Data >= 2024-05-01 accessed.
Outputs: docs/research/manifests/MEC-0015-dividend-provider-contract-manifest.json
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import httpx

# Ensure project is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.mec_0015_dividend_contract import (
    MEC_0015_DIVIDEND_START_DATE,
    MEC_0015_DIVIDEND_MAX_ALLOWED_DATE,
    validate_and_parse_dividend_records,
)


def _load_credentials_from_env_file() -> tuple[str, str]:
    """Safely bridge API credentials from environment or .env without logging."""
    import os

    key_id = os.environ.get("ACASH_ALPACA_API_KEY_ID", "") or os.environ.get("APCA_API_KEY_ID", "")
    secret = os.environ.get("ACASH_ALPACA_API_SECRET", "") or os.environ.get("APCA_API_SECRET_KEY", "")

    if not key_id or not secret:
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip("\"'")
                if k in ("ACASH_ALPACA_API_KEY_ID", "APCA_API_KEY_ID") and not key_id:
                    key_id = v
                if k in ("ACASH_ALPACA_API_SECRET", "APCA_API_SECRET_KEY") and not secret:
                    secret = v

    if not key_id or not secret:
        raise DataContractError(
            "CREDENTIAL_ABSENT: Neither ACASH_ALPACA_API_KEY_ID/APCA_API_KEY_ID nor "
            "ACASH_ALPACA_API_SECRET/APCA_API_SECRET_KEY are resolved."
        )
    return key_id, secret


def main() -> int:
    print("[MEC-0015] Starting Alpaca Corporate Actions (Cash Dividend) Qualification Probe...")
    key_id, secret = _load_credentials_from_env_file()

    headers = {
        "APCA-API-KEY-ID": key_id,
        "APCA-API-SECRET-KEY": secret,
        "Accept": "application/json",
    }
    params = {
        "symbols": "SPY",
        "types": "cash_dividend",
        "data_quality": "complete",
        "start": MEC_0015_DIVIDEND_START_DATE.isoformat(),
        "end": MEC_0015_DIVIDEND_MAX_ALLOWED_DATE.isoformat(),
    }
    url = "https://data.alpaca.markets/v1/corporate-actions"

    resp = httpx.get(url, headers=headers, params=params, timeout=20.0)
    if resp.status_code != 200:
        raise DataContractError(
            f"Alpaca API error: HTTP {resp.status_code}: {resp.text[:200]}"
        )

    report = validate_and_parse_dividend_records(resp.content)

    manifest_path = Path("docs/research/manifests/MEC-0015-dividend-provider-contract-manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("[MEC-0015] Dividend probe completed successfully.")
    print(f"  Record Count: {report.record_count}")
    print(f"  Query Range: {report.query_start} to {report.query_end}")
    print(f"  Max Accessed Date: {report.max_accessed_date}")
    print(f"  Provider Mapping: {report.provider_mapping_status}")
    print(f"  PIT Classification: {report.pit_vintage_status}")
    print(f"  Raw Payload SHA-256: {report.raw_payload_sha256}")
    print(f"  Manifest written to: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
