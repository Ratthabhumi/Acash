"""Universal Type-Preserving Canonical Serializer for the ACASH Architecture.

Centralizes deterministic, collision-free serialization and deep immutability primitives
across all layers of the quantitative stack (Phase 4 Research, Phase 5 Backtesting, Phase 6 Validation).

CANONICAL IDENTITY CONTRACT:
- Profile: ACASH Canonical JSON Serialization Profile v1
- Numerical Quantization: Cryptographic identity for Decimal values is defined over
  quantized canonical representation at 10^-18 precision using explicit ROUND_HALF_EVEN:
      CanonicalIdentity(x) = Q_18(x) = quantize(x, 10^-18, ROUND_HALF_EVEN)
  This ensures deterministic fixed-point comparability while bounding float64 precision drift.
- Signed Zero: Negative zero is canonicalized to positive zero (+0.0):
      Q_18(-0.0) = Q_18(+0.0) = "0.000000000000000000"
- Enum Identity: Enums are explicitly type-tagged preserving class name and value:
      {"__type__": "enum", "class": "EnumClassName", "value": "MEMBER_VALUE"}
  Ensuring Enum != str and EnumA.X != EnumB.X.
- Unordered Collections: Sets and frozensets are canonicalized by recursively normalizing
  each member, encoding each member to its canonical JSON string representation, sorting
  the resulting canonical strings lexicographically, and emitting an ordered JSON array.
- Dictionary Keys: Configuration dictionaries must strictly use string keys (isinstance(k, str)).
  Non-string keys (e.g. int, bool) are rejected to eliminate semantic key collisions.
- Closed-World Typing: Only supported types (None, bool, int, float, Decimal, str, bytes,
  dict, list, tuple, set, frozenset, Enum) are allowed; bytearray and arbitrary objects are rejected.
"""

from decimal import Decimal, ROUND_HALF_EVEN
from enum import Enum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping
import numpy as np

from acash.core.domain.exceptions import DataContractError

# Fixed canonical quantization precision constant (10^-18)
QUANTIZE_18 = Decimal("1e-18")


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
    """Deterministic, type-safe canonical serializer implementing the ACASH Canonical JSON Serialization Profile v1.

    ENFORCES:
    - Explicit type-tagging preventing semantic collision across primitive domains:
      * bool != int (e.g. True vs 1)
      * Decimal != float (exact Decimal string vs IEEE-754 float)
      * str != bytes
      * Enum != str (tagged with class name and member value)
      * EnumA.X != EnumB.X (differentiated by enum class)
    - String-only dictionary keys: Rejects non-string keys (e.g. {1: 'a', '1': 'b'}) to eliminate key collision.
    - Deterministic unordered collections: Sets and frozensets are sorted by their serialized canonical JSON strings.
    - Explicit Q_18 quantization: Decimal numbers are quantized to 10^-18 using ROUND_HALF_EVEN.
    - Signed zero canonicalization: -0.0 -> +0.0 ("0.000000000000000000").
    - Closed-world type validation: Only explicit primitive and collection types are permitted; bytearray is rejected.
    - Zero-tolerance non-finite numeric rejection (NaN, +Inf, -Inf).
    - Canonical formatting: separators=(',', ':'), sort_keys=True, ensure_ascii=True, allow_nan=False.
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
            normalized_dec = Decimal("0") if val.is_zero() else val
            quantized_dec = normalized_dec.quantize(QUANTIZE_18, rounding=ROUND_HALF_EVEN)
            return {"__type__": "decimal", "value": f"{quantized_dec:.18f}"}
        if isinstance(val, Enum):
            return {
                "__type__": "enum",
                "class": type(val).__name__,
                "value": str(val.value),
            }
        if isinstance(val, str):
            return val
        if isinstance(val, bytes):
            return {"__type__": "bytes", "value": val.hex()}
        if isinstance(val, (dict, Mapping)):
            normalized_dict = {}
            for k, v in val.items():
                if not isinstance(k, str):
                    raise DataContractError(
                        f"Dictionary keys in canonical configuration must be strictly strings, "
                        f"got key '{k}' of type '{type(k).__name__}'."
                    )
                normalized_dict[k] = cls.serialize_value(v)
            return {k: normalized_dict[k] for k in sorted(normalized_dict.keys())}
        if isinstance(val, (set, frozenset)):
            # Unordered collections: serialize each member, sort by canonical JSON string representation
            serialized_members = [cls.serialize_value(x) for x in val]
            return sorted(
                serialized_members,
                key=lambda m: json.dumps(m, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False),
            )
        if isinstance(val, (list, tuple)):
            # Ordered sequences: preserve sequential order
            return [cls.serialize_value(x) for x in val]
        raise DataContractError(f"Unsupported parameter type for canonical serialization: {type(val).__name__}")


    @classmethod
    def to_canonical_json(cls, obj: Any) -> str:
        """Convert any data structure into an ACASH Profile v1 canonical, collision-free JSON string."""
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

