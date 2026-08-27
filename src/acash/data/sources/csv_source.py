"""CSV data source adapter for the ACASH market data subsystem."""

import io
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union
import pandas as pd
import pyarrow as pa

from acash.data.schema import CANONICAL_ARROW_SCHEMA
from acash.data.sources.base import IDataSourceAdapter


class CsvSourceAdapter(IDataSourceAdapter):
    """Adapter for ingesting market data from CSV files."""

    def read_source(self, source_path_or_uri: Union[str, Path]) -> Tuple[bytes, pa.Table]:
        """Read CSV file and return raw bytes alongside parsed PyArrow table."""
        path = Path(source_path_or_uri)
        with open(path, "rb") as f:
            raw_bytes = f.read()

        df = pd.read_csv(io.BytesIO(raw_bytes))

        # Normalize column names to lowercase
        df.columns = df.columns.str.strip().str.lower()

        # Parse timestamps to UTC datetime
        def parse_utc_dt(val: Any) -> datetime:
            if isinstance(val, datetime):
                if val.tzinfo is None:
                    return val.replace(tzinfo=timezone.utc)
                return val.astimezone(timezone.utc)
            # Parse via pandas
            parsed = pd.to_datetime(val, utc=True)
            if hasattr(parsed, "to_pydatetime"):
                dt_obj: datetime = parsed.to_pydatetime()
                return dt_obj
            return datetime.fromisoformat(str(val)).astimezone(timezone.utc)


        records: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            rec = dict(row)
            rec["event_start_utc"] = parse_utc_dt(rec["event_start_utc"])
            rec["event_end_utc"] = parse_utc_dt(rec["event_end_utc"])
            if "knowledge_time_utc" in rec and pd.notna(rec["knowledge_time_utc"]):
                rec["knowledge_time_utc"] = parse_utc_dt(rec["knowledge_time_utc"])
            else:
                rec["knowledge_time_utc"] = rec["event_end_utc"]

            rec["open"] = Decimal(str(rec["open"]))
            rec["high"] = Decimal(str(rec["high"]))
            rec["low"] = Decimal(str(rec["low"]))
            rec["close"] = Decimal(str(rec["close"]))
            rec["volume"] = Decimal(str(rec["volume"]))
            rec["quote_volume"] = Decimal(str(rec.get("quote_volume", "0"))) if pd.notna(rec.get("quote_volume")) else Decimal("0")
            rec["trade_count"] = int(rec.get("trade_count", -1)) if pd.notna(rec.get("trade_count")) else -1
            rec["revision_seq"] = int(rec.get("revision_seq", 1)) if pd.notna(rec.get("revision_seq")) else None

            records.append(rec)

        pydict = {
            "source_id": [r["source_id"] for r in records],
            "symbol": [r["symbol"] for r in records],
            "timeframe": [r["timeframe"] for r in records],
            "event_start_utc": [r["event_start_utc"] for r in records],
            "event_end_utc": [r["event_end_utc"] for r in records],
            "knowledge_time_utc": [r["knowledge_time_utc"] for r in records],
            "revision_seq": [r.get("revision_seq", 1) or 1 for r in records],
            "open": [r["open"] for r in records],
            "high": [r["high"] for r in records],
            "low": [r["low"] for r in records],
            "close": [r["close"] for r in records],
            "volume": [r["volume"] for r in records],
            "quote_volume": [r["quote_volume"] for r in records],
            "trade_count": [r["trade_count"] for r in records],
        }

        table = pa.Table.from_pydict(pydict, schema=CANONICAL_ARROW_SCHEMA)
        return raw_bytes, table
