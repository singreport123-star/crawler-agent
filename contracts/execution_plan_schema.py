"""
execution_plan.json pydantic schema — FROZEN
Runtime 只讀，不可修改。
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class StepBase(BaseModel):
    id: str
    type: str
    consumes: list[str] = []
    produces: list[str] = []


class HttpRequestStep(StepBase):
    type: Literal["http_request"]
    session: str = "default"
    request: dict[str, Any]


class ExtractHtmlStep(StepBase):
    type: Literal["extract_html"]
    session: str = "default"
    from_: str = Field(..., alias="from")
    selectors: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)


class ParseTableStep(StepBase):
    type: Literal["parse_table"]
    from_: str = Field(..., alias="from")
    selectors: dict[str, Any]
    column_mode: Literal["index", "header"] = "header"
    skip_row_keyword: str | None = None
    add_columns: dict[str, str] = {}

    model_config = ConfigDict(populate_by_name=True)


class SaveCsvStep(StepBase):
    type: Literal["save_csv"]
    from_: str = Field(..., alias="from")
    path: str
    encoding: str = "utf-8-sig"

    model_config = ConfigDict(populate_by_name=True)


AnyStep = HttpRequestStep | ExtractHtmlStep | ParseTableStep | SaveCsvStep


class PlanInput(BaseModel):
    type: Literal["string", "integer", "date"]
    cli: str


class ExecutionPlanSchema(BaseModel):
    version: str = "1.0"
    plan_hash: str | None = None
    site: str
    inputs: dict[str, PlanInput]
    steps: list[dict]  # raw dict，runtime 自己 dispatch
