"""
compiler tests

關鍵驗證：compiler 產出的 plan_hash 必須對上 Milestone 1 的 hash
"""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from compiler.compiler import compile_context, compute_plan_hash, canonical_dumps

CONTEXT_PATH     = os.path.join(os.path.dirname(__file__), "..", "context", "tdcc_context.json")
PLAN_PATH        = os.path.join(os.path.dirname(__file__), "..", "plans", "tdcc_execution_plan.json")
MILESTONE1_HASH  = "sha256:bfd46d874c96a41588fd9b9c48ef55f5b39ffb6376e65b20b448dc7b82c36845"


def test_canonical_dumps_is_deterministic():
    data = {"b": 2, "a": 1, "c": {"z": 3, "x": 1}}
    s1 = canonical_dumps(data)
    s2 = canonical_dumps(data)
    assert s1 == s2


def test_canonical_dumps_sorts_keys():
    data = {"b": 2, "a": 1}
    s = canonical_dumps(data)
    assert s.index('"a"') < s.index('"b"')


def test_plan_hash_deterministic():
    with open(PLAN_PATH, encoding="utf-8") as f:
        plan = json.load(f)
    h1 = compute_plan_hash(plan)
    h2 = compute_plan_hash(plan)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_compiler_produces_valid_plan():
    plan = compile_context(CONTEXT_PATH)
    assert plan["version"] == "1.0"
    assert plan["plan_hash"].startswith("sha256:")
    assert len(plan["steps"]) == 5


def test_compiler_step_ids():
    plan = compile_context(CONTEXT_PATH)
    ids = [s["id"] for s in plan["steps"]]
    assert ids == ["load_page", "extract_csrf", "post_query", "parse_result", "save_output"]


def test_compiler_step_types():
    plan = compile_context(CONTEXT_PATH)
    types = [s["type"] for s in plan["steps"]]
    assert types == ["http_request", "extract_html", "http_request", "parse_table", "save_csv"]


def test_compiler_post_payload_contains_csrf():
    plan = compile_context(CONTEXT_PATH)
    post = next(s for s in plan["steps"] if s["id"] == "post_query")
    payload = post["request"]["payload"]
    assert "SYNCHRONIZER_TOKEN" in payload
    assert payload["SYNCHRONIZER_TOKEN"] == "{{steps.extract_csrf.outputs.csrf_token}}"


def test_compiler_post_payload_contains_inputs():
    plan = compile_context(CONTEXT_PATH)
    post = next(s for s in plan["steps"] if s["id"] == "post_query")
    payload = post["request"]["payload"]
    assert payload.get("stockNo") == "{{input.stock}}"
    assert payload.get("scaDate") == "{{input.date}}"


def test_compiler_parse_result_has_add_columns():
    plan = compile_context(CONTEXT_PATH)
    parse = next(s for s in plan["steps"] if s["id"] == "parse_result")
    add_cols = parse.get("add_columns", {})
    assert "日期" in add_cols
    assert "股票代號" in add_cols


def test_compiler_save_output_path():
    plan = compile_context(CONTEXT_PATH)
    save = next(s for s in plan["steps"] if s["id"] == "save_output")
    assert "{{input.stock}}" in save["path"]
    assert "{{input.date}}" in save["path"]


def test_compiler_hash_matches_milestone1():
    """
    最關鍵測試：compiler 產出的 plan 結構必須跟 Milestone 1 手寫版一致。
    如果 hash 不同，代表 compiler 產出的 execution_plan 跟手寫版有差異。
    這個測試會在 compiler 對齊後才會綠。
    """
    with open(PLAN_PATH, encoding="utf-8") as f:
        handwritten_plan = json.load(f)

    compiled_plan = compile_context(CONTEXT_PATH)

    # 比較 plan_hash
    handwritten_hash = handwritten_plan["plan_hash"]
    compiled_hash    = compiled_plan["plan_hash"]

    if handwritten_hash != compiled_hash:
        # 印出差異方便 debug
        print("\n=== handwritten steps ===")
        print(json.dumps(handwritten_plan["steps"], ensure_ascii=False, indent=2))
        print("\n=== compiled steps ===")
        print(json.dumps(compiled_plan["steps"], ensure_ascii=False, indent=2))

    assert compiled_hash == handwritten_hash, (
        f"plan_hash mismatch\n"
        f"  handwritten: {handwritten_hash}\n"
        f"  compiled:    {compiled_hash}\n"
        f"  → compiler output does not match Milestone 1 execution_plan"
    )
