"""
csrf_token capability transform

context.json capabilities.auth = ["csrf_token"]
→ 注入 load_page + extract_csrf steps
→ 在 post_query payload 裡帶入 token + bindings
"""
from __future__ import annotations
from typing import Any


def apply(context: dict) -> list[dict]:
    """
    回傳要注入到 execution_plan.steps 的 step list。
    只負責 csrf_token 相關的 steps。
    """
    entry_url = context["entry_url"]
    auth = context["auth"]
    token_selector = auth["token"]["source"]["selector"]
    token_field = auth["token"]["inject_to"]["name"]

    # 從 bindings 收集額外要 extract 的欄位
    # 例如 firDate 來自 extra_fields selector type
    extra_selectors = _collect_selector_extra_fields(context)

    # 從 bindings 收集 constant 注入（例如 SYNCHRONIZER_URI）
    binding_fields = _collect_binding_fields(auth)

    steps = []

    # Step 1: load_page
    steps.append({
        "id": "load_page",
        "type": "http_request",
        "session": "default",
        "consumes": [],
        "produces": ["steps.load_page.outputs.html"],
        "request": {
            "method": "GET",
            "url": entry_url,
        },
    })

    # Step 2: extract_csrf
    selectors: dict[str, Any] = {
        "csrf_token": {
            "type": "css",
            "query": token_selector,
            "attr": "value",
        }
    }
    produces = [
        "steps.extract_csrf.outputs.csrf_token",
    ]
    for name, selector in extra_selectors.items():
        canonical_name = _canonicalize_field_name(name)
        selectors[canonical_name] = {"type": "css", "query": selector, "attr": "value"}
        produces.append(f"steps.extract_csrf.outputs.{canonical_name}")

    steps.append({
        "id": "extract_csrf",
        "type": "extract_html",
        "session": "default",
        "consumes": ["steps.load_page.outputs.html"],
        "produces": produces,
        "from": "{{steps.load_page.outputs.html}}",
        "selectors": selectors,
    })

    return steps


def build_post_payload(context: dict) -> dict:
    """
    根據 context 建構 POST payload（用於 post_query step）。
    key 順序對齊手寫版 execution_plan。
    """
    auth = context["auth"]
    token_field = auth["token"]["inject_to"]["name"]

    payload: dict[str, str] = {}

    # 1. token
    payload[token_field] = "{{steps.extract_csrf.outputs.csrf_token}}"

    # 2. bindings（constants）
    for binding in auth.get("bindings", []):
        if binding["source"]["type"] == "constant":
            field_name = binding["inject_to"]["name"]
            payload[field_name] = binding["source"]["value"]

    # 3. extra_fields（constant 先，selector 後）
    for ef in context.get("extra_fields", []):
        field = ef["field"]
        val = ef["value"]
        if val["type"] == "constant":
            payload[field] = val["value"]

    # 4. selector extra_fields（用 canonical name 的 interpolation）
    for ef in context.get("extra_fields", []):
        field = ef["field"]
        val = ef["value"]
        if val["type"] == "selector":
            canonical = _canonicalize_field_name(field)
            payload[field] = f"{{{{steps.extract_csrf.outputs.{canonical}}}}}"

    # 5. inputs
    for input_name, input_def in context["inputs"].items():
        payload[input_def["field"]] = f"{{{{input.{input_name}}}}}"

    return payload


def _collect_selector_extra_fields(context: dict) -> dict[str, str]:
    """收集 extra_fields 裡 type=selector 的欄位，要在 extract_csrf 裡一起抓。"""
    result = {}
    for ef in context.get("extra_fields", []):
        if ef["value"]["type"] == "selector":
            result[ef["field"]] = ef["value"]["selector"]
    return result


def _canonicalize_field_name(name: str) -> str:
    """
    camelCase → snake_case，對齊手寫版 execution_plan 的 key 命名。
    例如 firDate → fir_date
    """
    import re
    return re.sub(r"([A-Z])", lambda m: "_" + m.group(1).lower(), name)


def _collect_binding_fields(auth: dict) -> dict[str, str]:
    """收集 auth.bindings 裡 type=constant 的欄位。"""
    result = {}
    for binding in auth.get("bindings", []):
        if binding["source"]["type"] == "constant":
            result[binding["inject_to"]["name"]] = binding["source"]["value"]
    return result
