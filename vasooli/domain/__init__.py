"""
Vasooli Domain package.

Core domain types, enumerations, and error definitions
for the evidence-first MSME compliance platform.
"""

from vasooli.domain.enums import (
    DecisionOutcome,
    ExtractionMethod,
    FactStatus,
    FactType,
    InterestCalculationMethod,
    PaymentBasis,
    RecoveryStage,
    ReviewAction,
    ReviewRouting,
    Severity,
)

__all__ = [
    "DecisionOutcome",
    "ExtractionMethod",
    "FactStatus",
    "FactType",
    "InterestCalculationMethod",
    "PaymentBasis",
    "RecoveryStage",
    "ReviewAction",
    "ReviewRouting",
    "Severity",
]
