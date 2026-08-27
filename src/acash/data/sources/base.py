"""Abstract base class for data source adapters."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Union
import pyarrow as pa


class IDataSourceAdapter(ABC):
    """Abstract interface for all ACASH market data source adapters."""

    @abstractmethod
    def read_source(self, source_path_or_uri: Union[str, Path]) -> Tuple[bytes, pa.Table]:
        """Read source data returning (raw_bytes, raw_arrow_table).

        Returns:
            Tuple[bytes, pa.Table]: (Exact raw input bytes for SHA-256 computation, PyArrow Table)
        """
        pass
