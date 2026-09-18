"""
Vasooli Domain Errors.

Custom exception hierarchy for the evidence-first pipeline.
Each exception carries context (IDs, messages) to support audit logging.
"""


class VasooliError(Exception):
    """Base exception for all Vasooli domain errors."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


# ---------------------------------------------------------------------------
# Extraction Errors
# ---------------------------------------------------------------------------


class ExtractionError(VasooliError):
    """Raised when fact extraction fails or produces invalid output."""
    pass


class DocumentParsingError(VasooliError):
    """Raised when a document cannot be parsed (corrupt PDF, unsupported format)."""
    pass


class AmbiguousClauseError(VasooliError):
    """Raised when a clause is too ambiguous for automated extraction."""
    pass


# ---------------------------------------------------------------------------
# Policy Errors
# ---------------------------------------------------------------------------


class PolicyEvaluationError(VasooliError):
    """Raised when policy rule evaluation fails."""
    pass


class PolicyNotFoundError(VasooliError):
    """Raised when a referenced policy rule does not exist."""
    pass


class PolicyVersionConflictError(VasooliError):
    """Raised when no valid policy version exists for the given effective date."""
    pass


# ---------------------------------------------------------------------------
# Financial Errors
# ---------------------------------------------------------------------------


class FinancialCalculationError(VasooliError):
    """Raised when a financial calculation fails or produces invalid results."""
    pass


class InvalidRateConfigError(VasooliError):
    """Raised when rate configuration is missing or invalid."""
    pass


# ---------------------------------------------------------------------------
# Validation Errors
# ---------------------------------------------------------------------------


class OutputValidationError(VasooliError):
    """Raised when LLM-generated output fails fact-consistency validation."""
    pass


class EvidenceMissingError(VasooliError):
    """Raised when a determination is attempted without linked evidence."""
    pass


class SchemaValidationError(VasooliError):
    """Raised when output fails structural/schema validation."""
    pass


# ---------------------------------------------------------------------------
# Security Errors
# ---------------------------------------------------------------------------


class DocumentSecurityError(VasooliError):
    """Raised when a document fails security checks (MIME, size, malware)."""
    pass


class PromptInjectionError(VasooliError):
    """Raised when prompt injection is detected in contract text."""
    pass


class TenantAccessError(VasooliError):
    """Raised when a user attempts cross-tenant resource access."""
    pass


# ---------------------------------------------------------------------------
# Audit & Persistence Errors
# ---------------------------------------------------------------------------


class AuditIntegrityError(VasooliError):
    """Raised when an audit record modification is attempted (immutable records)."""
    pass


class PersistenceError(VasooliError):
    """Raised when database storage or transaction execution fails."""
    pass


class DuplicateReportError(PersistenceError):
    """Raised when attempting to insert a duplicate report without version bump."""
    pass
