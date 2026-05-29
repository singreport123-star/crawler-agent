"""
Compiler: context.json → execution_plan.json

Pipeline:
  1. validate context (pydantic)
  2. normalize
  3. capability transforms
  4. assemble execution_plan
  5. canonical serialize + plan_hash
"""
from __future__ import annotations
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from compiler.transforms.csrf_token import apply as csrf_apply, build_post_payload, _canonicalize_field_name
from compiler.transforms.html_table import apply as html_apply
from compiler.validators.validate import validate_context, validate_execution_plan


# ---------- canonical serialization (FROZEN contract) ----------

def canonical_dumps(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_plan_hash(plan: dict) -> str:
    """plan_hash を除いた dict で hash を計算する"""
    plan_without_hash = {k: v for k, v in plan.items() if k != "plan_hash"}
    serialized = canonical_dumps(plan_without_hash)
    return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


# ---------- compiler ----------

def compile_context(context_path: str, output_path: str | None = None) -> dict:
    """
    context.json → execution_plan.json

    Args:
        context_path: context.json 路徑
        output_path: 輸出路徑，None 則只回傳不寫檔

    Returns:
        execution_plan dict
    """
    with open(context_path, encoding="utf-8") as f:
        raw = json.load(f)

    # 1. validate
    ctx = validate_context(raw)
    context = raw  # 後續用 raw dict 操作，pydantic 已驗證過

    # 2. capability transforms
    steps = []

    auth_caps = ctx.capabilities.auth
    response_caps = ctx.capabilities.response

    # csrf_token → load_page + extract_csrf
    if "csrf_token" in auth_caps:
        steps.extend(csrf_apply(context))

    # post_query step（中間連接 auth → response）
    post_payload = build_post_payload(context)
    consumes = [
        "steps.extract_csrf.outputs.csrf_token",
    ]
    # 加上 selector type 的 extra_fields（用 canonical name）
    for ef in context.get("extra_fields", []):
        if ef["value"]["type"] == "selector":
            canonical = _canonicalize_field_name(ef["field"])
            consumes.append(f"steps.extract_csrf.outputs.{canonical}")

    steps.append({
        "id": "post_query",
        "type": "http_request",
        "session": "default",
        "consumes": consumes,
        "produces": ["steps.post_query.outputs.html"],
        "request": {
            "method": context["request"]["method"],
            "url": context["entry_url"],
            "payload": post_payload,
        },
    })

    # html_table → parse_result + save_output
    if "html_table" in response_caps:
        steps.extend(html_apply(context, post_step_id="post_query"))

    # 3. assemble plan（不含 plan_hash）
    plan: dict = {
        "version": "1.0",
        "plan_hash": "",  # placeholder
        "site": context["site"],
        "inputs": {
            name: {"type": inp["type"], "cli": f"--{name}"}
            for name, inp in context["inputs"].items()
        },
        "steps": steps,
    }

    # 4. plan_hash
    plan["plan_hash"] = compute_plan_hash(plan)

    # 5. validate output
    validate_execution_plan(plan)

    # 6. write
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        print(f"compiled → {output_path}")
        print(f"plan_hash = {plan['plan_hash']}")

    return plan


# ---------- CLI ----------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compile context.json → execution_plan.json")
    parser.add_argument("--context", default="context/tdcc_context.json")
    parser.add_argument("--output",  default="plans/tdcc_execution_plan_compiled.json")
    args = parser.parse_args()

    compile_context(args.context, args.output)
