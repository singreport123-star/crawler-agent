"""
no_auth transform

沒有 auth（auth: null）的網站，直接 POST，payload 只有 extra_fields + inputs。
"""
from __future__ import annotations


def build_post_payload(context: dict) -> dict:
    payload: dict[str, str] = {}

    # extra_fields（constants only，no selector）
    for ef in context.get("extra_fields", []):
        field = ef["field"]
        val = ef["value"]
        if val["type"] == "constant":
            payload[field] = val["value"]

    # inputs
    for input_name, input_def in context["inputs"].items():
        payload[input_def["field"]] = f"{{{{input.{input_name}}}}}"

    return payload
