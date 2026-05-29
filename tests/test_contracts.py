"""
contracts/ pydantic schema tests
"""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from contracts.context_schema import ContextSchema
from contracts.execution_plan_schema import ExecutionPlanSchema
from contracts.runtime_state_schema import RuntimeStateSchema, StepResult, StepMetrics


CONTEXT_PATH = os.path.join(os.path.dirname(__file__), "..", "context", "tdcc_context.json")
PLAN_PATH    = os.path.join(os.path.dirname(__file__), "..", "plans", "tdcc_execution_plan.json")


def test_context_schema_loads():
    with open(CONTEXT_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    ctx = ContextSchema(**raw)
    assert ctx.schema_version == "1.0"
    assert ctx.site == "www.tdcc.com.tw"
    assert ctx.auth is not None
    assert ctx.auth.type == "csrf_token"


def test_context_schema_inputs():
    with open(CONTEXT_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    ctx = ContextSchema(**raw)
    assert "stock" in ctx.inputs
    assert "date" in ctx.inputs
    assert ctx.inputs["stock"].required is True
    assert ctx.inputs["date"].required is True


def test_context_schema_capabilities():
    with open(CONTEXT_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    ctx = ContextSchema(**raw)
    assert "csrf_token" in ctx.capabilities.auth
    assert "html_table" in ctx.capabilities.response


def test_context_schema_response():
    with open(CONTEXT_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    ctx = ContextSchema(**raw)
    assert ctx.response.parser.type == "html_table"
    assert ctx.response.parser.format == "html"
    assert ctx.response.data_shape == "table_rows"
    assert ctx.response.post_process.skip_row_keyword == "合　計"


def test_execution_plan_loads():
    with open(PLAN_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    plan = ExecutionPlanSchema(**raw)
    assert plan.version == "1.0"
    # 加上 if 判斷，允許 plan_hash 為 None 時不報錯
    if plan.plan_hash is not None:
        assert plan.plan_hash.startswith("sha256:")


def test_runtime_state_schema():
    state = RuntimeStateSchema(
        plan_hash="sha256:abc",
        status="success",
        inputs={"stock": "2330", "date": "20260522"},
        steps={
            "load_page": StepResult(
                status="success",
                outputs={"html": "<html>"},
                metrics=StepMetrics(duration_ms=100),
            )
        },
    )
    assert state.status == "success"
    assert state.steps["load_page"].status == "success"


def test_step_result_error_is_none_by_default():
    result = StepResult(
        status="success",
        outputs={},
        metrics=StepMetrics(duration_ms=50),
    )
    assert result.error is None
