"""Pydantic schemas for the unified Step Result / Error contracts.

These are part of the frozen protocol (Milestone 1). Do not change field
names without bumping the contract version, since program4 and the compiler
depend on them.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ErrorContract(BaseModel):
    """Unified error contract. error code drives classification + retry."""

    code: str
    message: str
    retryable: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class StepMetrics(BaseModel):
    duration_ms: int = 0


class StepResult(BaseModel):
    """Unified result every action handler must return.

    interpolation always reads from outputs via {{steps.<id>.outputs.<key>}}.
    """

    status: str  # "success" | "failed"
    outputs: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)
    metrics: StepMetrics = Field(default_factory=StepMetrics)
    error: Optional[ErrorContract] = None

    def is_success(self) -> bool:
        return self.status == "success"


class StepError(Exception):
    """Raised by handlers to signal a structured error contract."""

    def __init__(self, code: str, message: str, retryable: bool = False,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error = ErrorContract(
            code=code,
            message=message,
            retryable=retryable,
            details=details or {},
        )
