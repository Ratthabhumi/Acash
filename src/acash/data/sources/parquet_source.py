"""Parquet data source adapter for the ACASH market data subsystem."""

from pathlib import Path
from typing import Tuple, Union
import pyarrow as pa
import pyarrow.parquet as pq

from acash.data.sources.base import IDataSourceAdapter


class ParquetSourceAdapter(IDataSourceAdapter):
    """Adapter for reading market data from raw Parquet files."""

    def read_source(self, source_path_or_uri: Union[str, Path]) -> Tuple[bytes, pa.Table]:
        """Read Parquet file and return raw file bytes alongside PyArrow table."""
        path = Path(source_path_or_uri)
        with open(path, "rb") as f:
            raw_bytes = f.read()

        table = pq.read_table(path)
        return raw_bytes, table
