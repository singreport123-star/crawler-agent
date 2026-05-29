"""
runtime_state.json pydantic schema — FROZEN
動態執行狀態，runtime 寫，program4 讀。
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool
    details: dict[str, Any] = {}


class StepMetrics(BaseModel):
    duration_ms: float


class StepResult(BaseModel):
    status: Literal["success", "failed", "skipped", "running"]
    outputs: dict[str, Any] = {}
    meta: dict[str, Any] = {}
    metrics: StepMetrics
    error: ErrorDetail | None = None


class RuntimeStateSchema(BaseModel):
    plan_hash: str
    status: Literal["running", "success", "failed"]
    inputs: dict[str, str]
    steps: dict[str, StepResult] = {}
