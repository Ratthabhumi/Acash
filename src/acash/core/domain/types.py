"""Domain helper types and validation utilities for ACASH."""

import math
from decimal import Decimal
from typing import Any, Mapping, TypeVar

from acash.core.domain.exceptions import DomainValidationError

K = TypeVar("K")
V = TypeVar("V")


class FrozenDict(dict[K, V]):
    """An immutable dictionary that rejects in-place modifications."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def __setitem__(self, key: K, value: V) -> None:
        raise TypeError(f"'{self.__class__.__name__}' object does not support item assignment (immutable).")

    def __delitem__(self, key: K) -> None:
        raise TypeError(f"'{self.__class__.__name__}' object does not support item deletion (immutable).")

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError(f"'{self.__class__.__name__}' object does not support pop (immutable).")

    def popitem(self) -> Any:
        raise TypeError(f"'{self.__class__.__name__}' object does not support popitem (immutable).")

    def clear(self) -> None:
        raise TypeError(f"'{self.__class__.__name__}' object does not support clear (immutable).")

    def update(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(f"'{self.__class__.__name__}' object does not support update (immutable).")

    def setdefault(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError(f"'{self.__class__.__name__}' object does not support setdefault (immutable).")


def ensure_finite_decimal(val: Decimal, field_name: str = "field") -> Decimal:
    """Ensure a Decimal value is finite and real (rejects NaN, +Inf, -Inf)."""
    if val.is_nan() or val.is_infinite():
        raise DomainValidationError(f"{field_name} must be a finite Decimal, got: {val}")
    return val


def ensure_finite_float(val: float, field_name: str = "field") -> float:
    """Ensure a float value is finite and real (rejects NaN, +Inf, -Inf)."""
    if math.isnan(val) or math.isinf(val):
        raise DomainValidationError(f"{field_name} must be a finite float, got: {val}")
    return val


def freeze_mapping(mapping: Mapping[K, V]) -> FrozenDict[K, V]:
    """Create an immutable mapping from an input mapping via defensive copy."""
    if isinstance(mapping, FrozenDict):
        return mapping
    # Defensive copy into new FrozenDict
    return FrozenDict(dict(mapping))
