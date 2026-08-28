"""ACASH Statistical Validation & Overfitting Controls Engine (Phase 6).

Public API exports:
- CombinatorialPurgedCrossValidation
- DeflatedSharpeEngine
- MultipleTestingEngine
- OverfittingEngine
- StatisticalValidationGate
- Validation schemas (ValidationConfig, DSRResult, MultipleTestingResult, OverfittingReport, ValidationReport, ValidationGateVerdict)
"""

from acash.validation.cpcv import CombinatorialPurgedCrossValidation
from acash.validation.deflated_sharpe import DeflatedSharpeEngine
from acash.validation.gate import StatisticalValidationGate
from acash.validation.multiple_testing import MultipleTestingEngine
from acash.validation.overfitting import OverfittingEngine
from acash.validation.schema import (
    CPCVPartition,
    DSRResult,
    MultipleTestingResult,
    OverfittingReport,
    ValidationConfig,
    ValidationGateVerdict,
    ValidationReport,
)

__all__ = [
    "CombinatorialPurgedCrossValidation",
    "DeflatedSharpeEngine",
    "MultipleTestingEngine",
    "OverfittingEngine",
    "StatisticalValidationGate",
    "CPCVPartition",
    "DSRResult",
    "MultipleTestingResult",
    "OverfittingReport",
    "ValidationConfig",
    "ValidationGateVerdict",
    "ValidationReport",
]
