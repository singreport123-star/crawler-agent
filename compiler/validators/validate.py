"""
Compiler validation pass
context.json → validate → normalized dict
"""
from __future__ import annotations
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from contracts.context_schema import ContextSchema
from pydantic import ValidationError


def validate_context(raw: dict) -> ContextSchema:
    try:
        return ContextSchema(**raw)
    except ValidationError as e:
        raise ValueError(f"context.json validation failed:\n{e}") from e


def validate_execution_plan(plan: dict) -> dict:
    """
    基本 execution_plan 驗證：
    - version 存在
    - plan_hash 存在
    - steps 非空
    """
    assert plan.get("version"), "execution_plan missing version"
    assert plan.get("plan_hash"), "execution_plan missing plan_hash"
    assert plan.get("steps"), "execution_plan missing steps"
    return plan
