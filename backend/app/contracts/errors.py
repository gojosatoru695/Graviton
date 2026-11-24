from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(str, Enum):
    """
    Standardized, machine-readable error codes across Jarvis services.
    """
    FILE_PARSE_ERROR = "FILE_PARSE_ERROR"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    MISSING_REQUIRED_COLUMN = "MISSING_REQUIRED_COLUMN"
    AMBIGUOUS_PAYMENT_MATCH = "AMBIGUOUS_PAYMENT_MATCH"
    DUPLICATE_PAYMENT_CANDIDATE = "DUPLICATE_PAYMENT_CANDIDATE"
    UNEXPLAINED_SETTLEMENT_VARIANCE = "UNEXPLAINED_SETTLEMENT_VARIANCE"
    MISSING_CONNECTED_ACCOUNT = "MISSING_CONNECTED_ACCOUNT"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    PROMPT_INJECTION_BLOCKED = "PROMPT_INJECTION_BLOCKED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    LLM_OUTPUT_INVALID = "LLM_OUTPUT_INVALID"


class ErrorDetail(BaseModel):
    """
    Field-level or contextual error breakdown.
    """
    model_config = ConfigDict(strict=True, extra="forbid")

    field: Optional[str] = Field(
        None,
        description="Path or identifier of the failing field/column if applicable."
    )
    message: str = Field(
        ...,
        description="Human-readable explanation of the specific error."
    )
    rejected_value: Optional[Any] = Field(
        None,
        description="Sanitized representation of the invalid input value (never raw secrets)."
    )


class JarvisContractException(Exception):
    """
    Base application exception adhering to Jarvis contract error specifications.
    """
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        correlation_id: str,
        details: Optional[List[ErrorDetail]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.correlation_id = correlation_id
        self.details = details or []
        self.context = context or {}
