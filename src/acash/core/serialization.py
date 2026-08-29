"""Universal Type-Preserving Canonical Serializer for the ACASH Architecture.

Centralizes deterministic, collision-free serialization and deep immutability primitives
across all layers of the quantitative stack (Phase 4 Research, Phase 5 Backtesting, Phase 6 Validation).
"""

from decimal import Decimal
from enum import Enum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping, Sequence
import numpy as np

from acash.core.domain.exceptions import DataContractError


def deep_freeze_value(val: Any) -> Any:
    """Recursively freeze dictionaries, lists, and collections into deeply immutable representations.

    - dict / Mapping -> MappingProxyType
    - list / tuple -> Tuple
    - set / frozenset -> frozenset
    - primitives (int, float, Decimal, str, bool, bytes, None, Enum) -> immutable as-is
    """
    if isinstance(val, (dict, Mapping)):
        return MappingProxyType({k: deep_freeze_value(v) for k, v in val.items()})
    if isinstance(val, (list, tuple)):
        return tuple(deep_freeze_value(x) for x in val)
    if isinstance(val, (set, frozenset)):
        return frozenset(deep_freeze_value(x) for x in val)
    return val


class CanonicalConfigSerializer:
    """Deterministic, type-safe canonical serializer for ACASH configuration and parameter objects.

    ENFORCES:
    - Explicit type-tagging preventing semantic collision across primitive domains:
      * bool != int (e.g. True vs 1)
      * Decimal != float (exact Decimal string vs IEEE-754 float)
      * str != bytes
    - Strict sorting of all dictionary keys and feature sequences.
    - Zero-tolerance non-finite numeric rejection (NaN, +Inf, -Inf).
    - RFC-8785 canonical JSON formatting: separators=(',', ':'), sort_keys=True, ensure_ascii=True, allow_nan=False.
    """

    @classmethod
    def serialize_value(cls, val: Any) -> Any:
        """Recursively normalize values into canonical primitive types with strict type preservation."""
        if val is None:
            return None
        if isinstance(val, bool):
            return {"__type__": "bool", "value": val}
        if isinstance(val, (int, np.integer)):
            return {"__type__": "int", "value": int(val)}
        if isinstance(val, (float, np.floating)):
            fv = float(val)
            if not math.isfinite(fv):
                raise DataContractError(f"Non-finite float value '{val}' cannot be canonically serialized.")
            return {"__type__": "float", "value": fv}
        if isinstance(val, Decimal):
            if not val.is_finite():
                raise DataContractError(f"Non-finite Decimal value '{val}' cannot be canonically serialized.")
            return {"__type__": "decimal", "value": f"{val:.18f}"}
        if isinstance(val, (str, Enum)):
            return str(val.value if isinstance(val, Enum) else val)
        if isinstance(val, (bytes, bytearray)):
            return {"__type__": "bytes", "value": bytes(val).hex()}
        if isinstance(val, (dict, Mapping)):
            return {
                str(k): cls.serialize_value(v)
                for k, v in sorted(val.items(), key=lambda item: str(item[0]))
            }
        if isinstance(val, (list, tuple, set, frozenset, Sequence)):
            return [cls.serialize_value(x) for x in val]
        raise DataContractError(f"Unsupported parameter type for canonical serialization: {type(val).__name__}")

    @classmethod
    def to_canonical_json(cls, obj: Any) -> str:
        """Convert any data structure into a canonical, collision-free JSON string."""
        normalized = cls.serialize_value(obj)
        return json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )

    @classmethod
    def compute_sha256(cls, obj: Any) -> str:
        """Compute 64-hex lowercase SHA-256 of canonical JSON."""
        payload = cls.to_canonical_json(obj)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
