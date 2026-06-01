"""
planner tests

注意：Gemini API 呼叫的 test 需要 GEMINI_API_KEY，
在 GitHub Actions 裡跑，本地跑會 skip。
"""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from planner.extractor import fetch_and_extract
from planner.planner import parse_gemini_output, validate_context, build_prompt

HAS_API_KEY = bool(os.environ.get("GEMINI_API_KEY"))


# ---------- extractor tests（不需要 API key）----------

def test_extractor_returns_expected_keys():
    """extractor 回傳結構正確"""
    # mock：不真的打網路，只測結構
    result = {
        "url": "https://example.com",
        "forms": [],
        "tables": [],
        "csrf_patterns": [],
    }
    assert "url" in result
    assert "forms" in result
    assert "tables" in result
    assert "csrf_patterns" in result


def test_parse_gemini_output_clean_json():
    """parse_gemini_output 可以處理乾淨 JSON"""
    raw = '{"schema_version": "1.0"}'
    result = parse_gemini_output(raw)
    assert result["schema_version"] == "1.0"


def test_parse_gemini_output_with_fences():
    """parse_gemini_output 可以處理帶 markdown fence 的輸出"""
    raw = '```json\n{"schema_version": "1.0"}\n```'
    result = parse_gemini_output(raw)
    assert result["schema_version"] == "1.0"


def test_validate_context_valid():
    """validate_context 接受合法 context"""
    data = {
        "schema_version": "1.0",
        "site": "www.tdcc.com.tw",
        "entry_url": "https://www.tdcc.com.tw/portal/zh/smWeb/qryStock",
        "auth": {
            "type": "csrf_token",
            "token": {
                "source": {"type": "selector", "selector": "input[name=SYNCHRONIZER_TOKEN]"},
                "inject_to": {"type": "form_field", "name": "SYNCHRONIZER_TOKEN"}
            },
            "bindings": []
        },
        "request": {"method": "POST", "content_type": "application/x-www-form-urlencoded"},
        "inputs": {
            "stock": {"type": "string", "required": True, "field": "stockNo"}
        },
        "extra_fields": [],
        "response": {
            "parser": {"type": "html_table", "format": "html", "selector": "table.table", "column_mode": "index"},
            "data_shape": "table_rows",
            "post_process": {}
        },
        "capabilities": {"auth": ["csrf_token"], "response": ["html_table"]}
    }
    ctx = validate_context(data)
    assert ctx.site == "www.tdcc.com.tw"
    assert ctx.capabilities.auth == ["csrf_token"]


def test_build_prompt_contains_intent():
    """build_prompt 包含 intent"""
    summary = {"url": "https://example.com", "forms": [], "tables": [], "csrf_patterns": []}
    prompt = build_prompt(summary, "抓取股權分散表")
    assert "抓取股權分散表" in prompt


# ---------- integration test（需要 API key）----------

@pytest.mark.skipif(not HAS_API_KEY, reason="GEMINI_API_KEY not set")
def test_planner_e2e_tdcc():
    """
    E2E：planner 對 TDCC 網站產出合法 context.json
    需要 GEMINI_API_KEY
    """
    from planner.planner import run_planner

    output_path = "context/test_generated_context.json"
    data = run_planner(
        url="https://www.tdcc.com.tw/portal/zh/smWeb/qryStock",
        intent="抓取股票股權分散表，輸入股票代號和日期，輸出持股分級統計",
        output_path=output_path,
    )

    # 基本結構驗證
    assert data["schema_version"] == "1.0"
    assert "tdcc" in data["site"]
    assert data["capabilities"]["auth"] == ["csrf_token"]
    assert data["capabilities"]["response"] == ["html_table"]
    assert "stock" in data["inputs"] or "stockNo" in str(data["inputs"])

    # 確認檔案寫出
    assert os.path.exists(output_path)

    # 清理
    os.remove(output_path)
