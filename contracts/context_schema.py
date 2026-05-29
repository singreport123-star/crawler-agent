"""
context.json pydantic schema v1 — FROZEN
允許：新 parser type、新 capability、新 source type
不允許：改既有欄位語義、改 binding 結構
"""
from __future__ import annotations
from typing import Literal, Union
from pydantic import BaseModel, Field


# ---------- source types ----------

class SelectorSource(BaseModel):
    type: Literal["selector"]
    selector: str

class ConstantSource(BaseModel):
    type: Literal["constant"]
    value: str

class CookieSource(BaseModel):
    type: Literal["cookie"]
    name: str

class MetaSource(BaseModel):
    type: Literal["meta"]
    selector: str

AnySource = Union[SelectorSource, ConstantSource, CookieSource, MetaSource]


# ---------- inject_to types ----------

class FormFieldInject(BaseModel):
    type: Literal["form_field"]
    name: str

class HeaderInject(BaseModel):
    type: Literal["header"]
    name: str

AnyInject = Union[FormFieldInject, HeaderInject]


# ---------- auth ----------

class AuthToken(BaseModel):
    source: AnySource = Field(..., discriminator="type")
    inject_to: AnyInject = Field(..., discriminator="type")

class AuthBinding(BaseModel):
    source: AnySource = Field(..., discriminator="type")
    inject_to: AnyInject = Field(..., discriminator="type")

class AuthSchema(BaseModel):
    type: Literal["csrf_token"]
    token: AuthToken
    bindings: list[AuthBinding] = []


# ---------- request ----------

class RequestSchema(BaseModel):
    method: Literal["GET", "POST", "PUT", "DELETE"]
    content_type: Literal[
        "application/x-www-form-urlencoded",
        "application/json",
        "multipart/form-data",
    ] = "application/x-www-form-urlencoded"


# ---------- inputs ----------

class InputField(BaseModel):
    type: Literal["string", "integer", "date"]
    required: bool = False
    field: str


# ---------- extra_fields ----------

class ExtraField(BaseModel):
    field: str
    value: AnySource = Field(..., discriminator="type")


# ---------- response ----------

class ParserSchema(BaseModel):
    type: Literal["html_table", "json_path", "csv", "xml"]
    format: Literal["html", "json", "csv", "xml"]
    selector: str | None = None
    column_mode: Literal["index", "header"] = "header"

class PostProcess(BaseModel):
    skip_row_keyword: str | None = None

class ResponseSchema(BaseModel):
    parser: ParserSchema
    data_shape: Literal["table_rows", "key_value", "single_record", "nested"]
    post_process: PostProcess = PostProcess()


# ---------- capabilities ----------

class CapabilitiesSchema(BaseModel):
    auth: list[str] = []
    response: list[str] = []


# ---------- root ----------

class ContextSchema(BaseModel):
    schema_version: str = "1.0"
    site: str
    entry_url: str
    auth: AuthSchema | None = None
    request: RequestSchema
    inputs: dict[str, InputField]
    extra_fields: list[ExtraField] = []
    response: ResponseSchema
    capabilities: CapabilitiesSchema
